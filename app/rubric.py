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


BAO_CAO_TYPES = ("bao_cao_ung_dung", "bao_cao_co_ban")
DEFAULT_BAO_CAO = "bao_cao_ung_dung"

# Hai vòng đánh giá của một công trình SV NCKH:
#   tuyen_chon  → chấm bản Thuyết minh chuyên đề (bộ tiêu chí "thuyet_minh", phần TM)
#   nghiem_thu  → chấm Báo cáo tổng kết + sản phẩm (bộ tiêu chí "bao_cao_*", phần I, II)
VONG_TUYEN_CHON = "tuyen_chon"
VONG_NGHIEM_THU = "nghiem_thu"
VONG_LABELS = {VONG_TUYEN_CHON: "Tuyển chọn thuyết minh", VONG_NGHIEM_THU: "Nghiệm thu báo cáo"}


def bao_cao_type(submission: dict | None) -> str:
    """Loại nghiên cứu (cơ bản/ứng dụng) của công trình → chọn phiếu đánh giá báo cáo."""
    loai = (submission or {}).get("part_a", {}).get("loai")
    return loai if loai in BAO_CAO_TYPES else DEFAULT_BAO_CAO


def submission_vong(submission: dict | None) -> str:
    return (submission or {}).get("vong") or VONG_TUYEN_CHON


def active_rubric(store, submission: dict | None) -> dict:
    """Bộ tiêu chí ĐANG dùng để chấm hồ sơ, theo vòng đánh giá hiện tại.

    - Vòng tuyển chọn: phiếu Thuyết minh chuyên đề.
    - Vòng nghiệm thu: phiếu Báo cáo tổng kết (cơ bản/ứng dụng theo loại nghiên cứu).
    """
    if submission_vong(submission) == VONG_NGHIEM_THU:
        return get_rubric(store, bao_cao_type(submission))
    return get_rubric(store, "thuyet_minh")


# Tương thích ngược: rubric_for = bộ tiêu chí đang dùng để chấm (theo vòng).
rubric_for = active_rubric


def upload_part_map(store, submission: dict | None) -> dict[str, dict]:
    """Toàn bộ phần sinh viên có thể nộp trong 1 hồ sơ, gộp cả 2 vòng.

    Trả về {mã_phần: {"part_def", "rubric", "type", "group", "vong"}} theo thứ tự
    Vòng 1 (Thuyết minh: TM) rồi Vòng 2 (Báo cáo: I, II). Mã phần không trùng nhau
    giữa hai bộ tiêu chí nên gộp an toàn.
    """
    tm = get_rubric(store, "thuyet_minh")
    bc = get_rubric(store, bao_cao_type(submission))
    out: dict[str, dict] = {}
    for p in graded_parts(tm):
        out[p] = {"part_def": tm["parts"][p], "rubric": tm, "type": "thuyet_minh",
                  "vong": VONG_TUYEN_CHON, "group": "Vòng 1 — Thuyết minh chuyên đề (tuyển chọn)"}
    for p in graded_parts(bc):
        out[p] = {"part_def": bc["parts"][p], "rubric": bc, "type": bc.get("type"),
                  "vong": VONG_NGHIEM_THU, "group": "Vòng 2 — Báo cáo tổng kết & sản phẩm (nghiệm thu)"}
    return out


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
