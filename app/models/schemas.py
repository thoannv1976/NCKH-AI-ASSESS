"""Pydantic schemas dùng chung — đặc biệt là định dạng kết quả chấm của AI
(structured output: Claude bắt buộc trả về đúng schema này)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CriterionGrade(BaseModel):
    """Kết quả chấm một tiêu chí trong một lượt chấm."""

    id: str = Field(description="Mã tiêu chí, ví dụ TM1, I5, II2")
    score: float = Field(description="Điểm chấm, từ 0 đến điểm tối đa của tiêu chí, bước 0.25")
    comment: str = Field(description="Nhận xét ngắn gọn bằng tiếng Việt: điểm mạnh, điểm yếu, lý do mức điểm")
    evidence_ok: bool = Field(
        description="Minh chứng/sản phẩm liên quan tiêu chí này có đầy đủ và kiểm chứng được không"
    )


class PartGradeResult(BaseModel):
    """Kết quả chấm một Phần của phiếu đánh giá trong một lượt chấm độc lập."""

    criteria: list[CriterionGrade] = Field(description="Điểm từng tiêu chí của phần này, đủ mọi tiêu chí")
    evidence_findings: str = Field(
        description="Nhận định chung về minh chứng/sản phẩm kèm theo của phần này"
    )
    anomaly_flags: list[str] = Field(
        description="Các dấu hiệu bất thường cần Hội đồng thẩm định: đạo văn, trích dẫn ảo, "
        "số liệu/kết quả không nhất quán, sản phẩm khoa học không khớp công trình, liên kết không truy cập được... "
        "Để trống nếu không có."
    )
