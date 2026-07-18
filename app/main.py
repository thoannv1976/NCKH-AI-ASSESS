"""DNU AI-Assess — ứng dụng FastAPI chính."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import auth
from app.config import ROLE_ADMIN, ROLE_COUNCIL, get_settings, now_vn
from app.db import create_store
from app.rubric import get_rubric
from app.routers import admin, council, lecturer, reports, tasks
from app.services.ops import get_timeline
from app.storage import create_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_title, docs_url=None, redoc_url=None)

    app.state.store = create_store(settings)
    app.state.storage = create_storage(settings)
    templates = Jinja2Templates(directory=str(settings.base_dir / "app" / "templates"))
    templates.env.globals.update(
        app_mode=settings.app_mode, APP_TITLE=settings.app_title,
        ORG_NAME=settings.org_name, ORG_SHORT=settings.org_short, PROGRAM_YEAR=settings.program_year,
    )
    app.state.templates = templates

    static_dir = settings.base_dir / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)  # thư mục rỗng không được git/Docker giữ → tạo nếu thiếu
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(auth.router)
    app.include_router(lecturer.router)
    app.include_router(lecturer.files_router)
    app.include_router(council.router)
    app.include_router(admin.router)
    app.include_router(reports.router)
    app.include_router(tasks.router)

    # Seed rubric + timeline lần đầu
    get_rubric(app.state.store)
    get_timeline(app.state.store)

    # SEED_DEMO=1: tạo/backfill tài khoản + hồ sơ demo khi khởi động (idempotent — chạy mọi lần
    # để vá mật khẩu cho dữ liệu cũ từ lần deploy trước; không tạo trùng)
    if os.environ.get("SEED_DEMO") == "1":
        from scripts.seed_demo import seed

        try:
            seed(app.state.store, app.state.storage)
        except Exception:  # noqa: BLE001 — seed lỗi không được chặn app khởi động
            logging.getLogger("dnu").exception("Seed demo thất bại")

    # ADMIN_EMAILS: bảo đảm các email này là quản trị viên + đặt/đặt-lại mật khẩu theo ADMIN_PASSWORD
    from app.config import ROLE_ADMIN as _ADMIN
    from app.security import hash_password

    for email in settings.admin_emails:
        existing = app.state.store.find_one("users", email=email)
        if existing:
            fields = {"role": _ADMIN, "active": True}
            # Luôn đặt lại mật khẩu admin theo ADMIN_PASSWORD (bảo đảm đăng nhập được
            # kể cả khi tài khoản cũ thiếu/khác mật khẩu)
            if settings.admin_password:
                fields["password_hash"] = hash_password(settings.admin_password)
            app.state.store.patch("users", existing["id"], fields)
            logging.getLogger("dnu").info("Cập nhật quản trị viên: %s", email)
        else:
            app.state.store.add("users", {
                "email": email, "ho_ten": email.split("@")[0], "ma_gv": "",
                "khoa": "", "bo_mon": "", "role": _ADMIN, "active": True,
                "password_hash": hash_password(settings.admin_password) if settings.admin_password else None,
            })
            logging.getLogger("dnu").info("Tạo quản trị viên từ ADMIN_EMAILS: %s", email)

    _users = app.state.store.all("users")
    logging.getLogger("dnu").info(
        "Khởi động DNU AI-Assess: APP_MODE=%s, SEED_DEMO=%s, %d người dùng (%d có mật khẩu), admin_emails=%s",
        settings.app_mode, os.environ.get("SEED_DEMO", ""), len(_users),
        sum(1 for u in _users if u.get("password_hash")), settings.admin_emails,
    )

    @app.get("/")
    def root(request: Request):
        user = auth.current_user(request)
        if not user:
            return RedirectResponse("/login")
        dest = {ROLE_COUNCIL: "/council", ROLE_ADMIN: "/admin"}.get(user["role"], "/lecturer")
        return RedirectResponse(dest)

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "time": now_vn().isoformat()}

    @app.exception_handler(Exception)
    async def err_handler(request: Request, exc: Exception):
        logging.getLogger("dnu").exception("Lỗi không xử lý: %s", exc)
        return HTMLResponse("<h3>Có lỗi hệ thống. Vui lòng thử lại hoặc liên hệ quản trị viên.</h3>", status_code=500)

    return app


app = create_app()
