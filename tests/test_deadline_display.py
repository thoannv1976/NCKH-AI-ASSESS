"""Trang giảng viên phải hiển thị HẠN NỘP THẬT (theo cấu hình), không ghi cứng ngày."""
from app.services.ops import get_timeline
from tests.conftest import login


def test_lecturer_dashboard_shows_configured_deadline(client, store):
    tl = get_timeline(store)
    tl["deadline"] = "2026-07-08T17:00:00+07:00"
    store.put("config", "timeline", tl)

    login(client, "gv001@dainam.edu.vn")
    html = client.get("/lecturer").text
    assert "08/07/2026" in html          # đọc đúng hạn đã cấu hình
    assert "30/6/2026" not in html       # không còn ngày ghi cứng cũ
