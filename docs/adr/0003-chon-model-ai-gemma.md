# ADR 0003 — Chọn model AI cho Trợ lý OneBee

- Ngày: 29/9/2026 · Trạng thái: Chốt **có điều kiện** — còn đo tốc độ trên máy Box thật và anh chấm tay nhóm 2–3

## Bối cảnh
Anh chốt 29/9: dùng dòng **Gemma của Google**, ưu tiên **gọn nhẹ**, ngưỡng chất lượng **chặt**
(mỗi câu 3 lần; ý bắt buộc ≥ 90% chung và ≥ 85% mỗi nhóm; 0 lần bịa ở nhóm "phải nói không biết"; 0 ý cấm ở nhóm 1–2,
tổng ý cấm ≤ 2%; trên Box thật: chữ đầu ≤ 5 giây, ≥ 8 token/giây). Bộ 40 câu: `tests/ai/bo-cau-hoi-tieng-viet.yaml`.

## Kết quả chấm (máy thử đám mây 2 vCPU, 7 GB RAM, không GPU — tốc độ KHÔNG đại diện)
| Model | Tải | Lượt | Ý bắt buộc | N1 máy | N2 văn bản | N3 tóm tắt | N4 số liệu | N5 bịa | Ý cấm | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| `gemma3:1b` | 0,8 GB | 1 lần | 44% | 25% | 42% | 54% | 0% | 0 | 0 | ❌ từ chối gần như mọi câu |
| `gemma3:4b` | 3,3 GB | 1 lần | 90% | 75% | 76% | 100% | 100% | 0 | 1 | ❌ (vd: bảo in bằng "Super + P", sai hộ giao ít nhất) |
| `gemma4:e2b-it-qat` | 4,3 GB | 1 lần* | 95% | 88% | 88% | 100% | 100% | 0 | 1 | ❌ sát ngưỡng |
| **`gemma4:e2b-it-qat`** | 4,3 GB | **3 lần** | **98%** | **92%** | **97%** | 100% | 100% | **0** | 1/120 | ✅ **ĐẠT** |

\* lượt 1 dùng lời dặn cũ; lượt 2 thêm mục "Soạn văn bản" (thể thức theo Nghị định 30/2020/NĐ-CP, không tự thêm năm).
Chi tiết + toàn bộ câu trả lời: `reports/ai/260929-*`. Bộ chấm được sửa 4 chỗ chấm oan (ngày viết "10 tháng 10 năm 2026",
"4 giờ 30 chiều", "không được tắt", công thức `$7$ hộ`) và thêm 1 ý cấm (nghỉ trưa sai giờ) — áp dụng như nhau cho mọi model.

## Quyết định
- Model mặc định: **`gemma4:e2b-it-qat`** — bản Gemma nhẹ nhất vượt ngưỡng; Gemma 4 dùng giấy phép **Apache-2.0**
  (model card của Google), thuận lợi khi bán dịch vụ hơn Gemma 3 ("Gemma Terms of Use"). Nạp vào RAM ≈ 3,9 GB.
- Chưa chọn model dự phòng nhẹ hơn: `gemma3:1b` không dùng được, `gemma3:4b` không đạt.

## Điểm yếu còn thấy (phải kiểm lại sau mỗi lần đổi model / lời dặn)
- Hướng dẫn gõ Telex chữ "Việt" sai 2/3 lần (thiếu phím `j`, có lần nói `dd` ra "ệ") dù lời dặn có ví dụ.
- 1/3 lần viết thiếu "VIỆT NAM" trong Quốc hiệu; 1/3 lần tóm tắt sai giờ nghỉ trưa (13 giờ → "1 giờ 30 chiều").
- Model "suy nghĩ" trước khi trả lời → chờ chữ đầu ~47 giây trên máy thử (CPU yếu). Trên Box thật phải đo lại;
  không đạt ≤ 5 giây thì thử tắt chế độ suy nghĩ hoặc chọn máy có GPU.

## Việc còn lại trước khi chốt hẳn
1. Chạy `tests/ai/cham-diem-model.py --may-box-that` trên máy Box thật (đo tốc độ).
2. Anh chấm tay phiếu `reports/ai/260929-luot2-gemma4-e2b-3-lan-phieu-cham-tay.csv` (nhóm 2–3, điểm 1–5, cần ≥ 4).
3. Kiểm giấy phép Gemma 4 trên trang chính thức trước khi ghi vào hợp đồng dịch vụ.
