# DANH MỤC BÀN GIAO — AI-Assess

Bộ cài này là sản phẩm bàn giao phần mềm đánh giá năng lực ứng dụng AI của giảng viên. Cùng một bộ cài dùng để **cài mới** và **cập nhật** cho **nhiều trường** (mỗi trường một dự án GCP riêng). Khi bàn giao theo Hợp đồng (Phương án A), danh mục dưới đây tương ứng **Phụ lục 02 – Danh mục bàn giao**.

| # | Hạng mục | Thành phần trong bộ cài |
|---|---|---|
| 1 | Mã nguồn đầy đủ + hướng dẫn build/triển khai | `app/`, `rubrics/`, `scripts/`, `Dockerfile`, `requirements*.txt`; hướng dẫn: `docs/HUONG_DAN_CAI_DAT.md` |
| 2 | Hệ thống triển khai trên GCP của Trường | Cài mới: `deploy/deploy.sh`; cập nhật: `deploy/update.sh` (Cloud Run + Firestore + Storage + Secret Manager + Scheduler) |
| 3 | Bộ kiểm thử tự động + kết quả | `tests/` (~66 kiểm thử; chạy: `pytest -q`) |
| 4 | Tài liệu hướng dẫn | `docs/HUONG_DAN_SU_DUNG` (Word, có ảnh), `docs/HUONG_DAN_CAI_DAT.md`, `docs/HUONG_DAN_CHAY.md`; rubric & prompt chấm (xuất được từ app) |
| 5 | Biên bản tập huấn & nghiệm thu | Lập khi tập huấn/nghiệm thu (mẫu theo Hợp đồng) |

## Thành phần thư mục

```
AI-Assess-<phiên-bản>/
├── app/                     Mã nguồn ứng dụng (FastAPI): nộp hồ sơ, chấm AI, thẩm định, báo cáo, quản trị
├── rubrics/rubric.json      Rubric chấm điểm (4 mức)
├── deploy/deploy.sh         Cài đặt MỚI tự động lên Google Cloud (1 lệnh)
├── deploy/update.sh         CẬP NHẬT bản đã cài (an toàn dữ liệu)
├── scripts/                 Tiện ích: seed demo, sinh tài liệu, đóng gói, import
├── tests/                   Kiểm thử tự động
├── docs/                    Tài liệu: cài đặt, vận hành, sử dụng, danh mục bàn giao, CSV mẫu
├── Dockerfile               Đóng gói container cho Cloud Run
├── requirements*.txt        Thư viện (chạy / GCP / phát triển)
├── .env.example             Mẫu biến môi trường (gồm tên trường, SMTP)
└── VERSION                  Phiên bản phần mềm
```

## Cài đặt nhanh (mỗi trường)

Xem chi tiết tại `docs/HUONG_DAN_CAI_DAT.md`. Tóm tắt (trong Google Cloud Shell):

```bash
cd AI-Assess-*
export ANTHROPIC_API_KEY="sk-ant-..."
PROJECT_ID="<project-cua-truong>" ORG_NAME="Trường Đại học X" ORG_SHORT="UX" \
ADMIN_EMAIL="admin@x.edu.vn" bash deploy/deploy.sh
```

Cập nhật phiên bản (giữ nguyên dữ liệu):

```bash
PROJECT_ID="<project-cua-truong>" SERVICE="ai-assess" bash deploy/update.sh
```

## Đóng gói bộ cài (.zip để bàn giao)

```bash
bash scripts/build_bundle.sh        # tạo dist/AI-Assess-<phiên-bản>.zip
```

## Kiểm thử & chạy thử

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                       # chạy bộ kiểm thử
python scripts/seed_demo.py && uvicorn app.main:app --reload   # chạy thử cục bộ
```

## Nghiệm thu (tiêu chí theo Hợp đồng)

- Hệ thống chạy đúng chức năng Phần A–G.
- Chấm tự động bằng AI theo rubric (2 lượt + trung vị, trừ minh chứng).
- Phân quyền 3 vai trò (giảng viên / hội đồng / quản trị).
- Xuất báo cáo (bảng điểm, Excel, hồ sơ năng lực) và tải sản phẩm (ZIP).
- Bộ kiểm thử tự động chạy đạt (`pytest -q`).
