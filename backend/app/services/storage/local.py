from pathlib import Path
from uuid import uuid4


class LocalStorageService:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, extension: str) -> str:
        file_id = uuid4().hex
        filename = f"{file_id}{extension}"

        file_path = self.base_path / filename

        file_path.write_bytes(file_bytes)

        return filename

    def get_path(self, filename: str) -> Path:
        return self.base_path / filename

    def exists(self, filename: str) -> bool:
        return self.get_path(filename).exists()

    def delete(self, filename: str) -> None:
        file_path = self.get_path(filename)

        if file_path.exists():
            file_path.unlink()