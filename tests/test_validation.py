"""Unit test: kiểm tra hợp lệ tệp, tên tệp, Phần A."""
from app.services.validation import check_extension, check_naming, check_size, part_a_complete


def test_extension():
    assert check_extension("bai.docx") is None
    assert check_extension("bai.pdf") is None
    assert check_extension("bai.pptx") is None
    assert check_extension("bai.xlsx") is None
    assert check_extension("video.mp4") is None
    assert check_extension("script.exe") is not None
    assert check_extension("anh.png") is not None
    assert check_extension("khong_duoi") is not None


def test_size():
    assert check_size(1024) is None
    assert check_size(200 * 1024 * 1024) is None
    assert check_size(200 * 1024 * 1024 + 1) is not None
    assert check_size(0) is not None


def test_naming_convention():
    assert check_naming("GV001_PhanB_DeCuongHocPhan.docx", "GV001", "B") is None
    assert check_naming("gv001_phanb_decuong.docx", "GV001", "B") is None  # không phân biệt hoa thường
    assert check_naming("DeCuong.docx", "GV001", "B") is not None
    assert check_naming("GV002_PhanB_DeCuong.docx", "GV001", "B") is not None
    assert check_naming("GV001_PhanC_GiaoAn.docx", "GV001", "B") is not None


def test_part_a_complete():
    ok, missing = part_a_complete({
        "ho_ten": "A", "ma_gv": "GV001", "khoa_bo_mon": "CNTT",
        "hoc_phan": "AI", "cong_cu_ai": ["Claude"], "muc_thanh_thao": 4,
    })
    assert ok and not missing

    ok, missing = part_a_complete({"ho_ten": "A"})
    assert not ok
    assert len(missing) == 5

    ok, missing = part_a_complete(None)
    assert not ok
