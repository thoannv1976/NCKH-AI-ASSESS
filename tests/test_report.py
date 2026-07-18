"""Test xuất Phiếu đánh giá (docx + pdf) sau khi AI chấm điểm."""
from app.db import new_id
from app.rubric import get_rubric, graded_parts
from tests.conftest import login


def _make_graded(store, uid="u-gv1", ma="GV001", ho_ten="Nguyễn Văn An", loai="bao_cao_ung_dung"):
    """Tạo hồ sơ công trình đã có điểm (mô phỏng AI đã chấm)."""
    rub = get_rubric(store, loai)
    sid = new_id()
    store.put("submissions", sid, {
        "id": sid, "user_id": uid, "status": "graded", "ai_graded": True, "ai_total": 76,
        "anomaly_flags": ["Số liệu kết quả chưa nhất quán (thử nghiệm)"],
        "part_a": {"ten_cong_trinh": "Đề tài NCKH mẫu", "loai": loai, "ho_ten": ho_ten,
                   "ma_gv": ma, "khoa_bo_mon": "Viện KT&KDQT",
                   "thanh_vien": ["Trần Thị B - 2211110003"], "gvhd": "PGS. TS. Vũ Hoàng Nam"},
    })
    for p in graded_parts(rub):
        for c in rub["parts"][p]["criteria"]:
            store.put("scores", f"{sid}_{p}_{c['id']}", {
                "submission_id": sid, "part": p, "criterion_id": c["id"], "max": c["max"],
                "ai_score": round(c["max"] * 0.8, 2), "final_score": round(c["max"] * 0.8, 2),
                "council_score": None, "ai_comment": f"Nhận xét tiêu chí {c['id']}", "council_comment": "",
            })
    return sid


def test_report_docx_and_pdf(client, store):
    sid = _make_graded(store)
    login(client, "admin@dainam.edu.vn")
    rd = client.get(f"/council/submission/{sid}/report.docx")
    assert rd.status_code == 200
    assert "wordprocessingml" in rd.headers["content-type"]
    assert rd.content[:2] == b"PK" and len(rd.content) > 5000   # docx là zip
    rp = client.get(f"/council/submission/{sid}/report.pdf")
    assert rp.status_code == 200
    assert rp.headers["content-type"] == "application/pdf"
    assert rp.content[:4] == b"%PDF" and len(rp.content) > 5000


def test_report_council_can_download(client, store):
    sid = _make_graded(store)
    login(client, "hd@dainam.edu.vn")
    assert client.get(f"/council/submission/{sid}/report.pdf").status_code == 200


def test_report_requires_grading(client, store):
    sid = new_id()
    store.put("submissions", sid, {"id": sid, "user_id": "u-gv1", "status": "submitted"})
    login(client, "admin@dainam.edu.vn")
    assert client.get(f"/council/submission/{sid}/report.docx", follow_redirects=False).status_code == 400


def test_report_lecturer_forbidden(client, store):
    sid = _make_graded(store)
    login(client, "gv001@dainam.edu.vn")
    assert client.get(f"/council/submission/{sid}/report.pdf", follow_redirects=False).status_code == 403


def test_reports_zip_bulk(client, store):
    import io
    import zipfile

    _make_graded(store, "u-gv1", "GV001", "Nguyễn Văn An")
    _make_graded(store, "u-gv2", "GV002", "Trần Thị Bình")
    login(client, "admin@dainam.edu.vn")
    r = client.get("/reports/phieu-danh-gia.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    pdfs = [n for n in zf.namelist() if n.endswith(".pdf")]
    assert len(pdfs) == 2 and all(zf.read(n)[:4] == b"%PDF" for n in pdfs)
    # bản Word
    rd = client.get("/reports/phieu-danh-gia.zip", params={"fmt": "docx"})
    zf2 = zipfile.ZipFile(io.BytesIO(rd.content))
    assert len([n for n in zf2.namelist() if n.endswith(".docx")]) == 2


def test_reports_zip_lecturer_forbidden(client):
    login(client, "gv001@dainam.edu.vn")
    assert client.get("/reports/phieu-danh-gia.zip", follow_redirects=False).status_code == 403
