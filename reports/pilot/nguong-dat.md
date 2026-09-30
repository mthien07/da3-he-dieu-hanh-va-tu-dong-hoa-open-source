# Ngưỡng "đạt" của đợt chạy thử

Trạng thái: **ĐỀ XUẤT v2 (30/9) — chờ anh chốt** (chốt trước ngày cài máy đầu tiên; sau khi bắt đầu không sửa).
Các con số (4 giờ, 4/5, 72 giờ) là đề xuất, chưa có số liệu thật làm căn cứ — anh chỉnh theo thực tế đơn vị rồi mới chốt.

## Điều kiện bắt đầu
- Ít nhất **3 người dùng** (dưới 3 người thì khảo sát ẩn danh không hiện điểm → không đo được tiêu chí khảo sát).
- Có danh sách **việc bắt buộc** của từng người (lấy từ khảo sát trước khi cài: hóa đơn điện tử, chữ ký số, in, quét,
  phần mềm kế toán…), ghi rõ việc nào làm trên OneBee OS, việc nào làm trên **máy Windows dự phòng** đã thống nhất trước.
- Đo "trước" trên từng máy theo `docs/huong-dan/do-truoc-sau.md`.

## Tiêu chí
| # | Tiêu chí | Ngưỡng | Nguồn số liệu | Loại |
|---|---|---|---|---|
| 1 | Mất dữ liệu | 0 lần, **và** `sudo onebee-box khoi-phuc-thu` ĐẠT ở cuối tuần 2 và tuần 4 | Nhật ký tuần (ghi tay) + lệnh | Bắt buộc |
| 2 | Sao lưu đều | Mọi cảnh báo sao lưu máy trạm ("quá 3 ngày chưa sao lưu", "lỗi") trong email báo cáo sao lưu hằng đêm của Box được xử lý trong 1 ngày làm việc; lúc tổng hợp tuần, mọi máy có bản sao lưu ≤ 72 giờ | Email 23:00 của Box + `bao-cao-tuan` (tuổi bản sao lưu từng máy) | Bắt buộc |
| 3 | Việc bắt buộc | 100% việc trong danh sách làm được (trên OneBee OS hoặc máy Windows dự phòng như đã thống nhất) | Ghi tay | Bắt buộc |
| 4 | Quay về Windows vì lỗi OneBee | 0 máy. Phần mềm đã ghi trong danh sách "làm trên máy Windows dự phòng" không tính | `bao-cao-tuan` dòng "Đã phải quay về Windows" + ghi tay | |
| 5 | Yêu cầu hỗ trợ | Tuần 4 ≤ 1 yêu cầu/máy/tuần **hoặc** giảm ≥ 50% so với tuần 1 | `bao-cao-tuan` dòng "Mới trong tuần" | |
| 6 | Yêu cầu gấp | 100% có phản hồi và cách làm tiếp trong 4 giờ làm việc | `bao-cao-tuan` dòng "Gấp có phản hồi trong 4 giờ làm việc" | |
| 7 | File công việc | 0 file bị hỏng; file mở lệch bố cục đều có cách xử lý ghi lại | Ghi tay | |
| 8 | Khảo sát cuối tuần 4, câu 5 "muốn tiếp tục dùng" | Trung bình ≥ 4/5 **và** không phiếu nào ≤ 2 | `bao-cao-tuan` bảng khảo sát (cột "Số phiếu ≤ 2") | |
| 9 | Tốc độ | Khởi động và mở ứng dụng không chậm hơn "trước" (trung vị các lần đo) | `tests/do-dac/do-may.py` trước/sau | |

72 giờ (không phải 48) vì máy tắt từ chiều thứ Bảy đến sáng thứ Hai đã ~40–60 giờ; đúng bằng ngưỡng cảnh báo sẵn có của
`onebee-box may-tram`. Giờ làm việc dùng để tính tiêu chí 6: thứ Hai–thứ Bảy, 7:30–11:30 và 13:30–17:00 (đặt ở đầu file
`box/ansible/roles/box-fleet/files/onebee-bao-cao-tuan.py`, sửa nếu đơn vị làm giờ khác). "Phản hồi" = lần đầu kỹ thuật ghi
xử lý trên biểu mẫu `onebee-xu-ly` (kể cả ghi "Chưa xử lý được" kèm cách làm tạm).

## Cách kết luận
- **Dừng ngay** nếu mất dữ liệu (tiêu chí 1): khôi phục cho người dùng trước, tìm nguyên nhân, sửa xong mới chạy lại từ đầu.
- **Không đạt**: hỏng 1 tiêu chí bắt buộc (1–3), hoặc hỏng từ 2 tiêu chí còn lại trở lên.
- **Đạt có điều kiện**: chỉ hỏng 1 tiêu chí trong 4–9, có nguyên nhân rõ và cách sửa trước khi bán cho khách khác.
- **Đạt**: qua hết 9 tiêu chí.

Ngày chốt: ____ · Người chốt: ____
