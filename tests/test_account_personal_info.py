import re
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from main import USERS, _generate_jwt, app, initialize_auth_database
from _client import TestClient


class AccountPersonalInformationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "auth.db"
        self.auth_path_patch = patch("main.AUTH_DATABASE_PATH", self.database_path)
        self.auth_path_patch.start()
        self.addCleanup(self.auth_path_patch.stop)
        for phone in ("+8801999000001", "+8801999000002", "+8801999000003"):
            USERS.pop(phone, None)
        initialize_auth_database()
        self.phone = "+8801999000001"
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(self.temp_dir.cleanup)
        self._create_account(self.phone, "donor")
        self.client.cookies.set("access_token", _generate_jwt(self.phone, "donor"))

    def _create_account(self, phone, role, name="Ayesha Rahman"):
        now = 1_700_000_000
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """INSERT INTO auth_users (
                           phone, password_hash, created_at, updated_at, role, name,
                           email, district, address, status
                       ) VALUES (?, 'test-hash', ?, ?, ?, ?, 'ayesha@example.com',
                           'Dhaka', 'Road 1, Dhaka', 'active')""",
                    (phone, now, now, role, name),
                )
                if role == "donor":
                    connection.execute(
                        """INSERT INTO donor_profiles (
                               phone, name, email, blood_group, district, area, address,
                               updated_at
                           ) VALUES (?, ?, 'ayesha@example.com', 'A+', 'Dhaka',
                               'Dhanmondi', 'Road 1, Dhaka', ?)""",
                        (phone, name, now),
                    )

    def _request_phone_code(self, phone="+8801999000002"):
        sender = patch("main.send_sms_message")
        mocked_sender = sender.start()
        self.addCleanup(sender.stop)
        configured = patch("main.sms_is_configured", return_value=True)
        configured.start()
        self.addCleanup(configured.stop)
        response = self.client.post(
            "/api/v1/account/phone-update/request",
            json={"phone": phone},
        )
        return response, mocked_sender

    def test_account_profile_is_authenticated_and_returns_saved_values(self):
        response = self.client.get("/api/v1/account/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["phone"], self.phone)
        self.assertEqual(response.json()["profile"]["area"], "Dhanmondi")

        self.client.cookies.clear()
        unauthorized = self.client.get("/api/v1/account/profile")
        self.assertEqual(unauthorized.status_code, 401)

    def test_profile_update_validates_and_persists_account_and_donor_profile(self):
        invalid = self.client.put(
            "/api/v1/account/profile",
            json={
                "name": "Ayesha",
                "email": "not-an-email",
                "district": "Dhaka",
                "area": "Gulshan",
                "address": "Road 2, Dhaka",
            },
        )
        self.assertEqual(invalid.status_code, 422)

        response = self.client.put(
            "/api/v1/account/profile",
            json={
                "name": "Ayesha Karim",
                "email": "ayesha.karim@example.com",
                "district": "Chattogram",
                "area": "Agrabad",
                "address": "Road 2, Chattogram",
            },
        )
        self.assertEqual(response.status_code, 200)
        with closing(sqlite3.connect(self.database_path)) as connection:
            account = connection.execute(
                "SELECT name, email, district, address FROM auth_users WHERE phone = ?",
                (self.phone,),
            ).fetchone()
            donor = connection.execute(
                "SELECT name, email, district, area, address FROM donor_profiles WHERE phone = ?",
                (self.phone,),
            ).fetchone()
        self.assertEqual(account, ("Ayesha Karim", "ayesha.karim@example.com", "Chattogram", "Road 2, Chattogram"))
        self.assertEqual(
            donor,
            ("Ayesha Karim", "ayesha.karim@example.com", "Chattogram", "Agrabad", "Road 2, Chattogram"),
        )

    def test_phone_change_requires_valid_number_and_sms_configuration(self):
        invalid_phone = self.client.post(
            "/api/v1/account/phone-update/request",
            json={"phone": "+14155550123"},
        )
        self.assertEqual(invalid_phone.status_code, 422)

        with patch("main.sms_is_configured", return_value=False):
            unavailable = self.client.post(
                "/api/v1/account/phone-update/request",
                json={"phone": "+8801999000002"},
            )
        self.assertEqual(unavailable.status_code, 503)

    def test_phone_change_rejects_duplicate_number(self):
        duplicate_phone = "+8801999000003"
        self._create_account(duplicate_phone, "seeker")
        with patch("main.sms_is_configured", return_value=True):
            response = self.client.post(
                "/api/v1/account/phone-update/request",
                json={"phone": duplicate_phone},
            )
        self.assertEqual(response.status_code, 409)

    def test_phone_change_sms_failure_expires_the_challenge(self):
        with (
            patch("main.sms_is_configured", return_value=True),
            patch("main.send_sms_message", side_effect=OSError("gateway unavailable")),
        ):
            response = self.client.post(
                "/api/v1/account/phone-update/request",
                json={"phone": "+8801999000002"},
            )
        self.assertEqual(response.status_code, 503)
        with closing(sqlite3.connect(self.database_path)) as connection:
            challenge = connection.execute(
                "SELECT created_at, expires_at FROM account_phone_update_challenges"
            ).fetchone()
        self.assertEqual(challenge[0], challenge[1])

    def test_successful_phone_update_verifies_code_and_migrates_account_links(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """INSERT INTO donor_privacy_settings (phone, updated_at)
                       VALUES (?, 1700000000)""",
                    (self.phone,),
                )

        response, sender = self._request_phone_code()
        self.assertEqual(response.status_code, 202)
        message = sender.call_args.args[1]
        code = re.search(r"\b(\d{6})\b", message).group(1)
        verified = self.client.post(
            "/api/v1/account/phone-update/verify",
            json={"code": code},
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json()["phone"], "+8801999000002")
        self.assertIn("access_token", verified.cookies)

        with closing(sqlite3.connect(self.database_path)) as connection:
            phone = connection.execute("SELECT phone FROM auth_users").fetchone()[0]
            donor_phone = connection.execute("SELECT phone FROM donor_profiles").fetchone()[0]
            privacy_phone = connection.execute(
                "SELECT phone FROM donor_privacy_settings"
            ).fetchone()[0]
        self.assertEqual(phone, "+8801999000002")
        self.assertEqual(donor_phone, "+8801999000002")
        self.assertEqual(privacy_phone, "+8801999000002")

    def test_invalid_codes_are_rejected_and_attempts_are_limited(self):
        response, sender = self._request_phone_code()
        self.assertEqual(response.status_code, 202)
        correct_code = re.search(r"\b(\d{6})\b", sender.call_args.args[1]).group(1)
        invalid_code = "000000" if correct_code != "000000" else "000001"

        for _ in range(5):
            invalid = self.client.post(
                "/api/v1/account/phone-update/verify",
                json={"code": invalid_code},
            )
            self.assertEqual(invalid.status_code, 400)
        locked = self.client.post(
            "/api/v1/account/phone-update/verify",
            json={"code": correct_code},
        )
        self.assertEqual(locked.status_code, 400)
        with closing(sqlite3.connect(self.database_path)) as connection:
            current_phone = connection.execute("SELECT phone FROM auth_users").fetchone()[0]
        self.assertEqual(current_phone, self.phone)

    def test_expired_code_cannot_update_phone(self):
        response, sender = self._request_phone_code()
        self.assertEqual(response.status_code, 202)
        code = re.search(r"\b(\d{6})\b", sender.call_args.args[1]).group(1)
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE account_phone_update_challenges SET expires_at = 1"
                )
        expired = self.client.post(
            "/api/v1/account/phone-update/verify",
            json={"code": code},
        )
        self.assertEqual(expired.status_code, 400)
