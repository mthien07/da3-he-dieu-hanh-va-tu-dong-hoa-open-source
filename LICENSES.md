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
| `onebee-ai-rag` (dịch vụ Trợ lý AI & RAG nội bộ trong repo) | MIT | Gọi Ollama, tra cứu tri thức pháp lý (NĐ 30, Luật HTX) và phục vụ giao diện web tiếng Việt |
| Mailpit (chỉ dùng trong kiểm thử, không cài cho khách) | MIT | |
| vncsnapshot (chỉ dùng trong kiểm thử hỗ trợ từ xa) | GPL | Gói Ubuntu |
| n8n | Sustainable Use License (fair-code, **không** phải nguồn mở chuẩn OSI) | Theo n8n: chỉ giúp khách dựng n8n nội bộ của chính khách thì không cần giấy phép thương mại. Không bán n8n như dịch vụ host chung. |
| Uptime Kuma | MIT | |
| restic, rest-server | BSD-2-Clause | |
| Caddy | Apache-2.0 | |
| Authelia 4.39.28 (đăng nhập một lần, hai lớp) | Apache-2.0 | Tệp giấy phép đúng tag: https://raw.githubusercontent.com/authelia/authelia/v4.39.28/LICENSE (ADR 0006) |
| Python 3.14.10 (image `python:3.14.10-slim-trixie`, chạy cầu nối danh tính và dịch vụ Trợ lý AI & RAG — mã trong repo, MIT) | PSF-2.0 (Python-2.0) | Gói Debian trong image giữ giấy phép riêng; https://raw.githubusercontent.com/python/cpython/v3.14.10/LICENSE |

Giấy phép phần Box ghi theo trang của từng dự án — cần kiểm lại khi nâng phiên bản và trước khi phát hành v1.0.

→ Dịch vụ Trợ lý AI & RAG (`onebee-ai-rag`, MIT) tuân chuẩn OSI hoàn toàn; nếu giới thiệu tổng thể giải pháp là "mã nguồn mở", ghi chú rõ riêng trạng thái của n8n (fair-code) cho tới khi hoàn tất tách khỏi lõi.
