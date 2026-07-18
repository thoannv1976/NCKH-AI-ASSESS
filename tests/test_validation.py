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
    assert check_naming("SV001_PhanI_BaoCaoTongKet.docx", "SV001", "I") is None
    assert check_naming("sv001_phani_baocao.docx", "SV001", "I") is None  # không phân biệt hoa thường
    assert check_naming("BaoCao.docx", "SV001", "I") is not None
    assert check_naming("SV002_PhanI_BaoCao.docx", "SV001", "I") is not None
    assert check_naming("SV001_PhanII_SanPham.docx", "SV001", "I") is not None


def test_part_a_complete():
    ok, missing = part_a_complete({
        "ten_cong_trinh": "Đề tài NCKH", "loai": "thuyet_minh", "ho_ten": "A",
        "ma_gv": "2211110001", "khoa_bo_mon": "Viện KT&KDQT",
    })
    assert ok and not missing

    ok, missing = part_a_complete({"ho_ten": "A"})
    assert not ok
    assert len(missing) == 4  # thiếu ten_cong_trinh, loai, ma_gv, khoa_bo_mon

    ok, missing = part_a_complete(None)
    assert not ok
