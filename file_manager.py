
import hashlib
import re
from pathlib import Path

from config import CHUNK_SIZE, STORAGE_DIR


class FileManager:

    def __init__(self, peer_id):
        self.peer_id = str(peer_id)

        self.storage_path = (
            Path(STORAGE_DIR) / self.peer_id
        )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True
        )

        self.files = {}

    @staticmethod
    def calculate_hash(data):
        return hashlib.sha256(data).hexdigest()

    def split_file(self, file_path):

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(file_path)

        chunks = []
        file_hash = hashlib.sha256()
        file_size = 0

        with path.open("rb") as file:

            while True:

                chunk = file.read(CHUNK_SIZE)

                if not chunk:
                    break

                chunks.append(chunk)
                file_hash.update(chunk)
                file_size += len(chunk)

        file_id = file_hash.hexdigest()

        metadata = {
            "file_id": file_id,
            "filename": path.name,
            "file_size": file_size,
            "total_chunks": len(chunks),
            "chunk_size": CHUNK_SIZE,
            "sha256": file_id,
            "chunk_hashes": [
                self.calculate_hash(chunk)
                for chunk in chunks
            ]
        }

        for index, chunk in enumerate(chunks):

            self.store_chunk(
                file_id,
                index,
                chunk
            )

        self.files[file_id] = metadata

        return metadata

    def chunk_path(self, file_id, index):

        if not re.fullmatch(r"[0-9a-f]{64}", file_id):
            raise ValueError("Invalid file ID")

        if not isinstance(index, int) or index < 0:
            raise ValueError("Invalid chunk index")

        directory = self.storage_path / file_id

        return directory / f"chunk_{index:06d}.bin"

    def store_chunk(self, file_id, index, data):

        path = self.chunk_path(file_id, index)

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_bytes(data)

    def get_chunk(self, file_id, index):

        path = self.chunk_path(file_id, index)

        if not path.exists():
            return None

        return path.read_bytes()

    def has_chunk(self, file_id, index):

        return self.chunk_path(
            file_id, index
        ).is_file()

    def verify_chunk(self, data, expected_hash):

        return (
            self.calculate_hash(data)
            == expected_hash
        )

    def register_file(self, metadata):

        self.files[
            metadata["file_id"]
        ] = metadata

    def get_file_metadata(self, file_id):

        return self.files.get(file_id)

    def list_files(self):

        return list(self.files.values())

