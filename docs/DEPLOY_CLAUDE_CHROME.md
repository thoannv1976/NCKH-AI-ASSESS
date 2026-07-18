# Hướng dẫn để Claude for Chrome deploy / cập nhật app

Tài liệu này dùng khi nhờ **Claude for Chrome** (tác nhân điều khiển trình duyệt)
triển khai hoặc cập nhật hệ thống **FTU NCKH-Assess** lên **Google Cloud Run**,
thao tác qua **Google Cloud Shell** trong trình duyệt.

- Dự án GCP: `nckh-ai-assess`
- Dịch vụ Cloud Run: `nckh-assess` · Vùng: `asia-southeast1`
- Code chính thức: nhánh `main` của `https://github.com/thoannv1976/NCKH-AI-ASSESS`

---

## A. Chuẩn bị (người dùng làm 1 lần)

- Đăng nhập Google Cloud, chọn đúng dự án `nckh-ai-assess` (đã bật Billing).
- Mở **Cloud Shell** (biểu tượng terminal `>_` góc phải trên console).
- Chuẩn bị Claude API key thật `sk-ant-...` (hoặc nạp sau trong app tại *Cấu hình AI*).

---

## B. CẬP NHẬT bản đang chạy (thường dùng) — prompt dán cho Claude for Chrome

> Dán nguyên khối dưới đây vào Claude for Chrome.

```
Hãy CẬP NHẬT ứng dụng FTU NCKH-Assess đang chạy trên Cloud Run lên code mới nhất (nhánh main), thao tác trong Cloud Shell đang mở. Làm tuần tự, dừng lại báo tôi nếu có lỗi.

Bối cảnh: dự án "nckh-ai-assess", dịch vụ Cloud Run "nckh-assess", vùng "asia-southeast1", hạ tầng đã tạo từ trước. Chỉ cần build code mới, giữ nguyên dữ liệu.

Chạy lần lượt các khối lệnh sau (dán từng khối, chờ xong mới sang khối tiếp):

# 1) Lấy code mới nhất từ main
cd ~
rm -rf nckh-deploy
git clone https://github.com/thoannv1976/NCKH-AI-ASSESS.git nckh-deploy
cd nckh-deploy
head -1 README.md                      # phải in: # FTU NCKH-Assess
grep -m1 version rubrics/rubric.json   # phải thấy phiên bản rubric mới nhất

# 2) Cập nhật Cloud Run (giữ nguyên dữ liệu/secret/biến môi trường). Mất 3-7 phút.
PROJECT_ID="nckh-ai-assess" SERVICE="nckh-assess" bash deploy/update.sh

# 3) (Chạy 1 lần) Sửa tên trường bị mất dấu: xóa ORG_NAME/ORG_SHORT để dùng mặc định đúng trong code
gcloud run services update nckh-assess --region asia-southeast1 --remove-env-vars ORG_NAME,ORG_SHORT

# 4) Kiểm tra
URL=$(gcloud run services describe nckh-assess --region asia-southeast1 --format='value(status.url)')
echo "URL: $URL"
curl -s "$URL/healthz"                  # kỳ vọng: {"ok": true}

Sau khi xong: báo lại URL; mở URL kiểm tra trang đăng nhập hiển thị đúng "Trường Đại học Ngoại thương" (đủ dấu). KHÔNG đăng nhập hộ tôi. Nếu lỗi quyền/billing/secret thì chụp lại và hỏi tôi. Coi API key và mật khẩu là bí mật, không đăng ra ngoài.
```

### Sau khi Claude for Chrome chạy xong (người dùng làm trong app)
1. Đăng nhập **admin** → **Cấu hình**: nếu báo *"có bản rubric mới hơn"* → bấm **Nạp lại rubric mới nhất từ phần mềm** (chỉ thay bộ tiêu chí, không đụng hồ sơ/điểm/người dùng).
2. Đăng nhập **sinh viên** → **Phần A** chọn *Loại nghiên cứu* → dashboard hiện 2 nhóm ô nộp: Vòng 1 *Thuyết minh*, Vòng 2 *Báo cáo tổng kết & sản phẩm*.
3. **Hội đồng** → mở công trình → dùng công tắc **"Vòng đánh giá"** để chấm đúng phiếu.
4. Nạp **Claude API key thật** ở **Cấu hình AI** (nếu đang là placeholder).

---

## C. CÀI MỚI từ đầu (chỉ khi dựng trên một dự án GCP trắng)

```
# Lấy code
cd ~ && rm -rf nckh-deploy
git clone https://github.com/thoannv1976/NCKH-AI-ASSESS.git nckh-deploy
cd nckh-deploy

# Deploy toàn bộ (Firestore + GCS + Secret + Cloud Run + Scheduler). Mất 3-7 phút.
# Lưu ý: ANTHROPIC_API_KEY phải KHÁC RỖNG (Secret Manager không nhận payload rỗng).
PROJECT_ID="<project-id>" \
ORG_NAME="Trường Đại học Ngoại thương" ORG_SHORT="FTU" \
ADMIN_EMAIL="<admin@ftu.edu.vn>" \
SERVICE="nckh-assess" \
ANTHROPIC_API_KEY="<sk-ant-... hoặc chuỗi placeholder không rỗng>" \
bash deploy/deploy.sh
```
Script in ra khối **"CÀI ĐẶT HOÀN TẤT"**: URL hệ thống, tài khoản + mật khẩu quản trị (đổi ngay sau khi đăng nhập).

---

## D. Lưu ý & xử lý lỗi

- **`update.sh` không đụng** Firestore/bucket/secret → dữ liệu, người dùng, điểm được giữ nguyên.
- **Tên trường bị mất dấu** ("Trng i hc Ngoi thng"): do dán tiếng Việt vào terminal lỗi encoding. Cách sửa gọn nhất là **xóa biến `ORG_NAME`/`ORG_SHORT`** (bước 3 phần B) để app dùng mặc định đã ghi đúng trong code. Nếu cần tên tùy biến, ghi qua file để tránh lỗi:
  ```bash
  printf 'Trường Đại học Ngoại thương' > /tmp/org.txt
  gcloud run services update nckh-assess --region asia-southeast1 \
    --set-env-vars "ORG_NAME=$(cat /tmp/org.txt),ORG_SHORT=FTU"
  ```
- **Lỗi Secret Manager "payload rỗng"** khi cài mới: do `ANTHROPIC_API_KEY` để trống. Đưa một chuỗi placeholder không rỗng rồi chạy lại `deploy.sh`; nạp key thật trong app sau.
- **`update.sh` báo "chưa thấy dịch vụ"**: sai tên service. Liệt kê bằng `gcloud run services list --region asia-southeast1` rồi thay đúng vào `SERVICE=`.
- **Chi phí**: cấu hình `--min-instances 1 --no-cpu-throttling` (để chấm AI không bị ngắt) có tính phí; sau đợt dùng có thể hạ `--min-instances 0` để tiết kiệm.
- **Bảo mật**: không để Claude for Chrome dán API key/mật khẩu ra chat công khai, Google Doc chia sẻ hay commit lên GitHub.
