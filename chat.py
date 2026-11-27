
from datetime import datetime

from protocol import (
    MessageType,
    encode_json,
    decode_json
)

from config import MAX_PAYLOAD_SIZE


class GroupChat:

    def __init__(self, name, membership, reliable):
        self.name = name
        self.membership = membership
        self.reliable = reliable

    def send_message(self, message):

        message = message.strip()

        if not message:
            return

        payload = encode_json({
            "name": self.name,
            "message": message,
            "timestamp": datetime.now().strftime(
                "%H:%M:%S"
            )
        })

        if len(payload) > MAX_PAYLOAD_SIZE:
            print("[CHAT] Message is too long.")
            return

        peers = self.membership.get_peers()

        if not peers:
            print("[CHAT] No connected peers.")
            return

        for peer in peers:

            address = (
                peer["host"],
                peer["port"]
            )

            self.reliable.send(
                MessageType.CHAT,
                payload,
                address
            )

        print(f"[YOU] {message}")
        print(f"[CHAT] Sent to {len(peers)} peers.")

    def receive_message(self, packet):

        data = decode_json(packet.payload)

        name = data["name"]
        message = data["message"]
        timestamp = data["timestamp"]

        print(
            f"\n[{timestamp}] {name}: {message}",
            flush=True
        )

