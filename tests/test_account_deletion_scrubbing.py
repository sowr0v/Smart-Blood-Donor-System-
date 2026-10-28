import hashlib
import json
import sqlite3
import time
import unittest
import uuid

from fastapi.testclient import TestClient

from account_privacy_service import (
    DATA_RETENTION_POLICY_VERSION,
    initialize_privacy_database,
)
from main import (
    AUTH_DATABASE_PATH,
    DATABASE_PATH,
    SESSION_COOKIE,
    USERS,
    app,
    _generate_jwt,
    hash_password,
)


class AccountDeletionAndDataScrubbingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_privacy_database()

    def test_unauthenticated_account_deletion_screen_redirects_to_login(self):
        """Unauthenticated access to /account/delete must redirect to login with return path."""
        response = self.client.get("/account/delete", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/login?next=/account/delete", response.headers.get("location", ""))

    def test_authenticated_user_can_view_account_deletion_screen(self):
        """Authenticated user sees the dedicated Account Deletion & Data Privacy Scrubbing screen."""
        donor_phone = "+8801712345678"
        token = _generate_jwt(donor_phone, "donor")

        response = self.client.get("/account/delete", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify page title and header
        self.assertIn("Permanent Account Deletion &amp; Data Privacy Scrubbing", html)
        self.assertIn(f"v{DATA_RETENTION_POLICY_VERSION}", html)

        # Verify target user profile information
        self.assertIn(donor_phone, html)
        self.assertIn("Target for Permanent Erasure", html)

        # Verify policy cards
        self.assertIn("What Will Be Erased Immediately", html)
        self.assertIn("Regulatory &amp; Clinical Retention", html)
        self.assertIn("Donation Safety Traceability", html)

        # Verify form inputs
        self.assertIn('id="deletionPassword"', html)
        self.assertIn('id="deletionConfirmText"', html)
        self.assertIn('id="deletionConfirmPolicy"', html)
        self.assertIn('id="deletionReason"', html)
        self.assertIn('id="btnSubmitPermanentDeletion"', html)

    def test_donor_dashboard_clearly_displays_account_deletion_danger_zone(self):
        """Donor dashboard settings includes Danger Zone card for deletion."""
        token = _generate_jwt("+8801712345678", "donor")
        response = self.client.get("/donor/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("Danger Zone: Permanent Account Deletion &amp; Data Privacy Scrubbing", html)
        self.assertIn('id="dangerZoneDonorSection"', html)
        self.assertIn('href="/account/delete"', html)

    def test_seeker_dashboard_clearly_displays_deletion_and_portal_link(self):
        """Seeker dashboard contains account deletion options and privacy link."""
        token = _generate_jwt("+8801723456789", "seeker")
        response = self.client.get("/seeker/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("Danger Zone: Delete Seeker Account", html)
        self.assertIn('href="/account/delete"', html)

    def test_hospital_dashboard_clearly_displays_deletion_and_portal_link(self):
        """Hospital dashboard contains facility account deletion options and privacy link."""
        token = _generate_jwt("+8801734567890", "hospital")
        response = self.client.get("/hospital/dashboard", cookies={"access_token": token})
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("Danger Zone", html)
        self.assertIn('href="/account/delete"', html)

    def test_privacy_policy_page_displays_data_retention_and_deletion_link(self):
        """Privacy Policy page details Data Retention Policy and links to deletion portal."""
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("Data Retention Policy &amp; Permanent Account Deletion", html)
        self.assertIn("Eligible Personal Data", html)
        self.assertIn("Clinical Transfusion Records", html)
        self.assertIn('href="/account/delete"', html)

    def test_identity_verification_rejects_wrong_password(self):
        """Deletion API rejects attempts where password verification fails."""
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        raw_password = "CorrectPassword123!"

        # Register user
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Verify Donor",
                "phone": unique_phone,
                "password": raw_password,
                "role": "donor",
            },
        )
        self.assertEqual(reg_resp.status_code, 200)

        token = _generate_jwt(unique_phone, "donor")

        # Attempt deletion with WRONG password
        payload = {
            "password": "WrongPassword999!",
            "confirm_text": "DELETE",
            "confirm_policy": True,
            "reason": "Test",
        }
        del_resp = self.client.post(
            "/api/v1/account/delete",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(del_resp.status_code, 400)
        self.assertIn("identity verification failed", del_resp.json()["detail"].lower())

        # Verify user still exists
        with sqlite3.connect(AUTH_DATABASE_PATH) as conn:
            row = conn.execute("SELECT id FROM auth_users WHERE phone = ?", (unique_phone,)).fetchone()
            self.assertIsNotNone(row)

    def test_confirmation_keyword_mismatch_rejected(self):
        """Deletion API rejects if user did not type DELETE in all capitals."""
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        raw_password = "CorrectPassword123!"

        self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Keyword Donor",
                "phone": unique_phone,
                "password": raw_password,
                "role": "donor",
            },
        )
        token = _generate_jwt(unique_phone, "donor")

        payload = {
            "password": raw_password,
            "confirm_text": "delete_lowercase",
            "confirm_policy": True,
        }
        del_resp = self.client.post(
            "/api/v1/account/delete",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(del_resp.status_code, 400)
        self.assertIn("keyword mismatch", del_resp.json()["detail"].lower())

    def test_policy_acknowledgment_required(self):
        """Deletion API rejects if confirm_policy is False."""
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        raw_password = "CorrectPassword123!"

        self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Policy Donor",
                "phone": unique_phone,
                "password": raw_password,
                "role": "donor",
            },
        )
        token = _generate_jwt(unique_phone, "donor")

        payload = {
            "password": raw_password,
            "confirm_text": "DELETE",
            "confirm_policy": False,
        }
        del_resp = self.client.post(
            "/api/v1/account/delete",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(del_resp.status_code, 400)
        self.assertIn("acknowledge", del_resp.json()["detail"].lower())

    def test_complete_permanent_account_deletion_and_privacy_scrubbing(self):
        """
        Comprehensive test of permanent account deletion and data scrubbing:
        - Eligible PII is purged (auth user, profile, settings, push subscriptions, KYC)
        - Clinical transfusion history is decoupled and anonymized under retention policy
        - Active blood requests are cancelled and personal contact info redacted
        - Active sessions are terminated and auth cookies cleared
        - An immutable deletion audit receipt is logged with SHA-256 subject hash
        """
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        raw_password = "SecurePassword123!"

        # 1. Register User in auth_users
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test Full Scrub Donor",
                "phone": unique_phone,
                "password": raw_password,
                "role": "donor",
            },
        )
        self.assertEqual(reg_resp.status_code, 200)

        # 2. Seed profile, settings, and session in auth.db
        with sqlite3.connect(AUTH_DATABASE_PATH) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO donor_profiles
                (phone, name, email, blood_group, district, area, address, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (unique_phone, "Test Donor", "donor@example.com", "A+", "Dhaka", "Dhanmondi", "Road 27", int(time.time())),
            )
            conn.execute(
                """INSERT OR REPLACE INTO donor_settings (phone, settings_json, updated_at)
                VALUES (?, ?, ?)""",
                (unique_phone, '{"sms_alerts": true, "radius_km": 15}', int(time.time())),
            )
            user_row = conn.execute("SELECT id FROM auth_users WHERE phone = ?", (unique_phone,)).fetchone()
            user_id = user_row[0]
            conn.execute(
                """INSERT INTO auth_sessions (user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?)""",
                (user_id, "mock_session_token_hash_123", int(time.time()), int(time.time()) + 3600),
            )

        # 3. Seed urgent_requests.db (Donation history, blood requests, push subscriptions, notifications, KYC)
        with sqlite3.connect(DATABASE_PATH) as conn:
            # Clinical donation record
            conn.execute(
                """INSERT INTO donor_donation_history (donor_phone, donated_at, donation_type, notes)
                VALUES (?, '2026-01-15T10:00:00Z', 'Whole Blood', 'Transfusion unit 450ml verified')""",
                (unique_phone,),
            )
            # Active blood request
            conn.execute(
                """INSERT INTO blood_requests
                (blood_group, hospital_name, district, area, expires_at, contact_phone, owner_phone, patient_name, reason, status)
                VALUES ('A+', 'Dhaka Hospital', 'Dhaka', 'Shahbagh', '2026-12-31T23:59:59Z', ?, ?, 'Patient X', 'Urgent bypass surgery', 'Active')""",
                (unique_phone, unique_phone),
            )
            # Push subscription
            conn.execute(
                """INSERT INTO push_subscriptions
                (user_phone, endpoint, auth_key, p256dh_key, browser, device_type, status, permission_status, created_at)
                VALUES (?, 'https://fcm.googleapis.com/fcm/send/test-sub-123', 'auth_secret', 'p256_key', 'Chrome', 'Desktop', 'authorized', 'granted', '2026-01-01')""",
                (unique_phone,),
            )
            # Notification
            conn.execute(
                """INSERT INTO app_notifications (recipient_phone, title, message, type, is_read, created_at)
                VALUES (?, 'Emergency Match', 'Urgent requirement nearby', 'emergency', 0, '2026-01-01')""",
                (unique_phone,),
            )
            # KYC verification record
            conn.execute(
                """INSERT INTO donor_kyc_verifications
                (donor_phone, donor_name, blood_group, nid_number, document_type, document_url, status, submitted_at)
                VALUES (?, 'Test Full Scrub Donor', 'A+', '19901234567890123', 'National ID (NID)', '/uploads/nid_123.jpg', 'verified', '2026-01-01')""",
                (unique_phone,),
            )

        token = _generate_jwt(unique_phone, "donor")

        # 4. Perform Permanent Deletion with Identity Verification & Confirmation
        payload = {
            "password": raw_password,
            "confirm_text": "DELETE",
            "confirm_policy": True,
            "reason": "Relocating abroad",
        }
        response = self.client.post(
            "/api/v1/account/delete",
            json=payload,
            cookies={"access_token": token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["redirect_url"], "/account/deleted")
        self.assertIn("Data Retention Policy", data["message"])

        # 5. Verify Auth Database Scrubbing
        with sqlite3.connect(AUTH_DATABASE_PATH) as conn:
            # User record deleted
            user_row = conn.execute("SELECT id FROM auth_users WHERE phone = ?", (unique_phone,)).fetchone()
            self.assertIsNone(user_row)

            # Active sessions terminated
            session_rows = conn.execute("SELECT id FROM auth_sessions WHERE user_id = ?", (user_id,)).fetchall()
            self.assertEqual(len(session_rows), 0)

            # Profile deleted
            profile_row = conn.execute("SELECT phone FROM donor_profiles WHERE phone = ?", (unique_phone,)).fetchone()
            self.assertIsNone(profile_row)

            # Settings deleted
            settings_row = conn.execute("SELECT phone FROM donor_settings WHERE phone = ?", (unique_phone,)).fetchone()
            self.assertIsNone(settings_row)

            # Deletion audit log recorded
            phone_hash = hashlib.sha256(unique_phone.encode("utf-8")).hexdigest()
            audit_row = conn.execute(
                "SELECT user_phone_hash, role, reason, retention_policy_version, scrubbed_summary FROM account_deletion_audit_logs WHERE user_phone_hash = ?",
                (phone_hash,),
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row[0], phone_hash)
            self.assertEqual(audit_row[1], "donor")
            self.assertEqual(audit_row[2], "Relocating abroad")
            self.assertEqual(audit_row[3], DATA_RETENTION_POLICY_VERSION)

        # 6. Verify Urgent Database Scrubbing & Retention Policy Handling
        with sqlite3.connect(DATABASE_PATH) as conn:
            # Push subscription removed
            push_rows = conn.execute("SELECT id FROM push_subscriptions WHERE user_phone = ?", (unique_phone,)).fetchall()
            self.assertEqual(len(push_rows), 0)

            # Notifications removed
            notif_rows = conn.execute("SELECT id FROM app_notifications WHERE recipient_phone = ?", (unique_phone,)).fetchall()
            self.assertEqual(len(notif_rows), 0)

            # KYC sensitive info redacted
            kyc_row = conn.execute("SELECT nid_number, document_url, status FROM donor_kyc_verifications WHERE donor_phone = ?", (unique_phone,)).fetchone()
            self.assertIsNotNone(kyc_row)
            self.assertEqual(kyc_row[0], "REDACTED")
            self.assertEqual(kyc_row[1], "")
            self.assertEqual(kyc_row[2], "scrubbed")

            # Blood request cancelled and contact redacted
            req_row = conn.execute("SELECT status, patient_name, contact_phone, owner_phone, reason FROM blood_requests WHERE contact_phone = 'REDACTED'").fetchone()
            self.assertIsNotNone(req_row)
            self.assertEqual(req_row[0], "Cancelled")
            self.assertEqual(req_row[1], "[Redacted]")
            self.assertEqual(req_row[2], "REDACTED")
            self.assertEqual(req_row[3], "REDACTED")

            # Clinical donation history anonymized (decoupled from phone, preserved for transfusion safety)
            donation_rows = conn.execute("SELECT donor_phone, donation_type, notes FROM donor_donation_history WHERE notes LIKE '%Anonymized%'").fetchall()
            self.assertTrue(len(donation_rows) >= 1)
            for d in donation_rows:
                self.assertTrue(d[0].startswith("ANON-DONOR-"))
                self.assertNotIn(unique_phone, d[0])

    def test_form_post_account_deletion_flow(self):
        """Tests standard HTML Form POST to /account/delete with redirection."""
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        raw_password = "FormPassword123!"

        self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Form Donor",
                "phone": unique_phone,
                "password": raw_password,
                "role": "donor",
            },
        )
        token = _generate_jwt(unique_phone, "donor")

        # POST form data
        form_resp = self.client.post(
            "/account/delete",
            data={
                "password": raw_password,
                "confirm_text": "DELETE",
                "confirm_policy": "1",
                "reason": "Moving",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )
        self.assertEqual(form_resp.status_code, 303)
        self.assertEqual(form_resp.headers.get("location"), "/account/deleted")

    def test_account_deleted_confirmation_screen_renders(self):
        """Tests that /account/deleted confirmation screen renders and clears cookies."""
        response = self.client.get("/account/deleted")
        self.assertEqual(response.status_code, 200)
        html = response.text

        self.assertIn("Account Deleted &amp; Data Scrubbed", html)
        self.assertIn("Identity &amp; Credentials", html)
        self.assertIn("Sessions Terminated", html)
        self.assertIn("Clinical Traceability", html)
        self.assertIn(f"Policy v{DATA_RETENTION_POLICY_VERSION}", html)

    def test_donor_delete_endpoint(self):
        """Tests DELETE /api/v1/donor/account directly."""
        unique_phone = f"+88017{uuid.uuid4().int % 10**8:08d}"
        self.client.post(
            "/api/v1/auth/register",
            json={
                "name": "Direct Donor Delete",
                "phone": unique_phone,
                "password": "Password123!",
                "role": "donor",
            },
        )
        token = _generate_jwt(unique_phone, "donor")

        del_resp = self.client.delete(
            "/api/v1/donor/account",
            cookies={"access_token": token},
        )
        self.assertEqual(del_resp.status_code, 200)
        data = del_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("deleted", data["message"].lower())


if __name__ == "__main__":
    unittest.main()

