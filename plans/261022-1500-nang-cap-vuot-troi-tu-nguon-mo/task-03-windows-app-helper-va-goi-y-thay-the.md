# Task 03 — Windows App Helper & Gợi ý Ứng dụng Thay thế (`.exe` Interceptor)

**Ưu tiên:** Trung bình (P2)  
**Trạng thái:** Sẵn sàng thực hiện  
**Cảm hứng thiết kế:** **Zorin OS (Windows App Support)** (Gỡ bỏ cú sốc chuyển đổi của nhân viên văn phòng khi tải file `.exe`).

---

## 1. Hiện trạng & Vấn đề thực tế

- Người dùng văn phòng quen thói quen tải các file cài đặt từ mạng về (như Zalo, Chrome, Unikey, Foxit Reader, VLC, Ultraviewer, phần mềm kế toán) có đuôi `.exe` hoặc `.msi`.
- Trên Linux Mint mặc định, đúp chuột vào file `.exe` sẽ báo lỗi không mở được, hoặc bung ứng dụng nén Archive Manager, khiến người dùng hoang mang và kết luận "Linux dở, không dùng được".

---

## 2. Giải pháp kỹ thuật

### Bước 1: Đăng ký MIME Handler cho file PE/Windows Executable
- Tạo tệp `desktop-file` đăng ký với hệ thống Cinnamon:
  - MIME types: `application/x-msdos-program`, `application/x-msi`, `application/x-executable`
  - Ứng dụng xử lý mặc định: `/usr/local/bin/onebee-windows-app-helper`

### Bước 2: Xây dựng trình trợ lý `onebee-windows-app-helper` (Python + Zenity/GTK)
Khi người dùng bấm đúp vào file `.exe`, một cửa sổ giao diện thân thiện hiện lên:

1. **Nhận diện tự động tên ứng dụng phổ biến:**
   - Dò theo tên file hoặc mã băm:
     - `ZaloSetup.exe` ➔ Gợi ý: *"Đã có Zalo phiên bản Web / Native cho OneBee OS. Bấm để mở ngay!"*
     - `ChromeSetup.exe` ➔ Gợi ý: *"Đã cài sẵn trình duyệt Chromium / Firefox bảo mật. Bấm để dùng!"*
     - `Unikey.exe` ➔ Gợi ý: *"Hệ điều hành đã tích hợp sẵn bộ gõ IBus Bamboo chuẩn quốc gia, không cần cài Unikey!"*
     - `FoxitReader.exe` ➔ Gợi ý: *"Đã tích hợp sẵn trình đọc PDF nhẹ và không có quảng cáo độc hại."*
2. **Đối với phần mềm văn phòng chuyên ngành chưa có sẵn:**
   - Cung cấp nút:
     - 🚀 **"Chạy thử với môi trường tương thích WINE"** (nếu máy đã cài WINE/Bottles).
     - 💻 **"Mở trên máy ảo / máy kế toán chuyên dụng"** (nếu có cấu hình VM).
     - 📞 **"Yêu cầu hỗ trợ kỹ thuật OneBee"** (mở form yêu cầu để kỹ thuật viên kiểm tra phần mềm).

---

## 3. Các tệp cần sửa đổi & tạo mới

1. `desktop/scripts/onebee-windows-app-helper`: Script Python/Bash xử lý logic bắt file `.exe`.
2. `desktop/assets/onebee-exe-handler.desktop`: File desktop đăng ký MIME handler trong `/usr/share/applications/`.
3. `desktop/onebee-install.sh`: Bổ sung bước cài đặt helper và liên kết MIME handler.
4. `tests/desktop/check-exe-handler.sh`: Test tự động xác nhận MIME association và chạy thử lệnh helper với các mẫu file `.exe` giả lập.
