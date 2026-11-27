
import struct
import threading

from config import (
    REPLICATION_FACTOR,
    MAX_PAYLOAD_SIZE,
    CHUNK_SIZE
)

from protocol import MessageType


FRAGMENT_FORMAT = "!32sIII"
FRAGMENT_HEADER = struct.calcsize(
    FRAGMENT_FORMAT
)

FRAGMENT_SIZE = (
    MAX_PAYLOAD_SIZE - FRAGMENT_HEADER
)


class ReplicationManager:

    def __init__(self, file_manager,
                 membership, reliable):

        self.file_manager = file_manager
        self.membership = membership
        self.reliable = reliable

        self.fragments = {}
        self.lock = threading.Lock()

    def select_peers(self, chunk_index):

        peers = sorted(
            self.membership.get_peers(),
            key=lambda peer: peer["port"]
        )

        if not peers:
            return []

        count = min(
            REPLICATION_FACTOR,
            len(peers)
        )

        return [
            peers[
                (chunk_index + i) % len(peers)
            ]
            for i in range(count)
        ]

    def build_replication_plan(self, metadata):

        plan = {}

        for index in range(
            metadata["total_chunks"]
        ):

            plan[index] = self.select_peers(
                index
            )

        return plan

    @staticmethod
    def fragment_chunk(file_id, index, chunk):

        if not chunk or len(chunk) > CHUNK_SIZE:
            raise ValueError("Invalid chunk size")

        for offset in range(
            0, len(chunk), FRAGMENT_SIZE
        ):

            fragment = chunk[
                offset:offset + FRAGMENT_SIZE
            ]

            header = struct.pack(
                FRAGMENT_FORMAT,
                bytes.fromhex(file_id),
                index,
                offset,
                len(chunk)
            )

            yield header + fragment

    def send_chunk(self, file_id, index,
                   address,
                   message_type=MessageType.CHUNK_STORE):

        chunk = self.file_manager.get_chunk(
            file_id, index
        )

        if chunk is None:
            raise FileNotFoundError(
                f"Chunk {index} not found"
            )

        for payload in self.fragment_chunk(
            file_id, index, chunk
        ):

            self.reliable.send(
                message_type,
                payload,
                address
            )

    def receive_fragment(self, payload):

        if len(payload) <= FRAGMENT_HEADER:
            raise ValueError("Invalid fragment")

        raw_id, index, offset, total_size = (
            struct.unpack(
                FRAGMENT_FORMAT,
                payload[:FRAGMENT_HEADER]
            )
        )

        file_id = raw_id.hex()

        fragment = payload[FRAGMENT_HEADER:]

        metadata = (
            self.file_manager.get_file_metadata(
                file_id
            )
        )

        if metadata is None:
            return None

        if index >= metadata["total_chunks"]:
            raise ValueError("Invalid chunk index")

        expected_size = min(
            CHUNK_SIZE,
            metadata["file_size"]
            - index * CHUNK_SIZE
        )

        if total_size != expected_size:
            raise ValueError("Invalid chunk size")

        if offset >= total_size:
            raise ValueError("Invalid offset")

        if offset % FRAGMENT_SIZE != 0:
            raise ValueError("Invalid alignment")

        if len(fragment) != min(
            FRAGMENT_SIZE,
            total_size - offset
        ):
            raise ValueError("Invalid fragment size")

        key = (file_id, index)

        with self.lock:

            if self.file_manager.has_chunk(
                file_id, index
            ):
                return None

            parts = self.fragments.setdefault(
                key, {}
            )

            parts[offset] = fragment

            if sum(
                len(part)
                for part in parts.values()
            ) != total_size:

                return None

            chunk = b"".join(
                parts[position]
                for position in sorted(parts)
            )

            del self.fragments[key]

            expected_hash = (
                metadata["chunk_hashes"][index]
            )

            if not self.file_manager.verify_chunk(
                chunk, expected_hash
            ):
                raise ValueError(
                    "Chunk integrity failed"
                )

            self.file_manager.store_chunk(
                file_id, index, chunk
            )

        print(
            f"\n[CHUNK] Stored chunk {index}"
            " | SHA-256 verified",
            flush=True
        )

        return {
            "file_id": file_id,
            "chunk_index": index
        }

    def replicate_file(self, metadata):

        file_id = metadata["file_id"]

        plan = self.build_replication_plan(
            metadata
        )

        for index, peers in plan.items():

            for peer in peers:

                address = (
                    peer["host"],
                    peer["port"]
                )

                self.send_chunk(
                    file_id, index, address
                )

                print(
                    f"[REPLICATION] Chunk {index}"
                    f" queued for {peer['name']}"
                )

        return plan

