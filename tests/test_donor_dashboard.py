import unittest
from contextlib import closing
from datetime import timedelta
from fastapi.testclient import TestClient

from main import (
    app,
    _connection,
    _current_donor_date,
    _generate_jwt,
    initialize_auth_database,
)


class DonorDashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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
        self.assertIn('id="section-availability"', html)
        self.assertIn('id="donorAvailabilityToggle"', html)
        self.assertIn('id="availabilityStatusText"', html)
        self.assertIn('id="unavailabilityScheduleForm"', html)
        self.assertIn('id="unavailabilityStartDate"', html)
        self.assertIn('id="unavailabilityEndDate"', html)
        self.assertNotIn("Whole-blood estimate", html)
        self.assertNotIn('id="nextEligibleDate"', html)
        self.assertIn("Donor Profile & Medical Info", html)
        self.assertIn("Donation History", html)
        self.assertIn("Matched Blood Requests", html)
        self.assertIn("Accept & Decline Flow", html)
        self.assertIn("Request Details & Directions", html)
        self.assertIn('id="donor-request-details-content"', html)
        self.assertIn('id="donor-request-details-select"', html)
        self.assertIn('id="donor-request-directions"', html)
        self.assertIn('id="section-reviews"', html)
        self.assertIn('id="donor-review-list"', html)
        self.assertIn('id="donor-review-rating-filter"', html)
        self.assertIn("sample reviews", html)
        self.assertIn("Donor In-App Chat", html)
        self.assertIn("Donor Reviews", html)
        self.assertIn("Settings & Preferences", html)

    def test_donor_in_app_chat_rendered(self):
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/donor/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="section-chat"', html)
        self.assertIn('chat-module-shell', html)
        self.assertIn('chat-threads-sidebar', html)
        self.assertIn('Square Hospital - Blood Desk', html)
        self.assertIn('Dhaka Medical Desk', html)
        self.assertIn('chatMessages', html)
        self.assertIn('chatInput', html)
        self.assertIn('sendChatBtn', html)
        self.assertIn('sidebarChatBadge', html)
        self.assertIn('chatCategoryTabs', html)
        self.assertIn('chatRequestBanner', html)
        self.assertIn('quickReplyBar', html)
        self.assertIn('typingIndicator', html)

    def test_donor_chat_threads_api(self):
        response = self.client.get("/api/v1/donor/chat/threads")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["threads"]), 4)
        thread_ids = [t["id"] for t in data["threads"]]
        self.assertIn("thread-square", thread_ids)
        self.assertIn("thread-dmc", thread_ids)

        # Test filtering by category
        hospital_res = self.client.get("/api/v1/donor/chat/threads?category=hospital")
        self.assertEqual(hospital_res.status_code, 200)
        hosp_data = hospital_res.json()
        for t in hosp_data["threads"]:
            self.assertEqual(t["category"], "hospital")

    def test_donor_chat_messages_api(self):
        response = self.client.get("/api/v1/donor/chat/thread-square/messages")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["thread_id"], "thread-square")
        self.assertIsInstance(data["messages"], list)
        self.assertGreaterEqual(len(data["messages"]), 1)

    def test_donor_chat_send_and_read_api(self):
        # Test sending message
        send_res = self.client.post(
            "/api/v1/donor/chat/thread-square/send",
            json={"text": "I am on my way to Square Hospital", "sender": "you"},
        )
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.json()
        self.assertEqual(send_data["status"], "success")
        self.assertEqual(send_data["sent"]["text"], "I am on my way to Square Hospital")
        self.assertIn("reply", send_data)

        # Test marking thread as read
        read_res = self.client.post("/api/v1/donor/chat/thread-square/read")
        self.assertEqual(read_res.status_code, 200)
        read_data = read_res.json()
        self.assertEqual(read_data["status"], "success")
        self.assertEqual(read_data["unread_count"], 0)

    def test_donor_availability_api(self):
        initialize_auth_database()
        donor_token = _generate_jwt("+8801755555555", "donor")
        cookies = {"access_token": donor_token}

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
        self.assertEqual(data["preferred_zones"], ["Dhanmondi"])
        self.assertTrue(self.client.get("/api/v1/donor/availability", cookies=cookies).json()["is_available"])

        disabled = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": False},
            cookies=cookies,
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(self.client.get("/api/v1/donor/availability", cookies=cookies).json()["is_available"])

    def test_donor_availability_requires_donor_authentication(self):
        initialize_auth_database()
        endpoint = "/api/v1/donor/availability"
        payload = {"is_available": True}
        self.assertEqual(self.client.get(endpoint).status_code, 401)
        self.assertEqual(self.client.post(endpoint, json=payload).status_code, 401)

        seeker_cookies = {"access_token": _generate_jwt("+8801723456789", "seeker")}
        self.assertEqual(self.client.get(endpoint, cookies=seeker_cookies).status_code, 403)
        self.assertEqual(self.client.post(endpoint, json=payload, cookies=seeker_cookies).status_code, 403)

    def test_donor_can_schedule_cancel_and_auto_expire_unavailability(self):
        initialize_auth_database()
        donor_phone = "+8801755555560"
        cookies = {"access_token": _generate_jwt(donor_phone, "donor")}
        endpoint = "/api/v1/donor/availability/schedule"
        today = _current_donor_date()
        start_date = (today + timedelta(days=2)).isoformat()
        end_date = (today + timedelta(days=7)).isoformat()

        scheduled = self.client.post(
            endpoint,
            json={"start_date": start_date, "end_date": end_date},
            cookies=cookies,
        )
        self.assertEqual(scheduled.status_code, 200)
        self.assertTrue(scheduled.json()["is_available"])
        self.assertEqual(scheduled.json()["unavailability_start_date"], start_date)
        self.assertEqual(scheduled.json()["unavailability_end_date"], end_date)

        cancelled = self.client.delete(endpoint, cookies=cookies)
        self.assertEqual(cancelled.status_code, 200)
        self.assertTrue(cancelled.json()["is_available"])
        self.assertIsNone(cancelled.json()["unavailability_start_date"])

        active = self.client.post(
            endpoint,
            json={"start_date": today.isoformat(), "end_date": (today + timedelta(days=1)).isoformat()},
            cookies=cookies,
        )
        self.assertEqual(active.status_code, 200)
        self.assertFalse(active.json()["is_available"])
        self.assertTrue(active.json()["unavailability_active"])
        self.assertFalse(self.client.get("/api/v1/donor/availability", cookies=cookies).json()["is_available"])

        expired_end = (today - timedelta(days=1)).isoformat()
        with closing(_connection()) as connection:
            with connection:
                connection.execute(
                    """UPDATE donor_availability
                       SET unavailable_start_date = ?, unavailable_end_date = ?, is_available = 0
                       WHERE donor_phone = ?""",
                    (expired_end, expired_end, donor_phone),
                )
        reenabled = self.client.get("/api/v1/donor/availability", cookies=cookies)
        self.assertEqual(reenabled.status_code, 200)
        self.assertTrue(reenabled.json()["is_available"])
        self.assertIsNone(reenabled.json()["unavailability_end_date"])

    def test_donor_unavailability_schedule_rejects_invalid_or_unauthorized_ranges(self):
        initialize_auth_database()
        endpoint = "/api/v1/donor/availability/schedule"
        today = _current_donor_date()
        valid_range = {
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        }
        self.assertEqual(self.client.post(endpoint, json=valid_range).status_code, 401)
        self.assertEqual(self.client.delete(endpoint).status_code, 401)

        seeker_cookies = {"access_token": _generate_jwt("+8801723456789", "seeker")}
        self.assertEqual(
            self.client.post(endpoint, json=valid_range, cookies=seeker_cookies).status_code,
            403,
        )
        self.assertEqual(self.client.delete(endpoint, cookies=seeker_cookies).status_code, 403)

        donor_cookies = {"access_token": _generate_jwt("+8801755555561", "donor")}
        invalid_order = {
            "start_date": (today + timedelta(days=2)).isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        }
        self.assertEqual(
            self.client.post(endpoint, json=invalid_order, cookies=donor_cookies).status_code,
            422,
        )
        past_start = {
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": today.isoformat(),
        }
        self.assertEqual(
            self.client.post(endpoint, json=past_start, cookies=donor_cookies).status_code,
            422,
        )

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
