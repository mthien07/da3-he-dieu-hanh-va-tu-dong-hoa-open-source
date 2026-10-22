# Task 04 — Kho Prompt Hành chính & Tri thức Nội bộ RAG (Retrieval Augmented Generation)

**Ưu tiên:** Trung bình (P2)  
**Trạng thái:** Sẵn sàng thực hiện  
**Cảm hứng thiết kế:** **Nextcloud Assistant / Dify / Open WebUI Pipelines** (Biến mô hình AI từ công cụ chat phiếm thành trợ lý đắc lực làm việc hành chính thật sự).

---

## 1. Hiện trạng & Vấn đề thực tế

- Mô hình `gemma4:e2b-it-qat` trên Box đã được cấu hình system prompt hành chính theo Nghị định 30/2020/NĐ-CP.
- Tuy nhiên:
  1. Người dùng văn phòng cơ sở thường gõ câu hỏi ngắn cụt lủn hoặc không biết cách ra lệnh (prompting).
  2. Khi hỏi về các quy định riêng của Hợp tác xã (Luật HTX 2023, điều lệ đơn vị, quy chế chi tiêu nội bộ), mô hình LLM thuần túy không có dữ liệu này nên trả lời chung chung hoặc suy đoán.

---

## 2. Giải pháp kỹ thuật

### Bước 1: Đóng gói Kho Mẫu Prompt Hành chính 1-Click (Prompt Presets)
Cấu hình sẵn trên Open WebUI (qua API hoặc SQLite database lúc khởi tạo stack):
- 📝 **Soạn Tờ trình / Công văn:** Điền sẵn khung thể thức chuẩn (Kính gửi, Căn cứ pháp lý, Nội dung đề xuất, Nơi nhận theo NĐ 30).
- 📑 **Lập Biên bản cuộc họp:** Khung ghi nhận thành phần tham dự, nội dung thảo luận, biểu quyết, kết luận.
- 📜 **Hợp đồng thu mua / liên kết nông sản:** Điều khoản thanh toán, quy cách chất lượng, trách nhiệm giao nhận.
- 📊 **Tóm tắt báo cáo tài chính / doanh thu quý:** Trích xuất các chỉ số doanh thu, chi phí, công nợ tồn đọng.

### Bước 2: Tích hợp Bộ tri thức cơ sở (Knowledge Base / Local RAG)
Tận dụng tính năng RAG tích hợp sẵn của Open WebUI:
- Tạo một Knowledge Collection mặc định tên là `Thu_Vien_Phap_Ly_HTX`:
  - Nạp sẵn file văn bản: *Luật Hợp tác xã số 17/2023/QH15*, *Nghị định 30/2020/NĐ-CP về công tác văn thư*.
- Cung cấp giao diện / thư mục để đơn vị tự thả các file PDF nội bộ (Quy chế hoạt động, Bảng giá dịch vụ, Hợp đồng mẫu) vào để AI tự lập chỉ mục vector (embedding chạy cục bộ trên Box).
- Khi nhân viên hỏi: *"Quy trình kết nạp thành viên mới HTX theo luật hiện hành thế nào?"*, AI sẽ trích xuất đúng điều khoản luật để trả lời kèm nguồn tham chiếu.

---

## 3. Các tệp cần sửa đổi & tạo mới

1. `box/ansible/roles/box-stack/tasks/setup-rag-prompts.yml`: Kịch bản nạp sẵn prompt templates và tài liệu pháp lý mẫu vào Open WebUI.
2. `box/assets/prompts/`: Thư mục lưu trữ các mẫu prompt Markdown tiếng Việt chuẩn.
3. `box/assets/knowledge/`: Các văn bản pháp quy cốt lõi dạng Markdown/PDF đã làm sạch.
4. `tests/box/check-rag-prompts.sh`: Bài kiểm thử tự động gọi API Open WebUI xác nhận các template prompt và collection tri thức đã được kích hoạt thành công.
