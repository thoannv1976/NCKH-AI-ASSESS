"""Unit test: logic chấm 2 lượt + trung vị, trần điểm phần, cờ dưới mức tối thiểu, phân loại."""
from app.rubric import load_rubric_seed
from app.services.classify import classify
from app.services.grading.engine import (
    apply_evidence_rules, combine_two_passes, flag_below_min, median_of_three, part_total,
)
from app.services.ops import appeal_window_open, working_days_since
from app.config import parse_dt


def _type(key: str) -> dict:
    """Bộ tiêu chí của một loại công trình (hình dạng rubric đơn)."""
    return load_rubric_seed()["types"][key]


def test_two_passes_close_means_average():
    # lệch 1 điểm trên thang 8 = 12.5% < 15% → trung bình
    score, needs_third = combine_two_passes(8, 6.0, 7.0)
    assert not needs_third
    assert score == 6.5


def test_two_passes_diverged_triggers_third():
    # lệch 2 trên thang 8 = 25% > 15% → cần lượt 3
    _, needs_third = combine_two_passes(8, 5.0, 7.0)
    assert needs_third


def test_threshold_is_15_percent_of_max():
    # thang 10: lệch 1.5 = đúng 15% → KHÔNG vượt ngưỡng (phải >15%)
    score, needs_third = combine_two_passes(10, 7.0, 8.5)
    assert not needs_third
    assert score == 7.75
    _, needs_third = combine_two_passes(10, 7.0, 8.6)
    assert needs_third


def test_median_of_three():
    assert median_of_three(10, 5.0, 9.0, 8.0) == 8.0
    assert median_of_three(10, 9.0, 5.0, 5.5) == 5.5
    # điểm vượt trần bị kẹp về max trước khi lấy trung vị
    assert median_of_three(10, 12.0, 9.0, 11.0) == 10.0


def test_scores_clamped():
    score, _ = combine_two_passes(8, 9.5, 100.0)  # cả hai kẹp về 8
    assert score == 8.0


def test_evidence_penalty_optional_and_applies_when_required():
    """apply_evidence_rules chỉ trừ điểm khi được gọi với evidence_missing=True."""
    part = {"criteria": [
        {"id": "X1", "max": 8},
        {"id": "X2", "max": 6, "is_evidence_criterion": True},
    ]}
    finals = {
        "X1": {"score": 6.0, "comment": "tốt", "evidence_penalty": False},
        "X2": {"score": 4.0, "comment": "có", "evidence_penalty": False},
    }
    apply_evidence_rules(part, finals, evidence_missing=True)
    assert finals["X1"]["score"] == 3.0   # trừ 50%
    assert finals["X2"]["score"] == 0.0   # tiêu chí minh chứng → 0
    assert all(finals[c]["evidence_penalty"] for c in finals)


def test_evidence_no_penalty_when_present():
    part = _type("bao_cao_co_ban")["parts"]["I"]
    finals = {c["id"]: {"score": 2.0, "comment": "", "evidence_penalty": False} for c in part["criteria"]}
    apply_evidence_rules(part, finals, evidence_missing=False)
    assert all(f["score"] == 2.0 for f in finals.values())


def test_part_total_capped_at_max_score():
    part_i = _type("bao_cao_co_ban")["parts"]["I"]  # tối đa 85
    finals = {c["id"]: {"score": c["max"]} for c in part_i["criteria"]}
    assert part_total("I", part_i, finals) == 85.0


def test_flag_below_min_thuyet_minh():
    part_tm = _type("thuyet_minh")["parts"]["TM"]
    finals = {c["id"]: {"score": c["max"], "comment": "", "name": c["name"]} for c in part_tm["criteria"]}
    # Hạ TM1 xuống dưới mức tối thiểu (min=6)
    finals["TM1"]["score"] = 4.0
    flags = flag_below_min("TM", part_tm, finals)
    assert any("TM1" in f and "tối thiểu" in f for f in flags)


def test_classification_bao_cao():
    bc = _type("bao_cao_co_ban")
    assert classify(80, bc)["key"] == "du_dieu_kien_cap_truong"
    assert classify(100, bc)["key"] == "du_dieu_kien_cap_truong"
    assert classify(79.9, bc)["key"] == "kha"
    assert classify(65, bc)["key"] == "kha"
    assert classify(50, bc)["key"] == "dat"
    assert classify(49.9, bc)["key"] == "khong_dat"
    assert classify(0, bc)["key"] == "khong_dat"


def test_classification_thuyet_minh():
    tm = _type("thuyet_minh")
    assert classify(52, tm)["key"] == "de_nghi_thuc_hien"
    assert classify(100, tm)["key"] == "de_nghi_thuc_hien"
    assert classify(51.9, tm)["key"] == "khong_thuc_hien"
    assert classify(0, tm)["key"] == "khong_thuc_hien"


def test_appeal_window_3_working_days():
    # Công bố thứ Sáu 10/7/2026 → thứ 2(1), thứ 3(2), thứ 4(3 ngày làm việc 15/7)
    published = "2026-07-10T09:00:00+07:00"
    assert working_days_since(parse_dt(published), parse_dt("2026-07-11T09:00:00+07:00")) == 0  # thứ 7
    assert working_days_since(parse_dt(published), parse_dt("2026-07-13T09:00:00+07:00")) == 1  # thứ 2
    assert appeal_window_open(published, parse_dt("2026-07-15T16:00:00+07:00"))   # 3 ngày làm việc
    assert not appeal_window_open(published, parse_dt("2026-07-16T09:00:00+07:00"))  # ngày thứ 4


def test_prompt_includes_four_levels():
    """Prompt chấm phải liệt kê 4 mức neo (Xuất sắc/Đạt/Cơ bản/Chưa đạt) kèm khoảng điểm."""
    from app.services.grading.prompts import system_prompt

    part_tm = _type("thuyet_minh")["parts"]["TM"]
    sp = system_prompt("TM", part_tm)
    for label in ["Xuất sắc", "Đạt yêu cầu", "Cơ bản", "Chưa đạt"]:
        assert label in sp
    # TM1 tối đa 10 → mức Xuất sắc khoảng 9–10 điểm
    assert "9–10 điểm" in sp
