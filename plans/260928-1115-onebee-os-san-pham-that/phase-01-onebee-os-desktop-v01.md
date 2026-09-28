# Phase 1 — OneBee OS Desktop v0.1

## Context Links
- [plan.md](plan.md) · [phase-00](phase-00-chuan-bi-phan-cung-lab-repo.md) · ibus-bamboo: https://github.com/BambooEngine/ibus-bamboo

## Overview
- Ưu tiên: Cao · Trạng thái: ✅ Code + test mở rộng đạt (28/9); còn thử phiên Cinnamon thật · Dự kiến: tuần 2–4
- Cài Mint 22.3 chuẩn → chạy `desktop/onebee-install.sh` → máy thành "OneBee OS".

## Key Insights
- Mint 22.3 cùng nền Ubuntu 24.04 → CI thử playbook trong container ubuntu:24.04, còn kiểm thật phải trên VM Mint.
- Rủi ro người dùng hay gặp nhất: gõ tiếng Việt, vỡ font khi mở file Word/Excel, máy in.

## Requirements
- Chức năng: gõ tiếng Việt (Telex/VNI); font tương thích số đo với Arial/Times/Calibri/Cambria (Liberation, Carlito, Caladea) + Noto; LibreOffice giao diện tiếng Việt, mặc định lưu .docx/.xlsx/.pptx, kiểm chính tả tiếng Việt; trình duyệt; máy in CUPS; giao diện kiểu Windows (thanh tác vụ dưới, menu Start), hình nền + logo OneBee; tự cập nhật bảo mật.
- Phi chức năng: chạy lại nhiều lần không hỏng (idempotent); cài xong không cần mạng lần 2; có log cài đặt.

## Architecture
- `onebee-install.sh`: kiểm tra đúng Mint 22.x amd64 → cài Ansible từ kho chuẩn → chạy playbook local.
- Roles Ansible (đã làm): `base` (vi_VN, Asia/Ho_Chi_Minh) · `vietnamese` (gói ngôn ngữ, ibus-bamboo; dự phòng ibus-unikey) · `fonts` · `office` · `theme` · `updates`.
- Bỏ khỏi v0.1 (YAGNI): role `apps` (Mint đã có sẵn trình duyệt, máy in CUPS), `backup-client` (làm cùng Box ở Phase 2).
- Font Microsoft (Arial, Times thật): chỉ đưa vào sau khi kiểm giấy phép ở Phase 0.

## Related Code Files
- Tạo: `desktop/onebee-install.sh`, `desktop/ansible/site.yml`, `desktop/ansible/roles/*`, `tests/desktop/`, `docs/huong-dan/cai-dat-desktop.md`

## Implementation Steps
1. Viết khung script + playbook; CI chạy trong ubuntu:24.04, chạy 2 lần kiểm idempotent.
2. Lần lượt từng role; mỗi role có kiểm tra (vd: `ibus list-engine` có bamboo).
3. Anh chạy trên VM Mint (Cinnamon + Xfce), rồi 1 máy cũ thật.
4. Thử 10 file Word/Excel/PowerPoint thật của HTX (anh gom) → ghi lỗi hiển thị vào `reports/`.

## Todo List
- [x] Script + khung playbook  - [x] 6 role  - [x] Test container: cài 2 lần (lần 2 changed=0), 31 mục PASS + 4 mục LibreOffice kiểm qua UNO; đã sửa theo code review
- [x] CI GitHub Actions
- [x] Test mở rộng (28/9): gõ Telex thật qua IBus (Bamboo + Unikey) trong màn hình ảo; file Word tiếng Việt → PDF;
      chính tả; chờ khóa dpkg; giữ LC_*; tự sửa cấu hình lệch; systemd thật; Ubuntu 24.04; chặn sai đầu vào
- [x] Sửa lỗi test phát hiện: Cambria → Noto Serif (Caladea thiếu chữ Việt); thiếu python3-debian trên Ubuntu gốc
- [ ] Chạy VM Mint 22.3 Cinnamon (phiên đăng nhập thật: thanh bộ gõ, hình nền, phím tắt)
- [ ] Chạy máy thật (ở đơn vị pilot)  - [ ] Test 10 file Office thật của HTX

## Success Criteria
- Người không rành máy: gõ được tiếng Việt, mở/sửa/lưu file .docx mẫu không vỡ bố cục, in được 1 trang — trên VM và 1 máy cũ.
- Playbook chạy lần 2 báo 0 thay đổi. Thời gian cài được đo và ghi lại (chưa đặt chỉ tiêu trước khi đo).

## Risk Assessment
- File có macro VBA/bảng phức tạp lệch bố cục → ghi rõ giới hạn, gợi ý giữ bản gốc.
- ibus-bamboo không cài được trên 22.3 → dùng fcitx5-unikey.

## Security Considerations
- Không cài từ nguồn trôi nổi; chỉ kho chính thức Ubuntu/Mint + PPA đã ghi trong ADR. Tài khoản người dùng không có quyền sudo mặc định.

## Next Steps
- Role `backup-client` bật ở Phase 2; lệnh `hoi` thêm ở Phase 3.
