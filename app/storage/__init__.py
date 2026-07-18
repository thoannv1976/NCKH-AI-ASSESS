"""Tầng lưu trữ tệp sản phẩm/minh chứng: cục bộ (local) hoặc GCS (gcp)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class FileStorage(ABC):
    @abstractmethod
    def save(self, key: str, fileobj: BinaryIO) -> int:
        """Lưu tệp, trả về kích thước (bytes)."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(FileStorage):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("Đường dẫn tệp không hợp lệ")
        return p

    def save(self, key: str, fileobj: BinaryIO) -> int:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fileobj.seek(0)  # đảm bảo đọc từ đầu (tránh ghi tệp rỗng nếu con trỏ ở cuối)
        except (OSError, ValueError, AttributeError):
            pass
        size = 0
        with open(path, "wb") as out:
            while chunk := fileobj.read(1024 * 1024):
                out.write(chunk)
                size += len(chunk)
        return size

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class GcsStorage(FileStorage):
    """Lưu trên Google Cloud Storage; hỗ trợ signed URL để client upload trực tiếp
    (Cloud Run giới hạn request ~32MB nên tệp 200MB không đi qua server)."""

    def __init__(self, bucket: str):
        from google.cloud import storage  # noqa: PLC0415 — lazy import có chủ đích

        self._bucket = storage.Client().bucket(bucket)

    def save(self, key: str, fileobj: BinaryIO) -> int:
        blob = self._bucket.blob(key)
        # rewind=True: tua về đầu trước khi tải lên, tránh ghi blob RỖNG khi con trỏ
        # tệp không ở vị trí 0 (nguyên nhân tệp tải về bị rỗng).
        blob.upload_from_file(fileobj, rewind=True)
        blob.reload()
        return blob.size or 0

    def open(self, key: str):
        # Tải toàn bộ nội dung blob vào bộ đệm seek được (RAM cho tệp nhỏ, tràn ra đĩa
        # cho tệp lớn) rồi trả về ở vị trí 0 — đáng tin cậy hơn streaming reader khi
        # ghép ZIP / trích xuất / phục vụ tệp.
        import tempfile

        buf = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
        self._bucket.blob(key).download_to_file(buf)
        buf.seek(0)
        return buf

    def exists(self, key: str) -> bool:
        return self._bucket.blob(key).exists()

    def delete(self, key: str) -> None:
        blob = self._bucket.blob(key)
        if blob.exists():
            blob.delete()

    def signed_upload_url(self, key: str, content_type: str, expires_minutes: int = 30) -> str:
        from datetime import timedelta

        return self._bucket.blob(key).generate_signed_url(
            version="v4", expiration=timedelta(minutes=expires_minutes), method="PUT", content_type=content_type
        )


def create_storage(settings) -> FileStorage:
    if settings.app_mode == "gcp":
        return GcsStorage(settings.gcs_bucket)
    return LocalStorage(settings.data_dir / "uploads")
