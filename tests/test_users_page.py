"""Test phân trang + tìm kiếm trang quản lý người dùng."""
from tests.conftest import login


def _bulk_import(client, n):
    rows = ["ma_gv,ho_ten,email,don_vi,chuc_vu,role"]
    for i in range(n):
        rows.append(f"GVX{i:03d},Giảng viên {i},gvx{i:03d}@dnu.edu.vn,Khoa {i % 3},Giảng viên,lecturer")
    client.post("/admin/users/import", data={"csv_text": "\n".join(rows)}, follow_redirects=False)


def test_users_pagination(client, store):
    login(client, "admin@dainam.edu.vn")
    _bulk_import(client, 60)  # + 4 tài khoản seed = 64 → 2 trang (50/trang)
    r1 = client.get("/admin/users")
    assert r1.status_code == 200
    assert "Người dùng (64)" in r1.text
    assert "Trang 1/2" in r1.text
    assert r1.text.count("/toggle") == 50          # đúng 50 dòng/trang
    r2 = client.get("/admin/users", params={"page": 2})
    assert r2.text.count("/toggle") == 14          # 64 - 50


def test_users_search_filters(client, store):
    login(client, "admin@dainam.edu.vn")
    _bulk_import(client, 60)
    r = client.get("/admin/users", params={"q": "gvx042"})
    assert r.status_code == 200
    assert "gvx042@dnu.edu.vn" in r.text
    assert "(đã lọc)" in r.text
    assert r.text.count("/toggle") == 1            # chỉ 1 kết quả khớp
