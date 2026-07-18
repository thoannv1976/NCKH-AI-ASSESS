"""Tạo dữ liệu demo: người dùng 3 vai trò + 1 hồ sơ công trình mẫu (kèm tệp docx thật)
để demo trọn luồng nộp → khóa → chấm → thẩm định → công bố.

Chạy:  python scripts/seed_demo.py
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings, now_vn  # noqa: E402
from app.db import create_store, new_id  # noqa: E402
from app.rubric import get_rubric, graded_parts  # noqa: E402
from app.storage import create_storage  # noqa: E402

# Vai trò lecturer = chủ nhiệm/nhóm sinh viên; council = Hội đồng; admin = Phòng QLKH.
USERS = [
    {"ma_gv": "2211110001", "ho_ten": "Lê Khánh Linh", "email": "sv001@ftu.edu.vn",
     "khoa": "Viện Kinh tế & Kinh doanh quốc tế", "bo_mon": "Kinh tế đối ngoại",
     "chuc_vu": "Chủ nhiệm chuyên đề", "role": "lecturer"},
    {"ma_gv": "2211110045", "ho_ten": "Trần Minh Quân", "email": "sv002@ftu.edu.vn",
     "khoa": "Khoa Tài chính - Ngân hàng", "bo_mon": "Tài chính quốc tế",
     "chuc_vu": "Chủ nhiệm chuyên đề", "role": "lecturer"},
    {"ma_gv": "2211110088", "ho_ten": "Phạm Thu Hà", "email": "sv003@ftu.edu.vn",
     "khoa": "Khoa Quản trị kinh doanh", "bo_mon": "Marketing",
     "chuc_vu": "Chủ nhiệm chuyên đề", "role": "lecturer"},
    {"ma_gv": "HD001", "ho_ten": "TS. Nguyễn Bình Minh", "email": "hoidong@ftu.edu.vn",
     "khoa": "", "bo_mon": "", "chuc_vu": "Ủy viên phản biện Hội đồng", "role": "council"},
    {"ma_gv": "QLKH01", "ho_ten": "Phòng Quản lý Khoa học", "email": "admin@ftu.edu.vn",
     "khoa": "", "bo_mon": "", "chuc_vu": "Quản trị hệ thống", "role": "admin"},
]

# Nội dung mẫu theo phần của bộ tiêu chí "báo cáo nghiên cứu ứng dụng" (I, II).
SAMPLE_DOCS = {
    "I": ("BaoCaoTongKet", [
        "BÁO CÁO TỔNG KẾT: ỨNG DỤNG DỮ LIỆU LỚN TRONG DỰ BÁO NHU CẦU XUẤT KHẨU DỆT MAY VIỆT NAM",
        "1. Tổng quan tình hình nghiên cứu: tổng quan các nghiên cứu trong và ngoài nước về dự báo nhu cầu "
        "xuất khẩu; phân tích những tồn tại (thiếu mô hình kết hợp dữ liệu thời gian thực); lý do lựa chọn đề tài.",
        "2. Ý tưởng và cách tiếp cận: đề xuất mô hình kết hợp học máy và dữ liệu thương mại theo thời gian thực — "
        "có tính mới và ý nghĩa ứng dụng cho doanh nghiệp dệt may; cách tiếp cận liên ngành, sáng tạo.",
        "3. Mục tiêu nghiên cứu: xây dựng và kiểm định mô hình dự báo nhu cầu xuất khẩu theo quý, sai số < 10%.",
        "4. Phương pháp nghiên cứu: hồi quy chuỗi thời gian, random forest, kiểm định trên dữ liệu 2015–2025; "
        "trình bày rõ ràng, hiện đại, phù hợp nội dung.",
        "5. Kết quả nghiên cứu và khả năng ứng dụng: mô hình đạt MAPE 8.4%; bàn luận ý nghĩa; kết quả hoàn chỉnh "
        "giải quyết mục tiêu; đã triển khai thử tại 01 doanh nghiệp dệt may (có xác nhận ứng dụng).",
        "6. Hình thức trình bày: bố cục logic, đầy đủ theo quy định báo cáo tổng kết, trình bày sạch đẹp, ít lỗi.",
    ]),
    "II": ("SanPhamKhoaHoc", [
        "SẢN PHẨM KHOA HỌC VÀ ỨNG DỤNG KÈM THEO CÔNG TRÌNH",
        "1. Ứng dụng thực tiễn: Thỏa thuận hợp tác ba bên (Nhà trường – Công ty May X – nhóm sinh viên) mô tả rõ "
        "nội dung hợp tác, kinh phí tài trợ 20 triệu đồng, trách nhiệm và quyền lợi các bên.",
        "Giấy xác nhận ứng dụng của Công ty May X: mô tả chi tiết mô hình dự báo đã được sử dụng thử trong lập kế "
        "hoạch sản xuất quý IV/2025, đánh giá của lãnh đạo công ty; kèm email/biên bản làm việc và ảnh minh họa.",
        "2. Sản phẩm công bố: 01 bài đăng kỷ yếu hội thảo khoa học cấp Quốc gia, sinh viên là tác giả chính "
        "(đóng góp > 70%), nội dung phù hợp công trình, công bố trong thời gian thực hiện.",
    ]),
}


def make_docx(title: str, paragraphs: list[str]) -> bytes:
    import docx

    d = docx.Document()
    d.add_heading(title, level=1)
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def seed(store, storage) -> None:
    """Tạo người dùng demo + hồ sơ công trình mẫu trên store/storage cho trước (idempotent)."""
    get_rubric(store)

    from app.security import hash_password

    demo_pw = hash_password("demo123")  # mật khẩu demo dùng chung cho mọi tài khoản mẫu
    users_by_email = {}
    for u in USERS:
        existing = store.find_one("users", email=u["email"])
        if existing:
            if not existing.get("password_hash"):
                store.patch("users", existing["id"], {"password_hash": demo_pw, "active": True})
                print(f"~ backfill mật khẩu demo123 cho {u['email']}")
            users_by_email[u["email"]] = store.get("users", existing["id"])
            continue
        uid = store.add("users", {**u, "active": True, "password_hash": demo_pw})
        users_by_email[u["email"]] = store.get("users", uid)
        print(f"+ user {u['email']} ({u['role']}) — mật khẩu: demo123")

    # Hồ sơ công trình mẫu đầy đủ cho sinh viên chủ nhiệm đầu tiên
    owner = users_by_email["sv001@ftu.edu.vn"]
    if store.find_one("submissions", user_id=owner["id"]):
        print("Hồ sơ mẫu sv001 đã tồn tại — bỏ qua.")
        return
    sid = new_id()
    store.put("submissions", sid, {
        "id": sid, "user_id": owner["id"], "status": "submitted", "vong": "nghiem_thu",
        "part_a": {
            "ten_cong_trinh": "Ứng dụng dữ liệu lớn trong dự báo nhu cầu xuất khẩu dệt may Việt Nam",
            "loai": "bao_cao_ung_dung",
            "ho_ten": owner.get("ho_ten", ""), "ma_gv": owner.get("ma_gv", ""),
            "khoa_bo_mon": owner.get("khoa", ""),
            "thanh_vien": ["Nguyễn Văn A - 2211110002 - Anh 2 KTĐN",
                           "Trần Thị B - 2211110003 - Anh 2 KTĐN"],
            "gvhd": "PGS. TS. Vũ Hoàng Nam",
        },
        "created_at": now_vn().isoformat(), "submitted_at": now_vn().isoformat(),
    })
    rubric = get_rubric(store, "bao_cao_ung_dung")
    parts = graded_parts(rubric)
    for part in parts:
        name, paras = SAMPLE_DOCS[part]
        fname = f"{owner.get('ma_gv')}_Phan{part}_{name}.docx"
        key = f"{sid}/{part}/product/{int(time.time())}_{fname}"
        storage.save(key, io.BytesIO(make_docx(f"Phần {part}: {name}", paras)))
        store.add("submission_items", {
            "submission_id": sid, "part": part, "kind": "product", "type": "file",
            "storage_path": key, "original_name": fname,
            "size": 20000, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "uploaded_at": now_vn().isoformat(),
        })
    print(f"+ hồ sơ công trình mẫu sv001 ({sid}) với {len(parts)} phần (loại: nghiên cứu ứng dụng)")


def main() -> None:
    settings = get_settings()
    seed(create_store(settings), create_storage(settings))
    print("\nXong. Chạy: uvicorn app.main:app --reload  → http://localhost:8000 (đăng nhập tài khoản demo)")


if __name__ == "__main__":
    main()
