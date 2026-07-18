"""Cấu hình ứng dụng FTU NCKH-Assess.

Hệ thống quản lý và đánh giá đề tài/công trình nghiên cứu khoa học sinh viên
(Trường Đại học Ngoại thương). Hai chế độ chạy (APP_MODE):
- "local": SQLite + lưu tệp cục bộ + đăng nhập giả lập + email ghi log (dev/demo)
- "gcp":   Firestore + Google Cloud Storage + Google SSO + SMTP (production)
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

ALLOWED_EXTENSIONS = {".docx", ".pdf", ".pptx", ".xlsx", ".mp4"}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB/tệp

# Cấu trúc phần của mỗi bộ tiêu chí lấy từ rubric (khác nhau theo loại công trình:
# thuyết minh dùng 1 phần "TM"; báo cáo tổng kết dùng 2 phần "I", "II").
# Dùng app.rubric.graded_parts(rubric) để lấy danh sách phần được chấm của một hồ sơ.

# Vai trò (giữ khóa nội bộ để tương thích; nhãn hiển thị theo domain NCKH sinh viên):
#   lecturer → Chủ nhiệm/Nhóm sinh viên · council → Hội đồng đánh giá · admin → Quản trị (Phòng QLKH)
ROLE_LECTURER = "lecturer"
ROLE_COUNCIL = "council"
ROLE_ADMIN = "admin"


class Settings:
    def __init__(self) -> None:
        self.app_mode = os.environ.get("APP_MODE", "local")
        self.base_dir = Path(__file__).resolve().parent.parent

        # Định danh tổ chức (cho phép bàn giao nhiều trường — mặc định FTU)
        self.org_name = os.environ.get("ORG_NAME", "Trường Đại học Ngoại thương")
        self.org_short = os.environ.get("ORG_SHORT", "FTU")
        self.program_year = os.environ.get("PROGRAM_YEAR", "2026")
        self.app_title = os.environ.get("APP_TITLE", "") or f"{self.org_short} NCKH-Assess"

        self.data_dir = Path(os.environ.get("DATA_DIR", self.base_dir / "data"))
        self.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
        self.cron_token = os.environ.get("CRON_TOKEN", "dev-cron-token")

        # Chấm AI
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.grading_model = os.environ.get("GRADING_MODEL", "claude-opus-4-8")
        self.grader_kind = os.environ.get("GRADER", "claude" if self.anthropic_api_key else "mock")

        # Mốc thời gian mặc định (admin có thể sửa trong DB, DB là nguồn chính).
        # Mặc định theo hạn nộp Thuyết minh chuyên đề SV NCKH 2026: 17h00 ngày 28/03/2026.
        self.default_deadline = os.environ.get("DEADLINE", "2026-03-28T17:00:00+07:00")
        self.default_open_at = os.environ.get("OPEN_AT", "2026-02-13T00:00:00+07:00")

        # Đăng nhập bằng ID (email/mã GV) + mật khẩu
        # Bootstrap quản trị viên: các email này được tạo/nâng quyền admin khi khởi động
        self.admin_emails = [
            e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
        ]
        # Mật khẩu cho admin bootstrap; mật khẩu mặc định cho người dùng import không kèm mật khẩu
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "")
        self.default_password = os.environ.get("DEFAULT_PASSWORD", "FTU@2026")

        # GCP
        self.gcs_bucket = os.environ.get("GCS_BUCKET", "")
        self.firestore_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

        # SMTP (chế độ gcp)
        self.smtp_host = os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.mail_from = os.environ.get("MAIL_FROM", "nckh-assess@ftu.edu.vn")

        self.data_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Dùng trong test khi đổi biến môi trường."""
    global _settings
    _settings = None


def now_vn() -> datetime:
    return datetime.now(TZ)


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt
