# ADR 0004 — Quản lý tập trung máy trạm và hỗ trợ từ xa

- Ngày: 29/9/2026 · Trạng thái: Chốt cho v0.4 (chưa thử trên máy thật)

## Bối cảnh
Gói bảo trì cần: biết máy nào chưa cập nhật / chưa sao lưu / ổ sắp đầy; cập nhật cả đơn vị bằng 1 lệnh;
hỗ trợ từ xa khi người dùng gặp sự cố — nhưng **người dùng phải đồng ý** mỗi lần.

## Quyết định
1. **Máy trạm tự báo tình trạng** mỗi giờ (và 3 phút sau khi bật) về n8n trên Box (`/webhook/onebee-tinh-trang`).
   n8n kiểm tra dữ liệu rồi ghi `<tên>.json`. Chọn "máy trạm gửi lên" thay vì "Box hỏi xuống" vì máy trạm tắt/bật thất thường
   và dùng IP động — Box biết được lần liên lạc cuối và IP hiện tại của từng máy mà không cần IP cố định.
   - Khóa gửi tình trạng dùng chung cho mọi máy của 1 Box, **tách riêng** khóa webhook của Box (máy trạm không gửi giả
     được báo cáo sao lưu). Máy trạm A có thể gửi thay tên máy B → tình trạng máy trạm chỉ để tham khảo; **tình trạng
     sao lưu lấy từ kho trên Box**, không lấy từ máy trạm tự báo. Có khóa này cũng tạo được file `<tên-bất-kỳ>.json`
     (tên chỉ gồm a-z, 0-9, "-", tối đa 32 ký tự; báo cáo bỏ qua tên chưa cấp) — rủi ro chấp nhận ở v0.4: khóa chỉ nằm trên
     máy trạm của đơn vị, file root mới đọc được.
   - Box chỉ SSH tới IP máy trạm báo trong **2 giờ gần nhất**, và việc đầu tiên khi vào là **kiểm tra đúng tên máy**
     (`MAY_TRAM` trong cấu hình máy trạm) — IP động đã sang máy khác thì dừng, không cập nhật nhầm.
2. **Cập nhật qua SSH bằng Ansible chạy trên Box** (`onebee-box cap-nhat-may`). Mỗi Box sinh **1 khóa SSH riêng**
   (không dùng chung giữa các khách hàng). Máy trạm có tài khoản hệ thống `onebee-quantri` (không mật khẩu, không hiện ở màn
   hình đăng nhập, sudo không hỏi mật khẩu), `authorized_keys` có `from="<IP Box>"`. SSH của máy trạm **tắt đăng nhập bằng mật
   khẩu và root** — máy văn phòng không ai dùng SSH bằng mật khẩu, tắt đi để chống dò mật khẩu nhân viên trong LAN.
   Khóa máy (host key) ghi theo tên máy (`HostKeyAlias`) → đổi IP không sao, cài lại máy thì chạy lại `them-may`.
3. **Hỗ trợ từ xa: x11vnc (GPL-2.0, gói Ubuntu) chạy theo yêu cầu**, không chạy nền:
   người dùng bấm "Cho phép hỗ trợ từ xa" → hiện địa chỉ + mã 8 số dùng 1 lần → kỹ thuật kết nối → **người dùng bấm "Cho phép"
   lần nữa** (hộp thoại hiện IP máy xin vào, 1 phút không trả lời = từ chối) → xem được màn hình; kỹ thuật ngắt là phiên
   đóng; không ai vào sau 10 phút thì tự đóng. Chỉ nhận kết nối từ dải LAN và Tailscale. x11vnc chạy bằng quyền người dùng.
   Hộp thoại hỏi từng lần nên đoán mã hàng loạt không vào được (mỗi lần đoán đều phải qua người dùng).

## Phương án đã cân nhắc
| Phương án | Vì sao chưa chọn |
|---|---|
| Box hỏi máy trạm qua SSH theo lịch (không cần n8n) | Cần biết IP máy trạm trước (IP động); máy tắt lúc hỏi thì mất số liệu |
| RustDesk (tự dựng máy chủ trên Box) | Hỗ trợ được ngoài mạng nội bộ, nhưng thêm 2 dịch vụ + gói ngoài kho Ubuntu; giấy phép AGPL (theo trang dự án, chưa kiểm kỹ). Xem lại khi cần hỗ trợ khách ở xa không có Tailscale |
| Phần mềm điều khiển từ xa đóng (TeamViewer, UltraViewer…) | Không phải nguồn mở; điều khoản dùng cho doanh nghiệp phải kiểm riêng từng hãng |
| Chia sẻ màn hình có sẵn của Cinnamon | Cinnamon không có sẵn chia sẻ màn hình như GNOME |

## Hệ quả
- Box giữ **quyền root trên mọi máy trạm** → phải báo đơn vị, giữ Box kín; lộ khóa SSH của Box vẫn phải đứng ở đúng IP của
  Box mới dùng được.
- VNC không mã hóa: trong LAN chấp nhận được cho phiên ngắn; qua Internet **chỉ dùng qua Tailscale** (đã mã hóa).
- Phiên Wayland chưa hỗ trợ (Mint 22 mặc định X11). Hỗ trợ ngoài LAN không có Tailscale: chưa có.
- Kiểm trong container (Xvfb + vncsnapshot giả làm máy kỹ thuật, SSH giữa 2 container). Chưa thử trên máy thật.
