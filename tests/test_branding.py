"""Test tên trường (ORG_NAME/ORG_SHORT) cấu hình được — phục vụ bàn giao nhiều trường."""
import os

from fastapi.testclient import TestClient

from app.config import reset_settings


def _with_org(name: str, short: str):
    os.environ["ORG_NAME"] = name
    os.environ["ORG_SHORT"] = short
    reset_settings()


def _clear_org():
    os.environ.pop("ORG_NAME", None)
    os.environ.pop("ORG_SHORT", None)
    reset_settings()


def test_login_page_shows_configured_org():
    _with_org("Trường Đại học Thử Nghiệm", "TN")
    try:
        from app.main import create_app

        with TestClient(create_app()) as c:
            html = c.get("/login").text
            assert "Trường Đại học Thử Nghiệm" in html
            assert "TN NCKH-Assess" in html
            assert "Đại Nam" not in html
            assert "Ngoại thương" not in html
    finally:
        _clear_org()


def test_grading_prompt_uses_configured_org():
    _with_org("Trường ZZ", "ZZ")
    try:
        from app.rubric import load_rubric_seed
        from app.services.grading.prompts import system_prompt

        tm = load_rubric_seed()["types"]["thuyet_minh"]["parts"]["TM"]
        sp = system_prompt("TM", tm)
        assert "Trường ZZ (ZZ)" in sp
    finally:
        _clear_org()
