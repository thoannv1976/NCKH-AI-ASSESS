"""Nạp rubric chấm điểm. Rubric gốc seed từ rubrics/rubric.json; bản dùng thực tế
lưu trong DB (collection config/rubric) để quản trị viên có thể hiệu chỉnh.

Hệ thống hỗ trợ NHIỀU bộ tiêu chí (loại công trình) trong cùng một file:
- thuyet_minh:      Phiếu đánh giá Thuyết minh chuyên đề (vòng tuyển chọn, đạt ≥52).
- bao_cao_co_ban:   Phiếu đánh giá Báo cáo tổng kết — công trình nghiên cứu cơ bản.
- bao_cao_ung_dung: Phiếu đánh giá Báo cáo tổng kết — công trình nghiên cứu ứng dụng.

get_rubric(store, rubric_type) trả về bộ tiêu chí của MỘT loại, có hình dạng giống
rubric đơn trước đây (parts / classification / level_bands) để phần còn lại của hệ
thống dùng nguyên như cũ.
"""
from __future__ import annotations

import json
from pathlib import Path

RUBRIC_FILE = Path(__file__).resolve().parent.parent / "rubrics" / "rubric.json"


def load_rubric_seed() -> dict:
    with open(RUBRIC_FILE, encoding="utf-8") as f:
        return json.load(f)


def _full(store) -> dict:
    """Bản rubric đầy đủ (mọi loại công trình) đang dùng, seed vào DB nếu chưa có."""
    doc = store.get("config", "rubric")
    if not doc:
        doc = {"id": "rubric", **load_rubric_seed()}
        store.put("config", "rubric", doc)
    return doc


def rubric_types(store) -> dict[str, dict]:
    return _full(store).get("types", {})


def default_type(store) -> str:
    full = _full(store)
    return full.get("default_type") or next(iter(full.get("types", {})), "")


def resolve_type(store, rubric_type: str | None) -> str:
    types = rubric_types(store)
    if rubric_type and rubric_type in types:
        return rubric_type
    return default_type(store)


def get_rubric(store, rubric_type: str | None = None) -> dict:
    """Bộ tiêu chí của MỘT loại công trình (mặc định: loại đang đặt default_type).

    Trả về dict phẳng gồm parts/classification/level_bands (+ meta: type, version,
    label, pass_score, advance_score, evidence_required) — dùng như rubric đơn cũ.
    """
    full = _full(store)
    types = full.get("types", {})
    key = rubric_type if (rubric_type and rubric_type in types) else (full.get("default_type") or next(iter(types), ""))
    tdef = dict(types.get(key, {}))
    tdef["type"] = key
    tdef["version"] = full.get("version", "")
    return tdef


def rubric_for(store, submission: dict | None) -> dict:
    """Rubric ứng với loại nghiên cứu (part_a.loai) của một hồ sơ công trình."""
    loai = (submission or {}).get("part_a", {}).get("loai") if submission else None
    return get_rubric(store, loai)


def graded_parts(rubric: dict) -> list[str]:
    """Danh sách mã phần được chấm của một bộ tiêu chí (theo thứ tự khai báo)."""
    return [p for p, d in rubric.get("parts", {}).items() if d.get("graded")]


def all_class_labels(store) -> dict[str, str]:
    """Gộp nhãn xếp loại của MỌI loại công trình (dùng cho báo cáo tổng hợp lẫn loại)."""
    labels: dict[str, str] = {}
    for tdef in rubric_types(store).values():
        for c in tdef.get("classification", []):
            labels.setdefault(c["key"], c["label"])
    return labels


def top_class_keys(store) -> set[str]:
    """Khóa xếp loại cao nhất (ngưỡng min lớn nhất) của mỗi loại — công trình tiêu biểu."""
    keys = set()
    for tdef in rubric_types(store).values():
        cls = tdef.get("classification", [])
        if cls:
            keys.add(max(cls, key=lambda c: c["min"])["key"])
    return keys


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
