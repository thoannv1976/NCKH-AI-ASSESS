"""Phân trang 50 hồ sơ/trang cho trang Thẩm định (council) và Tải sản phẩm (downloads)."""
from app.db import new_id
from tests.conftest import login


def _make_subs(store, n):
    """Tạo n giảng viên + hồ sơ đã nộp trực tiếp trong store."""
    for i in range(n):
        uid = f"plg-{i}"
        store.put("users", uid, {
            "id": uid, "ma_gv": f"P{i:03d}", "ho_ten": f"GV {i}",
            "email": f"p{i}@x.edu.vn", "khoa": "CNTT", "role": "lecturer", "active": True,
        })
        sid = new_id()
        store.put("submissions", sid, {"id": sid, "user_id": uid, "status": "submitted"})


def test_council_list_pagination(client, store):
    _make_subs(store, 60)  # 60 hồ sơ → 2 trang (50/trang)
    login(client, "hd@dainam.edu.vn")
    r1 = client.get("/council")
    assert r1.status_code == 200
    assert "Trang 1/2" in r1.text
    assert r1.text.count("Thẩm định →") == 50
    r2 = client.get("/council", params={"page": 2})
    assert r2.text.count("Thẩm định →") == 10


def test_downloads_pagination(client, store):
    _make_subs(store, 60)
    login(client, "admin@dainam.edu.vn")
    r1 = client.get("/admin/downloads")
    assert r1.status_code == 200
    assert "Trang 1/2" in r1.text
    assert r1.text.count("/download.zip") == 50   # liên kết ZIP từng hồ sơ
    r2 = client.get("/admin/downloads", params={"page": 2})
    assert r2.text.count("/download.zip") == 10
