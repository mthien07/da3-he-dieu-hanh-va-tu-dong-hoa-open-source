# Task 05 — Cảnh báo Sự cố Chủ động qua Telegram / Webhook n8n

**Ưu tiên:** Trung bình (P2)  
**Trạng thái:** Sẵn sàng thực hiện  
**Cảm hứng thiết kế:** **Synology DSM / TrueNAS Alerts** (Hệ thống tự động thông báo trước khi sự cố biến thành thảm họa).

---

## 1. Hiện trạng & Vấn đề thực tế

- OneBee Box chạy tự động ở góc văn phòng không có màn hình hiển thị.
- Nếu xảy ra các lỗi nghiêm trọng như:
  - Ổ cứng lưu trữ bị đầy (>90%).
  - Sao lưu 12h trưa của máy kế toán bị lỗi (máy tắt hoặc mạng kẹt).
  - Dịch vụ AI hoặc Samba bị dừng đột ngột.
  - Quá nhiệt CPU (trên các mini PC tải nặng).
- Người dùng không hề hay biết cho đến khi dữ liệu bị mất hoặc máy trạm không làm việc được.

---

## 2. Giải pháp kỹ thuật

### Tích hợp Workflow Giám sát & Bắn Cảnh báo trên n8n:
Xây dựng workflow tự động chạy theo lịch trình (cron) trên n8n nội bộ:

1. **Báo cáo Sao lưu Định kỳ (Daily Backup Digest):**
   - Chạy lúc **12:30 trưa mỗi ngày** (sau chu kỳ sao lưu trưa).
   - Đọc kết quả log `rest-server` / `onebee-sao-luu`.
   - Nếu toàn bộ máy sao lưu thành công ➔ Bắn thông báo xanh:
     > `✅ [OneBee Box - HTX Long An] Sao lưu trưa 22/10 hoàn tất: 5/5 máy trạm an toàn (Đã lưu 1.2 GB dữ liệu mới).`
   - Nếu có máy trượt sao lưu ➔ Bắn cảnh báo đỏ:
     > `⚠️ [CẢNH BÁO SAO LƯU] Máy Ke-Toan-01 chưa hoàn tất sao lưu trưa nay! Đề nghị kiểm tra máy có đang bật và cắm dây mạng không.`
2. **Cảnh báo Sức khỏe Phần cứng Khẩn cấp (Immediate Alerts):**
   - Quét định kỳ mỗi giờ:
     - Dung lượng phân vùng `/data` > 85%: Gửi tin nhắn thông báo dọn dẹp ổ đĩa.
     - Dung lượng > 95%: Bắn cảnh báo khẩn cấp (Emergency) kèm nút tạm ngưng nhận file dung lượng lớn.
3. **Kênh nhận tin nhắn:**
   - Hỗ trợ cấu hình nhanh:
     - **Telegram Bot** (Miễn phí, cực kỳ dễ tạo và bảo mật).
     - **Zalo OA / Zalo Webhook** (kết nối qua API n8n).
     - **Email quản trị viên** (qua SMTP máy chủ).

---

## 3. Các tệp cần sửa đổi & tạo mới

1. `box/ansible/roles/box-stack/templates/workflows/onebee-alerts-workflow.json.j2`: Workflow n8n xuất mẫu.
2. `box/scripts/modules/alert.sh`: Script gửi cảnh báo từ dòng lệnh (cho cron và script chẩn đoán gọi).
3. `box/docs/huong-dan/cai-dat-thong-bao-telegram.md`: Tài liệu hướng dẫn 3 bước tạo bot Telegram cho HTX.
4. `tests/box/check-alerts.sh`: Test giả lập bắn cảnh báo vào webhook mock server xác nhận payload định dạng chuẩn tiếng Việt.
