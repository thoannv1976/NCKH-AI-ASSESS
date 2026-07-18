"""Gửi email tự động: xác nhận nộp, nhắc hạn 24h, trả kết quả.
Chế độ local ghi vào email_logs + console; chế độ gcp gửi SMTP thật.
Mọi email đều được lưu email_logs để đối soát."""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.config import get_settings, now_vn

logger = logging.getLogger("dnu.email")


def send_email(store, to: str, subject: str, body: str, kind: str = "general") -> None:
    settings = get_settings()
    status = "logged"
    error = ""
    if settings.app_mode == "gcp" and settings.smtp_host:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = settings.mail_from
            msg["To"] = to
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            status = "sent"
        except Exception as exc:  # noqa: BLE001 — lỗi gửi mail không được làm hỏng nghiệp vụ chính
            status, error = "error", str(exc)
    else:
        logger.info("[EMAIL → %s] %s\n%s", to, subject, body)
    store.add("email_logs", {
        "to": to, "subject": subject, "body": body, "kind": kind,
        "status": status, "error": error, "ts": now_vn().isoformat(),
    })


def _signoff(s) -> str:
    return f"Trân trọng,\nBan tổ chức Chương trình đánh giá năng lực AI – {s.org_short} {s.program_year}"


def email_submit_confirmation(store, user: dict, summary: dict) -> None:
    s = get_settings()
    missing = "\n".join(f"  - {w}" for w in summary.get("warnings", [])) or "  (không có)"
    body = (
        f"Kính gửi {user.get('ho_ten', user['email'])},\n\n"
        f"Hệ thống {s.app_title} xác nhận đã tiếp nhận hồ sơ của thầy/cô lúc {now_vn():%H:%M ngày %d/%m/%Y}.\n"
        f"Các mục cần lưu ý bổ sung trước hạn nộp:\n{missing}\n\n"
        "Thầy/cô có thể nộp lại nhiều lần trước hạn; hệ thống chỉ chấm bản nộp cuối cùng.\n\n"
        f"{_signoff(s)}"
    )
    send_email(store, user["email"], f"[{s.app_title}] Xác nhận nộp hồ sơ thành công", body, kind="confirm")


def email_reminder(store, user: dict, warnings: list[str]) -> None:
    s = get_settings()
    miss = "\n".join(f"  - {w}" for w in warnings)
    body = (
        f"Kính gửi {user.get('ho_ten', user['email'])},\n\n"
        "Còn chưa đầy 24 giờ là đến hạn nộp hồ sơ. "
        "Hồ sơ của thầy/cô còn thiếu các mục sau:\n"
        f"{miss}\n\nĐề nghị thầy/cô hoàn thiện trên hệ thống {s.app_title} trước hạn.\n\n"
        f"{_signoff(s)}"
    )
    send_email(store, user["email"], f"[{s.app_title}] Nhắc hoàn thiện hồ sơ trước hạn 24 giờ", body, kind="reminder")


def email_result(store, user: dict, total: float, label: str, detail_lines: list[str]) -> None:
    s = get_settings()
    detail = "\n".join(detail_lines)
    body = (
        f"Kính gửi {user.get('ho_ten', user['email'])},\n\n"
        f"Kết quả đánh giá năng lực ứng dụng AI năm {s.program_year} của thầy/cô:\n"
        f"  Tổng điểm: {total:g}/100 — Mức năng lực: {label}\n\n"
        f"Điểm thành phần:\n{detail}\n\n"
        "Thầy/cô đăng nhập hệ thống để xem nhận xét chi tiết từng tiêu chí. "
        "Quyền phản hồi kết quả: trong 03 ngày làm việc kể từ ngày công bố, gửi trực tiếp trên hệ thống.\n\n"
        f"{_signoff(s)}"
    )
    send_email(store, user["email"],
               f"[{s.app_title}] Kết quả đánh giá năng lực ứng dụng AI {s.program_year}", body, kind="result")
