# KẾ HOẠCH XÂY DỰNG HỆ THỐNG DNU AI-ASSESS

**Hệ thống tiếp nhận hồ sơ và chấm điểm tự động bằng AI — Chương trình đánh giá năng lực ứng dụng AI của giảng viên Trường Đại học Đại Nam năm 2026**

| Thông tin | Nội dung |
|---|---|
| Căn cứ | Đề bài đánh giá năng lực ứng dụng AI dành cho giảng viên DNU 2026 (kèm Phụ lục mô tả phần mềm) |
| Ngày lập kế hoạch | 12/6/2026 |
| Hạn hệ thống phải sẵn sàng | **trước 22/6/2026** (ngày bắt đầu phổ biến đề bài) |
| Giai đoạn cao điểm nộp bài | 25/6 – 17h00 ngày 30/6/2026 |
| Giai đoạn chấm & thẩm định | 01/7 – 10/7/2026 (báo cáo toàn trường hạn 10/7) |

---

## 1. Mục tiêu và phạm vi

Xây dựng ứng dụng web **DNU AI-Assess** phục vụ trọn vòng đời đợt đánh giá:

1. **Tiếp nhận hồ sơ trực tuyến** theo cấu trúc Phần A–G (kê khai, tải sản phẩm + minh chứng, kiểm tra hợp lệ thời gian thực, nộp lại trước hạn).
2. **Chấm tự động bằng Claude API** theo đúng rubric trong đề bài: mỗi tiêu chí chấm 2 lượt độc lập, lệch >15% chấm lượt 3 và lấy trung vị; tự động đối chiếu danh mục minh chứng Phần G với minh chứng thực nộp.
3. **Thẩm định bởi Hội đồng**: xem điểm AI đề xuất + nhận xét, điều chỉnh, phê duyệt; ghi vết mọi thao tác (audit log); xử lý phản hồi của giảng viên trong 3 ngày làm việc.
4. **Báo cáo**: dashboard tiến độ theo khoa/bộ môn, phân loại 4 mức năng lực, xuất báo cáo toàn trường, Hồ sơ năng lực AI từng giảng viên (PDF), danh sách đề xuất giảng viên nòng cốt.
5. **Quản trị**: danh sách giảng viên, cấu hình rubric/trọng số/mốc thời gian, khởi động chấm, sao lưu dữ liệu.

**Ngoài phạm vi:** chấm điểm thủ công ngoài hệ thống, tích hợp LMS, app di động native (giao diện web responsive đáp ứng mobile).

---

## 2. Tóm tắt nghiệp vụ cốt lõi (từ đề bài)

### 2.1. Cấu trúc hồ sơ và thang điểm

| Phần | Nội dung | Điểm | Tiêu chí (điểm tối đa) |
|---|---|---|---|
| A | Thông tin chung — điều kiện hợp lệ | Đạt/Không đạt | Kê khai đủ trên hệ thống |
| B | Phát triển CTĐT và học phần | 20 | Đề cương cập nhật (8) · Đối sánh & cải tiến (6) · Khai thác AI (4) · Minh chứng (2) |
| C | Giảng dạy và hỗ trợ học tập | 40 | C1 Giáo án (10) · C2 Học liệu số (10) · C3 Trợ lý AI (10) · C4 Dạy học phân hóa (10) |
| D | Đánh giá người học | 10 | Ngân hàng câu hỏi (5) · Rubric + chấm thử (3) · Kiểm soát lạm dụng AI (2) |
| E | Nghiên cứu khoa học | 20 | Tổng quan tài liệu (10) · Đề cương NC (8) · Khai thác AI phản biện (2) · *Thưởng tối đa +2, trần 20* |
| F | Phục vụ cộng đồng, DN, chia sẻ tri thức | 5 | Giá trị thực tiễn (3) · Mức độ ứng dụng AI + minh chứng (2) |
| G | Bài học kinh nghiệm + danh mục minh chứng | 5 | Báo cáo kinh nghiệm (3) · Danh mục minh chứng (2) |
| | **Tổng** | **100** | |

### 2.2. Phân loại năng lực (tự động sau khi Hội đồng phê duyệt)

| Mức | Điểm | Sử dụng kết quả |
|---|---|---|
| Dẫn dắt (nòng cốt) | 85–100 | Đội ngũ nòng cốt AI — **bắt buộc thẩm định bởi con người** |
| Thành thạo | 70–84 | Mở rộng ứng dụng, bồi dưỡng nâng cao |
| Cơ bản | 50–69 | Bồi dưỡng trọng tâm theo nhóm kỹ năng thiếu |
| Khởi đầu | < 50 | Đào tạo nền tảng, nòng cốt hỗ trợ trực tiếp |

### 2.3. Quy tắc nghiệp vụ quan trọng

- **Hạn nộp cứng:** khóa hồ sơ lúc **17h00 ngày 30/6/2026** (giờ Việt Nam); sau hạn hệ thống không tiếp nhận.
- **Nộp nhiều lần** trước hạn; chỉ chấm **bản nộp cuối cùng**.
- **Định dạng tệp:** docx, pdf, pptx, xlsx, mp4 — tối đa **200MB/tệp**; chấp nhận liên kết (chatbot, video, hội thoại AI) ở chế độ truy cập được.
- **Quy ước tên tệp:** `MãGV_TênPhần_TênSảnPhẩm` (hệ thống kiểm tra và cảnh báo).
- **Thiếu minh chứng AI** ở sản phẩm nào → trừ **tối đa 50%** điểm của tiêu chí liên quan.
- **Email tự động:** xác nhận nộp thành công; nhắc mục còn thiếu **trước hạn 24 giờ**; trả kết quả kèm nhận xét chi tiết.
- **Phản hồi kết quả:** trong **3 ngày làm việc** từ ngày công bố; Hội đồng xem xét trên hệ thống.
- **Điểm AI chỉ có giá trị đề xuất** — điểm cuối cùng do Hội đồng phê duyệt.
- **Thẩm định bắt buộc bởi con người:** hồ sơ điểm cao (đề xuất nòng cốt, ≥85) và hồ sơ có dấu hiệu bất thường về minh chứng.

---

## 3. Kiến trúc hệ thống và công nghệ

### 3.1. Sơ đồ tổng thể

```
                ┌────────────────────────────────────────────────────────┐
                │                    Google Cloud Run                     │
   Giảng viên   │  ┌──────────────────────────────────────────────────┐  │
   Hội đồng   ──┼─▶│           Ứng dụng FastAPI (1 container)          │  │
   Quản trị     │  │  • Giao diện web Jinja2 + Tailwind (tiếng Việt)   │  │
                │  │  • REST API nội bộ  • Worker chấm điểm (async)    │  │
      ▲         │  └───────┬──────────────┬──────────────┬────────────┘  │
      │ SSO     └──────────┼──────────────┼──────────────┼───────────────┘
      │                    │              │              │
┌─────┴──────┐    ┌────────▼─────┐ ┌──────▼──────┐ ┌─────▼─────────────┐
│  Google    │    │  Firestore   │ │Cloud Storage│ │    Claude API     │
│ Workspace  │    │ (hồ sơ, điểm,│ │(tệp sản phẩm│ │ (chấm theo rubric,│
│ SSO (DNU)  │    │ audit, cấu   │ │+ minh chứng,│ │ structured output,│
└────────────┘    │   hình)      │ │ signed URL) │ │   Batches API)    │
                  └──────────────┘ └─────────────┘ └───────────────────┘
                         ▲
              ┌──────────┴──────────┐      ┌─────────────────────┐
              │   Cloud Scheduler   │      │  Dịch vụ Email SMTP │
              │ (khóa hạn, nhắc 24h)│      │ (xác nhận/nhắc/KQ)  │
              └─────────────────────┘      └─────────────────────┘
```

### 3.2. Lựa chọn công nghệ (bám Phụ lục đề bài)

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Backend | **Python 3.12 + FastAPI** | Đề bài cho phép FastAPI/Node.js; chọn Python vì hệ sinh thái trích xuất tài liệu mạnh (`python-docx`, `pypdf`, `python-pptx`, `openpyxl`), SDK `anthropic` chính thức, xuất PDF tốt |
| Frontend | **Jinja2 (server-render) + TailwindCSS + Alpine.js + Chart.js** | Responsive, tiếng Việt, 1 container duy nhất — đơn giản hóa triển khai Cloud Run, không cần build SPA riêng |
| CSDL | **Firestore** (production) / **SQLite** (chế độ dev cục bộ) | Theo đề bài; tầng truy cập dữ liệu trừu tượng hóa (repository pattern) để chạy demo không cần GCP |
| Lưu tệp | **Google Cloud Storage** (production) / thư mục cục bộ (dev) | Theo đề bài; upload trực tiếp bằng **signed URL** |
| Chấm AI | **Claude API — model mặc định `claude-opus-4-8`** (cấu hình được qua biến môi trường) | Model Opus mới nhất, chất lượng chấm + nhận xét tiếng Việt tốt; dùng **structured outputs** (JSON schema) để điểm luôn đúng định dạng; **Message Batches API** giảm 50% chi phí khi chấm hàng loạt |
| Xác thực | **Đăng nhập Google (OAuth 2.0)** giới hạn domain email DNU + chế độ đăng nhập giả lập khi dev | Theo đề bài (Google Workspace SSO); phân quyền 3 vai trò |
| Email | SMTP (tài khoản Google Workspace) qua tầng trừu tượng `EmailSender`; dev mode ghi log | Xác nhận nộp, nhắc hạn, trả kết quả |
| Lập lịch | **Cloud Scheduler** gọi endpoint `/tasks/*` (xác thực OIDC) | Nhắc hạn 24h, khóa hồ sơ đúng 17h00 30/6 |
| Xuất PDF | **WeasyPrint** (HTML → PDF, nhúng font Noto Sans hỗ trợ tiếng Việt) | Hồ sơ năng lực AI từng giảng viên |
| Triển khai | **Docker + Google Cloud Run** (autoscaling) | Theo đề bài; chịu tải cao điểm 25–30/6 |

### 3.3. Hai chế độ chạy (quyết định kiến trúc quan trọng)

Toàn bộ tầng hạ tầng đi qua interface trừu tượng, chọn bằng biến môi trường `APP_MODE`:

| | `APP_MODE=local` (dev/demo) | `APP_MODE=gcp` (production) |
|---|---|---|
| CSDL | SQLite (file) | Firestore |
| Tệp | Thư mục `./data/uploads` | GCS + signed URL |
| Đăng nhập | Form giả lập chọn vai trò | Google SSO, lọc domain DNU |
| Email | In ra log / hộp thư giả | SMTP thật |
| Chấm AI | Claude API thật (hoặc mock khi chạy test) | Claude API (Batches) |

→ Cho phép phát triển, demo và kiểm thử đầy đủ chức năng mà không cần hạ tầng GCP; chuyển production chỉ đổi cấu hình.

### 3.4. Lưu ý kỹ thuật then chốt

- **Upload 200MB trên Cloud Run:** Cloud Run giới hạn request ~32MB, nên tệp **không đi qua server**. Luồng: client xin *signed URL* → upload thẳng lên GCS (resumable) → báo server xác nhận metadata. Ở chế độ local thì upload trực tiếp vào ổ đĩa.
- **Múi giờ:** mọi mốc thời gian xử lý theo `Asia/Ho_Chi_Minh`; khóa hạn kiểm tra phía server (không tin client).
- **Chấm điểm chạy nền có checkpoint:** trạng thái từng lượt chấm lưu Firestore — quá trình chấm có thể dừng/chạy lại không mất dữ liệu, không chấm trùng.
- **Claude API:** dùng **structured outputs** (`output_config.format` / `messages.parse()` với Pydantic) để kết quả chấm luôn là JSON hợp lệ theo schema rubric; **prompt caching** cho phần rubric + hướng dẫn chấm dùng chung; **Batches API** cho 2 lượt chấm đầu (không nhạy độ trễ, giảm 50% chi phí), lượt 3 (trọng tài) gọi trực tiếp.

---

## 4. Mô hình dữ liệu (Firestore collections)

```
users                 # giảng viên, hội đồng, quản trị
  {uid}: email, ho_ten, ma_gv, khoa, bo_mon, role(lecturer|council|admin), active

submissions           # 1 hồ sơ / giảng viên
  {sid}: user_id, status(draft|submitted|locked|grading|graded|approved|published),
         part_a{ho_ten, ma_gv, khoa_bo_mon, hoc_phan, cong_cu_ai[], muc_thanh_thao(1-5)},
         submitted_at, locked_at, valid(bool), validation_notes[]

submission_items      # sản phẩm & minh chứng từng phần
  {iid}: submission_id, part(B..G), kind(product|evidence), type(file|link),
         storage_path|url, original_name, size, content_type, uploaded_at, replaced(bool)

grading_runs          # từng lượt chấm AI (bất biến — phục vụ kiểm chứng)
  {rid}: submission_id, part, pass_no(1|2|3), model, batch_id?, criteria[{id, score, comment}],
         evidence_penalty_applied, raw_request_hash, created_at, status

scores                # điểm hợp nhất theo tiêu chí
  {sid_part_crit}: submission_id, part, criterion_id, max_score,
                   ai_score(median/mean), ai_comment, needs_third_pass(bool),
                   council_score?, council_comment?, final_score, adjusted_by?, adjusted_at?

reviews               # phê duyệt cấp hồ sơ của Hội đồng
  {sid}: reviewer_ids[], mandatory(bool, lý do), status(pending|in_review|approved),
         approved_at, total_final, classification(dan_dat|thanh_thao|co_ban|khoi_dau)

appeals               # phản hồi kết quả của giảng viên (3 ngày làm việc)
  {aid}: submission_id, content, created_at, status(open|resolved), resolution, resolved_by

audit_logs            # append-only, ghi vết mọi thao tác chấm/điều chỉnh/phê duyệt
  {lid}: actor, role, action, target, before, after, ip, ts

config                # rubric (tiêu chí + điểm tối đa + mô tả mức chất lượng), trọng số,
                      # mốc thời gian (mở nộp, khóa, công bố), model AI, ngưỡng lệch 15%
email_logs            # nhật ký gửi email (xác nhận, nhắc hạn, kết quả)
```

---

## 5. Thiết kế chức năng theo 5 phân hệ

### 5.1. Phân hệ nộp hồ sơ (giảng viên)

- Đăng nhập email DNU → trang tổng quan hồ sơ: thanh tiến độ A–G, đếm ngược hạn nộp.
- **Phần A:** form kê khai (họ tên, mã GV, khoa/bộ môn, học phần 2026–2027, danh mục công cụ AI, tự đánh giá thang 5 mức) — điều kiện hợp lệ.
- **Phần B–G:** mỗi phần một trang: danh sách sản phẩm yêu cầu, upload tệp/dán liên kết cho **sản phẩm** và **minh chứng** riêng biệt; kiểm tra thời gian thực: định dạng, dung lượng ≤200MB, quy ước tên tệp, link truy cập được (HTTP check); cảnh báo mục còn thiếu.
- Nộp lại không giới hạn trước hạn (bản mới thay bản cũ, có lịch sử); nút **"Nộp hồ sơ"** → email xác nhận tự động.
- Sau công bố: xem điểm thành phần + nhận xét từng tiêu chí; gửi **phản hồi** trong 3 ngày làm việc.

### 5.2. Phân hệ chấm tự động (chi tiết tại mục 6)

### 5.3. Phân hệ thẩm định (Hội đồng)

- Danh sách hồ sơ: lọc theo khoa, trạng thái, điểm AI; **hàng đợi thẩm định bắt buộc** (≥85 điểm hoặc cờ minh chứng bất thường) hiển thị nổi bật.
- Trang chấm chi tiết: xem song song sản phẩm (preview/tải về) — điểm AI từng tiêu chí + nhận xét + chênh lệch giữa các lượt chấm; điều chỉnh điểm/nhận xét (bắt buộc ghi lý do) → audit log; phê duyệt từng hồ sơ.
- Xử lý phản hồi của giảng viên: xem, trả lời, điều chỉnh nếu chấp nhận → ghi vết.
- Điểm cuối cùng = điểm Hội đồng phê duyệt.

### 5.4. Phân hệ báo cáo

- **Dashboard:** tiến độ nộp theo khoa/bộ môn (realtime), tỷ lệ hồ sơ hợp lệ, tiến độ chấm/thẩm định, phân bố điểm, phân bố 4 mức năng lực.
- **Xuất:** báo cáo tổng hợp toàn trường (xlsx + pdf, hạn 10/7) · Hồ sơ năng lực AI từng giảng viên (PDF: điểm từng phần, nhận xét, mức phân loại, định hướng bồi dưỡng) · danh sách đề xuất giảng viên nòng cốt.
- Gửi email kết quả + nhận xét chi tiết đến từng giảng viên sau khi công bố.

### 5.5. Phân hệ quản trị

- Quản lý giảng viên: import từ Excel/CSV (mã GV, email, khoa/bộ môn), gán vai trò Hội đồng.
- Cấu hình: rubric (tiêu chí, điểm tối đa, mô tả mức chất lượng dùng trong prompt chấm), trọng số, mốc thời gian, model AI, ngưỡng chênh lệch.
- Vận hành chấm: nút "Khóa hồ sơ & kiểm tra hợp lệ" (Bước 1), "Bắt đầu chấm" (Bước 2–3), màn hình giám sát tiến trình (số hồ sơ đã chấm, lỗi, retry).
- Sao lưu: xuất toàn bộ dữ liệu + nhật ký (zip lên GCS theo lịch hằng ngày).

---

## 6. Thiết kế engine chấm tự động bằng Claude API

Bám đúng "Quy trình chấm tự động" 5 bước của đề bài:

```
Bước 1  Khóa hồ sơ (17h00 30/6, Cloud Scheduler) → kiểm tra hợp lệ
        (đủ Phần A, đủ sản phẩm + minh chứng từng phần) → đánh dấu valid/invalid
Bước 2  Trích xuất nội dung:
        docx → python-docx · pdf → pypdf (hoặc gửi PDF trực tiếp dạng document block)
        pptx → python-pptx · xlsx → openpyxl · mp4 → metadata + người chấm xem link
        link → tải snapshot HTML/ảnh chụp, lưu GCS làm căn cứ chấm
Bước 3  Chấm bằng Claude:
        for each (hồ sơ, phần B..G):
          prompt = [system: vai trò giám khảo + rubric phần đó (cache)]
                   + [nội dung sản phẩm + minh chứng + thông tin học phần Phần A]
          → Lượt 1 + Lượt 2: 2 request độc lập qua Batches API
          → so từng tiêu chí: nếu |s1 − s2| > 15% × điểm_tối_đa
               → Lượt 3 (gọi trực tiếp) → điểm tiêu chí = trung vị(s1, s2, s3)
            ngược lại → điểm = trung bình(s1, s2)
        + kiểm tra minh chứng: thiếu/không kiểm chứng được → trừ ≤50% tiêu chí liên quan
        + Phần G: đối chiếu tự động danh mục minh chứng kê khai vs. minh chứng thực nộp
        + Phần E: cộng điểm thưởng ≤2, trần 20
        + sinh cờ "bất thường minh chứng" (link chết, minh chứng không khớp, nghi sao chép)
Bước 4  Hội đồng thẩm định (01/7–10/7): bắt buộc với hồ sơ ≥85 hoặc có cờ bất thường
Bước 5  Tổng hợp điểm → phân loại 4 mức → sinh báo cáo + email kết quả từng giảng viên
```

**Định dạng kết quả chấm (structured output — JSON schema bắt buộc):**

```json
{
  "part": "B",
  "criteria": [
    {"id": "B1", "score": 6.5, "max": 8,
     "comment": "CLO viết rõ, đo lường được; ma trận CLO-PLO đầy đủ nhưng...",
     "evidence_ok": true}
  ],
  "evidence_findings": "Nhật ký prompt đầy đủ cho 2 nhiệm vụ...",
  "anomaly_flags": []
}
```

**Độ tin cậy & chi phí:**

- Mỗi tiêu chí có *mô tả thang mức chất lượng* trong prompt để 2 lượt chấm hội tụ.
- Prompt caching: system prompt + rubric mỗi phần dùng chung toàn bộ hồ sơ → tiết kiệm lớn.
- Batches API (lượt 1, 2): −50% chi phí; cửa sổ chấm 10 ngày nên độ trễ batch (≤24h) chấp nhận được.
- Ước lượng: ~300 GV × 6 phần × 2,2 lượt ≈ **4.000 request**, mỗi request vào ~15–30K token (sản phẩm) + ra ~1,5K token → nằm thoải mái trong cửa sổ 01–10/7; có retry/backoff và resume theo checkpoint.
- Khi chạy test tự động: dùng mock Claude client (không tốn phí, kết quả cố định).

---

## 7. Phân quyền và bảo mật

| Vai trò | Quyền |
|---|---|
| Giảng viên | Chỉ hồ sơ của mình: kê khai, nộp, xem điểm + nhận xét sau công bố, gửi phản hồi |
| Hội đồng | Xem mọi hồ sơ + điểm AI, điều chỉnh, phê duyệt, xử lý phản hồi |
| Quản trị | Toàn quyền cấu hình + vận hành; không sửa điểm trực tiếp (tách vai trò) |

- HTTPS toàn bộ (Cloud Run mặc định); Firestore/GCS mã hóa at-rest; signed URL có hạn dùng.
- Session cookie ký (HttpOnly, Secure); CSRF token cho form; kiểm tra quyền ở từng route.
- **Audit log append-only** cho mọi thao tác chấm, sửa điểm, phê duyệt, xuất dữ liệu.
- Giảng viên không xem được hồ sơ người khác; mọi truy cập tệp đi qua kiểm tra quyền.

---

## 8. Cấu trúc mã nguồn dự kiến

```
dnuai2/
├── app/
│   ├── main.py               # FastAPI app, mount routers + static
│   ├── config.py             # cấu hình theo APP_MODE, mốc thời gian, model AI
│   ├── auth/                 # Google SSO + dev login, session, RBAC
│   ├── models/               # Pydantic schemas (hồ sơ, điểm, rubric, audit)
│   ├── db/                   # repository interface + SQLite impl + Firestore impl
│   ├── storage/              # storage interface + local impl + GCS signed URL impl
│   ├── routers/              # lecturer.py, council.py, admin.py, reports.py, tasks.py
│   ├── services/
│   │   ├── validation.py     # hợp lệ hồ sơ, tên tệp, định dạng, link check
│   │   ├── extraction.py     # docx/pdf/pptx/xlsx → text; snapshot link
│   │   ├── grading/          # prompts.py, engine.py (2-pass+median), batch.py, evidence.py
│   │   ├── classify.py       # phân loại 4 mức, danh sách nòng cốt
│   │   ├── emailer.py        # template tiếng Việt: xác nhận/nhắc/kết quả
│   │   └── pdf_export.py     # hồ sơ năng lực PDF, báo cáo toàn trường
│   ├── templates/            # Jinja2 (base, lecturer/, council/, admin/, reports/)
│   └── static/               # css (tailwind build), js (alpine), logo DNU
├── rubrics/                  # rubric.json — toàn bộ tiêu chí B–G theo đề bài (seed)
├── scripts/                  # seed dữ liệu mẫu, import GV, chạy chấm thủ công
├── tests/                    # pytest: validation, engine chấm (mock AI), phân quyền, e2e
├── Dockerfile  ·  docker-compose.yml (dev)  ·  requirements.txt
├── .github/workflows/ci.yml  # lint + test
└── docs/                     # kế hoạch này, hướng dẫn triển khai, hướng dẫn sử dụng
```

---

## 9. Lộ trình thực hiện

Phát triển bằng Claude Code (agentic coding) theo đúng Phụ lục. Lịch bám mốc thực tế (hôm nay 12/6 → go-live 22/6):

| GĐ | Thời gian | Nội dung | Sản phẩm bàn giao / tiêu chí nghiệm thu |
|---|---|---|---|
| 0 | 12/6 | Khung dự án | Skeleton FastAPI + Docker + CI chạy xanh; cấu hình 2 chế độ; layout giao diện tiếng Việt; đăng nhập dev-mode 3 vai trò |
| 1 | 13–14/6 | Phân hệ nộp hồ sơ | Form Phần A; upload/link sản phẩm + minh chứng B–G; validate realtime (định dạng/200MB/tên tệp); nộp lại; khóa theo giờ hạn; email xác nhận (log); rubric.json seed đúng đề bài |
| 2 | 15–16/6 | Engine chấm AI | Trích xuất docx/pdf/pptx/xlsx; prompt + structured output từng phần B–G; 2 lượt + lượt 3 trung vị; trừ điểm thiếu minh chứng; đối chiếu Phần G; cờ bất thường; checkpoint/resume; test với hồ sơ mẫu + mock |
| 3 | 17/6 | Phân hệ thẩm định | UI Hội đồng (danh sách, chi tiết, điều chỉnh + lý do, phê duyệt); hàng đợi bắt buộc; audit log; luồng phản hồi 3 ngày |
| 4 | 18/6 | Báo cáo | Dashboard tiến độ + phân loại; xuất xlsx/PDF toàn trường; Hồ sơ năng lực PDF; danh sách nòng cốt; email kết quả |
| 5 | 19/6 | Quản trị + tự động hóa | Import GV; cấu hình rubric/mốc thời gian; màn hình vận hành chấm; endpoint Cloud Scheduler (nhắc 24h, khóa hạn); sao lưu |
| 6 | 20–21/6 | Production & kiểm thử | Google SSO; Firestore + GCS signed URL; deploy Cloud Run; test tải upload đồng thời; test e2e bằng bộ hồ sơ mẫu; rà soát bảo mật; tài liệu vận hành |
| — | 22/6 | **Go-live** | Bàn giao kèm hướng dẫn sử dụng cho GV/Hội đồng/quản trị |

Trong vận hành: trực hỗ trợ cao điểm 25–30/6; chạy chấm 01/7; hỗ trợ thẩm định đến 10/7.

---

## 10. Triển khai và vận hành

- **Build & deploy:** `gcloud run deploy dnu-ai-assess --source .` (Cloud Build); min-instances=1 trong giai đoạn 25/6–10/7 (tránh cold start), max-instances tự co giãn; CPU 1, RAM 1–2GB.
- **Biến môi trường chính:** `APP_MODE=gcp`, `ANTHROPIC_API_KEY` (Secret Manager), `GRADING_MODEL=claude-opus-4-8`, `GCS_BUCKET`, `GOOGLE_OAUTH_CLIENT_ID/SECRET`, `SMTP_*`, `DEADLINE=2026-06-30T17:00:00+07:00`.
- **Cloud Scheduler:** `*/30 * * * *` kiểm tra mốc nhắc hạn/khóa hồ sơ → POST `/tasks/cron` (OIDC).
- **Giám sát:** Cloud Logging + trang `/admin/health`; cảnh báo lỗi chấm qua email quản trị.
- **Sao lưu:** export Firestore + đồng bộ bucket hằng ngày 0h, giữ 30 ngày.

## 11. Kiểm thử

- **Unit:** validation tệp/tên/hạn, tính trung vị & ngưỡng 15%, trừ điểm minh chứng, phân loại 4 mức, RBAC.
- **Tích hợp:** luồng nộp → khóa → chấm (mock Claude) → thẩm định → công bố → phản hồi.
- **Bộ hồ sơ mẫu:** 5 hồ sơ giả lập (đủ/thiếu minh chứng/điểm cao/link hỏng/nộp muộn) — vừa test vừa demo.
- **Chấm thật thí điểm:** chạy Claude API thật trên 2–3 hồ sơ mẫu để hiệu chỉnh prompt rubric trước go-live.
- **Tải:** mô phỏng 100 GV nộp đồng thời tối 30/6 (signed URL không qua server nên chủ yếu test Firestore writes).

## 12. Rủi ro chính và phương án

| Rủi ro | Mức | Phương án |
|---|---|---|
| Nghẽn giờ chót 30/6 (upload lớn đồng thời) | Cao | Signed URL upload thẳng GCS; autoscaling; min-instances; khuyến cáo nộp sớm + email nhắc 24h |
| Rate limit / chi phí Claude API khi chấm | TB | Batches API + prompt caching; chấm rải trong 01–05/7; retry backoff; checkpoint resume; theo dõi usage |
| AI chấm lệch/thiếu nhất quán | TB | Rubric mô tả mức chất lượng chi tiết; 2 lượt + trung vị theo đúng đề bài; Hội đồng quyết định cuối |
| Link minh chứng không truy cập được | TB | Kiểm tra link lúc nộp + cảnh báo GV; snapshot lưu căn cứ; thiếu → trừ ≤50% theo quy định |
| Tệp phức tạp trích xuất kém (scan, ảnh) | TB | PDF gửi trực tiếp document block cho Claude (đọc được ảnh/scan); ghi chú để Hội đồng xem bản gốc |
| SSO/quyền cấu hình sai | Thấp | Dev-mode tách biệt; test phân quyền tự động; rà soát trước go-live |
| Trượt tiến độ trước 22/6 | TB | Ưu tiên P0 = nộp hồ sơ + chấm + thẩm định; báo cáo/quản trị có thể hoàn thiện song song 23–24/6 |

---

## 13. Việc cần phía DNU cung cấp (trước 20/6)

1. Google Cloud project + quyền triển khai (Cloud Run, Firestore, GCS, Scheduler, Secret Manager).
2. `ANTHROPIC_API_KEY` (khuyến nghị nâng tier đủ cho ~4.000 request chấm).
3. OAuth Client (Google Workspace) + domain email DNU; tài khoản SMTP gửi thông báo.
4. Danh sách giảng viên cơ hữu (mã GV, họ tên, email, khoa/bộ môn) dạng Excel.
5. Danh sách thành viên Hội đồng + quản trị viên; logo/định dạng nhận diện DNU cho giao diện và PDF.

---

*Kế hoạch này là tài liệu sống — cập nhật khi có quyết định mới trong quá trình xây dựng.*
