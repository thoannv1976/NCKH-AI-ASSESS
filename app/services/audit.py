"""Audit log append-only: mọi thao tác chấm, điều chỉnh điểm, phê duyệt, công bố."""
from __future__ import annotations

from app.config import now_vn


def log(store, actor: dict | None, action: str, target: str, before=None, after=None, note: str = "") -> None:
    store.add(
        "audit_logs",
        {
            "actor": (actor or {}).get("email", "system"),
            "role": (actor or {}).get("role", "system"),
            "action": action,
            "target": target,
            "before": before,
            "after": after,
            "note": note,
            "ts": now_vn().isoformat(),
        },
    )
