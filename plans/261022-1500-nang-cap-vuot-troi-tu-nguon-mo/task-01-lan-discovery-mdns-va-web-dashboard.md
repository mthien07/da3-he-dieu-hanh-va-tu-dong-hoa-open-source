# Task 01 — Zero-Config LAN Discovery (`onebee.local`) & Web Dashboard

**Ưu tiên:** Cao (P1)  
**Trạng thái:** Sẵn sàng thực hiện  
**Cảm hứng thiết kế:** **CasaOS / Umbrel** (Giải quyết bài toán người dùng không nhớ địa chỉ IP máy chủ).

---

## 1. Hiện trạng & Vấn đề thực tế

- **Hiện trạng:** Để truy cập các dịch vụ trên OneBee Box (Trợ lý AI, Thư mục chia sẻ, Báo cáo), người dùng phải nhớ địa chỉ IP (ví dụ: `http://192.168.1.100:3000`).
- **Rủi ro thực tế:** 
  1. Hầu hết router tại HTX/SME cấp IP động (DHCP), khi mất điện hoặc khởi động lại modem, IP của Box bị đổi dẫn đến người dùng không truy cập được.
  2. Người dùng không chuyên rất khó nhớ các cổng `:3000`, `:5678`.

---

## 2. Giải pháp kỹ thuật

### Bước 1: Cấu hình `avahi-daemon` (mDNS) trên OneBee Box
- Cài đặt và kích hoạt dịch vụ `avahi-daemon` trong vai trò `box-setup` của Ansible.
- Cấu hình hostname quảng bá dạng: `onebee.local` (hoặc `box.local`).
- Thiết lập tệp dịch vụ `/etc/avahi/services/http.service` để các thiết bị trong mạng LAN (Windows, macOS, iOS, Android, Linux Mint) tự động nhận diện tên miền `http://onebee.local`.

### Bước 2: Web Dashboard nhẹ tại cổng 80 (Caddy Reverse Proxy / Static Landing)
- Xây dựng một trang Landing Dashboard tĩnh cực nhẹ (HTML + Tailwind CSS / Alpine.js) đặt tại root (`/` cổng 80):
  - **Tên đơn vị:** Hiển thị tên HTX / doanh nghiệp.
  - **Widget sức khỏe hệ thống (System Status):** Gọi API nhẹ lấy % CPU, RAM, dung lượng ổ cứng còn trống, trạng thái dịch vụ (AI, Samba, Backup).
  - **Lối tắt truy cập nhanh (Quick Launch):**
    - 🤖 **Trợ lý AI nội bộ** (Chuyển tiếp đến cổng 3000 / Open WebUI).
    - 📁 **Thư mục dùng chung** (Hướng dẫn mở Samba `\\onebee.local\chung` hoặc `smb://onebee.local/chung`).
    - 🛠️ **Yêu cầu hỗ trợ kỹ thuật** (Mở form gửi tín hiệu qua n8n).
    - 📖 **Cẩm nang sử dụng** (Hướng dẫn phím tắt, in ấn, lưu trữ).

---

## 3. Các tệp cần sửa đổi & tạo mới

1. `box/ansible/roles/box-setup/tasks/main.yml`: Thêm task cài đặt và cấu hình `avahi-daemon`.
2. `box/ansible/roles/box-stack/templates/Caddyfile.j2`: Cấu hình reverse proxy cổng 80 trỏ về Dashboard và định tuyến tên miền `onebee.local`.
3. `box/web-dashboard/index.html`: Giao diện Dashboard Web thuần tiếng Việt, thân thiện, tải nhanh dưới 100ms.
4. `tests/box/check-mdns-dashboard.sh`: Bài kiểm thử tự động xác nhận mDNS phân giải được `onebee.local` và cổng 80 trả về HTTP 200 kèm nội dung Dashboard.

---

## 4. Kiểm thử nghiệm thu (Verification)

```bash
# Kiểm tra phân giải mDNS
avahi-resolve-host-name onebee.local

# Kiểm tra HTTP 80
curl -si http://onebee.local | grep -q "OneBee Box"
```
Đạt yêu cầu: Cả 2 lệnh trả về thành công 100%.
