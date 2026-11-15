# Giấy phép các thành phần (100% Chuẩn OSI — Proof of Freedom)

Mã nguồn của **OneBee OS** trong kho lưu trữ này (kịch bản, playbook Ansible, dịch vụ lõi DX-OS, tài liệu): **MIT License** (`SPDX-License-Identifier: MIT` — xem [LICENSE](LICENSE)).
Toàn bộ các thành phần chạy trong đường dẫn thực thi của **OneBee OS v1.3.0 (DX-OS Open-Core)** đều mang **giấy phép nguồn mở chuẩn OSI (Open Source Initiative)**, không còn bất kỳ thành phần Source-Available hay giới hạn thương hiệu nào.

## OneBee OS Desktop
| Thành phần | Giấy phép (Chuẩn OSI) | Ghi chú |
|---|---|---|
| Linux Mint 22.x / Ubuntu 24.04 | GPL-2.0 / GPL-3.0 / LGPL | Công cụ hệ thống từ kho chính thức |
| LibreOffice | MPL-2.0 | Bộ ứng dụng văn phòng mở |
| IBus | LGPL-2.1+ | Khung bộ gõ |
| ibus-bamboo | GPL-3.0 | Bộ gõ tiếng Việt Telex/VNI |
| ibus-unikey (dự phòng) | GPL-3.0 | |
| Font Liberation 2, Carlito, Noto | SIL OFL 1.1 | Tương thích bố cục văn bản hành chính |
| Font Caladea | Apache-2.0 / OFL 1.1 | |
| ansible-core | GPL-3.0+ | Công cụ tự động hóa cấu hình |
| x11vnc | GPL-2.0 | Hỗ trợ từ xa có xin phép người dùng |
| OpenSSH server | BSD-2-Clause | Quản trị từ xa an toàn |
| zenity, libnotify-bin | LGPL-2.1+ | Hộp thoại và thông báo bàn làm việc |

## OneBee Box (DX-OS Open-Core v1.3.0)
| Thành phần | Phiên bản ghim | Giấy phép (Chuẩn OSI) | Vai trò trong kiến trúc 3 tầng DX-OS |
|---|---|---|---|
| Ubuntu Server 24.04, Docker, Samba | 24.04 LTS | GPL-3.0 / Apache-2.0 | Hệ điều hành máy chủ & chia sẻ tệp LAN |
| Caddy | `2.11.2-alpine` | Apache-2.0 | Cổng ngược HTTPS nội bộ & ForwardAuth |
| Authelia | `4.39.28` | Apache-2.0 | Định danh tập trung (SSO) & 2FA TOTP (`[H]`) |
| `onebee-cau-noi.py` (OneBee) | `1.3.0` | MIT | Cầu nối SSO -> JWT HS256 (60s) & Quản trị người dùng (`[H]`) |
| Node-RED | `4.1.8-22` | Apache-2.0 | Động cơ quy trình nghiệp vụ & Phê duyệt Poka-yoke (`[P]`) |
| PostgreSQL + `pgvector` | `0.8.2-pg16` | PostgreSQL / MIT | CSDL quan hệ, tìm kiếm Vector & phân quyền RLS (`[D]`) |
| PostgREST | `v12.2.12` | MIT | Cổng RESTful API sinh tự động từ lược đồ PostgreSQL (`[D]`) |
| SeaweedFS | `3.80` | Apache-2.0 | Kho lưu trữ đối tượng tương thích S3 nội bộ (`[D]`) |
| ClamAV | `1.4.2` | GPL-2.0 | Quét và cách ly mã độc cho mọi tệp tải lên (`[D]`) |
| `onebee-kho-tep.py` (OneBee) | `1.3.0` | MIT | Cổng kiểm dịch tệp (ClamAV -> SeaweedFS / Quarantine) (`[D]`) |
| Ollama | `0.21.0` | MIT | Động cơ suy luận mô hình ngôn ngữ lớn tại chỗ (`[I]`) |
| Mô hình Qwen 2.5 (`qwen2.5:1.5b` / `3b`) | `2.5` | Apache-2.0 | Mô hình ngôn ngữ tiếng Việt gọn nhẹ chạy CPU (`[I]`) |
| `onebee-ai-rag.py` (OneBee) | `1.3.0` | MIT | Dịch vụ Trợ lý AI, RAG SQLite FTS5 & Văn bản Nghị định 30 (`[I]`) |
| Uptime Kuma | `1.23.17-alpine` | MIT | Giám sát trạng thái các dịch vụ nội bộ |
| Restic & `rest-server` | `0.18.0` / `0.14.0` | BSD-2-Clause | Sao lưu mã hóa chống mã độc tống tiền |
| MeshCentral (tùy chọn) | `1.1.56` | Apache-2.0 | Hỗ trợ kỹ thuật từ xa trong mạng nội bộ |

> **Lịch sử chuyển đổi giấy phép (ADR 0006 & ADR 0007):** Từ phiên bản `v1.3.0`, dự án đã loại bỏ hoàn toàn `Node-RED` (Sustainable Use License) và `OneBee AI RAG` (điều khoản thương hiệu từ v0.6.6+) để đạt chuẩn **100% OSI Open Source**.
