# THÔNG TIN DEPLOY — BẢN CHẠY CỦA DNU (ghi nhớ để không nhầm lẫn)

> Tài liệu vận hành riêng cho **bản đang chạy của Trường Đại học Đại Nam**.
> Đọc kỹ trước mỗi lần deploy code mới. (Trường khác cài mới xem `HUONG_DAN_CAI_DAT.md`.)

## 1. Thông số cố định của bản chạy

| Mục | Giá trị |
|---|---|
| Dịch vụ Cloud Run (SERVICE) | **`dnu-ai-assess`** |
| Vùng (REGION) | **`asia-southeast1`** |
| Project number | **`65018963525`** |
| Địa chỉ hệ thống | `https://dnu-ai-assess-65018963525.asia-southeast1.run.app` |
| URL tương đương (cùng 1 app) | `https://dnu-ai-assess-avppo6x4pa-as.a.run.app` |
| Mã nguồn | GitHub `thoannv1976/dnuai2`, nhánh **`claude/zen-franklin-kfnqp2`** |

> **Hai URL trên là CÙNG MỘT ứng dụng** (Cloud Run cấp 2 dạng URL). Nên dùng nhất
> quán URL dạng số dự án (`...-65018963525...`). Đăng nhập ở URL này không tự đăng
> nhập ở URL kia (cookie theo tên miền) — không phải 2 app khác nhau.

## 2. Quy tắc BẮT BUỘC khi deploy code mới (đây là CẬP NHẬT, không phải cài mới)

1. **Luôn dùng `deploy/update.sh`** — KHÔNG dùng `deploy/deploy.sh`.
   `update.sh` chỉ build lại mã nguồn và triển khai đè, **giữ nguyên** dữ liệu
   (Firestore, bucket), secret và biến môi trường.
2. **Luôn đặt `SERVICE=dnu-ai-assess`.** Script mặc định tên là `ai-assess` — nếu
   quên đặt, lệnh sẽ trỏ sang một dịch vụ khác (sai/không tồn tại).
3. **Lấy code nhánh `claude/zen-franklin-kfnqp2`** (bản mới nhất).

### KHÔNG được làm (gây mất dữ liệu / nhầm lẫn)
- ❌ **KHÔNG chạy `deploy.sh`** lên bản đang chạy — nó tạo secret theo tên mới
  (đổi `SECRET_KEY` → đăng xuất mọi người, đặt lại mật khẩu admin) và có thể tạo
  một dịch vụ `ai-assess` trùng lặp.
- ❌ KHÔNG tạo mới Firestore/bucket/secret, KHÔNG đổi biến môi trường.
- ❌ KHÔNG xóa hay “dọn” tài nguyên cũ.

## 3. Lệnh cập nhật chuẩn (Google Cloud Shell)

```bash
# 1) Xác định project và đặt project hiện hành
export PROJECT_ID="$(gcloud projects list --filter='projectNumber=65018963525' --format='value(projectId)')"
gcloud config set project "$PROJECT_ID"

# 2) Lấy mã nguồn mới nhất (nhánh claude/zen-franklin-kfnqp2)
REPO=~/dnuai2; BRANCH=claude/zen-franklin-kfnqp2
if [ -d "$REPO/.git" ]; then
  cd "$REPO" && git fetch origin && git checkout "$BRANCH" && git pull origin "$BRANCH"
else
  git clone -b "$BRANCH" https://github.com/thoannv1976/dnuai2.git "$REPO" && cd "$REPO"
fi
# (Nếu git đòi đăng nhập GitHub: chạy `gh auth login` một lần rồi làm lại.)

# 3) CẬP NHẬT — nhớ SERVICE=dnu-ai-assess
PROJECT_ID="$PROJECT_ID" SERVICE="dnu-ai-assess" REGION="asia-southeast1" bash deploy/update.sh
```

## 4. Sau khi deploy

```bash
# Đặt timeout dài cho gói tải lớn (chỉ cần chạy 1 lần, hoặc lặp lại sau nếu đổi lại)
gcloud run services update dnu-ai-assess --region asia-southeast1 --timeout 3600

# Kiểm tra
URL="$(gcloud run services describe dnu-ai-assess --region asia-southeast1 --format='value(status.url)')"
echo "$URL"; curl -sS "$URL/healthz"        # phải trả về {"ok": true}
gcloud run services logs read dnu-ai-assess --region asia-southeast1 --limit 30 | grep -iE "error|exception|traceback" || echo "OK, không thấy lỗi"
```

Trong app: đăng nhập Admin → **Cấu hình → Rubric**, nếu báo “có bản rubric mới hơn”
thì bấm **Nạp lại rubric mới nhất**.

## 5. Cài đặt MỚI (chỉ khi dựng lại từ đầu / cho trường khác)

Dùng `deploy/deploy.sh` với tham số riêng (xem `HUONG_DAN_CAI_DAT.md`). KHÔNG áp dụng
cho bản DNU đang chạy.

## 6. Ghi chú
- Khi nhánh `claude/zen-franklin-kfnqp2` được merge vào `main`, đổi `BRANCH=main`.
- Hạn nộp và mốc thời gian chỉnh trong app (Admin → Cấu hình), không sửa bằng deploy.
