# Phase 2 — OneBee Box v0.1 (máy chủ nội bộ)

## Context Links
- [plan.md](plan.md) · Open WebUI license: https://docs.openwebui.com/license/

## Overview
- Ưu tiên: Cao · Trạng thái: Chưa bắt đầu · Dự kiến: tuần 4–6
- 1 máy trong LAN chạy toàn bộ dịch vụ bằng Docker Compose, dựng bằng 1 lệnh.

## Key Insights
- Cấu hình tối thiểu cho AI chưa chốt: đo ở phase này (CPU-only và nếu có GPU) rồi mới ghi vào bảng giá.
- Open WebUI phải giữ nguyên thương hiệu khi >50 người dùng → giao diện chat mang tên Open WebUI, OneBee chỉ là đơn vị triển khai.

## Requirements
- Dịch vụ: Ollama (AI) · Open WebUI (chat tiếng Việt trên trình duyệt) · n8n (tự động hóa) · Samba (thư mục chung) · restic REST server (nhận sao lưu máy trạm) · Uptime Kuma (giám sát) · Caddy (cổng vào, tên `box.onebee.lan`).
- Sao lưu Box ra ổ ngoài; tùy chọn sao lưu mã hóa ra ngoài đơn vị.
- Mất điện/khởi động lại → mọi dịch vụ tự lên.

## Architecture
```
Máy trạm OneBee OS ──LAN──▶ Caddy ─┬─ Open WebUI ─▶ Ollama
   restic (hằng ngày) ──────────────┼─ restic-server ─▶ ổ dữ liệu ─▶ ổ ngoài
                                    ├─ n8n ─▶ cảnh báo (Telegram/Zalo)
                                    ├─ Samba (thư mục chung)
                                    └─ Uptime Kuma
Truy cập từ xa (hỗ trợ kỹ thuật): chỉ qua Tailscale/WireGuard, không mở cổng ra Internet.
```

## Related Code Files
- Tạo: `box/docker-compose.yml`, `box/.env.example`, `box/scripts/cai-dat-box.sh`, `box/scripts/khoi-phuc-thu.sh`, `tests/box/`, `docs/huong-dan/van-hanh-box.md`
- Sửa: role `backup-client` (Phase 1) trỏ về Box

## Implementation Steps
1. Compose + `.env.example`; script cài sinh mật khẩu ngẫu nhiên.
2. CI: `docker compose config` + dựng thử các dịch vụ không cần GPU.
3. Anh chạy trên máy Box thật; em đo RAM/CPU khi AI trả lời.
4. Nối máy trạm: sao lưu hằng ngày → **thử khôi phục 1 file** (bắt buộc).

## Todo List
- [ ] Compose 7 dịch vụ  - [ ] Script cài  - [ ] CI  - [ ] Chạy máy thật  - [ ] Sao lưu + khôi phục thử  - [ ] Đo tài nguyên

## Success Criteria
- Máy sạch → `cai-dat-box.sh` → mọi dịch vụ chạy. Rút điện, bật lại → tự lên.
- Khôi phục thành công 1 file đã xóa từ bản sao lưu.

## Risk Assessment
- Máy Box yếu → AI chậm: chọn model nhỏ hoặc tách AI thành tùy chọn trả thêm.
- Ổ đơn hỏng → mất dữ liệu: bắt buộc có ổ sao lưu thứ 2.

## Security Considerations
- Không mở cổng ra Internet; mật khẩu sinh ngẫu nhiên, không dùng mặc định; sao lưu ra ngoài phải mã hóa; tách tài khoản quản trị/người dùng.

## Next Steps
- Phase 3 dùng Ollama + n8n của Box.
