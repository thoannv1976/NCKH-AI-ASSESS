# HƯỚNG DẪN CÀI ĐẶT & CẬP NHẬT AI-ASSESS LÊN GOOGLE CLOUD

Tài liệu hướng dẫn **cài đặt mới** và **cập nhật** phần mềm **AI-Assess** (đánh giá năng lực ứng dụng AI của giảng viên) lên tài khoản Google Cloud (GCP) của một Trường. Mỗi trường cài trên **dự án GCP riêng**; dữ liệu và chi phí nằm hoàn toàn trên tài khoản của trường đó. Cùng một bộ cài dùng được cho nhiều trường — chỉ cần đổi tham số định danh (tên trường, dự án, email quản trị).

## 1. Kiến trúc & thành phần

| Thành phần | Dịch vụ Google Cloud | Vai trò |
|---|---|---|
| Ứng dụng web | **Cloud Run** | Chạy phần mềm (đóng gói container), tự co giãn theo tải |
| Cơ sở dữ liệu | **Firestore** (Native) | Hồ sơ, điểm, người dùng, nhật ký |
| Lưu tệp | **Cloud Storage** | Sản phẩm và minh chứng của giảng viên |
| Bí mật | **Secret Manager** | API key, khóa phiên, token, mật khẩu |
| Lập lịch | **Cloud Scheduler** | Nhắc hạn 24h, khóa hồ sơ đúng hạn |
| Chấm điểm | **Claude API** (Anthropic) | Chấm tự động theo rubric |

## 2. Chuẩn bị (một lần cho mỗi trường)

1. **Tài khoản Google Cloud của Trường** với một **Project** (ví dụ `truong-x-aiassess`) đã **bật Billing**. Người cài cần quyền `Owner` hoặc (`Editor` + `Secret Manager Admin`) trên project.
2. **Khóa Claude API** (`sk-ant-...`) lấy từ https://console.anthropic.com (mục API Keys). Có thể để sau và nạp trong phần mềm.
3. **Bộ cài** (file `.zip` bàn giao, giải nén ra thư mục có `Dockerfile`).
4. **Danh sách giảng viên** dạng CSV theo mẫu `docs/mau_import_giang_vien.csv`.

> Khuyến nghị dùng **Google Cloud Shell** (biểu tượng `>_` góc trên phải Console) — đã cài sẵn `gcloud`, `gsutil`, không cần cài gì trên máy cá nhân. Kéo–thả file `.zip` vào Cloud Shell rồi `unzip`.

## 3. Cài đặt MỚI tự động (khuyến nghị — 1 lệnh)

Trong Cloud Shell, vào thư mục bộ cài và chạy `deploy/deploy.sh` với các tham số của trường:

```bash
cd AI-Assess-*                          # vào thư mục bộ cài (có Dockerfile)
export ANTHROPIC_API_KEY="sk-ant-..."   # khóa Claude API (có thể bỏ qua, nạp sau trong app)
PROJECT_ID="truong-x-aiassess" \
ORG_NAME="Trường Đại học X" \
ORG_SHORT="UX" \
ADMIN_EMAIL="admin@x.edu.vn" \
bash deploy/deploy.sh
```

Script tự động: bật API → tạo Firestore → tạo bucket → tạo secret (khóa phiên, token, mật khẩu admin, API key) → cấp quyền → build & deploy Cloud Run → tạo Cloud Scheduler. Mất khoảng **3–7 phút**.

Kết thúc, màn hình in ra **Địa chỉ hệ thống**, **tài khoản** và **mật khẩu quản trị** — hãy lưu lại và đổi mật khẩu sau khi đăng nhập. Tên trường (`ORG_NAME`/`ORG_SHORT`) sẽ hiển thị trên giao diện, email và tài liệu của trường đó.

**Biến tùy chỉnh** (đặt trước lệnh nếu cần):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `PROJECT_ID` | *(bắt buộc)* | Mã dự án GCP của trường |
| `ORG_NAME` / `ORG_SHORT` | Trường Đại học Đại Nam / DNU | Tên & viết tắt hiển thị |
| `PROGRAM_YEAR` | 2026 | Năm chương trình |
| `ADMIN_EMAIL` | admin@example.edu.vn | Tài khoản quản trị đầu tiên |
| `SERVICE` | ai-assess | Tên dịch vụ Cloud Run + tiền tố tài nguyên |
| `REGION` | asia-southeast1 | Vùng triển khai |
| `GRADING_MODEL` | claude-opus-4-8 | Model AI chấm |
| `DEADLINE` / `OPEN_AT` | 30/6 – 25/6/2026 | Mốc thời gian (sửa được trong app) |
| `SMTP_HOST`,`SMTP_USER`,`SMTP_PASSWORD`,`MAIL_FROM` | *(trống)* | Cấu hình email (xem mục 6) |

## 4. Cài đặt thủ công (khi cần kiểm soát từng bước)

Thay `PROJECT`, `PREFIX` (mặc định `ai-assess`), `BUCKET` cho phù hợp:

```bash
PROJECT=truong-x-aiassess; PREFIX=ai-assess; REGION=asia-southeast1
BUCKET=${PROJECT}-${PREFIX}
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com storage.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com

gcloud firestore databases create --location=$REGION
gsutil mb -l $REGION gs://$BUCKET

printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create ${PREFIX}-secret-key --data-file=-
printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create ${PREFIX}-cron-token --data-file=-
printf '%s' "Admin@2026"              | gcloud secrets create ${PREFIX}-admin-password --data-file=-
printf '%s' "sk-ant-..."              | gcloud secrets create ${PREFIX}-anthropic-key --data-file=-

NUM=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
SA="${NUM}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role=roles/datastore.user
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
gsutil iam ch "serviceAccount:$SA:roles/storage.objectAdmin" gs://$BUCKET

gcloud run deploy $PREFIX --source . --region $REGION --allow-unauthenticated --min-instances 1 --memory 1Gi \
  --set-env-vars "^@@^APP_MODE=gcp@@GCS_BUCKET=$BUCKET@@GOOGLE_CLOUD_PROJECT=$PROJECT@@GRADING_MODEL=claude-opus-4-8@@ADMIN_EMAILS=admin@x.edu.vn@@ORG_NAME=Trường Đại học X@@ORG_SHORT=UX@@PROGRAM_YEAR=2026" \
  --set-secrets SECRET_KEY=${PREFIX}-secret-key:latest,CRON_TOKEN=${PREFIX}-cron-token:latest,ADMIN_PASSWORD=${PREFIX}-admin-password:latest,ANTHROPIC_API_KEY=${PREFIX}-anthropic-key:latest

# Scheduler (thay <URL> bằng địa chỉ Cloud Run, <TOKEN> bằng giá trị ${PREFIX}-cron-token)
gcloud scheduler jobs create http ${PREFIX}-cron --location $REGION \
  --schedule "*/30 * * * *" --uri "<URL>/tasks/cron" --http-method POST \
  --headers "X-Cron-Token=<TOKEN>" --time-zone "Asia/Ho_Chi_Minh"
```

## 5. Sau khi cài đặt

1. Mở **Địa chỉ hệ thống**, đăng nhập tài khoản **quản trị** (email + mật khẩu in khi cài). Vào **Đổi mật khẩu**.
2. Vào **Cấu hình AI**: nạp/kiểm tra **Claude API key** (nếu chưa đặt khi cài), bấm **Kiểm tra kết nối Claude**.
3. Vào **Cấu hình → Rubric**: bấm **Nạp lại rubric mới nhất từ phần mềm** để chắc chắn đang dùng rubric mới nhất kèm bộ cài.
4. Vào **Người dùng → Import (CSV)**: tải danh sách giảng viên theo mẫu `docs/mau_import_giang_vien.csv` (cột `ma_gv,ho_ten,email,don_vi,bo_mon,chuc_vu,role,password`; vẫn nhận cột cũ `khoa`).
5. Vào **Cấu hình**: kiểm tra mốc thời gian (mở nộp, hạn nộp).
6. Kiểm tra nhanh: mở `<URL>/healthz` (trả về `{"ok": true}`).

## 6. Cấu hình email gửi đi (tùy chọn nhưng khuyến nghị)

Mặc định (chưa cấu hình SMTP) phần mềm **chỉ ghi log** email, không gửi ra ngoài (xem trạng thái tại Admin → nhật ký email). Để gửi thật, dùng **Google Workspace/Gmail của trường**:

1. Bật **Xác minh 2 bước** cho tài khoản gửi (ví dụ `ai-assess@x.edu.vn`).
2. Tạo **App Password** (Google Account → Security → App passwords) — chuỗi 16 ký tự.
3. Cài/đặt lại với các biến SMTP:

```bash
PROJECT_ID="truong-x-aiassess" ORG_NAME="Trường Đại học X" ORG_SHORT="UX" \
ADMIN_EMAIL="admin@x.edu.vn" \
SMTP_HOST="smtp.gmail.com" SMTP_USER="ai-assess@x.edu.vn" \
SMTP_PASSWORD="<app-password-16-ky-tu>" MAIL_FROM="ai-assess@x.edu.vn" \
bash deploy/deploy.sh
```

> Dùng email **Workspace theo tên miền trường** (giới hạn ~2.000 thư/ngày, ít vào spam) thay cho Gmail cá nhân (~500/ngày, dễ vào spam). `MAIL_FROM` nên trùng `SMTP_USER`.

## 7. Vận hành

- **Giảng viên** nộp hồ sơ A–G (nhiều tệp/liên kết), nộp lại trước hạn.
- **Khóa hồ sơ**: tự động đúng hạn (Scheduler) hoặc bấm *Khóa ngay* tại trang Vận hành.
- **Chấm**: Admin/Hội đồng vào **Thẩm định**, mở từng hồ sơ và bấm *Chấm tự động hồ sơ này* (kiểm soát tiến độ & chi phí). Theo dõi token/chi phí tại **Chi phí AI**.
- **Phê duyệt & Công bố**: Hội đồng điều chỉnh + phê duyệt; Admin *Công bố* để gửi email kết quả.
- **Bảng điểm / Tải sản phẩm**: xem/tải điểm và sản phẩm toàn trường (Excel/ZIP).

## 8. CẬP NHẬT phiên bản (an toàn dữ liệu)

Khi có bản cập nhật phần mềm: giải nén bộ cài **bản mới**, vào thư mục đó và chạy:

```bash
PROJECT_ID="truong-x-aiassess" SERVICE="ai-assess" bash deploy/update.sh
```

Script chỉ **build lại mã nguồn và triển khai đè** lên dịch vụ đang chạy; **không đụng** tới Firestore, bucket, secret hay biến môi trường — nên **toàn bộ dữ liệu (hồ sơ, điểm, người dùng, cấu hình) được giữ nguyên**.

Sau cập nhật, nếu có thay đổi rubric: Admin → **Cấu hình** → nếu báo "có bản rubric mới hơn" thì bấm **Nạp lại rubric mới nhất từ phần mềm**.

## 9. Bàn giao cho nhiều trường

- Mỗi trường = **một dự án GCP riêng** + một lần chạy `deploy.sh` với `PROJECT_ID`/`ORG_NAME`/`ORG_SHORT`/`ADMIN_EMAIL` của trường đó. Dữ liệu các trường hoàn toàn tách biệt.
- Dùng `SERVICE`/`PREFIX` mặc định (`ai-assess`) cho mọi trường (vì mỗi trường ở project khác nhau, không trùng tài nguyên).
- Cập nhật cho từng trường: chạy `update.sh` với `PROJECT_ID` tương ứng. Có thể lặp qua danh sách project bằng vòng lặp.

## 10. Sao lưu dữ liệu

- Trong app: **Vận hành → Tải bản sao lưu dữ liệu (JSON)**.
- Firestore: `gcloud firestore export gs://<BUCKET>/backups/$(date +%F)`.
- Tệp: dữ liệu đã nằm trên bucket `gs://<PROJECT>-ai-assess`.

## 11. Chi phí vận hành (Trường tự chi trả)

- **AI (Claude API)**: ~2 USD/hồ sơ (≈ 40.000–70.000đ/giảng viên/đợt), tùy độ dài tài liệu và số lần chấm lại.
- **Google Cloud**: ~2,5–5 triệu/đợt (Cloud Run + Firestore + Storage, ~2 tháng cao điểm).
- Ngoài đợt đánh giá, hạ `min-instances` về 0 để gần như không phát sinh chi phí Cloud Run:
  `gcloud run services update ai-assess --region asia-southeast1 --min-instances 0`

## 12. Bảo mật

- Mọi bí mật (API key, khóa phiên, mật khẩu admin, token, mật khẩu SMTP) lưu trong **Secret Manager**, không nằm trong mã nguồn.
- Truy cập HTTPS mặc định của Cloud Run; phân quyền 3 vai trò; nhật ký thao tác (audit log).
- Khuyến cáo: đổi mật khẩu admin sau khi cài; cấp mật khẩu riêng cho từng người; nhắc giảng viên đổi mật khẩu lần đầu.

## 13. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân & cách xử lý |
|---|---|
| Đăng nhập báo sai mật khẩu | Dùng đúng mật khẩu admin in khi cài; hoặc admin đặt lại tại Người dùng |
| Bấm chấm/kiểm tra báo lỗi 529 | Máy chủ Claude quá tải tạm thời — chờ ít phút thử lại (hệ thống đã tự thử lại); KHÔNG phải do API key |
| Bấm chấm báo lỗi 401 | API key sai/đã thu hồi — vào Cấu hình AI nạp lại key |
| Email không tới | Chưa cấu hình SMTP (xem mục 6); kiểm tra trạng thái tại Admin → nhật ký email |
| Tệp >32MB tải lên thất bại | Giới hạn request Cloud Run (~32MB); nén/chia nhỏ tệp |
| Không tạo được Firestore | Tạo thủ công Firestore (Native mode, đúng vùng) trong Console rồi chạy lại |
| Xem log lỗi | `gcloud run services logs read ai-assess --region asia-southeast1 --limit 50` |

## 14. Chạy thử trên máy (không cần GCP)

```bash
pip install -r requirements.txt
python scripts/seed_demo.py          # tạo tài khoản + hồ sơ demo (mật khẩu demo123)
uvicorn app.main:app --reload        # mở http://localhost:8000
```

---
*Mọi vướng mắc trong thời gian bảo hành, liên hệ đơn vị cung cấp theo thông tin trong Hợp đồng.*
