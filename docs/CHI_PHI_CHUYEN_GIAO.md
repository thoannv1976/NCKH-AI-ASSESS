# DỰ TOÁN CHI PHÍ CHUYỂN GIAO PHẦN MỀM DNU AI-ASSESS

*Tài liệu tham khảo phục vụ đàm phán — số liệu vận hành tính từ đo đạc thực tế của hệ thống; phí chuyển giao là khung giá thị trường, có thể điều chỉnh theo phạm vi và hình thức hợp đồng. Tỷ giá quy đổi tạm tính: 1 USD ≈ 25.500đ.*

---

## 0. Tóm tắt khuyến nghị

| Khoản | Hình thức | Khoảng giá | Khuyến nghị |
|---|---|---|---|
| **Phí chuyển giao phần mềm** (bản hiện tại, pilot-ready) | Một lần | 60–110 triệu | **~85 triệu** |
| Triển khai + cấu hình trên hạ tầng DNU | Một lần | 10–20 triệu | **~15 triệu** |
| Đào tạo + tài liệu + bảo hành 6 tháng | Một lần (kèm theo) | 8–15 triệu | **~10 triệu** |
| **Cộng gói chuyển giao** | | **78–145 triệu** | **~110 triệu** |
| Chi phí vận hành 1 đợt 500 GV (AI + cloud) | DNU tự trả (pass-through) | 25–45 triệu | **~32 triệu** |
| Bảo trì/hỗ trợ năm tiếp theo (tùy chọn) | Hằng năm | 15–20%/năm | **~18 triệu/năm** |

> **Điểm mấu chốt:** app đã hỗ trợ DNU **tự nạp API key của trường** và chạy trên **tài khoản Google Cloud của trường**, nên chi phí AI + cloud được tính **trực tiếp vào tài khoản DNU** (pass-through), không phải khoản bên cung cấp "thu". Bên cung cấp chỉ thu: **phí chuyển giao + triển khai + đào tạo + (tùy chọn) bảo trì**.

---

## 1. Chi phí vận hành 1 đợt đánh giá (500 giảng viên)

Tính từ số liệu đo thực tế trong hệ thống (trang *Chi phí AI*): mỗi hồ sơ chấm AI tốn **~13 lượt gọi ≈ 2,05 USD** (model `claude-opus-4-8`, chấm 6 phần × 2 lượt + lượt 3 khi lệch >15%).

### 1.1. Chi phí AI (Claude API) — khoản lớn nhất

| Hạng mục | Cách tính | Thành tiền |
|---|---|---|
| Chấm 1 hồ sơ (1 vòng) | ~13 lượt × ~0,158 USD ≈ **2 USD/hồ sơ** (~51.000đ) | — |
| Chấm 500 hồ sơ (1 vòng) | 500 × 2 USD = **1.000 USD** | **~25,5 triệu** |
| Dự phòng chấm lại/chấm thử (+20%) | | **~5 triệu** |
| **Cộng AI (chưa tối ưu)** | | **~30 triệu** |
| *Nếu bật prompt caching + Batches API (−40–50%)* | | *~15–18 triệu* |

- Khoảng dao động theo độ "nặng" của bài (slide nhiều, tài liệu dài): **40.000–70.000đ/giảng viên**.
- Có thể giảm mạnh nếu triển khai **Batches API** (−50% giá) và **prompt caching** rubric dùng chung.

### 1.2. Chi phí Google Cloud (1 đợt ~1,5–2 tháng cao điểm)

| Thành phần | Ước tính | Thành tiền |
|---|---|---|
| Cloud Run (autoscaling, min-instance giờ cao điểm) | $30–60/tháng × ~2 tháng | ~1,5–3 triệu |
| Firestore (đọc/ghi hồ sơ, điểm) | phần lớn trong hạn miễn phí | ~0,3–1 triệu |
| Cloud Storage (500 GV × 50–200MB = 25–100GB + egress tải ZIP) | $0,02/GB/tháng + egress | ~0,5–1,5 triệu |
| **Cộng cloud** | | **~2,5–5 triệu** |

### 1.3. Tổng vận hành 1 đợt 500 GV

**~30–45 triệu** (chưa tối ưu) hoặc **~18–25 triệu** (có Batches + caching) — gần như toàn bộ là chi phí AI, do DNU trả trực tiếp qua tài khoản của trường.

---

## 2. Phí chuyển giao phần mềm (một lần)

Phản ánh giá trị xây dựng: ứng dụng web hoàn chỉnh (FastAPI), 5 phân hệ (nộp hồ sơ, chấm AI, thẩm định, báo cáo, quản trị), engine chấm theo rubric chuẩn DNU (2 lượt + trung vị, trừ minh chứng, phát hiện bất thường), xuất Excel/Word/ZIP/PDF, đăng nhập + phân quyền, ~56 kiểm thử tự động, mã nguồn mở bàn giao.

| Hạng mục | Nội dung | Khoảng giá |
|---|---|---|
| **Bản quyền/chuyển giao mã nguồn** (vĩnh viễn, dùng nội bộ DNU) | Toàn bộ mã nguồn + quyền sử dụng + tài liệu kỹ thuật | 60–110 triệu |
| **Triển khai & cấu hình** | Dựng trên GCP của DNU: Firestore, Cloud Storage, Cloud Run, Cloud Scheduler, nạp API key, import danh sách GV | 10–20 triệu |
| **Đào tạo & tài liệu** | Tập huấn quản trị viên + Hội đồng + hỗ trợ giảng viên; tài liệu hướng dẫn vận hành | 8–15 triệu |
| **Bảo hành 6 tháng** | Sửa lỗi, hỗ trợ kỹ thuật trong đợt đánh giá đầu | (kèm theo) |

**Cộng gói chuyển giao: ~78–145 triệu (khuyến nghị ~110 triệu).**

---

## 3. Hạng mục nâng cấp quy mô lớn (tùy chọn, để chạy ổn định 300–500 GV)

Hệ thống hiện tại đủ cho pilot/đợt vừa; để vận hành thật ở giờ cao điểm 500 GV nên bổ sung:

| Hạng mục | Mô tả | Ước tính |
|---|---|---|
| Upload thẳng GCS (signed URL) | Bỏ giới hạn 32MB, chịu tải giờ chót | 12–20 triệu |
| Hàng đợi chấm + Batches API + chạy song song | Chấm hàng nghìn lượt bền vững, giảm 50% chi phí AI | 20–35 triệu |
| Gửi PDF/ảnh cho AI (vision) + kiểm thử tải | Chấm đúng bài scan; bảo đảm chịu tải | 10–18 triệu |
| Email dịch vụ + quên mật khẩu + sao lưu tự động | Vận hành 500 tài khoản mượt | 8–15 triệu |
| **Cộng gói nâng cấp** | | **~50–88 triệu** |

> Nếu DNU muốn **bản production hoàn chỉnh quy mô lớn** ngay: gộp Mục 2 + Mục 3 ≈ **150–230 triệu**.

---

## 4. Ba mô hình thu phí — chọn theo nhu cầu DNU

**Mô hình A — Chuyển giao trọn gói một lần (khuyến nghị).**
DNU sở hữu phần mềm + mã nguồn, tự vận hành trên hạ tầng & API key của trường.
- Thu: **~110 triệu** (Mục 2) + (tùy chọn) nâng cấp Mục 3.
- DNU tự trả AI + cloud (~30 triệu/đợt). Bên cung cấp không dính chi phí vận hành.
- Ưu: minh bạch, DNU chủ động, dùng nhiều năm. Hợp với đơn vị nhà nước (tài sản trọn gói).

**Mô hình B — Dịch vụ theo đợt / theo đầu giảng viên.**
Bên cung cấp vận hành trọn gói, thu theo số GV.
- Đơn giá đề xuất: **120.000–180.000đ/giảng viên/đợt** (đã gồm AI + cloud + vận hành + hỗ trợ).
- 500 GV → **60–90 triệu/đợt**. Không phí chuyển giao ban đầu.
- Ưu: DNU không cần lo kỹ thuật; phù hợp dùng 1–2 đợt thử.

**Mô hình C — Thuê bao SaaS hằng năm.**
- Phí nền tảng **~60–90 triệu/năm** + chi phí AI thực dùng (pass-through hoặc trọn gói +20%).
- Ưu: cập nhật liên tục, hỗ trợ thường xuyên.

---

## 5. Khuyến nghị cho DNU

Vì là đơn vị giáo dục dùng lâu dài và app đã hỗ trợ nạp API key + chạy trên GCP của trường, **Mô hình A (chuyển giao trọn gói)** là phù hợp nhất:

> **Gói đề xuất:** ~110 triệu (chuyển giao + triển khai + đào tạo + bảo hành 6 tháng).
> Cộng nâng cấp quy mô lớn nếu cần chạy 500 GV ngay: +50–88 triệu.
> DNU dự trù riêng ~30 triệu/đợt cho AI + cloud (giảm còn ~18 triệu nếu bật Batches/caching).
> Bảo trì năm tiếp theo (tùy chọn): ~18 triệu/năm.

---

## 6. Giả định & lưu ý

- Chi phí AI tính theo giá `claude-opus-4-8` ($5/$25 mỗi triệu token) và đo đạc thực tế (~2 USD/hồ sơ); thay đổi theo độ dài tài liệu, số lần chấm lại, và model được chọn (dùng Sonnet/Haiku rẻ hơn nhưng chất lượng thấp hơn).
- Cloud tính theo đơn giá GCP khu vực Đông Nam Á, đợt cao điểm ~2 tháng; ngoài đợt gần như bằng 0 nếu hạ min-instances về 0.
- Phí chuyển giao/license là khung thị trường VN cho phần mềm tùy biến mức trung bình, **chưa gồm VAT**.
- Mọi con số là **dự toán tham khảo**, chốt theo hợp đồng và phạm vi cụ thể.
