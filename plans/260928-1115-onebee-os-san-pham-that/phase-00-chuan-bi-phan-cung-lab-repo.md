# Phase 0 — Chuẩn bị: phần cứng, lab VM, giấy phép, dọn repo

## Context Links
- [plan.md](plan.md) · hồ sơ thi: `docs/m02-m03-ho-so-du-thi.md` · cẩm nang: `~/Desktop/Thi/DA3-Hoan-thien-28-9/`

## Overview
- Ưu tiên: Cao · Trạng thái: ✅ Xong 28/9 (trừ khảo sát phần mềm chỉ-Windows — chuyển sang Phase 5) · Thời lượng dự kiến: 1 tuần

## Key Insights
- Mint 22.3 chỉ amd64 → kiểm kê máy trước khi hứa với khách.
- n8n dùng Sustainable Use License (fair-code, không phải giấy phép OSI). Theo n8n: đơn vị chỉ giúp khách dựng n8n nội bộ của chính khách thì không cần giấy phép thương mại. Không được bán n8n như dịch vụ host chung.
- Open WebUI từ v0.6.6 có điều khoản giữ thương hiệu: >50 người dùng/30 ngày thì không được gỡ/đổi logo "Open WebUI". Không được đóng logo OneBee thay thế.
- → Khi nói "mã nguồn mở" phải ghi rõ thành phần nào là OSI, thành phần nào là fair-code.

## Requirements
- Bảng kiểm kê máy: CPU, 64-bit?, RAM, ổ (HDD/SSD, dung lượng), card đồ họa, máy in đang dùng.
- Danh sách phần mềm HTX đang dùng hằng ngày, đánh dấu phần mềm chỉ chạy Windows.
- Lab VM chạy được Mint 22.3 (Cinnamon + Xfce), có snapshot sạch.

## Architecture — khung repo đề xuất
```
desktop/            onebee-install.sh + ansible/ (roles: base, vietnamese, fonts, office, apps, theme, updates, backup-client)
box/                docker-compose.yml, .env.example, scripts/
ai-cli/             lệnh `hoi`
workflows/          file JSON n8n mẫu
fleet/              inventory + playbook quản lý tập trung
tests/              kiểm thử tự động
docs/               hướng dẫn tiếng Việt; docs/hoi-thi/ (chuyển hồ sơ thi cũ vào đây)
demo/               web demo hiện có
```

## Related Code Files
- Tạo: các thư mục trên, `.github/workflows/ci.yml`, `docs/adr/0001-chon-nen-tang.md`
- Sửa: `README.md` (thêm mục "Trạng thái thật"), di chuyển `docs/*.md` hồ sơ thi → `docs/hoi-thi/`
- Sửa: `demo/index.html` — gỡ/ghi "ví dụ minh họa" cho 80.000.000đ, "Giảm 80%", "giảm 40% RAM"

## Implementation Steps
1. Anh kiểm kê máy theo bảng mẫu em gửi (chụp màn hình thông số cũng được).
2. Khảo sát phần mềm chỉ-Windows ở HTX OneBee: kê khai thuế, BHXH, hóa đơn điện tử, ký số USB token, kế toán.
3. Kiểm Parallels trên MacBook chạy VM x86 Mint 22.3; tạo 2 VM (Cinnamon, Xfce) + snapshot.
4. Em dọn repo, tạo khung, CI (shellcheck, ansible-lint, yamllint).
5. Em viết ADR ngắn: chọn Mint, Ansible, Compose; bảng giấy phép từng thành phần.

## Todo List
- [x] ~~Bảng kiểm kê máy~~ — không có máy cũ; thay bằng container Mint 22.3 + VM
- [ ] Danh sách phần mềm chỉ-Windows (làm khi khảo sát đơn vị pilot)
- [x] Lab test: container `linuxmintd/mint22.3-amd64` (CI) · [ ] VM Mint trên Parallels (anh)
- [x] Khung repo + CI  - [x] ADR 0001 + LICENSES.md  - [x] Sửa số liệu demo

## Success Criteria
- VM Mint 22.3 chạy; CI xanh trên `main`; bảng kiểm kê + danh sách phần mềm chỉ-Windows có đủ.

## Risk Assessment
- Máy ≤2GB RAM hoặc 32-bit → dùng bản Xfce hoặc loại khỏi phạm vi; ổ HDD chậm → báo giá thêm SSD.
- Phần mềm thuế/BHXH/ký số chỉ chạy Windows → phương án: giữ 1 máy Windows dùng chung, dùng bản web nếu có, hoặc thử Wine/VM. Chốt sau khảo sát, không hứa trước.

## Security Considerations
- Không commit mật khẩu/tên máy/IP thật của đơn vị; `.env` vào `.gitignore`.

## Next Steps
- Xong Phase 0 → Phase 1 (Desktop) và bắt đầu chọn phần cứng Box cho Phase 2.
