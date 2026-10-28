import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt
from admin_portal import initialize_admin_and_notification_database


class AdminKycQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        initialize_admin_and_notification_database()
        self.admin_token = _generate_jwt("+8801745678901", "admin")
        self.donor_token = _generate_jwt("+8801712345678", "donor")

    def test_admin_dashboard_renders_kyc_section_and_modal(self):
        response = self.client.get(
            "/admin/dashboard",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="section-kyc"', html)
        self.assertIn('id="kycTableBody"', html)
        self.assertIn('id="kycPendingCountBadge"', html)
        self.assertIn('id="kycApprovedCountBadge"', html)
        self.assertIn('id="kycReviewModal"', html)
        self.assertIn('id="kycModalTitle"', html)
        self.assertIn('id="kycDonorName"', html)
        self.assertIn('id="kycDonorPhone"', html)
        self.assertIn('id="kycBloodGroup"', html)
        self.assertIn('id="kycDocType"', html)
        self.assertIn('id="kycNidNumber"', html)
        self.assertIn('id="kycSubmissionDate"', html)
        self.assertIn('id="kycDocPreview"', html)

    def test_get_kyc_queue_pending(self):
        response = self.client.get(
            "/api/v1/admin/kyc/queue?status=pending",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("queue", data)
        self.assertIn("kyc_requests", data)
        self.assertIn("counts", data)
        self.assertIn("pending_count", data)

    def test_get_kyc_queue_all(self):
        response = self.client.get(
            "/api/v1/admin/kyc/queue?status=all",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["queue"]), 1)

    def test_get_kyc_detail_and_review(self):
        # 1. Get queue to find an item
        queue_resp = self.client.get(
            "/api/v1/admin/kyc/queue?status=all",
            cookies={"access_token": self.admin_token},
        )
        queue_data = queue_resp.json()
        items = queue_data["queue"]
        self.assertGreater(len(items), 0)
        item_id = items[0]["id"]

        # 2. Get detail
        detail_resp = self.client.get(
            f"/api/v1/admin/kyc/{item_id}",
            cookies={"access_token": self.admin_token},
        )
        self.assertEqual(detail_resp.status_code, 200)
        detail_data = detail_resp.json()
        self.assertEqual(detail_data["status"], "success")
        self.assertIn("record", detail_data)
        self.assertIn("kyc", detail_data)
        self.assertEqual(detail_data["kyc"]["id"], item_id)

        # 3. Review decision (approve)
        review_resp = self.client.post(
            f"/api/v1/admin/kyc/{item_id}/review",
            cookies={"access_token": self.admin_token},
            json={
                "action": "approve",
                "reason": "All documents verified successfully.",
                "reviewer_name": "System Admin",
            },
        )
        self.assertEqual(review_resp.status_code, 200)
        self.assertEqual(review_resp.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
