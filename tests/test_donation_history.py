import sqlite3
import unittest
import uuid
from contextlib import closing
from datetime import date

from fastapi.testclient import TestClient

from main import (
    AUTH_DATABASE_PATH,
    DATABASE_PATH,
    _current_donor_date,
    _generate_jwt,
    app,
    initialize_urgent_database,
)


class DonationHistoryTests(unittest.TestCase):
    def setUp(self):
        initialize_urgent_database()
        self.client = TestClient(app)
        self.donor_phone = f"+88017{uuid.uuid4().int % 10**9:09d}"
        self.other_donor_phone = f"+88017{uuid.uuid4().int % 10**9:09d}"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def tearDown(self):
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.executemany(
                    "DELETE FROM donation_history WHERE donor_phone = ?",
                    [(self.donor_phone,), (self.other_donor_phone,)],
                )
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.execute("DELETE FROM donor_profiles WHERE phone = ?", (self.donor_phone,))

    def test_donation_history_requires_donor_authentication(self):
        endpoint = "/api/v1/donor/donation-history"
        self.assertEqual(self.client.get(endpoint).status_code, 401)

        seeker_token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.get(endpoint, cookies={"access_token": seeker_token})
        self.assertEqual(response.status_code, 403)

    def test_donation_history_is_private_and_newest_first(self):
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.executemany(
                    """INSERT INTO donation_history
                       (donor_phone, donation_date, donation_type, hospital_name, district, area)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            self.donor_phone,
                            "2025-04-12",
                            "Platelets",
                            "Square Hospital",
                            "Dhaka",
                            "Panthapath",
                        ),
                        (
                            self.donor_phone,
                            "2024-11-03",
                            "Whole Blood",
                            "Dhaka Medical College",
                            "Dhaka",
                            "Shahbagh",
                        ),
                        (
                            self.other_donor_phone,
                            "2026-01-14",
                            "Whole Blood",
                            "Private donor record",
                            "Dhaka",
                            "Dhanmondi",
                        ),
                    ],
                )

        response = self.client.get(
            "/api/v1/donor/donation-history",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(
            [record["donation_date"] for record in data["donations"]],
            ["2025-04-12", "2024-11-03"],
        )
        self.assertEqual(data["donations"][0]["hospital_name"], "Square Hospital")
        self.assertEqual(data["donations"][0]["donation_type"], "Platelets")
        self.assertEqual(data["last_donated"], "2025-04-12")
        self.assertEqual(data["next_eligible_date"], "2025-06-07")
        self.assertEqual(
            data["days_until_eligible"],
            max(0, (date.fromisoformat("2025-06-07") - _current_donor_date()).days),
        )
        self.assertTrue(
            all(record["hospital_name"] != "Private donor record" for record in data["donations"])
        )

    def test_last_donated_uses_completed_history_not_profile_default(self):
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """INSERT INTO donor_profiles (
                           phone, name, blood_group, district, area, address, last_donation, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self.donor_phone,
                        "History Test Donor",
                        "A+",
                        "Dhaka",
                        "Dhanmondi",
                        "Test address",
                        "2026-01-14",
                        0,
                    ),
                )

        response = self.client.get(
            "/api/v1/donor/donation-history",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["donations"], [])
        self.assertIsNone(data["last_donated"])
        self.assertIsNone(data["next_eligible_date"])
        self.assertIsNone(data["days_until_eligible"])

    def test_dashboard_renders_donation_history_state(self):
        response = self.client.get(
            "/donor/dashboard",
            cookies={"access_token": self.donor_token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="section-history"', response.text)
        self.assertIn('id="donation-history-list"', response.text)
        self.assertIn('id="donation-total-count"', response.text)
        self.assertIn('id="donation-lives-saved"', response.text)
        self.assertIn('id="donation-last-date"', response.text)
        self.assertIn('id="donation-eligibility"', response.text)
        self.assertIn("completed donations", response.text)
