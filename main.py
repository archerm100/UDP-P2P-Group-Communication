import socket
import threading
import uuid
import argparse

from config import (
    HOST,
    MAX_PACKET_SIZE,
    HEARTBEAT_INTERVAL
)

from protocol import (
    Packet,
    MessageType,
    encode_packet,
    decode_packet,
    encode_json,
    decode_json
)

from membership import Membership
from reliable_udp import ReliableUDP
from chat import GroupChat
from file_service import FileService


class Peer:

    def __init__(self, name, port, bootstrap=None):
        self.name = name
        self.port = port
        self.peer_id = uuid.uuid4()
        self.bootstrap = bootstrap

        self.running = threading.Event()
        self.running.set()

        self.membership = Membership(self.peer_id)

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.socket.bind((HOST, port))
        self.socket.settimeout(1)

        self.reliable = ReliableUDP(
            self.socket, self.peer_id
        )

        self.chat = GroupChat(
            self.name,
            self.membership,
            self.reliable
        )

        self.file_service = FileService(self)

    def own_record(self):
        return {
            "peer_id": str(self.peer_id),
            "name": self.name,
            "host": HOST,
            "port": self.port
        }

    def peer_record(self, peer):
        return {
            key: peer[key]
            for key in (
                "peer_id", "name", "host", "port"
            )
        }

    def send_message(self, message_type, data, address):
        packet = Packet(
            message_type=message_type,
            sender_id=self.peer_id,
            payload=encode_json(data)
        )

        try:
            self.socket.sendto(
                encode_packet(packet),
                address
            )
        except OSError as error:
            if self.running.is_set():
                print(f"\n[NETWORK ERROR] {error}")

    def broadcast(self, message_type, data):
        for peer in self.membership.get_peers():
            address = (peer["host"], peer["port"])

            self.send_message(
                message_type,
                data,
                address
            )

    def contact_peer(self, record):
        if record["peer_id"] == str(self.peer_id):
            return

        known = self.membership.get_peers()

        if any(
            p["peer_id"] == record["peer_id"]
            for p in known
        ):
            return

        address = (
            record["host"],
            int(record["port"])
        )

        self.send_message(
            MessageType.HEARTBEAT,
            {"name": self.name},
            address
        )

    def handle_packet(self, packet, address):
        if packet.sender_id == self.peer_id:
            return

        if not self.reliable.process_incoming(
            packet, address
        ):
            return

        if packet.message_type == MessageType.CHAT:
            self.chat.receive_message(packet)
            return

        if self.file_service.handle_packet(
            packet, address
        ):
            return

        data = decode_json(packet.payload)
        message_type = packet.message_type

        if not isinstance(data, dict):
            return

        if message_type == MessageType.JOIN:

            self.membership.add_peer(
                packet.sender_id,
                data["name"],
                address
            )

            self.send_message(
                MessageType.JOIN_REPLY,
                self.own_record(),
                address
            )

            for peer in self.membership.get_peers():

                if peer["peer_id"] == str(packet.sender_id):
                    continue

                self.send_message(
                    MessageType.JOIN_REPLY,
                    self.peer_record(peer),
                    address
                )

                self.send_message(
                    MessageType.PEER_UPDATE,
                    {
                        "peer_id": str(packet.sender_id),
                        "name": data["name"],
                        "host": address[0],
                        "port": address[1]
                    },
                    (peer["host"], peer["port"])
                )

        elif message_type in (
            MessageType.JOIN_REPLY,
            MessageType.PEER_UPDATE
        ):
            self.contact_peer(data)

        elif message_type == MessageType.HEARTBEAT:

            already_known = any(
                p["peer_id"] == str(packet.sender_id)
                for p in self.membership.get_peers()
            )

            self.membership.add_peer(
                packet.sender_id,
                data["name"],
                address
            )

            if not already_known:
                self.send_message(
                    MessageType.HEARTBEAT,
                    {"name": self.name},
                    address
                )

        elif message_type == MessageType.LEAVE:

            self.membership.remove_peer(
                packet.sender_id,
                "left the group"
            )

    def receive_loop(self):

        while self.running.is_set():

            try:
                data, address = self.socket.recvfrom(
                    MAX_PACKET_SIZE + 1
                )

                packet = decode_packet(data)

                self.handle_packet(packet, address)

            except socket.timeout:
                continue

            except (ValueError, KeyError, TypeError,
                    OverflowError):
                continue

            except OSError:
                break

    def heartbeat_loop(self):

        while self.running.is_set():

            self.membership.remove_inactive_peers()

            peers = self.membership.get_peers()

            if self.bootstrap and not peers:
                self.send_message(
                    MessageType.JOIN,
                    {"name": self.name},
                    self.bootstrap
                )

            self.broadcast(
                MessageType.HEARTBEAT,
                {"name": self.name}
            )

            for peer in peers:
                self.broadcast(
                    MessageType.PEER_UPDATE,
                    self.peer_record(peer)
                )

            # Sleep in small intervals for clean shutdown.
            for _ in range(HEARTBEAT_INTERVAL * 10):
                if not self.running.is_set():
                    return

                threading.Event().wait(0.1)

    def start(self):

        threading.Thread(
            target=self.receive_loop,
            daemon=True
        ).start()

        threading.Thread(
            target=self.heartbeat_loop,
            daemon=True
        ).start()

        print("\n===== RPGP PEER STARTED =====")
        print(f"Name: {self.name}")
        print(f"Peer ID: {self.peer_id}")
        print(f"Address: {HOST}:{self.port}")
        print("Commands: peers, chat, share, files, chunks, download, stats, help, exit")
        print("=============================\n")

        try:
            while self.running.is_set():

                command = input(
                    f"{self.name}> "
                ).strip()

                if command.lower().startswith("chat "):
                    self.chat.send_message(command[5:])

                elif command.lower().startswith("share "):
                    try:
                        self.file_service.share(command[6:].strip())
                    except Exception as error:
                        print("[SHARE ERROR]", error)

                elif command.lower() == "files":
                    self.file_service.list_files()

                elif command.lower() == "chunks":
                    self.file_service.list_chunks()

                elif command.lower().startswith("download "):
                    try:
                        self.file_service.download(command[9:].strip())
                    except Exception as error:
                        print("[DOWNLOAD ERROR]", error)

                elif command.lower() == "stats":
                    print(self.reliable.get_stats())

                elif command.lower() == "peers":
                    self.membership.display_peers()

                elif command == "help":
                    print("peers - List active peers")
                    print("help  - Show commands")
                    print("chat <message> - Send group message")
                    print("share <path> - Share a file")
                    print("files - List shared files")
                    print("chunks - List local chunks")
                    print("download <filename or ID> - Download file")
                    print("stats - Show reliability statistics")
                    print("exit  - Leave the group")

                elif command == "exit":
                    break

                elif command:
                    print("Unknown command. Type help.")

        except (KeyboardInterrupt, EOFError):
            pass

        finally:
            self.shutdown()

    def shutdown(self):

        self.running.clear()

        self.broadcast(
            MessageType.LEAVE,
            {"name": self.name}
        )

        self.reliable.stop()
        self.socket.close()

        print("\nPeer stopped.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="RPGP UDP P2P application"
    )

    parser.add_argument("--name", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--bootstrap", type=int)

    args = parser.parse_args()

    bootstrap = None

    if args.bootstrap is not None:
        bootstrap = (HOST, args.bootstrap)

    peer = Peer(
        args.name,
        args.port,
        bootstrap
    )

    peer.start()
