# Quản lý máy trạm từ OneBee Box

Cần: Box đã cài; mỗi máy trạm đã dán cấu hình từ `sudo onebee-box them-may <tên>` vào `/etc/onebee/may-tram.env`
và chạy lại bộ cài OneBee OS (xem [cai-dat-onebee-box.md](cai-dat-onebee-box.md), mục 4). Thiết kế: [ADR 0004](../adr/0004-quan-ly-tap-trung-va-ho-tro-tu-xa.md).

## 1. Xem tình trạng các máy
```bash
sudo onebee-box may-tram
```
```
ketoan-01  ỔN         sao lưu 5 giờ trước · báo tình trạng 12 phút trước · ổ trống 63% · đã cập nhật
kho-02     CẦN XỬ LÝ
           → chưa từng sao lưu lên Box
           → chưa báo tình trạng (máy chưa cài bản mới hoặc chưa bật lần nào)
```
Giám sát dịch vụ của chính Box (Uptime Kuma, `http://<ip-box>:3001`):

![Giám sát dịch vụ trên Box](anh/04-giam-sat-uptime-kuma.png)

Box cảnh báo máy trạm khi: quá 3 ngày chưa sao lưu · quá 2 ngày không liên lạc · ổ hệ thống còn dưới 10% · có bản vá bảo mật chưa cài
(hoặc từ 30 gói chờ cập nhật) · cần khởi động lại. Bảng này đi kèm **email báo cáo sao lưu 23:00 hằng ngày**.

Máy trạm gửi mỗi giờ: tên, IP, phiên bản, số gói chờ cập nhật, cần khởi động lại không, ổ còn trống, đã bật bao lâu,
lần sao lưu cuối. **Không gửi** tên file, nội dung, lịch sử dùng máy. Gửi ngay trên máy trạm: `sudo onebee-bao-tinh-trang`.

## 2. Cập nhật phần mềm máy trạm
```bash
sudo onebee-box cap-nhat-may ketoan-01     # 1 máy
sudo onebee-box cap-nhat-may --tat-ca      # mọi máy đã cấp
```
Box vào máy trạm qua SSH (tài khoản `onebee-quantri`), cập nhật toàn bộ gói + ứng dụng Flatpak, rồi gửi lại tình trạng.
Máy tắt hoặc mất mạng → báo "không vào được", máy khác vẫn chạy tiếp. Nhật ký: `/var/log/onebee-box/cap-nhat-may-*.log`.
Máy trạm vẫn tự cập nhật hằng ngày (mintupdate) — lệnh này để cập nhật ngay, ví dụ khi có bản vá khẩn.
SSH vào máy trạm **chỉ** cho tài khoản `onebee-quantri`, bằng khóa của Box, từ IP của Box (tắt mật khẩu, tắt root,
tài khoản khác bị từ chối). Kỹ thuật cần vào máy trạm bằng dòng lệnh: SSH vào Box trước, rồi từ Box
`sudo ssh -i /etc/onebee-box/secrets/ssh/quan-tri onebee-quantri@<ip-máy-trạm>`.

- Báo "chưa báo tình trạng (chưa biết địa chỉ)": máy chưa bật từ khi cài, hoặc chưa chạy lại bộ cài sau khi dán cấu hình.
- Báo "REMOTE HOST IDENTIFICATION HAS CHANGED": máy trạm đã cài lại hệ điều hành (khóa SSH của máy đổi) → **chỉ khi chắc đó là
  máy của mình**, xóa khóa cũ trên Box: `sudo ssh-keygen -R <tên-máy> -f /etc/onebee-box/secrets/ssh/known_hosts`, rồi chạy lại
  `sudo onebee-box cap-nhat-may <tên-máy>`. Nếu máy không hề cài lại mà vẫn báo: có thể máy khác đang giả danh — kiểm tra trước.
  (Lệnh `them-may` không đụng tới khóa SSH đã ghim; máy cài lại cần dán lại cấu hình mới + chạy lại bộ cài như máy mới.)

## 3. Hỗ trợ từ xa (người dùng phải đồng ý)
1. Người dùng mở menu → **"Cho phép hỗ trợ từ xa (OneBee)"** → hộp thoại hiện **địa chỉ** và **mã 8 số** → đọc cho kỹ thuật.
2. Kỹ thuật mở phần mềm xem VNC bất kỳ (TigerVNC Viewer, Remmina…) → nhập `<địa chỉ>:5900` → nhập mã.
3. Máy người dùng hỏi **"Máy … xin xem và điều khiển màn hình. Cho phép?"** → người dùng bấm **Cho phép**.
4. Xong việc: kỹ thuật đóng cửa sổ VNC, hoặc người dùng bấm **"Dừng hỗ trợ"** → phiên đóng, mã hết hiệu lực.

Chỉ nhận kết nối từ mạng nội bộ (10.x, 172.16–31.x, 192.168.x) và Tailscale (100.64–127.x). Hỗ trợ từ xa ngoài đơn vị:
cài Tailscale trên máy kỹ thuật và máy trạm (cùng mạng Tailscale). Kết nối VNC không mã hóa → **ngoài LAN chỉ dùng qua Tailscale**.
Người dùng không có menu (ví dụ đang ở màn hình dòng lệnh): `onebee-ho-tro --khong-hoi` (in địa chỉ + mã ra màn hình).

## Giới hạn
- Chưa thử trên máy thật (đã kiểm trong container: báo tình trạng, cập nhật qua SSH giữa 2 container, VNC giả lập).
- Phiên Wayland chưa hỗ trợ hỗ trợ từ xa (Mint 22 mặc định X11).
- Khóa gửi tình trạng dùng chung cho các máy của 1 Box → tình trạng máy trạm tự báo chỉ để tham khảo; tình trạng sao lưu
  Box tự đọc từ kho sao lưu.
