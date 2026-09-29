# Chấm Trợ lý OneBee — 29/09/2026 — máy: Máy thử nghiệm đám mây (2 vCPU, 7GB RAM, không GPU)

> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,
> không dùng cho bảng giá/cấu hình tối thiểu.

Bộ câu hỏi: 40 câu × 3 lần. Lời dặn hệ thống: `box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md (chấm lại từ 260929-1022-cham-tro-ly-tra-loi.csv)`.

| Model | Kết luận | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:e2b-it-qat` | ✅ ĐẠT | 98% | 92% | 97% | 100% | 100% | 100% | 0 | 1 | 47.2s | 10.5 | ? GB |

Nhóm: N1 = Dùng máy OneBee; N2 = Soạn văn bản hành chính; N3 = Tóm tắt văn bản; N4 = Trích số liệu từ bảng; N5 = Phải nói "không biết" (không bịa)

## `gemma4:e2b-it-qat`

- ✅ Vượt mọi ngưỡng (còn phần chấm tay nhóm 2–3)

Câu chưa đạt (tối đa 15 dòng):

- `n1-02` lần 1: thiếu ['vieejt / v-i-e-e-j-t / v i e e j t']; phạm cấm —
- `n1-02` lần 3: thiếu ['vieejt / v-i-e-e-j-t / v i e e j t']; phạm cấm —
- `n2-01` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam']; phạm cấm —
- `n2-04` lần 1: thiếu ['5/5 / năm thành viên / 5 thành viên']; phạm cấm —
- `n2-04` lần 3: thiếu ['2 máy tính / hai máy tính']; phạm cấm —
- `n3-08` lần 1: thiếu —; phạm cấm ['(đến|-|–) ?(1 giờ 30 chiều|13 giờ 30|13h30|13:30)']
