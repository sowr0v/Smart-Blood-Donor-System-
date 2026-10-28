import unittest
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app, _generate_jwt
from admin_portal import (
    calculate_duplicate_risk,
    evaluate_suspicious_content,
    DATABASE_PATH,
    AUTH_DATABASE_PATH,
    initialize_admin_and_notification_database,
)


class AdminBloodRequestModerationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_token = _generate_jwt("+8801745678901", "admin")
        self.donor_token = _generate_jwt("+8801712345678", "donor")
        self.admin_cookies = {"access_token": self.admin_token}
        self.donor_cookies = {"access_token": self.donor_token}
        initialize_admin_and_notification_database()

    def test_admin_dashboard_renders_moderation_screen_and_components(self):
        """Acceptance Criteria: Blood requests can be reviewed on administrator screen."""
        response = self.client.get("/admin/dashboard", cookies=self.admin_cookies)
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("section-requests", html)
        self.assertIn("moderationRequestsTableBody", html)
        self.assertIn("moderationStatusFilter", html)
        self.assertIn("moderationUrgencyFilter", html)
        self.assertIn("moderationRiskFilter", html)
        self.assertIn("moderationSearchInput", html)
        self.assertIn("duplicateInspectionModal", html)
        self.assertIn("statusUpdateModal", html)
        self.assertIn("requestHistoryModal", html)
        self.assertIn("nav-item-requests", html)

    def test_admin_requests_route_redirects_to_moderation_section(self):
        """Verifies dedicated admin request routes redirect to section-requests."""
        for path in ["/admin/requests", "/admin/moderation"]:
            resp = self.client.get(path, cookies=self.admin_cookies, follow_redirects=False)
            self.assertEqual(resp.status_code, 303)
            self.assertIn("/admin/dashboard#requests", resp.headers.get("location"))

    def test_unauthenticated_requests_route_redirects_to_login(self):
        """Unauthenticated requests route redirects to login console."""
        resp = self.client.get("/admin/requests", follow_redirects=False)
        self.assertEqual(resp.status_code, 303)
        self.assertIn("/admin/login", resp.headers.get("location"))

    def test_get_requests_for_moderation_api_returns_stats_and_requests(self):
        """Acceptance Criteria: Blood requests can be reviewed via moderation API."""
        resp = self.client.get("/api/v1/admin/requests/moderation", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("total", data)
        self.assertIn("stats", data)
        self.assertIn("requests", data)

        stats = data["stats"]
        self.assertIn("total_requests", stats)
        self.assertIn("flagged_count", stats)
        self.assertIn("duplicate_count", stats)
        self.assertIn("high_risk_count", stats)
        self.assertIn("approved_count", stats)
        self.assertIn("active_count", stats)

        # Ensure enriched fields are present
        if data["requests"]:
            sample = data["requests"][0]
            self.assertIn("duplicate_risk", sample)
            self.assertIn("duplicate_label", sample)
            self.assertIn("duplicate_candidates", sample)
            self.assertIn("is_suspicious", sample)
            self.assertIn("moderation_status", sample)

    def test_duplicate_detection_heuristic_scoring(self):
        """Acceptance Criteria: Multi-factor duplicate request identification and risk scores."""
        all_reqs = [
            {
                "id": 101,
                "blood_group": "A+",
                "hospital_name": "Dhaka Medical College Hospital",
                "patient_name": "Shahidul Alam",
                "contact_phone": "+8801711223344",
                "area": "Shahbagh",
            },
            {
                "id": 102,
                "blood_group": "A+",
                "hospital_name": "Dhaka Medical College Hospital",
                "patient_name": "Shahidul Alam",
                "contact_phone": "01711223344",  # normalized phone match (+65%) + hosp (+30%) + patient (+45%)
                "area": "Shahbagh",
            },
            {
                "id": 103,
                "blood_group": "B-",
                "hospital_name": "Square Hospital",
                "patient_name": "Farhana Begum",
                "contact_phone": "+8801799887766",
                "area": "Panthapath",
            },
        ]

        # Target 102 should be identified as high risk duplicate of 101
        score, label, candidates = calculate_duplicate_risk(
            102, "01711223344", "Dhaka Medical College Hospital", "A+", "Shahidul Alam", "Shahbagh", all_reqs
        )
        self.assertGreaterEqual(score, 70.0)
        self.assertEqual(label, "High Risk Duplicate")
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["request_id"], 101)
        self.assertGreaterEqual(candidates[0]["risk_score"], 70.0)

        # Target 103 should be evaluated as unique / low risk
        score_103, label_103, candidates_103 = calculate_duplicate_risk(
            103, "+8801799887766", "Square Hospital", "B-", "Farhana Begum", "Panthapath", all_reqs
        )
        self.assertLess(score_103, 35.0)
        self.assertEqual(label_103, "Unique / Low Risk")

    def test_evaluate_suspicious_content(self):
        """Acceptance Criteria: Suspicious or inappropriate requests can be identified."""
        suspicious_req = {
            "patient_name": "John Doe",
            "reason": "Need blood urgent send bKash advance money",
            "hospital_name": "General Hospital",
            "units": 15,  # abnormal volume
        }
        is_susp, reasons = evaluate_suspicious_content(suspicious_req)
        self.assertTrue(is_susp)
        self.assertTrue(any("commercial" in r.lower() or "bkash" in r.lower() for r in reasons))
        self.assertTrue(any("volume" in r.lower() or "units" in r.lower() for r in reasons))

        clean_req = {
            "patient_name": "Nusrat Jahan",
            "reason": "Emergency caesarean operation scheduled",
            "hospital_name": "Dhaka Medical College",
            "units": 2,
        }
        clean_susp, clean_reasons = evaluate_suspicious_content(clean_req)
        self.assertFalse(clean_susp)
        self.assertEqual(len(clean_reasons), 0)

    def test_flag_suspicious_request(self):
        """Acceptance Criteria: Suspicious or duplicate requests can be flagged."""
        # Find or ensure a request exists
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()
            req_id = row[0]

        response = self.client.post(
            f"/api/v1/admin/requests/{req_id}/moderate",
            json={"action": "flag", "notes": "Suspicious contact information provided"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["moderation_status"], "flagged")

        # Verify in database
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            status_row = conn.execute("SELECT moderation_status FROM blood_requests WHERE id = ?", (req_id,)).fetchone()
            self.assertEqual(status_row[0], "flagged")

    def test_mark_request_as_duplicate(self):
        """Acceptance Criteria: Administrators can mark a request as duplicate."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            rows = conn.execute("SELECT id FROM blood_requests ORDER BY id LIMIT 2").fetchall()
            target_id = rows[1][0]
            canonical_id = rows[0][0]

        response = self.client.post(
            f"/api/v1/admin/requests/{target_id}/moderate",
            json={"action": "duplicate", "duplicate_of_id": canonical_id, "notes": f"Duplicate of #{canonical_id}"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["moderation_status"], "duplicate")
        self.assertEqual(data["new_status"], "Closed")

        # Verify in database
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            row = conn.execute("SELECT moderation_status, status, duplicate_of_id FROM blood_requests WHERE id = ?", (target_id,)).fetchone()
            self.assertEqual(row[0], "duplicate")
            self.assertEqual(row[1], "Closed")
            self.assertEqual(row[2], canonical_id)

    def test_approve_moderated_request(self):
        """Acceptance Criteria: Administrators can take moderation actions (Approve)."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            req_id = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()[0]

        response = self.client.post(
            f"/api/v1/admin/requests/{req_id}/moderate",
            json={"action": "approve", "notes": "Verified genuine request"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["moderation_status"], "approved")
        self.assertEqual(data["new_status"], "Active")

    def test_update_request_status_api(self):
        """Acceptance Criteria: Request status can be updated."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            req_id = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()[0]

        # Update to Fulfilled
        resp = self.client.post(
            f"/api/v1/admin/requests/{req_id}/status",
            json={"status": "Fulfilled", "reason": "Patient received 2 units from donor"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["status_value"], "Fulfilled")

        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            status_val = conn.execute("SELECT status FROM blood_requests WHERE id = ?", (req_id,)).fetchone()[0]
            self.assertEqual(status_val, "Fulfilled")

        # Reset back to Active
        resp2 = self.client.post(
            f"/api/v1/admin/requests/{req_id}/status",
            json={"status": "Active", "reason": "Re-activated"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(resp2.status_code, 200)

    def test_moderation_actions_are_recorded_in_history_and_audit(self):
        """Acceptance Criteria: Moderation actions are recorded."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            req_id = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()[0]

        test_notes = "Flagged due to anomalous location and urgency mismatch"
        # Perform moderation action
        self.client.post(
            f"/api/v1/admin/requests/{req_id}/moderate",
            json={"action": "flag", "notes": test_notes},
            cookies=self.admin_cookies,
        )

        # Retrieve request history
        history_resp = self.client.get(f"/api/v1/admin/requests/{req_id}/history", cookies=self.admin_cookies)
        self.assertEqual(history_resp.status_code, 200)
        history_data = history_resp.json()
        self.assertEqual(history_data["status"], "success")
        self.assertGreater(history_data["total"], 0)

        # Verify entry details
        latest = history_data["history"][0]
        self.assertEqual(latest["request_id"], req_id)
        self.assertEqual(latest["action"], "flag")
        self.assertIn("+8801745678901", latest["admin_phone"])
        self.assertIn("System Admin", latest["admin_name"])
        self.assertEqual(latest["notes"], test_notes)
        self.assertTrue(bool(latest["created_at"]))

        # Verify central admin audit log also received a record
        with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as a_conn:
            audit_row = a_conn.execute(
                "SELECT * FROM admin_audit_logs WHERE target = ? ORDER BY id DESC LIMIT 1",
                (f"Request #{req_id}",),
            ).fetchone()
            self.assertIsNotNone(audit_row)

    def test_inspect_duplicate_candidates_endpoint(self):
        """Acceptance Criteria: Duplicate request indicators and candidate breakdown are displayed."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            req_id = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()[0]

        resp = self.client.get(f"/api/v1/admin/requests/{req_id}/duplicates", cookies=self.admin_cookies)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("target_request", data)
        self.assertIn("duplicate_risk", data)
        self.assertIn("risk_label", data)
        self.assertIn("candidates", data)

    def test_filtering_requests_by_filters(self):
        """Verifies filtering by status, urgency, risk level, and search."""
        # 1. Filter by status
        resp_flagged = self.client.get("/api/v1/admin/requests/moderation?status=flagged", cookies=self.admin_cookies)
        self.assertEqual(resp_flagged.status_code, 200)

        # 2. Filter by urgency
        resp_crit = self.client.get("/api/v1/admin/requests/moderation?urgency=critical", cookies=self.admin_cookies)
        self.assertEqual(resp_crit.status_code, 200)

        # 3. Filter by duplicate risk
        resp_risk = self.client.get("/api/v1/admin/requests/moderation?risk_level=high", cookies=self.admin_cookies)
        self.assertEqual(resp_risk.status_code, 200)

        # 4. Search filter
        resp_search = self.client.get("/api/v1/admin/requests/moderation?search=Hospital", cookies=self.admin_cookies)
        self.assertEqual(resp_search.status_code, 200)

    def test_invalid_action_returns_422(self):
        """Verifies validation error on unsupported moderation action."""
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            req_id = conn.execute("SELECT id FROM blood_requests LIMIT 1").fetchone()[0]

        resp = self.client.post(
            f"/api/v1/admin/requests/{req_id}/moderate",
            json={"action": "unknown_action"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nonexistent_request_returns_404(self):
        """Verifies 404 for invalid request id."""
        resp = self.client.post(
            "/api/v1/admin/requests/999999/moderate",
            json={"action": "approve"},
            cookies=self.admin_cookies,
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

