"""Phân hệ nộp hồ sơ — dành cho giảng viên."""
from __future__ import annotations

import re
import time

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.config import (
    GRADED_PARTS, ROLE_ADMIN, ROLE_COUNCIL, ROLE_LECTURER, now_vn, parse_dt,
)
from app.auth import require_role
from app.db import new_id
from app.rubric import get_rubric
from app.services import audit
from app.services.emailer import email_submit_confirmation
from app.services.grading.engine import invalidate_grading
from app.services.ops import appeal_window_open, deadline_passed, get_timeline
from app.services.validation import check_extension, check_link, check_naming, check_size, completeness

router = APIRouter(prefix="/lecturer")
lecturer_dep = Depends(require_role(ROLE_LECTURER))


def get_submission(store, user: dict) -> dict:
    sub = store.find_one("submissions", user_id=user["id"])
    if not sub:
        sub = {
            "id": new_id(), "user_id": user["id"], "status": "draft",
            "part_a": {"ho_ten": user.get("ho_ten", ""), "ma_gv": user.get("ma_gv", ""),
                       "khoa_bo_mon": " - ".join(x for x in [user.get("khoa", ""), user.get("bo_mon", "")] if x)},
            "created_at": now_vn().isoformat(),
        }
        store.put("submissions", sub["id"], sub)
    return sub


def ensure_editable(store, sub: dict) -> None:
    if deadline_passed(store) or sub.get("status") not in ("draft", "submitted"):
        raise HTTPException(400, "Đã quá hạn nộp hoặc hồ sơ đã bị khóa — không thể chỉnh sửa. "
                                 "Nếu Nhà trường vừa gia hạn, hãy đề nghị Quản trị viên mở khóa hồ sơ.")


def mark_dirty(store, sub: dict) -> None:
    """Giảng viên vừa thay đổi hồ sơ → xóa kết quả chấm thử cũ (nếu có) để chấm lại trên nội dung mới."""
    invalidate_grading(store, sub["id"])


def render(request: Request, template: str, user: dict, **ctx):
    return request.app.state.templates.TemplateResponse(
        request, template, {"user": user, "now": now_vn(), **ctx}
    )


@router.get("")
def dashboard(request: Request, user: dict = lecturer_dep):
    store = request.app.state.store
    sub = get_submission(store, user)
    rubric = get_rubric(store)
    summary = completeness(store, sub)
    items = store.find("submission_items", submission_id=sub["id"])
    tl = get_timeline(store)
    try:
        deadline_str = f"{parse_dt(tl['deadline']):%Hh%M ngày %d/%m/%Y}"
    except Exception:  # noqa: BLE001 — hạn nộp định dạng lạ thì hiện nguyên văn
        deadline_str = tl.get("deadline", "")
    return render(request, "lecturer/dashboard.html", user, sub=sub, rubric=rubric,
                  summary=summary, items=items, timeline=tl, deadline_str=deadline_str,
                  deadline_passed=deadline_passed(store), parts=GRADED_PARTS)


@router.get("/part-a")
def part_a_form(request: Request, user: dict = lecturer_dep):
    store = request.app.state.store
    sub = get_submission(store, user)
    return render(request, "lecturer/part_a.html", user, sub=sub,
                  rubric=get_rubric(store), deadline_passed=deadline_passed(store))


@router.post("/part-a")
def part_a_save(
    request: Request,
    user: dict = lecturer_dep,
    ho_ten: str = Form(""),
    ma_gv: str = Form(""),
    khoa_bo_mon: str = Form(""),
    hoc_phan: str = Form(""),
    cong_cu_ai: str = Form(""),
    muc_thanh_thao: int = Form(0),
):
    store = request.app.state.store
    sub = get_submission(store, user)
    ensure_editable(store, sub)
    tools = [t.strip() for t in re.split(r"[,;\n]", cong_cu_ai) if t.strip()]
    part_a = {
        "ho_ten": ho_ten.strip(), "ma_gv": ma_gv.strip(), "khoa_bo_mon": khoa_bo_mon.strip(),
        "hoc_phan": hoc_phan.strip(), "cong_cu_ai": tools,
        "muc_thanh_thao": muc_thanh_thao if 1 <= muc_thanh_thao <= 5 else None,
    }
    store.patch("submissions", sub["id"], {"part_a": part_a})
    mark_dirty(store, sub)
    return RedirectResponse("/lecturer?saved=A", status_code=303)


@router.get("/part/{part}")
def part_page(part: str, request: Request, user: dict = lecturer_dep):
    part = part.upper()
    if part not in GRADED_PARTS:
        raise HTTPException(404)
    store = request.app.state.store
    sub = get_submission(store, user)
    rubric = get_rubric(store)
    items = [i for i in store.find("submission_items", submission_id=sub["id"]) if i["part"] == part]
    return render(request, "lecturer/part_edit.html", user, sub=sub, part=part,
                  part_def=rubric["parts"][part], items=items,
                  deadline_passed=deadline_passed(store), ma_gv=sub.get("part_a", {}).get("ma_gv", ""))


@router.post("/part/{part}/upload")
async def upload_file(part: str, request: Request, kind: str = Form(...),
                      files: list[UploadFile] = File(default=[]), user: dict = lecturer_dep):
    """Tải lên MỘT hoặc NHIỀU tệp cùng lúc. Tệp lỗi (sai định dạng/quá 200MB) được bỏ qua
    và báo lại; các tệp hợp lệ vẫn được lưu."""
    part = part.upper()
    if part not in GRADED_PARTS or kind not in ("product", "evidence"):
        raise HTTPException(404)
    store, storage = request.app.state.store, request.app.state.storage
    sub = get_submission(store, user)
    ensure_editable(store, sub)

    chosen = [f for f in (files or []) if f is not None and f.filename]
    if not chosen:
        raise HTTPException(400, "Chưa chọn tệp")

    ma_gv = sub.get("part_a", {}).get("ma_gv", "") or user.get("ma_gv", "")
    uploaded, errors = 0, []
    for file in chosen:
        err = check_extension(file.filename)
        if err:
            errors.append(f"{file.filename}: {err}")
            continue
        safe_name = re.sub(r"[^\w\.\-]", "_", file.filename, flags=re.UNICODE)
        key = f"{sub['id']}/{part}/{kind}/{int(time.time() * 1000)}_{safe_name}"
        size = storage.save(key, file.file)
        err = check_size(size)
        if err:
            storage.delete(key)
            errors.append(f"{file.filename}: {err}")
            continue
        store.put("submission_items", new_id(), {
            "submission_id": sub["id"], "part": part, "kind": kind,
            "type": "file", "storage_path": key, "original_name": file.filename,
            "size": size, "content_type": file.content_type,
            "naming_warning": check_naming(file.filename, ma_gv, part) if ma_gv else None,
            "uploaded_at": now_vn().isoformat(),
        })
        uploaded += 1

    if uploaded:
        mark_dirty(store, sub)
    params = f"uploaded={uploaded}"
    if errors:
        from urllib.parse import quote

        params += "&upload_errors=" + quote(" | ".join(errors))
    return RedirectResponse(f"/lecturer/part/{part}?{params}", status_code=303)


@router.post("/part/{part}/link")
def add_link(part: str, request: Request, kind: str = Form(...), url: str = Form(...),
             label: str = Form(""), user: dict = lecturer_dep):
    part = part.upper()
    if part not in GRADED_PARTS or kind not in ("product", "evidence"):
        raise HTTPException(404)
    store = request.app.state.store
    sub = get_submission(store, user)
    ensure_editable(store, sub)
    url = url.strip()
    ok, note = check_link(url)
    snapshot = ""
    if ok:
        try:
            html = httpx.get(url, timeout=8, follow_redirects=True,
                             headers={"User-Agent": "DNU-AI-Assess/1.0"}).text
            snapshot = re.sub(r"<[^>]+>", " ", html)
            snapshot = re.sub(r"\s+", " ", snapshot)[:20000]
        except Exception:  # noqa: BLE001 — snapshot là best-effort
            snapshot = ""
    item = {
        "id": new_id(), "submission_id": sub["id"], "part": part, "kind": kind,
        "type": "link", "url": url, "original_name": label.strip() or url,
        "link_ok": ok, "link_note": note, "link_snapshot": snapshot,
        "uploaded_at": now_vn().isoformat(),
    }
    store.put("submission_items", item["id"], item)
    mark_dirty(store, sub)
    return RedirectResponse(f"/lecturer/part/{part}?linked=1", status_code=303)


@router.post("/item/{item_id}/delete")
def delete_item(item_id: str, request: Request, user: dict = lecturer_dep):
    store, storage = request.app.state.store, request.app.state.storage
    sub = get_submission(store, user)
    ensure_editable(store, sub)
    item = store.get("submission_items", item_id)
    if not item or item["submission_id"] != sub["id"]:
        raise HTTPException(404)
    if item["type"] == "file":
        storage.delete(item["storage_path"])
    store.delete("submission_items", item_id)
    mark_dirty(store, sub)
    return RedirectResponse(f"/lecturer/part/{item['part']}?deleted=1", status_code=303)


@router.post("/submit")
def submit(request: Request, user: dict = lecturer_dep):
    store = request.app.state.store
    sub = get_submission(store, user)
    ensure_editable(store, sub)
    summary = completeness(store, sub)
    if not summary["A"]["ok"]:
        raise HTTPException(400, "Phần A chưa đầy đủ: " + ", ".join(summary["A"]["missing"]))
    store.patch("submissions", sub["id"], {
        "status": "submitted", "submitted_at": now_vn().isoformat(),
        "valid": summary["valid"], "validation": summary,
    })
    audit.log(store, user, "submit", f"submissions/{sub['id']}",
              note=f"Nộp hồ sơ; cảnh báo: {len(summary['warnings'])}")
    email_submit_confirmation(store, user, summary)
    return RedirectResponse("/lecturer?submitted=1", status_code=303)


@router.get("/result")
def result(request: Request, user: dict = lecturer_dep):
    store = request.app.state.store
    sub = get_submission(store, user)
    if sub.get("status") != "published":
        return render(request, "lecturer/result.html", user, sub=sub, published=False,
                      review=None, scores={}, rubric=get_rubric(store), appeal=None, appeal_open=False)
    review = store.get("reviews", sub["id"])
    scores = store.find("scores", submission_id=sub["id"])
    by_part: dict[str, list] = {}
    for s in sorted(scores, key=lambda x: x["criterion_id"]):
        by_part.setdefault(s["part"], []).append(s)
    appeal = store.find_one("appeals", submission_id=sub["id"])
    return render(request, "lecturer/result.html", user, sub=sub, published=True,
                  review=review, scores=by_part, rubric=get_rubric(store), appeal=appeal,
                  appeal_open=appeal_window_open(sub["published_at"]))


@router.post("/appeal")
def appeal(request: Request, content: str = Form(...), user: dict = lecturer_dep):
    store = request.app.state.store
    sub = get_submission(store, user)
    if sub.get("status") != "published":
        raise HTTPException(400, "Kết quả chưa công bố")
    if not appeal_window_open(sub["published_at"]):
        raise HTTPException(400, "Đã hết thời hạn phản hồi (03 ngày làm việc kể từ ngày công bố)")
    if store.find_one("appeals", submission_id=sub["id"]):
        raise HTTPException(400, "Thầy/cô đã gửi phản hồi; vui lòng chờ Hội đồng xem xét")
    store.add("appeals", {
        "submission_id": sub["id"], "user_id": user["id"], "content": content.strip(),
        "status": "open", "resolution": "", "created_at": now_vn().isoformat(),
    })
    audit.log(store, user, "appeal", f"submissions/{sub['id']}")
    return RedirectResponse("/lecturer/result?appealed=1", status_code=303)


# ---- tải tệp (dùng chung cho GV chủ hồ sơ, Hội đồng, quản trị) ----

files_router = APIRouter()


@files_router.get("/file/{item_id}")
def download(item_id: str, request: Request, user: dict = Depends(require_role(ROLE_LECTURER, ROLE_COUNCIL, ROLE_ADMIN))):
    store, storage = request.app.state.store, request.app.state.storage
    item = store.get("submission_items", item_id)
    if not item or item["type"] != "file":
        raise HTTPException(404)
    if user["role"] == ROLE_LECTURER:
        sub = store.get("submissions", item["submission_id"])
        if not sub or sub["user_id"] != user["id"]:
            raise HTTPException(403)
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    f = storage.open(item["storage_path"])
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(item['original_name'])}"}
    return StreamingResponse(f, media_type=item.get("content_type") or "application/octet-stream", headers=headers)
