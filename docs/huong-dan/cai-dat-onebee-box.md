# Hướng dẫn cài OneBee Box

OneBee Box là 1 máy chủ đặt tại đơn vị, trong mạng LAN. Dịch vụ sau khi cài:

| Dịch vụ | Địa chỉ trong LAN | Dùng để |
|---|---|---|
| Trang giới thiệu | `http://<ip-box>/` | Bấm vào các dịch vụ bên dưới |
| Trợ lý AI (Open WebUI + Ollama) | `http://<ip-box>:3000` | Hỏi đáp, soạn thảo — AI chạy tại chỗ, không gửi dữ liệu ra ngoài |
| Tự động hóa (n8n) | `http://<ip-box>:5678` | Quy trình tự động |
| Giám sát (Uptime Kuma) | `http://<ip-box>:3001` | Theo dõi dịch vụ còn chạy không |
| Thư mục chung (Samba) | `smb://<ip-box>/chung` | Chia sẻ file trong đơn vị |
| Kho sao lưu máy trạm | cổng 8000 | Máy trạm OneBee OS tự sao lưu lên |

## 1. Chuẩn bị
- Máy 64-bit cài **Ubuntu Server 24.04 LTS**, nối mạng LAN, nên đặt IP cố định (trên router hoặc netplan).
- Ổ dữ liệu đủ lớn cho thư mục chung + sao lưu máy trạm. **1 ổ ngoài riêng** để Box tự sao lưu.
- Cấu hình máy cho AI: chưa chốt — đo ở phần thử nghiệm (Phase 3). Chạy được không cần card đồ họa (chậm hơn).
- **Không mở các cổng trên ra Internet ở router.** Hỗ trợ từ xa qua VPN (Tailscale/WireGuard).

## 2. Cài đặt
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee
sudo ./box/onebee-box-install.sh
```
Lần đầu tải vài GB image. Xong sẽ in địa chỉ trang giới thiệu.

## 3. Việc làm ngay sau khi cài
1. **Trợ lý AI** và **n8n**: tài khoản quản trị `quantri@onebee.lan` đã tạo sẵn, đăng ký tự do đã tắt. Mật khẩu: `sudo onebee-box in-khoa`
   (dòng `webui-admin-password`, `n8n-owner-password`). Model AI (`gemma4:e2b-it-qat`) tự tải khi cài.
2. **Uptime Kuma** (`:3001`): vẫn lấy người mở đầu tiên làm quản trị → kỹ thuật viên mở và tạo tài khoản ngay sau khi cài.
3. **Email báo cáo**: làm theo mục 4 của [dung-tro-ly-ai-va-quy-trinh-tu-dong.md](dung-tro-ly-ai-va-quy-trinh-tu-dong.md).
4. **Thư mục chung**: tài khoản `onebee`, mật khẩu xem bằng `sudo cat /etc/onebee-box/secrets/samba-onebee`.
5. **Ổ sao lưu**: gắn ổ ngoài vào `/mnt/onebee-sao-luu`. Khai báo trong `/etc/fstab` có `nofail` để máy vẫn khởi động
   khi rút ổ, ví dụ: `UUID=<uuid-ổ> /mnt/onebee-sao-luu ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2`
   (xem UUID bằng `sudo blkid`). Rồi chạy lần lượt:
   - `sudo onebee-box khoi-tao` — tạo kho sao lưu (mã hóa) trên ổ ngoài
   - `sudo onebee-box in-khoa` — **in khóa ra giấy hoặc chép USB, cất két**. Hỏng ổ Box mà mất khóa thì bản sao lưu vô dụng.
   - `sudo onebee-box khoi-phuc-thu` — phải thấy dòng `ĐẠT`
   Chưa gắn ổ thì lệnh sao lưu **từ chối chạy** (không ghi vào ổ hệ thống) — lịch 23:00 sẽ báo lỗi trong nhật ký.

## 4. Cấp cho máy trạm (sao lưu, Trợ lý AI, quản lý tập trung)
Trên Box:
```bash
sudo onebee-box them-may ketoan-01
```
Dán các dòng in ra (9 dòng: `MAY_TRAM`, `BOX_IP`, `RESTIC_…`, `HOI_…`, `TINH_TRANG_…`, `QUAN_TRI_SSH_KEY`) vào máy trạm tại
`/etc/onebee/may-tram.env`, rồi chạy lại `sudo ./desktop/onebee-install.sh` trên máy trạm. Máy trạm sẽ:
- tự sao lưu `/home` lúc 12:00 hằng ngày (máy tắt thì chạy bù khi bật); sao lưu ngay: `sudo onebee-sao-luu`;
- dùng được lệnh `hoi` (Trợ lý AI chưa chạy lúc cấp thì thiếu 2 dòng `HOI_…` — chạy lại lệnh sau);
- báo tình trạng về Box mỗi giờ và cho Box vào cập nhật qua SSH — xem [quan-ly-may-tram.md](quan-ly-may-tram.md).
Máy trạm cài bản v0.1 (file `sao-luu.env`) được bộ cài tự đổi tên sang `may-tram.env`.

## 5. Lệnh quản trị
| Lệnh | Việc |
|---|---|
| `sudo onebee-box trang-thai` | Dịch vụ đang chạy, dung lượng ổ |
| `sudo onebee-box them-may <tên>` | Cấp cho máy trạm: sao lưu, khóa Trợ lý AI, quản lý tập trung |
| `sudo onebee-box may-tram` | Tình trạng các máy trạm (sao lưu, cập nhật, ổ đĩa, liên lạc cuối) |
| `sudo onebee-box cap-nhat-may <tên>` / `--tat-ca` | Cập nhật phần mềm máy trạm từ Box |
| `sudo onebee-box dong-bo-tro-ly` | Tạo/cập nhật "Trợ lý OneBee" trong Open WebUI |
| `sudo onebee-box dat-mat-khau-email` / `email-thu` | Đặt mật khẩu hộp thư gửi / gửi email thử |
| `sudo onebee-box khoi-tao` | Tạo kho sao lưu Box trên ổ ngoài (1 lần) |
| `sudo onebee-box sao-luu` | Sao lưu Box ra ổ ngoài ngay + dọn bản cũ (tự chạy 23:00 hằng ngày) |
| `sudo onebee-box in-khoa` | In khóa bí mật để cất ngoài Box |
| `sudo onebee-box khoi-phuc-thu` | Thử khôi phục 1 file — kiểm tra sao lưu dùng được |

## Khôi phục toàn bộ khi hỏng ổ Box (tóm tắt)
1. Cài lại Ubuntu Server 24.04 + chạy `sudo ./box/onebee-box-install.sh`.
2. Gắn ổ sao lưu; lấy khóa `restic-box` từ bản in (`in-khoa`).
3. `sudo systemctl stop docker`; khôi phục 2 nhóm dữ liệu:
   `RESTIC_REPOSITORY=/mnt/onebee-sao-luu/restic-box restic restore latest --tag onebee-box,csdl --target /`
   và `... restic restore latest --tag onebee-box,chung --target /`
4. `sudo systemctl start docker && cd /opt/onebee-box && sudo docker compose up -d`.
Chưa diễn tập quy trình này trên máy thật — cần làm ở Phase 5.

## Quyền riêng tư
Box giữ mật khẩu kho sao lưu của từng máy trạm (để tự dọn bản cũ) → người quản trị Box **đọc được** bản sao lưu `/home`
của mọi máy. Box còn có **quyền quản trị (root) trên máy trạm** qua SSH để cập nhật. Cần thông báo 2 điều này cho đơn vị
khi triển khai, và giữ Box kín (chỉ kỹ thuật viên có mật khẩu).

## Giới hạn đã biết
- Chưa giới hạn dung lượng từng máy trạm trên Box; theo dõi bằng `sudo onebee-box trang-thai`.
- Sao lưu lỗi được báo qua email (cần cấu hình email); nhật ký: `journalctl -u onebee-box-sao-luu`.
- Chưa kiểm trên máy thật; đã kiểm tự động trong container "Ubuntu 24.04 + systemd" (xem `tests/box/`).
- HTTP trong LAN, chưa có TLS nội bộ.
- Chưa có bản sao ngoài đơn vị (chưa đủ quy tắc 3-2-1).
- Uptime Kuma chưa cài sẵn danh sách theo dõi — thêm tay ở lần đầu.
