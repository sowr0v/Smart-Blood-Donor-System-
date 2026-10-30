import unittest
from _client import TestClient
from main import app, _generate_jwt, USERS
from admin_portal import initialize_admin_and_notification_database


class AdminUserManagementTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_admin_and_notification_database()
        self.admin_phone = "+8801745678901"
        self.admin_token = _generate_jwt(self.admin_phone, "admin")
        self.client.cookies.set("access_token", self.admin_token)

        self.donor_phone = "+8801712345678"
        self.donor_token = _generate_jwt(self.donor_phone, "donor")

    def test_unauthorized_user_cannot_access_admin_api(self):
        non_admin_client = TestClient(app)
        non_admin_client.cookies.set("access_token", self.donor_token)

        response = non_admin_client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Administrative privileges required", response.json()["detail"])

    def test_unauthenticated_user_cannot_access_admin_api(self):
        unauth_client = TestClient(app)
        response = unauth_client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Sign in as an administrator", response.json()["detail"])

    def test_admin_dashboard_renders_for_admin(self):
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("User Management &amp; Role Control", response.text)
        self.assertIn("Security &amp; Administrative Audit Trail", response.text)

    def test_admin_can_search_and_list_users(self):
        response = self.client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["users"], list)
        self.assertGreaterEqual(len(data["users"]), 1)
        self.assertIn("metrics", data)

        # Search test
        search_res = self.client.get("/api/v1/admin/users?query=Ayesha")
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()["users"]
        self.assertTrue(any("Ayesha" in u["name"] for u in results))

        # Role filter test
        role_res = self.client.get("/api/v1/admin/users?role=donor")
        self.assertEqual(role_res.status_code, 200)
        donor_results = role_res.json()["users"]
        self.assertTrue(all(u["role"] == "donor" for u in donor_results))

    def test_admin_can_view_single_user_dossier(self):
        response = self.client.get(f"/api/v1/admin/users/{self.donor_phone}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["phone"], self.donor_phone)
        self.assertIn("audit_history", data)

        # Non-existent user test
        missing_res = self.client.get("/api/v1/admin/users/+8801700000000")
        self.assertEqual(missing_res.status_code, 404)

    def test_admin_can_modify_user_role_and_audit_is_recorded(self):
        # Update donor to seeker
        payload = {"role": "seeker", "reason": "User requested role switch"}
        response = self.client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "seeker")

        # Verify audit logs recorded this
        audit_res = self.client.get("/api/v1/admin/audit-logs")
        self.assertEqual(audit_res.status_code, 200)
        logs = audit_res.json()["logs"]
        role_logs = [l for l in logs if l.get("target_phone") == self.donor_phone and l["action"] == "ROLE_MODIFIED"]
        self.assertTrue(len(role_logs) > 0)
        self.assertIn("User requested role switch", role_logs[0]["details"])

        # Switch back to donor
        restore_payload = {"role": "donor", "reason": "Restoring original test role"}
        self.client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=restore_payload)

    def test_admin_prevented_from_demoting_self(self):
        payload = {"role": "donor", "reason": "Accidental self demotion"}
        response = self.client.put(f"/api/v1/admin/users/{self.admin_phone}/role", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot demote their own account", response.json()["detail"])

    def test_admin_can_modify_status_and_suspended_user_cannot_login(self):
        target_phone = "+8801723456789"  # seeker Nabil
        
        # Suspend user
        suspend_payload = {"status": "suspended", "reason": "Policy violation test"}
        res = self.client.put(f"/api/v1/admin/users/{target_phone}/status", json=suspend_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["status"], "suspended")

        # Try logging in with suspended user credentials via web form
        login_client = TestClient(app)
        login_res = login_client.post(
            "/login",
            data={"phone_number": target_phone, "password": "match123"},
            follow_redirects=False,
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("suspended", login_res.text.lower())

        # Try logging in via JSON API
        api_login_res = login_client.post(
            "/api/v1/auth/login",
            json={"phone": target_phone, "password": "match123"},
        )
        self.assertEqual(api_login_res.status_code, 403)
        self.assertIn("suspended", api_login_res.json()["detail"].lower())

        # Reactivate user
        activate_payload = {"status": "active", "reason": "Appeal accepted"}
        activate_res = self.client.put(f"/api/v1/admin/users/{target_phone}/status", json=activate_payload)
        self.assertEqual(activate_res.status_code, 200)
        self.assertEqual(activate_res.json()["user"]["status"], "active")

    def test_admin_prevented_from_suspending_self(self):
        payload = {"status": "suspended", "reason": "Lockout test"}
        response = self.client.put(f"/api/v1/admin/users/{self.admin_phone}/status", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot suspend their own account", response.json()["detail"])

    def test_admin_can_create_new_user(self):
        test_new_phone = "+8801755112233"
        payload = {
            "phone": test_new_phone,
            "name": "Audit New User",
            "role": "hospital",
            "blood_group": "B+",
            "status": "active",
            "password": "Password12345",
        }
        res = self.client.post("/api/v1/admin/users", json=payload)
        if res.status_code == 200:
            self.assertEqual(res.json()["status"], "success")
            self.assertEqual(res.json()["user"]["role"], "hospital")
        else:
            self.assertEqual(res.status_code, 409)

        # Duplicate creation returns 409
        dup_res = self.client.post("/api/v1/admin/users", json=payload)
        self.assertEqual(dup_res.status_code, 409)

    def test_non_admin_cannot_modify_roles_or_privilege_escalate(self):
        non_admin_client = TestClient(app)
        non_admin_client.cookies.set("access_token", self.donor_token)

        # Non-admin trying to grant themselves admin role
        payload = {"role": "admin", "reason": "Privilege escalation attempt"}
        response = non_admin_client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Administrative privileges required", response.json()["detail"])

        # Non-admin trying to change another user's status
        status_payload = {"status": "suspended", "reason": "Unauthorized suspension"}
        res2 = non_admin_client.put(f"/api/v1/admin/users/+8801723456789/status", json=status_payload)
        self.assertEqual(res2.status_code, 403)

    def test_invalid_role_and_status_rejected(self):
        # Invalid role
        bad_role_payload = {"role": "superman", "reason": "Invalid role test"}
        res1 = self.client.put(f"/api/v1/admin/users/{self.donor_phone}/role", json=bad_role_payload)
        self.assertEqual(res1.status_code, 422)

        # Invalid status
        bad_status_payload = {"status": "destroyed", "reason": "Invalid status test"}
        res2 = self.client.put(f"/api/v1/admin/users/{self.donor_phone}/status", json=bad_status_payload)
        self.assertEqual(res2.status_code, 422)

    def test_update_user_profile_admin(self):
        payload = {
            "name": "Ayesha Rahman Updated",
            "blood_group": "O+",
            "district": "Chittagong",
            "status": "active",
        }
        res = self.client.put(f"/api/v1/admin/users/{self.donor_phone}", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        # Verify through dossier endpoint
        dossier_res = self.client.get(f"/api/v1/admin/users/{self.donor_phone}")
        self.assertEqual(dossier_res.status_code, 200)
        self.assertEqual(dossier_res.json()["user"]["name"], "Ayesha Rahman Updated")
        self.assertEqual(dossier_res.json()["user"]["district"], "Chittagong")

        # Restore name
        restore_payload = {"name": "Ayesha Rahman", "district": "Dhaka"}
        self.client.put(f"/api/v1/admin/users/{self.donor_phone}", json=restore_payload)


if __name__ == "__main__":
    unittest.main()
