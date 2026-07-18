"""Test bootstrap quản trị viên (ADMIN_EMAILS + ADMIN_PASSWORD) và quản trị mật khẩu người dùng."""
import os

from fastapi.testclient import TestClient

from app.config import reset_settings
from tests.conftest import login


def _fresh_app():
    reset_settings()
    from app.main import create_app

    return create_app()


def test_admin_emails_bootstrap_with_password(store):
    store.wipe()
    os.environ["ADMIN_EMAILS"] = "hoanganh.goldenlight@gmail.com"
    os.environ["ADMIN_PASSWORD"] = "BanToChuc@2026"
    try:
        app = _fresh_app()
        st = app.state.store
        created = st.find_one("users", email="hoanganh.goldenlight@gmail.com")
        assert created and created["role"] == "admin"
        assert created.get("password_hash")

        with TestClient(app) as c:
            # đăng nhập bằng email admin + mật khẩu bootstrap
            resp = c.post("/login", data={"login_id": "hoanganh.goldenlight@gmail.com",
                                          "password": "BanToChuc@2026"}, follow_redirects=False)
            assert resp.status_code == 303
            assert c.get("/admin", follow_redirects=False).status_code == 200
    finally:
        os.environ.pop("ADMIN_EMAILS", None)
        os.environ.pop("ADMIN_PASSWORD", None)
        reset_settings()


def test_admin_can_add_user_and_reset_password(client, store):
    login(client, "admin@dainam.edu.vn")
    # thêm giảng viên mới với mật khẩu
    resp = client.post("/admin/users/add", data={
        "ho_ten": "GV Mới", "email": "gvmoi@dainam.edu.vn", "ma_gv": "GV099",
        "role": "lecturer", "password": "matkhau1",
    }, follow_redirects=False)
    assert resp.status_code == 303
    new_user = store.find_one("users", email="gvmoi@dainam.edu.vn")
    assert new_user and new_user["role"] == "lecturer"

    # người dùng mới đăng nhập được
    client.get("/logout")
    assert client.post("/login", data={"login_id": "gvmoi@dainam.edu.vn", "password": "matkhau1"},
                       follow_redirects=False).status_code == 303

    # admin đặt lại mật khẩu
    login(client, "admin@dainam.edu.vn")
    resp = client.post(f"/admin/users/{new_user['id']}/password",
                       data={"new_password": "matkhaumoi9"}, follow_redirects=False)
    assert resp.status_code == 303
    client.get("/logout")
    assert client.post("/login", data={"login_id": "gvmoi@dainam.edu.vn", "password": "matkhaumoi9"},
                       follow_redirects=False).status_code == 303


def test_admin_can_lock_user(client, store):
    login(client, "admin@dainam.edu.vn")
    target = store.find_one("users", email="gv002@dainam.edu.vn")
    resp = client.post(f"/admin/users/{target['id']}/toggle", follow_redirects=False)
    assert resp.status_code == 303
    assert store.get("users", target["id"])["active"] is False
    # tài khoản bị khóa không đăng nhập được
    client.get("/logout")
    assert client.post("/login", data={"login_id": "gv002@dainam.edu.vn", "password": "test123"},
                       follow_redirects=False).status_code == 401


def test_import_csv_sets_default_password(client, store):
    login(client, "admin@dainam.edu.vn")
    csv_text = "ma_gv,ho_ten,email,khoa,role\nGV100,Người Import,imp@dainam.edu.vn,CNTT,lecturer"
    resp = client.post("/admin/users/import", data={"csv_text": csv_text}, follow_redirects=False)
    assert resp.status_code == 303
    client.get("/logout")
    # mật khẩu mặc định DNU@2026 (DEFAULT_PASSWORD chưa đặt trong test → mặc định)
    assert client.post("/login", data={"login_id": "imp@dainam.edu.vn", "password": "DNU@2026"},
                       follow_redirects=False).status_code == 303


def test_import_csv_don_vi_and_chuc_vu(client, store):
    """Cột mới don_vi/chuc_vu/ma_dinh_danh được nhận; don_vi lưu nội bộ ở khóa 'khoa'."""
    login(client, "admin@dainam.edu.vn")
    csv_text = (
        "ma_dinh_danh,ho_ten,email,don_vi,bo_mon,chuc_vu,role\n"
        "GV200,Đơn Vị Mới,donvi@dainam.edu.vn,Khoa CT-QP-TC,,Trưởng khoa,lecturer"
    )
    resp = client.post("/admin/users/import", data={"csv_text": csv_text}, follow_redirects=False)
    assert resp.status_code == 303
    u = store.find_one("users", email="donvi@dainam.edu.vn")
    assert u is not None
    assert u["ma_gv"] == "GV200"          # alias ma_dinh_danh → ma_gv
    assert u["khoa"] == "Khoa CT-QP-TC"   # alias don_vi → khoa (lưu nội bộ)
    assert u["chuc_vu"] == "Trưởng khoa"


def test_add_user_stores_chuc_vu(client, store):
    login(client, "admin@dainam.edu.vn")
    resp = client.post("/admin/users/add", data={
        "ho_ten": "GV Chức Vụ", "email": "cv@dainam.edu.vn", "ma_gv": "GV300",
        "khoa": "Quản trị kinh doanh", "bo_mon": "Marketing", "chuc_vu": "Phó Trưởng khoa",
        "role": "lecturer", "password": "matkhau1",
    }, follow_redirects=False)
    assert resp.status_code == 303
    u = store.find_one("users", email="cv@dainam.edu.vn")
    assert u and u["chuc_vu"] == "Phó Trưởng khoa" and u["khoa"] == "Quản trị kinh doanh"
