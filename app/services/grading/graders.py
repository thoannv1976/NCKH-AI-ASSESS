"""Các bộ chấm: ClaudeGrader (Claude API, structured output) và MockGrader
(xác định, không tốn phí — dùng cho test/demo khi chưa có API key)."""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod

from app.models.schemas import CriterionGrade, PartGradeResult
from app.services.grading.prompts import system_prompt, user_prompt

logger = logging.getLogger("dnu.grading")


def is_transient_error(exc: Exception) -> bool:
    """Lỗi tạm thời nên thử lại: quá tải (529), giới hạn tần suất (429), 5xx, lỗi mạng/timeout.

    Lỗi cấu hình (key sai 401, không có quyền 403, sai model 404, yêu cầu sai 400)
    KHÔNG tạm thời → không thử lại, báo ngay cho Admin.
    """
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status == 429 or status >= 500):
        return True
    return type(exc).__name__ in {
        "OverloadedError", "InternalServerError", "RateLimitError",
        "APITimeoutError", "APIConnectionError",
    }


def friendly_ai_error(exc: Exception, model: str = "") -> str:
    """Thông điệp dễ hiểu cho Admin, phân biệt lỗi tạm thời và lỗi cấu hình."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    text = str(exc).lower()
    if status == 529 or name == "OverloadedError" or "overloaded" in text:
        return ("Máy chủ Claude đang quá tải (529 Overloaded) — lỗi tạm thời từ phía Anthropic, "
                "KHÔNG phải do API key. Vui lòng thử lại sau ít phút.")
    if status == 401 or name == "AuthenticationError":
        return "API key không hợp lệ hoặc đã bị thu hồi (401). Vui lòng nạp lại key."
    if status == 403 or name == "PermissionDeniedError":
        return "API key không có quyền dùng model này (403). Kiểm tra quyền và hạn mức tài khoản Anthropic."
    if status == 404 or name == "NotFoundError":
        return f"Không tìm thấy model '{model}' (404). Kiểm tra lại tên model."
    if status == 429 or name == "RateLimitError":
        return "Đã chạm giới hạn tần suất gọi (429). Thử lại sau ít phút hoặc giảm tốc độ chấm."
    return f"Lỗi kết nối: {name}: {exc}"[:200]


class Grader(ABC):
    name = "base"

    @abstractmethod
    def grade(self, part: str, part_def: dict, context: dict,
              products_text: str, evidence_text: str, pass_no: int) -> PartGradeResult: ...


class MockGrader(Grader):
    """Điểm giả lập xác định theo hash (ổn định giữa các lần chạy, lượt 1/2 lệch nhẹ)."""

    name = "mock"

    def _factor(self, key: str) -> float:
        h = hashlib.sha256(key.encode()).digest()
        return 0.5 + (h[0] / 255) * 0.45  # 0.50 → 0.95

    def grade(self, part, part_def, context, products_text, evidence_text, pass_no):
        sid = context.get("submission_id", "")
        has_products = bool(products_text.strip()) and "[Không có sản phẩm" not in products_text
        has_evidence = bool(evidence_text.strip()) and "[Không có minh chứng" not in evidence_text
        criteria = []
        for c in part_def["criteria"]:
            base = self._factor(f"{sid}:{part}:{c['id']}")
            jitter = ((pass_no * 7919) % 13 - 6) / 100  # ±0.06 — đa số dưới ngưỡng lệch 15%
            factor = min(0.98, max(0.05, base + jitter)) if has_products else 0.0
            if c.get("bonus"):
                factor = factor if "khuyến khích" in products_text.lower() else 0.0
            score = round(round(c["max"] * factor / 0.25) * 0.25, 2)
            criteria.append(CriterionGrade(
                id=c["id"], score=score,
                comment=f"[Chấm thử nghiệm lượt {pass_no}] Đánh giá tự động tiêu chí {c['id']}: "
                        f"đạt khoảng {factor * 100:.0f}% yêu cầu." if has_products
                        else f"Không có sản phẩm cho tiêu chí {c['id']} — 0 điểm.",
                evidence_ok=has_evidence,
            ))
        flags = []
        if "BATTHUONG" in products_text:
            flags.append("Phát hiện dấu hiệu bất thường trong nội dung (mock)")
        return PartGradeResult(
            criteria=criteria,
            evidence_findings="Minh chứng có nộp." if has_evidence else "Không có minh chứng cho phần này.",
            anomaly_flags=flags,
        )


class ClaudeGrader(Grader):
    """Chấm bằng Claude API.

    - Structured output (messages.parse + Pydantic) → kết quả luôn đúng schema.
    - System prompt chứa rubric gắn cache_control → các hồ sơ cùng Phần dùng lại cache.
    - SDK tự retry 429/5xx; bọc thêm lần thử cho lỗi tạm thời (quá tải 529, mạng),
      dừng ngay với lỗi cấu hình (key/model sai) để khỏi tốn thời gian.
    """

    name = "claude"

    def __init__(self, model: str, api_key: str = "", on_usage=None):
        import anthropic

        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key or None, max_retries=3)
        self.on_usage = on_usage  # callable(model, usage) — ghi nhận token đã dùng

    def grade(self, part, part_def, context, products_text, evidence_text, pass_no):
        sys_blocks = [{
            "type": "text",
            "text": system_prompt(part, part_def),
            "cache_control": {"type": "ephemeral"},
        }]
        msg = user_prompt(part, context, products_text, evidence_text)
        last_exc: Exception | None = None
        attempts = 4
        for attempt in range(attempts):
            try:
                response = self.client.messages.parse(
                    model=self.model,
                    max_tokens=8000,
                    system=sys_blocks,
                    messages=[{"role": "user", "content": msg}],
                    output_format=PartGradeResult,
                )
                if self.on_usage is not None:
                    try:
                        self.on_usage(self.model, getattr(response, "usage", None))
                    except Exception:  # noqa: BLE001 — ghi usage lỗi không được làm hỏng việc chấm
                        logger.warning("Không ghi được usage AI", exc_info=True)
                result = response.parsed_output
                if result is None:
                    raise ValueError("Claude không trả về kết quả đúng schema")
                return result
            except Exception as exc:  # noqa: BLE001 — phân loại tạm thời / cấu hình
                last_exc = exc
                logger.warning("Lỗi chấm %s lượt %s (lần %s): %s", part, pass_no, attempt + 1, exc)
                # ValueError = output lệch schema (thử lại); lỗi cấu hình (key/model) → dừng ngay
                retryable = isinstance(exc, ValueError) or is_transient_error(exc)
                if not retryable or attempt == attempts - 1:
                    break
                time.sleep(2 * (attempt + 1))  # backoff 2s, 4s, 6s cho lỗi quá tải
        raise RuntimeError(f"Chấm Phần {part} thất bại: {friendly_ai_error(last_exc, self.model)}")


def create_grader(settings, store=None) -> Grader:
    """Tạo bộ chấm. Nếu có store: dùng cấu hình AI Admin nạp trong app (DB) và ghi nhận usage."""
    if store is not None:
        from app.services.ai_config import get_ai_config
        from app.services.ai_usage import record_usage

        cfg = get_ai_config(store)
        if cfg["grader"] == "claude":
            return ClaudeGrader(cfg["model"], cfg["api_key"],
                                on_usage=lambda model, usage: record_usage(store, model, usage))
        return MockGrader()
    if settings.grader_kind == "claude":
        return ClaudeGrader(settings.grading_model, settings.anthropic_api_key)
    return MockGrader()
