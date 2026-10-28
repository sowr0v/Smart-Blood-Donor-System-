import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from main import app, _generate_jwt, DATABASE_PATH, AUTH_DATABASE_PATH
from admin_portal import (
    initialize_admin_and_notification_database,
    dispatch_in_app_notification,
)


class InAppNotificationCenterTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_phone = "+8801745678901"
        self.donor_phone = "+8801712345678"
        self.seeker_phone = "+8801723456789"

        self.admin_token = _generate_jwt(self.admin_phone, "admin")
        self.donor_token = _generate_jwt(self.donor_phone, "donor")
        self.seeker_token = _generate_jwt(self.seeker_phone, "seeker")

        self.admin_cookies = {"access_token": self.admin_token}
        self.donor_cookies = {"access_token": self.donor_token}
        self.seeker_cookies = {"access_token": self.seeker_token}

        initialize_admin_and_notification_database()

    # -------------------------------------------------------------------------
    # Acceptance Criterion 1: Notification center is accessible
    # -------------------------------------------------------------------------
    def test_notification_center_screen_accessible_for_admin(self):
        """Notification center route /notifications renders successfully for admin."""
        res = self.client.get("/notifications", cookies=self.admin_cookies)
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("In-App Notification Center", html)
        self.assertIn("fullNotificationList", html)
        self.assertIn("screenUnreadBadge", html)
        self.assertIn("notifBellBtn", html)
        self.assertIn("notificationDrawer", html)
        self.assertIn("/admin/dashboard", html)
        self.assertIn("/static/css/notifications.css", html)
        self.assertIn("/static/js/notifications.js", html)

    def test_notification_center_screen_accessible_for_donor(self):
        """Notification center route /notifications renders successfully for donor."""
        res = self.client.get("/notifications", cookies=self.donor_cookies)
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("In-App Notification Center", html)
        self.assertIn("fullNotificationList", html)
        self.assertIn("/donor/dashboard", html)

    def test_notification_center_screen_accessible_for_seeker(self):
        """Notification center route /notifications renders successfully for seeker."""
        res = self.client.get("/notifications", cookies=self.seeker_cookies)
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("In-App Notification Center", html)
        self.assertIn("fullNotificationList", html)
        self.assertIn("/seeker/dashboard", html)

    def test_notification_center_alias_route_accessible(self):
        """Alias route /notification-center renders successfully."""
        res = self.client.get("/notification-center", cookies=self.donor_cookies)
        self.assertEqual(res.status_code, 200)
        self.assertIn("In-App Notification Center", res.text)

    def test_notification_center_accessible_from_all_dashboards(self):
        """Bell button and notification drawer are accessible across role dashboards."""
        endpoints = [
            ("/admin/dashboard", self.admin_cookies),
            ("/donor/dashboard", self.donor_cookies),
            ("/seeker/dashboard", self.seeker_cookies),
        ]
        for url, cookies in endpoints:
            res = self.client.get(url, cookies=cookies)
            self.assertEqual(res.status_code, 200)
            self.assertIn("notifBellBtn", res.text, f"Missing notifBellBtn in {url}")
            self.assertIn("notificationDrawer", res.text, f"Missing notificationDrawer in {url}")
            self.assertIn("notificationBadge", res.text, f"Missing notificationBadge in {url}")
            self.assertIn("notifications.js", res.text, f"Missing notifications.js in {url}")

    # -------------------------------------------------------------------------
    # Acceptance Criterion 2: Notifications are listed
    # -------------------------------------------------------------------------
    def test_notifications_are_listed_via_api(self):
        """Notifications are listed via /api/v1/notifications with metadata."""
        res = self.client.get("/api/v1/notifications", cookies=self.donor_cookies)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("notifications", data)
        self.assertIn("unread_count", data)
        self.assertIn("total", data)
        self.assertGreater(len(data["notifications"]), 0)

        # Verify notification object attributes
        item = data["notifications"][0]
        self.assertIn("id", item)
        self.assertIn("recipient_phone", item)
        self.assertIn("title", item)
        self.assertIn("message", item)
        self.assertIn("type", item)
        self.assertIn("link", item)
        self.assertIn("is_read", item)
        self.assertIn("priority", item)
        self.assertIn("created_at", item)

    def test_notifications_listed_filtered_by_type(self):
        """Filter notifications by category (request, message, account)."""
        # Filter request
        res = self.client.get("/api/v1/notifications?phone=+8801712345678&type=request")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertTrue(all(n["type"] == "request" for n in items))

        # Filter message
        res = self.client.get("/api/v1/notifications?phone=+8801712345678&type=message")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertTrue(all(n["type"] == "message" for n in items))

        # Filter account
        res = self.client.get("/api/v1/notifications?phone=+8801712345678&type=account")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertTrue(all(n["type"] == "account" for n in items))

    def test_notifications_listed_filtered_by_search_query(self):
        """Keyword search filters notifications by title or message text."""
        res = self.client.get("/api/v1/notifications?phone=+8801712345678&q=Square+Hospital")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertGreater(len(items), 0)
        for item in items:
            text = f"{item['title']} {item['message']}".lower()
            self.assertIn("square hospital", text)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 3: Unread notifications are identifiable
    # -------------------------------------------------------------------------
    def test_unread_notifications_are_identifiable(self):
        """Unread notifications have is_read=0 and are reported by unread_count and filter."""
        res = self.client.get("/api/v1/notifications?phone=+8801712345678")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        unread_count = data["unread_count"]
        self.assertGreater(unread_count, 0)

        # Fetch only unread
        res_unread = self.client.get("/api/v1/notifications?phone=+8801712345678&status=unread")
        self.assertEqual(res_unread.status_code, 200)
        unread_items = res_unread.json()["notifications"]
        self.assertEqual(len(unread_items), unread_count)
        self.assertTrue(all(item["is_read"] == 0 for item in unread_items))

        # Fetch only read
        res_read = self.client.get("/api/v1/notifications?phone=+8801712345678&status=read")
        self.assertEqual(res_read.status_code, 200)
        read_items = res_read.json()["notifications"]
        self.assertTrue(all(item["is_read"] == 1 for item in read_items))

    def test_unread_badges_rendered_on_screen(self):
        """Notification center page renders unread badges and indicators."""
        res = self.client.get("/notifications", cookies=self.donor_cookies)
        self.assertEqual(res.status_code, 200)
        html = res.text
        self.assertIn("notif-unread-indicator-dot", html)
        self.assertIn("notif-unread-pill-badge", html)
        self.assertIn("UNREAD", html)
        self.assertIn("screen-unread-badge-pill", html)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 4: Notifications can be marked as read
    # -------------------------------------------------------------------------
    def test_individual_notification_marked_as_read(self):
        """Single notification can be marked as read via POST /api/v1/notifications/{id}/read."""
        # Create a fresh unread notification
        test_id = dispatch_in_app_notification(
            recipient_phone=self.donor_phone,
            title="Test Unread Notification",
            message="Please mark me as read.",
            notif_type="system",
            link="/test",
            priority="normal",
        )

        # Verify initial unread state
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT is_read FROM app_notifications WHERE id = ?", (test_id,)).fetchone()
            self.assertEqual(row[0], 0)

        # Call mark read endpoint
        mark_res = self.client.post(f"/api/v1/notifications/{test_id}/read")
        self.assertEqual(mark_res.status_code, 200)
        self.assertEqual(mark_res.json()["status"], "success")
        self.assertEqual(mark_res.json()["is_read"], 1)

        # Verify updated read state in DB
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT is_read FROM app_notifications WHERE id = ?", (test_id,)).fetchone()
            self.assertEqual(row[0], 1)

    def test_notification_marked_as_unread(self):
        """Notification can be marked back as unread via POST /api/v1/notifications/{id}/unread."""
        test_id = dispatch_in_app_notification(
            recipient_phone=self.donor_phone,
            title="Test Read Item",
            message="Testing unread toggle.",
            notif_type="system",
            link="",
            priority="normal",
        )
        # Mark read first
        self.client.post(f"/api/v1/notifications/{test_id}/read")

        # Mark unread
        res = self.client.post(f"/api/v1/notifications/{test_id}/unread")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["is_read"], 0)

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT is_read FROM app_notifications WHERE id = ?", (test_id,)).fetchone()
            self.assertEqual(row[0], 0)

    def test_mark_all_notifications_read(self):
        """All user notifications can be marked as read via POST /api/v1/notifications/mark-all-read."""
        # Ensure at least 2 unread exist for seeker
        dispatch_in_app_notification(self.seeker_phone, "Seeker Test 1", "Msg 1", "request", "/test1")
        dispatch_in_app_notification(self.seeker_phone, "Seeker Test 2", "Msg 2", "message", "/test2")

        # Mark all read for seeker
        mark_all_res = self.client.post(
            f"/api/v1/notifications/mark-all-read?phone={self.seeker_phone}",
            cookies=self.seeker_cookies,
        )
        self.assertEqual(mark_all_res.status_code, 200)
        self.assertEqual(mark_all_res.json()["status"], "success")

        # Verify unread count is now 0
        get_res = self.client.get(f"/api/v1/notifications?phone={self.seeker_phone}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["unread_count"], 0)

    def test_mark_nonexistent_notification_returns_404(self):
        """Marking a non-existent notification as read returns 404."""
        res = self.client.post("/api/v1/notifications/999999/read")
        self.assertEqual(res.status_code, 404)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 5: Notification timestamps are displayed
    # -------------------------------------------------------------------------
    def test_notification_timestamps_are_displayed_and_valid(self):
        """Every notification has a valid ISO timestamp and timestamps are in HTML."""
        res = self.client.get(f"/api/v1/notifications?phone={self.donor_phone}")
        self.assertEqual(res.status_code, 200)
        notifications = res.json()["notifications"]
        self.assertGreater(len(notifications), 0)

        for item in notifications:
            ts = item.get("created_at")
            self.assertTrue(ts, "Notification missing created_at timestamp")
            # Parse ISO format
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            self.assertIsInstance(parsed, datetime)

        # Check HTML renders timestamp elements
        html_res = self.client.get("/notifications", cookies=self.donor_cookies)
        self.assertEqual(html_res.status_code, 200)
        self.assertIn("notif-card-timestamp", html_res.text)
        self.assertIn("notif-time-text", html_res.text)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 6: Relevant notifications linked to actions/pages
    # -------------------------------------------------------------------------
    def test_notifications_are_linked_to_actions_and_pages(self):
        """Notifications contain actionable links (find blood, chat, dashboard, kyc)."""
        res = self.client.get(f"/api/v1/notifications?phone={self.donor_phone}")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]

        links = [n.get("link") for n in items if n.get("link")]
        self.assertGreater(len(links), 0)
        self.assertTrue(any("/find-blood" in l for l in links))
        self.assertTrue(any("chat" in l or "dashboard" in l for l in links))

        # Check HTML renders action buttons for linked items
        html_res = self.client.get("/notifications", cookies=self.donor_cookies)
        self.assertEqual(html_res.status_code, 200)
        self.assertIn("btn-notif-action", html_res.text)
        self.assertIn("Take Action", html_res.text)

    # -------------------------------------------------------------------------
    # Event-Driven Notification Generation
    # -------------------------------------------------------------------------
    def test_sending_chat_message_generates_in_app_notification(self):
        """Sending a chat message generates an in-app notification for recipient peer."""
        initial_res = self.client.get(f"/api/v1/notifications?phone={self.donor_phone}&type=message")
        initial_count = len(initial_res.json()["notifications"])

        # Seeker sends live chat message to donor thread
        sent = self.client.post(
            "/api/v1/seeker/chat/thread-ayesha/send",
            json={"text": "Notification event test: I will arrive in 15 minutes."},
            cookies=self.seeker_cookies,
        )
        self.assertEqual(sent.status_code, 200)

        # Donor notifications should now contain the new message notification
        updated_res = self.client.get(f"/api/v1/notifications?phone={self.donor_phone}&type=message")
        self.assertEqual(updated_res.status_code, 200)
        updated_items = updated_res.json()["notifications"]
        self.assertGreater(len(updated_items), initial_count)

        latest = updated_items[0]
        self.assertEqual(latest["type"], "message")
        self.assertIn("Notification event test", latest["message"])
        self.assertEqual(latest["is_read"], 0)
        self.assertIn("chat", latest["link"])

    def test_creating_blood_request_generates_in_app_notification(self):
        """Creating a standard blood request publishes in-app notification."""
        needed_at = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        create_res = self.client.post(
            "/api/v1/seeker/requests",
            json={
                "patient_name": "Tariqul Alam",
                "blood_group": "B+",
                "hospital_name": "Square Hospital",
                "district": "Dhaka",
                "area": "Panthapath",
                "units": 2,
                "needed_at": needed_at,
                "reason": "Elective bypass surgery",
                "contact_phone": "+8801723456789",
            },
            cookies=self.seeker_cookies,
        )
        self.assertEqual(create_res.status_code, 200)

        # Check seeker received confirmation notification
        res = self.client.get(f"/api/v1/notifications?phone={self.seeker_phone}&type=request")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertTrue(any("Blood Request Published" in n["title"] for n in items))

    def test_emergency_blood_broadcast_generates_critical_alert(self):
        """Emergency blood broadcast publishes critical alert in notifications."""
        create_res = self.client.post(
            "/api/v1/seeker/requests/emergency",
            json={
                "patient_name": "Emergency Patient",
                "blood_group": "AB+",
                "hospital_name": "Ibn Sina Hospital",
                "district": "Dhaka",
                "area": "Dhanmondi",
                "units": 3,
                "urgency_level": "Code Red (Within 1 Hour)",
                "reason": "Massive trauma hemorrhage",
                "contact_phone": "+8801723456789",
            },
            cookies=self.seeker_cookies,
        )
        self.assertEqual(create_res.status_code, 200)

        # Check critical notification was broadcast to all
        res = self.client.get("/api/v1/notifications?type=emergency")
        self.assertEqual(res.status_code, 200)
        items = res.json()["notifications"]
        self.assertTrue(any("Emergency Blood Request" in n["title"] or "EMERGENCY" in n["title"] for n in items))

    def test_successful_login_generates_account_activity_notification(self):
        """Successful login records an account activity notification."""
        login_res = self.client.post(
            "/login",
            data={
                "phone_number": "+8801712345678",
                "password": "secret123",
                "admin_console": "false",
            },
            follow_redirects=False,
        )
        self.assertEqual(login_res.status_code, 303)

        # Check account activity notifications for donor
        notif_res = self.client.get(f"/api/v1/notifications?phone={self.donor_phone}&type=account")
        self.assertEqual(notif_res.status_code, 200)
        items = notif_res.json()["notifications"]
        self.assertTrue(any("Login" in n["title"] or "Login" in n["message"] for n in items))

    def test_delete_notification_endpoint(self):
        """DELETE /api/v1/notifications/{id} removes the notification."""
        test_id = dispatch_in_app_notification(
            recipient_phone=self.donor_phone,
            title="Temporary Item",
            message="To be deleted.",
            notif_type="system",
            link="",
            priority="normal",
        )
        del_res = self.client.delete(f"/api/v1/notifications/{test_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "success")

        # Deleting again returns 404
        del_again = self.client.delete(f"/api/v1/notifications/{test_id}")
        self.assertEqual(del_again.status_code, 404)

    def test_send_in_app_notification_api(self):
        """POST /api/v1/notifications/send dispatches new notification."""
        payload = {
            "recipient_phone": self.donor_phone,
            "title": "Manual Broadcast Alert",
            "message": "Custom administrator dispatch message.",
            "type": "system",
            "link": "/find-blood",
            "priority": "high",
        }
        res = self.client.post("/api/v1/notifications/send", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")
        self.assertIn("id", res.json())


if __name__ == "__main__":
    unittest.main()
