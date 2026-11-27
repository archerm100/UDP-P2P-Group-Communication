
import hashlib
import time
from pathlib import Path

from config import DOWNLOAD_DIR, CHUNK_SIZE

from protocol import (
    MessageType,
    encode_json
)


class Downloader:

    def __init__(self, file_manager,
                 membership, reliable):

        self.file_manager = file_manager
        self.membership = membership
        self.reliable = reliable

        self.download_path = (
            Path(DOWNLOAD_DIR)
            / file_manager.peer_id
        )

        self.download_path.mkdir(
            parents=True,
            exist_ok=True
        )

    def missing_chunks(self, metadata):

        file_id = metadata["file_id"]
        missing = []

        for index in range(
            metadata["total_chunks"]
        ):

            chunk = self.file_manager.get_chunk(
                file_id, index
            )

            expected_hash = (
                metadata["chunk_hashes"][index]
            )

            if chunk is None or not (
                self.file_manager.verify_chunk(
                    chunk, expected_hash
                )
            ):
                missing.append(index)

        return missing

    def request_chunk(self, file_id, index):

        payload = encode_json({
            "file_id": file_id,
            "chunk_index": index
        })

        for peer in self.membership.get_peers():

            address = (
                peer["host"],
                peer["port"]
            )

            self.reliable.send(
                MessageType.CHUNK_REQUEST,
                payload,
                address
            )

    def reconstruct_file(self, metadata):

        file_id = metadata["file_id"]

        filename = Path(
            metadata["filename"]
        ).name

        if filename in ("", ".", ".."):
            raise ValueError("Invalid filename")

        output = self.download_path / filename

        temporary = self.download_path / (
            file_id + ".part"
        )

        file_hash = hashlib.sha256()
        total_bytes = 0

        try:

            with temporary.open("wb") as file:

                for index in range(
                    metadata["total_chunks"]
                ):

                    chunk = (
                        self.file_manager.get_chunk(
                            file_id, index
                        )
                    )

                    if chunk is None:
                        raise ValueError(
                            f"Missing chunk {index}"
                        )

                    expected_hash = (
                        metadata["chunk_hashes"][index]
                    )

                    if not (
                        self.file_manager.verify_chunk(
                            chunk, expected_hash
                        )
                    ):
                        raise ValueError(
                            f"Corrupt chunk {index}"
                        )

                    file.write(chunk)
                    file_hash.update(chunk)
                    total_bytes += len(chunk)

            if total_bytes != metadata["file_size"]:
                raise ValueError("File size mismatch")

            if (
                file_hash.hexdigest()
                != metadata["sha256"]
            ):
                raise ValueError(
                    "File integrity check failed"
                )

            temporary.replace(output)

        except Exception:

            temporary.unlink(missing_ok=True)
            raise

        print("\n[DOWNLOAD] File reconstructed")
        print("[DOWNLOAD] SHA-256 verified")
        print("[DOWNLOAD] Saved to:", output)

        return output

    def download_file(self, file_id, timeout=60):

        metadata = (
            self.file_manager.get_file_metadata(
                file_id
            )
        )

        if metadata is None:
            raise ValueError("Unknown file ID")

        start = time.monotonic()
        deadline = start + timeout

        print(
            "[DOWNLOAD] Requesting:",
            metadata["filename"]
        )

        while True:

            missing = self.missing_chunks(
                metadata
            )

            if not missing:
                break

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Missing chunks: {missing}"
                )

            for index in missing:
                self.request_chunk(
                    file_id, index
                )

            time.sleep(2)

        output = self.reconstruct_file(metadata)

        elapsed = time.monotonic() - start

        print(
            f"[DOWNLOAD] Time: {elapsed:.3f} seconds"
        )

        return output

