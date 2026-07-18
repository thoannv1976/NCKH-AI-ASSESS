#!/usr/bin/env bash
# =============================================================================
# AI-Assess — CẬP NHẬT một bản đã cài (nâng cấp phần mềm, an toàn dữ liệu)
# =============================================================================
# Chỉ build lại mã nguồn mới và triển khai đè lên dịch vụ Cloud Run đang chạy.
# KHÔNG đụng tới Firestore, bucket, secret hay biến môi trường hiện có — vì vậy
# DỮ LIỆU (hồ sơ, điểm, người dùng, cấu hình) được giữ nguyên.
#
# Cách dùng (chạy từ thư mục gốc bộ cài bản MỚI):
#   PROJECT_ID=ten-du-an SERVICE=ai-assess bash deploy/update.sh
#
# Sau khi cập nhật, nếu có thay đổi rubric: đăng nhập Admin → Cấu hình →
# "Nạp lại rubric mới nhất từ phần mềm".
# =============================================================================
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
SERVICE="${SERVICE:-ai-assess}"
REGION="${REGION:-asia-southeast1}"

c_green="\033[0;32m"; c_yellow="\033[1;33m"; c_red="\033[0;31m"; c_off="\033[0m"
say()  { echo -e "${c_green}==>${c_off} $*"; }
warn() { echo -e "${c_yellow}[!]${c_off} $*"; }
die()  { echo -e "${c_red}[LỖI]${c_off} $*" >&2; exit 1; }

[ -n "$PROJECT_ID" ] || die "Chưa đặt PROJECT_ID. Ví dụ: PROJECT_ID=truong-x SERVICE=ai-assess bash deploy/update.sh"
command -v gcloud >/dev/null || die "Không tìm thấy gcloud. Hãy chạy trong Google Cloud Shell."
cd "$(dirname "$0")/.."
[ -f Dockerfile ] || die "Không thấy Dockerfile — hãy chạy script từ thư mục gốc bộ cài (bản mới)."

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud run services describe "$SERVICE" --region "$REGION" >/dev/null 2>&1 \
  || die "Chưa thấy dịch vụ '$SERVICE' tại $REGION. Đây là CÀI MỚI? Hãy dùng deploy/deploy.sh."

say "Cập nhật dịch vụ '$SERVICE' (dự án $PROJECT_ID, vùng $REGION)..."
warn "Giữ nguyên toàn bộ dữ liệu, biến môi trường và secret hiện có."
# Không truyền --set-env-vars/--set-secrets → Cloud Run giữ nguyên cấu hình cũ.
# --no-cpu-throttling: cấp CPU liên tục để tiến trình chấm nền chạy xong (tránh treo "đang chấm").
gcloud run deploy "$SERVICE" --source . --region "$REGION" --no-cpu-throttling --quiet

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
say "ĐÃ CẬP NHẬT XONG."
echo    "------------------------------------------------------------------"
echo -e "  Địa chỉ hệ thống : ${c_green}${URL}${c_off}"
echo    "------------------------------------------------------------------"
echo    "Khuyến nghị sau cập nhật:"
echo    "  • Đăng nhập Admin → Cấu hình: nếu báo 'có bản rubric mới hơn', bấm"
echo    "    'Nạp lại rubric mới nhất từ phần mềm'."
echo    "  • Kiểm tra nhanh: mở ${URL}/healthz (trả về {\"ok\": true})."
