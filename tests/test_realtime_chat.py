import sqlite3
import unittest
from starlette.websockets import WebSocketDisconnect
from _client import TestClient

from main import DATABASE_PATH, app, _generate_jwt


DONOR_TOKEN = _generate_jwt("+8801712345678", "donor")
SEEKER_TOKEN = _generate_jwt("+8801723456789", "seeker")


class RealtimeChatConnectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.donor_headers = {"cookie": f"access_token={DONOR_TOKEN}"}
        self.seeker_headers = {"cookie": f"access_token={SEEKER_TOKEN}"}

    def test_donor_and_seeker_websocket_connection_and_presence(self):
        with self.client.websocket_connect("/ws/chat/donor", headers=self.donor_headers) as donor_socket:
            donor_init = donor_socket.receive_json()
            self.assertEqual(donor_init["type"], "connection_established")
            self.assertEqual(donor_init["role"], "donor")
            donor_socket.send_json({"action": "ping"})
            self.assertEqual(donor_socket.receive_json()["type"], "pong")

            with self.client.websocket_connect("/ws/chat/seeker", headers=self.seeker_headers) as seeker_socket:
                seeker_init = seeker_socket.receive_json()
                self.assertEqual(seeker_init["type"], "connection_established")
                self.assertEqual(seeker_init["role"], "seeker")
                donor_presence = donor_socket.receive_json()
                self.assertEqual(donor_presence["type"], "presence")
                self.assertEqual(donor_presence["role"], "seeker")
                self.assertEqual(donor_presence["status"], "online")

    def test_bidirectional_messages_persist_and_arrive_in_realtime(self):
        with self.client.websocket_connect("/ws/chat/donor", headers=self.donor_headers) as donor_socket:
            donor_socket.receive_json()
            with self.client.websocket_connect("/ws/chat/seeker", headers=self.seeker_headers) as seeker_socket:
                seeker_socket.receive_json()
                donor_socket.receive_json()

                sent_by_seeker = self.client.post(
                    "/api/v1/seeker/chat/thread-ayesha/send",
                    json={"text": "Please confirm your arrival time."},
                    cookies={"access_token": SEEKER_TOKEN},
                )
                self.assertEqual(sent_by_seeker.status_code, 200)
                self.assertEqual(sent_by_seeker.json()["sent"]["text"], "Please confirm your arrival time.")
                self.assertEqual(seeker_socket.receive_json()["type"], "chat_message")
                donor_event = donor_socket.receive_json()
                self.assertEqual(donor_event["thread_id"], "thread-nabil")
                self.assertIn("Please confirm", donor_event["text"])

                sent_by_donor = self.client.post(
                    "/api/v1/donor/chat/thread-nabil/send",
                    json={"text": "I will be there in 20 minutes."},
                    cookies={"access_token": DONOR_TOKEN},
                )
                self.assertEqual(sent_by_donor.status_code, 200)
                self.assertEqual(donor_socket.receive_json()["type"], "chat_message")
                seeker_event = seeker_socket.receive_json()
                self.assertEqual(seeker_event["thread_id"], "thread-ayesha")
                self.assertIn("20 minutes", seeker_event["text"])

                history = self.client.get(
                    "/api/v1/seeker/chat/thread-ayesha/messages",
                    cookies={"access_token": SEEKER_TOKEN},
                )
                self.assertEqual(history.status_code, 200)
                self.assertEqual(history.json()["messages"][-1]["text"], "I will be there in 20 minutes.")

    def test_typing_indicators_are_scoped_to_conversation_participants(self):
        with self.client.websocket_connect("/ws/chat/donor", headers=self.donor_headers) as donor_socket:
            donor_socket.receive_json()
            with self.client.websocket_connect("/ws/chat/seeker", headers=self.seeker_headers) as seeker_socket:
                seeker_socket.receive_json()
                donor_socket.receive_json()
                seeker_socket.send_json({
                    "action": "typing",
                    "thread_id": "thread-ayesha",
                    "typing": True,
                })
                self.assertEqual(seeker_socket.receive_json()["type"], "typing_sent")
                event = donor_socket.receive_json()
                self.assertEqual(event["type"], "typing")
                self.assertEqual(event["thread_id"], "thread-nabil")
                self.assertTrue(event["typing"])

    def test_chat_requires_authentication_and_conversation_membership(self):
        unauthenticated = TestClient(app)
        self.assertEqual(
            unauthenticated.get("/api/v1/seeker/chat/threads").status_code,
            401,
        )
        other_seeker = TestClient(
            app,
            cookies={"access_token": _generate_jwt("+8801787654321", "seeker")},
        )
        self.assertEqual(
            other_seeker.get("/api/v1/seeker/chat/thread-ayesha/messages").status_code,
            401,
        )
        wrong_role = TestClient(
            app,
            cookies={"access_token": _generate_jwt("+8801723456789", "donor")},
        )
        self.assertEqual(
            wrong_role.get("/api/v1/donor/chat/threads").status_code,
            401,
        )
        with self.assertRaises(WebSocketDisconnect) as disconnect:
            with unauthenticated.websocket_connect("/ws/chat/seeker") as socket:
                socket.receive_json()
        self.assertEqual(disconnect.exception.code, 4401)

    def test_available_donor_list_is_chat_ready_and_does_not_expose_phone(self):
        response = self.client.get(
            "/api/v1/seeker/chat/available-donors",
            cookies={"access_token": SEEKER_TOKEN},
        )
        self.assertEqual(response.status_code, 200)
        donors = response.json()["donors"]
        donors_by_name = {donor["name"]: donor for donor in donors}
        expected_names = {
            "Ayesha Rahman",
            "Tanvir Ahmed",
            "Sadia Islam",
            "Rafiqul Islam",
        }
        self.assertTrue(expected_names.issubset(donors_by_name))
        self.assertTrue(all("phone" not in donor for donor in donors))

        with sqlite3.connect(DATABASE_PATH) as connection:
            existing_threads = {
                row[0] for row in connection.execute("SELECT id FROM chat_threads")
            }
        created_threads = []
        try:
            for name in expected_names:
                start_response = self.client.post(
                    "/api/v1/seeker/chat/conversations",
                    json={"donor_id": donors_by_name[name]["id"]},
                    cookies={"access_token": SEEKER_TOKEN},
                )
                self.assertEqual(start_response.status_code, 200, name)
                thread = start_response.json()["thread"]
                self.assertEqual(thread["name"], name)
                if thread["id"] not in existing_threads:
                    created_threads.append(thread["id"])
        finally:
            with sqlite3.connect(DATABASE_PATH) as connection:
                for thread_id in created_threads:
                    connection.execute(
                        "DELETE FROM chat_messages WHERE thread_id = ?",
                        (thread_id,),
                    )
                    connection.execute(
                        "DELETE FROM chat_threads WHERE id = ?",
                        (thread_id,),
                    )

    def test_report_and_restrict_actions_apply_server_side_rules(self):
        try:
            report_response = self.client.post(
                "/api/v1/seeker/chat/thread-ayesha/report",
                json={"reason": "safety", "details": "Test report"},
                cookies={"access_token": SEEKER_TOKEN},
            )
            self.assertEqual(report_response.status_code, 200)
            self.assertEqual(report_response.json()["status"], "success")

            block_response = self.client.post(
                "/api/v1/seeker/chat/thread-ayesha/block",
                cookies={"access_token": SEEKER_TOKEN},
            )
            self.assertEqual(block_response.status_code, 200)
            restricted_send = self.client.post(
                "/api/v1/donor/chat/thread-nabil/send",
                json={"text": "This must not be delivered."},
                cookies={"access_token": DONOR_TOKEN},
            )
            self.assertEqual(restricted_send.status_code, 403)
        finally:
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute(
                    """DELETE FROM chat_blocks
                       WHERE blocker_phone = ? AND blocked_phone = ?""",
                    ("+8801723456789", "+8801712345678"),
                )
                connection.execute(
                    "DELETE FROM chat_reports WHERE reporter_phone = ?",
                    ("+8801723456789",),
                )
