import unittest
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

import main
from main import app, _generate_jwt


class DonorDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path_patch = patch.object(
            main, "AUTH_DATABASE_PATH", Path(self.temp_dir.name) / "auth.db"
        )
        self.database_path_patch.start()
        main.initialize_auth_database()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_unauthorized_dashboard_redirects_to_login(self):
        response = self.client.get("/donor/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login?next=/donor/dashboard", response.headers.get("location", ""))

    def test_preview_mode_allows_dashboard_view(self):
        response = self.client.get("/donor/dashboard?preview=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Donor Personal Dashboard", response.text)

    def test_authenticated_donor_can_access_dashboard(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/donor/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify all 9 required sidebar items
        self.assertIn("Donor Availability", html)
        self.assertIn("Donor Profile & Medical Info", html)
        self.assertIn("Donation History", html)
        self.assertIn("Matched Blood Requests", html)
        self.assertIn("Accept & Decline Flow", html)
        self.assertIn("Request Details & Directions", html)
        self.assertIn("Donor In-App Chat", html)
        self.assertIn("Donor Reviews", html)
        self.assertIn("Settings & Preferences", html)

    def test_donor_availability_api(self):
        token = _generate_jwt("+8801712345678", "donor")
        cookies = {"access_token": token}
        initial = self.client.get("/api/v1/donor/availability", cookies=cookies)
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()["is_available"])

        response = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": True, "radius_km": 15, "preferred_zones": ["Dhanmondi"]},
            cookies=cookies,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["is_available"])
        self.assertEqual(data["radius_km"], 15)

        saved = self.client.get("/api/v1/donor/availability", cookies=cookies)
        self.assertTrue(saved.json()["is_available"])
        self.assertEqual(saved.json()["preferred_zones"], ["Dhanmondi"])
        dashboard = self.client.get("/donor/dashboard", cookies=cookies)
        self.assertIn('id="availability-toggle" role="switch" checked', dashboard.text)
        self.assertIn("Available for requests", dashboard.text)

        disabled = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": False},
            cookies=cookies,
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.json()["radius_km"], 15)
        self.assertEqual(disabled.json()["preferred_zones"], ["Dhanmondi"])
        self.assertFalse(self.client.get("/api/v1/donor/availability", cookies=cookies).json()["is_available"])

    def test_donor_availability_requires_authenticated_donor(self):
        unauthorized = self.client.post(
            "/api/v1/donor/availability", json={"is_available": True}
        )
        self.assertEqual(unauthorized.status_code, 401)

        seeker_token = _generate_jwt("+8801723456789", "seeker")
        forbidden = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": True},
            cookies={"access_token": seeker_token},
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_temporary_and_scheduled_unavailability_and_emergency_preference(self):
        cookies = {"access_token": _generate_jwt("+8801712345678", "donor")}
        today = datetime.now(timezone.utc).date()
        temporary_until = (today + timedelta(days=2)).isoformat()
        temporary = self.client.post(
            "/api/v1/donor/availability",
            json={
                "is_available": True,
                "unavailability_mode": "temporary",
                "temporary_unavailable_until": temporary_until,
                "emergency_contact_preference": "phone_call",
            },
            cookies=cookies,
        )
        self.assertEqual(temporary.status_code, 200)
        self.assertFalse(temporary.json()["is_matchable"])
        self.assertEqual(temporary.json()["matching_status"], "Temporarily unavailable")
        self.assertEqual(temporary.json()["emergency_contact_preference"], "phone_call")

        scheduled = self.client.post(
            "/api/v1/donor/availability",
            json={
                "is_available": True,
                "unavailability_mode": "scheduled",
                "scheduled_unavailable_start": today.isoformat(),
                "scheduled_unavailable_end": (today + timedelta(days=1)).isoformat(),
                "emergency_contact_preference": "both",
            },
            cookies=cookies,
        )
        self.assertEqual(scheduled.status_code, 200)
        self.assertFalse(scheduled.json()["is_matchable"])
        self.assertEqual(scheduled.json()["matching_status"], "Unavailable by schedule")
        self.assertEqual(scheduled.json()["emergency_contact_preference"], "both")

        future_start = (today + timedelta(days=3)).isoformat()
        future_schedule = self.client.post(
            "/api/v1/donor/availability",
            json={
                "is_available": True,
                "unavailability_mode": "scheduled",
                "scheduled_unavailable_start": future_start,
                "scheduled_unavailable_end": (today + timedelta(days=4)).isoformat(),
            },
            cookies=cookies,
        )
        self.assertTrue(future_schedule.json()["is_matchable"])
        self.assertEqual(future_schedule.json()["emergency_contact_preference"], "both")

        saved = self.client.get("/api/v1/donor/availability", cookies=cookies)
        self.assertEqual(saved.json()["scheduled_unavailable_start"], future_start)
        self.assertEqual(saved.json()["emergency_contact_preference"], "both")

    def test_invalid_unavailability_windows_are_rejected(self):
        cookies = {"access_token": _generate_jwt("+8801712345678", "donor")}
        today = datetime.now(timezone.utc).date()
        response = self.client.post(
            "/api/v1/donor/availability",
            json={
                "is_available": True,
                "unavailability_mode": "scheduled",
                "scheduled_unavailable_start": (today + timedelta(days=2)).isoformat(),
                "scheduled_unavailable_end": (today + timedelta(days=1)).isoformat(),
            },
            cookies=cookies,
        )
        self.assertEqual(response.status_code, 422)

    def test_existing_availability_records_survive_schema_migration(self):
        connection = sqlite3.connect(main.AUTH_DATABASE_PATH)
        try:
            with connection:
                connection.execute("DROP TABLE donor_availability")
                connection.execute(
                    """CREATE TABLE donor_availability (
                       donor_phone TEXT PRIMARY KEY,
                       is_available INTEGER NOT NULL DEFAULT 0,
                       radius_km INTEGER NOT NULL DEFAULT 10,
                       preferred_zones TEXT NOT NULL DEFAULT '[]',
                       updated_at TEXT NOT NULL)"""
                )
                connection.execute(
                    """INSERT INTO donor_availability
                       (donor_phone, is_available, radius_km, preferred_zones, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    ("+8801712345678", 1, 20, '["Mirpur"]', "2026-10-01T00:00:00+00:00"),
                )
        finally:
            connection.close()

        main.initialize_auth_database()
        response = self.client.get(
            "/api/v1/donor/availability",
            cookies={"access_token": _generate_jwt("+8801712345678", "donor")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_available"])
        self.assertEqual(response.json()["radius_km"], 20)
        self.assertEqual(response.json()["preferred_zones"], ["Mirpur"])
        self.assertEqual(response.json()["emergency_contact_preference"], "sms")

    def test_donor_respond_request_api(self):
        response = self.client.post(
            "/api/v1/donor/requests/req-001/respond",
            json={"action": "accept", "eta": "30 mins", "note": "On the way"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "accept")

    def test_logout_redirects_to_login(self):
        response = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/login")

    def test_logged_in_user_visiting_home_shows_dashboard_and_logout(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.text)
        self.assertIn("Logout", response.text)

    def test_auth_status_api(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/api/v1/auth/status", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_authenticated"])
        self.assertEqual(data["role"], "donor")

