import uuid
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile


class StoragePort(Protocol):
    async def save(self, file: UploadFile, subdir: str) -> str: ...

    async def delete(self, url: str) -> None: ...


class LocalDiskStorage:
    def __init__(self, base_dir: str = "uploads", public_prefix: str = "/static/uploads"):
        self.base_dir = Path(base_dir)
        self.public_prefix = public_prefix

    async def save(self, file: UploadFile, subdir: str) -> str:
        ext = Path(file.filename or "").suffix.lower()
        dest_dir = self.base_dir / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4()}{ext}"
        dest_path = dest_dir / filename
        content = await file.read()
        dest_path.write_bytes(content)
        return f"{self.public_prefix}/{subdir}/{filename}"

    async def delete(self, url: str) -> None:
        relative = url.removeprefix(self.public_prefix).lstrip("/")
        path = self.base_dir / relative
        if path.exists():
            path.unlink()


def get_storage() -> StoragePort:
    return LocalDiskStorage()
