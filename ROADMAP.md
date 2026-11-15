# Lộ trình Phát triển (ROADMAP) — OneBee OS (DX-OS Open-Core)

Lộ trình phát triển của **OneBee OS** hướng tới việc xây dựng một khung nền tảng chuyển đổi số mở (Open-Core Digital Transformation OS) bền vững, gọn nhẹ và tự chủ hoàn toàn cho các Doanh nghiệp Siêu nhỏ và Hợp tác xã (MSME/HTX) tại Việt Nam.

---

## Đã hoàn thành

### `v1.0.0` — Nền tảng Máy trạm & Hộp Dịch vụ Nội bộ (Foundation)
- Tự động hóa triển khai **OneBee Desktop** (Ubuntu 24.04 LTS, bộ gõ tiếng Việt `ibus-bamboo`, LibreOffice, trình duyệt, công cụ AI dòng lệnh `hoi`).
- Đóng gói **OneBee Box** chạy bằng Docker Compose với Cổng nội bộ Caddy, Ollama AI nội bộ, sao lưu Restic và giám sát Uptime Kuma.

### `v1.1.0` & `v1.2.0` — Vận hành Thực chiến, HTTPS Nội bộ & Bộ cài Ngoại tuyến (Field Operations)
- Tự động cấp chứng chỉ HTTPS nội bộ (Caddy Local CA) và quảng bá tên miền `.local` qua mDNS (Avahi).
- Cảnh báo chủ động qua systemd timer (nhiệt độ CPU, dung lượng đĩa, trạng thái container, tuổi bản sao lưu) và tích hợp hỗ trợ từ xa MeshCentral.
- Đóng gói bộ cài đặt ngoại tuyến (Air-gapped USB Installer) cho vùng sâu vùng xa.

### `v1.3.0` — Kiến trúc Lõi Mở DX-OS 100% Chuẩn OSI (OLP 2026 Release)
- **Chuẩn hóa Giấy phép 100% OSI (Proof of Freedom)**:
  - Thay thế công cụ fair-code cũ (Sustainable Use License) bằng **Node-RED 4.1.8 (`Apache-2.0`)** kèm 11 luồng nghiệp vụ và phê duyệt tự động.
  - Thay thế `giao diện AI bên thứ ba` (giấy phép kèm điều khoản ràng buộc thương hiệu từ v0.6.6+) bằng dịch vụ **`onebee-ai-rag.py` (`MIT`)** tích hợp RAG SQLite FTS5 và thư viện mẫu văn bản hành chính theo **Nghị định 30/2020/NĐ-CP**.
  - Gắn định danh `SPDX-License-Identifier: MIT` trên 100% tệp mã nguồn và kiểm tra tự động trên CI (`scripts/chen-giay-phep.py --kiem`).
- **Định danh Tập trung (SSO) & Phân quyền Dữ liệu Tận gốc (Zero-Trust RBAC)**:
  - Tích hợp **Authelia 4.39.28 (`Apache-2.0`)** làm cổng xác thực duy nhất (SSO + 2FA TOTP) kết hợp **Cầu nối JWT (`onebee-cau-noi.py`)** cấp JWT ngắn hạn (60 giây) xuống **PostgreSQL 16 + `pgvector` + PostgREST 12.2.12** với chính sách **Row-Level Security (RLS)** theo 3 vai trò (`nhan_vien`, `ky_thuat`, `quan_ly`).
- **Sổ Điều hành HTX (`[H]-[P]-[D]-[I]`) & Cơ chế Chống sai sót Poka-yoke**:
  - Ứng dụng web 1 trang tại `/so-dieu-hanh/` phục vụ tạo phiếu Đơn hàng / Hỗ trợ / Khảo sát, đính kèm tệp và phê duyệt quản lý.
  - Ràng buộc Poka-yoke 3 lớp (UI + Node-RED + PostgreSQL `CHECK` constraint) ngăn người tạo tự duyệt phiếu của chính mình và bắt buộc ghi lý do khi từ chối.
- **Kho Lưu trữ Đối tượng & Cách ly Mã độc Tự động**:
  - Tích hợp **SeaweedFS (`Apache-2.0`)** và **ClamAV (`GPL-2.0`)** thông qua `onebee-kho-tep.py` để quét mọi tệp tải lên và cách ly tức thời tệp nhiễm mã độc (`INFECTED`).

---

## Kế hoạch Tiếp theo (2027)

### `v1.4.0` — Liên thông Liên Hợp tác xã & Truy xuất Nguồn gốc Nông sản (Q1–Q2/2027)
- Đồng bộ dữ liệu tổng hợp ẩn danh giữa nhiều OneBee Box của các HTX thành viên về Liên minh HTX tỉnh qua kênh WireGuard VPN nội bộ.
- Sinh mã QR truy xuất nguồn gốc lô mật ong / nông sản trực tiếp từ phiếu `DA_DUYET` trong PostgreSQL và lưu chứng thư số trên SeaweedFS.

### `v1.5.0` — Gói Phần cứng Tham chiếu Mở & Triển khai Tự động Zero-Touch (Q3–Q4/2027)
- Phát hành ảnh đĩa cài sẵn (Golden Image ISO/IMG) cho Mini PC x86_64 và ARM64 (RK3588) giúp HTX cắm điện là chạy trong 10 phút.
- Mở rộng bộ mẫu nghiệp vụ ngành dọc (HTX Nông nghiệp, HTX Dược liệu, Doanh nghiệp Chế biến Nhỏ) dưới dạng gói plugin mở cài bằng 1 lệnh `sudo onebee-box cai-goi-nganh`.
