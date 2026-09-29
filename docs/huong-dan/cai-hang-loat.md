# Cài OneBee OS cho nhiều máy (và đường lui bằng Clonezilla)

Hai cách:
- **Cách A — cài từng máy**: Linux Mint chuẩn + bộ cài OneBee OS. Dùng khi các máy khác cấu hình nhau (thường gặp ở HTX).
- **Cách B — nhân bản ảnh đĩa bằng Clonezilla**: làm 1 máy mẫu rồi chép sang các máy **cùng dòng máy** (cùng ổ, cùng chipset).

Dù cách nào: **sao lưu nguyên ổ Windows trước khi xóa** (mục 1) — đó là đường lui nếu đơn vị muốn quay lại.

> Chưa làm thử trên máy thật. Thời gian từng bước ghi vào bảng ở mục 5 khi làm thật lần đầu (tiêu chí Phase 4: cài liền 3 máy).

## 1. Sao lưu nguyên ổ Windows (bắt buộc, trước khi cài)
Cần: USB Clonezilla Live (tải tại clonezilla.org, ghi USB bằng balenaEtcher/Rufus), 1 ổ ngoài trống ≥ dung lượng đã dùng của ổ Windows.
1. Trên Windows: ghi lại tên máy, danh sách phần mềm đang dùng, **khóa khôi phục BitLocker** nếu ổ có mã hóa BitLocker
   (Cài đặt → Bảo mật thiết bị / "Manage BitLocker"). Chép riêng dữ liệu quan trọng ra ổ ngoài (lớp an toàn thứ 2).
2. Khởi động từ USB Clonezilla → `device-image` → `local_dev` (chọn ổ ngoài) → `Beginner` → **`savedisk`**
   → đặt tên ảnh theo máy, ví dụ `2026-10-05-ketoan-01-windows` → chọn ổ Windows → đồng ý kiểm tra ảnh sau khi lưu.
3. Ghi vào bảng mục 5: tên ảnh, dung lượng, thời gian. **Không xóa ảnh này** cho tới hết thời gian dùng thử (khuyên ≥ 3 tháng).

Quay lại Windows: khởi động Clonezilla → `device-image` → **`restoredisk`** → chọn đúng ảnh của máy đó.

## 2. Cách A — cài từng máy
1. Ghi USB Linux Mint 22.x Cinnamon (linuxmint.com). Khởi động từ USB → Install Linux Mint → tiếng Việt, xóa ổ và cài.
   Tên máy đặt theo tên sẽ cấp trên Box (ví dụ `ketoan-01`) cho dễ nhận.
2. Sau khi vào máy: mở Terminal
   ```bash
   sudo apt install -y git
   git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
   ```
3. Trên Box: `sudo onebee-box them-may ketoan-01` → chép kết quả (qua USB, hoặc mở Terminal Box qua SSH rồi dán) vào
   máy trạm: `sudo mkdir -p /etc/onebee && sudo nano /etc/onebee/may-tram.env`.
4. `cd onebee && sudo ./desktop/onebee-install.sh` → khởi động lại.
5. Kiểm tra: gõ tiếng Việt, mở 1 file Word mẫu, `sudo onebee-sao-luu`, trên Box `sudo onebee-box may-tram` thấy máy ỔN.

## 3. Cách B — nhân bản cho lô máy cùng dòng
1. Làm **máy mẫu** theo cách A bước 1–2 và 4, **không** dán `may-tram.env` (mỗi máy phải có cấu hình riêng).
2. Dọn máy mẫu trước khi chụp ảnh:
   ```bash
   sudo rm -f /etc/onebee/may-tram.env /etc/onebee-hoi.conf /var/lib/onebee/sao-luu-cuoi
   sudo rm -f /etc/ssh/ssh_host_*                       # mỗi máy phải có khóa SSH riêng
   sudo truncate -s 0 /etc/machine-id && sudo rm -f /var/lib/dbus/machine-id
   sudo poweroff
   ```
3. Clonezilla: `device-image` → `savedisk` → ảnh `onebee-mau-<dòng-máy>`.
4. Mỗi máy trong lô: (sau khi đã sao lưu Windows ở mục 1) Clonezilla → `restoredisk` ảnh mẫu → khởi động vào Mint rồi:
   ```bash
   sudo hostnamectl set-hostname kho-02
   sudo systemd-machine-id-setup
   sudo ssh-keygen -A                                   # sinh khóa SSH riêng cho máy này
   ```
   Rồi làm tiếp cách A bước 3–5 (cấp tên trên Box, dán cấu hình, chạy lại bộ cài).
5. Tài khoản người dùng: máy mẫu có sẵn tài khoản → đổi mật khẩu từng máy (`passwd`) hoặc tạo tài khoản riêng cho người dùng.

## 4. Phần cứng
Ghi vào bảng dưới mỗi dòng máy đã cài: wifi, âm thanh, máy in, máy quét có chạy không. Mint dùng được phần lớn máy văn phòng,
nhưng wifi/máy in đời mới có thể cần driver riêng — thử bằng USB Mint (chế độ chạy thử, chưa cài) **trước khi** xóa Windows.

## 5. Bảng ghi thời gian và phần cứng (điền khi làm thật)
| Máy | Dòng máy / CPU / RAM / ổ | Cách | Sao lưu Windows (phút) | Cài Mint (phút) | Bộ cài OneBee (phút) | Tổng (phút) | Wifi / in / quét | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |
