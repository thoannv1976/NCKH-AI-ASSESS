"""Test tổng hợp tình trạng nộp bài: đã nộp / nháp / chưa tạo hồ sơ."""
from app.db import new_id
from app.services.ops import submission_tracking
from tests.conftest import graded_parts_for, login


def test_tracking_three_states(client, store):
    # thêm 1 giảng viên chưa tạo hồ sơ
    store.put("users", "u-gv3", {"id": "u-gv3", "ma_gv": "GV003", "ho_ten": "GV Ba",
                                 "email": "gv3@x.edu.vn", "khoa": "CNTT", "role": "lecturer", "active": True})
    s1 = new_id()
    store.put("submissions", s1, {"id": s1, "user_id": "u-gv1", "status": "submitted",
                                  "submitted_at": "2026-06-30T10:00:00"})
    s2 = new_id()
    store.put("submissions", s2, {"id": s2, "user_id": "u-gv2", "status": "draft", "part_a": {}})

    rows, counts = submission_tracking(store)
    assert counts["lecturers"] == 3
    assert counts["submitted"] == 1 and counts["draft"] == 1 and counts["none"] == 1

    login(client, "admin@dainam.edu.vn")
    assert client.get("/admin/tracking").status_code == 200
    assert client.get("/admin/tracking", params={"state": "none"}).status_code == 200
    rx = client.get("/admin/tracking.xlsx")
    assert rx.status_code == 200 and "spreadsheetml" in rx.headers["content-type"] and len(rx.content) > 2000


def test_tracking_ready_but_unsubmitted(client, store):
    """Draft đủ bài nhưng chưa bấm Nộp → ready=True."""
    sid = new_id()
    store.put("submissions", sid, {"id": sid, "user_id": "u-gv1", "status": "draft",
        "part_a": {"ten_cong_trinh": "Đề tài mẫu", "loai": "thuyet_minh", "ho_ten": "An",
                   "ma_gv": "GV001", "khoa_bo_mon": "Viện KT&KDQT"}})
    for p in graded_parts_for(store, "thuyet_minh"):
        store.add("submission_items", {"submission_id": sid, "part": p, "kind": "product",
                                       "type": "file", "original_name": "x.docx"})
    rows, counts = submission_tracking(store)
    assert counts["ready_unsubmitted"] >= 1
    row = next(r for r in rows if r["user"]["id"] == "u-gv1")
    assert row["state"] == "draft" and row["ready"] and not row["missing"]


def test_tracking_lecturer_forbidden(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.get("/admin/tracking", follow_redirects=False).status_code == 403
