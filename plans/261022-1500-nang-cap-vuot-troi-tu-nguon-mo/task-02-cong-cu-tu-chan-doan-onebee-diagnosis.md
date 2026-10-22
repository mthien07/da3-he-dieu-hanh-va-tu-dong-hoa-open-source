# Task 02 — Bộ công cụ Tự chẩn đoán lỗi OneBee Diagnosis (`onebee-box chan-doan`)

**Ưu tiên:** Cao (P1)  
**Trạng thái:** Sẵn sàng thực hiện  
**Cảm hứng thiết kế:** **YunoHost (`yunohost diagnosis`)** (Giải quyết bài toán kỹ thuật viên từ xa cần nắm bắt ngay sức khỏe hệ thống khi có sự cố).

---

## 1. Hiện trạng & Vấn đề thực tế

- Khi khách hàng báo sự cố (ví dụ: "AI không trả lời", "không lưu được file vào thư mục chung", "máy chạy chậm"), kỹ thuật viên phải gõ nhiều lệnh phân mảnh (`docker ps`, `df -h`, `free -m`, `systemctl status`, `tail -n 50...`) để dò lỗi.
- Người dùng tại chỗ không có công cụ tự kiểm tra để biết lỗi do đứt mạng LAN, router hay do Box.

---

## 2. Giải pháp kỹ thuật

### Bổ sung lệnh `onebee-box chan-doan` (và `onebee-chan-doan` trên máy trạm):
Xây dựng một script kiểm tra tự động chạy qua 7 hạng mục then chốt:

1. **Kết nối mạng & Gateway (Network):**
   - Ping kiểm tra Gateway router nội bộ (<5ms).
   - Kiểm tra kết nối Internet (DNS 1.1.1.1, 8.8.8.8) và mạng ảo Tailscale.
2. **Tài nguyên phần cứng (Resources):**
   - Dung lượng ổ đĩa phân vùng root `/` và dữ liệu `/data` (cảnh báo VÀNG nếu >80%, ĐỎ nếu >90%).
   - Tải CPU load average và RAM khả dụng (cảnh báo nếu RAM trống < 1.5 GB khiến Ollama crash).
3. **Trạng thái các container Docker (Services):**
   - Kiểm tra container `ollama`, `open-webui`, `n8n`, `rest-server` đang chạy (UP) và khỏe mạnh (healthy).
4. **Kiểm tra AI Model (AI Health):**
   - Gửi 1 prompt test ngắn `{"model": "gemma4:e2b-it-qat", "prompt": "test", "stream": false}` đến Ollama API (cổng 11434) đo thời gian phản hồi (chậm nếu >5s).
5. **Kiểm tra Thư mục chia sẻ (Samba):**
   - Xác nhận service `smbd` đang chạy và quyền ghi (write permission) trên `/data/chung`.
6. **Kiểm tra Bản sao lưu gần nhất (Backup Recency):**
   - Đọc snapshot mới nhất trong Restic repo; cảnh báo nếu không có snapshot nào trong vòng 26 giờ qua.
7. **Chứng chỉ bảo mật & Khóa (Security & SSL):**
   - Kiểm tra hạn dùng của chứng chỉ TLS nội bộ (cảnh báo nếu còn dưới 15 ngày).

### Định dạng đầu ra:
- **Chế độ dòng lệnh (CLI):** In ra bảng màu sắc nét (Xanh lá `[OK]`, Vàng `[CẢNH BÁO]`, Đỏ `[LỖI]`) với kết luận tổng thể và gợi ý hành động cụ thể bằng tiếng Việt.
- **Chế độ JSON (`--json`):** Trả về cấu trúc JSON để n8n hoặc dashboard Web hiển thị.

---

## 3. Các tệp cần sửa đổi & tạo mới

1. `box/scripts/onebee-box`: Thêm subcommand `chan-doan` gọi module chẩn đoán.
2. `box/scripts/modules/diagnosis.sh`: Logic kiểm tra 7 hạng mục.
3. `desktop/scripts/onebee-chan-doan`: Script kiểm tra nhanh trên máy trạm (kết nối tới Box, mount Samba, Restic client).
4. `tests/box/check-diagnosis.sh`: Bài kiểm thử tự động xác nhận script chẩn đoán chạy ra kết quả `OK` khi mọi dịch vụ đều sống, và báo `FAIL` chính xác khi giả lập tắt 1 dịch vụ.
