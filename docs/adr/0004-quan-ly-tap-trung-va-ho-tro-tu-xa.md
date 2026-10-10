# ADR 0004 — Quản lý tập trung máy trạm và hỗ trợ từ xa

- Ngày: 29/9/2026 · Trạng thái: Chốt cho v0.4 (chưa thử trên máy thật) · Sửa 10/10/2026: mục 1 và 2 theo rà soát bảo mật (`docs/security-audit.md`, F2)

## Bối cảnh
Gói bảo trì cần: biết máy nào chưa cập nhật / chưa sao lưu / ổ sắp đầy; cập nhật cả đơn vị bằng 1 lệnh;
hỗ trợ từ xa khi người dùng gặp sự cố — nhưng **người dùng phải đồng ý** mỗi lần.

## Quyết định
1. **Máy trạm tự báo tình trạng** mỗi giờ (và 3 phút sau khi bật) về n8n trên Box (`/webhook/onebee-tinh-trang`).
   n8n kiểm tra dữ liệu rồi ghi `<tên>.json`. Chọn "máy trạm gửi lên" thay vì "Box hỏi xuống" vì máy trạm tắt/bật thất thường
   và dùng IP động — Box biết được lần liên lạc cuối và IP hiện tại của từng máy mà không cần IP cố định.
   - **Cách cũ (v0.4–1.0.0-rc.1, đã thay):** khóa gửi tình trạng dùng chung cho mọi máy → máy A giả được báo cáo của máy B, tạo được
     file tên bất kỳ, và Box tin IP trong báo cáo để SSH (lái khóa quản trị tới máy lạ). Rủi ro này được chấp nhận ở v0.4, nhưng
     rà soát bảo mật 10/10/2026 (F2) cho thấy khóa đó đi qua HTTP mỗi giờ nên không còn chấp nhận được.
   - **Cách mới:** báo cáo **ký HMAC-SHA256** bằng khóa suy từ mật khẩu kho sao lưu của máy (`RESTIC_PASSWORD`; restic mã hóa phía máy nên
     chưa từng đi qua mạng). n8n **không giữ khóa** — chỉ nhận máy có file đánh dấu trong `may-da-cap/` (Box ghi, n8n chỉ đọc) và lưu
     nguyên văn; **Box tự kiểm chữ ký** + độ lệch giờ ký (giới hạn phát lại trong ±10 phút qua đường bình thường; n8n bị chiếm phát lại được
     báo cáo ký cũ nhưng IP nằm trong phần ký + khóa ghim + chứng minh nên không lái được SSH). Khóa chung ở cửa chỉ còn là bộ lọc rác. Báo cáo cũ không ký vẫn
     nhận (chuyển tiếp) nhưng gắn nhãn "chưa ký". **Tình trạng sao lưu vẫn lấy từ kho trên Box.**
   - **IP để SSH:** máy chưa ghim chỉ dùng IP trong báo cáo có chữ ký hợp lệ ≤ 2 giờ; máy đã ghim khóa SSH dùng IP tới 30 ngày (IP đã sang
     máy khác thì khóa host lệch, SSH dừng). **Lần đầu vào máy phải chứng minh** biết mật khẩu kho sao lưu (đọc qua SSH, so với bản
     Box giữ) rồi mới ghim khóa SSH; các lần sau `StrictHostKeyChecking=yes` và chứng minh lại. Việc kiểm `MAY_TRAM` trên máy đích chỉ còn là
     lớp phụ (máy giả tự trả lời được).
2. **Cập nhật qua SSH bằng Ansible chạy trên Box** (`onebee-box cap-nhat-may`). Mỗi Box sinh **1 khóa SSH riêng**
   (không dùng chung giữa các khách hàng). Máy trạm có tài khoản hệ thống `onebee-quantri` (không mật khẩu, không hiện ở màn
   hình đăng nhập, sudo không hỏi mật khẩu), `authorized_keys` có `from="<IP Box>"`. SSH của máy trạm **tắt đăng nhập bằng mật
   khẩu và root** — máy văn phòng không ai dùng SSH bằng mật khẩu, tắt đi để chống dò mật khẩu nhân viên trong LAN.
   Khóa máy (host key) ghi theo tên máy (`HostKeyAlias`) → đổi IP không sao; cài lại máy thì `ghim-lai-may` rồi chứng minh lại.
   Thu hồi một máy: `thu-hoi-may` (gỡ quyền kho HTTP, khóa Trợ lý AI, ghim SSH, chỗ báo tình trạng). Đẩy lại cấu hình xuống máy:
   `dong-bo-may` — cùng điều kiện (chỉ tới máy đã chứng minh), cùng một nguồn dựng cấu hình với `them-may`.
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
- Box giữ **quyền root trên mọi máy trạm** (rủi ro đã chấp nhận, F4) → phải báo đơn vị, giữ Box kín; lộ khóa SSH của Box vẫn phải đứng ở
  đúng IP của Box mới dùng được. Chiếm được Box (root) thì đọc được mọi mật khẩu kho và đẩy được cấu hình/chứng chỉ bất kỳ xuống máy.
- Chữ ký chưa chống được người có **mật khẩu kho sao lưu** của máy (root trên máy đó, hoặc root trên Box) — đúng chủ trương: nhân viên
  không có sudo (kiểm bằng cảnh báo tài khoản sudo).
- VNC không mã hóa: trong LAN chấp nhận được cho phiên ngắn; qua Internet **chỉ dùng qua Tailscale** (đã mã hóa).
- Phiên Wayland chưa hỗ trợ (Mint 22 mặc định X11). Hỗ trợ ngoài LAN không có Tailscale: chưa có.
- Kiểm trong container (Xvfb + vncsnapshot giả làm máy kỹ thuật, SSH giữa 2 container). Chưa thử trên máy thật.
