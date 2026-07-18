# DNU AI-Assess

Hệ thống tiếp nhận hồ sơ và **chấm điểm tự động bằng AI** phục vụ Chương trình khảo sát, đánh giá năng lực ứng dụng AI của giảng viên **Trường Đại học Đại Nam (DNU) năm 2026**.

## Chức năng chính

- **Nộp hồ sơ trực tuyến** theo cấu trúc Phần A–G: kê khai thông tin, tải sản phẩm và minh chứng sử dụng AI, kiểm tra hợp lệ thời gian thực, nộp lại trước hạn (17h00 ngày 30/6/2026).
- **Chấm tự động bằng Claude API** theo rubric của đề bài: mỗi tiêu chí chấm 2 lượt độc lập, chênh lệch >15% chấm lượt thứ 3 và lấy trung vị; tự động đối chiếu minh chứng Phần G.
- **Thẩm định bởi Hội đồng**: điều chỉnh và phê duyệt điểm AI đề xuất, ghi vết đầy đủ (audit log), xử lý phản hồi của giảng viên.
- **Báo cáo**: dashboard tiến độ theo khoa/bộ môn, phân loại 4 mức năng lực, xuất báo cáo toàn trường và Hồ sơ năng lực AI từng giảng viên (PDF).
- **Quản trị**: danh sách giảng viên, cấu hình rubric/mốc thời gian, vận hành chấm, sao lưu.

## Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.12 · FastAPI |
| Frontend | Jinja2 · TailwindCSS · Alpine.js · Chart.js (tiếng Việt, responsive) |
| Chấm AI | Claude API (`claude-opus-4-8`, structured outputs) — chấm từng hồ sơ theo yêu cầu |
| Dữ liệu | Firestore + Google Cloud Storage (production) · SQLite + thư mục cục bộ (dev) |
| Xác thực | Đăng nhập ID (email/mã GV) + mật khẩu · 3 vai trò: giảng viên / hội đồng / quản trị |
| Triển khai | Docker · Google Cloud Run · Cloud Scheduler |

## Cài đặt & bàn giao

Cài MỚI lên Google Cloud của một Trường bằng **một lệnh** (trong Google Cloud Shell):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
PROJECT_ID="<project>" ORG_NAME="Trường Đại học X" ORG_SHORT="UX" \
ADMIN_EMAIL="admin@x.edu.vn" bash deploy/deploy.sh
```

Cập nhật bản đã cài (giữ nguyên dữ liệu): `PROJECT_ID="<project>" SERVICE="ai-assess" bash deploy/update.sh`

- 📦 Đóng gói bộ cài bàn giao: `bash scripts/build_bundle.sh` → `dist/AI-Assess-<phiên-bản>.zip`
- 🚀 **[Hướng dẫn cài đặt & cập nhật GCP](docs/HUONG_DAN_CAI_DAT.md)** · 📋 **[Danh mục bàn giao](docs/DANH_MUC_BAN_GIAO.md)**
- 🏫 Bàn giao **nhiều trường**: mỗi trường một dự án GCP riêng, đặt `ORG_NAME`/`ORG_SHORT` để hiển thị đúng thương hiệu.

## Chạy nhanh (demo cục bộ, không cần GCP)

```bash
pip install -r requirements.txt
python scripts/seed_demo.py        # tạo tài khoản demo + hồ sơ mẫu
uvicorn app.main:app --reload      # → http://localhost:8000
```

Đăng nhập `admin@dainam.edu.vn` → **Khóa ngay** → **Bắt đầu chấm** → đăng nhập `hoidong@dainam.edu.vn` thẩm định/phê duyệt → admin **Công bố** → đăng nhập `gv001@dainam.edu.vn` xem kết quả. Đặt `ANTHROPIC_API_KEY` để chấm bằng Claude thật (không có thì dùng bộ chấm mock cho demo).

Kiểm thử: `pytest -q` (24 test) · Lint: `ruff check app tests scripts`

## Tài liệu

- 📋 **[Kế hoạch xây dựng](docs/KE_HOACH_XAY_DUNG.md)** — kiến trúc, mô hình dữ liệu, thiết kế engine chấm, lộ trình, rủi ro.
- 🚀 **[Hướng dẫn chạy & triển khai](docs/HUONG_DAN_CHAY.md)** — chạy local, deploy Cloud Run, biến môi trường, luồng nghiệp vụ.

## Trạng thái

🟢 **Hoàn thành các giai đoạn 0–5 (chế độ local đầy đủ chức năng):** nộp hồ sơ A–G, engine chấm Claude (2 lượt + trung vị, trừ minh chứng, đối chiếu Phần G), thẩm định + audit log, phản hồi 3 ngày, dashboard/báo cáo/hồ sơ năng lực, quản trị + cron nhắc hạn/khóa hồ sơ, Dockerfile + CI.

⏭ **Còn lại (Giai đoạn 6 — production):** kích hoạt Firestore/GCS signed URL + Google SSO trên môi trường GCP thật, chấm thí điểm bằng Claude API thật để hiệu chỉnh prompt, kiểm thử tải. Mốc go-live: **22/6/2026**.
