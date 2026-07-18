# Hướng dẫn chạy DNU AI-Assess

## 1. Chạy thử nghiệm trên máy (chế độ local)

Không cần Google Cloud — dữ liệu lưu SQLite + thư mục `data/`, email ghi log.

```bash
pip install -r requirements.txt

# Tạo dữ liệu demo: 3 giảng viên + hội đồng + quản trị + 1 hồ sơ mẫu đầy đủ (docx thật)
python scripts/seed_demo.py

uvicorn app.main:app --reload
# → http://localhost:8000 — đăng nhập bằng ID + mật khẩu
```

**Đăng nhập:** bằng **ID (email hoặc mã giảng viên) + mật khẩu**. Tài khoản demo (mật khẩu đều là `demo123`):
`admin@dainam.edu.vn` (quản trị) · `hoidong@dainam.edu.vn` (hội đồng) · `gv001@dainam.edu.vn` hoặc mã `GV001` (giảng viên, có hồ sơ mẫu). Mọi người dùng có thể tự **Đổi mật khẩu** sau khi đăng nhập; quản trị viên đặt lại mật khẩu / thêm người dùng tại **/admin/users**.

**Demo trọn luồng:** đăng nhập admin → *Khóa ngay* → *Bắt đầu chấm* (chờ vài giây) → đăng nhập hội đồng → thẩm định/điều chỉnh → *Phê duyệt* → admin *Công bố* → đăng nhập gv001 xem kết quả + gửi phản hồi.

### Chấm bằng Claude API thật

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GRADING_MODEL=claude-opus-4-8   # mặc định
uvicorn app.main:app --reload
```

Không có API key → hệ thống tự dùng bộ chấm `mock` (điểm giả lập, phục vụ demo/giao diện). Ép kiểu bộ chấm bằng `GRADER=mock|claude`.

## 2. Kiểm thử

```bash
pip install -r requirements-dev.txt
ruff check app tests scripts
pytest -q          # validation, logic 2 lượt + trung vị, phân quyền, đăng nhập, e2e trọn luồng
```

## 3. Triển khai production (Google Cloud Run)

```bash
# Một lần: tạo Firestore (Native mode) + bucket GCS
gcloud run deploy dnu-ai-assess --source . --region asia-southeast1 \
  --allow-unauthenticated --min-instances 1 --memory 1Gi \
  --set-env-vars APP_MODE=gcp,GCS_BUCKET=<bucket>,ADMIN_EMAILS=admin@dainam.edu.vn \
  --set-env-vars SMTP_HOST=...,SMTP_USER=...,MAIL_FROM=... \
  --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest,SECRET_KEY=app-secret:latest,ADMIN_PASSWORD=admin-pass:latest,SMTP_PASSWORD=smtp-pass:latest,CRON_TOKEN=cron-token:latest
```

`ADMIN_EMAILS` + `ADMIN_PASSWORD` tạo sẵn tài khoản quản trị đầu tiên để đăng nhập ngay sau khi deploy.

Cloud Scheduler (nhắc hạn 24h + khóa hồ sơ đúng 17h00 30/6):

```bash
gcloud scheduler jobs create http dnu-cron --schedule "*/30 * * * *" \
  --uri https://<service-url>/tasks/cron --http-method POST \
  --headers X-Cron-Token=<CRON_TOKEN> --time-zone "Asia/Ho_Chi_Minh"
```

Sau triển khai: đăng nhập admin → **/admin/users** import danh sách giảng viên
(CSV: `ma_gv,ho_ten,email,don_vi,bo_mon,chuc_vu,role,password`; vẫn nhận cột cũ `khoa`). Không có cột `password` → dùng mật khẩu mặc định `DEFAULT_PASSWORD`.

## 4. Biến môi trường chính

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `APP_MODE` | `local` | `local` (SQLite + tệp cục bộ) / `gcp` (Firestore + GCS) |
| `ANTHROPIC_API_KEY` | — | Khóa Claude API; không có → bộ chấm mock |
| `GRADING_MODEL` | `claude-opus-4-8` | Model chấm điểm |
| `GRADER` | tự động | Ép `mock` hoặc `claude` |
| `DEADLINE` | `2026-06-30T17:00:00+07:00` | Hạn nộp (admin sửa được trong /admin/config) |
| `ADMIN_EMAILS` | — | Email (phân cách dấu phẩy) được tự tạo/nâng quyền **quản trị viên** khi khởi động |
| `ADMIN_PASSWORD` | — | Mật khẩu đặt cho tài khoản trong `ADMIN_EMAILS` (nếu chưa có mật khẩu) |
| `DEFAULT_PASSWORD` | `DNU@2026` | Mật khẩu mặc định cho người dùng import CSV không kèm cột password |
| `SEED_DEMO` | — | `1`: tự tạo tài khoản + hồ sơ demo khi khởi động (mật khẩu `demo123`) |
| `SECRET_KEY` | dev | Khóa ký cookie phiên đăng nhập (đặt giá trị ngẫu nhiên ở production) |
| `CRON_TOKEN` | dev | Token bảo vệ endpoint /tasks/cron |
| `DATA_DIR` | `./data` | Thư mục dữ liệu (chế độ local) |

> **Đăng nhập** dùng **ID (email hoặc mã giảng viên) + mật khẩu** băm PBKDF2. Không còn dùng Google SSO.

## 6. Cấu hình AI trong app & thống kê chi phí

Quản trị viên có thể **nạp Claude API key + chọn model ngay trong app** tại **Cấu hình → Cấu hình AI chấm điểm** (không cần đổi biến môi trường; cấu hình DB ưu tiên hơn `ANTHROPIC_API_KEY`). Có nút **Kiểm tra kết nối Claude**. Chế độ: *Tự động* (có key → dùng Claude), *Bắt buộc Claude*, hoặc *Mock* (giả lập).

Mỗi lần gọi Claude được ghi nhận; xem **Thống kê sử dụng AI** (`/admin/ai-usage`): số lần gọi, token (input/output/cache), **ước tính chi phí USD/VND** theo từng model. API key lưu dạng ẩn (chỉ hiện 4 ký tự cuối), không hiển thị nguyên văn.

## 5. Cấu trúc luồng nghiệp vụ

```
GV đăng nhập → kê khai Phần A → nộp sản phẩm + minh chứng B–G (tệp ≤200MB / liên kết)
   → bấm NỘP (email xác nhận; nộp lại được trước hạn — chỉ chấm bản cuối)
[Tùy chọn] Admin/Hội đồng "Chấm tự động hồ sơ này" để kiểm thử & chấm thử TRƯỚC hạn:
   chấm AI theo rubric, KHÔNG khóa quyền sửa của GV; GV sửa lại thì kết quả thử bị xóa để chấm lại.
17h00 30/6: Cloud Scheduler khóa hồ sơ + kiểm tra hợp lệ (trước đó 24h tự nhắc mục thiếu)
Chấm: Admin/Hội đồng vào trang Thẩm định, mở TỪNG hồ sơ và bấm "Chấm tự động hồ sơ này"
   (chấm lần lượt để kiểm soát tiến độ & chi phí — KHÔNG còn chấm toàn bộ tự động).
   Hồ sơ đã khóa khi chấm sẽ chuyển 'graded'; mỗi tiêu chí 2 lượt độc lập, lệch >15% chấm lượt 3 lấy trung vị;
   thiếu minh chứng trừ ≤50%; đối chiếu Phần G; hồ sơ ≥85 hoặc bất thường → thẩm định bắt buộc
Hội đồng xem điểm AI + nhận xét → điều chỉnh (ghi vết) → PHÊ DUYỆT
Admin CÔNG BỐ → email kết quả từng GV → GV xem điểm/nhận xét, phản hồi trong 3 ngày làm việc
Báo cáo: dashboard theo khoa, phân loại 4 mức, xuất Excel, Hồ sơ năng lực (in/PDF), danh sách nòng cốt
```
