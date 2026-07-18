"""Engine chấm tự động công trình/thuyết minh NCKH sinh viên.

Quy tắc cốt lõi:
- Mỗi Phần chấm 2 lượt độc lập; tiêu chí nào lệch >15% điểm tối đa → chấm lượt 3
  và lấy TRUNG VỊ; ngược lại lấy trung bình 2 lượt.
- Điểm mỗi phần kẹp trần theo max_score của phần.
- Với bộ tiêu chí "thuyết minh": tiêu chí nào dưới mức điểm tối thiểu (min) được ghi
  cờ để Hội đồng lưu ý (điều kiện đề nghị thực hiện: tổng ≥52 và không tiêu chí nào
  dưới mức tối thiểu).
- (Tùy chọn) Nếu rubric đặt evidence_required=true: sản phẩm thiếu minh chứng → trừ
  tối đa 50% điểm tiêu chí liên quan; hệ thống đối chiếu danh mục minh chứng ở Phần G.
- Hồ sơ đạt ngưỡng xét chọn cấp Trường hoặc có cờ bất thường → thẩm định bắt buộc.
- Checkpoint từng phần trong DB: chạy lại không chấm trùng, không mất dữ liệu.
"""
from __future__ import annotations

import logging
import statistics

from app.config import now_vn
from app.rubric import graded_parts, rubric_for
from app.services.extraction import build_part_content
from app.services.grading.graders import Grader

logger = logging.getLogger("ftu.grading")

DIVERGENCE_THRESHOLD = 0.15  # 15%
DEFAULT_MANDATORY_REVIEW_SCORE = 80  # ngưỡng mặc định (đủ điều kiện dự cấp Trường)


def clamp(value: float, max_value: float) -> float:
    return max(0.0, min(float(max_value), float(value)))


def combine_two_passes(crit_max: float, s1: float, s2: float) -> tuple[float, bool]:
    """Trả về (điểm tạm, có cần lượt 3 không)."""
    s1, s2 = clamp(s1, crit_max), clamp(s2, crit_max)
    if abs(s1 - s2) > DIVERGENCE_THRESHOLD * crit_max:
        return 0.0, True
    return round((s1 + s2) / 2, 2), False


def median_of_three(crit_max: float, s1: float, s2: float, s3: float) -> float:
    return round(statistics.median([clamp(s1, crit_max), clamp(s2, crit_max), clamp(s3, crit_max)]), 2)


def apply_evidence_rules(part_def: dict, finals: dict[str, dict], evidence_missing: bool) -> None:
    """Áp quy định trừ điểm thiếu minh chứng (tối đa 50% tiêu chí liên quan)."""
    for c in part_def["criteria"]:
        f = finals[c["id"]]
        if evidence_missing:
            if c.get("is_evidence_criterion"):
                f["score"] = 0.0
                f["comment"] += " | Không có minh chứng để kiểm chứng → 0 điểm tiêu chí minh chứng."
            else:
                f["score"] = round(f["score"] * 0.5, 2)
                f["comment"] += " | Thiếu minh chứng sử dụng AI → trừ 50% điểm theo quy định."
            f["evidence_penalty"] = True


def part_total(part: str, part_def: dict, finals: dict[str, dict]) -> float:
    total = sum(f["score"] for f in finals.values())
    return round(min(total, part_def["max_score"]), 2)  # Phần E: trần 20 (điểm thưởng không vượt trần)


def g_crosscheck_text(store, submission: dict) -> str:
    """Đối chiếu tự động: các phần B–F có minh chứng thực nộp hay không."""
    items = store.find("submission_items", submission_id=submission["id"])
    lines = []
    for p in ["B", "C", "D", "E", "F"]:
        evs = [i for i in items if i["part"] == p and i["kind"] == "evidence"]
        names = ", ".join((i.get("original_name") or i.get("url") or "?") for i in evs) or "KHÔNG CÓ"
        lines.append(f"- Phần {p}: {len(evs)} minh chứng thực nộp ({names})")
    return "\n".join(lines)


def flag_below_min(part: str, part_def: dict, finals: dict[str, dict]) -> list[str]:
    """Cờ các tiêu chí dưới mức điểm tối thiểu (rubric thuyết minh có khóa 'min')."""
    flags = []
    for c in part_def["criteria"]:
        mn = c.get("min")
        if mn and finals[c["id"]]["score"] < mn:
            flags.append(f"Tiêu chí {c['id']} ({c['name']}) đạt {finals[c['id']]['score']:g} — dưới mức tối thiểu {mn:g}")
    return flags


def grade_part(store, storage, grader: Grader, submission: dict, part: str, rubric: dict) -> dict:
    """Chấm một Phần: 2 lượt (+ lượt 3 nếu lệch), áp quy tắc minh chứng, lưu scores."""
    part_def = rubric["parts"][part]
    evidence_required = rubric.get("evidence_required", False)
    crit_defs = {c["id"]: c for c in part_def["criteria"]}
    items = store.find("submission_items", submission_id=submission["id"])
    products_text, evidence_text = build_part_content(storage, items, part)
    evidence_missing = (
        evidence_required and part != "G"
        and not any(i["part"] == part and i["kind"] == "evidence" for i in items)
    )

    context = {
        "submission_id": submission["id"],
        "part_a": submission.get("part_a", {}),
        "rubric_label": rubric.get("label", ""),
        "research_kind": rubric.get("research_kind", ""),
        "rubric_desc": rubric.get("description", ""),
        "g_crosscheck": g_crosscheck_text(store, submission) if part == "G" else "",
    }

    def run_pass(no: int):
        result = grader.grade(part, part_def, context, products_text, evidence_text, pass_no=no)
        store.add("grading_runs", {
            "submission_id": submission["id"], "part": part, "pass_no": no,
            "model": getattr(grader, "model", grader.name),
            "criteria": [c.model_dump() for c in result.criteria],
            "evidence_findings": result.evidence_findings,
            "anomaly_flags": result.anomaly_flags,
            "created_at": now_vn().isoformat(),
        })
        return result

    r1, r2 = run_pass(1), run_pass(2)
    by1 = {c.id: c for c in r1.criteria}
    by2 = {c.id: c for c in r2.criteria}

    finals: dict[str, dict] = {}
    diverged_ids: list[str] = []
    for cid, cdef in crit_defs.items():
        s1 = by1[cid].score if cid in by1 else 0.0
        s2 = by2[cid].score if cid in by2 else 0.0
        score, needs_third = combine_two_passes(cdef["max"], s1, s2)
        finals[cid] = {
            "criterion_id": cid, "max": cdef["max"], "passes": [s1, s2],
            "score": score, "needs_third_pass": needs_third,
            "comment": (by1.get(cid) or by2.get(cid)).comment if (by1.get(cid) or by2.get(cid)) else "",
            "evidence_ok": (cid in by1 and by1[cid].evidence_ok) and (cid in by2 and by2[cid].evidence_ok),
            "evidence_penalty": False,
        }
        if needs_third:
            diverged_ids.append(cid)

    anomaly_flags = list(dict.fromkeys(r1.anomaly_flags + r2.anomaly_flags))

    if diverged_ids:
        r3 = run_pass(3)
        by3 = {c.id: c for c in r3.criteria}
        anomaly_flags = list(dict.fromkeys(anomaly_flags + r3.anomaly_flags))
        for cid in diverged_ids:
            cdef = crit_defs[cid]
            s1, s2 = finals[cid]["passes"]
            s3 = by3[cid].score if cid in by3 else 0.0
            finals[cid]["passes"] = [s1, s2, s3]
            finals[cid]["score"] = median_of_three(cdef["max"], s1, s2, s3)
            finals[cid]["comment"] += " | Hai lượt chấm lệch >15%, đã chấm lượt 3 và lấy trung vị."

    apply_evidence_rules(part_def, finals, evidence_missing)
    anomaly_flags = list(dict.fromkeys(anomaly_flags + flag_below_min(part, part_def, finals)))

    if evidence_missing:
        anomaly_flags.append(f"Phần {part}: không nộp minh chứng sử dụng AI")

    for cid, f in finals.items():
        store.put("scores", f"{submission['id']}_{part}_{cid}", {
            "submission_id": submission["id"], "part": part, **f,
            "ai_score": f["score"], "ai_comment": f["comment"],
            "council_score": None, "council_comment": "",
            "final_score": f["score"],
            "graded_at": now_vn().isoformat(),
        })

    total = part_total(part, part_def, finals)
    return {"part": part, "total": total, "anomaly_flags": anomaly_flags,
            "evidence_findings": f"{r1.evidence_findings}", "evidence_missing": evidence_missing}


def invalidate_grading(store, submission_id: str) -> None:
    """Xóa checkpoint chấm khi giảng viên sửa hồ sơ — để lần chấm sau (thử hoặc chính thức)
    chấm lại trên nội dung mới, không dùng kết quả cũ."""
    sub = store.get("submissions", submission_id)
    if not sub:
        return
    if sub.get("grading_progress") or sub.get("ai_graded"):
        store.patch("submissions", submission_id, {
            "grading_progress": {}, "part_results": {}, "anomaly_flags": [],
            "ai_graded": False, "ai_total": None,
        })


def grade_submission(store, storage, grader: Grader, submission_id: str,
                     force: bool = False, keep_status: bool = False) -> dict:
    """Chấm toàn bộ hồ sơ (B–G) với checkpoint từng phần.

    keep_status=True: chấm thử theo yêu cầu (Admin/Hội đồng) — KHÔNG đổi trạng thái hồ sơ
    sang 'graded' (giữ nguyên để giảng viên vẫn sửa/nộp được trước hạn). Vẫn lưu điểm,
    nhận xét, review để Hội đồng xem.
    """
    submission = store.get("submissions", submission_id)
    if not submission:
        raise ValueError("Không tìm thấy hồ sơ")
    original_status = submission.get("status")
    rubric = rubric_for(store, submission)
    parts = graded_parts(rubric)
    progress = {} if force else (submission.get("grading_progress") or {})
    part_results = submission.get("part_results") or {}
    all_flags: list[str] = submission.get("anomaly_flags") or [] if not force else []
    store.patch("submissions", submission_id, {"status": "grading"})

    try:
        for part in parts:
            if progress.get(part) and not force:
                continue
            logger.info("Chấm hồ sơ %s — Phần %s", submission_id, part)
            result = grade_part(store, storage, grader, submission, part, rubric)
            part_results[part] = {"total": result["total"], "evidence_missing": result["evidence_missing"]}
            all_flags = list(dict.fromkeys(all_flags + result["anomaly_flags"]))
            progress[part] = True
            store.patch("submissions", submission_id, {
                "grading_progress": progress, "part_results": part_results, "anomaly_flags": all_flags,
            })
    except Exception:
        # Khôi phục trạng thái để không kẹt ở 'grading' (đặc biệt khi chấm thử trước hạn)
        store.patch("submissions", submission_id, {"status": original_status})
        raise

    ai_total = round(sum(p["total"] for p in part_results.values()), 2)
    review_threshold = rubric.get("advance_score") or rubric.get("pass_score") or DEFAULT_MANDATORY_REVIEW_SCORE
    mandatory = ai_total >= review_threshold or bool(all_flags)
    mandatory_reason = []
    if ai_total >= review_threshold:
        mandatory_reason.append(f"Điểm AI {ai_total:g} ≥ {review_threshold:g} (diện xét chọn/đạt) — cần Hội đồng thẩm định")
    if all_flags:
        mandatory_reason.append("Có tiêu chí dưới mức tối thiểu hoặc dấu hiệu bất thường")

    final_status = original_status if keep_status else "graded"
    store.patch("submissions", submission_id, {
        "status": final_status, "ai_total": ai_total,
        "ai_graded": True, "ai_graded_at": now_vn().isoformat(),
    })
    store.put("reviews", submission_id, {
        "submission_id": submission_id, "status": "pending",
        "mandatory": mandatory, "mandatory_reason": "; ".join(mandatory_reason),
        "ai_total": ai_total, "created_at": now_vn().isoformat(),
        "approved_at": None, "total_final": None, "classification": None, "reviewer": None,
    })
    return {"submission_id": submission_id, "ai_total": ai_total, "mandatory": mandatory}


def run_grading(store, storage, grader: Grader, only_ids: list[str] | None = None, force: bool = False) -> dict:
    """Bước 3: chấm mọi hồ sơ đã khóa & hợp lệ. Trả về thống kê. Lỗi hồ sơ nào ghi nhận hồ sơ đó."""
    subs = [s for s in store.all("submissions") if s.get("status") in ("locked", "grading", "graded")]
    if only_ids:
        subs = [s for s in subs if s["id"] in only_ids]
    stats = {"total": 0, "graded": 0, "skipped_invalid": 0, "errors": []}
    for sub in subs:
        stats["total"] += 1
        if not sub.get("valid", False):
            stats["skipped_invalid"] += 1
            continue
        if sub.get("status") == "graded" and not force:
            continue
        try:
            grade_submission(store, storage, grader, sub["id"], force=force)
            stats["graded"] += 1
        except Exception as exc:  # noqa: BLE001 — một hồ sơ lỗi không dừng cả đợt chấm
            logger.exception("Lỗi chấm hồ sơ %s", sub["id"])
            stats["errors"].append({"submission_id": sub["id"], "error": str(exc)})
            store.patch("submissions", sub["id"], {"grading_error": str(exc)})
    return stats
