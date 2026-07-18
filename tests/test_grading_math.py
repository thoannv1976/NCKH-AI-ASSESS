"""Unit test: logic chấm 2 lượt + trung vị, trừ minh chứng, trần điểm E, phân loại."""
from app.rubric import load_rubric_seed
from app.services.classify import classify
from app.services.grading.engine import (
    apply_evidence_rules, combine_two_passes, median_of_three, part_total,
)
from app.services.ops import appeal_window_open, working_days_since
from app.config import parse_dt


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


def test_evidence_penalty_missing():
    rubric = load_rubric_seed()
    part_b = rubric["parts"]["B"]
    finals = {
        "B1": {"score": 6.0, "comment": "tốt", "evidence_penalty": False},
        "B2": {"score": 4.0, "comment": "khá", "evidence_penalty": False},
        "B3": {"score": 3.0, "comment": "khá", "evidence_penalty": False},
        "B4": {"score": 1.5, "comment": "có", "evidence_penalty": False},
    }
    apply_evidence_rules(part_b, finals, evidence_missing=True)
    assert finals["B1"]["score"] == 3.0   # trừ 50%
    assert finals["B2"]["score"] == 2.0
    assert finals["B4"]["score"] == 0.0   # tiêu chí minh chứng → 0
    assert all(finals[c]["evidence_penalty"] for c in finals)


def test_evidence_no_penalty_when_present():
    rubric = load_rubric_seed()
    part_b = rubric["parts"]["B"]
    finals = {c["id"]: {"score": 2.0, "comment": "", "evidence_penalty": False} for c in part_b["criteria"]}
    apply_evidence_rules(part_b, finals, evidence_missing=False)
    assert all(f["score"] == 2.0 for f in finals.values())


def test_part_e_bonus_capped_at_20():
    rubric = load_rubric_seed()
    part_e = rubric["parts"]["E"]
    finals = {
        "E1": {"score": 10.0}, "E2": {"score": 8.0}, "E3": {"score": 2.0},
        "E_BONUS": {"score": 2.0},
    }
    assert part_total("E", part_e, finals) == 20.0  # 22 → trần 20


def test_classification_thresholds():
    rubric = load_rubric_seed()
    assert classify(85, rubric)["key"] == "dan_dat"
    assert classify(100, rubric)["key"] == "dan_dat"
    assert classify(84.5, rubric)["key"] == "thanh_thao"
    assert classify(70, rubric)["key"] == "thanh_thao"
    assert classify(69.9, rubric)["key"] == "co_ban"
    assert classify(50, rubric)["key"] == "co_ban"
    assert classify(49.9, rubric)["key"] == "khoi_dau"
    assert classify(0, rubric)["key"] == "khoi_dau"


def test_appeal_window_3_working_days():
    # Công bố thứ Sáu 10/7/2026 → thứ 2(1), thứ 3(2), thứ 4(3 ngày làm việc 15/7)
    published = "2026-07-10T09:00:00+07:00"
    assert working_days_since(parse_dt(published), parse_dt("2026-07-11T09:00:00+07:00")) == 0  # thứ 7
    assert working_days_since(parse_dt(published), parse_dt("2026-07-13T09:00:00+07:00")) == 1  # thứ 2
    assert appeal_window_open(published, parse_dt("2026-07-15T16:00:00+07:00"))   # 3 ngày làm việc
    assert not appeal_window_open(published, parse_dt("2026-07-16T09:00:00+07:00"))  # ngày thứ 4


def test_prompt_includes_four_levels():
    """Prompt chấm phải liệt kê 4 mức neo (Xuất sắc/Đạt/Cơ bản/Chưa đạt) kèm khoảng điểm."""
    from app.rubric import load_rubric_seed
    from app.services.grading.prompts import system_prompt

    rubric = load_rubric_seed()
    sp = system_prompt("B", rubric["parts"]["B"])
    for label in ["Xuất sắc", "Đạt yêu cầu", "Cơ bản", "Chưa đạt"]:
        assert label in sp
    # B1 tối đa 8 → mức Xuất sắc khoảng 7.25–8 điểm
    assert "7.25–8 điểm" in sp
