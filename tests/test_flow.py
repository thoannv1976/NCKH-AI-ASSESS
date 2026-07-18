"""Test e2e trọn luồng: kê khai → nộp → khóa → chấm (mock) → thẩm định → công bố → phản hồi."""
from app.services.grading.engine import run_grading
from app.services.grading.graders import MockGrader
from tests.conftest import login, make_docx_bytes

DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _fill_submission(client, store):
    """GV001 kê khai Phần A + nộp sản phẩm/minh chứng cho mọi phần B–G."""
    login(client, "gv001@dainam.edu.vn")
    resp = client.post("/lecturer/part-a", data={
        "ho_ten": "Nguyễn Văn An", "ma_gv": "GV001", "khoa_bo_mon": "CNTT - KTPM",
        "hoc_phan": "Nhập môn AI (HK1 2026-2027)", "cong_cu_ai": "Claude, ChatGPT",
        "muc_thanh_thao": 4,
    }, follow_redirects=False)
    assert resp.status_code == 303

    for part in ["B", "C", "D", "E", "F", "G"]:
        data = make_docx_bytes(f"Sản phẩm phần {part}", ["Nội dung sản phẩm chi tiết.", "Có nhiệm vụ khuyến khích."])
        resp = client.post(f"/lecturer/part/{part}/upload", data={"kind": "product"},
                           files={"files": (f"GV001_Phan{part}_SanPham.docx", data, DOCX_CT)},
                           follow_redirects=False)
        assert resp.status_code == 303, resp.text
        if part != "G":
            ev = make_docx_bytes(f"Nhật ký prompt phần {part}", ["Prompt 1...", "Prompt 2..."])
            resp = client.post(f"/lecturer/part/{part}/upload", data={"kind": "evidence"},
                               files={"files": (f"GV001_Phan{part}_NhatKyPrompt.docx", ev, DOCX_CT)},
                               follow_redirects=False)
            assert resp.status_code == 303

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

    # Chấm tự động (Bước 2-3, mock grader, chạy đồng bộ trong test)
    stats = run_grading(store, storage, MockGrader())
    assert stats["graded"] == 1 and not stats["errors"]
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "graded"
    assert 0 < sub["ai_total"] <= 100

    # Điểm từng tiêu chí + các lượt chấm được lưu
    scores = store.find("scores", submission_id=sub["id"])
    assert len(scores) == 4 + 4 + 3 + 4 + 2 + 2  # B,C,D,E(4 gồm bonus),F,G
    runs = store.find("grading_runs", submission_id=sub["id"])
    assert len(runs) >= 12  # ≥ 2 lượt × 6 phần
    review = store.get("reviews", sub["id"])
    assert review["status"] == "pending"

    # Hội đồng điều chỉnh một tiêu chí + phê duyệt (Bước 4)
    login(client, "hd@dainam.edu.vn")
    target = next(s for s in scores if s["part"] == "B" and s["criterion_id"] == "B1")
    resp = client.post(f"/council/submission/{sub['id']}/score", data={
        "score_id": target["id"], "council_score": 7.5, "reason": "Đề cương tốt hơn mức AI đánh giá",
    }, follow_redirects=False)
    assert resp.status_code == 303
    adjusted = store.get("scores", target["id"])
    assert adjusted["final_score"] == 7.5
    assert any(log["action"] == "adjust_score" for log in store.all("audit_logs"))

    resp = client.post(f"/council/submission/{sub['id']}/approve", follow_redirects=False)
    assert resp.status_code == 303
    review = store.get("reviews", sub["id"])
    assert review["status"] == "approved"
    assert review["classification"] in ("dan_dat", "thanh_thao", "co_ban", "khoi_dau")

    # Công bố (Bước 5) + email kết quả
    login(client, "admin@dainam.edu.vn")
    resp = client.post("/admin/publish", follow_redirects=False)
    assert resp.status_code == 303
    sub = store.get("submissions", sub["id"])
    assert sub["status"] == "published"
    assert any(e["kind"] == "result" for e in store.all("email_logs"))

    # Giảng viên xem kết quả + gửi phản hồi trong hạn
    login(client, "gv001@dainam.edu.vn")
    resp = client.get("/lecturer/result")
    assert resp.status_code == 200
    assert "Tổng điểm" in resp.text
    resp = client.post("/lecturer/appeal", data={"content": "Đề nghị xem lại tiêu chí C2"},
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
    tl["deadline"] = "2026-06-01T17:00:00+07:00"
    store.put("config", "timeline", tl)

    login(client, "gv001@dainam.edu.vn")
    data = make_docx_bytes("Muộn", ["nộp muộn"])
    resp = client.post("/lecturer/part/B/upload", data={"kind": "product"},
                       files={"files": ("GV001_PhanB_Muon.docx", data, DOCX_CT)},
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
    client.get("/lecturer")  # tạo submission
    a = make_docx_bytes("SP 1", ["nội dung 1"])
    b = make_docx_bytes("SP 2", ["nội dung 2"])
    bad = b"khong phai docx"
    resp = client.post(
        "/lecturer/part/C/upload", data={"kind": "product"},
        files=[
            ("files", ("GV001_PhanC_File1.docx", a, DOCX_CT)),
            ("files", ("GV001_PhanC_File2.docx", b, DOCX_CT)),
            ("files", ("GV001_PhanC_Anh.png", bad, "image/png")),  # sai định dạng → bỏ qua
        ],
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "uploaded=2" in resp.headers["location"]
    assert "upload_errors=" in resp.headers["location"]
    sub = store.find_one("submissions", user_id="u-gv1")
    items = [i for i in store.find("submission_items", submission_id=sub["id"])
             if i["part"] == "C" and i["kind"] == "product"]
    assert len(items) == 2
    names = sorted(i["original_name"] for i in items)
    assert names == ["GV001_PhanC_File1.docx", "GV001_PhanC_File2.docx"]


def test_missing_evidence_penalty_in_flow(client, store, storage):
    """Hồ sơ chỉ nộp sản phẩm Phần B không minh chứng → điểm B bị trừ 50%, B4=0, có cờ bất thường."""
    login(client, "gv002@dainam.edu.vn")
    client.post("/lecturer/part-a", data={
        "ho_ten": "Trần Thị Bình", "ma_gv": "GV002", "khoa_bo_mon": "CNTT",
        "hoc_phan": "CSDL", "cong_cu_ai": "Claude", "muc_thanh_thao": 3,
    }, follow_redirects=False)
    data = make_docx_bytes("Đề cương", ["Nội dung đề cương."])
    client.post("/lecturer/part/B/upload", data={"kind": "product"},
                files={"files": ("GV002_PhanB_DeCuong.docx", data, DOCX_CT)}, follow_redirects=False)
    client.post("/lecturer/submit", follow_redirects=False)

    sub = store.find_one("submissions", user_id="u-gv2")
    login(client, "admin@dainam.edu.vn")
    client.post("/admin/lock", follow_redirects=False)
    run_grading(store, storage, MockGrader(), only_ids=[sub["id"]])

    sub = store.get("submissions", sub["id"])
    assert any("không nộp minh chứng" in f for f in sub["anomaly_flags"])
    b4 = store.get("scores", f"{sub['id']}_B_B4")
    assert b4["final_score"] == 0.0
    b1 = store.get("scores", f"{sub['id']}_B_B1")
    assert b1["evidence_penalty"] is True
    review = store.get("reviews", sub["id"])
    assert review["mandatory"] is True  # bất thường minh chứng → thẩm định bắt buộc
