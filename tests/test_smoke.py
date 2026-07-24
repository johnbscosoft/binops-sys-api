import unittest

from pydantic import ValidationError

from app.features.authentication_settings.schema import AuthenticationSettingsUpdate
from app.features.users.two_factor import generate_otp, hash_otp, mask_email, verify_otp
from app.main import health_check


class HealthCheckTests(unittest.TestCase):
    def test_health_check_response(self) -> None:
        response = health_check()

        self.assertTrue(response["status"])
        self.assertEqual(response["data"][0]["status"], "ok")


class TwoFactorTests(unittest.TestCase):
    def test_generated_otp_is_six_digits(self) -> None:
        otp = generate_otp()

        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_otp_hash_verification(self) -> None:
        challenge_id = "challenge-id"
        otp_hash = hash_otp(challenge_id, "123456")

        self.assertTrue(verify_otp(challenge_id, "123456", otp_hash))
        self.assertFalse(verify_otp(challenge_id, "654321", otp_hash))

    def test_email_is_masked(self) -> None:
        masked = mask_email("john@example.com")

        self.assertNotIn("john@", masked)
        self.assertTrue(masked.endswith("@example.com"))

    def test_enabled_otp_requires_a_delivery_channel(self) -> None:
        with self.assertRaises(ValidationError):
            AuthenticationSettingsUpdate(
                otp_enabled=True,
                email_otp_enabled=False,
                sms_otp_enabled=False,
            )


if __name__ == "__main__":
    unittest.main()
