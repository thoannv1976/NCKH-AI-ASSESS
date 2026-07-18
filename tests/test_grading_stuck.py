"""Test khôi phục hồ sơ bị kẹt 'đang chấm' (Cloud Run cắt CPU khiến luồng nền treo)."""
from datetime import timedelta

from app.config import now_vn
from app.db import new_id
from app.services.ops import grade_job_stale, reset_stuck_grading
from tests.conftest import login


def _stuck_sub(store, uid="u-gv1", minutes=30, prev="locked"):
    sid = new_id()
    started = (now_vn() - timedelta(minutes=minutes)).isoformat()
    store.put("submissions", sid, {"id": sid, "user_id": uid, "status": "grading",
                                   "grade_job": {"running": True, "started_at": started, "prev_status": prev}})
    return sid


def test_grade_job_stale():
    assert grade_job_stale({"running": True, "started_at": (now_vn() - timedelta(minutes=30)).isoformat()})
    assert grade_job_stale({"running": True})                      # thiếu started_at → coi như treo
    assert not grade_job_stale({"running": True, "started_at": now_vn().isoformat()})
    assert not grade_job_stale({"running": False})
    assert not grade_job_stale(None)


def test_reset_stuck_grading_resets_stale_only(client, store):
    old = _stuck_sub(store, "u-gv1", minutes=30, prev="locked")
    fresh = _stuck_sub(store, "u-gv2", minutes=1)     # mới bắt đầu → KHÔNG reset
    assert reset_stuck_grading(store) == 1
    so = store.get("submissions", old)
    assert so["status"] == "locked" and so["grade_job"]["running"] is False
    assert store.get("submissions", fresh)["status"] == "grading"


def test_reset_grading_route(client, store):
    sid = _stuck_sub(store)
    login(client, "admin@dainam.edu.vn")
    assert client.post("/admin/reset-grading", follow_redirects=False).status_code == 303
    assert store.get("submissions", sid)["grade_job"]["running"] is False


def test_grade_blocked_only_when_actively_running(client, store):
    # Job mới chạy (chưa treo) → chặn chấm lại
    sid = _stuck_sub(store, minutes=1)
    login(client, "admin@dainam.edu.vn")
    assert client.post(f"/council/submission/{sid}/grade", follow_redirects=False).status_code == 400


def test_reset_grading_forbidden_for_lecturer(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.post("/admin/reset-grading", follow_redirects=False).status_code == 403
