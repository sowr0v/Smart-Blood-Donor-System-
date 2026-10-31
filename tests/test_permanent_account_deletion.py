import time
import uuid
import unittest
from contextlib import closing
import sqlite3

from _client import TestClient
from main import (
    app,
    _generate_jwt,
    hash_password,
    initialize_auth_database,
    initialize_urgent_database,
    AUTH_DATABASE_PATH,
    DATABASE_PATH,
    USERS,
    _connection,
)


class PermanentAccountDeletionTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_auth_database()
        initialize_urgent_database()

    def _create_test_user(self, phone: str, password: str, name: str = "Test Donor", role: str = "donor") -> int:
        now = int(time.time())
        pw_hash = hash_password(password)
        with closing(_connection()) as conn:
            with conn:
                # Remove existing if any
                conn.execute("DELETE FROM auth_users WHERE phone = ?", (phone,))
                conn.execute("DELETE FROM donor_profiles WHERE phone = ?", (phone,))
                cur = conn.execute(
                    """INSERT INTO auth_users (phone, password_hash, role, name, email, address, district, area, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                    (phone, pw_hash, role, name, f"{phone.replace('+', '')}@example.com", "123 Test Street", "Dhaka", "Dhanmondi", now, now),
                )
                user_id = cur.lastrowid

                # Add profile
                conn.execute(
                    """INSERT OR REPLACE INTO donor_profiles (phone, name, email, blood_group, district, area, address, fitness_status, is_available, updated_at)
                       VALUES (?, ?, ?, 'O+', 'Dhaka', 'Dhanmondi', '123 Test Street', 'Eligible', 1, ?)""",
                    (phone, name, f"{phone.replace('+', '')}@example.com", now),
                )

                # Add session
                conn.execute(
                    """INSERT INTO auth_sessions (user_id, token_hash, created_at, expires_at)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, f"test_session_hash_{phone}", now, now + 86400),
                )
                return user_id

    def test_deletion_fails_when_unauthenticated(self):
        response = self.client.post(
            "/api/user/delete-account",
            json={"password": "anyPassword123!"},
        )
        self.assertEqual(response.status_code, 401)

    def test_deletion_fails_with_incorrect_password(self):
        phone = "+8801799990001"
        self._create_test_user(phone, "CorrectPassword123!", "Alice Donor")
        token = _generate_jwt(phone, "donor")

        response = self.client.post(
            "/api/user/delete-account",
            cookies={"access_token": token},
            json={"password": "WrongPassword999!"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Incorrect password", response.json().get("detail", ""))

        # Verify user still active and PII intact
        with closing(_connection()) as conn:
            row = conn.execute("SELECT * FROM auth_users WHERE phone = ?", (phone,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "Alice Donor")
            self.assertEqual(row["status"], "active")

    def test_deletion_succeeds_and_scrubs_pii(self):
        phone = "+8801799990002"
        user_id = self._create_test_user(phone, "SecretKey1234!", "Dr. Robert Smith")
        token = _generate_jwt(phone, "donor")

        response = self.client.post(
            "/api/user/delete-account",
            cookies={"access_token": token},
            json={
                "password": "SecretKey1234!",
                "confirmation": "DELETE",
                "reason": "Moving abroad",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("scrubbed_id", data)
        self.assertIn("/login?account_deleted=1", data.get("redirect_url", ""))

        with closing(_connection()) as conn:
            # 1. Original phone must no longer exist in auth_users
            original_row = conn.execute("SELECT * FROM auth_users WHERE phone = ?", (phone,)).fetchone()
            self.assertIsNone(original_row)

            # 2. Record by ID must have PII scrubbed
            scrubbed_row = conn.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone()
            self.assertIsNotNone(scrubbed_row)
            self.assertTrue(scrubbed_row["name"].startswith("[Scrubbed Donor - ID:"))
            self.assertEqual(scrubbed_row["status"], "permanently_deleted")
            self.assertEqual(scrubbed_row["address"], "[Purged]")
            self.assertEqual(scrubbed_row["district"], "")
            self.assertEqual(scrubbed_row["area"], "")
            self.assertNotIn("Dr. Robert Smith", scrubbed_row["name"])
            self.assertNotIn("example.com", scrubbed_row["email"])

            # 3. Donor profile must be purged
            profile = conn.execute("SELECT * FROM donor_profiles WHERE phone = ?", (phone,)).fetchone()
            self.assertIsNone(profile)

    def test_operational_records_preserved_anonymously(self):
        phone = "+8801799990003"
        user_id = self._create_test_user(phone, "MedHistoryPass123!", "Fatima Begum")
        token = _generate_jwt(phone, "donor")

        now = int(time.time())
        # Add a blood request and 2 completed donations for Fatima in operational DB
        with closing(sqlite3.connect(DATABASE_PATH)) as u_conn:
            with u_conn:
                u_conn.execute("DELETE FROM donor_donation_history WHERE donor_phone = ?", (phone,))
                req_cur = u_conn.execute(
                    """INSERT INTO blood_requests (
                           blood_group, hospital_name, district, area, distance_km,
                           expires_at, contact_phone, is_emergency
                       ) VALUES ('B+', 'Square Hospital', 'Dhaka', 'Panthapath', 1.5, '2026-12-31', '+8801700000000', 0)"""
                )
                req_id = req_cur.lastrowid
                u_conn.execute(
                    """INSERT INTO donor_donation_history
                       (donor_phone, request_id, donated_at, donation_type, notes)
                       VALUES (?, ?, '2026-03-10', 'Whole Blood', 'Completed 450mL donation at Square Hospital')""",
                    (phone, req_id),
                )
                u_conn.execute(
                    """INSERT INTO donor_donation_history
                       (donor_phone, request_id, donated_at, donation_type, notes)
                       VALUES (?, ?, '2026-07-22', 'Plasma', 'Completed apheresis donation at DMCH')""",
                    (phone, None),
                )

        # Execute deletion
        response = self.client.post(
            "/api/user/delete-account",
            cookies={"access_token": token},
            json={"password": "MedHistoryPass123!", "confirmation": "DELETE"},
        )
        self.assertEqual(response.status_code, 200)
        scrubbed_id = response.json()["scrubbed_id"]

        # Verify operational medical records are preserved but anonymized
        with closing(sqlite3.connect(DATABASE_PATH)) as u_conn:
            # No donations remain attached to original phone
            donations_by_old_phone = u_conn.execute(
                "SELECT * FROM donor_donation_history WHERE donor_phone = ?",
                (phone,),
            ).fetchall()
            self.assertEqual(len(donations_by_old_phone), 0)

            # Both donations are preserved under the scrubbed_id
            donations_by_scrubbed_id = u_conn.execute(
                "SELECT * FROM donor_donation_history WHERE donor_phone = ? ORDER BY id ASC",
                (scrubbed_id,),
            ).fetchall()
            self.assertEqual(len(donations_by_scrubbed_id), 2)

            d1 = dict(donations_by_scrubbed_id[0]) if hasattr(donations_by_scrubbed_id[0], 'keys') else {
                "id": donations_by_scrubbed_id[0][0],
                "donor_phone": donations_by_scrubbed_id[0][1],
                "request_id": donations_by_scrubbed_id[0][2],
                "donated_at": donations_by_scrubbed_id[0][3],
                "donation_type": donations_by_scrubbed_id[0][4],
                "notes": donations_by_scrubbed_id[0][5],
            }
            self.assertEqual(d1["donated_at"], "2026-03-10")
            self.assertEqual(d1["donation_type"], "Whole Blood")

            d2 = dict(donations_by_scrubbed_id[1]) if hasattr(donations_by_scrubbed_id[1], 'keys') else {
                "id": donations_by_scrubbed_id[1][0],
                "donor_phone": donations_by_scrubbed_id[1][1],
                "request_id": donations_by_scrubbed_id[1][2],
                "donated_at": donations_by_scrubbed_id[1][3],
                "donation_type": donations_by_scrubbed_id[1][4],
                "notes": donations_by_scrubbed_id[1][5],
            }
            self.assertEqual(d2["donated_at"], "2026-07-22")
            self.assertEqual(d2["donation_type"], "Plasma")

    def test_session_invalidation_and_confirmation(self):
        phone = "+8801799990004"
        user_id = self._create_test_user(phone, "SessionSecurePass1!", "Tanvir Ahmed")
        token = _generate_jwt(phone, "donor")

        # Execute deletion
        response = self.client.post(
            "/donor/delete-account",
            cookies={"access_token": token},
            json={"password": "SessionSecurePass1!", "confirmation": "DELETE"},
        )
        self.assertEqual(response.status_code, 200)

        # Verify sessions in DB are cleared
        with closing(_connection()) as conn:
            sessions = conn.execute("SELECT * FROM auth_sessions WHERE user_id = ?", (user_id,)).fetchall()
            self.assertEqual(len(sessions), 0)

        # Verify session cookies are invalidated (deleted)
        cookies = response.cookies
        # Check set-cookie header or cookie jar for expiry / clearing
        set_cookie_header = response.headers.get("set-cookie", "")
        self.assertTrue(
            'access_token=""' in set_cookie_header or 'access_token=;' in set_cookie_header or 'Max-Age=0' in set_cookie_header
        )

    def test_admin_scrubbed_accounts_audit_endpoint(self):
        admin_token = _generate_jwt("+8801745678901", "admin")
        response = self.client.get(
            "/api/v1/admin/scrubbed-accounts",
            cookies={"access_token": admin_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("scrubbed_accounts", data)

    def test_ui_routes_and_danger_zone_elements(self):
        donor_token = _generate_jwt("+8801712345678", "donor")

        # 1. Test /donor/settings redirects to /donor/dashboard#section-settings
        settings_resp = self.client.get(
            "/donor/settings",
            cookies={"access_token": donor_token},
            follow_redirects=False,
        )
        self.assertEqual(settings_resp.status_code, 303)
        self.assertIn("#section-settings", settings_resp.headers.get("location", ""))

        # 2. Test /account-deletion page renders
        del_page_resp = self.client.get(
            "/account-deletion",
            cookies={"access_token": donor_token},
        )
        self.assertEqual(del_page_resp.status_code, 200)
        del_html = del_page_resp.text
        self.assertIn("Permanent Account Deletion &amp; Data Privacy Scrubbing", del_html)
        self.assertIn("Data Retention &amp; Privacy Scrubbing Policy", del_html)
        self.assertIn("btnOpenDeletionModal", del_html)
        self.assertIn("accountDeletionModal", del_html)
        self.assertIn("deletePassword", del_html)

        # 3. Test donor dashboard renders danger zone card and modal
        dash_resp = self.client.get(
            "/donor/dashboard?preview=1",
            cookies={"access_token": donor_token},
        )
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.text
        self.assertIn('id="dangerZoneDonorSection"', dash_html)
        self.assertIn('id="btnOpenDonorDeleteModal"', dash_html)
        self.assertIn('id="donorDeleteAccountModal"', dash_html)
        self.assertIn('id="donorDeletePassword"', dash_html)
        self.assertIn('id="donorDeleteConfirm"', dash_html)


if __name__ == "__main__":
    unittest.main()
