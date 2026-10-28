import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from main import app, _generate_jwt, DATABASE_PATH, AUTH_DATABASE_PATH
from admin_portal import (
    initialize_admin_and_notification_database,
    dispatch_web_push_notification,
    dispatch_in_app_notification,
    sanitize_push_payload,
)


class WebPushNotificationsGatewayTests(unittest.TestCase):
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
    # Screen & Gateway Accessibility
    # -------------------------------------------------------------------------
    def test_push_gateway_screen_accessible(self):
        """Screen /push-gateway and /admin/push-gateway render successfully."""
        for path in ["/push-gateway", "/admin/push-gateway"]:
            res = self.client.get(path, cookies=self.admin_cookies)
            self.assertEqual(res.status_code, 200)
            html = res.text
            self.assertIn("Web Push Notifications Gateway (FCM)", html)
            self.assertIn("This screen manages browser-based push notifications", html)
            self.assertIn("permissionSection", html)
            self.assertIn("preferencesSection", html)
            self.assertIn("devicesSection", html)
            self.assertIn("dispatchSection", html)
            self.assertIn("logsSection", html)
            self.assertIn("push_gateway.css", html)
            self.assertIn("push_gateway.js", html)

    def test_push_gateway_screen_accessible_for_donor_and_seeker(self):
        """Push gateway screen renders properly for donor and seeker users."""
        res_donor = self.client.get("/push-gateway", cookies=self.donor_cookies)
        self.assertEqual(res_donor.status_code, 200)
        self.assertIn("Web Push Notifications Gateway (FCM)", res_donor.text)

        res_seeker = self.client.get("/push-gateway", cookies=self.seeker_cookies)
        self.assertEqual(res_seeker.status_code, 200)
        self.assertIn("Web Push Notifications Gateway (FCM)", res_seeker.text)

    def test_service_worker_endpoints_served(self):
        """Service worker scripts are accessible at root paths with javascript MIME."""
        res_fcm = self.client.get("/firebase-messaging-sw.js")
        self.assertEqual(res_fcm.status_code, 200)
        self.assertIn("application/javascript", res_fcm.headers["content-type"])
        self.assertIn("Service-Worker-Allowed", res_fcm.headers)

        res_sw = self.client.get("/sw.js")
        self.assertEqual(res_sw.status_code, 200)
        self.assertIn("application/javascript", res_sw.headers["content-type"])

    # -------------------------------------------------------------------------
    # Acceptance Criterion 1: Push notification permission can be requested
    # -------------------------------------------------------------------------
    def test_push_permission_requested_and_device_subscribed(self):
        """Push notification permission can be requested and device authorized."""
        test_endpoint = "https://fcm.googleapis.com/fcm/send/test_device_token_xyz_9988"
        payload = {
            "endpoint": test_endpoint,
            "auth_key": "auth_key_test_123",
            "p256dh_key": "p256dh_key_test_456",
            "browser": "Chrome 122 on Windows",
            "device_type": "Desktop",
            "user_phone": self.donor_phone,
            "permission_status": "granted",
        }
        res = self.client.post("/api/v1/notifications/push/subscribe", json=payload, cookies=self.donor_cookies)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["permission_status"], "granted")
        self.assertIn("device_id", data)

        # Verify DB storage
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM push_subscriptions WHERE endpoint = ?", (test_endpoint,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["user_phone"], self.donor_phone)
            self.assertEqual(row["status"], "authorized")
            self.assertEqual(row["permission_status"], "granted")
            self.assertEqual(row["browser"], "Chrome 122 on Windows")
            self.assertEqual(row["device_type"], "Desktop")

    def test_subscribing_existing_endpoint_updates_rather_than_duplicates(self):
        """Re-subscribing an existing endpoint updates status and timestamp."""
        endpoint = "https://fcm.googleapis.com/fcm/send/test_endpoint_dedup_001"
        payload1 = {
            "endpoint": endpoint,
            "browser": "Chrome 120",
            "device_type": "Desktop",
            "user_phone": self.seeker_phone,
            "permission_status": "granted",
        }
        res1 = self.client.post("/api/v1/notifications/push/subscribe", json=payload1)
        id1 = res1.json()["device_id"]

        # Subscribe again with updated browser
        payload2 = {
            "endpoint": endpoint,
            "browser": "Chrome 122 Updated",
            "device_type": "Desktop",
            "user_phone": self.seeker_phone,
            "permission_status": "granted",
        }
        res2 = self.client.post("/api/v1/notifications/push/subscribe", json=payload2)
        id2 = res2.json()["device_id"]

        self.assertEqual(id1, id2)
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()[0]
            self.assertEqual(cnt, 1)
            row = conn.execute("SELECT browser FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()
            self.assertEqual(row[0], "Chrome 122 Updated")

    # -------------------------------------------------------------------------
    # Acceptance Criterion 2: Notifications can be delivered to authorized devices
    # -------------------------------------------------------------------------
    def test_notifications_delivered_to_authorized_devices(self):
        """Notifications are delivered to authorized devices and logged with FCM message ID."""
        # Ensure an authorized device exists for donor
        endpoint = "https://fcm.googleapis.com/fcm/send/fcm_token_donor_auth_test_1"
        self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={
                "endpoint": endpoint,
                "user_phone": self.donor_phone,
                "browser": "Firefox on Linux",
                "device_type": "Desktop",
                "permission_status": "granted",
            },
        )

        # Dispatch push notification to donor
        payload = {
            "recipient_phone": self.donor_phone,
            "title": "Blood Match Available",
            "body": "A compatible request for A+ blood is waiting at DMCH.",
            "click_url": "/find-blood",
            "event_type": "request",
        }
        res = self.client.post("/api/v1/notifications/push/send", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["delivered"], 1)
        self.assertEqual(data["failed"], 0)
        self.assertGreater(len(data["fcm_message_ids"]), 0)
        self.assertTrue(data["fcm_message_ids"][0].startswith("fcm_msg_"))

        # Verify dispatch log record
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            log = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE recipient_phone = ? AND status = 'delivered' ORDER BY id DESC LIMIT 1",
                (self.donor_phone,),
            ).fetchone()
            self.assertIsNotNone(log)
            self.assertEqual(log["title"], "Blood Match Available")
            self.assertEqual(log["status"], "delivered")
            self.assertTrue(log["fcm_message_id"].startswith("fcm_msg_"))

    def test_broadcast_delivers_to_all_authorized_devices(self):
        """Broadcasting with recipient_phone='all' delivers to all active authorized devices."""
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": "all",
                "title": "Platform Health Notice",
                "body": "System scheduled maintenance at midnight.",
                "click_url": "/",
                "event_type": "system",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data["status"], ["success", "partial"])
        self.assertGreater(data["delivered"], 0)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 3: Relevant events trigger notifications
    # -------------------------------------------------------------------------
    def test_emergency_blood_broadcast_triggers_web_push(self):
        """Emergency blood broadcast triggers web push notification."""
        create_res = self.client.post(
            "/api/v1/seeker/requests/emergency",
            json={
                "patient_name": "Emergency Trauma Recipient",
                "blood_group": "A+",
                "hospital_name": "Dhaka Medical College",
                "district": "Dhaka",
                "area": "Bakshibazar",
                "units": 2,
                "urgency_level": "Code Red (Within 1 Hour)",
                "reason": "Severe hemorrhage",
                "contact_phone": "+8801723456789",
            },
            cookies=self.seeker_cookies,
        )
        self.assertEqual(create_res.status_code, 200)

        # Check push dispatch logs recorded emergency broadcast
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE event_type = 'emergency' ORDER BY id DESC LIMIT 5"
            ).fetchall()
            self.assertGreater(len(rows), 0)
            self.assertTrue(any("Emergency" in r["title"] or "URGENT" in r["title"] for r in rows))

    def test_standard_blood_request_triggers_web_push(self):
        """Creating standard blood request triggers web push notification."""
        needed_at = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        create_res = self.client.post(
            "/api/v1/seeker/requests",
            json={
                "patient_name": "Mizanur Rahman",
                "blood_group": "A+",
                "hospital_name": "Ibn Sina Medical",
                "district": "Dhaka",
                "area": "Kalyanpur",
                "units": 1,
                "needed_at": needed_at,
                "reason": "Orthopedic surgery",
                "contact_phone": "+8801723456789",
            },
            cookies=self.seeker_cookies,
        )
        self.assertEqual(create_res.status_code, 200)

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE event_type = 'request' ORDER BY id DESC LIMIT 5"
            ).fetchall()
            self.assertGreater(len(rows), 0)

    def test_sending_chat_message_triggers_web_push(self):
        """Direct chat message send triggers web push notification to recipient."""
        # Ensure recipient donor has authorized device
        self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/fcm_token_donor_chat_test",
                "user_phone": self.donor_phone,
                "permission_status": "granted",
            },
        )

        sent = self.client.post(
            "/api/v1/seeker/chat/thread-ayesha/send",
            json={"text": "Hello, when can you donate blood today?"},
            cookies=self.seeker_cookies,
        )
        self.assertEqual(sent.status_code, 200)

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE recipient_phone = ? AND event_type = 'message' ORDER BY id DESC LIMIT 1",
                (self.donor_phone,),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertIn("Message", row["title"])
            self.assertIn("Hello", row["body"])

    def test_donor_kyc_approval_triggers_web_push(self):
        """Admin approving donor KYC triggers web push notification to donor."""
        # Ensure donor has an authorized device
        self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/fcm_token_donor_kyc_test",
                "user_phone": self.donor_phone,
                "permission_status": "granted",
            },
        )

        # Ensure a pending KYC verification exists for self.donor_phone
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO donor_kyc_verifications (donor_phone, donor_name, blood_group, nid_number, document_type, status, submitted_at)
                    VALUES (?, 'Ayesha Rahman', 'A+', '19922612345678901', 'National ID (NID)', 'pending', ?)
                    """,
                    (self.donor_phone, datetime.now(timezone.utc).isoformat()),
                )
                item_id = cursor.lastrowid

        res = self.client.post(
            f"/api/v1/admin/kyc/{item_id}/review",
            json={"action": "approve", "reason": "National ID confirmed with government portal", "reviewer_name": "Supervisor Admin"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(res.status_code, 200)

        # Check push dispatch logs
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            log = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE recipient_phone = ? AND event_type = 'kyc' ORDER BY id DESC LIMIT 1",
                (self.donor_phone,),
            ).fetchone()
            self.assertIsNotNone(log)
            self.assertIn("Verification Approved", log["title"])

    # -------------------------------------------------------------------------
    # Acceptance Criterion 4: Users can manage notification permission
    # -------------------------------------------------------------------------
    def test_users_can_retrieve_and_update_notification_preferences(self):
        """User can retrieve and manage push notification permissions and preferences."""
        # Get preferences
        get_res = self.client.get(f"/api/v1/notifications/push/preferences?phone={self.donor_phone}", cookies=self.donor_cookies)
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("preferences", data)
        self.assertEqual(data["preferences"]["push_enabled"], 1)

        # Update preferences (turn off direct chat messages)
        update_payload = {
            "phone": self.donor_phone,
            "push_enabled": True,
            "emergency_alerts": True,
            "request_updates": True,
            "chat_messages": False,
            "system_announcements": True,
        }
        post_res = self.client.post("/api/v1/notifications/push/preferences", json=update_payload, cookies=self.donor_cookies)
        self.assertEqual(post_res.status_code, 200)

        # Verify updated preferences
        verify_res = self.client.get(f"/api/v1/notifications/push/preferences?phone={self.donor_phone}")
        self.assertEqual(verify_res.json()["preferences"]["chat_messages"], 0)

    def test_push_delivery_suppressed_when_user_disables_category(self):
        """Push notifications are suppressed when user opts out of that event category."""
        # Disable request updates for donor
        self.client.post(
            "/api/v1/notifications/push/preferences",
            json={"phone": self.donor_phone, "push_enabled": True, "request_updates": False},
        )

        # Dispatch request notification
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": self.donor_phone,
                "title": "Matching Blood Request",
                "body": "A donor request is waiting for your response.",
                "event_type": "request",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "suppressed")
        self.assertEqual(data["delivered"], 0)

        # Reset preference back to enabled
        self.client.post(
            "/api/v1/notifications/push/preferences",
            json={"phone": self.donor_phone, "push_enabled": True, "request_updates": True, "chat_messages": True},
        )

    def test_user_can_view_authorized_devices_and_revoke_permission(self):
        """User can list authorized devices and revoke permission for a specific device."""
        # Subscribe a test device
        ep = "https://fcm.googleapis.com/fcm/send/test_device_to_revoke_123"
        sub_res = self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={"endpoint": ep, "user_phone": self.donor_phone, "permission_status": "granted"},
        )
        device_id = sub_res.json()["device_id"]

        # View devices
        dev_res = self.client.get(f"/api/v1/notifications/push/devices?phone={self.donor_phone}")
        self.assertEqual(dev_res.status_code, 200)
        devices = dev_res.json()["devices"]
        self.assertTrue(any(d["id"] == device_id for d in devices))

        # Revoke device
        del_res = self.client.delete(f"/api/v1/notifications/push/devices/{device_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "success")

        # Verify device is now revoked
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT status FROM push_subscriptions WHERE id = ?", (device_id,)).fetchone()
            self.assertEqual(row[0], "revoked")

    def test_unsubscribe_endpoint_revokes_permission(self):
        """POST /api/v1/notifications/push/unsubscribe revokes the device endpoint."""
        ep = "https://fcm.googleapis.com/fcm/send/test_unsub_device_001"
        self.client.post("/api/v1/notifications/push/subscribe", json={"endpoint": ep, "user_phone": self.seeker_phone})

        unsub_res = self.client.post("/api/v1/notifications/push/unsubscribe", json={"endpoint": ep})
        self.assertEqual(unsub_res.status_code, 200)
        self.assertEqual(unsub_res.json()["status"], "success")

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT status FROM push_subscriptions WHERE endpoint = ?", (ep,)).fetchone()
            self.assertEqual(row[0], "revoked")

    # -------------------------------------------------------------------------
    # Acceptance Criterion 5: Failed notification delivery is handled appropriately
    # -------------------------------------------------------------------------
    def test_failed_delivery_with_expired_token_is_handled_and_pruned(self):
        """Failed delivery due to expired token is logged and device subscription pruned."""
        expired_endpoint = "https://fcm.googleapis.com/fcm/send/fcm_expired_token_bad_device"
        self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={"endpoint": expired_endpoint, "user_phone": self.donor_phone, "permission_status": "granted"},
        )

        # Dispatch with simulated token expired failure
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": self.donor_phone,
                "title": "Failed Delivery Test",
                "body": "Testing invalid token pruning.",
                "simulate_failure": "token_expired",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["failed"], 0)

        # Verify log recorded failure reason
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            log = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE status = 'failed' AND failure_reason = 'device_unregistered' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(log)
            self.assertEqual(log["failure_reason"], "device_unregistered")

            # Verify invalid device was marked expired in push_subscriptions
            sub = conn.execute("SELECT status FROM push_subscriptions WHERE endpoint = ?", (expired_endpoint,)).fetchone()
            self.assertEqual(sub[0], "expired")

    def test_network_timeout_failure_handled_without_crash(self):
        """Network timeout during push dispatch is logged as failed without crashing."""
        self.client.post(
            "/api/v1/notifications/push/subscribe",
            json={"endpoint": "https://fcm.googleapis.com/fcm/send/fresh_timeout_device_001", "user_phone": self.donor_phone, "permission_status": "granted"},
        )
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": self.donor_phone,
                "title": "Timeout Test",
                "body": "Testing gateway timeout recovery.",
                "simulate_failure": "network_timeout",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["failed"], 0)

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            log = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE failure_reason = 'network_timeout' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(log)

    def test_dispatch_to_user_with_no_devices_handled_gracefully(self):
        """Dispatching push to user with no devices logs appropriately without crashing."""
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": "+8801700000000",
                "title": "No Device Alert",
                "body": "User has zero subscribed devices.",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["delivered"], 0)

    def test_retry_failed_push_notification_endpoint(self):
        """POST /api/v1/notifications/push/retry/{id} retries a failed push dispatch."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT id FROM push_dispatch_logs WHERE status = 'failed' LIMIT 1").fetchone()
            log_id = row[0] if row else 1

        retry_res = self.client.post(f"/api/v1/notifications/push/retry/{log_id}")
        self.assertEqual(retry_res.status_code, 200)
        self.assertEqual(retry_res.json()["status"], "success")

    def test_push_stats_endpoint_returns_metrics(self):
        """GET /api/v1/notifications/push/stats returns accurate metrics."""
        res = self.client.get("/api/v1/notifications/push/stats")
        self.assertEqual(res.status_code, 200)
        stats = res.json()["stats"]
        self.assertIn("total_devices", stats)
        self.assertIn("authorized_devices", stats)
        self.assertIn("delivered", stats)
        self.assertIn("failed", stats)
        self.assertIn("success_rate_percent", stats)

    # -------------------------------------------------------------------------
    # Acceptance Criterion 6: Notification data does not expose sensitive information
    # -------------------------------------------------------------------------
    def test_confidential_medical_diagnosis_is_scrubbed_from_push(self):
        """Stigmatizing confidential medical diagnosis is generalized before push delivery."""
        sensitive_body = "Patient has HIV positive status and stage 4 terminal carcinoma. Transfusion needed."
        title, clean_body, data, was_scrubbed = sanitize_push_payload("Blood Need", sensitive_body)
        self.assertTrue(was_scrubbed)
        self.assertNotIn("hiv", clean_body.lower())
        self.assertNotIn("carcinoma", clean_body.lower())
        self.assertIn("critical medical requirement", clean_body.lower())

    def test_national_id_number_is_masked_in_push_data(self):
        """Full 10-17 digit NID number is masked to protect citizen identity."""
        body = "Donor verification for NID: 19922612345678901 is required."
        title, clean_body, data, was_scrubbed = sanitize_push_payload("KYC Verification", body)
        self.assertTrue(was_scrubbed)
        self.assertNotIn("19922612345678901", clean_body)
        self.assertIn("8901", clean_body)

    def test_passwords_and_tokens_are_redacted_from_push(self):
        """Passwords, auth tokens, and OTP codes are redacted from notification text and payload."""
        body = "Account alert. Your password: mySecretPassword123 and token: eyJhbGciOiJIUzI1NiJ9"
        title, clean_body, clean_data, was_scrubbed = sanitize_push_payload(
            "Account Security",
            body,
            {"token": "secret_jwt_xyz", "otp": "998822", "patient_name": "Ayesha"},
        )
        self.assertTrue(was_scrubbed)
        self.assertNotIn("mySecretPassword123", clean_body)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", clean_body)
        self.assertEqual(clean_data["token"], "[REDACTED]")
        self.assertEqual(clean_data["otp"], "[REDACTED]")
        self.assertEqual(clean_data["patient_name"], "Ayesha")

    def test_excessively_long_push_body_is_truncated(self):
        """Overly long message body is safely truncated for lockscreen notification display."""
        very_long_text = "Important blood request notification. " * 20
        self.assertGreater(len(very_long_text), 300)

        title, clean_body, data, was_scrubbed = sanitize_push_payload("Alert", very_long_text)
        self.assertTrue(was_scrubbed)
        self.assertLessEqual(len(clean_body), 240)
        self.assertTrue(clean_body.endswith("..."))

    def test_dispatch_records_sensitive_data_scrubbed_indicator(self):
        """Push dispatch with sanitized sensitive data records scrubbed indicator in DB."""
        res = self.client.post(
            "/api/v1/notifications/push/send",
            json={
                "recipient_phone": self.donor_phone,
                "title": "Medical Transfusion Notice",
                "body": "Patient with confidential diagnosis NID: 19922612345678901 requires urgent blood.",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["sensitive_data_scrubbed"])

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            log = conn.execute(
                "SELECT * FROM push_dispatch_logs WHERE sensitive_data_scrubbed = 1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(log)
            self.assertNotIn("19922612345678901", log["body"])


if __name__ == "__main__":
    unittest.main()
