
import threading
import time
import random

from config import (
    RETRANSMISSION_TIMEOUT,
    MAX_RETRIES,
    PACKET_LOSS_RATE,
    WINDOW_SIZE
)

from protocol import (
    Packet,
    MessageType,
    PacketFlag,
    encode_packet
)


class ReliableUDP:

    def __init__(self, sock, peer_id):
        self.socket = sock
        self.peer_id = peer_id

        self.sequence = 0
        self.pending = {}
        self.received = set()

        self.lock = threading.Lock()
        self.window = threading.Condition(self.lock)
        self.running = True

        self.sent_packets = 0
        self.acknowledged_packets = 0
        self.retransmissions = 0
        self.failed_packets = 0
        self.dropped_packets = 0

        self.worker = threading.Thread(
            target=self.retransmit_loop,
            daemon=True
        )
        self.worker.start()

    def next_sequence(self):
        with self.lock:
            self.sequence += 1
            return self.sequence

    def send_raw(self, data, address):
        if random.random() < PACKET_LOSS_RATE:
            with self.lock:
                self.dropped_packets += 1
            return

        try:
            self.socket.sendto(data, address)
        except OSError:
            pass

    def send(self, message_type, payload, address,
             stream_id=0):

        sequence = self.next_sequence()

        packet = Packet(
            message_type=message_type,
            sender_id=self.peer_id,
            sequence_number=sequence,
            stream_id=stream_id,
            flags=int(PacketFlag.RELIABLE),
            payload=payload
        )

        encoded = encode_packet(packet)
        key = (address, sequence)

        with self.window:

            while self.running and sum(
                1 for dest, seq in self.pending
                if dest == address
            ) >= WINDOW_SIZE:
                self.window.wait(timeout=0.1)

            if not self.running:
                raise RuntimeError("Transport stopped")

            self.pending[key] = {
                "data": encoded,
                "address": address,
                "time": time.monotonic(),
                "retries": 0
            }

            self.sent_packets += 1

        self.send_raw(encoded, address)

        return sequence

    def send_ack(self, packet, address):

        ack = Packet(
            message_type=MessageType.ACK,
            sender_id=self.peer_id,
            acknowledgment_number=(
                packet.sequence_number
            ),
            stream_id=packet.stream_id
        )

        self.send_raw(
            encode_packet(ack),
            address
        )

    def handle_ack(self, packet, address):

        key = (
            address,
            packet.acknowledgment_number
        )

        with self.lock:
            if key in self.pending:
                del self.pending[key]
                self.acknowledged_packets += 1
                self.window.notify_all()

    def process_incoming(self, packet, address):

        if packet.message_type == MessageType.ACK:
            self.handle_ack(packet, address)
            return False

        if not packet.flags & PacketFlag.RELIABLE:
            return True

        self.send_ack(packet, address)

        key = (
            packet.sender_id,
            packet.sequence_number
        )

        with self.lock:
            if key in self.received:
                return False

            self.received.add(key)

        return True

    def retransmit_loop(self):

        while self.running:

            now = time.monotonic()
            resend = []

            with self.lock:

                for key, item in list(
                    self.pending.items()
                ):

                    elapsed = now - item["time"]

                    if elapsed < RETRANSMISSION_TIMEOUT:
                        continue

                    if item["retries"] >= MAX_RETRIES:

                        del self.pending[key]
                        self.failed_packets += 1
                        self.window.notify_all()

                        print(
                            "\n[FAILED] Packet",
                            key[1],
                            "could not be delivered."
                        )
                        continue

                    item["time"] = now
                    item["retries"] += 1

                    self.retransmissions += 1

                    resend.append((
                        item["data"],
                        item["address"]
                    ))

            for data, address in resend:
                self.send_raw(data, address)

            time.sleep(0.05)

    def get_stats(self):

        with self.lock:
            return {
                "sent_packets": self.sent_packets,
                "acknowledged_packets":
                    self.acknowledged_packets,
                "retransmissions":
                    self.retransmissions,
                "failed_packets":
                    self.failed_packets,
                "dropped_packets":
                    self.dropped_packets,
                "pending_packets":
                    len(self.pending)
            }

    def stop(self):
        with self.window:
            self.running = False
            self.window.notify_all()

        self.worker.join(timeout=1)

