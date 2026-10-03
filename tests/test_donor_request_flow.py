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
        self.request_ids = []
        with sqlite3.connect(DATABASE_PATH) as connection:
            for index in range(2):
                cursor = connection.execute(
                    """INSERT INTO blood_requests (
                           blood_group, hospital_name, district, area, distance_km,
                           expires_at, contact_phone, is_emergency
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        "A+",
                        f"Request Flow Test Hospital {index}",
                        "Dhaka",
                        "Dhanmondi",
                        1.0,
                        (datetime.now(timezone.utc) + timedelta(hours=1 + index)).isoformat(),
                        "+8801700000099",
                    ),
                )
                self.request_ids.append(cursor.lastrowid)
        self.addCleanup(self._remove_test_requests)

    def _remove_test_requests(self):
        with sqlite3.connect(DATABASE_PATH) as connection:
            placeholders = ",".join("?" for _ in self.request_ids)
            connection.execute(
                f"DELETE FROM seeker_notifications WHERE request_id IN ({placeholders})",
                self.request_ids,
            )
            connection.execute(
                f"DELETE FROM donor_request_responses WHERE request_id IN ({placeholders})",
                self.request_ids,
            )
            connection.execute(
                f"DELETE FROM blood_requests WHERE id IN ({placeholders})",
                self.request_ids,
            )

    def test_accept_updates_status_and_queues_seeker_notification(self):
        active_requests = self.client.get("/api/v1/requests/urgent").json()
        active_request_ids = {item["id"] for item in active_requests}
        request_id = self.request_ids[0]
        self.assertIn(request_id, active_request_ids)

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
        active_request_ids = {item["id"] for item in active_requests}
        request_id = self.request_ids[1]
        self.assertIn(request_id, active_request_ids)

        response = self.client.post(
            f"/api/v1/donor/requests/{request_id}/respond",
            json={"action": "decline", "reason": "Unavailable"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request_status"], "declined")

    def test_expired_request_cannot_be_answered(self):
        active_requests = self.client.get("/api/v1/requests/urgent").json()
        active_request_ids = {item["id"] for item in active_requests}
        request_id = self.request_ids[0]
        self.assertIn(request_id, active_request_ids)
        original_expiry = next(
            item["expires_at"] for item in active_requests if item["id"] == request_id
        )

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
