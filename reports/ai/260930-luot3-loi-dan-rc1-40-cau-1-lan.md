# Chấm Trợ lý OneBee — 30/09/2026 — máy: container thu nghiem 2 vCPU, khong GPU (khong phai may Box that)

> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,
> không dùng cho bảng giá/cấu hình tối thiểu.

Bộ câu hỏi: 40 câu × 1 lần. Lời dặn hệ thống: `box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md` (bản 1.0.0-rc.1: biết ngày hôm nay, soạn ngay văn bản, thư mục chung, chuỗi phím Telex).

| Model | Kết luận | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:e2b-it-qat` | ✅ ĐẠT | 98% | 94% | 94% | 100% | 100% | 100% | 0 | 0 | 47.1s | 10.4 | 3.9 GB |

Nhóm: N1 = Dùng máy OneBee; N2 = Soạn văn bản hành chính; N3 = Tóm tắt văn bản; N4 = Trích số liệu từ bảng; N5 = Phải nói "không biết" (không bịa)

## `gemma4:e2b-it-qat`

- ✅ Vượt mọi ngưỡng (còn phần chấm tay nhóm 2–3)

Câu chưa đạt (tối đa 15 dòng):

- `n1-06` lần 1: thiếu ['sao lưu']; phạm cấm —
- `n2-02` lần 1: thiếu ['cộng hòa xã hội chủ nghĩa việt nam / cộng hoà xã hội chủ nghĩa việt nam']; phạm cấm —
- `n2-04` lần 1: thiếu ['2 máy tính / hai máy tính']; phạm cấm —
