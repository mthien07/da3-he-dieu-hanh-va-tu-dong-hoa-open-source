# Chấm Trợ lý OneBee — 14/11/2026 — máy: may ao Box VMware 4 vCPU, 10 GB RAM, khong GPU (khong phai Box that)

> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,
> không dùng cho bảng giá/cấu hình tối thiểu.

Bộ câu hỏi: 40 câu × 1 lần. Lời dặn hệ thống: `box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md` bản trước khi sửa dòng xuất PDF (SHA-256 `73b9a6f7…`; dòng 32: "Xuất PDF: trong Writer/Calc chọn menu Tệp → Xuất dưới dạng → Xuất thành PDF."). Mốc so sánh cho lượt 5, cùng máy, model, bộ câu.

| Model | Kết luận | Ý bắt buộc | N1 | N2 | N3 | N4 | N5 | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:e2b-it-qat` | ✅ ĐẠT | 100% | 100% | 100% | 100% | 100% | 100% | 0 | 0 | 40.4s | 12.4 | 3.9 GB |

Nhóm: N1 = Dùng máy OneBee; N2 = Soạn văn bản hành chính; N3 = Tóm tắt văn bản; N4 = Trích số liệu từ bảng; N5 = Phải nói "không biết" (không bịa)

## `gemma4:e2b-it-qat`

- ✅ Vượt mọi ngưỡng (còn phần chấm tay nhóm 2–3)
