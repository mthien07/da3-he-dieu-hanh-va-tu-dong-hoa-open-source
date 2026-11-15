<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Nhật ký thay đổi (CHANGELOG)

Tất cả thay đổi quan trọng của **OneBee DX-OS Open-Core** được ghi lại tại đây (chi tiết kỹ thuật từng lượt nghiệm thu xem thêm ở [docs/project-changelog.md](docs/project-changelog.md)).

## [1.3.0] — 15/11/2026

### Thêm mới
- Hoàn thiện hồ sơ kiến trúc DX-OS Open-Core 3 tầng & 4 nguyên lý thiết kế ([docs/kien-truc-dx-os.md](docs/kien-truc-dx-os.md)).
- Bổ sung đặc tả API & CLI công khai ([docs/api/openapi-dxos.md](docs/api/openapi-dxos.md)), lộ trình phát triển 2026–2027 ([ROADMAP.md](ROADMAP.md)) và bảng đối chiếu PoF 50/50 ([docs/olp-2026-tu-cham-pof.md](docs/olp-2026-tu-cham-pof.md)).
- Bổ sung chế độ bản chạy thử công khai OLP 2026 (`onebee_box_che_do_demo`) và dữ liệu giả lập tự động đặt lại lúc 03:00 mỗi đêm.
- Thêm kiểm thử `tests/box/test_olp_2026_ho_so.py` kiểm chứng hồ sơ, giấy phép và sự đồng bộ tài liệu.

### Thay đổi
- Chuẩn hóa 100% thành phần lõi mặc định sang giấy phép đạt chuẩn OSI: **Caddy (Apache-2.0)**, **Authelia (Apache-2.0)**, **PostgreSQL + pgvector (PostgreSQL)**, **PostgREST (MIT)**, **SeaweedFS (Apache-2.0)**, **ClamAV `clamscan` (GPL-2.0-only)**, **Node-RED (Apache-2.0)**, **`onebee-ai-rag.py` (MIT)**, **Ollama (MIT)**, **Uptime Kuma (MIT)**, **restic (BSD-2-Clause)**.
- Loại bỏ hoàn toàn `n8n` (SUL), `Open WebUI` (điều khoản thương hiệu) và `libclamunrar` khỏi cấu hình mặc định.
- Nâng phiên bản phát hành `1.3.0` đồng bộ trên `desktop/ansible/group_vars/all.yml`, `box/ansible/group_vars/all.yml`, `scripts/dong-goi-ban-phat-hanh.sh` và bộ kiểm thử.

## [1.2.0] — 14/11/2026
- Trải nghiệm người dùng: Trung tâm OneBee tự mở lần đầu, trang Kiểm tra máy, LibreOffice Ribbon thực sự, hỗ trợ Telex trên Firefox, sửa lệnh `onebee-box` UTF-8 và 4 mẫu soạn văn bản hành chính.

## [1.0.0] — 14–15/10/2026
- Phát hành bản thương mại đầu tiên OneBee OS Desktop + OneBee Box: nghiệm thu 127/127 bước Box và 71/71 bước Desktop trong container; 198 unit test và lint sạch.

## [0.3.0] — 29/09/2026
- Ra mắt Trợ lý AI Gemma tiếng Việt chạy nội bộ và hệ thống tự động hóa email, nhắc hạn, tóm tắt PDF, sao lưu 2 tầng chống mã độc tống tiền.
