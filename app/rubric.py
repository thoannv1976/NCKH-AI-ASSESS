"""Nạp rubric chấm điểm. Rubric gốc seed từ rubrics/rubric.json; bản dùng thực tế
lưu trong DB (collection config/rubric) để quản trị viên có thể hiệu chỉnh."""
from __future__ import annotations

import json
from pathlib import Path

RUBRIC_FILE = Path(__file__).resolve().parent.parent / "rubrics" / "rubric.json"


def load_rubric_seed() -> dict:
    with open(RUBRIC_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_rubric(store) -> dict:
    doc = store.get("config", "rubric")
    if not doc:
        doc = {"id": "rubric", **load_rubric_seed()}
        store.put("config", "rubric", doc)
    return doc


def reload_rubric(store) -> tuple[str | None, str]:
    """Ghi đè rubric đang dùng (config/rubric) bằng bản mới nhất kèm theo phần mềm.

    An toàn: CHỈ cập nhật config/rubric — không đụng tới hồ sơ, điểm, người dùng hay
    cấu hình khác. Trả về (phiên bản cũ, phiên bản mới) để ghi nhật ký/thông báo.
    """
    old = store.get("config", "rubric") or {}
    seed = load_rubric_seed()
    store.put("config", "rubric", {"id": "rubric", **seed})
    return old.get("version"), seed.get("version", "")


def part_rubric(rubric: dict, part: str) -> dict:
    return rubric["parts"][part]


def criteria_map(part_def: dict) -> dict[str, dict]:
    return {c["id"]: c for c in part_def.get("criteria", [])}
