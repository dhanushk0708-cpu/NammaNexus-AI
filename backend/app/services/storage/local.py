from pathlib import Path
from uuid import uuid4


class StorageKeyValidationError(ValueError):
    """Raised when a storage key is invalid or unsafe."""


class StorageKeyNotFoundError(StorageKeyValidationError):
    """Raised when a referenced storage key does not exist."""


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
        if not filename or filename in {".", ".."}:
            raise StorageKeyValidationError("Invalid storage key.")

        candidate = Path(filename)

        if (
            candidate.is_absolute()
            or ".." in candidate.parts
            or candidate.name != filename
        ):
            raise StorageKeyValidationError("Invalid storage key.")

        return self.base_path / candidate

    def exists(self, filename: str) -> bool:
        try:
            return self.get_path(filename).exists()
        except StorageKeyValidationError:
            return False

    def validate_image_reference(self, filename: str | None) -> str | None:
        if filename is None:
            return None

        resolved_path = self.get_path(filename)

        if not resolved_path.exists():
            raise StorageKeyNotFoundError(
                "Referenced image does not exist."
            )

        return filename

    def read_image(self, filename: str) -> bytes:
        """Read a stored image and return its bytes."""
        resolved_path = self.get_path(filename)

        if not resolved_path.exists():
            raise StorageKeyNotFoundError(
                "Referenced image does not exist."
            )

        return resolved_path.read_bytes()

    def delete(self, filename: str) -> None:
        file_path = self.get_path(filename)

        if file_path.exists():
            file_path.unlink()