import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import USERS, _generate_jwt, app, initialize_auth_database


class CommunicationPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "auth.db"
        self.database_patch = patch("main.AUTH_DATABASE_PATH", self.database_path)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        initialize_auth_database()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(self.temp_dir.cleanup)
        self.donor_phone = "+8801999000091"
        self.seeker_phone = "+8801999000092"
        USERS.pop(self.donor_phone, None)
        USERS.pop(self.seeker_phone, None)

    def _login_as(self, phone, role):
        self.client.cookies.set("access_token", _generate_jwt(phone, role))

    def _payload(self):
        return {
            "channels": {
                "in_app_chat": False,
                "sms": False,
                "phone_call": True,
                "whatsapp": True,
                "push_notification": False,
            },
            "alert_types": {
                "critical_emergency": False,
                "matching_requests": False,
                "chat_messages": True,
                "donation_reminders": False,
                "account_updates": True,
            },
            "frequency": "daily",
        }

    def test_preferences_require_authenticated_donor_or_seeker(self):
        anonymous = self.client.get("/api/v1/account/communication-preferences")
        self.assertEqual(anonymous.status_code, 401)

        self._login_as("+8801745678901", "admin")
        admin = self.client.get("/api/v1/account/communication-preferences")
        self.assertEqual(admin.status_code, 403)

    def test_donor_preferences_persist_and_critical_alerts_cannot_be_disabled(self):
        self._login_as(self.donor_phone, "donor")
        initial = self.client.get("/api/v1/account/communication-preferences")
        self.assertEqual(initial.status_code, 200)
        self.assertTrue(initial.json()["preferences"]["alert_types"]["critical_emergency"])

        saved = self.client.put(
            "/api/v1/account/communication-preferences",
            json=self._payload(),
        )
        self.assertEqual(saved.status_code, 200)
        preferences = saved.json()["preferences"]
        self.assertTrue(preferences["alert_types"]["critical_emergency"])
        self.assertEqual(preferences["critical_frequency"], "immediate")
        self.assertEqual(preferences["frequency"], "daily")
        self.assertFalse(preferences["channels"]["phone_call"])
        self.assertFalse(preferences["channels"]["whatsapp"])
        self.assertCountEqual(
            saved.json()["privacy_restrictions"],
            ["phone_call", "whatsapp"],
        )

        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """SELECT role, preferences_json FROM communication_preferences
                   WHERE phone = ?""",
                (self.donor_phone,),
            ).fetchone()
        self.assertEqual(row[0], "donor")
        persisted = json.loads(row[1])
        self.assertTrue(persisted["alert_types"]["critical_emergency"])
        self.assertFalse(persisted["channels"]["sms"])

        fetched = self.client.get("/api/v1/account/communication-preferences")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["preferences"]["frequency"], "daily")

    def test_donor_call_and_whatsapp_preferences_follow_contact_consent(self):
        self._login_as(self.donor_phone, "donor")
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """INSERT INTO donor_privacy_settings (
                           phone, share_direct_contact, phone_visibility, updated_at
                       ) VALUES (?, 1, 'public', 1)""",
                    (self.donor_phone,),
                )
        allowed = self.client.put(
            "/api/v1/account/communication-preferences",
            json=self._payload(),
        )
        self.assertEqual(allowed.status_code, 200)
        channels = allowed.json()["preferences"]["channels"]
        self.assertTrue(channels["phone_call"])
        self.assertTrue(channels["whatsapp"])
        self.assertEqual(allowed.json()["privacy_restrictions"], [])

    def test_seeker_preferences_persist_all_channels_and_alert_types(self):
        self._login_as(self.seeker_phone, "seeker")
        saved = self.client.put(
            "/api/v1/account/communication-preferences",
            json=self._payload(),
        )
        self.assertEqual(saved.status_code, 200)
        preferences = saved.json()["preferences"]
        self.assertEqual(preferences["channels"], self._payload()["channels"])
        self.assertTrue(preferences["alert_types"]["critical_emergency"])
        self.assertFalse(preferences["alert_types"]["matching_requests"])

        with closing(sqlite3.connect(self.database_path)) as connection:
            stored = connection.execute(
                "SELECT role FROM communication_preferences WHERE phone = ?",
                (self.seeker_phone,),
            ).fetchone()
        self.assertEqual(stored[0], "seeker")

    def test_preferences_are_isolated_between_roles_sharing_a_phone(self):
        shared_phone = "+8801999000093"
        self.addCleanup(USERS.pop, shared_phone, None)
        self._login_as(shared_phone, "donor")
        donor_payload = self._payload()
        donor_payload["channels"]["sms"] = False
        donor_saved = self.client.put(
            "/api/v1/account/communication-preferences",
            json=donor_payload,
        )
        self.assertEqual(donor_saved.status_code, 200)

        USERS.pop(shared_phone, None)
        self._login_as(shared_phone, "seeker")
        seeker_initial = self.client.get("/api/v1/account/communication-preferences")
        self.assertTrue(seeker_initial.json()["preferences"]["channels"]["sms"])
        seeker_payload = self._payload()
        seeker_payload["channels"]["sms"] = True
        seeker_saved = self.client.put(
            "/api/v1/account/communication-preferences",
            json=seeker_payload,
        )
        self.assertEqual(seeker_saved.status_code, 200)

        USERS.pop(shared_phone, None)
        self._login_as(shared_phone, "donor")
        donor_fetched = self.client.get("/api/v1/account/communication-preferences")
        self.assertFalse(donor_fetched.json()["preferences"]["channels"]["sms"])
        with closing(sqlite3.connect(self.database_path)) as connection:
            roles = connection.execute(
                "SELECT role FROM communication_preferences WHERE phone = ? ORDER BY role",
                (shared_phone,),
            ).fetchall()
        self.assertEqual([row[0] for row in roles], ["donor", "seeker"])

    def test_existing_phone_key_schema_migrates_without_losing_preferences(self):
        shared_phone = "+8801999000094"
        self.addCleanup(USERS.pop, shared_phone, None)
        existing_preferences = self._payload()
        existing_preferences["channels"]["sms"] = False

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute("DROP TABLE communication_preferences")
                connection.execute(
                    """CREATE TABLE communication_preferences (
                           phone TEXT PRIMARY KEY,
                           role TEXT NOT NULL CHECK (role IN ('donor', 'seeker')),
                           preferences_json TEXT NOT NULL,
                           updated_at INTEGER NOT NULL
                       )"""
                )
                connection.execute(
                    """INSERT INTO communication_preferences
                       (phone, role, preferences_json, updated_at)
                       VALUES (?, 'donor', ?, 1)""",
                    (shared_phone, json.dumps(existing_preferences)),
                )

        self._login_as(shared_phone, "donor")
        loaded = self.client.get("/api/v1/account/communication-preferences")
        self.assertEqual(loaded.status_code, 200)
        self.assertFalse(loaded.json()["preferences"]["channels"]["sms"])

        USERS.pop(shared_phone, None)
        self._login_as(shared_phone, "seeker")
        saved = self.client.put(
            "/api/v1/account/communication-preferences",
            json=self._payload(),
        )
        self.assertEqual(saved.status_code, 200)

        with closing(sqlite3.connect(self.database_path)) as connection:
            primary_key = [
                row[1]
                for row in sorted(
                    (row for row in connection.execute(
                        "PRAGMA table_info(communication_preferences)"
                    ).fetchall() if row[5]),
                    key=lambda row: row[5],
                )
            ]
            roles = connection.execute(
                "SELECT role FROM communication_preferences WHERE phone = ? ORDER BY role",
                (shared_phone,),
            ).fetchall()
        self.assertEqual(primary_key, ["phone", "role"])
        self.assertEqual([row[0] for row in roles], ["donor", "seeker"])

    def test_unsupported_alert_frequency_is_rejected(self):
        self._login_as(self.seeker_phone, "seeker")
        invalid = self._payload()
        invalid["frequency"] = "never"
        response = self.client.put(
            "/api/v1/account/communication-preferences",
            json=invalid,
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
