# Giấy phép các thành phần

Mã nguồn của OneBee OS trong repo này (script, playbook, tài liệu): **MIT** (xem README).
OneBee OS **không bán phần mềm**; các thành phần bên dưới giữ nguyên giấy phép của tác giả.

## OneBee OS Desktop
| Thành phần | Giấy phép | Ghi chú |
|---|---|---|
| Linux Mint 22.x / Ubuntu 24.04 | Nhiều giấy phép nguồn mở (chủ yếu GPL) | Công cụ Mint như mintupdate: GPL-3 |
| LibreOffice | MPL-2.0 (một phần GPL/MIT) | |
| IBus | LGPL-2.1+ | |
| ibus-bamboo | GPL-3.0 | PPA của dự án BambooEngine |
| ibus-unikey (dự phòng) | GPL | |
| Font Liberation 2 | SIL OFL 1.1 | |
| Font Carlito | SIL OFL 1.1 | |
| Font Caladea | Apache-2.0 / OFL 1.1 | |
| Font Noto | SIL OFL 1.1 | |
| ansible-core | GPL-3.0+ | Chỉ dùng để cài đặt, không phân phối lại |
| x11vnc (hỗ trợ từ xa, từ v0.4) | GPL-2.0 | Gói Ubuntu; theo file copyright của gói |
| OpenSSH server (Box cập nhật máy trạm, từ v0.4) | BSD (giấy phép OpenSSH) | Gói Ubuntu |
| zenity, libnotify-bin (hộp thoại, thông báo) | LGPL | Có sẵn trên Mint |

Nguồn: file `/usr/share/doc/<gói>/copyright` của từng gói trên Linux Mint 22.3 / Ubuntu 24.04.
Clonezilla (sao lưu/nhân bản ổ đĩa, chỉ dùng như công cụ khi cài, không phân phối): GPL theo trang dự án — kiểm lại trước khi ghi vào hợp đồng.

## OneBee Box
| Thành phần | Giấy phép | Lưu ý khi kinh doanh |
|---|---|---|
| Ubuntu Server 24.04, Docker (docker.io), Samba | Nguồn mở (Apache-2.0, GPL-3.0…) | Gói từ kho Ubuntu |
| Ollama | MIT | |
| Model Gemma 4 (`gemma4:e2b-it-qat`, Google) | Apache-2.0 (theo model card Gemma 4) | Kiểm lại trang giấy phép chính thức trước khi ghi vào hợp đồng |
| Mailpit (chỉ dùng trong kiểm thử, không cài cho khách) | MIT | |
| vncsnapshot (chỉ dùng trong kiểm thử hỗ trợ từ xa) | GPL | Gói Ubuntu |
| Open WebUI | BSD-3 + điều khoản thương hiệu (từ v0.6.6) | >50 người dùng/30 ngày: không được gỡ/đổi thương hiệu "Open WebUI". OneBee không đổi tên/logo. |
| n8n | Sustainable Use License (fair-code, **không** phải nguồn mở chuẩn OSI) | Theo n8n: chỉ giúp khách dựng n8n nội bộ của chính khách thì không cần giấy phép thương mại. Không bán n8n như dịch vụ host chung. |
| Uptime Kuma | MIT | |
| restic, rest-server | BSD-2-Clause | |
| Caddy | Apache-2.0 | |
| Authelia 4.39.28 (đăng nhập một lần, hai lớp) | Apache-2.0 | Tệp giấy phép đúng tag: https://raw.githubusercontent.com/authelia/authelia/v4.39.28/LICENSE (ADR 0006) |
| Python 3.14.10 (image `python:3.14.10-slim-trixie`, chạy cầu nối danh tính — mã cầu nối trong repo, MIT) | PSF-2.0 (Python-2.0) | Gói Debian trong image giữ giấy phép riêng; https://raw.githubusercontent.com/python/cpython/v3.14.10/LICENSE |
| PostgreSQL 18.7 (image `pgvector/pgvector:0.8.7-pg18-trixie`, CSDL dữ liệu cấu trúc) | PostgreSQL License (kiểu BSD/MIT) | https://raw.githubusercontent.com/postgres/postgres/REL_18_7/COPYRIGHT (ADR 0006); gói Debian trong image giữ giấy phép riêng |
| pgvector 0.8.7 (mở rộng vector trong cùng image) | PostgreSQL License | https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/LICENSE (ADR 0006) |
| PostgREST 16.5 (API tự sinh trên CSDL) | MIT | https://raw.githubusercontent.com/PostgREST/postgrest/v16.5/LICENSE (ADR 0006) |

Giấy phép phần Box ghi theo trang của từng dự án — cần kiểm lại khi nâng phiên bản và trước khi phát hành v1.0.

→ Khi giới thiệu sản phẩm là "mã nguồn mở", phải nói rõ n8n là fair-code và điều khoản thương hiệu của Open WebUI.

## Lõi DX-OS: thành phần của kiến trúc ba tầng
<!-- Khối của hồ sơ kiến trúc (docs/kien-truc-dx-os.md): liệt kê đủ thành phần Tầng 1 theo Đề thi, kể cả dòng đã có ở bảng Box phía trên -->
Nguồn: [ADR 0006](docs/adr/0006-loi-dx-os-open-core.md), tệp giấy phép đọc đúng tag đã dựng thử. Mã do dự án viết (cầu nối danh tính, dịch vụ tệp,
`onebee-ai-rag`, trang Sổ điều hành, `onebee-box`, `hoi`) là MIT, xem [LICENSE](LICENSE).

| Thành phần | Giấy phép | Ghi chú |
|---|---|---|
| SeaweedFS 4.53 (kho tệp kiểu đối tượng) | Apache-2.0 | https://raw.githubusercontent.com/seaweedfs/seaweedfs/4.53/LICENSE |
| ClamAV 1.5.4 (kiểm dịch tệp tải lên, chạy từng lượt bằng `clamscan`) | GPL-2.0-only (lõi) | Image dựng cục bộ **xóa `libclamunrar`** (giấy phép UnRAR, không phải OSI); các thư viện kèm theo giữ giấy phép riêng (LGPL-2.1, Apache-2.0, BSD-3-Clause, MIT, Zlib). https://raw.githubusercontent.com/Cisco-Talos/clamav/clamav-1.5.4/COPYING.txt |
| cvdupdate 1.2.0 (tải chữ ký ClamAV ở máy có Internet, chép sang Box không có mạng) | Apache-2.0 | Chỉ chạy ở máy kỹ thuật, không cài trên Box |
| Node-RED 5.0.9 (động cơ quy trình) | Apache-2.0 | https://raw.githubusercontent.com/node-red/node-red/5.0.9/LICENSE |
| node-red-node-email 5.2.5 (nút gửi thư SMTP) | Apache-2.0 | Gói npm khai `Apache-2.0` |
