<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Lộ trình phát triển OneBee DX-OS Open-Core (ROADMAP)

> **Cam kết duy trì mã nguồn mở:** Nhóm tác giả và HTX OneBee cam kết duy trì kho mã nguồn mở công khai, cập nhật vá lỗi bảo mật và phản hồi cộng đồng trên GitHub Issues **tối thiểu 12 tháng sau cuộc thi OLP 2026 (tối thiểu đến hết tháng 12/2027)** dưới giấy phép **MIT**.

---

## Các mốc đã hoàn thành

### `v1.0.0` → `v1.2.0` — Nền tảng Máy văn phòng & Máy chủ nội bộ HTX (10–11/2026)
- Bộ cài tự động idempotent (`changed=0`) cho Linux Mint 22.x (Desktop) và Ubuntu Server 24.04 LTS (Box).
- Bộ gõ IBus Bamboo tiếng Việt, LibreOffice cấu hình chuẩn `.docx/.xlsx` và giao diện Ribbon, Trung tâm OneBee, sao lưu bất biến 2 tầng `restic`, CA nội bộ ràng buộc tên.
- Mô hình AI Gemma 4 chạy tại chỗ qua Ollama + công cụ dòng lệnh `hoi`, bộ kiểm thử 190+ test tự động và nghiệm thu container.

### `v1.3.0` (Đang hoàn thiện cho OLP 2026) — Nâng cấp toàn diện **DX-OS Open-Core 100% OSI**
- **100% giấy phép OSI:** Loại bỏ toàn bộ thành phần ngoài OSI (mục fair-code và mục có điều khoản hạn chế thương hiệu ở bản v1.0–v1.2), giữ trọn hệ sinh thái **MIT / Apache-2.0 / PostgreSQL / GPL-2.0-only / BSD-2-Clause**.
- **Tầng Nền tảng Dịch vụ Lõi số (Headless PaaS):**
  - Authelia 4.39.28 SSO + 2FA TOTP + cầu nối JWT `ES256` 60 giây (`onebee-dinh-danh`).
  - PostgreSQL 18.7 + `pgvector 0.8.7` + PostgREST 16.5 với Row-Level Security (RLS).
  - Kho tệp SeaweedFS 4.53 + kiểm dịch mã độc biên mạng `clamscan` (ClamAV 1.5.4).
  - Động cơ quy trình Node-RED 5.0.9 cho luồng phê duyệt và thông báo email SMTP.
  - Dịch vụ Trợ lý AI & RAG thuần lõi `onebee-ai-rag.py` (MIT) hỗ trợ `/ai/*` (SSO) và `/ai-cli/*` (`hoi` Bearer token).
- **Tầng Không gian Năng lực số (H-P-D-I):** Giao diện Web Workspace thống nhất cho Hợp tác xã / SME và chế độ bản chạy thử công khai trên Internet.

---

## Kế hoạch phát triển sau cuộc thi (12/2026 – 12/2027)

### `v1.4.0` (Quý I–II/2027) — Mở rộng kết nối OT / IoT & Hỗ trợ cài đặt thực địa
- Chuẩn hóa bộ thu thập telemetry nông nghiệp / nhà kho theo chuẩn mở **NGSI-LD** nối trực tiếp vào đường ống Node-RED và PostgreSQL (`Tầng Nền tảng Dịch vụ Lõi số`).
- Triển khai thí điểm và công bố bộ số liệu thực tế sau 6 tháng vận hành tại các Hợp tác xã thành viên (`reports/`).
- Bổ sung bộ cài tự động cập nhật cơ sở dữ liệu chữ ký ClamAV ngoại tuyến (`cvdupdate` USB sync) cho Box không có Internet.

### `v1.5.0` (Quý III/2027) — Dữ liệu lạnh phân tích & Kiểm toán chuỗi cung ứng
- Thử nghiệm phân tầng dữ liệu lạnh theo kiến trúc **Lakehouse (Apache Iceberg)** trên SeaweedFS cho báo cáo tổng hợp đa niên độ.
- Ký số toàn bộ bản phát hành `.tar.gz` bằng **Cosign / Minisign** trong GitHub Actions release workflow.
- Bổ sung kết nối hóa đơn điện tử và thanh toán QR VietQR mở trên `Tầng Nền tảng Kinh doanh số`.

### `v2.0.0` (Quý IV/2027) — Quản trị dữ liệu liên thông (OpenMetadata) & Đa Box chi nhánh
- Tích hợp **OpenMetadata** cho danh mục dữ liệu và truy vết dòng dữ liệu ở các HTX liên hiệp quy mô lớn.
- Hỗ trợ đồng bộ liên thông giữa nhiều OneBee Box chi nhánh qua WireGuard/Tailscale với định danh liên kết Authelia OIDC.

---

## Tham gia đóng góp
- Xem hướng dẫn đóng góp và cách chạy kiểm thử tại [CONTRIBUTING.md](CONTRIBUTING.md).
- Gửi báo lỗi hoặc đề xuất tính năng qua [GitHub Issues](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/issues).
- Báo cáo lỗ hổng bảo mật riêng tư theo hướng dẫn tại [SECURITY.md](SECURITY.md).
