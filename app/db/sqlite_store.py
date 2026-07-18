"""DocStore trên SQLite — mỗi collection một bảng (id TEXT PK, doc JSON)."""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path

from app.db import DocStore

_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class SqliteStore(DocStore):
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.Lock()
        self._known: set[str] = set()
        with self._conn() as con:
            con.execute("PRAGMA journal_mode=WAL")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def _table(self, con: sqlite3.Connection, coll: str) -> str:
        if not _NAME_RE.match(coll):
            raise ValueError(f"Tên collection không hợp lệ: {coll}")
        if coll not in self._known:
            con.execute(f"CREATE TABLE IF NOT EXISTS {coll} (id TEXT PRIMARY KEY, doc TEXT NOT NULL)")
            self._known.add(coll)
        return coll

    def get(self, coll: str, doc_id: str) -> dict | None:
        with self._lock, self._conn() as con:
            t = self._table(con, coll)
            row = con.execute(f"SELECT doc FROM {t} WHERE id=?", (doc_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, coll: str, doc_id: str, doc: dict) -> None:
        doc = dict(doc)
        doc["id"] = doc_id
        with self._lock, self._conn() as con:
            t = self._table(con, coll)
            con.execute(
                f"INSERT INTO {t}(id, doc) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET doc=excluded.doc",
                (doc_id, json.dumps(doc, ensure_ascii=False)),
            )

    def delete(self, coll: str, doc_id: str) -> None:
        with self._lock, self._conn() as con:
            t = self._table(con, coll)
            con.execute(f"DELETE FROM {t} WHERE id=?", (doc_id,))

    def all(self, coll: str) -> list[dict]:
        with self._lock, self._conn() as con:
            t = self._table(con, coll)
            rows = con.execute(f"SELECT doc FROM {t}").fetchall()
        return [json.loads(r[0]) for r in rows]

    def wipe(self) -> None:
        with self._lock, self._conn() as con:
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                if _NAME_RE.match(t):
                    con.execute(f"DELETE FROM {t}")
