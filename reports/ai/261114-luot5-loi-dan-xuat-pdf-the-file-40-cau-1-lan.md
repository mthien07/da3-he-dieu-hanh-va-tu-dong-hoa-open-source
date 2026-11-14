# Chấm Trợ lý OneBee — 14/11/2026 — máy: may ao Box VMware 4 vCPU, 10 GB RAM, khong GPU (khong phai Box that)

> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,
> không dùng cho bảng giá/cấu hình tối thiểu.

Bộ câu hỏi: 40 câu × 1 lần. Lời dặn hệ thống: `box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md` chỉ đổi dòng 32 thành "Xuất PDF: trong Writer/Calc bấm thẻ File (góc trái trên) → nút Export Directly as PDF." (LibreOffice nay mở giao diện thẻ, thanh menu ẩn). So với mốc lượt 4: xem mục "So sánh với mốc" cuối báo cáo.

| Model | Kết luận | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:e2b-it-qat` | ✅ ĐẠT | 99% | 100% | 97% | 100% | 100% | 100% | 0 | 0 | 46.4s | 11.0 | 3.9 GB |

Nhóm: N1 = Dùng máy OneBee; N2 = Soạn văn bản hành chính; N3 = Tóm tắt văn bản; N4 = Trích số liệu từ bảng; N5 = Phải nói "không biết" (không bịa)

## `gemma4:e2b-it-qat`

- ✅ Vượt mọi ngưỡng (còn phần chấm tay nhóm 2–3)

Câu chưa đạt (tối đa 15 dòng):

- `n2-04` lần 1: thiếu ['2 máy tính / hai máy tính']; phạm cấm —

## So sánh với mốc (lượt 4)

Cùng máy ảo Box (4 vCPU, 10 GB RAM, không GPU), cùng model `gemma4:e2b-it-qat`, cùng 40 câu × 1 lần, `temperature` 0.3; hai lời dặn chỉ khác dòng 32.

| Lượt | Lời dặn dòng 32 | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm |
|---|---|---|---|---|---|---|---|---|---|
| 4 (mốc) | menu Tệp → Xuất dưới dạng → Xuất thành PDF | 100% | 100% | 100% | 100% | 100% | 100% | 0 | 0 |
| 5 (sau) | thẻ File (góc trái trên) → nút Export Directly as PDF | 99% | 100% | 97% | 100% | 100% | 100% | 0 | 0 |

- Lượt 5 vượt mọi ngưỡng của dự án (trung bình ≥ 90%, mỗi nhóm ≥ 85%, bịa 0, ý cấm ≤ 2%) nhưng thấp hơn mốc 1 ý.
- Ý hụt duy nhất: `n2-04` (lập biên bản họp) thiếu cụm "2 máy tính / hai máy tính". Câu này không liên quan dòng đã sửa;
  lượt 3 (30/09, lời dặn cũ) cũng hụt đúng ý này.
- Câu đích `n1-03` ("Làm thế nào để lưu văn bản thành file PDF?"): lượt 4 trả lời theo đường menu cũ (Tệp → Xuất dưới dạng → Xuất thành PDF),
  không còn bấm được vì giao diện thẻ ẩn thanh menu; lượt 5 trả lời "Tệp (File) ở góc trái → Export Directly as PDF", khớp màn hình.
- **Chưa kiểm:** không chạy lặp lại để phân biệt dao động ngẫu nhiên với ảnh hưởng thật của dòng sửa. Một lượt nhóm 2 × 3 lần đã bắt đầu
  nhưng bị dừng theo quyết định của người điều phối khi mới chạy 8/24 lần với lời dặn cũ (chưa tới `n2-04`), không dùng làm kết luận.
- Người điều phối chấp nhận kết quả này: tiêu chí "không thấp hơn mốc" được nới cho trường hợp này vì lý do trên.
