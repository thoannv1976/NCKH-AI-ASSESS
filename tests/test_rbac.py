"""Test phân quyền 3 vai trò."""
from tests.conftest import login


def test_anonymous_redirected_to_login(client):
    for path in ["/lecturer", "/council", "/admin", "/reports"]:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


def test_lecturer_cannot_access_staff_pages(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.get("/admin", follow_redirects=False).status_code == 403
    assert client.get("/council", follow_redirects=False).status_code == 403
    assert client.get("/reports", follow_redirects=False).status_code == 403
    assert client.get("/lecturer", follow_redirects=False).status_code == 200


def test_council_cannot_access_admin(client):
    login(client, "hd@dainam.edu.vn")
    assert client.get("/admin", follow_redirects=False).status_code == 403
    assert client.get("/council", follow_redirects=False).status_code == 200
    assert client.get("/reports", follow_redirects=False).status_code == 200


def test_admin_access(client):
    login(client, "admin@dainam.edu.vn")
    assert client.get("/admin", follow_redirects=False).status_code == 200
    assert client.get("/council", follow_redirects=False).status_code == 200


def test_lecturer_cannot_download_others_file(client, store, storage):
    import io

    login(client, "gv001@dainam.edu.vn")
    client.get("/lecturer")  # tạo submission cho gv001
    # tạo hồ sơ + tệp của GV002
    sub2 = {"id": "sub-gv2", "user_id": "u-gv2", "status": "draft", "part_a": {}}
    store.put("submissions", sub2["id"], sub2)
    storage.save("sub-gv2/B/product/x.docx", io.BytesIO(b"x"))
    store.put("submission_items", "item-gv2", {
        "id": "item-gv2", "submission_id": "sub-gv2", "part": "B", "kind": "product",
        "type": "file", "storage_path": "sub-gv2/B/product/x.docx", "original_name": "x.docx",
    })
    assert client.get("/file/item-gv2", follow_redirects=False).status_code == 403
    # hội đồng thì xem được
    login(client, "hd@dainam.edu.vn")
    assert client.get("/file/item-gv2", follow_redirects=False).status_code == 200


def test_cron_requires_token(client):
    assert client.post("/tasks/cron").status_code == 403
    assert client.post("/tasks/cron", headers={"X-Cron-Token": "test-cron"}).status_code == 200


def test_wrong_password_rejected(client):
    resp = client.post("/login", data={"login_id": "gv001@dainam.edu.vn", "password": "sai-mat-khau"},
                       follow_redirects=False)
    assert resp.status_code == 401


def test_login_by_ma_gv(client):
    # đăng nhập bằng mã giảng viên thay vì email
    resp = client.post("/login", data={"login_id": "GV001", "password": "test123"}, follow_redirects=False)
    assert resp.status_code == 303
    assert client.get("/lecturer", follow_redirects=False).status_code == 200


def test_change_password(client):
    login(client, "gv001@dainam.edu.vn")
    resp = client.post("/change-password",
                       data={"current": "test123", "new_password": "moimk456", "confirm": "moimk456"},
                       follow_redirects=False)
    assert resp.status_code == 303
    client.get("/logout")
    # mật khẩu cũ không còn dùng được, mật khẩu mới đăng nhập được
    assert client.post("/login", data={"login_id": "gv001@dainam.edu.vn", "password": "test123"},
                       follow_redirects=False).status_code == 401
    assert client.post("/login", data={"login_id": "gv001@dainam.edu.vn", "password": "moimk456"},
                       follow_redirects=False).status_code == 303
