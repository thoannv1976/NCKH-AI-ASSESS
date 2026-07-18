#!/usr/bin/env bash
# Đóng gói bộ cài bàn giao AI-Assess thành 1 file .zip (mã nguồn + tài liệu +
# script cài đặt/cập nhật). Dùng để bàn giao cho các trường.
# Chạy: bash scripts/build_bundle.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PRODUCT="AI-Assess"
VER_NUM="$(head -1 VERSION | awk '{print $NF}')"     # ví dụ 1.1.0
OUT_DIR="dist"
STAGE="${OUT_DIR}/${PRODUCT}-${VER_NUM}"
ZIP="${OUT_DIR}/${PRODUCT}-${VER_NUM}.zip"

rm -rf "$STAGE" "$ZIP"
mkdir -p "$STAGE"

# Sao chép các thành phần cần bàn giao (loại trừ tệp tạm/dữ liệu/môi trường)
for item in app rubrics scripts deploy docs tests \
            Dockerfile requirements.txt requirements-gcp.txt requirements-dev.txt \
            .env.example .gitignore README.md VERSION .github; do
  [ -e "$item" ] && cp -r "$item" "$STAGE/" || true
done

# Dọn rác trong bản sao
find "$STAGE" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type d -name '.ruff_cache' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$STAGE/data" "$STAGE/dist" 2>/dev/null || true
# Bảo đảm script cài đặt/cập nhật có quyền chạy
chmod +x "$STAGE"/deploy/*.sh "$STAGE"/scripts/*.sh 2>/dev/null || true

( cd "$OUT_DIR" && zip -rq "$(basename "$ZIP")" "${PRODUCT}-${VER_NUM}" )
rm -rf "$STAGE"
echo "Đã tạo bộ cài: $ZIP (phiên bản ${VER_NUM})"
ls -lh "$ZIP" | awk '{print $5, $9}'
