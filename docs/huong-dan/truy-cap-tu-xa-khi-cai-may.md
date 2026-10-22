# Vào máy từ xa để cài tiếp (máy mới cài, ở nơi khác)

Dùng khi máy vừa cài xong Ubuntu 24.04 / Linux Mint 22, đặt ở đơn vị khác mạng (thường chỉ có wifi), và kỹ thuật cần vào từ xa để
chạy bộ cài OneBee. Script `scripts/mo-truy-cap-tu-xa.sh` mở **tạm** hai đường vào:

| Đường | Dùng để | Xác thực |
|---|---|---|
| **Tailscale SSH** | Chạy bộ cài, xem nhật ký | Tài khoản Tailscale của kỹ thuật (không cần khóa SSH, không cần mật khẩu máy) |
| **Chia sẻ màn hình GNOME (RDP, cổng 3389)** | Xem và điều khiển màn hình | Mật khẩu ngẫu nhiên 16 ký tự, chỉ root đọc được trong `/root/onebee-truy-cap-tu-xa.txt` |

Không có mật khẩu nào đi qua Zalo: người tại máy chỉ gửi **đường link đăng nhập Tailscale** (dùng 1 lần) và **tên máy**.
Chia sẻ màn hình chỉ bật được trên phiên **GNOME** (Ubuntu). Mint Cinnamon chỉ có SSH; sau khi cài OneBee Desktop dùng
`onebee-ho-tro` (người dùng bấm Cho phép, xem [quan-ly-may-tram.md](quan-ly-may-tram.md#3-hỗ-trợ-từ-xa-người-dùng-phải-đồng-ý)).

## Người tại máy làm (khoảng 5 phút)
1. Đăng nhập máy, cắm sạc (laptop), nối wifi.
2. Mở **Terminal** (Ctrl + Alt + T), dán 2 lệnh:
   ```bash
   wget -O mo-truy-cap-tu-xa.sh https://raw.githubusercontent.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/main/scripts/mo-truy-cap-tu-xa.sh
   sudo bash mo-truy-cap-tu-xa.sh
   ```
3. Màn hình hiện dòng `https://login.tailscale.com/a/...` → **chụp hoặc chép gửi kỹ thuật**, giữ nguyên cửa sổ đến khi hiện
   "ĐÃ MỞ TRUY CẬP TỪ XA".
   Nếu hiện hộp thoại hỏi mật khẩu **keyring / Login**: gõ mật khẩu đăng nhập máy → Mở khóa (GNOME cất mật khẩu chia sẻ màn hình ở đó).
   Dòng "Màn hình: CHƯA BẬT — keyring GNOME đang khóa" nghĩa là máy đang **tự đăng nhập** không cần mật khẩu: đăng xuất, đăng nhập lại
   bằng mật khẩu rồi chạy lại lệnh `sudo bash ...` ở trên (SSH vẫn dùng được trong lúc đó).
4. Gửi kỹ thuật dòng `Máy: ... IP Tailscale: ...`. **Không đăng xuất** (chia sẻ màn hình dùng phiên đang mở); máy sẽ không tự khóa,
   không tự tắt màn hình, cắm điện thì không ngủ cho đến khi tắt cầu nối.

## Kỹ thuật làm
1. Mở link nhận được, đăng nhập **tài khoản Tailscale của mình** → máy vào tailnet của kỹ thuật (thiết bị của chính mình).
2. SSH: `tailscale ssh root@<tên máy>` (lần đầu trình duyệt hỏi xác nhận lại — chính sách SSH mặc định của tailnet cá nhân là "check").
   Tailnet đã sửa ACL thì cần một mục `ssh` cho phép thiết bị của mình vào `root`/`autogroup:nonroot`.
3. Màn hình: `sudo cat /root/onebee-truy-cap-tu-xa.txt` lấy mật khẩu → mở Remmina (Linux), Windows App / Microsoft Remote Desktop
   (macOS, Windows) → `<IP Tailscale>:3389`, tài khoản `onebee`. Lần đầu phần mềm hỏi chứng chỉ tự ký `CN=onebee-<tên máy>` → chấp nhận.
4. Cài tiếp như bình thường ([huong-dan-cai-dat-tu-a-den-z.md](huong-dan-cai-dat-tu-a-den-z.md)). Chạy bộ cài trong `tmux`
   (`sudo apt install tmux; tmux`) để mất mạng giữa chừng không làm dừng bộ cài.

## Lưu ý khi máy này thành OneBee Box
Tailscale SSH **không** bị tường lửa Box chặn (tailscaled nhận cổng 22 của IP Tailscale trước iptables), nên chạy
`box/onebee-box-install.sh` qua `tailscale ssh` không mất kết nối giữa chừng. Nhưng chia sẻ màn hình (3389) và các trang web của Box
(3000, 5678, 3001…) qua Tailscale bị chặn nếu chưa khai máy kỹ thuật: thêm IP Tailscale của máy kỹ thuật vào `onebee_box_tailscale_cho_phep`
(`box/ansible/group_vars/all.yml`), ví dụ `["100.64.1.2"]` ([cai-dat-onebee-box.md](cai-dat-onebee-box.md)).

## Cài xong: tắt cầu nối
Người tại máy hoặc kỹ thuật (qua SSH, chạy cuối cùng vì sẽ ngắt kết nối):
```bash
sudo bash mo-truy-cap-tu-xa.sh --tat
```
Lệnh gỡ chia sẻ màn hình và mật khẩu RDP, trả lại khóa màn hình / chế độ ngủ, tắt Tailscale SSH và rời tailnet.
Cấu hình Chia sẻ màn hình (RDP) của người dùng bị đặt lại về mặc định. Gói Tailscale vẫn giữ (hỗ trợ lâu dài qua Tailscale theo ADR 0004 cần nó, nhưng phải đăng nhập lại vào **tailnet của đơn vị**).

## Giới hạn
- RDP nghe trên mọi mạng của máy (cả wifi LAN) trong lúc cầu nối bật; bảo vệ bằng TLS + mật khẩu ngẫu nhiên. Tắt cầu nối ngay khi xong.
- Đã kiểm bằng unit test (lệnh giả) và kiểm cú pháp `grdctl` trên gói Ubuntu 24.04; **chưa chạy trên máy thật** — lần dùng đầu
  ghi kết quả vào phiếu [kiem-thu-tren-may-that.md](../kiem-thu-tren-may-that.md).
