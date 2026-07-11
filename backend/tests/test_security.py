import unittest

from app.security import adminEmail, hashPassword, normalizeEmail, verifyPassword


class PasswordSecurityTest(unittest.TestCase):
    def testPasswordHashUsesUniqueSaltAndVerifies(self) -> None:
        password = "a-long-and-private-password"

        firstHash = hashPassword(password)
        secondHash = hashPassword(password)

        self.assertNotEqual(firstHash, secondHash)
        self.assertTrue(firstHash.startswith("scrypt$"))
        self.assertTrue(verifyPassword(password, firstHash))
        self.assertFalse(verifyPassword("not-the-password", firstHash))

    def testMalformedOrUnexpectedHashesAreRejected(self) -> None:
        self.assertFalse(verifyPassword("anything", ""))
        self.assertFalse(verifyPassword("anything", "pbkdf2$1$2$3$4$5"))
        self.assertFalse(verifyPassword("anything", "scrypt$999$8$1$00$00"))

    def testEmailNormalizationMatchesTheOnlyAdminIdentity(self) -> None:
        self.assertEqual(normalizeEmail("  ME@JackHales.com "), adminEmail)


if __name__ == "__main__":
    unittest.main()
