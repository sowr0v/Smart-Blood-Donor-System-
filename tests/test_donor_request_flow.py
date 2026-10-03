import sqlite3
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from main import DATABASE_PATH, app, _generate_jwt


class DonorRequestFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.donor_phone = f"+88017{uuid.uuid4().int % 10**9:09d}"
        self.client.cookies.set("access_token", _generate_jwt(self.donor_phone, "donor"))

    def test_accept_updates_status_and_queues_seeker_notification(self):
        active_requests = self.client.get("/api/v1/requests/urgent").json()
        self.assertTrue(active_requests)
        request_id = active_requests[0]["id"]

        response = self.client.post(
            f"/api/v1/donor/requests/{request_id}/respond",
            json={"action": "accept", "eta": "30 mins", "note": "On the way"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["request_status"], "accepted")
        self.assertEqual(data["notification"]["recipient"], "seeker")
        self.assertEqual(data["notification"]["status"], "queued")

        updated_requests = self.client.get("/api/v1/requests/urgent").json()
        updated_request = next(item for item in updated_requests if item["id"] == request_id)
        self.assertEqual(updated_request["response_status"], "accepted")
        with sqlite3.connect(DATABASE_PATH) as connection:
            notification = connection.execute(
                "SELECT response FROM seeker_notifications WHERE request_id = ? AND donor_phone = ?",
                (request_id, self.donor_phone),
            ).fetchone()
        self.assertEqual(notification, ("accept",))

        duplicate = self.client.post(
            f"/api/v1/donor/requests/{request_id}/respond",
            json={"action": "decline"},
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_decline_updates_status(self):
        active_requests = self.client.get("/api/v1/requests/urgent").json()
        self.assertGreaterEqual(len(active_requests), 2)
        request_id = active_requests[1]["id"]

        response = self.client.post(
            f"/api/v1/donor/requests/{request_id}/respond",
            json={"action": "decline", "reason": "Unavailable"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request_status"], "declined")

    def test_expired_request_cannot_be_answered(self):
        active_requests = self.client.get("/api/v1/requests/urgent").json()
        self.assertTrue(active_requests)
        request_id = active_requests[0]["id"]
        original_expiry = active_requests[0]["expires_at"]

        try:
            expired_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute(
                    "UPDATE blood_requests SET expires_at = ? WHERE id = ?",
                    (expired_at, request_id),
                )
            response = self.client.post(
                f"/api/v1/donor/requests/{request_id}/respond",
                json={"action": "accept"},
            )
            self.assertEqual(response.status_code, 409)
        finally:
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute(
                    "UPDATE blood_requests SET expires_at = ? WHERE id = ?",
                    (original_expiry, request_id),
                )
