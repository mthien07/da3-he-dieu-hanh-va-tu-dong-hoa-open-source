# Tự thử OneBee OS trên máy ảo (VirtualBox / VMware) — danh sách kiểm tra

Dành cho người thử bản phát hành trước khi cài cho đơn vị thật. Làm theo thứ tự, đánh dấu từng ô; ô nào không đạt ghi lại
(ảnh chụp màn hình + dòng lệnh + nội dung lỗi) và gửi kỹ thuật.

## 0. Chuẩn bị (1 lần)
- Máy thật: CPU hỗ trợ ảo hóa (bật VT-x/AMD-V trong BIOS), RAM ≥ 16 GB (Box cần nhiều RAM cho AI), ổ trống ≥ 120 GB.
- Tải: Linux Mint 22.3 Cinnamon (linuxmint.com), Ubuntu Server 24.04 LTS (ubuntu.com). Kiểm SHA256 theo trang tải.
- Mạng của 2 máy ảo: **Bridged** (cầu nối) để chúng thấy nhau như 2 máy trong LAN thật.

| Máy ảo | CPU | RAM | Ổ | Ghi chú |
|---|---|---|---|---|
| `box` — Ubuntu Server 24.04 | 4 | 8–12 GB | 60 GB + **1 ổ thứ 2 20 GB** (làm "ổ sao lưu ngoài") | Chọn cài OpenSSH server khi cài Ubuntu |
| `ketoan-01` — Linux Mint 22.3 | 2 | 4 GB | 40 GB | Tiếng Việt, múi giờ Hồ Chí Minh |

## 1. Cài Box (máy ảo `box`)
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee && cd onebee
sudo ./box/onebee-box-install.sh          # lần đầu tải vài GB, 15–40 phút tùy mạng
```
- [ ] Cài xong, in dòng `[OneBee Box] Hoàn tất`. Chạy lại lần 2: xong nhanh, không lỗi.
- [ ] Từ máy thật mở `http://<ip-box>/` thấy trang OneBee Box; `:3000` Trợ lý AI; `:5678` n8n; `:3001` Uptime Kuma.
- [ ] `sudo onebee-box in-khoa` → đăng nhập được 3 trang trên bằng `quantri@onebee.lan` (Uptime Kuma: tài khoản `quantri`)
      với mật khẩu dòng `webui-admin-password`, `n8n-owner-password`, `uptime-kuma-password`. **Không** trang nào mời "tạo tài khoản quản trị".
- [ ] Trợ lý AI: chọn "Trợ lý OneBee", hỏi "soạn thông báo họp HTX sáng thứ Hai" → trả lời tiếng Việt. **Ghi thời gian chờ chữ đầu tiên**
      và thời gian trả lời xong (đây là số đo tốc độ AI còn thiếu).
- [ ] Uptime Kuma: thấy 5 mục theo dõi, đều xanh.

**Ổ sao lưu:** gắn ổ thứ 2: `sudo mkfs.ext4 /dev/sdb` (kiểm đúng tên ổ bằng `lsblk`!), thêm vào `/etc/fstab` theo
[cai-dat-onebee-box.md](cai-dat-onebee-box.md) mục 3, `sudo mount -a`, rồi:
- [ ] `sudo onebee-box khoi-tao` → `sudo onebee-box in-khoa > ~/khoa.txt` (giả làm bản in) → `sudo onebee-box khoi-phuc-thu` thấy `ĐẠT`.

**Email (tùy chọn, cần tài khoản Gmail có "mật khẩu ứng dụng"):** theo [dung-tro-ly-ai-va-quy-trinh-tu-dong.md](dung-tro-ly-ai-va-quy-trinh-tu-dong.md) mục 4.
- [ ] `sudo onebee-box email-thu` → email tới (xem cả mục Spam).

## 2. Cài máy trạm (máy ảo `ketoan-01`)
- [ ] Trước khi cài Box: khai `onebee_box_ma_don_vi` (viết tắt tên khách) và `onebee_box_dia_chi` trong `box/ansible/group_vars/all.yml` — thiếu mã thì bộ cài dừng
- [ ] Trên Box: `sudo onebee-box them-may ketoan-01` → chép 12 dòng (gồm `BOX_CA`, `BOX_CA_VAN_TAY`, `BOX_HTTPS`) vào máy trạm `/etc/onebee/may-tram.env` (`sudo nano`).
- [ ] Máy trạm: `git clone …` như trên → `sudo ./desktop/onebee-install.sh` → khởi động lại.
- [ ] Sau khi khởi động: giao diện tiếng Việt, hình nền OneBee; **Super + Space** đổi gõ tiếng Việt; gõ Telex "Hợp tác xã" đúng dấu.
- [ ] LibreOffice Writer: gõ vài dòng, Ctrl+S → mặc định lưu .docx, không hỏi định dạng. Mở 1 file Word thật của anh → bố cục có lệch không?
- [ ] Terminal: `hoi cách xuất file PDF` → có câu trả lời.
- [ ] `sudo onebee-sao-luu` → "Sao lưu xong".
- [ ] Menu có **"Báo cần hỗ trợ (OneBee)"** (mở biểu mẫu, gửi thử → email tới người nhận nếu đã cấu hình email) và **"Cho phép hỗ trợ từ xa (OneBee)"**.

## 3. Quản lý từ Box
- [ ] Đợi ~5 phút sau khi máy trạm khởi động → Box: `sudo onebee-box may-tram` thấy `ketoan-01` và tình trạng.
- [ ] `sudo onebee-box cap-nhat-may ketoan-01` → lần đầu in "Đã ghim khóa SSH của ketoan-01", cập nhật xong, không hỏi mật khẩu; lần 2 không ghim lại.
- [ ] `sudo onebee-box may-tram` không còn cảnh báo "chưa có chữ ký" sau khi máy chạy lại bộ cài; `sudo onebee-box thu-hoi-may` rồi `them-may` cấp lại được.
- [ ] Hỗ trợ từ xa: máy trạm bấm "Cho phép hỗ trợ từ xa" → từ máy thật dùng TigerVNC Viewer / Remmina vào `<ip-máy-trạm>:5900`, nhập mã
      → máy trạm hỏi "Cho phép?" → bấm Cho phép → xem được màn hình. Thử cả mã sai và bấm Từ chối.
- [ ] `sudo onebee-box bao-cao-tuan` → nhật ký tuần có yêu cầu hỗ trợ vừa gửi thử.

## 4. Diễn tập hỏng ổ Box (quan trọng — nên làm trước khi bán)
1. Chụp nhanh (snapshot) máy ảo `box` để quay lại được.
2. Tạo vài dữ liệu: file trong thư mục chung, 1 yêu cầu hỗ trợ, 1 đơn hàng. `sudo onebee-box sao-luu`.
3. Cài lại Ubuntu Server trên ổ hệ thống của `box` (giữ nguyên ổ thứ 2), cài lại Box, gắn lại ổ thứ 2.
4. `sudo onebee-box khoi-phuc-toan-bo ~/khoa.txt` (chép file khóa vào trước) → chạy lại bộ cài → `sudo onebee-box khoi-phuc-thu`.
- [ ] Đăng nhập bằng **mật khẩu cũ**, thấy lại dữ liệu; máy trạm `hoi` và `sudo onebee-sao-luu` chạy tiếp mà không sửa gì.

## 5. Đo trước/sau (nếu thử trên máy thật cũ)
Theo [do-truoc-sau.md](do-truoc-sau.md). Máy ảo **không** dùng để lấy số tốc độ đưa vào tài liệu bán hàng.

## Đã kiểm tự động (không cần thử lại bằng tay)
Các mục trên đều đã có kiểm thử tự động trong container (xem `tests/README.md`). Chưa kiểm được tự động: phiên Cinnamon thật (thanh bộ gõ,
hộp thoại, thông báo), phần cứng, mạng LAN thật, email qua máy chủ thư thật, **tốc độ AI**, VNC viewer thật.
