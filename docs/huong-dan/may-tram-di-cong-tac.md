# Máy trạm đi công tác kết nối OneBee Box từ xa

Một máy trạm OneBee mang ra ngoài văn phòng vẫn dùng được thư mục chung (Samba), kho tệp (`/files/`), Sổ điều hành (`/so-dieu-hanh/`), Trợ lý AI (`hoi`), sao lưu (`restic`) và báo tình trạng qua mạng VPN Tailscale của đơn vị mà **không mở cổng nào trên router**. Box duyệt **theo từng máy, từng cổng** (`443, 445, 8000`) và thu hồi có hiệu lực ngay cả với kết nối đang mở. Thiết kế chi tiết: [ADR 0008](../adr/0008-may-tram-di-cong-tac-qua-vpn.md).

## 1. Khi nào dùng và cần chuẩn bị gì trước

Chỉ dùng cho laptop/máy trạm do đơn vị quản lý đã cài OneBee OS Desktop. Trước khi duyệt máy đầu tiên, đơn vị cần:
1. **Box đã bật HTTPS** (`onebee_box_https: true` trong `box/ansible/group_vars/all.yml`, xem [cai-dat-onebee-box.md](cai-dat-onebee-box.md)). Không có HTTPS thì Trợ lý AI không mở và máy trạm không có cách xác thực Box khi ở mạng lạ.
2. **Box đã vào tailnet của đơn vị** (`tailscale up`, gắn nhãn `tag:box`).
3. **Máy trạm đã được cấp trên Box** bằng `sudo onebee-box them-may <tên-máy>` và đã chạy bộ cài OneBee OS.

## 2. Đặt ACL của tailnet (làm một lần trên bảng điều khiển Tailscale)

Tường lửa trên Box là lớp quyết định chính (lọc theo từng IP và từng cổng ở bảng `mangle` trước cả quy tắc của `tailscaled`). Tuy nhiên, đơn vị vẫn nên đặt ACL trên bảng điều khiển Tailscale làm lớp bảo vệ thứ hai — đặc biệt để **không mở Tailscale SSH** từ máy công tác vào Box:

```json
{
  "tagOwners": {
    "tag:box": ["autogroup:admin"],
    "tag:kythuat": ["autogroup:admin"],
    "tag:congtac": ["autogroup:admin"]
  },
  "acls": [
    {"action": "accept", "src": ["tag:kythuat"], "dst": ["tag:box:22,80,443,445,3001,8000"]},
    {"action": "accept", "src": ["tag:congtac"], "dst": ["tag:box:443,445,8000"]}
  ]
}
```

Chính sách này cố ý **không có mục `ssh`**: không thiết bị nào được Tailscale SSH vào Box. Máy kỹ thuật vẫn SSH thường qua cổng 22 (đã mở ở dòng đầu của `acls`), và lệnh SSH đó vẫn đi qua tường lửa Box. Đừng thêm mục `ssh` kiểu `"action": "check"` với nguồn là tag: Tailscale từ chối lưu chính sách (`"check" action does not support tags in src`).

## 3. Bốn luồng vận hành

### 3.1. Trước chuyến đi, tại văn phòng (kỹ thuật thực hiện, khoảng 10 phút)
1. **Trên máy trạm:**
   ```bash
   sudo onebee-cong-tac bat
   ```
   Lệnh tự cài Tailscale (nếu chưa có), chạy `tailscale up --reset --hostname=<tên-máy> --accept-dns=false --accept-routes=false --shields-up --ssh=false` và in đường link đăng nhập để kỹ thuật duyệt vào tailnet (gắn `tag:congtac`). Có thể truyền `--khoa tskey-auth-…` (khóa dùng một lần đã gắn sẵn `tag:congtac`) để không phải mở link.
2. **Trên Box:**
   ```bash
   sudo onebee-box duyet-tu-xa ketoan-01
   ```
   (Thêm `--ngay 14` nếu muốn lượt duyệt tự hết hạn sau 14 ngày; không truyền `--ngay` thì lượt duyệt không hạn cho tới khi thu hồi). Box tìm IP Tailscale theo tên máy, in thông tin thiết bị và hỏi gõ `duyet` để xác nhận, mở đúng 3 cổng TCP `443, 445, 8000` cho IP đó, rồi tự chạy `dong-bo-may` để đẩy `BOX_IP_TU_XA` và địa chỉ kho sao lưu theo tên Box xuống máy trạm.
3. **Thử ngay trước khi giao máy:** Tắt Wi-Fi văn phòng, phát 4G từ điện thoại. Chạy `onebee-cong-tac xem` thấy báo `Đường tới Box: từ xa qua VPN`; thử `hoi xin chào` và mở lối tắt **Chia sẻ nội bộ (OneBee Box)** (nhập lại mật khẩu thư mục chung một lần).

### 3.2. Trong lúc đi công tác
Nhân viên **không phải gõ lệnh nào**. Mỗi khi đổi mạng (Wi-Fi khách sạn, 4G, quán cà phê) hoặc định kỳ mỗi 5 phút, công cụ `onebee-chon-duong-box` tự thử bắt tay TLS (với CA riêng của Box) tới địa chỉ LAN của Box:
- Nếu không thấy Box thật ở mạng hiện tại, dòng `/etc/hosts` tự trỏ tên `box.<mã>.onebee.internal` sang IP Tailscale của Box.
- Mọi dịch vụ (`hoi`, Sổ điều hành, kho tệp, thư mục chung, sao lưu, báo tình trạng) đều đi theo tên Box nên hoạt động bình thường.

### 3.3. Khi máy về lại văn phòng
- Nhân viên cắm mạng văn phòng (hoặc nối Wi-Fi văn phòng): máy thấy Box thật trong LAN và tự trả `/etc/hosts` về IP LAN trong vòng 5 phút (hoặc ngay khi đổi mạng).
- Kỹ thuật thu hồi quyền từ xa trên Box:
  ```bash
  sudo onebee-box thu-hoi-tu-xa ketoan-01
  ```
  Và trên máy trạm (khi không còn đi công tác):
  ```bash
  sudo onebee-cong-tac tat
  sudo onebee-box dong-bo-may ketoan-01   # chạy trên Box để gỡ BOX_IP_TU_XA khỏi máy trạm
  ```

### 3.4. Khi mất máy đang đi công tác
Chạy ngay trên Box:
```bash
sudo onebee-box thu-hoi-may ketoan-01
```
Lệnh này tự động gọi luôn `thu-hoi-tu-xa` (đóng tường lửa, gỡ khỏi `hosts allow` của Samba, chạy `conntrack -D` cắt đứt ngay lập tức mọi kết nối HTTPS/SMB đang mở), đồng thời khóa tài khoản kho sao lưu HTTP và khóa `hoi` của máy.
Sau đó kỹ thuật thực hiện thêm:
1. Xóa thiết bị khỏi tailnet trên bảng điều khiển Tailscale.
2. Thu hồi tài khoản đăng nhập một lần của người dùng trên máy đó: `sudo onebee-box xoa-nguoi <tên-đăng-nhập>` và `sudo onebee-box go-khoa-hoi <tên-đăng-nhập>`.
3. Đổi mật khẩu thư mục chung Samba (`sudo smbpasswd -a onebee` và cập nhật `/etc/onebee-box/secrets/samba-onebee`).

## 4. Máy đã đi xa mà chưa kịp chuẩn bị ở văn phòng

Cần người cầm máy biết mật khẩu tài khoản quản trị (`quantri`) trên máy trạm (hoặc kỹ thuật vào tạm qua [truy-cap-tu-xa-khi-cai-may.md](truy-cap-tu-xa-khi-cai-may.md)):
1. Trên Box, xem địa chỉ Tailscale của Box (`tailscale ip -4`, ví dụ `100.64.0.1`).
2. Trên máy trạm:
   ```bash
   sudo onebee-cong-tac bat --box-tu-xa 100.64.0.1
   ```
   Ghi lại địa chỉ IP Tailscale của máy trạm in ra trên màn hình (ví dụ `100.64.0.7`).
3. Trên Box:
   ```bash
   sudo onebee-box duyet-tu-xa ketoan-01 --ip 100.64.0.7 --ngay 14
   ```

## 5. Giới hạn cần lưu ý

- **Lượt duyệt mặc định không hạn:** Nếu không truyền `--ngay N`, lượt duyệt giữ nguyên cho tới khi kỹ thuật thu hồi tay. `sudo onebee-box chan-doan` sẽ cảnh báo khi có lượt không hạn mở quá 30 ngày; xem danh sách đang mở bằng `sudo onebee-box tu-xa`.
- **Không cập nhật / đồng bộ / xoay khóa từ Box tới máy đang ở xa:** SSH quản trị trên máy trạm chỉ nhận từ IP LAN của Box (`from="<BOX_IP>"`). Nếu chạy `xoay-khoa` trên Box trong lúc máy đang đi công tác, máy đó sẽ tạm mất sao lưu và `hoi` theo máy cho tới khi về lại LAN và chạy `dong-bo-may`.
- **Không dùng `onebee-ho-tro` (VNC) tới máy đang đi công tác:** Máy công tác chạy Tailscale với `--shields-up` để chặn mọi kết nối đi vào từ mạng ngoài.
- **Dung lượng 4G và tốc độ thư mục chung:** Sao lưu lúc 12:00 và mở tệp lớn trong thư mục chung qua 4G sẽ tốn dung lượng di động và chậm hơn trong LAN.
- **Mật khẩu thư mục chung dùng chung:** Samba dùng chung tài khoản `onebee`, nên việc chặn từng máy công tác dựa vào tường lửa Box và `hosts allow`.
- **Khuyến nghị mã hóa ổ đĩa (LUKS):** Laptop mang ra ngoài văn phòng nên bật mã hóa ổ đĩa lúc cài hệ điều hành để bảo vệ dữ liệu nếu mất máy.

## 6. Bảng xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `hoi` hoặc trình duyệt báo không kết nối được Box khi ở ngoài LAN | Tailscale trên máy chưa nối, hoặc Box chưa `duyet-tu-xa`, hoặc máy chưa có `BOX_IP_TU_XA` | Trên máy trạm chạy `onebee-cong-tac xem` và `onebee-chan-doan`. Nếu chưa có `BOX_IP_TU_XA`, chạy `sudo onebee-cong-tac bat --box-tu-xa <IP-Tailscale-Box>`; trên Box kiểm `sudo onebee-box tu-xa` |
| Bấm lối tắt "Chia sẻ nội bộ" hỏi lại mật khẩu một lần | Lối tắt chuyển từ `smb://<IP-LAN>/chung` sang `smb://box.<mã>.onebee.internal/chung` | Nhập tài khoản `onebee` và mật khẩu thư mục chung như lần đầu, đánh dấu nhớ mật khẩu |
| Lượt duyệt có `--ngay N` hết hạn giữa chuyến đi | Quá thời hạn đã cấp, bộ hẹn giờ trên Box đã tự thu hồi | Trên Box chạy lại `sudo onebee-box duyet-tu-xa <tên-máy> --ngay <số-ngày-mới>` (không cần thao tác gì trên máy trạm) |
| `duyet-tu-xa` báo không tìm thấy hoặc có hơn một thiết bị trùng tên | Máy trạm chưa vào tailnet, hoặc có thiết bị cũ trùng tên trong tailnet | Mở bảng điều khiển Tailscale kiểm tra đúng IP của máy, xóa thiết bị thừa, rồi chạy `sudo onebee-box duyet-tu-xa <tên-máy> --ip <IPv4>` |
