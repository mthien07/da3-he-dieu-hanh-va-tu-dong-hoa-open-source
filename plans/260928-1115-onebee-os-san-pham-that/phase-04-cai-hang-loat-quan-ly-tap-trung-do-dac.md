# Phase 4 — Cài hàng loạt, quản lý tập trung, đo đạc

## Context Links
- [plan.md](plan.md) · [phase-01](phase-01-onebee-os-desktop-v01.md) · [phase-02](phase-02-onebee-box-may-chu-noi-bo-v01.md)

## Overview
- Ưu tiên: Cao (lõi của gói bảo trì) · Trạng thái: Chưa bắt đầu · Dự kiến: tuần 8–10

## Key Insights
- Hai cách cài: (a) cài Mint chuẩn + `onebee-install.sh` cho máy khác cấu hình; (b) Clonezilla chép ảnh đĩa cho lô máy giống nhau.
- Số liệu "trước/sau" chỉ có giá trị khi đo trên **cùng một máy** bằng cùng một cách.

## Requirements
- Từ Box: cập nhật toàn bộ máy trạm 1 lệnh; báo cáo 1 trang (máy nào chưa cập nhật/chưa sao lưu/ổ sắp đầy).
- Hỗ trợ từ xa trong LAN/qua Tailscale, người dùng phải bấm đồng ý.
- Bộ đo chuẩn: thời gian khởi động, RAM trống sau khởi động, thời gian mở LibreOffice/trình duyệt, dung lượng ổ còn trống.

## Architecture
- `fleet/inventory.yml` + playbook `cap-nhat.yml`, `bao-cao.yml` chạy từ Box qua SSH khóa riêng.
- Máy trạm: systemd timer gửi tình trạng về n8n → trang báo cáo.
- `tests/do-dac/do-may.sh`: chạy trên Windows cũ (đo tay theo checklist) và OneBee OS → CSV vào `reports/do-dac/`.

## Related Code Files
- Tạo: `fleet/*`, `tests/do-dac/*`, `docs/huong-dan/cai-hang-loat.md`, `docs/huong-dan/clonezilla.md`

## Implementation Steps
1. Playbook quản lý tập trung + timer báo tình trạng.
2. Quy trình Clonezilla: sao lưu nguyên ổ Windows trước khi cài (đường lui), ảnh chuẩn cho lô máy.
3. Công cụ hỗ trợ từ xa: chọn sau khi kiểm giấy phép (ghi vào ADR).
4. Đo trước/sau trên máy thật của đơn vị pilot (không có máy cũ riêng để thử).

## Todo List
- [ ] Playbook fleet  - [ ] Timer + báo cáo  - [ ] Quy trình Clonezilla  - [ ] Hỗ trợ từ xa  - [ ] Đo trước/sau trên máy đơn vị pilot

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
