import sqlite3
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from main import DATABASE_PATH, _generate_jwt, app


class DonorHistoryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.donor_phone = f"+88017{uuid.uuid4().int % 10**9:09d}"
        self.other_donor_phone = f"+88017{uuid.uuid4().int % 10**9:09d}"
        self.request_id = None
        self.addCleanup(self._remove_test_history)

    def _remove_test_history(self):
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                "DELETE FROM donor_donation_history WHERE donor_phone IN (?, ?)",
                (self.donor_phone, self.other_donor_phone),
            )
            if self.request_id is not None:
                connection.execute("DELETE FROM blood_requests WHERE id = ?", (self.request_id,))

    def test_authenticated_donor_gets_only_own_history_in_reverse_chronological_order(self):
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.execute(
                """INSERT INTO blood_requests (
                       blood_group, hospital_name, district, area, distance_km,
                       expires_at, contact_phone, is_emergency
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    "A+",
                    "History Test Hospital",
                    "Dhaka",
                    "Dhanmondi",
                    2.0,
                    (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "+8801700000099",
                ),
            )
            self.request_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO donor_donation_history
                   (donor_phone, request_id, donated_at, donation_type, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (self.donor_phone, self.request_id, "2026-01-14", "Whole Blood", "Verified"),
                    (self.donor_phone, None, "2026-05-20", "Platelets", ""),
                    (self.other_donor_phone, self.request_id, "2026-06-01", "Plasma", "Private"),
                ],
            )

        response = self.client.get(
            "/api/v1/donor/donations",
            cookies={"access_token": _generate_jwt(self.donor_phone, "donor")},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(
            [donation["donated_at"] for donation in data["donations"]],
            ["2026-05-20", "2026-01-14"],
        )
        self.assertEqual(data["donations"][1]["hospital_name"], "History Test Hospital")
        self.assertEqual(data["donations"][1]["area"], "Dhanmondi")
        self.assertNotIn("Private", str(data["donations"]))

    def test_donation_history_requires_an_authenticated_donor(self):
        anonymous_response = self.client.get("/api/v1/donor/donations")
        self.assertEqual(anonymous_response.status_code, 401)

        seeker_response = self.client.get(
            "/api/v1/donor/donations",
            cookies={"access_token": _generate_jwt(self.other_donor_phone, "seeker")},
        )
        self.assertEqual(seeker_response.status_code, 403)

    def test_donor_dashboard_renders_history_screen(self):
        response = self.client.get(
            "/donor/dashboard",
            cookies={"access_token": _generate_jwt(self.donor_phone, "donor")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="donationHistoryList"', response.text)
        self.assertIn('id="donationHistoryCount"', response.text)
