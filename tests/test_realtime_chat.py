import unittest
from fastapi.testclient import TestClient

from main import app, _generate_jwt


class RealtimeChatConnectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_donor_and_seeker_websocket_connection_and_presence(self):
        # 1. Connect donor websocket
        with self.client.websocket_connect("/ws/chat/donor") as ws_donor:
            donor_init = ws_donor.receive_json()
            self.assertEqual(donor_init["type"], "connection_established")
            self.assertEqual(donor_init["role"], "donor")

            # Test ping/pong
            ws_donor.send_json({"action": "ping"})
            pong = ws_donor.receive_json()
            self.assertEqual(pong["type"], "pong")

            # 2. Connect seeker websocket while donor is connected
            with self.client.websocket_connect("/ws/chat/seeker") as ws_seeker:
                seeker_init = ws_seeker.receive_json()
                self.assertEqual(seeker_init["type"], "connection_established")
                self.assertEqual(seeker_init["role"], "seeker")

                # Donor should have received presence of seeker
                donor_received = ws_donor.receive_json()
                self.assertEqual(donor_received["type"], "presence")
                self.assertEqual(donor_received["role"], "seeker")
                self.assertEqual(donor_received["status"], "online")

    def test_bidirectional_realtime_chat_bridge(self):
        with self.client.websocket_connect("/ws/chat/donor") as ws_donor:
            ws_donor.receive_json()  # connection_established

            with self.client.websocket_connect("/ws/chat/seeker") as ws_seeker:
                ws_seeker.receive_json()  # connection_established
                ws_donor.receive_json()  # seeker presence

                # Case A: Seeker sends message -> Delivered in real time to Donor
                send_resp = self.client.post(
                    "/api/v1/seeker/chat/thread-ayesha/send",
                    json={"text": "Doctor asked for 1 more bag of A+ blood urgently."},
                )
                self.assertEqual(send_resp.status_code, 200)

                # Seeker receives message_sent confirmation over websocket
                seeker_ws_event = ws_seeker.receive_json()
                self.assertEqual(seeker_ws_event["type"], "message_sent")
                self.assertEqual(seeker_ws_event["thread_id"], "thread-ayesha")

                # Donor receives live chat_message over websocket on thread-nabil
                donor_ws_msg = ws_donor.receive_json()
                self.assertEqual(donor_ws_msg["type"], "chat_message")
                self.assertEqual(donor_ws_msg["thread_id"], "thread-nabil")
                self.assertIn("Doctor asked for 1 more bag", donor_ws_msg["text"])

                # Case B: Donor replies -> Delivered in real time to Seeker
                donor_send_resp = self.client.post(
                    "/api/v1/donor/chat/thread-nabil/send",
                    json={"text": "I am standing at the hospital reception counter right now.", "sender": "you"},
                )
                self.assertEqual(donor_send_resp.status_code, 200)

                # Seeker receives live chat_message over websocket on thread-ayesha
                seeker_ws_msg = ws_seeker.receive_json()
                self.assertEqual(seeker_ws_msg["type"], "chat_message")
                self.assertEqual(seeker_ws_msg["thread_id"], "thread-ayesha")
                self.assertIn("standing at the hospital reception counter", seeker_ws_msg["text"])

    def test_typing_indicators_broadcast_between_donor_and_seeker(self):
        with self.client.websocket_connect("/ws/chat/donor") as ws_donor:
            ws_donor.receive_json()

            with self.client.websocket_connect("/ws/chat/seeker") as ws_seeker:
                ws_seeker.receive_json()
                ws_donor.receive_json()  # presence

                # Seeker starts typing
                ws_seeker.send_json({"action": "typing", "thread_id": "thread-ayesha", "typing": True})
                donor_typing_event = ws_donor.receive_json()
                self.assertEqual(donor_typing_event["type"], "typing")
                self.assertEqual(donor_typing_event["thread_id"], "thread-nabil")
                self.assertTrue(donor_typing_event["typing"])

                # Donor starts typing
                ws_donor.send_json({"action": "typing", "thread_id": "thread-nabil", "typing": True})
                seeker_typing_event = ws_seeker.receive_json()
                self.assertEqual(seeker_typing_event["type"], "typing")
                self.assertEqual(seeker_typing_event["thread_id"], "thread-ayesha")
                self.assertTrue(seeker_typing_event["typing"])

    def test_seeker_chat_read_endpoint(self):
        read_resp = self.client.post("/api/v1/seeker/chat/thread-ayesha/read")
        self.assertEqual(read_resp.status_code, 200)
        data = read_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["unread_count"], 0)
