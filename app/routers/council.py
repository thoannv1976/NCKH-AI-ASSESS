"""Phân hệ thẩm định — dành cho Hội đồng đánh giá cấp Trường."""
from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_role
from app.config import GRADED_PARTS, ROLE_ADMIN, ROLE_COUNCIL, get_settings, now_vn
from app.rubric import get_rubric
from app.services import audit
from app.services.grading.engine import grade_submission
from app.services.grading.graders import create_grader
from app.services.ops import approve_submission, grade_job_stale, part_totals_final

router = APIRouter(prefix="/council")
council_dep = Depends(require_role(ROLE_COUNCIL, ROLE_ADMIN))


def render(request: Request, template: str, user: dict, **ctx):
    return request.app.state.templates.TemplateResponse(request, template, {"user": user, "now": now_vn(), **ctx})


@router.get("")
def list_submissions(request: Request, khoa: str = "", status: str = "", page: int = 1,
                     user: dict = council_dep):
    store = request.app.state.store
    subs = store.all("submissions")
    users = {u["id"]: u for u in store.all("users")}
    reviews = {r["submission_id"]: r for r in store.all("reviews")}
    rows = []
    for s in subs:
        if s.get("status") in ("draft",):
            continue
        u = users.get(s["user_id"], {})
        if khoa and u.get("khoa") != khoa:
            continue
        if status and s.get("status") != status:
            continue
        rows.append({"sub": s, "user": u, "review": reviews.get(s["id"])})
    rows.sort(key=lambda r: (
        not (r["review"] or {}).get("mandatory", False),
        -(r["sub"].get("ai_total") or 0),
    ))
    total = len(rows)
    per_page = 50
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    khoas = sorted({u.get("khoa", "") for u in users.values() if u.get("khoa")})
    return render(request, "council/list.html", user, rows=rows[start:start + per_page], khoas=khoas,
                  khoa=khoa, status=status, total=total, page=page, pages=pages, per_page=per_page)


@router.get("/submission/{sid}")
def detail(sid: str, request: Request, user: dict = council_dep):
    store = request.app.state.store
    sub = store.get("submissions", sid)
    if not sub:
        raise HTTPException(404)
    owner = store.get("users", sub["user_id"])
    rubric = get_rubric(store)
    review = store.get("reviews", sid)
    items = store.find("submission_items", submission_id=sid)
    scores = store.find("scores", submission_id=sid)
    by_part: dict[str, list] = {}
    for s in sorted(scores, key=lambda x: x["criterion_id"]):
        by_part.setdefault(s["part"], []).append(s)
    totals = part_totals_final(store, sid)
    appeal = store.find_one("appeals", submission_id=sid)
    return render(request, "council/detail.html", user, sub=sub, owner=owner, rubric=rubric,
                  review=review, items=items, scores=by_part, totals=totals,
                  total_now=round(sum(totals.values()), 2), parts=GRADED_PARTS, appeal=appeal,
                  grade_job=sub.get("grade_job") or {})


@router.post("/submission/{sid}/grade")
def grade_one(sid: str, request: Request, user: dict = council_dep):
    """Chấm tự động MỘT giảng viên theo yêu cầu (Admin/Hội đồng), chạy nền.

    - Trước hạn (hồ sơ draft/submitted): chấm thử, GIỮ trạng thái để giảng viên vẫn sửa/nộp được.
    - Sau hạn (hồ sơ đã khóa): chấm chính thức → chuyển trạng thái 'graded' để Hội đồng phê duyệt.
    - Hồ sơ đã phê duyệt/công bố: không chấm lại (tránh xóa kết quả đã chốt).
    """
    app = request.app
    store, storage = app.state.store, app.state.storage
    sub = store.get("submissions", sid)
    if not sub:
        raise HTTPException(404)
    if sub.get("status") in ("approved", "published"):
        raise HTTPException(400, "Hồ sơ đã được phê duyệt/công bố — không thể chấm lại.")
    job = sub.get("grade_job") or {}
    # Đang chấm thật sự thì chặn; nhưng job 'treo' quá lâu (Cloud Run cắt CPU) thì cho chấm lại.
    if job.get("running") and not grade_job_stale(job):
        raise HTTPException(400, "Hồ sơ này đang được chấm")
    keep_status = sub.get("status") in ("draft", "submitted")  # trước hạn → giữ trạng thái
    prev_status = sub.get("status")
    if prev_status == "grading":  # đang kẹt/chấm lại → lấy trạng thái gốc từ job cũ
        prev_status = job.get("prev_status") or "submitted"
    grader = create_grader(get_settings(), store)
    store.patch("submissions", sid, {"grade_job": {
        "running": True, "started_at": now_vn().isoformat(), "prev_status": prev_status,
        "by": user["email"], "grader": grader.name, "error": None,
    }})
    audit.log(store, user, "grade_one", f"submissions/{sid}",
              note=f"Chấm theo yêu cầu (grader={grader.name}, "
                   f"{'chấm thử giữ trạng thái' if keep_status else 'chấm chính thức'})")

    def worker():
        job = {"running": False, "finished_at": now_vn().isoformat(),
               "by": user["email"], "grader": grader.name, "error": None}
        try:
            grade_submission(store, storage, grader, sid, force=True, keep_status=keep_status)
        except Exception as exc:  # noqa: BLE001 — ghi lỗi để hiển thị, không làm sập tiến trình
            job["error"] = str(exc)
        store.patch("submissions", sid, {"grade_job": job})

    threading.Thread(target=worker, daemon=True).start()
    return RedirectResponse(f"/council/submission/{sid}?grading=started", status_code=303)


@router.get("/submission/{sid}/download.zip")
def download_submission(sid: str, request: Request, user: dict = council_dep):
    """Tải toàn bộ sản phẩm + minh chứng của một giảng viên (ZIP, theo luồng)."""
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.services.downloads import folder_name, stream_zip

    store, storage = request.app.state.store, request.app.state.storage
    sub = store.get("submissions", sid)
    if not sub:
        raise HTTPException(404)
    owner = store.get("users", sub["user_id"]) or {}
    audit.log(store, user, "download_submission", f"submissions/{sid}")
    fname = f"{folder_name(owner)}.zip"
    return StreamingResponse(stream_zip(store, storage, [sub]), media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}",
        "X-Accel-Buffering": "no",
    })


def _report_ctx_or_404(request: Request, sid: str):
    from app.services.report import build_report_context

    ctx = build_report_context(request.app.state.store, sid)
    if not ctx:
        raise HTTPException(400, "Hồ sơ chưa được chấm — chưa thể xuất phiếu đánh giá.")
    return ctx


@router.get("/submission/{sid}/report.docx")
def report_docx(sid: str, request: Request, user: dict = council_dep):
    from urllib.parse import quote

    from fastapi.responses import Response

    from app.services.report import report_to_docx

    ctx = _report_ctx_or_404(request, sid)
    audit.log(request.app.state.store, user, "report_docx", f"submissions/{sid}")
    return Response(report_to_docx(ctx),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(ctx['filename_base'])}.docx"})


@router.get("/submission/{sid}/report.pdf")
def report_pdf(sid: str, request: Request, user: dict = council_dep):
    from urllib.parse import quote

    from fastapi.responses import Response

    from app.services.report import report_to_pdf

    ctx = _report_ctx_or_404(request, sid)
    audit.log(request.app.state.store, user, "report_pdf", f"submissions/{sid}")
    return Response(report_to_pdf(ctx), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(ctx['filename_base'])}.pdf"})


@router.post("/submission/{sid}/score")
def adjust_score(sid: str, request: Request, score_id: str = Form(...),
                 council_score: float = Form(...), reason: str = Form(...), user: dict = council_dep):
    store = request.app.state.store
    score = store.get("scores", score_id)
    if not score or score["submission_id"] != sid:
        raise HTTPException(404)
    if not reason.strip():
        raise HTTPException(400, "Bắt buộc ghi lý do điều chỉnh")
    if not 0 <= council_score <= score["max"]:
        raise HTTPException(400, f"Điểm phải trong khoảng 0–{score['max']}")
    before = {"final_score": score["final_score"], "council_score": score.get("council_score")}
    score.update({
        "council_score": round(council_score, 2),
        "council_comment": reason.strip(),
        "final_score": round(council_score, 2),
        "adjusted_by": user["email"], "adjusted_at": now_vn().isoformat(),
    })
    store.put("scores", score_id, score)
    audit.log(store, user, "adjust_score", f"scores/{score_id}", before=before,
              after={"final_score": score["final_score"]}, note=reason.strip())
    return RedirectResponse(f"/council/submission/{sid}#part-{score['part']}", status_code=303)


@router.post("/submission/{sid}/approve")
def approve(sid: str, request: Request, user: dict = council_dep):
    store = request.app.state.store
    sub = store.get("submissions", sid)
    if not sub or sub.get("status") not in ("graded", "approved"):
        raise HTTPException(400, "Hồ sơ chưa được chấm xong")
    approve_submission(store, sid, user)
    return RedirectResponse(f"/council/submission/{sid}?approved=1", status_code=303)


@router.get("/appeals")
def appeals(request: Request, user: dict = council_dep):
    store = request.app.state.store
    rows = []
    for a in sorted(store.all("appeals"), key=lambda x: x["created_at"], reverse=True):
        sub = store.get("submissions", a["submission_id"])
        owner = store.get("users", a["user_id"])
        rows.append({"appeal": a, "sub": sub, "user": owner})
    return render(request, "council/appeals.html", user, rows=rows)


@router.post("/appeal/{aid}/resolve")
def resolve_appeal(aid: str, request: Request, resolution: str = Form(...), user: dict = council_dep):
    store = request.app.state.store
    a = store.get("appeals", aid)
    if not a:
        raise HTTPException(404)
    store.patch("appeals", aid, {
        "status": "resolved", "resolution": resolution.strip(),
        "resolved_by": user["email"], "resolved_at": now_vn().isoformat(),
    })
    audit.log(store, user, "resolve_appeal", f"appeals/{aid}", note=resolution.strip())
    return RedirectResponse("/council/appeals?resolved=1", status_code=303)
