"""Endpoint cho Cloud Scheduler (hoặc cron bất kỳ): nhắc hạn 24h và khóa hồ sơ đúng hạn.

Bảo vệ bằng header X-Cron-Token (CRON_TOKEN). Trên Cloud Run production nên dùng
thêm OIDC của Cloud Scheduler (service account invoker).
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings, now_vn, parse_dt
from app.services.ops import get_timeline, lock_all, send_reminders

router = APIRouter(prefix="/tasks")


@router.post("/cron")
def cron(request: Request, x_cron_token: str = Header("")):
    if x_cron_token != get_settings().cron_token:
        raise HTTPException(403, "Sai cron token")
    store = request.app.state.store
    tl = get_timeline(store)
    deadline = parse_dt(tl["deadline"])
    now = now_vn()
    actions: list[str] = []

    # Nhắc các mục còn thiếu trước hạn 24 giờ (một lần)
    if not tl.get("reminder_sent") and deadline - timedelta(hours=24) <= now < deadline:
        sent = send_reminders(store)
        actions.append(f"reminders_sent={sent}")

    # Khóa hồ sơ ngay sau hạn (Bước 1 quy trình chấm)
    if now >= deadline and not tl.get("locked_done"):
        result = lock_all(store, None)
        actions.append(f"locked={result['locked']} invalid={result['invalid']}")

    return {"ok": True, "now": now.isoformat(), "actions": actions}
