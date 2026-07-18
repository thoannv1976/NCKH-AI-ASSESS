#!/usr/bin/env bash
# =============================================================================
# AI-Assess — Cài đặt MỚI lên Google Cloud (Cloud Run + Firestore + GCS)
# =============================================================================
# Dựng toàn bộ hệ thống trên tài khoản Google Cloud của một Trường bằng 1 lệnh.
# Dùng cho NHIỀU trường: mỗi trường một dự án GCP (PROJECT_ID) riêng, đặt tên
# tổ chức (ORG_NAME/ORG_SHORT) để hiển thị đúng thương hiệu trường đó.
#
# Yêu cầu: chạy trong Google Cloud Shell (có sẵn gcloud, gsutil) hoặc máy đã cài
# Google Cloud SDK và đã `gcloud auth login`.
#
# Cách dùng tối thiểu:
#   PROJECT_ID=ten-du-an ORG_NAME="Trường Đại học X" ORG_SHORT="UX" \
#   ADMIN_EMAIL="admin@x.edu.vn" ANTHROPIC_API_KEY="sk-ant-..." bash deploy/deploy.sh
#
# Script idempotent: chạy lại nhiều lần không gây lỗi (bỏ qua tài nguyên đã có).
# Để CẬP NHẬT một bản đã cài (không đụng dữ liệu/secret), dùng deploy/update.sh.
# =============================================================================
set -euo pipefail

# ----------------------------- CẤU HÌNH ---------------------------------------
PROJECT_ID="${PROJECT_ID:-}"                        # BẮT BUỘC: mã dự án GCP của Trường
ORG_NAME="${ORG_NAME:-Trường Đại học Đại Nam}"      # Tên trường hiển thị trên giao diện/email
ORG_SHORT="${ORG_SHORT:-DNU}"                       # Tên viết tắt (dùng cho tiêu đề "X AI-Assess")
PROGRAM_YEAR="${PROGRAM_YEAR:-2026}"                # Năm chương trình
REGION="${REGION:-asia-southeast1}"                 # Vùng triển khai (Singapore)
SERVICE="${SERVICE:-ai-assess}"                     # Tên dịch vụ Cloud Run (cũng là tiền tố tài nguyên)
PREFIX="${PREFIX:-$SERVICE}"                         # Tiền tố cho secret/bucket/scheduler
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.edu.vn}"  # Email tài khoản quản trị đầu tiên
GRADING_MODEL="${GRADING_MODEL:-claude-opus-4-8}"   # Model AI dùng để chấm
BUCKET="${BUCKET:-${PROJECT_ID}-${PREFIX}}"         # Bucket lưu sản phẩm/minh chứng
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"          # Khóa Claude API (có thể nạp sau trong app)
DEADLINE="${DEADLINE:-2026-06-30T17:00:00+07:00}"   # Hạn nộp (admin sửa được trong app)
OPEN_AT="${OPEN_AT:-2026-06-25T00:00:00+07:00}"     # Mốc mở nộp
# Email (tùy chọn) — để gửi email thật; bỏ trống = chỉ ghi log trong app
SMTP_HOST="${SMTP_HOST:-}"; SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:-}"; SMTP_PASSWORD="${SMTP_PASSWORD:-}"
MAIL_FROM="${MAIL_FROM:-$SMTP_USER}"
# -----------------------------------------------------------------------------

c_green="\033[0;32m"; c_yellow="\033[1;33m"; c_red="\033[0;31m"; c_off="\033[0m"
say()  { echo -e "${c_green}==>${c_off} $*"; }
warn() { echo -e "${c_yellow}[!]${c_off} $*"; }
die()  { echo -e "${c_red}[LỖI]${c_off} $*" >&2; exit 1; }

[ -n "$PROJECT_ID" ] || die "Chưa đặt PROJECT_ID. Ví dụ: PROJECT_ID=truong-x bash deploy/deploy.sh"
command -v gcloud >/dev/null || die "Không tìm thấy gcloud. Hãy chạy trong Google Cloud Shell."
command -v gsutil >/dev/null || die "Không tìm thấy gsutil."
cd "$(dirname "$0")/.."
[ -f Dockerfile ] || die "Không thấy Dockerfile — hãy chạy script từ thư mục gốc bộ cài."

rand() { openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n'; }

say "Trường: $ORG_NAME ($ORG_SHORT) | Dự án: $PROJECT_ID | Vùng: $REGION | Dịch vụ: $SERVICE"
gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 1) Bật các API cần thiết --------------------------------------------------
say "Bật các API (Cloud Run, Build, Firestore, Storage, Secret Manager, Scheduler)..."
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com storage.googleapis.com secretmanager.googleapis.com \
  cloudscheduler.googleapis.com --quiet

# 2) Firestore (Native mode) ------------------------------------------------
if gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  say "Firestore đã tồn tại — bỏ qua."
else
  say "Tạo Firestore (Native mode) tại $REGION..."
  gcloud firestore databases create --location="$REGION" --quiet \
    || warn "Không tạo được Firestore tự động — hãy tạo thủ công (Native mode) rồi chạy lại."
fi

# 3) Bucket Cloud Storage ----------------------------------------------------
if gsutil ls -b "gs://${BUCKET}" >/dev/null 2>&1; then
  say "Bucket gs://${BUCKET} đã tồn tại — bỏ qua."
else
  say "Tạo bucket gs://${BUCKET}..."
  gsutil mb -l "$REGION" "gs://${BUCKET}"
fi

# 4) Secrets ----------------------------------------------------------------
ensure_secret() { # tên_secret  giá_trị
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    say "Secret $name đã tồn tại — giữ nguyên."
  else
    say "Tạo secret $name..."
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --quiet
  fi
}
set_secret() { # tên_secret  giá_trị  (luôn thêm phiên bản mới)
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --quiet
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --quiet
  fi
}
ADMIN_PW_VAL="${ADMIN_PASSWORD:-${ORG_SHORT}-$(head -c 6 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 8)@${PROGRAM_YEAR}}"
ensure_secret "${PREFIX}-secret-key" "$(rand)"
ensure_secret "${PREFIX}-cron-token" "$(rand)"
ensure_secret "${PREFIX}-admin-password" "$ADMIN_PW_VAL"
if [ -n "$ANTHROPIC_API_KEY" ]; then
  set_secret "${PREFIX}-anthropic-key" "$ANTHROPIC_API_KEY"
else
  ensure_secret "${PREFIX}-anthropic-key" ""   # placeholder; admin nạp key trong app sau
  warn "Chưa cung cấp ANTHROPIC_API_KEY — sẽ nạp trong app tại 'Cấu hình AI' sau khi cài."
fi
SECRETS="SECRET_KEY=${PREFIX}-secret-key:latest,CRON_TOKEN=${PREFIX}-cron-token:latest,ADMIN_PASSWORD=${PREFIX}-admin-password:latest,ANTHROPIC_API_KEY=${PREFIX}-anthropic-key:latest"
if [ -n "$SMTP_PASSWORD" ]; then
  set_secret "${PREFIX}-smtp-password" "$SMTP_PASSWORD"
  SECRETS="${SECRETS},SMTP_PASSWORD=${PREFIX}-smtp-password:latest"
fi

CRON_TOKEN_VAL="$(gcloud secrets versions access latest --secret="${PREFIX}-cron-token")"
ADMIN_PW_SHOWN="$(gcloud secrets versions access latest --secret="${PREFIX}-admin-password")"

# 5) Cấp quyền cho service account chạy Cloud Run ---------------------------
say "Cấp quyền cho service account $RUNTIME_SA..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/datastore.user" --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor" --quiet >/dev/null
gsutil iam ch "serviceAccount:${RUNTIME_SA}:roles/storage.objectAdmin" "gs://${BUCKET}" >/dev/null

# 6) Triển khai Cloud Run từ mã nguồn ---------------------------------------
# Dùng dấu phân tách tùy biến (^@@^) để ORG_NAME có dấu cách/đặc biệt không gây lỗi.
ENVV="^@@^APP_MODE=gcp@@GCS_BUCKET=${BUCKET}@@GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
ENVV="${ENVV}@@GRADING_MODEL=${GRADING_MODEL}@@ADMIN_EMAILS=${ADMIN_EMAIL}"
ENVV="${ENVV}@@DEADLINE=${DEADLINE}@@OPEN_AT=${OPEN_AT}"
ENVV="${ENVV}@@ORG_NAME=${ORG_NAME}@@ORG_SHORT=${ORG_SHORT}@@PROGRAM_YEAR=${PROGRAM_YEAR}"
if [ -n "$SMTP_HOST" ]; then
  ENVV="${ENVV}@@SMTP_HOST=${SMTP_HOST}@@SMTP_PORT=${SMTP_PORT}@@SMTP_USER=${SMTP_USER}@@MAIL_FROM=${MAIL_FROM}"
fi

say "Triển khai Cloud Run (build container + deploy, mất 3–7 phút)..."
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 1 --max-instances 10 --memory 1Gi --cpu 1 --timeout 3600 \
  --no-cpu-throttling \
  --set-env-vars "$ENVV" \
  --set-secrets "$SECRETS" \
  --quiet

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"

# 7) Cloud Scheduler: nhắc hạn 24h + khóa hồ sơ đúng hạn --------------------
say "Cấu hình Cloud Scheduler (chạy mỗi 30 phút)..."
SCHED_ARGS=(--schedule="*/30 * * * *" --uri="${URL}/tasks/cron" --http-method=POST
  --headers="X-Cron-Token=${CRON_TOKEN_VAL}" --time-zone="Asia/Ho_Chi_Minh" --location="$REGION" --quiet)
if gcloud scheduler jobs describe "${PREFIX}-cron" --location="$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "${PREFIX}-cron" "${SCHED_ARGS[@]}" >/dev/null || warn "Không cập nhật được Scheduler."
else
  gcloud scheduler jobs create http "${PREFIX}-cron" "${SCHED_ARGS[@]}" >/dev/null || warn "Không tạo được Scheduler (có thể tạo sau)."
fi

# 8) Hoàn tất ---------------------------------------------------------------
echo
say "CÀI ĐẶT HOÀN TẤT cho $ORG_NAME."
echo    "------------------------------------------------------------------"
echo -e "  Địa chỉ hệ thống : ${c_green}${URL}${c_off}"
echo    "  Tài khoản quản trị: ${ADMIN_EMAIL}"
echo -e "  Mật khẩu quản trị : ${c_yellow}${ADMIN_PW_SHOWN}${c_off}  (đổi ngay sau khi đăng nhập)"
echo    "------------------------------------------------------------------"
echo    "Bước tiếp theo:"
echo    "  1. Mở ${URL} và đăng nhập bằng tài khoản quản trị ở trên."
echo    "  2. Vào 'Cấu hình AI' nạp/kiểm tra Claude API key (nếu chưa đặt khi cài)."
echo    "  3. Vào 'Người dùng' → Import danh sách giảng viên (CSV mẫu trong docs/)."
echo    "  4. Kiểm tra mốc thời gian trong 'Cấu hình' (hạn nộp hiện tại: ${DEADLINE})."
echo    "  5. Lần cài đầu: vào 'Cấu hình' → 'Nạp lại rubric mới nhất' để chắc chắn dùng rubric mới nhất."
