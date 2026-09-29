# Chấm Trợ lý OneBee — 29/09/2026 — máy: Máy thử nghiệm đám mây (2 vCPU, 7GB RAM, không GPU)

> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,
> không dùng cho bảng giá/cấu hình tối thiểu.

Bộ câu hỏi: 40 câu × 1 lần. Lời dặn hệ thống: bản TRƯỚC khi thêm mục "Soạn văn bản" (chấm lại từ 260929-0751-cham-tro-ly-tra-loi.csv)`.

| Model | Kết luận | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gemma3:1b` | ❌ KHÔNG ĐẠT | 44% | 25% | 42% | 54% | 0% | 100% | 0 | 0 | 0.5s | 15.9 | ? GB |
| `gemma4:e2b-it-qat` | ❌ KHÔNG ĐẠT | 95% | 88% | 88% | 100% | 100% | 100% | 0 | 1 | 43.9s | 10.8 | ? GB |
| `gemma3:4b` | ❌ KHÔNG ĐẠT | 90% | 75% | 76% | 100% | 100% | 100% | 0 | 1 | 9.2s | 4.6 | ? GB |

Nhóm: N1 = Dùng máy OneBee; N2 = Soạn văn bản hành chính; N3 = Tóm tắt văn bản; N4 = Trích số liệu từ bảng; N5 = Phải nói "không biết" (không bịa)

## `gemma3:1b`

- ❌ Ý bắt buộc chung 44% < 90%
- ❌ Nhóm 1 (Dùng máy OneBee) 25% < 85%
- ❌ Nhóm 2 (Soạn văn bản hành chính) 42% < 85%
- ❌ Nhóm 3 (Tóm tắt văn bản) 54% < 85%
- ❌ Nhóm 4 (Trích số liệu từ bảng) 0% < 85%

Câu chưa đạt (tối đa 15 dòng):

- `n1-01` lần 1: thiếu ['super', 'space']; phạm cấm —
- `n1-02` lần 1: thiếu ['vieejt / v-i-e-e-j-t / v i e e j t']; phạm cấm —
- `n1-05` lần 1: thiếu ['ctrl + p / ctrl+p / ctrl p']; phạm cấm —
- `n1-06` lần 1: thiếu ['sao lưu', 'quản trị']; phạm cấm —
- `n1-07` lần 1: thiếu ['smb://', 'chung']; phạm cấm —
- `n1-08` lần 1: thiếu ['không nên / không tắt / đừng tắt / không được tắt / chờ / đợi']; phạm cấm —
- `n2-01` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam', 'độc lập - tự do - hạnh phúc / độc lập – tự do – hạnh phúc', 'quý iii / quý 3']; phạm cấm —
- `n2-02` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam', 'nơi nhận']; phạm cấm —
- `n2-03` lần 1: thiếu ['thông báo', '2/9 / 02/09 / 2 tháng 9 / 02 tháng 9', '1/9 / 01/09 / 1 tháng 9 / 01 tháng 9']; phạm cấm —
- `n2-04` lần 1: thiếu ['5/5 / năm thành viên / 5 thành viên', '2 máy tính / hai máy tính']; phạm cấm —
- `n2-05` lần 1: thiếu ['tờ trình', '15.000.000 / 15 triệu / mười lăm triệu', 'máy in']; phạm cấm —
- `n2-06` lần 1: thiếu ['30/2020/nđ-cp / nghị định 30/2020 / nghị định số 30/2020']; phạm cấm —
- `n3-02` lần 1: thiếu ['kho lạnh', '50 m² / 50m² / 50 m2 / 50 mét vuông', 'bưởi']; phạm cấm —
- `n3-06` lần 1: thiếu ['1.000 đồng / 1000 đồng / 1.000đ / 1 nghìn / một nghìn', '7 ngày', 'thùng']; phạm cấm —
- `n3-07` lần 1: thiếu ['khoa', 'xe giao hàng / giao hàng', 'hạnh', 'khách hàng']; phạm cấm —

## `gemma4:e2b-it-qat`

- ❌ Tỉ lệ phạm ý cấm 2.5% > 2%

Câu chưa đạt (tối đa 15 dòng):

- `n1-02` lần 1: thiếu ['vieejt / v-i-e-e-j-t / v i e e j t']; phạm cấm —
- `n2-06` lần 1: thiếu ['30/2020/nđ-cp / nghị định 30/2020 / nghị định số 30/2020']; phạm cấm —
- `n3-08` lần 1: thiếu —; phạm cấm ['(đến|-|–) ?(1 giờ 30 chiều|13 giờ 30|13h30|13:30)']

## `gemma3:4b`

- ❌ Nhóm 1 (Dùng máy OneBee) 75% < 85%
- ❌ Nhóm 2 (Soạn văn bản hành chính) 76% < 85%
- ❌ Tỉ lệ phạm ý cấm 2.5% > 2%

Câu chưa đạt (tối đa 15 dòng):

- `n1-02` lần 1: thiếu ['vieejt / v-i-e-e-j-t / v i e e j t']; phạm cấm —
- `n1-05` lần 1: thiếu ['ctrl + p / ctrl+p / ctrl p']; phạm cấm —
- `n2-01` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam', 'độc lập - tự do - hạnh phúc / độc lập – tự do – hạnh phúc']; phạm cấm —
- `n2-02` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam', 'nơi nhận']; phạm cấm —
- `n2-06` lần 1: thiếu ['30/2020/nđ-cp / nghị định 30/2020 / nghị định số 30/2020']; phạm cấm —
- `n4-07` lần 1: thiếu —; phạm cấm ['ít nhất (là )?hộ sáu']
