"""Test mở khóa hồ sơ khi gia hạn nộp bài (hồ sơ đã khóa không nộp lại được nếu không mở khóa)."""
from app.db import new_id
from app.services.ops import get_timeline
from tests.conftest import login

PART_A = {"ho_ten": "An", "ma_gv": "GV001", "khoa_bo_mon": "CNTT",
          "hoc_phan": "AI", "cong_cu_ai": "Claude", "muc_thanh_thao": 4}


def _locked_sub(store):
    sid = new_id()
    store.put("submissions", sid, {"id": sid, "user_id": "u-gv1", "status": "locked",
                                   "part_a": {**PART_A, "cong_cu_ai": ["Claude"]}})
    tl = get_timeline(store)
    tl["locked_done"] = True
    store.put("config", "timeline", tl)
    return sid


def test_locked_blocks_edit_then_unlock_reopens(client, store):
    sid = _locked_sub(store)
    # Giảng viên KHÔNG sửa/nộp được khi hồ sơ đang khóa
    login(client, "gv001@dainam.edu.vn")
    assert client.post("/lecturer/part-a", data=PART_A, follow_redirects=False).status_code == 400

    # Admin mở khóa
    login(client, "admin@dainam.edu.vn")
    assert client.post("/admin/unlock", follow_redirects=False).status_code == 303
    assert store.get("submissions", sid)["status"] == "submitted"
    assert get_timeline(store)["locked_done"] is False

    # Giảng viên sửa/nộp lại được (hạn nộp trong test ở tương lai)
    login(client, "gv001@dainam.edu.vn")
    assert client.post("/lecturer/part-a", data=PART_A, follow_redirects=False).status_code == 303


def test_extend_deadline_resets_lock_flag(client, store):
    tl = get_timeline(store)
    tl["locked_done"] = True
    store.put("config", "timeline", tl)
    login(client, "admin@dainam.edu.vn")
    r = client.post("/admin/config/timeline",
                    data={"deadline": "2099-01-01T17:00:00+07:00", "open_at": "2020-01-01T00:00:00+07:00"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert get_timeline(store)["locked_done"] is False


def test_unlock_lecturer_forbidden(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.post("/admin/unlock", follow_redirects=False).status_code == 403
