# Phase 3 — Trợ lý AI tiếng Việt + workflow n8n mẫu

## Context Links
- [plan.md](plan.md) · n8n license FAQ: https://support.n8n.io/article/can-i-use-your-license-for-my-use-case

## Overview
- Ưu tiên: Trung bình · Trạng thái: Chưa bắt đầu · Dự kiến: tuần 6–8

## Key Insights
- Chưa chọn model trước: chấm thử bằng bộ câu hỏi tiếng Việt thật trên phần cứng Box thật.
- Trợ lý chỉ **gợi ý**, không tự chạy lệnh trên máy người dùng.

## Requirements
- Lệnh `hoi "cách gõ dấu"` trên máy trạm → trả lời tiếng Việt, ngắn, từng bước; không cần mạng Internet.
- Bộ 30 câu hỏi kiểm thử (gõ dấu, in, xuất PDF, chia sẻ file, sao lưu…) + đáp án chuẩn.
- 3–5 workflow n8n: báo cáo sao lưu hằng ngày; cảnh báo máy trạm quá 3 ngày chưa sao lưu/cập nhật; tóm tắt văn bản PDF bằng AI nội bộ; (chốt thêm với anh theo nhu cầu HTX).

## Architecture
- `ai-cli/hoi`: Python chỉ dùng thư viện chuẩn, gọi Ollama API trên Box; system prompt tiếng Việt về Mint/LibreOffice; timeout + thông báo lỗi dễ hiểu khi Box tắt.
- Workflow lưu dạng JSON trong `workflows/`, script import 1 lệnh.

## Related Code Files
- Tạo: `ai-cli/hoi`, `ai-cli/system-prompt-vi.md`, `tests/ai/bo-30-cau-hoi.yaml`, `tests/ai/cham-diem.py`, `workflows/*.json`, `workflows/import.sh`
- Sửa: role `apps` (Phase 1) cài `hoi`

## Implementation Steps
1. Viết bộ 30 câu + đáp án (anh duyệt).
2. Chấm 3–4 model mở trên Box: độ đúng + thời gian trả lời → chọn model, ghi vào `reports/`.
3. Viết `hoi` + test; thêm vào Desktop.
4. Viết workflow, test trên Box.

## Todo List
- [ ] Bộ câu hỏi  - [ ] Chấm model  - [ ] Lệnh `hoi`  - [ ] 3–5 workflow  - [ ] Hướng dẫn sử dụng

## Success Criteria
- Model được chọn đạt ngưỡng đúng anh chốt trên bộ 30 câu; thời gian trả lời được đo và ghi lại.
- Workflow import và chạy được trên Box sạch.

## Risk Assessment
- AI trả lời sai → ghi rõ "trợ lý có thể sai", kèm đường dẫn tài liệu chuẩn.
- Gửi cảnh báo qua Zalo cần tài khoản OA → bắt đầu bằng Telegram hoặc email, Zalo làm sau.

## Security Considerations
- Câu hỏi và dữ liệu không rời LAN; không gửi lên AI đám mây. Log câu hỏi lưu cục bộ, có hạn xóa.

## Next Steps
- Phase 4 dùng n8n để gom báo cáo tình trạng toàn bộ máy.
