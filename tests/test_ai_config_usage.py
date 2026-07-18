"""Test cấu hình AI do Admin nạp + thống kê sử dụng (số lần gọi, token, chi phí)."""
from types import SimpleNamespace

from app.services.ai_config import get_ai_config, set_ai_config
from app.services.ai_usage import cost_usd, get_stats, record_usage, reset_stats
from app.services.grading.graders import (
    MockGrader,
    create_grader,
    friendly_ai_error,
    is_transient_error,
)
from tests.conftest import login


class _Overloaded(Exception):
    status_code = 529


class _AuthError(Exception):
    status_code = 401


class OverloadedError(Exception):  # phân loại theo tên lớp (SDK anthropic)
    pass


class APIConnectionError(Exception):
    pass


def test_is_transient_error_classification():
    assert is_transient_error(_Overloaded()) is True          # 529 quá tải
    assert is_transient_error(OverloadedError()) is True       # theo tên lớp
    assert is_transient_error(APIConnectionError()) is True    # lỗi mạng
    assert is_transient_error(_AuthError()) is False           # 401 key sai → không thử lại
    assert is_transient_error(ValueError("schema")) is False   # không phải lỗi API


def test_friendly_ai_error_messages():
    overloaded = friendly_ai_error(_Overloaded())
    assert "quá tải" in overloaded and "529" in overloaded and "API key" in overloaded
    assert "không hợp lệ" in friendly_ai_error(_AuthError())
    assert "404" in friendly_ai_error(type("NotFoundError", (Exception,), {"status_code": 404})(), "model-x")


def test_cost_estimate_opus():
    # Opus 4.8: input 5$/MTok, output 25$/MTok → 1tr in + 1tr out = 30$
    assert abs(cost_usd("claude-opus-4-8", 1_000_000, 1_000_000) - 30.0) < 1e-6
    # cache đọc 0.1×, cache tạo 1.25×
    c = cost_usd("claude-opus-4-8", 0, 0, cache_read=1_000_000, cache_creation=1_000_000)
    assert abs(c - (0.5 + 6.25)) < 1e-6


def test_record_and_aggregate_usage(store):
    store.wipe()
    record_usage(store, "claude-opus-4-8",
                 SimpleNamespace(input_tokens=10_000, output_tokens=2_000,
                                 cache_read_input_tokens=5_000, cache_creation_input_tokens=0))
    record_usage(store, "claude-opus-4-8",
                 SimpleNamespace(input_tokens=20_000, output_tokens=3_000,
                                 cache_read_input_tokens=0, cache_creation_input_tokens=0))
    stats = get_stats(store)
    assert stats["calls"] == 2
    assert stats["input"] == 30_000
    assert stats["output"] == 5_000
    assert stats["cache_read"] == 5_000
    assert stats["cost_usd"] > 0
    assert "claude-opus-4-8" in stats["by_model"]
    assert stats["by_model"]["claude-opus-4-8"]["calls"] == 2
    assert reset_stats(store) == 2
    assert get_stats(store)["calls"] == 0


def test_ai_config_db_overrides_env(store):
    store.wipe()
    # Mặc định chưa cấu hình → mock (test env không có ANTHROPIC_API_KEY)
    assert get_ai_config(store)["grader"] == "mock"
    set_ai_config(store, api_key="sk-ant-test-12345678", model="claude-opus-4-8", grader="auto")
    cfg = get_ai_config(store)
    assert cfg["has_key"] and cfg["grader"] == "claude" and cfg["key_source"] == "DB"
    assert cfg["key_hint"].endswith("5678")
    # ép mock dù có key
    set_ai_config(store, grader="mock")
    assert get_ai_config(store)["grader"] == "mock"
    # xóa key
    set_ai_config(store, grader="auto", clear_key=True)
    assert get_ai_config(store)["has_key"] is False


def test_create_grader_uses_db_config(store):
    store.wipe()
    # không key → mock
    assert isinstance(create_grader(None, store), MockGrader)
    # có key + auto → ClaudeGrader (không gọi API khi khởi tạo)
    set_ai_config(store, api_key="sk-ant-abc", grader="claude")
    g = create_grader(None, store)
    assert g.name == "claude"
    assert callable(g.on_usage)  # có ghi nhận usage


def test_admin_can_set_ai_config_and_view_usage(client, store):
    login(client, "admin@dainam.edu.vn")
    r = client.post("/admin/config/ai",
                    data={"api_key": "sk-ant-xyz9999", "model": "claude-opus-4-8", "grader": "auto"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert get_ai_config(store)["has_key"]
    # API key KHÔNG hiển thị nguyên văn trên trang cấu hình
    page = client.get("/admin/config").text
    assert "sk-ant-xyz9999" not in page
    assert "Đã cấu hình" in page
    # trang thống kê mở được
    assert client.get("/admin/ai-usage").status_code == 200


def test_lecturer_cannot_access_ai_pages(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.get("/admin/ai-usage", follow_redirects=False).status_code == 403
    assert client.post("/admin/config/ai", data={"grader": "mock"}, follow_redirects=False).status_code == 403
