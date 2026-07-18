"""Cấu hình AI do Admin nạp trong app (lưu DB), ưu tiên hơn biến môi trường.

Cho phép nạp/đổi API key và model ngay trên giao diện mà không cần đổi biến môi trường.
"""
from __future__ import annotations

from app.config import get_settings


def get_ai_config(store) -> dict:
    """Hợp nhất cấu hình AI: DB (config/ai) ưu tiên, fallback biến môi trường."""
    s = get_settings()
    doc = store.get("config", "ai") or {}
    api_key = (doc.get("api_key") or "").strip() or s.anthropic_api_key
    model = (doc.get("model") or "").strip() or s.grading_model
    forced = doc.get("grader") or "auto"  # auto | claude | mock
    if forced == "claude":
        kind = "claude"
    elif forced == "mock":
        kind = "mock"
    else:
        kind = "claude" if api_key else "mock"
    return {
        "api_key": api_key, "model": model, "grader": kind, "forced": forced,
        "has_key": bool(api_key), "key_source": "DB" if doc.get("api_key") else ("ENV" if s.anthropic_api_key else "—"),
        "key_hint": ("••••" + api_key[-4:]) if api_key and len(api_key) >= 4 else "",
    }


def set_ai_config(store, *, api_key: str | None = None, model: str | None = None,
                  grader: str | None = None, clear_key: bool = False) -> None:
    doc = store.get("config", "ai") or {"id": "ai"}
    if clear_key:
        doc["api_key"] = ""
    elif api_key and api_key.strip():
        doc["api_key"] = api_key.strip()
    if model is not None:
        doc["model"] = model.strip()
    if grader is not None and grader in ("auto", "claude", "mock"):
        doc["grader"] = grader
    store.put("config", "ai", doc)
