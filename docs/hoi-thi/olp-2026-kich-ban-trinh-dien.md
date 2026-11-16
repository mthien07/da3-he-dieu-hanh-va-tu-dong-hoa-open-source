<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Kịch bản thuyết trình Chung kết OLP 2026 (Tổng thời lượng: 15 phút)

Kịch bản trình bày trước Hội đồng Giám khảo OLP Tin học Sinh viên Việt Nam 2026 — Khối Phần mềm Nguồn mở, bám sát **4 nội dung bắt buộc (Mục 6 Đề thi)** cùng **phương án dự phòng offline 100%**.

---

## Tổng quan phân bổ thời gian (15/15 phút)

| Phần | Nội dung chính | Thời lượng |
|---|---|---|
| **Phần 1** | Bài toán doanh nghiệp/HTX, kiến trúc **3 tầng** DX-OS Open-Core & lựa chọn công nghệ 100% OSI | **03 phút** |
| **Phần 2** | Tính năng nền tảng lõi chạy ngầm & bài toán minh họa nghiệp vụ (`H-P-D-I`) | **03 phút** |
| **Phần 3** | **Live Demo trọn vòng `H → P → D → I`** trên bản chạy thử công khai + CLI `hoi` máy trạm | **07 phút** |
| **Phần 4** | Định hướng phát triển hậu cuộc thi (`ROADMAP.md`), cộng đồng & Q&A nhanh | **02 phút** |
| **Tổng cộng** | | **15 phút** |

---

## Chi tiết từng phần

### Phần 1 — Đặt vấn đề, Kiến trúc 3 tầng DX-OS & Lựa chọn công nghệ OSI (03:00)
- **Slide 1–2 (01:00):** Thực trạng chuyển đổi số tại Hợp tác xã & SME: phụ thuộc phần mềm văn phòng không bản quyền, thiếu IT chuyên trách sao lưu/vận hành, lo ngại rò rỉ dữ liệu nội bộ khi dùng AI đám mây công cộng.
- **Slide 3–4 (02:00):** Giải pháp **OneBee DX-OS Open-Core** — kết hợp **Máy trạm Linux tiếng Việt** và **Máy chủ nội bộ Headless PaaS 100% OSI**:
  - **Tầng Nền tảng Dịch vụ Lõi số:** Caddy 2.11.4, Authelia 4.39.28 + JWT HS256 sống 60 giây, PostgreSQL 18.7 + `pgvector` + PostgREST 16.5 (RLS), SeaweedFS 4.53 + ClamAV 1.5.4 (`clamscan`), Node-RED 5.0.9, `onebee-ai-rag.py` (MIT) + Ollama + Gemma 4, restic rest-server, Uptime Kuma.
  - **Tầng Không gian Năng lực số (`H-P-D-I`):** Hợp nhất luồng công việc, quy trình, điều hành và trí tuệ nhân tạo.
  - **Tầng Nền tảng Kinh doanh số:** Định hướng mở rộng hóa đơn điện tử, TMĐT và tích hợp ngân hàng mở.
  - Nhấn mạnh việc **loại bỏ hoàn toàn** các thành phần ngoài OSI để giữ chuẩn Open-Core MIT/Apache-2.0.

### Phần 2 — Tính năng nền tảng lõi & 4 nguyên lý thiết kế (03:00)
- **Slide 5–6 (03:00):** Giới thiệu ngắn gọn **4 nguyên lý** đã chạy thật:
  1. Tách dữ liệu **nóng/lạnh** (PostgreSQL OLTP vs `restic` `--append-only` bất biến).
  2. **Hội tụ** telemetry máy trạm (`onebee-bao-tinh-trang`) về cùng CSDL tác nghiệp.
  3. Quản trị chất lượng (`CHECK`, RLS, OpenAPI tự sinh từ PostgREST, chống rò rỉ PII).
  4. **Zero-Trust + GitOps + Kiểm dịch biên mạng** (TLS, `forward_auth`, `clamscan` tại `/files/`, Ansible `changed=0`).

### Phần 3 — Live Demo trọn vòng `H → P → D → I` & `hoi` CLI (07:00)
*(Thực hiện trên Box của đơn vị hoặc bản chạy thử công khai nếu đã có host; nếu chưa có host, demo trên máy ảo cục bộ như phương án dự phòng bên dưới)*
1. **[H] Điều phối công việc (01:30):**
   - Đăng nhập bằng `nhanvien1` qua Authelia `/dangnhap/`.
   - Tạo đơn hàng nông sản HTX mới, đính kèm 1 tệp PDF hợp đồng mẫu -> hệ thống quét `clamscan` và trả nhãn `CLEAN` trong SeaweedFS.
   - Thử gửi tệp mẫu kiểm tra EICAR -> bị chặn tại biên mạng với trạng thái `INFECTED` (422).
2. **[P] Vận hành quy trình (01:30):**
   - Đăng nhập tài khoản `quanly1` đã ghi danh TOTP trước buổi thi (minh họa phân quyền RLS khác biệt so với `nhanvien1`), xem đơn `CHO_DUYET`, bấm **Phê duyệt** -> Node-RED chuyển trạng thái sang `DA_DUYET` và ghi nhật ký thông báo.
3. **[D] Điều hành & Giám sát (01:30):**
   - Mở bảng Điều hành `[D]`: số liệu tổng hợp tăng trực tiếp từ PostgreSQL, xem trạng thái máy trạm hội tụ và Uptime Kuma.
4. **[I] Trợ lý AI nội bộ & `hoi` CLI (02:30):**
   - Bấm **Tóm tắt điều hành** (`/ai/tom-tat`) với số liệu tuần: AI tổng hợp nhanh, giữ nguyên số liệu, kèm lời nhắc đối chiếu văn bản gốc.
   - Mở terminal máy trạm chạy `hoi "thể thức công văn theo Nghị định 30 gồm những thành phần nào?"`: truy xuất RAG qua `/ai/hoi` bằng khóa riêng `obk-` của máy trạm, có trích dẫn nguồn tiếng Việt.

### Phần 4 — Định hướng phát triển & Cộng đồng (02:00)
- **Slide 7–8 (02:00):** Trình bày lộ trình `ROADMAP.md` (`v1.4` IoT NGSI-LD cho nông nghiệp HTX -> `v1.5` Apache Iceberg -> `v2.0` OpenMetadata), cam kết duy trì repo tối thiểu 12 tháng tới 12/2027, và mời Ban Giám khảo đặt câu hỏi.

---

## Phương án dự phòng rủi ro tại hội trường (Offline 100%)
1. **Chuẩn bị sẵn 01 video quay màn hình không cắt ghép (3–5 phút)** quay trọn vẹn vòng `H → P → D → I` và `hoi` CLI trên chính bản demo/VM, lưu cục bộ trên máy thuyết trình.
2. **Máy chủ Demo dự phòng cục bộ:** Mang theo laptop cấu hình sẵn VM/Docker chạy cục bộ `onebee-box` + `localhost` để sẵn sàng demo ngay cả khi Wi-Fi hội trường mất kết nối Internet.
3. **Kiểm tra trước giờ thi 30 phút:** Bật/xác nhận trạng thái reset dữ liệu 03:00 của host demo công khai và kiểm tra mic/HDMI/terminal font cỡ lớn (`18pt`).
