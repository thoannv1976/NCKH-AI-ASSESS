"""Tầng truy cập dữ liệu kiểu document-store.

Interface chung cho 2 hiện thực: SQLite (local) và Firestore (gcp), giúp toàn bộ
nghiệp vụ không phụ thuộc hạ tầng. Document là dict, luôn chứa khóa "id".
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


def new_id() -> str:
    return uuid.uuid4().hex


class DocStore(ABC):
    @abstractmethod
    def get(self, coll: str, doc_id: str) -> dict | None: ...

    @abstractmethod
    def put(self, coll: str, doc_id: str, doc: dict) -> None: ...

    @abstractmethod
    def delete(self, coll: str, doc_id: str) -> None: ...

    @abstractmethod
    def all(self, coll: str) -> list[dict]: ...

    @abstractmethod
    def wipe(self) -> None: ...

    # ----- tiện ích chung -----
    def add(self, coll: str, doc: dict) -> str:
        doc_id = doc.get("id") or new_id()
        doc["id"] = doc_id
        self.put(coll, doc_id, doc)
        return doc_id

    def patch(self, coll: str, doc_id: str, fields: dict) -> dict:
        doc = self.get(coll, doc_id) or {"id": doc_id}
        doc.update(fields)
        self.put(coll, doc_id, doc)
        return doc

    def find(self, coll: str, **eq: Any) -> list[dict]:
        return [d for d in self.all(coll) if all(d.get(k) == v for k, v in eq.items())]

    def find_one(self, coll: str, **eq: Any) -> dict | None:
        rows = self.find(coll, **eq)
        return rows[0] if rows else None


def create_store(settings) -> DocStore:
    if settings.app_mode == "gcp":
        from app.db.firestore_store import FirestoreStore

        return FirestoreStore(settings.firestore_project)
    from app.db.sqlite_store import SqliteStore

    return SqliteStore(settings.data_dir / "dnu_ai_assess.db")
