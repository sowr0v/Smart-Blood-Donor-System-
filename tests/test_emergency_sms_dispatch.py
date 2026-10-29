import json
import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from admin_portal import initialize_admin_and_notification_database
from main import AUTH_DATABASE_PATH, DATABASE_PATH, _generate_jwt, app, initialize_auth_database


class EmergencySmsDispatchTests(unittest.TestCase):
    eligible_phone = "+8801999901001"
    universal_donor_phone = "+8801999901002"
    unavailable_phone = "+8801999901003"
    opted_out_phone = "+8801999901004"
    wrong_location_phone = "+8801999901005"

    def setUp(self):
        self.client = TestClient(app)
        initialize_auth_database()
        initialize_admin_and_notification_database()
        self.admin_cookies = {
            "access_token": _generate_jwt("+8801745678901", "admin")
        }
        self.donor_phones = (
            self.eligible_phone,
            self.universal_donor_phone,
            self.unavailable_phone,
            self.opted_out_phone,
            self.wrong_location_phone,
        )
        self.request_id = self._create_emergency_request()
        self._create_donor(self.eligible_phone, "A+", "Dhaka", True)
        self._create_donor(self.universal_donor_phone, "O-", "Dhaka", True)
        self._create_donor(self.unavailable_phone, "A+", "Dhaka", False)
        self._create_donor(self.opted_out_phone, "A+", "Dhaka", True, sms_alerts=False)
        self._create_donor(self.wrong_location_phone, "A+", "Sylhet", True)

    def tearDown(self):
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.executemany(
                    "DELETE FROM sms_dispatch_logs WHERE recipient_phone = ?",
                    [(phone,) for phone in self.donor_phones],
                )
                if self.request_id:
                    connection.execute(
                        "DELETE FROM blood_requests WHERE id = ?",
                        (self.request_id,),
                    )
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                for table in ("donor_settings", "donor_privacy_settings", "donor_profiles", "auth_users"):
                    connection.executemany(
                        f"DELETE FROM {table} WHERE phone = ?",
                        [(phone,) for phone in self.donor_phones],
                    )
        self.client.close()

    @staticmethod
    def _create_donor(
        phone: str,
        blood_group: str,
        district: str,
        is_available: bool,
        sms_alerts: bool = True,
    ) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """INSERT OR REPLACE INTO auth_users
                       (phone, password_hash, role, name, blood_group, district,
                        status, created_at, updated_at)
                       VALUES (?, 'test-hash', 'donor', 'SMS Test Donor', ?, ?,
                               'active', ?, ?)""",
                    (phone, blood_group, district, now, now),
                )
                connection.execute(
                    """INSERT OR REPLACE INTO donor_profiles
                       (phone, name, blood_group, district, area, address,
                        fitness_status, preferred_donation_types, is_available, updated_at)
                       VALUES (?, 'SMS Test Donor', ?, ?, 'Central', 'Test address',
                               'Eligible', 'Whole Blood', ?, ?)""",
                    (phone, blood_group, district, int(is_available), now),
                )
                if not sms_alerts:
                    connection.execute(
                        """INSERT OR REPLACE INTO donor_settings
                           (phone, settings_json, updated_at) VALUES (?, ?, ?)""",
                        (phone, json.dumps({"sms_alerts": False}), now),
                    )

    @staticmethod
    def _create_emergency_request() -> int:
        now = datetime.now(timezone.utc)
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                cursor = connection.execute(
                    """INSERT INTO blood_requests (
                           blood_group, hospital_name, district, area, expires_at,
                           contact_phone, is_emergency, status, moderation_status
                       ) VALUES ('A+', 'Emergency Test Hospital', 'Dhaka', 'Central',
                                 ?, '+8801888800000', 1, 'Active', 'approved')""",
                    ((now + timedelta(hours=2)).isoformat(),),
                )
                return int(cursor.lastrowid)

    def _payload(self, **overrides):
        payload = {
            "blood_group": "A+",
            "hospital_name": "Emergency Test Hospital",
            "district": "Dhaka",
            "area": "Central",
            "request_id": self.request_id,
            "is_critical": True,
        }
        payload.update(overrides)
        return payload

    def test_only_active_opted_in_matching_donors_receive_sms_and_duplicates_are_skipped(self):
        with patch("main.sms_is_configured", return_value=True), patch(
            "main.send_sms_message"
        ) as send_sms:
            response = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["sent_count"], 2)
            self.assertEqual(data["failed_count"], 0)
            self.assertEqual(
                {call.args[0] for call in send_sms.call_args_list},
                {self.eligible_phone, self.universal_donor_phone},
            )
            self.assertNotIn(self.eligible_phone, json.dumps(data))
            self.assertTrue(all(item["status"] == "sent" for item in data["dispatches"]))

            repeated = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(repeated.json()["status"], "duplicate")
            self.assertEqual(repeated.json()["skipped_duplicate_count"], 2)
            self.assertEqual(send_sms.call_count, 2)

    def test_requested_recipients_cannot_bypass_eligibility_filters(self):
        with patch("main.sms_is_configured", return_value=True), patch(
            "main.send_sms_message"
        ) as send_sms:
            response = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(
                    recipients=[self.eligible_phone, self.unavailable_phone, "+8801888800001"]
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sent_count"], 1)
        send_sms.assert_called_once()
        self.assertEqual(send_sms.call_args.args[0], self.eligible_phone)

    def test_noncritical_and_mismatched_or_inactive_requests_are_rejected(self):
        noncritical = self.client.post(
            "/api/v1/notifications/sms/dispatch",
            cookies=self.admin_cookies,
            json=self._payload(is_critical=False),
        )
        self.assertEqual(noncritical.status_code, 422)

        mismatched = self.client.post(
            "/api/v1/notifications/sms/dispatch",
            cookies=self.admin_cookies,
            json=self._payload(blood_group="B+"),
        )
        self.assertEqual(mismatched.status_code, 422)

        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    "UPDATE blood_requests SET status = 'Closed' WHERE id = ?",
                    (self.request_id,),
                )
        inactive = self.client.post(
            "/api/v1/notifications/sms/dispatch",
            cookies=self.admin_cookies,
            json=self._payload(),
        )
        self.assertEqual(inactive.status_code, 409)

    def test_gateway_failure_is_recorded_and_failed_alert_can_be_retried(self):
        with patch("main.sms_is_configured", return_value=True), patch(
            "main.send_sms_message", side_effect=RuntimeError("provider unavailable")
        ) as send_sms:
            failed = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["status"], "failed")
        self.assertEqual(failed.json()["failed_count"], 2)
        self.assertTrue(
            all(item["failure_reason"] for item in failed.json()["dispatches"])
        )

        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            rows = connection.execute(
                """SELECT status, failure_reason FROM sms_dispatch_logs
                   WHERE recipient_phone IN (?, ?)""",
                (self.eligible_phone, self.universal_donor_phone),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row[0] == "failed" and row[1] for row in rows))

        with patch("main.sms_is_configured", return_value=True), patch(
            "main.send_sms_message"
        ) as retry:
            retried = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(retried.json()["sent_count"], 2)
        self.assertEqual(retry.call_count, 2)
        self.assertEqual(send_sms.call_count, 2)

    def test_partial_gateway_failure_reports_each_delivery_status(self):
        with patch("main.sms_is_configured", return_value=True), patch(
            "main.send_sms_message", side_effect=[None, RuntimeError("provider unavailable")]
        ):
            response = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "partial_failure")
        self.assertEqual(data["sent_count"], 1)
        self.assertEqual(data["failed_count"], 1)
        self.assertEqual(
            {item["status"] for item in data["dispatches"]},
            {"sent", "failed"},
        )

    def test_missing_gateway_records_failed_delivery_without_claiming_success(self):
        with patch("main.sms_is_configured", return_value=False), patch(
            "main.send_sms_message"
        ) as send_sms:
            response = self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["sent_count"], 0)
        self.assertEqual(response.json()["failed_count"], 2)
        send_sms.assert_not_called()

    def test_dispatch_and_logs_require_admin_and_logs_mask_recipient_phone(self):
        unauthorized = self.client.post(
            "/api/v1/notifications/sms/dispatch",
            json=self._payload(),
        )
        self.assertEqual(unauthorized.status_code, 401)
        non_admin = self.client.get(
            "/api/v1/notifications/sms/logs",
            cookies={"access_token": _generate_jwt(self.eligible_phone, "donor")},
        )
        self.assertEqual(non_admin.status_code, 403)

        with patch("main.sms_is_configured", return_value=False):
            self.client.post(
                "/api/v1/notifications/sms/dispatch",
                cookies=self.admin_cookies,
                json=self._payload(),
            )
        logs = self.client.get(
            "/api/v1/notifications/sms/logs",
            cookies=self.admin_cookies,
        )
        self.assertEqual(logs.status_code, 200)
        self.assertNotIn(self.eligible_phone, json.dumps(logs.json()))
        self.assertIn("••••1001", json.dumps(logs.json(), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
