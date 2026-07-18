"""Kiểm tra hợp lệ hồ sơ: định dạng tệp, dung lượng, quy ước tên tệp,
liên kết truy cập được, tính đầy đủ sản phẩm + minh chứng từng phần."""
from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.config import ALLOWED_EXTENSIONS, GRADED_PARTS, MAX_FILE_SIZE

PART_A_REQUIRED = ["ho_ten", "ma_gv", "khoa_bo_mon", "hoc_phan", "cong_cu_ai", "muc_thanh_thao"]


def check_extension(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            f"Định dạng {ext or '(không có)'} không được chấp nhận. "
            f"Chỉ nhận: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return None


def check_size(size: int) -> str | None:
    if size > MAX_FILE_SIZE:
        return f"Tệp {size / 1024 / 1024:.0f}MB vượt giới hạn 200MB/tệp"
    if size == 0:
        return "Tệp rỗng"
    return None


def check_naming(filename: str, ma_gv: str, part: str) -> str | None:
    """Quy ước: MãGV_TênPhần_TênSảnPhẩm (vd GV001_PhanB_DeCuongHocPhan.docx).
    Chỉ cảnh báo, không chặn nộp."""
    stem = Path(filename).stem
    pattern = rf"^{re.escape(ma_gv)}_Phan{part}_.+$"
    if not re.match(pattern, stem, flags=re.IGNORECASE):
        return f"Tên tệp nên theo cấu trúc {ma_gv}_Phan{part}_TênSảnPhẩm (hiện tại: {filename})"
    return None


def check_link(url: str, timeout: float = 6.0) -> tuple[bool, str]:
    """Kiểm tra liên kết truy cập được (best-effort)."""
    if not re.match(r"^https?://", url):
        return False, "Liên kết phải bắt đầu bằng http:// hoặc https://"
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": "DNU-AI-Assess/1.0"})
        if resp.status_code < 400:
            return True, f"Truy cập được (HTTP {resp.status_code})"
        return False, f"Liên kết trả về HTTP {resp.status_code} — kiểm tra chế độ chia sẻ"
    except Exception as exc:  # noqa: BLE001 — mọi lỗi mạng đều coi là không truy cập được
        return False, f"Không truy cập được liên kết ({type(exc).__name__})"


def part_a_complete(part_a: dict | None) -> tuple[bool, list[str]]:
    part_a = part_a or {}
    missing = []
    labels = {
        "ho_ten": "Họ tên", "ma_gv": "Mã giảng viên", "khoa_bo_mon": "Đơn vị/Bộ môn",
        "hoc_phan": "Học phần đăng ký", "cong_cu_ai": "Danh mục công cụ AI",
        "muc_thanh_thao": "Mức độ thành thạo tự đánh giá",
    }
    for f in PART_A_REQUIRED:
        v = part_a.get(f)
        if v in (None, "", []):
            missing.append(labels[f])
    return (not missing), missing


def completeness(store, submission: dict) -> dict:
    """Checklist đầy đủ từng phần: A hợp lệ; B–G có sản phẩm và minh chứng.

    Trả về {"A": {...}, "B": {"products": n, "evidences": n, "ok": bool}, ...,
            "valid": bool, "warnings": [...]}.
    Phần G dùng chính danh mục minh chứng làm minh chứng nên chỉ cần sản phẩm.
    """
    items = store.find("submission_items", submission_id=submission["id"])
    result: dict = {}
    a_ok, a_missing = part_a_complete(submission.get("part_a"))
    result["A"] = {"ok": a_ok, "missing": a_missing}
    warnings: list[str] = []
    for part in GRADED_PARTS:
        prods = [i for i in items if i["part"] == part and i["kind"] == "product"]
        evs = [i for i in items if i["part"] == part and i["kind"] == "evidence"]
        need_evidence = part != "G"
        ok = bool(prods) and (bool(evs) or not need_evidence)
        result[part] = {"products": len(prods), "evidences": len(evs), "ok": ok}
        if not prods:
            warnings.append(f"Phần {part}: chưa có sản phẩm")
        elif need_evidence and not evs:
            warnings.append(f"Phần {part}: chưa có minh chứng sử dụng AI (sẽ bị trừ tối đa 50% điểm tiêu chí liên quan)")
        for it in prods + evs:
            if it.get("type") == "link" and not it.get("link_ok", True):
                warnings.append(f"Phần {part}: liên kết '{it.get('original_name') or it.get('url')}' không truy cập được")
    # Hồ sơ hợp lệ khi Phần A đầy đủ (điều kiện hợp lệ theo đề bài)
    result["valid"] = a_ok
    result["warnings"] = warnings
    return result
