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

Giấy phép phần Box ghi theo trang của từng dự án — cần kiểm lại khi nâng phiên bản và trước khi phát hành v1.0.

→ Khi giới thiệu sản phẩm là "mã nguồn mở", phải nói rõ n8n là fair-code và điều khoản thương hiệu của Open WebUI.
