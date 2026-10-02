import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt


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
        self.assertIn("Donor Profile & Medical Info", html)
        self.assertIn("Donation History", html)
        self.assertIn("Matched Blood Requests", html)
        self.assertIn("Accept & Decline Flow", html)
        self.assertIn("Request Details & Directions", html)
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
        response = self.client.post(
            "/api/v1/donor/availability",
            json={"is_available": True, "radius_km": 15, "preferred_zones": ["Dhanmondi"]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["is_available"])
        self.assertEqual(data["radius_km"], 15)

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

