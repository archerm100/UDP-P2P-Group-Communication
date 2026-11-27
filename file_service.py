
import threading
import time
import struct

from config import MAX_PAYLOAD_SIZE
from protocol import (
    MessageType,
    encode_json,
    decode_json
)

from file_manager import FileManager
from replication import (
    ReplicationManager,
    FRAGMENT_FORMAT,
    FRAGMENT_HEADER
)
from downloader import Downloader


class FileService:

    def __init__(self, peer):

        self.peer = peer
        self.membership = peer.membership
        self.reliable = peer.reliable

        self.manager = FileManager(peer.peer_id)

        self.replication = ReplicationManager(
            self.manager,
            self.membership,
            self.reliable
        )

        self.downloader = Downloader(
            self.manager,
            self.membership,
            self.reliable
        )

        self.confirmations = set()
        self.active_requests = set()
        self.lock = threading.Lock()

    def background(self, function, *args):

        def run():
            try:
                function(*args)
            except Exception as error:
                print(f"\n[FILE ERROR] {error}")

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def send_json(self, message_type,
                  data, address):

        return self.reliable.send(
            message_type,
            encode_json(data),
            address
        )

    def announce(self, metadata, address):

        sequence = self.send_json(
            MessageType.FILE_ANNOUNCE,
            metadata,
            address
        )

        deadline = time.monotonic() + 15

        while time.monotonic() < deadline:

            with self.reliable.lock:

                pending = (
                    address, sequence
                ) in self.reliable.pending

            if not pending:
                return

            time.sleep(0.05)

        raise TimeoutError(
            "Metadata announcement timed out"
        )

    def share(self, path):

        start = time.monotonic()

        metadata = self.manager.split_file(path)

        if len(encode_json(metadata)) > MAX_PAYLOAD_SIZE:
            raise ValueError(
                "File metadata exceeds packet limit"
            )

        peers = self.membership.get_peers()

        if not peers:
            print("[SHARE] No connected peers")
            return

        file_id = metadata["file_id"]

        print("\n===== FILE SHARING =====")
        print("Filename:", metadata["filename"])
        print("File ID:", file_id)
        print("Size:", metadata["file_size"])
        print("Chunks:", metadata["total_chunks"])

        for peer in peers:

            address = (
                peer["host"], peer["port"]
            )

            self.announce(metadata, address)

        plan = self.replication.build_replication_plan(
            metadata
        )

        expected = set()

        for index, targets in plan.items():

            for target in targets:

                expected.add((
                    file_id,
                    index,
                    target["host"],
                    target["port"]
                ))

        with self.lock:
            self.confirmations.difference_update(
                expected
            )

        self.replication.replicate_file(
            metadata
        )

        deadline = time.monotonic() + 60

        while time.monotonic() < deadline:

            with self.lock:

                confirmed = len(
                    expected & self.confirmations
                )

            if confirmed == len(expected):
                break

            time.sleep(0.1)

        elapsed = time.monotonic() - start

        print("\n===== REPLICATION RESULT =====")
        print("Expected replicas:", len(expected))
        print("Confirmed replicas:", confirmed)
        print(f"Time: {elapsed:.3f} seconds")

        if confirmed == len(expected):
            print("[SHARE] Replication completed!")
        else:
            print("[SHARE] Replication incomplete")

    def list_files(self):

        print("\n===== AVAILABLE FILES =====")

        files = self.manager.list_files()

        if not files:
            print("No files available.")

        for metadata in files:

            print(
                f"{metadata['filename']} | "
                f"{metadata['file_size']} bytes"
            )

            print("ID:", metadata["file_id"])

        print("===========================\n")

    def list_chunks(self):

        print("\n===== LOCAL CHUNKS =====")

        for metadata in self.manager.list_files():

            file_id = metadata["file_id"]

            available = [
                i for i in range(
                    metadata["total_chunks"]
                )
                if self.manager.has_chunk(
                    file_id, i
                )
            ]

            print(
                metadata["filename"],
                "| Chunks:", available
            )

        print("Storage:", self.manager.storage_path)
        print("========================\n")

    def download(self, identifier):

        matches = [
            metadata
            for metadata in self.manager.list_files()
            if identifier in (
                metadata["file_id"],
                metadata["filename"]
            )
        ]

        if not matches:
            print("[DOWNLOAD] File not found")
            return

        if len(matches) > 1:
            print("[DOWNLOAD] Use the full file ID")
            return

        self.downloader.download_file(
            matches[0]["file_id"]
        )

    def serve_chunk(self, file_id,
                    index, address):

        key = (file_id, index, address)

        with self.lock:

            if key in self.active_requests:
                return

            self.active_requests.add(key)

        try:

            if self.manager.has_chunk(
                file_id, index
            ):

                self.replication.send_chunk(
                    file_id,
                    index,
                    address,
                    MessageType.CHUNK_DATA
                )

        finally:

            with self.lock:
                self.active_requests.discard(key)

    def handle_packet(self, packet, address):

        kind = packet.message_type

        if kind == MessageType.FILE_ANNOUNCE:

            metadata = decode_json(packet.payload)

            self.manager.register_file(metadata)

            print(
                f"\n[FILE] Available: "
                f"{metadata['filename']}",
                flush=True
            )

            return True

        if kind in (
            MessageType.CHUNK_STORE,
            MessageType.CHUNK_DATA
        ):

            result = self.replication.receive_fragment(
                packet.payload
            )

            if (
                result is None
                and kind == MessageType.CHUNK_STORE
            ):

                raw_id, index, offset, total = (
                    struct.unpack(
                        FRAGMENT_FORMAT,
                        packet.payload[:FRAGMENT_HEADER]
                    )
                )

                if offset == 0 and self.manager.has_chunk(
                    raw_id.hex(), index
                ):

                    result = {
                        "file_id": raw_id.hex(),
                        "chunk_index": index
                    }

            if (
                result
                and kind == MessageType.CHUNK_STORE
            ):

                self.background(
                    self.send_json,
                    MessageType.CHUNK_CONFIRM,
                    result,
                    address
                )

            return True

        if kind == MessageType.CHUNK_REQUEST:

            data = decode_json(packet.payload)

            self.background(
                self.serve_chunk,
                data["file_id"],
                data["chunk_index"],
                address
            )

            return True

        if kind == MessageType.CHUNK_CONFIRM:

            data = decode_json(packet.payload)

            key = (
                data["file_id"],
                data["chunk_index"],
                address[0],
                address[1]
            )

            with self.lock:
                self.confirmations.add(key)

            print(
                f"\n[CONFIRMED] Chunk "
                f"{data['chunk_index']} "
                f"stored at port {address[1]}"
            )

            return True

        return False

