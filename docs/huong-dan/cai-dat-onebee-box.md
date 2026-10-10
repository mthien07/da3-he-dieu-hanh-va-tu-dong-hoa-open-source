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
- **Tường lửa tự bật khi cài**: chỉ máy cùng mạng LAN với Box (vd `192.168.1.0/24`) vào được các dịch vụ trên, kể cả
  thư mục chung và SSH. Máy ở mạng khác (Wi-Fi khách tách mạng, mạng ngoài) bị chặn. Đơn vị có nhiều mạng (vd phòng kế toán
  `192.168.2.0/24`): khai báo trong `box/ansible/group_vars/all.yml` → `onebee_box_lan_cho_phep: ["192.168.1.0/24", "192.168.2.0/24"]`
  rồi chạy lại bộ cài. Xem quy tắc: `sudo onebee-tuong-lua xem`. Lưu ý: Wi-Fi khách **cùng mạng** với máy văn phòng thì
  tường lửa không phân biệt được — nên tách Wi-Fi khách ra mạng riêng trên router.
  Tường lửa lọc **mọi cổng mạng** trừ `lo` và mạng Docker: qua cổng mạng chính chỉ mạng LAN cho phép; card mạng phụ, `wg0`, `tun0` bị chặn hết;
  qua **Tailscale** chỉ máy kỹ thuật khai trong `onebee_box_tailscale_cho_phep` (vd `["100.64.1.2"]`) vào được web/SSH/thư mục chung — để trống là chặn hết kết nối Tailscale
  (bộ cài cảnh báo nếu Box đang nối Tailscale mà chưa khai). Nên đặt thêm ACL phía Tailscale: `tag:kythuat` → Box tcp 22, 80, 443, 3000, 5678, 3001; thiết bị khác trong tailnet không vào được Box.
  Đổi dải IP của mạng LAN (thay router): khởi động lại Box hoặc chạy `sudo systemctl restart onebee-tuong-lua` để tường lửa nhận dải mới.

## 2. Cài đặt
**Trước khi chạy bộ cài**, mở `box/ansible/group_vars/all.yml` và khai 2 giá trị (bộ cài dừng và báo rõ nếu thiếu):
- `onebee_box_ma_don_vi`: **viết tắt tên khách hàng** (chữ thường không dấu, số, gạch giữa; ví dụ `anphu`). Mã nằm trong chứng chỉ CA riêng của Box
  (chỉ cho phép tên `<mã>.onebee.internal`), nên mỗi khách một mã khác nhau.
- `onebee_box_dia_chi`: **IP tĩnh của Box** (cùng giá trị bạn đặt "giữ IP cố định" trên router hoặc netplan). Để trống thì bộ cài lấy IP hiện có
  và cảnh báo. IP và mã nằm trong CA: **đổi một trong hai = xoay CA** (mọi máy trạm phải nhận CA mới) — hãy chốt trước khi cấp máy.

Bộ cài sinh **CA riêng của Box** (khóa gốc ở `/etc/onebee-box/secrets/ca/`, có trong bản sao lưu Box, không gắn vào container nào). CA bị ràng buộc
tên: chỉ cấp được chứng chỉ cho IP của Box và `<mã>.onebee.internal`. Dịch vụ vẫn chạy HTTP ở giai đoạn này; máy trạm nhận CA qua `them-may`/`dong-bo-may`.
Xem vân tay CA để đối chiếu khi cài CA lên máy quản lý/laptop kỹ thuật: `sudo onebee-box in-ca` (cũng nằm ở dòng cuối `in-khoa`).
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee
sudo ./box/onebee-box-install.sh
```
Lần đầu tải vài GB image. Xong sẽ in địa chỉ trang giới thiệu:

![Trang giới thiệu OneBee Box](anh/01-trang-gioi-thieu-box.png)

### Bật HTTPS (khuyến nghị — chưa bật mặc định)
Mật khẩu và khóa đang đi qua LAN dạng rõ ở chế độ HTTP. Bật HTTPS (CA riêng của Box + Caddy, xem `docs/adr/0005-https-noi-bo-caddy-ca-rang-buoc-ten.md`):
1. Cài/cập nhật Box như trên → bộ cài tự đẩy CA xuống mọi máy trạm đã cấp (máy tắt thì bật lên rồi `sudo onebee-box dong-bo-may --tat-ca`).
2. Kiểm: `sudo onebee-box may-chua-nhan-ca` không in tên máy nào.
3. Đặt `onebee_box_https: true` trong `box/ansible/group_vars/all.yml`, chạy lại bộ cài. Nếu còn máy chưa nhận CA, bộ cài **giữ HTTP** và nêu tên máy.
4. Từ đó dùng `https://<ip-box>[:cổng]`; các cổng 3000/5678/3001/8000 do Caddy giữ (cổng backend đóng hẳn); `http://` tới các cổng này tự chuyển sang `https://`.
   Máy trạm nhận URL https + chứng chỉ CA, Firefox mở sẵn Box bằng https. **Máy tắt lúc chuyển**: bật lên rồi `sudo onebee-box dong-bo-may <tên>` (trong 30 ngày với máy đã ghim khóa SSH).
5. **Thiết bị không do OneBee quản lý** (laptop kỹ thuật, điện thoại, máy của quản lý): tải `http://<ip-box>/onebee-ca.crt`, đối chiếu vân tay SHA-256 với `sudo onebee-box in-ca` (hoặc bản in `in-khoa`) rồi mới cài.
   Sau khi đã cài, **mọi** cảnh báo chứng chỉ ở địa chỉ Box là dấu hiệu bị tấn công — không bấm "tiếp tục", báo kỹ thuật.
6. Kỹ thuật vào Box qua Tailscale: thêm dòng `/etc/hosts` `<IP Tailscale của Box> box.<mã đơn vị>.onebee.internal`, mở `https://box.<mã đơn vị>.onebee.internal:3000` (mở bằng IP 100.x trần không dùng được).
   Mỗi khách dùng **một hồ sơ Firefox riêng** (CA của khách A chỉ cấp cho tên của khách A, nhưng các khách hay trùng dải `192.168.1.x`).
7. Hoàn tác: `onebee_box_https: false` → chạy lại bộ cài (máy trạm tự nhận cờ `BOX_HTTPS=0`, về HTTP).
Hết hạn CA trung gian (1 năm) được gia hạn tự động mỗi đêm sao lưu; `sudo onebee-box trang-thai` hiện số ngày còn lại.

### Thư mục chung (Samba): chỉ SMB 3.1.1 + mã hóa
Từ bản này thư mục chung bắt buộc **SMB 3.1.1 và mã hóa** (`server min protocol = SMB3_11`, `server smb encrypt = required`): giữ nguyên nội dung khi đi qua LAN, chống hạ cấp.
Chỉ **Windows 10 trở lên và Linux** nối được. Máy Windows 7/8, máy photocopy/quét cũ **không** nối được — nếu cần, đặt `onebee_box_samba_smb3: false` (chấp nhận bỏ bảo vệ này).
Thử trước trên 1 máy Windows 10 và 1 máy Linux Mint rồi mới áp cho cả đơn vị; kiểm trên Box: `sudo smbstatus` (cột Encryption/Protocol).

## 3. Việc làm ngay sau khi cài
0. **SSH vào Box chỉ bằng khóa** (Box giữ khóa vào được mọi máy trạm): từ máy kỹ thuật `ssh-copy-id <tài-khoản>@<ip-box>`,
   thử `ssh <tài-khoản>@<ip-box>` vào được, rồi chạy lại `sudo ./box/onebee-box-install.sh` → Box tắt đăng nhập SSH bằng mật khẩu
   và không cho root. Chưa có khóa thì bộ cài giữ nguyên mật khẩu và in cảnh báo (không tự khóa anh ở ngoài).
1. **Trợ lý AI** và **n8n**: tài khoản quản trị `quantri@onebee.lan` đã tạo sẵn, đăng ký tự do đã tắt. Mật khẩu: `sudo onebee-box in-khoa`
   (dòng `webui-admin-password`, `n8n-owner-password`). Model AI (`gemma4:e2b-it-qat`) tự tải khi cài.
2. **Giám sát (Uptime Kuma, `:3001`)**: tài khoản `quantri` tạo sẵn (mật khẩu dòng `uptime-kuma-password`), đã có 5 mục theo dõi
   các dịch vụ của Box; khi đã cấu hình email, dịch vụ nào ngừng sẽ có email báo.
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
Dán các dòng in ra (12 dòng (gồm `BOX_CA`, `BOX_CA_VAN_TAY`, `BOX_HTTPS`): `MAY_TRAM`, `BOX_IP`, `RESTIC_…`, `HOI_…`, `TINH_TRANG_…`, `QUAN_TRI_SSH_KEY`) vào máy trạm tại
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
| `sudo onebee-box cap-nhat-may <tên>` / `--tat-ca` | Cập nhật phần mềm máy trạm từ Box (lần đầu máy phải chứng minh rồi mới ghim khóa SSH) |
| `sudo onebee-box dong-bo-may <tên>` / `--tat-ca` | Đẩy lại cấu hình (`may-tram.env`) từ Box xuống máy trạm |
| `sudo onebee-box thu-hoi-may <tên>` | Thu hồi máy (mất máy, nghỉ việc, nghi giả mạo); giữ kho sao lưu |
| `sudo onebee-box ghim-lai-may <tên>` | Máy cài lại hệ điều hành: bỏ khóa SSH đã ghim để ghim lại |
| `sudo onebee-box bao-cao-tuan [YYYY-MM-DD]` | Nhật ký tuần: yêu cầu hỗ trợ, khảo sát, tình trạng máy (ẩn tên) |
| `sudo onebee-box dong-bo-tro-ly` | Tạo/cập nhật "Trợ lý OneBee" trong Open WebUI |
| `sudo onebee-box dat-mat-khau-email` / `email-thu` | Đặt mật khẩu hộp thư gửi / gửi email thử |
| `sudo onebee-box khoi-tao` | Tạo kho sao lưu Box trên ổ ngoài (1 lần) |
| `sudo onebee-box sao-luu` | Sao lưu Box ra ổ ngoài ngay + dọn bản cũ (tự chạy 23:00 hằng ngày) |
| `sudo onebee-box in-khoa` | In khóa bí mật để cất ngoài Box |
| `sudo onebee-box khoi-phuc-thu` | Thử khôi phục 1 file — kiểm tra sao lưu dùng được |
| `sudo onebee-box khoi-phuc-toan-bo [file-khóa]` | Hỏng ổ Box: lấy lại toàn bộ trên Box cài lại (mục dưới) |

## Khôi phục toàn bộ khi hỏng ổ Box
1. Cài lại Ubuntu Server 24.04 + chạy `sudo ./box/onebee-box-install.sh` (như máy mới).
2. Gắn ổ sao lưu cũ vào `/mnt/onebee-sao-luu` (mục 3). Chép file khóa đã in từ `in-khoa` (hoặc gõ tay dòng `restic-box`).
3. `sudo onebee-box khoi-phuc-toan-bo /đường/dẫn/khoa.txt` — lấy lại dữ liệu Trợ lý AI, n8n, giám sát, sổ hỗ trợ, thư mục chung,
   toàn bộ khóa bí mật (mật khẩu cũ dùng lại được), khóa SSH quản trị máy trạm.
4. Chạy lại bộ cài, rồi `sudo onebee-box khoi-phuc-thu`. **Máy trạm không phải làm gì**: sao lưu, `hoi`, cập nhật từ Box chạy tiếp
   (kho sao lưu máy trạm là bản sao nên không nằm trong bản sao lưu Box — máy trạm tự tạo kho mới ở lần sao lưu sau).
Đã diễn tập tự động trong container (`tests/box/check-khoi-phuc-toan-bo.sh`); nên diễn tập 1 lần trên máy ảo trước khi bán.

## Nâng cấp phiên bản dịch vụ
Phiên bản các dịch vụ (Caddy, Ollama, Open WebUI, n8n, Uptime Kuma, rest-server) ghim cả **tag lẫn digest** trong
`box/ansible/group_vars/all.yml` (`onebee_box_images`). Nâng cấp = sửa cả hai rồi chạy lại bộ cài. Với n8n, mỗi lần đổi image bộ cài
**tự dừng n8n và chép nguyên thư mục dữ liệu** sang `/srv/onebee/n8n.truoc-<phiên-bản-cũ>` (n8n chạy migration CSDL khi khởi động,
không quay lui được). Hoàn tác: `docker compose stop n8n` (trong `/opt/onebee-box`) → xóa `/srv/onebee/n8n` → đổi tên thư mục chép về
`/srv/onebee/n8n` → ghim lại image cũ → chạy lại bộ cài. Thư mục chép không tự xóa — xóa tay khi đã dùng ổn:
`sudo rm -rf /srv/onebee/n8n.truoc-*`. n8n 2.40.x đã ngừng nhận bản vá (bản cuối 2.40.7).

## Quyền riêng tư
Box giữ mật khẩu kho sao lưu của từng máy trạm (để tự dọn bản cũ) → người quản trị Box **đọc được** bản sao lưu `/home`
của mọi máy. Box còn có **quyền quản trị (root) trên máy trạm** qua SSH để cập nhật. Cần thông báo 2 điều này cho đơn vị
khi triển khai, và giữ Box kín (chỉ kỹ thuật viên có mật khẩu). Chat Trợ lý AI của nhân viên: tài khoản quản trị Open WebUI bị chặn
không xem/xuất được, nhưng quản trị vẫn đặt lại được mật khẩu nhân viên rồi đăng nhập, và người có root trên Box vẫn đọc được
file dữ liệu — cũng cần nói rõ với đơn vị.

## Giới hạn đã biết
- Chưa giới hạn dung lượng từng máy trạm trên Box; theo dõi bằng `sudo onebee-box trang-thai`.
- Sao lưu lỗi được báo qua email (cần cấu hình email); nhật ký: `journalctl -u onebee-box-sao-luu`.
- Chưa kiểm trên máy thật; đã kiểm tự động trong container "Ubuntu 24.04 + systemd" (xem `tests/box/`).
- HTTP trong LAN, chưa có TLS nội bộ.
- Chưa có bản sao ngoài đơn vị (chưa đủ quy tắc 3-2-1).
- Giám sát chưa theo dõi Samba và chính máy Box (CPU, ổ đĩa) — ổ đĩa Box xem bằng `sudo onebee-box trang-thai`.
