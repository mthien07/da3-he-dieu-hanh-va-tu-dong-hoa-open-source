# ADR 0002 — Nền tảng cho OneBee Box (máy chủ nội bộ)

- Ngày: 28/9/2026 · Trạng thái: Đã chốt cho v0.1

## Quyết định
1. **Hệ điều hành: Ubuntu Server 24.04 LTS** (không dùng Debian 13 như dự kiến ban đầu): cùng nền với Linux Mint 22
   của máy trạm → một bộ kỹ năng, một kho gói; Docker + Compose có sẵn trong kho Ubuntu (`docker.io`, `docker-compose-v2`)
   nên nhận bản vá qua unattended-upgrades.
2. **Cấu hình bằng Ansible chạy tại chỗ** (giống Desktop), chỉ module `ansible.builtin`.
3. **Dịch vụ chạy bằng Docker Compose**, image **ghim phiên bản cố định** trong `box/ansible/group_vars/all.yml`
   (nâng cấp = sửa phiên bản → chạy lại bộ cài).
4. **Không mở API Ollama ra LAN** (API không có mật khẩu). Người dùng hỏi AI qua Open WebUI (có tài khoản).
5. **HTTP trong LAN (v0.1); từ rà soát bảo mật 10/10/2026 có thể bật HTTPS nội bộ** (CA riêng + Caddy, xem ADR 0005; bật bằng `onebee_box_https: true`, mặc định chưa bật). Truy cập từ xa chỉ qua VPN (Tailscale/WireGuard). Không mở cổng trên router.
6. **Samba cài thẳng trên máy chủ** (gói Ubuntu, nhận bản vá tự động), không chạy trong container.
7. **Sao lưu 2 tầng bằng restic**:
   - Máy trạm → Box (rest-server, `--private-repos --append-only`): mỗi máy chỉ thấy kho của mình và **không xóa được**
     bản cũ → mã độc tống tiền trên máy trạm không phá được bản sao lưu. Box giữ mật khẩu kho để tự dọn bản cũ.
   - Box → ổ ngoài (mã hóa), hằng ngày 23:00; tạm dừng Open WebUI/n8n/Uptime Kuma lúc chụp để dữ liệu nhất quán.
     Không sao lưu model AI (tải lại được) và kho máy trạm (đã là bản sao). Thư mục chung sao lưu SAU khi chạy lại
     dịch vụ (có thể lâu) → dịch vụ chỉ dừng trong lúc chụp phần dữ liệu CSDL.
8. **Chống bản sao lưu giả mạo**: máy trạm bị chiếm có thể tạo bản mang ngày tương lai để chính sách dọn đẩy bản
   thật ra. Box giữ mọi bản 30 ngày gần nhất (`--keep-within 30d`) và **không dọn** kho nào có bản ngày tương lai (báo CẢNH BÁO).
9. **Ổ sao lưu phải là ổ gắn riêng** (`mountpoint`), kho chỉ tạo bằng lệnh tay `onebee-box khoi-tao` — lịch tự động
   không bao giờ tự tạo kho (tránh âm thầm ghi vào ổ hệ thống khi rút ổ ngoài).
10. **Quyền riêng tư**: Box giữ mật khẩu kho của từng máy trạm → quản trị Box đọc được sao lưu `/home`. Chấp nhận ở v0.1,
   phải thông báo cho đơn vị.
11. **Chưa chọn model AI mặc định** — chấm thử tiếng Việt ở Phase 3 rồi mới chọn.

## Hệ quả / giới hạn
- Chưa có TLS nội bộ; n8n phải chạy `N8N_SECURE_COOKIE=false`.
- Chỉ 1 ổ dữ liệu + 1 ổ sao lưu (chưa đủ 3-2-1: chưa có bản sao ngoài đơn vị).
- Docker bỏ qua tường lửa ufw với cổng đã publish → dựa vào router không mở cổng.
- Open WebUI / n8n / Uptime Kuma lấy người mở đầu tiên làm quản trị → kỹ thuật viên tạo tài khoản ngay sau khi cài.
- Máy đã có Docker CE thì dùng luôn (không cài đè `docker.io`).
