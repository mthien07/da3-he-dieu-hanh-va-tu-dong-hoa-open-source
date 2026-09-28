# Phase 6 — Đóng gói dịch vụ bán được, release v1.0

## Context Links
- [plan.md](plan.md) · [phase-05](phase-05-mo-hinh-diem-tai-htx-onebee.md)

## Overview
- Ưu tiên: Trung bình · Trạng thái: Chưa bắt đầu · Dự kiến: tuần 14–16

## Requirements
- Tài liệu người dùng tiếng Việt có ảnh; 5 video hướng dẫn ngắn; checklist khảo sát khách.
- Bảng giá Starter/Business/Bảo trì tính lại từ chi phí thật của pilot.
- Mẫu hợp đồng triển khai + bảo trì (SLA) — cần người có chuyên môn pháp lý xem trước khi dùng.
- Demo web + README cập nhật số liệu thật từ `reports/`, gỡ hết số chưa có nguồn.
- Bảng giấy phép thành phần (OSI vs fair-code) đưa vào README.
- Release v1.0 trên GitHub: changelog, hướng dẫn cài, checksum.

## Related Code Files
- Tạo: `docs/huong-dan/*`, `docs/kinh-doanh/bang-gia.md`, `docs/kinh-doanh/mau-hop-dong-bao-tri.md`, `CHANGELOG.md`, `LICENSES.md`
- Sửa: `README.md`, `demo/index.html`

## Implementation Steps
1. Hoàn thiện tài liệu + video từ ghi chú pilot.
2. Tính lại giá; cập nhật mô hình hòa vốn trong hồ sơ thi bằng số thật.
3. Kiểm tra toàn bộ trên máy sạch (VM + máy cũ) theo hướng dẫn → sửa chỗ vướng.
4. Gắn tag v1.0.

## Todo List
- [ ] Tài liệu  - [ ] Video  - [ ] Bảng giá  - [ ] Mẫu hợp đồng  - [ ] Demo + README  - [ ] LICENSES.md  - [ ] Release v1.0

## Success Criteria
- Người ngoài đội làm theo tài liệu tự cài được Desktop + Box trên máy sạch.
- Mọi con số công bố đều truy ra được file đo trong `reports/`.

## Risk Assessment
- Giá tính lại cao hơn khung giá đã nói ở hội thi → trình bày minh bạch lý do (số thật).

## Security Considerations
- Release kèm checksum; không đóng gói khóa/mật khẩu mẫu dùng được thật.

## Next Steps
- Khách hàng đầu tiên ngoài OneBee; xét lại việc làm ISO riêng.
