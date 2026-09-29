# Phase 3 — Trợ lý AI tiếng Việt + workflow n8n mẫu

## Context Links
- [plan.md](plan.md) · [phase-02](phase-02-onebee-box-may-chu-noi-bo-v01.md) · ADR 0002 · [research](research/phase-03-model-ai-va-open-webui.md)
- n8n license FAQ: https://support.n8n.io/article/can-i-use-your-license-for-my-use-case

## Overview
- Ưu tiên: Cao · Trạng thái: Đã lên plan (29/9), chờ anh chốt 4 câu hỏi cuối file · Dự kiến: tuần 6–8
- Mục tiêu: AI trên Box **trả lời đúng, có ích cho HTX**, chọn bằng số đo (không chọn theo cảm tính);
  máy trạm hỏi được bằng lệnh `hoi`; 3–4 quy trình tự động chạy sẵn trên n8n.

## Key Insights
- Test Box 28/9: model 0.5b hỏi "Thủ đô Việt Nam?" 9 lần: 7 đúng, 2 sai ("TP. Hồ Chí Minh"), có lần bịa số liệu
  → model nhỏ không dùng được cho người dùng; phải chấm bằng bộ câu hỏi thật.
- Ứng viên trên Ollama (kích thước tải, theo trang Ollama 29/9): `qwen3.5:4b` 3.4GB, `qwen3.5:9b` 6.6GB,
  `gemma4:12b` 7.6GB, cùng các đời trước `qwen3`, `gemma3`, `llama3.1:8b`. **Chưa có số đo tiếng Việt nào** — chưa chọn.
- Open WebUI v0.11.4 (đã đọc mã nguồn trong image): có `WEBUI_ADMIN_EMAIL/PASSWORD` (tạo sẵn quản trị + tự tắt đăng ký →
  hết rủi ro "ai mở trước thành quản trị"), `ENABLE_API_KEYS` (mặc định tắt), `API_KEYS_ALLOWED_ENDPOINTS` (giới hạn khóa API).
- Giữ quyết định ADR 0002: **không mở API Ollama ra LAN**. Lệnh `hoi` gọi qua Open WebUI (có khóa API, có nhật ký).
- Trợ lý chỉ **gợi ý**, không tự chạy lệnh trên máy người dùng.

## Các bước (làm theo thứ tự)

### 3A. Bộ câu hỏi chấm điểm tiếng Việt (em soạn, anh duyệt)
- 40 câu, 5 nhóm × 8 câu: (1) dùng máy OneBee (gõ dấu, in, PDF, thư mục chung, sao lưu); (2) soạn văn bản hành chính
  (công văn, thông báo, biên bản — đúng thể thức); (3) tóm tắt / trích ý văn bản dài; (4) trích số liệu từ bảng;
  (5) **câu không biết** — phải nói "không biết/không chắc", không bịa.
- Mỗi câu: đáp án mẫu + ý bắt buộc (từ khóa) + ý cấm (sai hay gặp). Lưu `tests/ai/bo-cau-hoi-tieng-viet.yaml`.

### 3B. Công cụ chấm (chạy được trên máy nào cũng được)
- `tests/ai/cham-diem-model.py`: gọi từng model qua Ollama, ghi câu trả lời, **thời gian chờ chữ đầu, tốc độ chữ/giây,
  RAM**; chấm tự động theo ý bắt buộc/ý cấm → xuất `reports/ai/<ngày>-<máy>.md` + CSV.
- Phiếu chấm tay (CSV) để anh chấm lại câu nhóm 2–3 (máy không chấm được văn phong).
- Kiểm trong CI với model nhỏ nhất (chỉ kiểm công cụ chạy đúng, không kiểm chất lượng).

### 3C. Chấm model và chọn (cần máy Box thật — xem câu hỏi 1)
- Chạy 3B trên phần cứng Box thật với 4–6 ứng viên vừa RAM/VRAM. Ghi bảng: model × điểm × tốc độ × RAM.
- Chọn **1 model mặc định + 1 model nhẹ dự phòng**; ghi ADR 0003. Ngưỡng đạt đề xuất (anh chốt):
  ≥ 80% ý bắt buộc, 0 câu bịa ở nhóm 5, ≤ 10 giây ra chữ đầu.
- Đưa model đã chọn vào `onebee_box_ai_models` → bộ cài tự tải.

### 3D. Open WebUI dùng thật cho đơn vị
- Bộ cài tạo sẵn tài khoản quản trị (`WEBUI_ADMIN_*`, mật khẩu sinh ngẫu nhiên, xem bằng `onebee-box in-khoa`) → tắt đăng ký tự do.
- Lời nhắc hệ thống tiếng Việt mặc định: xưng hô, trả lời ngắn, nói rõ khi không chắc, không bịa số liệu.
- (Tùy chọn, nếu 3C cho thấy cần) Kho tri thức: nạp hướng dẫn OneBee + văn bản mẫu của HTX để AI trả lời dựa vào tài liệu.

### 3E. Lệnh `hoi` trên máy trạm
- `hoi "cách xuất file PDF"` → gọi Open WebUI (khóa API riêng từng máy, chỉ cho phép endpoint hỏi đáp) → in câu trả lời.
- Python thư viện chuẩn, không cần cài thêm. Box tắt → báo dễ hiểu. Không gửi gì ra Internet.
- Cấp khóa: mở rộng `onebee-box them-may` → in thêm `HOI_API_KEY`; role Desktop mới `ai-cli` cài lệnh khi có khóa.
- Test: máy trạm Mint (container) hỏi Box thật trong test Docker lồng.

### 3F. Workflow n8n mẫu (3–4 cái, nhập sẵn khi cài)
| # | Workflow | Kích hoạt | Kết quả |
|---|---|---|---|
| 1 | Báo cáo sao lưu | `onebee-box sao-luu` gọi webhook sau mỗi lần chạy | Tin nhắn "đã sao lưu / LỖI" |
| 2 | Máy trạm quá 3 ngày chưa sao lưu | Hằng ngày 8:00, Box gửi danh sách thời điểm sao lưu cuối | Cảnh báo tên máy |
| 3 | Tóm tắt văn bản bằng AI nội bộ | Biểu mẫu n8n: tải PDF/DOCX lên | Bản tóm tắt 5 ý (AI chạy trên Box) |
| 4 | (anh chọn — câu hỏi 3) | | |
- Kênh báo: xem câu hỏi 2. Workflow lưu JSON trong `box/ansible/roles/box-n8n/files/`, bộ cài nhập bằng `n8n import:workflow`.
- Tạo sẵn tài khoản chủ n8n + tài khoản Uptime Kuma lúc cài (nếu làm được qua CLI/API — kiểm ở bước này).

## Related Code Files
- Tạo: `tests/ai/*`, `reports/ai/*`, `docs/adr/0003-chon-model-ai.md`, `desktop/ansible/roles/ai-cli/*`,
  `box/ansible/roles/box-n8n/*`, `docs/huong-dan/dung-tro-ly-ai.md`
- Sửa: `box/.../docker-compose.yml.j2` (WEBUI_ADMIN_*, ENABLE_API_KEYS…), `onebee-box.sh.j2` (them-may cấp khóa AI,
  webhook sau sao lưu), `group_vars` (model mặc định), `tests/box/*`

## Success Criteria
- Có bảng điểm ≥ 4 model đo trên máy Box thật; model chọn đạt ngưỡng anh chốt; ADR 0003 ghi lý do.
- `hoi` trả lời từ máy trạm qua Box trong test tự động; tắt Box → báo lỗi dễ hiểu.
- 3 workflow chạy được trên Box sạch ngay sau khi cài (test tự động kích hoạt và kiểm kết quả).
- Không còn bước "ai mở trước thành quản trị" với Open WebUI.

## Risk Assessment
- Không có máy Box thật → 3C không làm được; 3A, 3B, 3D, 3E, 3F vẫn làm được (test bằng model nhỏ).
- Model tốt nhất có thể quá chậm trên CPU → chọn model nhẹ hơn hoặc ghi rõ cấu hình tối thiểu có GPU vào bảng giá.
- AI vẫn có thể sai → giao diện và `hoi` luôn ghi "AI có thể sai, kiểm tra lại số liệu quan trọng".
- Kênh Telegram/email cần Internet; Zalo OA cần đăng ký doanh nghiệp → bắt đầu bằng kênh đơn giản nhất.

## Security Considerations
- Khóa API mỗi máy trạm chỉ gọi được endpoint hỏi đáp (`API_KEYS_ALLOWED_ENDPOINTS`); thu hồi được từng khóa.
- Câu hỏi/văn bản không rời LAN (trừ tin nhắn cảnh báo nếu chọn Telegram/email — chỉ gửi trạng thái, không gửi nội dung).
- Webhook n8n chỉ nhận từ Box (có mã bí mật trong header).

## Câu hỏi cần anh chốt
1. **Máy Box thật để chấm model**: máy nào, RAM bao nhiêu, có card đồ họa (GPU) không? Chưa có thì em làm 3A–3F trước.
2. **Kênh nhận cảnh báo**: Telegram (dễ nhất), email, hay Zalo (khó hơn, cần Zalo OA)?
3. **Workflow thứ 4** HTX cần nhất: nhắc hạn nộp báo cáo/thuế/BHXH, tổng hợp đơn hàng, hay việc khác?
4. **Ngưỡng đạt** cho model: dùng ngưỡng đề xuất ở 3C hay anh muốn chặt/lỏng hơn?
