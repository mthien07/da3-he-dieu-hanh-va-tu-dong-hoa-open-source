# Task 04 — Kế hoạch kiểm thử máy thật & Chuẩn bị phát hành v1.0.0

**Ưu tiên:** Cao (Sau khi hoàn tất Task 01–03)  
**Trạng thái:** Chờ nghiệm thu thực địa  
**Căn cứ:** `docs/kiem-thu-tren-may-that.md` (Nhóm B, C, D, E) và `docs/huong-dan/thu-nghiem-tren-may-ao.md`.

---

## 1. Mục tiêu

Đưa OneBee OS từ trạng thái "đã kiểm thử container" sang "đã nghiệm thu trên phần cứng và môi trường mạng thực tế", ghi nhận số liệu đo đạc khách quan vào thư mục `reports/`, hoàn tất các tiêu chí để gắn thẻ phát hành chính thức **v1.0.0**.

---

## 2. Kế hoạch kiểm thử thực địa (Theo nhóm B–E)

### Nhóm B: Kiểm thử Box trên máy chủ thực tế
- **Cài đặt Ubuntu Server 24.04 chuẩn trên máy Box:**
  - Chạy playbook `site.yml` với IP tĩnh và `onebee_box_ma_don_vi`.
  - Kiểm tra chạy lại lần 2: Đảm bảo `changed=0 failed=0`.
- **Đo đạc hiệu năng AI thực tế:**
  - Chạy mô hình sản phẩm `gemma4:e2b-it-qat` trên Ollama.
  - Đo tốc độ phản hồi (token/giây), mức chiếm dụng RAM/VRAM và CPU khi 1 máy, 3 máy và 5 máy trạm cùng gửi truy vấn qua lệnh `hoi`.
  - Lưu kết quả vào `reports/ai/do-dac-toc-do-box-that.md`.
- **Kiểm tra kho lưu trữ & ổ sao lưu gắn ngoài:**
  - Gắn ổ USB / HDD di động làm ổ sao lưu `BACKUP_MOUNT`.
  - Chạy thử sao lưu và khôi phục dữ liệu thực tế.

### Nhóm C: Kiểm thử máy trạm Linux Mint thực tế (Desktop)
- **Môi trường đồ họa Cinnamon:**
  - Cài đặt trên máy tính văn phòng thực tế chạy Linux Mint 22.x.
  - Kiểm tra bộ gõ tiếng Việt IBus Bamboo trong LibreOffice, trình duyệt Firefox và terminal.
  - Kiểm tra phím tắt và menu tiện ích OneBee (`hoi`, báo tình trạng, yêu cầu hỗ trợ).
  - Kiểm tra Firefox: Xác nhận CA OneBee được nhận diện tự động và ghim đúng ràng buộc tên miền.

### Nhóm D: Thiết bị ngoại vi & mạng hỗn hợp
- **Windows 10 / 11 trong cùng mạng LAN:**
  - Kết nối chia sẻ Samba qua giao thức SMB 3.1.1 có mã hóa.
  - Cài đặt thủ công file chứng chỉ `http://<IP-Box>/onebee-ca.crt` vào Trusted Root Certification Authorities trên Windows và truy cập `https://<IP-Box>:3000`.
- **Máy in LAN:** Xác nhận việc cài đặt CA và tường lửa Box không gây cản trở kết nối tới máy in nội bộ.

### Nhóm E: Kịch bản phục hồi thảm họa
- **Giả lập hỏng ổ đĩa Box:** Cài đặt lại hệ điều hành trên Box sạch, khôi phục từ ổ cứng sao lưu và file chìa khóa `khoa.txt`.
- **Xác minh sau phục hồi:** Vân tay CA giữ nguyên, HTTPS hoạt động trở lại bình thường mà các máy trạm không cần phải cấu hình lại.

---

## 3. Quy trình đóng gói và phát hành v1.0.0

1. **Cập nhật số liệu vào tài liệu:**
   - Đưa số liệu đo đạc RAM, tốc độ token/s từ file `reports/` vào `README.md` và `docs/kinh-doanh/bang-gia.md`.
   - Loại bỏ hoàn toàn các nhãn `[Unverified]` hoặc số liệu ước tính tạm thời.
2. **Cập nhật CHANGELOG & Hồ sơ phát hành:**
   - Tổng kết toàn bộ tính năng và bản vá từ v0.1 đến v1.0.0 trong `docs/project-changelog.md`.
3. **Tạo thẻ Tag & Phát hành GitHub:**
   - Kiểm tra commit cuối cùng trên nhánh `main` sạch sẽ và CI xanh.
   - Gắn tag: `git tag -a v1.0.0 -m "Phát hành OneBee OS v1.0.0: Nền tảng hệ điều hành văn phòng & máy chủ AI nội bộ"`
   - Đẩy tag lên GitHub: `git push origin v1.0.0`
   - Soạn Release trên GitHub đính kèm checksum và hướng dẫn cài đặt nhanh.

---

## 4. Tiêu chuẩn hoàn thành
- [ ] Tất cả các bài kiểm tra nhóm B, C, D, E trong phiếu kiểm thử đạt yêu cầu.
- [ ] Báo cáo đo đạc thực tế được lưu trữ đầy đủ trong `reports/`.
- [x] Thẻ tag `v1.0.0` được tạo và phát hành công khai trên GitHub (15/10/2026, giờ Việt Nam).
