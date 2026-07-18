"""Xác thực & phân quyền — đăng nhập bằng ID (email hoặc mã giảng viên) + mật khẩu.

Mật khẩu băm PBKDF2 (app/security.py). Phiên đăng nhập lưu trong cookie ký
(itsdangerous), hết hạn sau 12 giờ. Phân quyền 3 vai trò: giảng viên / hội đồng / quản trị.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import ROLE_ADMIN, ROLE_COUNCIL, ROLE_LECTURER, get_settings
from app.security import hash_password, verify_password

SESSION_COOKIE = "dnu_session"
SESSION_MAX_AGE = 12 * 3600

router = APIRouter()


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="dnu-session")


def create_session_cookie(user: dict) -> str:
    return _serializer().dumps({"uid": user["id"], "email": user["email"], "role": user["role"]})


def read_session(request: Request) -> dict | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        return _serializer().loads(raw, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None


def current_user(request: Request) -> dict | None:
    sess = read_session(request)
    if not sess:
        return None
    user = request.app.state.store.get("users", sess["uid"])
    if not user or not user.get("active", True):
        return None
    return user


def require_user(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_role(*roles: str):
    def dep(request: Request) -> dict:
        user = require_user(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập chức năng này")
        return user

    return dep


def find_by_login(store, login_id: str) -> dict | None:
    """Tìm người dùng theo email (không phân biệt hoa thường) hoặc mã giảng viên."""
    login_id = login_id.strip()
    user = store.find_one("users", email=login_id.lower())
    if user:
        return user
    # so khớp mã GV (không phân biệt hoa thường)
    for u in store.all("users"):
        if (u.get("ma_gv") or "").strip().lower() == login_id.lower() and login_id:
            return u
    return None


def set_password(store, user: dict, password: str) -> None:
    store.patch("users", user["id"], {"password_hash": hash_password(password)})


def _login_ok(user: dict) -> RedirectResponse:
    dest = {ROLE_LECTURER: "/lecturer", ROLE_COUNCIL: "/council", ROLE_ADMIN: "/admin"}.get(user["role"], "/")
    resp = RedirectResponse(dest, status_code=303)
    resp.set_cookie(
        SESSION_COOKIE, create_session_cookie(user),
        max_age=SESSION_MAX_AGE, httponly=True, samesite="lax",
        secure=get_settings().app_mode == "gcp",
    )
    return resp


@router.get("/login")
def login_page(request: Request, error: str = ""):
    return request.app.state.templates.TemplateResponse(
        request, "login.html", {"settings": get_settings(), "user": None, "error": error},
    )


@router.post("/login")
def login(request: Request, login_id: str = Form(...), password: str = Form(...)):
    store = request.app.state.store
    user = find_by_login(store, login_id)
    if not user or not user.get("active", True) or not verify_password(password, user.get("password_hash")):
        return request.app.state.templates.TemplateResponse(
            request, "login.html",
            {"settings": get_settings(), "user": None,
             "error": "Sai ID hoặc mật khẩu (hoặc tài khoản đã bị khóa)."},
            status_code=401,
        )
    return _login_ok(user)


@router.get("/change-password")
def change_password_page(request: Request, error: str = "", ok: str = ""):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request, "change_password.html", {"user": user, "error": error, "ok": ok},
    )


@router.post("/change-password")
def change_password(request: Request, current: str = Form(...),
                    new_password: str = Form(...), confirm: str = Form(...)):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    store = request.app.state.store
    if not verify_password(current, user.get("password_hash")):
        return RedirectResponse("/change-password?error=Mật+khẩu+hiện+tại+không+đúng", status_code=303)
    if len(new_password) < 6:
        return RedirectResponse("/change-password?error=Mật+khẩu+mới+tối+thiểu+6+ký+tự", status_code=303)
    if new_password != confirm:
        return RedirectResponse("/change-password?error=Xác+nhận+mật+khẩu+không+khớp", status_code=303)
    set_password(store, user, new_password)
    return RedirectResponse("/change-password?ok=1", status_code=303)


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
