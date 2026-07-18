# FTU NCKH-Assess

Hệ thống tiếp nhận hồ sơ và **hỗ trợ đánh giá bằng AI** phục vụ công tác **quản lý và đánh giá đề tài/công trình sinh viên nghiên cứu khoa học (SV NCKH)** của **Trường Đại học Ngoại thương (FTU) năm 2026**.

Hệ thống bám theo Thể lệ Cuộc thi SV NCKH và Kế hoạch tổ chức của Nhà trường: từ vòng **tuyển chọn thuyết minh chuyên đề** đến **đánh giá/nghiệm thu báo cáo tổng kết công trình**.

## Chức năng chính

- **Nộp hồ sơ trực tuyến**: nhóm sinh viên (01 chủ nhiệm + tối đa 04 thành viên) kê khai thông tin công trình, chọn loại nghiên cứu, tải tài liệu/sản phẩm và minh chứng; kiểm tra hợp lệ thời gian thực, nộp lại trước hạn.
- **Đa bộ tiêu chí theo loại công trình** (`rubrics/rubric.json`):
  - **Thuyết minh chuyên đề** (vòng tuyển chọn): 10 nội dung, thang 100, đề nghị thực hiện khi ≥ 52 điểm và không tiêu chí nào dưới mức tối thiểu.
  - **Báo cáo tổng kết — nghiên cứu cơ bản** (Phụ lục 4.1, Điều 6 Thể lệ).
  - **Báo cáo tổng kết — nghiên cứu ứng dụng** (Phụ lục 4.2, Điều 6 Thể lệ).
- **Chấm sơ bộ bằng Claude API** theo đúng phiếu đánh giá: mỗi tiêu chí chấm 2 lượt độc lập, chênh lệch >15% chấm lượt 3 và lấy trung vị; cảnh báo tiêu chí dưới mức tối thiểu và dấu hiệu bất thường (đạo văn, trích dẫn ảo, số liệu không nhất quán…).
- **Thẩm định bởi Hội đồng**: ủy viên phản biện điều chỉnh và phê duyệt điểm AI đề xuất; điểm công trình là điểm trung bình của các thành viên; ghi vết đầy đủ (audit log); xử lý khiếu nại/phản hồi.
- **Báo cáo**: dashboard tiến độ theo đơn vị (Viện/Khoa/Cơ sở), xếp loại công trình, danh sách công trình đủ điều kiện xét chọn dự Cuộc thi cấp Trường (≥ 80 điểm), xuất phiếu đánh giá từng công trình (PDF/DOCX).
- **Quản trị (Phòng QLKH)**: danh sách người dùng, cấu hình bộ tiêu chí/mốc thời gian, vận hành chấm, sao lưu.

## Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.12 · FastAPI |
| Frontend | Jinja2 · TailwindCSS · Alpine.js · Chart.js (tiếng Việt, responsive) |
| Chấm AI | Claude API (`claude-opus-4-8`, structured outputs) — chấm từng hồ sơ theo yêu cầu |
| Dữ liệu | Firestore + Google Cloud Storage (production) · SQLite + thư mục cục bộ (dev) |
| Xác thực | Đăng nhập ID (email/MSSV) + mật khẩu · 3 vai trò: chủ nhiệm/nhóm SV · hội đồng · quản trị (QLKH) |
| Triển khai | Docker · Google Cloud Run · Cloud Scheduler |

## Cài đặt & bàn giao

Cài MỚI lên Google Cloud bằng **một lệnh** (trong Google Cloud Shell):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
PROJECT_ID="<project>" ORG_NAME="Trường Đại học X" ORG_SHORT="UX" \
ADMIN_EMAIL="admin@x.edu.vn" bash deploy/deploy.sh
```

Cập nhật bản đã cài (giữ nguyên dữ liệu): `PROJECT_ID="<project>" SERVICE="nckh-assess" bash deploy/update.sh`

- 📦 Đóng gói bộ cài bàn giao: `bash scripts/build_bundle.sh` → `dist/NCKH-Assess-<phiên-bản>.zip`
- 🏫 Bàn giao **nhiều trường**: mỗi trường một dự án GCP riêng, đặt `ORG_NAME`/`ORG_SHORT` để hiển thị đúng thương hiệu.

## Chạy nhanh (demo cục bộ, không cần GCP)

```bash
pip install -r requirements.txt
python scripts/seed_demo.py        # tạo tài khoản demo + hồ sơ công trình mẫu
uvicorn app.main:app --reload      # → http://localhost:8000
```

Đăng nhập `admin@ftu.edu.vn` → **Khóa ngay** → **Bắt đầu chấm** → đăng nhập `hoidong@ftu.edu.vn` thẩm định/phê duyệt → admin **Công bố** → đăng nhập `sv001@ftu.edu.vn` xem kết quả (mật khẩu demo: `demo123`). Đặt `ANTHROPIC_API_KEY` để chấm bằng Claude thật (không có thì dùng bộ chấm mock cho demo).

Kiểm thử: `pytest -q` · Lint: `ruff check app tests scripts`

## Bộ tiêu chí đánh giá

Toàn bộ tiêu chí nằm trong `rubrics/rubric.json`, tách theo loại công trình (`thuyet_minh`, `bao_cao_co_ban`, `bao_cao_ung_dung`). Mỗi hồ sơ chọn loại ở Phần A và hệ thống tự áp phiếu đánh giá tương ứng. Quản trị viên có thể xem/xuất phiếu và nạp lại bộ tiêu chí trong mục **Cấu hình** mà không ảnh hưởng hồ sơ/điểm đã có.
