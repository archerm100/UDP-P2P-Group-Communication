import time
import threading

from config import PEER_TIMEOUT


class Membership:

    def __init__(self, own_id):
        self.own_id = str(own_id)
        self.peers = {}
        self.lock = threading.Lock()

    def add_peer(self, peer_id, name, address):
        peer_id = str(peer_id)

        if peer_id == self.own_id:
            return

        with self.lock:
            is_new = peer_id not in self.peers

            self.peers[peer_id] = {
                "peer_id": peer_id,
                "name": name,
                "host": address[0],
                "port": address[1],
                "last_seen": time.monotonic()
            }

        if is_new:
            print(
                f"\n[JOIN] {name} connected "
                f"from {address}",
                flush=True
            )

    def remove_peer(self, peer_id, reason="left"):
        peer_id = str(peer_id)

        with self.lock:
            peer = self.peers.pop(peer_id, None)

        if peer:
            print(
                f"\n[LEAVE] {peer['name']} {reason}",
                flush=True
            )

    def get_peers(self):
        with self.lock:
            return [
                peer.copy()
                for peer in self.peers.values()
            ]

    def remove_inactive_peers(self):
        now = time.monotonic()
        expired = []

        with self.lock:
            for peer_id, peer in list(self.peers.items()):
                if now - peer["last_seen"] > PEER_TIMEOUT:
                    expired.append(
                        self.peers.pop(peer_id)
                    )

        for peer in expired:
            print(
                f"\n[TIMEOUT] {peer['name']} disconnected",
                flush=True
            )

        return expired

    def display_peers(self):
        peers = self.get_peers()

        print("\n===== ACTIVE PEERS =====")

        if not peers:
            print("No other active peers.")

        for peer in peers:
            print(
                f"{peer['name']} | "
                f"{peer['host']}:{peer['port']}"
            )

        print(f"Total peers including you: {len(peers) + 1}")
        print("========================\n")
