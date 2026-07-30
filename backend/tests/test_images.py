import unittest

from fastapi import HTTPException, Request

from fakedb import FakeDatabase

from app.images import ImageError, imageId, imageUrl, probeImage
from app.main import (
    adminDeleteImage,
    adminListImages,
    adminUpdateImageAlt,
    getImage,
    uploadImage,
)
from app.schemas import ImageAltUpdate


def pngBytes(width: int = 640, height: int = 360, marker: bytes = b"") -> bytes:
    header = b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR"
    return header + width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00" + marker


def gifBytes(width: int = 12, height: int = 8) -> bytes:
    return b"GIF89a" + width.to_bytes(2, "little") + height.to_bytes(2, "little") + b"\x80\x00\x00"


def jpegBytes(width: int = 800, height: int = 600) -> bytes:
    app0 = b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    frame = b"\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big") + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    sof0 = b"\xff\xc0" + (len(frame) + 2).to_bytes(2, "big") + frame
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def webpLosslessBytes(width: int = 300, height: int = 200) -> bytes:
    bits = (width - 1) | ((height - 1) << 14)
    payload = b"\x2f" + bits.to_bytes(4, "little") + b"\x00" * 8
    body = b"WEBP" + b"VP8L" + len(payload).to_bytes(4, "little") + payload
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def webpExtendedBytes(width: int = 1600, height: int = 900) -> bytes:
    payload = b"\x10\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little") + b"\x00" * 8
    body = b"WEBP" + b"VP8X" + len(payload).to_bytes(4, "little") + payload
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def uploadRequest(data: bytes, filename: str = "", alt: str = "") -> Request:
    headers = [(b"content-length", str(len(data)).encode()), (b"host", b"api.jackhales.com")]
    if filename:
        headers.append((b"x-image-filename", filename.encode()))
    if alt:
        headers.append((b"x-image-alt", alt.encode()))

    async def receive() -> dict:
        return {"type": "http.request", "body": data, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/admin/images",
            "headers": headers,
            "scheme": "https",
            "server": ("api.jackhales.com", 443),
            "query_string": b"",
            "client": ("127.0.0.1", 1234),
        },
        receive,
    )


def plainRequest() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/admin/images",
            "headers": [(b"host", b"api.jackhales.com")],
            "scheme": "https",
            "server": ("api.jackhales.com", 443),
            "query_string": b"",
            "client": ("127.0.0.1", 1234),
        }
    )


class ImageAuthorizationTest(unittest.TestCase):
    def testEveryImageRouteExceptTheServedBytesRequiresTheAdminSession(self) -> None:
        from app.main import adminOnly, app

        guarded = {
            (route.path, method)
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/admin/images")
            for method in route.methods
            if any(dependency.call is adminOnly for dependency in route.dependant.dependencies)
        }
        expected = {
            ("/api/admin/images", "POST"),
            ("/api/admin/images", "GET"),
            ("/api/admin/images/{imageId}", "PATCH"),
            ("/api/admin/images/{imageId}", "DELETE"),
        }

        self.assertEqual(guarded & expected, expected)


class ImageProbeTest(unittest.TestCase):
    def testEverySupportedFormatReportsItsOwnDimensions(self) -> None:
        cases = [
            (pngBytes(640, 360), "image/png", 640, 360),
            (jpegBytes(800, 600), "image/jpeg", 800, 600),
            (gifBytes(12, 8), "image/gif", 12, 8),
            (webpLosslessBytes(300, 200), "image/webp", 300, 200),
            (webpExtendedBytes(1600, 900), "image/webp", 1600, 900),
        ]
        for data, contentType, width, height in cases:
            with self.subTest(contentType=contentType, width=width):
                probe = probeImage(data)
                self.assertEqual(probe["contentType"], contentType)
                self.assertEqual((probe["width"], probe["height"]), (width, height))
                self.assertEqual(probe["byteSize"], len(data))

    def testTheDeclaredTypeNeverOverridesWhatTheBytesProve(self) -> None:
        # An SVG dressed up as a PNG upload is still refused, because nothing reads the header.
        with self.assertRaises(ImageError):
            probeImage(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')

    def testEmptyOversizedAndUnknownBytesAreRefused(self) -> None:
        for data in (b"", b"not an image at all", pngBytes(0, 0)):
            with self.subTest(data=data[:12]), self.assertRaises(ImageError):
                probeImage(data)

    def testAnImageLargerThanTheCapIsRefusedBeforeItIsStored(self) -> None:
        with self.assertRaises(ImageError):
            probeImage(pngBytes(10, 10, marker=b"\x00" * (8 * 1024 * 1024)))

    def testAnImageTooLargeInEitherDirectionIsRefused(self) -> None:
        with self.assertRaises(ImageError):
            probeImage(pngBytes(20000, 10))

    def testTheUrlCarriesTheDimensionsAndStaysUnderTheApiBase(self) -> None:
        self.assertEqual(
            imageUrl("abc123", 1600, 900, "https://api.jackhales.com/api/"),
            "https://api.jackhales.com/api/images/abc123?w=1600&h=900",
        )


class ImageStorageTest(unittest.IsolatedAsyncioTestCase):
    async def testUploadingStoresTheBytesOnceAndReturnsAContentAddressedUrl(self) -> None:
        database = FakeDatabase()
        data = pngBytes(640, 360)

        result = await uploadImage(uploadRequest(data, "diagram.png", "A wiring diagram"), database)

        self.assertEqual(result["id"], imageId(data))
        self.assertEqual(result["url"], f"https://api.jackhales.com/api/images/{imageId(data)}?w=640&h=360")
        self.assertEqual(result["contentType"], "image/png")
        self.assertEqual((result["width"], result["height"]), (640, 360))
        self.assertEqual(result["alt"], "A wiring diagram")
        self.assertEqual(result["filename"], "diagram.png")
        self.assertIsInstance(result["createdUnix"], float)

    async def testTheSameImagePastedTwiceIsStoredOnce(self) -> None:
        database = FakeDatabase()
        data = pngBytes(640, 360)

        first = await uploadImage(uploadRequest(data, "one.png"), database)
        second = await uploadImage(uploadRequest(data, "two.png"), database)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(database.articleImages.documents), 1)

    async def testAnAltTextArrivingWithADuplicateFillsAnEmptyOne(self) -> None:
        database = FakeDatabase()
        data = pngBytes(200, 100)
        await uploadImage(uploadRequest(data, "chart.png"), database)

        second = await uploadImage(uploadRequest(data, "chart.png", "A revenue chart"), database)

        self.assertEqual(second["alt"], "A revenue chart")

    async def testAFilenameCannotCarryAPathAndAltTextIsCollapsed(self) -> None:
        database = FakeDatabase()

        result = await uploadImage(
            uploadRequest(pngBytes(10, 10), "../../etc/passwd.png", "  spaced   out  "), database
        )

        self.assertEqual(result["filename"], "passwd.png")
        self.assertEqual(result["alt"], "spaced out")

    async def testAnUploadThatIsNotAnImageIsRejectedWith422(self) -> None:
        database = FakeDatabase()

        with self.assertRaises(HTTPException) as caught:
            await uploadImage(uploadRequest(b"just some text"), database)

        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(database.articleImages.documents, [])

    async def testTheLibraryStopsAcceptingUploadsAtItsCeiling(self) -> None:
        database = FakeDatabase()
        database.articleImages.documents.append({"_id": "existing", "byteSize": 256 * 1024 * 1024, "data": b""})

        with self.assertRaises(HTTPException) as caught:
            await uploadImage(uploadRequest(pngBytes(10, 10)), database)

        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("full", caught.exception.detail)

    async def testAnOversizedContentLengthIsRefusedBeforeTheBodyIsRead(self) -> None:
        database = FakeDatabase()
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/admin/images",
                "headers": [(b"content-length", str(9 * 1024 * 1024).encode()), (b"host", b"api.jackhales.com")],
                "scheme": "https",
                "server": ("api.jackhales.com", 443),
                "query_string": b"",
                "client": ("127.0.0.1", 1234),
            }
        )

        with self.assertRaises(HTTPException) as caught:
            await uploadImage(request, database)

        self.assertEqual(caught.exception.status_code, 413)


class ImageServingTest(unittest.IsolatedAsyncioTestCase):
    async def testAStoredImageIsServedWithItsRealTypeAndAnImmutableCache(self) -> None:
        database = FakeDatabase()
        data = pngBytes(640, 360)
        stored = await uploadImage(uploadRequest(data), database)

        response = await getImage(stored["id"], database)

        self.assertEqual(response.body, data)
        self.assertEqual(response.media_type, "image/png")
        self.assertIn("immutable", response.headers["cache-control"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    async def testAnUnknownImageIsNotFound(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await getImage("nope", FakeDatabase())

        self.assertEqual(caught.exception.status_code, 404)


class ImageLibraryTest(unittest.IsolatedAsyncioTestCase):
    async def testTheListingReportsUsageAndNeverCarriesTheImageBytes(self) -> None:
        database = FakeDatabase()
        await uploadImage(uploadRequest(pngBytes(640, 360)), database)
        await uploadImage(uploadRequest(jpegBytes(800, 600)), database)

        listing = await adminListImages(plainRequest(), database)

        self.assertEqual(listing["total"], 2)
        self.assertEqual(listing["bytesUsed"], sum(image["byteSize"] for image in listing["images"]))
        self.assertEqual(listing["bytesAvailable"], 256 * 1024 * 1024 - listing["bytesUsed"])
        self.assertNotIn("data", str(listing))

    async def testAltTextCanBeCorrectedAfterUpload(self) -> None:
        database = FakeDatabase()
        stored = await uploadImage(uploadRequest(pngBytes(640, 360)), database)

        updated = await adminUpdateImageAlt(stored["id"], ImageAltUpdate(alt="A corrected description"), plainRequest(), database)

        self.assertEqual(updated["alt"], "A corrected description")
        self.assertGreaterEqual(updated["updatedUnix"], updated["createdUnix"])

    async def testAnUnusedImageCanBeDeleted(self) -> None:
        database = FakeDatabase()
        stored = await uploadImage(uploadRequest(pngBytes(640, 360)), database)

        self.assertEqual(await adminDeleteImage(stored["id"], database), {"deleted": True})
        self.assertEqual(database.articleImages.documents, [])

    async def testAnImageUsedByAnArticleCannotBeDeleted(self) -> None:
        database = FakeDatabase()
        stored = await uploadImage(uploadRequest(pngBytes(640, 360)), database)
        await database.articles.insert_one(
            {"title": "Prime research", "slug": "prime-research", "bodyMarkdown": f"![A chart]({stored['url']})"}
        )

        with self.assertRaises(HTTPException) as caught:
            await adminDeleteImage(stored["id"], database)

        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("Prime research", caught.exception.detail)
        self.assertEqual(len(database.articleImages.documents), 1)

    async def testAnImageUsedAsAHeroOrSocialCardCannotBeDeleted(self) -> None:
        for field, article in (
            ("heroImage", {"title": "Hero user", "heroImage": {"url": "", "alt": ""}}),
            ("seo", {"title": "Social user", "seo": {"ogImageUrl": ""}}),
        ):
            with self.subTest(field=field):
                database = FakeDatabase()
                stored = await uploadImage(uploadRequest(pngBytes(640, 360)), database)
                if field == "heroImage":
                    article["heroImage"]["url"] = stored["url"]
                else:
                    article["seo"]["ogImageUrl"] = stored["url"]
                await database.articles.insert_one(article)

                with self.assertRaises(HTTPException) as caught:
                    await adminDeleteImage(stored["id"], database)

                self.assertEqual(caught.exception.status_code, 409)

    async def testDeletingAnUnknownImageIsNotFound(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            await adminDeleteImage("nope", FakeDatabase())

        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
