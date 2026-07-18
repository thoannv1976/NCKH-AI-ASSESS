"""Phân loại/xếp loại công trình theo bảng classification của bộ tiêu chí đang dùng."""
from __future__ import annotations


def classify(total: float, rubric: dict) -> dict:
    for level in sorted(rubric["classification"], key=lambda x: -x["min"]):
        if total >= level["min"]:
            return level
    return rubric["classification"][-1]
