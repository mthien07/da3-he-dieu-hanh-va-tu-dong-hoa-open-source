# Phase 5 — Mô hình điểm tại HTX OneBee

## Context Links
- [plan.md](plan.md) · Hồ sơ thi: "tháng 1 chạy mô hình điểm tại OneBee" (cẩm nang mục 2.3)

## Overview
- Ưu tiên: Cao · Trạng thái: 🔄 Công cụ + tài liệu chạy thử xong (30/9); chờ máy + anh chốt ngưỡng đạt để bắt đầu 4 tuần · Dự kiến: tuần 10–14 (4 tuần dùng thật)
- 2–5 máy + 1 Box tại chính HTX OneBee, dùng cho công việc thật; ≥ 3 người dùng (để khảo sát ẩn danh đo được).

## Key Insights
- Đây là nơi sinh ra số liệu thật để thay mọi con số "giả định" trong hồ sơ và demo.

## Requirements
- Trước khi cài: sao lưu nguyên ổ Windows (Clonezilla) → khôi phục được trong ngày nếu cần.
- Ghi nhận hằng tuần: số yêu cầu hỗ trợ, thời gian xử lý, file không mở được, phần mềm phải quay về Windows.
- Khảo sát hài lòng 5 câu cuối tuần 2 và tuần 4.
- Ghi chi phí thật: giờ công cài/đào tạo/hỗ trợ, phần cứng phải thay (SSD, RAM).

## Related Code Files
- Đã tạo (30/9): n8n quy trình 07 (báo cần hỗ trợ + email), 08 (kỹ thuật ghi xử lý, tài khoản `kythuat`), 09 (khảo sát ẩn danh);
  `onebee-box bao-cao-tuan` (`box-fleet/files/onebee-bao-cao-tuan.py`, không in tên/mô tả); mục menu "Báo cần hỗ trợ";
  `docs/huong-dan/chay-thu-tai-don-vi.md`, `dao-tao-buoi-1-3.md`, `to-phim-tat.md`; `reports/pilot/` (README, ngưỡng đề xuất, mẫu báo cáo).
- Sẽ tạo khi chạy thật: `reports/pilot/nhat-ky-tuan-*.md`, `reports/pilot/bao-cao-pilot.md`

## Implementation Steps
1. Khảo sát + sao lưu → cài → đào tạo 2–3 buổi (theo mô hình KD).
2. 4 tuần dùng thật; em tổng hợp nhật ký hằng tuần, sửa lỗi theo đợt.
3. Báo cáo pilot: số liệu thật, bài học, danh sách giới hạn.

## Todo List
- [x] Công cụ ghi yêu cầu hỗ trợ, khảo sát, nhật ký tuần  - [x] Giáo án 3 buổi, tờ phím tắt, quy trình chạy thử
- [ ] Anh chốt ngưỡng đạt (`reports/pilot/nguong-dat.md`)  - [ ] Sao lưu Windows  - [ ] Cài + đào tạo  - [ ] 4 nhật ký tuần
- [ ] 2 lần khảo sát  - [ ] Báo cáo pilot

## Success Criteria
- 4 tuần dùng thật, không mất dữ liệu; có báo cáo pilot với số đo thật.
- Ngưỡng "đạt" (9 tiêu chí, `reports/pilot/nguong-dat.md` v2) do anh chốt trước khi bắt đầu.

## Risk Assessment
- Người dùng phản ứng vì đổi thói quen → đào tạo, dán phím tắt, giữ 1 máy Windows dự phòng.
- Công việc gấp bị chậm → đường lui khôi phục Windows trong ngày.

## Security Considerations
- Dữ liệu thật của HTX: không đưa vào repo công khai; nhật ký pilot ẩn tên người, số liệu kế toán.

## Next Steps
- Số liệu pilot → cập nhật bảng giá, demo, slide (Phase 6).
