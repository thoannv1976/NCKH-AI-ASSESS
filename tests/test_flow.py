"""Test e2e trọn luồng: kê khai → nộp → khóa → chấm (mock) → thẩm định → công bố → phản hồi."""
from app.services.grading.engine import run_grading
from app.services.grading.graders import MockGrader
from tests.conftest import DOCX_CT, fill_part_a, login, make_docx_bytes, upload_all_parts


def _fill_submission(client, store):
    """sv001 (u-gv1) kê khai Phần A + nộp tài liệu cho mọi phần được chấm (loại thuyết minh)."""
    login(client, "gv001@dainam.edu.vn")
    fill_part_a(client, ma_gv="GV001", ho_ten="Nguyễn Văn An", loai="thuyet_minh")
    upload_all_parts(client, store, ma_gv="GV001", loai="thuyet_minh")
    resp = client.post("/lecturer/submit", follow_redirects=False)
    assert resp.status_code == 303
    sub = store.find_one("submissions", user_id="u-gv1")
    assert sub["status"] == "submitted"
    assert sub["valid"] is True
    return sub


def test_full_flow(client, store, storage):
    sub = _fill_submission(client, store)

    # Email xác nhận đã ghi log
    assert any(e["kind"] == "confirm" for e in store.all("email_logs"))

    # Khóa hồ sơ (Bước 1)
    login(client, "admin@dainam.edu.vn")
    resp = client.post("/admin/lock", follow_redirects=False)
    assert resp.status_code == 303
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "locked" and sub["valid"] is True

    # Chấm tự động (mock grader, chạy đồng bộ trong test)
    stats = run_grading(store, storage, MockGrader())
    assert stats["graded"] == 1 and not stats["errors"]
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "graded"
    assert 0 < sub["ai_total"] <= 100

    # Điểm từng tiêu chí + các lượt chấm được lưu (thuyết minh: 1 phần TM, 10 tiêu chí)
    scores = store.find("scores", submission_id=sub["id"])
    assert len(scores) == 10
    runs = store.find("grading_runs", submission_id=sub["id"])
    assert len(runs) >= 2  # ≥ 2 lượt × 1 phần
    review = store.get("reviews", sub["id"])
    assert review["status"] == "pending"

    # Hội đồng điều chỉnh một tiêu chí + phê duyệt (Bước 4)
    login(client, "hd@dainam.edu.vn")
    target = next(s for s in scores if s["part"] == "TM" and s["criterion_id"] == "TM1")
    resp = client.post(f"/council/submission/{sub['id']}/score", data={
        "score_id": target["id"], "council_score": 8.0, "reason": "Tổng quan tốt hơn mức AI đánh giá",
    }, follow_redirects=False)
    assert resp.status_code == 303
    adjusted = store.get("scores", target["id"])
    assert adjusted["final_score"] == 8.0
    assert any(log["action"] == "adjust_score" for log in store.all("audit_logs"))

    resp = client.post(f"/council/submission/{sub['id']}/approve", follow_redirects=False)
    assert resp.status_code == 303
    review = store.get("reviews", sub["id"])
    assert review["status"] == "approved"
    assert review["classification"] in ("de_nghi_thuc_hien", "khong_thuc_hien")

    # Công bố (Bước 5) + email kết quả
    login(client, "admin@dainam.edu.vn")
    resp = client.post("/admin/publish", follow_redirects=False)
    assert resp.status_code == 303
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "published"
    assert any(e["kind"] == "result" for e in store.all("email_logs"))

    # Chủ nhiệm xem kết quả + gửi phản hồi trong hạn
    login(client, "gv001@dainam.edu.vn")
    resp = client.get("/lecturer/result")
    assert resp.status_code == 200
    assert "Tổng điểm" in resp.text
    resp = client.post("/lecturer/appeal", data={"content": "Đề nghị xem lại tiêu chí TM2"},
                       follow_redirects=False)
    assert resp.status_code == 303
    assert store.find_one("appeals", submission_id=sub["id"])["status"] == "open"

    # Hội đồng trả lời phản hồi
    login(client, "hd@dainam.edu.vn")
    appeal = store.find_one("appeals", submission_id=sub["id"])
    resp = client.post(f"/council/appeal/{appeal['id']}/resolve",
                       data={"resolution": "Đã xem xét, giữ nguyên kết quả"}, follow_redirects=False)
    assert resp.status_code == 303
    assert store.get("appeals", appeal["id"])["status"] == "resolved"


def test_resubmit_before_deadline(client, store):
    _fill_submission(client, store)
    # Nộp lại lần 2 vẫn được trước hạn
    resp = client.post("/lecturer/submit", follow_redirects=False)
    assert resp.status_code == 303


def test_locked_after_deadline(client, store):
    sub = _fill_submission(client, store)
    # Đặt hạn về quá khứ
    tl = store.get("config", "timeline")
    tl["deadline"] = "2026-03-01T17:00:00+07:00"
    store.put("config", "timeline", tl)

    login(client, "gv001@dainam.edu.vn")
    data = make_docx_bytes("Muộn", ["nộp muộn"])
    resp = client.post("/lecturer/part/TM/upload", data={"kind": "product"},
                       files={"files": ("GV001_PhanTM_Muon.docx", data, DOCX_CT)},
                       follow_redirects=False)
    assert resp.status_code == 400  # hệ thống không tiếp nhận sau hạn
    resp = client.post("/lecturer/submit", follow_redirects=False)
    assert resp.status_code == 400

    # Cron khóa hồ sơ sau hạn
    resp = client.post("/tasks/cron", headers={"X-Cron-Token": "test-cron"})
    assert resp.status_code == 200
    assert store.get("submissions", sub["id"])["status"] == "locked"


def test_upload_multiple_files_at_once(client, store):
    """Tải nhiều tệp trong một lần; tệp sai định dạng bị bỏ qua, tệp hợp lệ vẫn lưu."""
    login(client, "gv001@dainam.edu.vn")
    fill_part_a(client, ma_gv="GV001", loai="bao_cao_co_ban")  # loại có phần "I"
    a = make_docx_bytes("SP 1", ["nội dung 1"])
    b = make_docx_bytes("SP 2", ["nội dung 2"])
    bad = b"khong phai docx"
    resp = client.post(
        "/lecturer/part/I/upload", data={"kind": "product"},
        files=[
            ("files", ("GV001_PhanI_File1.docx", a, DOCX_CT)),
            ("files", ("GV001_PhanI_File2.docx", b, DOCX_CT)),
            ("files", ("GV001_PhanI_Anh.png", bad, "image/png")),  # sai định dạng → bỏ qua
        ],
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "uploaded=2" in resp.headers["location"]
    assert "upload_errors=" in resp.headers["location"]
    sub = store.find_one("submissions", user_id="u-gv1")
    items = [i for i in store.find("submission_items", submission_id=sub["id"])
             if i["part"] == "I" and i["kind"] == "product"]
    assert len(items) == 2
    names = sorted(i["original_name"] for i in items)
    assert names == ["GV001_PhanI_File1.docx", "GV001_PhanI_File2.docx"]


def test_bao_cao_ung_dung_grades_two_parts(client, store, storage):
    """Hồ sơ loại 'báo cáo nghiên cứu ứng dụng' có 2 phần I, II — chấm đủ 8 tiêu chí."""
    login(client, "gv002@dainam.edu.vn")
    fill_part_a(client, ma_gv="GV002", ho_ten="Trần Thị Bình", loai="bao_cao_ung_dung")
    upload_all_parts(client, store, ma_gv="GV002", loai="bao_cao_ung_dung")
    client.post("/lecturer/submit", follow_redirects=False)

    sub = store.find_one("submissions", user_id="u-gv2")
    login(client, "admin@dainam.edu.vn")
    client.post("/admin/lock", follow_redirects=False)
    run_grading(store, storage, MockGrader(), only_ids=[sub["id"]])

    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "graded"
    scores = store.find("scores", submission_id=sub["id"])
    parts = {s["part"] for s in scores}
    assert parts == {"I", "II"}
    assert len(scores) == 8  # I: 6 tiêu chí + II: 2 tiêu chí
    assert 0 < sub["ai_total"] <= 100
