"""DocStore trên Google Firestore (APP_MODE=gcp).

Import google-cloud-firestore tại chỗ để chế độ local không cần cài thư viện GCP.
"""
from __future__ import annotations

from app.db import DocStore


class FirestoreStore(DocStore):
    def __init__(self, project: str = ""):
        from google.cloud import firestore  # noqa: PLC0415 — lazy import có chủ đích

        self._client = firestore.Client(project=project or None)

    def get(self, coll: str, doc_id: str) -> dict | None:
        snap = self._client.collection(coll).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def put(self, coll: str, doc_id: str, doc: dict) -> None:
        doc = dict(doc)
        doc["id"] = doc_id
        self._client.collection(coll).document(doc_id).set(doc)

    def delete(self, coll: str, doc_id: str) -> None:
        self._client.collection(coll).document(doc_id).delete()

    def all(self, coll: str) -> list[dict]:
        return [snap.to_dict() for snap in self._client.collection(coll).stream()]

    def find(self, coll: str, **eq):
        query = self._client.collection(coll)
        for k, v in eq.items():
            query = query.where(field_path=k, op_string="==", value=v)
        return [snap.to_dict() for snap in query.stream()]

    def wipe(self) -> None:
        raise RuntimeError("Không hỗ trợ xóa toàn bộ dữ liệu Firestore từ ứng dụng")
