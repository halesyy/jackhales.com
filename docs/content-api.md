# Draft Content API

Status: `1.0`

The content API lets a local command or agent work on **drafts** of jackhales.com
articles. It is authenticated by a single API key generated in `/admin`.

Publishing is deliberately not part of this surface. Only the admin session can
change an article's status, and a published article is read-only to every API key.

## The Key

- Exactly one key exists at a time. It lives in MongoDB as `apiKeys._id: "active"`.
- Generating a new key in `/admin` **supersedes** the previous one immediately.
- Only an HMAC-SHA256 hash is stored. The plaintext is shown once, at generation.
- The key is presented as `Authorization: Bearer <key>` or `X-API-Key: <key>`.
  It is never accepted from a query string.
- Format: `jhk_live_<43 url-safe characters>`. Only the last six are ever displayed again.

```sh
scripts/jackhales-content status      # where the key resolves from, never its value
scripts/jackhales-content login --apply   # store it in the macOS Keychain
scripts/jackhales-content whoami      # ask the API what this key may do
```

## Guardrails

| Guardrail | Behaviour |
| --- | --- |
| Publication state | `status`, `publish`, `published`, `publishedState` are rejected by the request model with `422` |
| AI attribution | `aiAssisted` is rejected with `422` and set to `true` by the API on every key-authenticated write |
| Published articles | Every write route returns `409` and changes nothing |
| Unknown fields | Rejected (`extra="forbid"`) rather than silently ignored |
| Deletion | Articles cannot be deleted; only sections within a draft can |
| Admin routes | `/api/admin/*` never accepts an API key — it requires the admin session cookie |
| Image and canonical URLs | Must start with `https://`, `http://` or `/` |
| Ambiguous text replacement | Refused unless `expectedCount` confirms the number of matches |
| Failed edits | Validated before the write, so a rejected edit leaves the draft untouched |

## Endpoints

All paths are relative to `https://api.jackhales.com/api`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/content/whoami` | Scope, label, and the explicit list of what the key cannot do |
| `GET` | `/content/articles` | List articles; `?status=draft` or `?status=published` |
| `GET` | `/content/articles/{slug}` | Read one article, including the raw `bodyMarkdown` |
| `POST` | `/content/articles` | Create a draft (`status` is always `draft`) |
| `PATCH` | `/content/articles/{slug}` | Update title, slug, summary, `publishedAt`, `seo`, `heroImage` |
| `PUT` | `/content/articles/{slug}/body` | Replace the whole raw Markdown body |
| `POST` | `/content/articles/{slug}/body/replace` | Exact text replacement with an occurrence guard |
| `GET` | `/content/articles/{slug}/sections` | List addressable sections |
| `PUT` | `/content/articles/{slug}/sections/{sectionId}` | Rewrite one section's heading and/or body |
| `POST` | `/content/articles/{slug}/sections` | Insert a section `after` or `before` another |
| `DELETE` | `/content/articles/{slug}/sections/{sectionId}` | Remove one section |

Reads cover published articles too, so an agent can use live work as context.
Writes are refused on anything that is not a draft.

## Sections

Sections are how an article is edited without rewriting it. The body is split on
ATX headings, ignoring any heading inside a fenced code block. Each section gets a
stable id from its heading anchor, with `-2`, `-3` suffixes for repeated headings.
Text before the first heading is addressable as `preamble`. Sections can also be
addressed by their numeric index.

```json
{
  "slug": "a-draft",
  "status": "draft",
  "editable": true,
  "sections": [
    { "id": "preamble", "index": 0, "level": 0, "heading": "", "body": "…", "characters": 42, "words": 7 },
    { "id": "background", "index": 1, "level": 2, "heading": "Background", "body": "…", "characters": 310, "words": 52 }
  ]
}
```

A section edit splices only that section's lines. Every other line of the article,
including its blank-line spacing, is preserved byte for byte.

## Article Fields

```jsonc
{
  "title": "…",
  "slug": "a-draft",
  "summary": "…",
  "bodyMarkdown": "…",
  "publishedAt": "2026-07-29T00:00:00Z",
  "status": "draft",              // read-only for API keys
  "aiAssisted": true,             // set by the API on every key write; not settable by a key
  "seo": {
    "metaTitle": null,            // falls back to the title
    "metaDescription": null,      // falls back to the summary
    "canonicalUrl": null,
    "keywords": [],
    "ogImageUrl": null,
    "noIndex": false
  },
  "heroImage": { "url": "/images/hero.png", "alt": "…", "caption": "" }
}
```

`PATCH` accepts `clearHeroImage: true` to remove the hero image.

## Body Formatting

`bodyMarkdown` is GitHub-flavoured Markdown. Two shapes get extra treatment when
the site renders them.

### Images

A key can upload a picture, place it, move it and re-describe it:

| Endpoint | Does |
| --- | --- |
| `GET /api/content/images` | list the shared library |
| `POST /api/content/images` | upload; the body is the file itself |
| `PATCH /api/content/images/{imageId}` | correct the alt stored on the library record |
| `GET /api/content/articles/{slug}/images` | where each picture sits in one article |
| `POST /api/content/articles/{slug}/images` | place one in a section |
| `PATCH /api/content/articles/{slug}/images/{imageRef}` | edit alt/caption/url, or move it |
| `DELETE /api/content/articles/{slug}/images/{imageRef}` | take it out of the body |

A key **cannot** delete from the library, and every body route refuses a
published article with `409` like any other body edit. Placement, movement and
removal all set `aiAssisted`.

Uploads take raw bytes with an optional `X-Image-Filename` and `X-Image-Alt`
header — not a multipart form. The format is sniffed from the bytes, so the
declared content type is irrelevant and SVG is refused. 8 MB per image, bounded
overall by `IMAGE_STORAGE_MAX_BYTES`.

Nothing resizes server-side. The browser editor downscales a paste to 1800px and
re-encodes it as WebP; an API client should do the equivalent before uploading,
or readers pay for the full-size original.

`GET /api/content/articles/{slug}/images` returns each image with a stable `id`
(the content digest for an uploaded picture), the `sectionId` it sits in, and
whether it is `standalone` — an image on its own line renders as a figure, one
inside a sentence stays inline and can be edited but not moved.

```markdown
![A revenue chart broken down by region](https://api.jackhales.com/api/images/70486bca…?w=1800&h=1013 "Revenue by region, FY2026")
```

The alt text is the description for someone who cannot see the image; only a
decorative image gets an empty `![]`. The optional title renders as a
`<figcaption>`. An image alone on its own line becomes a `<figure>`; inside a
sentence it stays inline. `heroImage.url` takes the same kind of URL.

Uploaded image URLs are content addressed — the id is a digest of the bytes, so
a URL never changes meaning, is cached for a year, and is safe to reuse across
articles. The `?w=…&h=…` pair is the stored size and lets the page reserve the
space before the bytes arrive; preserve it, or the article shifts as it loads.

### Tables

Plain GFM, no custom syntax:

```markdown
| Region | Revenue | Growth | Notes             |
| ------ | ------: | :----: | ----------------- |
| Sydney | 1,200   | 12%    | Strongest quarter |
| Perth  | 940     | 4%     | Flat on last year |
```

The renderer puts a table in a panel that scrolls inside its own box, so a wide
table never pushes the page sideways. `:---` is left, `:---:` centre, `---:`
right; a column whose every body value is a number is right-aligned
automatically, so declare an alignment on a numeric column only to override that.
The header row is required, a literal pipe in a cell is escaped as `\|`, and
cells take inline Markdown but not lists or paragraphs. GFM has no table caption
— use a short italic line underneath.

Pad the columns as shown. `/admin` has a visual table editor that writes padded
GFM, so matching it keeps a later round trip through that grid from producing a
whitespace-only diff.

## AI Attribution

Any write made with an API key sets `aiAssisted` to `true` on that article. The
site renders it as an AI-assisted badge linking to
[`/ai-assisted`](https://jackhales.com/ai-assisted), which explains that the
direction, research and conclusions are Jack's and that AI helped with drafting
and structuring.

A key cannot send `aiAssisted` in either direction — attempting it is a `422`.
Only the admin form can clear the flag, so assistance cannot quietly go
unrecorded.

## Type Definitions

- Python (authoritative): [`backend/app/schemas.py`](../backend/app/schemas.py)
- TypeScript for the site: [`frontend/lib/types.ts`](../frontend/lib/types.ts)
- TypeScript for external consumers: [`docs/content-api.d.ts`](./content-api.d.ts)
- Generated OpenAPI: `https://api.jackhales.com/openapi.json`

## Local Command

`scripts/jackhales-content` needs no dependencies beyond Python 3.9+. Write
commands print a JSON plan and only change anything with `--apply`.

```sh
scripts/jackhales-content list --status draft
scripts/jackhales-content read a-draft --raw
scripts/jackhales-content sections a-draft
scripts/jackhales-content new "A new piece" --summary "What it covers"
scripts/jackhales-content new "A new piece" --summary "What it covers" --apply
scripts/jackhales-content set a-draft --meta-title "…" --hero-image /images/hero.png --apply
scripts/jackhales-content section a-draft background --body-file section.md --apply
scripts/jackhales-content replace a-draft --find "old phrase" --with "new phrase" --apply
scripts/jackhales-content add-section a-draft --heading "Results" --after background --apply
```

Point it at a local backend with `JACKHALES_API_BASE_URL=http://localhost:8000/api`.

The same operations are available through Plumb as `scripts/plumb services
jackhales …`, which is the route to use when the key is held in Plumb's
credential store.
