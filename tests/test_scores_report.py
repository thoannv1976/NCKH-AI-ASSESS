"""Test bảng điểm tất cả công trình: xem được điểm trước khi Hội đồng chốt + tải Excel."""
import io

from app.services.grading.engine import grade_submission
from app.services.grading.graders import MockGrader
from tests.conftest import DOCX_CT, fill_part_a, login, make_docx_bytes


def _submit(client, store, email, ma):
    login(client, email)
    fill_part_a(client, ma_gv=ma, ho_ten="SV " + ma, loai="thuyet_minh")
    client.post("/lecturer/part/TM/upload", data={"kind": "product"},
                files={"files": (f"{ma}_PhanTM.docx", make_docx_bytes("Thuyết minh", ["x"]), DOCX_CT)},
                follow_redirects=False)
    client.post("/lecturer/submit", follow_redirects=False)
    return store.find_one("submissions", user_id=f"u-{'gv1' if ma == 'GV001' else 'gv2'}")


def test_scores_visible_before_council_finalizes(client, store, storage):
    sub = _submit(client, store, "gv001@dainam.edu.vn", "GV001")
    # Chấm thử (chưa chốt) — review vẫn 'pending'
    grade_submission(store, storage, MockGrader(), sub["id"], force=True, keep_status=True)
    assert store.get("reviews", sub["id"])["status"] == "pending"

    login(client, "admin@dainam.edu.vn")
    page = client.get("/reports/scores")
    assert page.status_code == 200
    assert "GV001" in page.text
    assert "Tạm tính" in page.text  # điểm hiện ra dù chưa chốt


def test_scores_xlsx_download(client, store, storage):
    sub = _submit(client, store, "gv001@dainam.edu.vn", "GV001")
    grade_submission(store, storage, MockGrader(), sub["id"], force=True, keep_status=True)
    login(client, "admin@dainam.edu.vn")
    r = client.get("/reports/scores.xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb["Bảng điểm"]
    text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    assert "GV001" in text
    assert "Tổng (hiện tại)" in text
    assert "Tạm tính (chưa chốt)" in text


def test_scores_includes_ungraded_submitted(client, store):
    """Hồ sơ đã nộp nhưng chưa chấm vẫn hiện trong bảng (đánh dấu 'Chưa chấm')."""
    _submit(client, store, "gv001@dainam.edu.vn", "GV001")
    login(client, "admin@dainam.edu.vn")
    page = client.get("/reports/scores").text
    assert "GV001" in page
    assert "Chưa chấm" in page


def test_council_can_view_scores_lecturer_cannot(client, store, storage):
    sub = _submit(client, store, "gv001@dainam.edu.vn", "GV001")
    grade_submission(store, storage, MockGrader(), sub["id"], force=True, keep_status=True)
    login(client, "hd@dainam.edu.vn")
    assert client.get("/reports/scores", follow_redirects=False).status_code == 200
    assert client.get("/reports/scores.xlsx", follow_redirects=False).status_code == 200
    login(client, "gv002@dainam.edu.vn")
    assert client.get("/reports/scores", follow_redirects=False).status_code == 403
    assert client.get("/reports/scores.xlsx", follow_redirects=False).status_code == 403
