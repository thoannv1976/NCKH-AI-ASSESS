"""Test chấm tự động từng giảng viên theo yêu cầu (Admin/Hội đồng) — chấm thử trước hạn."""
import time

from app.services.grading.engine import grade_submission, invalidate_grading
from app.services.grading.graders import MockGrader
from tests.conftest import DOCX_CT, fill_part_a, login, make_docx_bytes


def _make_submitted(client, store, email="gv001@dainam.edu.vn", ma="GV001"):
    login(client, email)
    fill_part_a(client, ma_gv=ma, ho_ten="SV Test", loai="bao_cao_ung_dung")
    data = make_docx_bytes("Báo cáo I", ["nội dung phần I"])
    client.post("/lecturer/part/I/upload", data={"kind": "product"},
                files={"files": ("GV001_PhanI_SP.docx", data, DOCX_CT)}, follow_redirects=False)
    client.post("/lecturer/part/I/upload", data={"kind": "evidence"},
                files={"files": ("GV001_PhanI_MC.docx", data, DOCX_CT)}, follow_redirects=False)
    client.post("/lecturer/submit", follow_redirects=False)
    return store.find_one("submissions", user_id="u-gv1")


def _wait_done(store, sid, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        sub = store.get("submissions", sid)
        if not (sub.get("grade_job") or {}).get("running"):
            return sub
        time.sleep(0.1)
    raise AssertionError("Phiên chấm không kết thúc trong thời gian chờ")


def test_grade_submission_keep_status_does_not_lock_lecturer(client, store, storage):
    """Chấm thử (keep_status) giữ nguyên trạng thái 'submitted' → giảng viên vẫn sửa được."""
    sub = _make_submitted(client, store)
    assert sub["status"] == "submitted"
    grade_submission(store, storage, MockGrader(), sub["id"], force=True, keep_status=True)
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "submitted"          # KHÔNG bị chuyển 'graded'
    assert sub["ai_graded"] is True
    assert sub.get("ai_total") is not None
    assert store.find("scores", submission_id=sub["id"])   # có điểm
    assert store.get("reviews", sub["id"])["status"] == "pending"

    # Giảng viên vẫn upload/sửa được sau khi chấm thử
    login(client, "gv001@dainam.edu.vn")
    data = make_docx_bytes("Thêm", ["x"])
    r = client.post("/lecturer/part/II/upload", data={"kind": "product"},
                    files={"files": ("GV001_PhanII_SP.docx", data, DOCX_CT)}, follow_redirects=False)
    assert r.status_code == 303


def test_council_grade_one_endpoint(client, store):
    sub = _make_submitted(client, store)
    login(client, "hd@dainam.edu.vn")
    r = client.post(f"/council/submission/{sub['id']}/grade", follow_redirects=False)
    assert r.status_code == 303
    sub = _wait_done(store, sub["id"])
    assert sub.get("ai_graded") is True
    assert sub["status"] == "submitted"   # giữ nguyên
    assert store.find("scores", submission_id=sub["id"])
    # ghi vết
    assert any(log["action"] == "grade_one" for log in store.all("audit_logs"))


def test_admin_can_grade_one(client, store):
    sub = _make_submitted(client, store)
    login(client, "admin@dainam.edu.vn")
    r = client.post(f"/council/submission/{sub['id']}/grade", follow_redirects=False)
    assert r.status_code == 303
    sub = _wait_done(store, sub["id"])
    assert sub.get("ai_graded") is True


def test_lecturer_cannot_grade(client, store):
    sub = _make_submitted(client, store)
    login(client, "gv002@dainam.edu.vn")  # giảng viên khác
    r = client.post(f"/council/submission/{sub['id']}/grade", follow_redirects=False)
    assert r.status_code == 403


def test_lecturer_edit_invalidates_test_grade(client, store, storage):
    sub = _make_submitted(client, store)
    grade_submission(store, storage, MockGrader(), sub["id"], force=True, keep_status=True)
    assert store.get("submissions", sub["id"])["ai_graded"] is True

    # Giảng viên sửa hồ sơ → kết quả chấm thử bị xóa để chấm lại trên nội dung mới
    login(client, "gv001@dainam.edu.vn")
    data = make_docx_bytes("Sửa", ["y"])
    client.post("/lecturer/part/II/upload", data={"kind": "product"},
                files={"files": ("GV001_PhanII_SP.docx", data, DOCX_CT)}, follow_redirects=False)
    sub = store.get("submissions", sub["id"])
    assert sub.get("ai_graded") is False
    assert not sub.get("grading_progress")


def test_invalidate_grading_helper(store):
    store.put("submissions", "s1", {"id": "s1", "ai_graded": True, "ai_total": 80,
                                    "grading_progress": {"I": True}, "part_results": {"I": {}}})
    invalidate_grading(store, "s1")
    s = store.get("submissions", "s1")
    assert s["ai_graded"] is False and not s["grading_progress"] and s["ai_total"] is None


def test_grade_locked_becomes_graded_then_approve(client, store, storage):
    """Sau hạn: hồ sơ đã khóa → chấm chính thức → status 'graded' → Hội đồng phê duyệt được."""
    sub = _make_submitted(client, store)
    # Admin khóa hồ sơ (mô phỏng sau hạn)
    login(client, "admin@dainam.edu.vn")
    client.post("/admin/lock", follow_redirects=False)
    assert store.get("submissions", sub["id"])["status"] == "locked"

    # Hội đồng chấm hồ sơ đã khóa → chuyển 'graded'
    login(client, "hd@dainam.edu.vn")
    r = client.post(f"/council/submission/{sub['id']}/grade", follow_redirects=False)
    assert r.status_code == 303
    sub = _wait_done(store, sub["id"])
    assert sub["status"] == "graded"          # chấm chính thức, KHÔNG giữ 'locked'
    assert sub["ai_graded"] is True

    # Phê duyệt được
    r = client.post(f"/council/submission/{sub['id']}/approve", follow_redirects=False)
    assert r.status_code == 303
    assert store.get("submissions", sub["id"])["status"] == "approved"

    # Không cho chấm lại hồ sơ đã phê duyệt
    r = client.post(f"/council/submission/{sub['id']}/grade", follow_redirects=False)
    assert r.status_code == 400


def test_no_batch_grade_endpoint(client):
    """Đã bỏ chức năng chấm toàn bộ tự động — endpoint /admin/grade không còn."""
    login(client, "admin@dainam.edu.vn")
    assert client.post("/admin/grade", follow_redirects=False).status_code == 404
