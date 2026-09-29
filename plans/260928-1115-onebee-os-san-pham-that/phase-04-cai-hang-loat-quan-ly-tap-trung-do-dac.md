# Phase 4 — Cài hàng loạt, quản lý tập trung, đo đạc

## Context Links
- [plan.md](plan.md) · [phase-01](phase-01-onebee-os-desktop-v01.md) · [phase-02](phase-02-onebee-box-may-chu-noi-bo-v01.md)

## Overview
- Ưu tiên: Cao (lõi của gói bảo trì) · Trạng thái: 🔄 Code + test container (29/9); còn làm thật: cài liền 3 máy, đo trước/sau trên máy đơn vị · Dự kiến: tuần 8–10

## Key Insights
- Hai cách cài: (a) cài Mint chuẩn + `onebee-install.sh` cho máy khác cấu hình; (b) Clonezilla chép ảnh đĩa cho lô máy giống nhau.
- Số liệu "trước/sau" chỉ có giá trị khi đo trên **cùng một máy** bằng cùng một cách.

## Requirements
- Từ Box: cập nhật toàn bộ máy trạm 1 lệnh; báo cáo 1 trang (máy nào chưa cập nhật/chưa sao lưu/ổ sắp đầy).
- Hỗ trợ từ xa trong LAN/qua Tailscale, người dùng phải bấm đồng ý.
- Bộ đo chuẩn: thời gian khởi động, RAM trống sau khởi động, thời gian mở LibreOffice/trình duyệt, dung lượng ổ còn trống.

## Architecture (đã làm — chi tiết ADR 0004)
- Máy trạm: timer `onebee-bao-tinh-trang` mỗi giờ → n8n (quy trình 06) → `/srv/onebee/tinh-trang-may/<tên>.json`.
- Box: `onebee-box may-tram` (bảng) + email 23:00 (quy trình 01) dùng chung `onebee-may-tram.py`; sao lưu lấy từ kho trên Box.
- Box: `onebee-box cap-nhat-may <tên>|--tat-ca` → playbook `cap-nhat-may-tram.yml` qua SSH (khóa riêng từng Box,
  tài khoản `onebee-quantri`, `from=<IP Box>`); kho máy lấy IP từ báo cáo ≤ 2 giờ, kiểm đúng tên máy trước khi cập nhật.
  (Không dùng `fleet/inventory.yml` cố định: IP máy trạm động.)
- Hỗ trợ từ xa: `onebee-ho-tro` (x11vnc theo yêu cầu, mã 1 lần + người dùng bấm Cho phép mỗi kết nối).
- `tests/do-dac/do-may.py` (Linux, tự đo + nhận số bấm giờ) → CSV `reports/do-dac/`; Windows đo tay theo `docs/huong-dan/do-truoc-sau.md`.

## Related Code Files
- Box: role `box-fleet` (mới), `box-n8n` (quy trình 06, khóa máy trạm), `box-stack` (lệnh `may-tram`, `cap-nhat-may`, `them-may` 9 dòng)
- Desktop: role `quan-ly-tap-trung`, `ho-tro-tu-xa` (mới), `backup-client` (đọc cấu hình 1 lần, chỉ nạp dòng RESTIC_), `ai-cli`
- Test: `tests/box/check-quan-ly-tap-trung.sh`, `tests/box/test_onebee_may_tram.py`, `tests/desktop/extended/check-ho-tro-tu-xa-inside.sh`
- Tài liệu: `docs/adr/0004-*`, `docs/huong-dan/quan-ly-may-tram.md`, `cai-hang-loat.md` (gồm Clonezilla), `do-truoc-sau.md`

## Implementation Steps
1. Playbook quản lý tập trung + timer báo tình trạng.
2. Quy trình Clonezilla: sao lưu nguyên ổ Windows trước khi cài (đường lui), ảnh chuẩn cho lô máy.
3. Công cụ hỗ trợ từ xa: chọn sau khi kiểm giấy phép (ghi vào ADR).
4. Đo trước/sau trên máy thật của đơn vị pilot (không có máy cũ riêng để thử).

## Todo List
- [x] Playbook cập nhật từ Box  - [x] Timer + báo cáo (lệnh + email)  - [x] Tài liệu Clonezilla/cài hàng loạt  - [x] Hỗ trợ từ xa
- [x] Bộ đo trước/sau  - [ ] Cài liền 3 máy thật, ghi thời gian  - [ ] Đo trước/sau trên máy đơn vị pilot  - [ ] Thử SSH/hỗ trợ từ xa trên máy thật

## Success Criteria
- Cài liền 3 máy theo quy trình, thời gian thực tế được ghi lại.
- Báo cáo tình trạng hiện đúng khi cố tình tắt sao lưu 1 máy.
- Có file CSV đo trước/sau — nguồn duy nhất cho số liệu trên slide/demo về sau.

## Risk Assessment
- Máy khác driver (wifi, máy in) → ghi danh sách phần cứng đã thử/không hỗ trợ.

## Security Considerations
- Khóa SSH riêng từng đơn vị, không dùng chung giữa khách; hỗ trợ từ xa phải có người dùng đồng ý.

## Next Steps
- Mang toàn bộ vào pilot Phase 5.
