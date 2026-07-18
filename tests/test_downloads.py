"""Test tải sản phẩm dạng ZIP: một công trình và toàn bộ công trình."""
import io
import zipfile

from tests.conftest import DOCX_CT, fill_part_a, login, make_docx_bytes


def _submit_with_files(client, store, email, ma):
    login(client, email)
    fill_part_a(client, ma_gv=ma, ho_ten="SV " + ma, loai="bao_cao_co_ban")
    client.post("/lecturer/part/I/upload", data={"kind": "product"},
                files={"files": (f"{ma}_PhanI_BaoCao.docx", make_docx_bytes("Báo cáo", ["x"]), DOCX_CT)},
                follow_redirects=False)
    client.post("/lecturer/part/I/upload", data={"kind": "evidence"},
                files={"files": (f"{ma}_PhanI_TraSoat.docx", make_docx_bytes("Tra soát", ["y"]), DOCX_CT)},
                follow_redirects=False)
    client.post("/lecturer/part/II/link", data={"kind": "product", "url": "https://example.com/baibao",
                                                "label": "Bài kỷ yếu"}, follow_redirects=False)
    client.post("/lecturer/submit", follow_redirects=False)


def test_admin_download_single_submission(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    sub = store.find_one("submissions", user_id="u-gv1")
    login(client, "admin@dainam.edu.vn")
    r = client.get(f"/council/submission/{sub['id']}/download.zip")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert any("PhanI_SanPham/GV001_PhanI_BaoCao.docx" in n for n in names)
    assert any("PhanI_MinhChung/GV001_PhanI_TraSoat.docx" in n for n in names)
    assert any("PhanA_ThongTin.txt" in n for n in names)
    assert any("LIEN_KET.txt" in n for n in names)  # liên kết Phần II
    # nội dung tệp đọc được
    docx_name = next(n for n in names if n.endswith("GV001_PhanI_BaoCao.docx"))
    assert len(zf.read(docx_name)) > 0


def test_council_can_download_single(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    sub = store.find_one("submissions", user_id="u-gv1")
    login(client, "hd@dainam.edu.vn")
    assert client.get(f"/council/submission/{sub['id']}/download.zip").status_code == 200


def test_admin_download_all(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    _submit_with_files(client, store, "gv002@dainam.edu.vn", "GV002")
    login(client, "admin@dainam.edu.vn")
    r = client.get("/admin/download/all.zip")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "DANH_SACH.csv" in names
    assert any("GV001_" in n for n in names) and any("GV002_" in n for n in names)
    # CSV có BOM + 2 giảng viên
    csv_text = zf.read("DANH_SACH.csv").decode("utf-8-sig")
    assert "GV001" in csv_text and "GV002" in csv_text


def test_admin_download_all_filter_khoa(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    login(client, "admin@dainam.edu.vn")
    r = client.get("/admin/download/all.zip", params={"khoa": "KhongCoKhoaNay"})
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    # chỉ có manifest, không có hồ sơ nào
    assert zf.namelist() == ["DANH_SACH.csv"]


def test_admin_download_selected(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    _submit_with_files(client, store, "gv002@dainam.edu.vn", "GV002")
    sub1 = store.find_one("submissions", user_id="u-gv1")
    login(client, "admin@dainam.edu.vn")
    r = client.post("/admin/download/selected.zip", data={"sid": [sub1["id"]]})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert any("GV001_" in n for n in names)
    assert not any("GV002_" in n for n in names)   # chỉ đóng gói hồ sơ được chọn
    assert "DANH_SACH.csv" in names
    # nội dung tệp đọc được (không rỗng)
    docx_name = next(n for n in names if n.endswith(".docx"))
    assert len(zf.read(docx_name)) > 0


def test_download_selected_empty_rejected(client, store):
    login(client, "admin@dainam.edu.vn")
    assert client.post("/admin/download/selected.zip", data={}, follow_redirects=False).status_code == 400


def test_downloads_page_sorting(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    login(client, "admin@dainam.edu.vn")
    for s in ("ma_gv", "ho_ten", "don_vi", "upload", "files"):
        assert client.get("/admin/downloads", params={"sort": s}).status_code == 200


def test_downloads_page_and_permissions(client, store):
    _submit_with_files(client, store, "gv001@dainam.edu.vn", "GV001")
    login(client, "admin@dainam.edu.vn")
    assert client.get("/admin/downloads").status_code == 200
    # giảng viên không được tải toàn bộ hay trang quản lý
    login(client, "gv002@dainam.edu.vn")
    assert client.get("/admin/download/all.zip", follow_redirects=False).status_code == 403
    assert client.get("/admin/downloads", follow_redirects=False).status_code == 403
    sub = store.find_one("submissions", user_id="u-gv1")
    assert client.get(f"/council/submission/{sub['id']}/download.zip", follow_redirects=False).status_code == 403
