# QUY TRÌNH THAO TÁC CHUẨN (SOP) TRIỂN KHAI THỰC ĐỊA ONEBEE OS
*(Tài liệu nghiệp vụ dành cho kỹ thuật viên triển khai tại Hợp tác xã)*

---

## BƯỚC 1: KHẢO SÁT & CHUẨN BỊ MÔI TRƯỜNG TẠI CƠ SỞ (15 phút)
1. **Mạng LAN:**
   - Xác định dải mạng IP của văn phòng HTX (Ví dụ: `192.168.1.0/24`).
   - Yêu cầu người quản lý mạng cấp 1 IP tĩnh hoặc cấu hình gán cố định DHCP trên Router cho Box.
2. **Nguồn điện & Vị trí đặt máy:**
   - Đặt OneBee Box ở vị trí thoáng mát, cắm dây mạng LAN Cat6 trực tiếp vào Router chính hoặc Switch trung tâm.
   - Gắn ổ cứng sao lưu ngoài USB vào cổng USB 3.0 (màu xanh).

---

## BƯỚC 2: CÀI ĐẶT ONEBEE BOX BẰNG USB OFFLINE (10 phút)
1. Cắm USB cài đặt OneBee Offline vào Box.
2. Mở terminal, chạy lệnh:
   ```bash
   cd /media/usb/onebee-bundle
   sudo ./cai-tu-usb-offline.sh
   ```
3. Sau khi cài đặt hoàn tất, chạy lệnh kiểm tra sức khỏe 7 hạng mục:
   ```bash
   sudo onebee-box chan-doan
   ```
   *Yêu cầu bắt buộc: Tất cả 7 hạng mục phải báo `OK` (màu xanh).*

---

## BƯỚC 3: CẤU HÌNH TỰ ĐỘNG HÓA & CẢNH BÁO TELEGRAM (5 phút)
1. Cấu hình bot nhận cảnh báo:
   ```bash
   sudo onebee-box dat-telegram
   ```
   - Nhập Token Bot và Chat ID nhóm quản lý HTX.
   - Xác nhận điện thoại quản lý nhận được tin nhắn thông báo thử nghiệm.
2. Khởi tạo ổ sao lưu ngoài:
   ```bash
   sudo onebee-box khoi-tao
   sudo onebee-box sao-luu
   ```
3. Xuất file khóa an toàn để niêm phong:
   ```bash
   sudo onebee-box in-khoa > /home/onebee/khoa-dan-tu.txt
   ```

---

## BƯỚC 4: KẾT NỐI VÀ CÀI ĐẶT CÁC MÁY TRẠM (MỖI MÁY 5 PHÚT)
1. **Đối với máy trạm Linux Mint:**
   - Cấp tài khoản máy trạm trên Box:
     ```bash
     sudo onebee-box them-may ke-toan-01
     ```
   - Copy file cấu hình `may-tram.env` sang máy trạm và chạy:
     ```bash
     sudo desktop/onebee-install.sh
     ```
2. **Đối với máy trạm Windows 10/11:**
   - Mở File Explorer, gõ: `\\onebee.local\chung`.
   - Đăng nhập bằng tài khoản chung và ghim shortcut ra màn hình Desktop.
   - Nhập chứng chỉ `http://onebee.local/onebee-ca.crt` vào máy.

---

## BƯỚC 5: NGHIỆM THU & BÀN GIAO (15 phút)
1. Mở `http://onebee.local` trên máy trạm để cán bộ trải nghiệm Dashboard.
2. Hướng dẫn cán bộ thử nghiệm các mẫu prompt AI: `/to-trinh`, `/bien-ban`, `/hop-dong`.
3. Bàn giao phong bì mật khẩu niêm phong và ký Biên bản bàn giao.
