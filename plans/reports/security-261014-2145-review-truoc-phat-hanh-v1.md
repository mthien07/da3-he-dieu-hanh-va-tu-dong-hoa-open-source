# Rà soát bảo mật trước phát hành v1.0.0 (14/10/2026)

**Phạm vi:** dải commit `c341bed..ed4b03b` (16057f5 → 8328dbf: CORS HTTP, gia hạn CA, xoay-khoa, `hoi` + 308, gỡ CA Firefox, tường lửa mangle/IPv6, apt) + quét toàn repo (`box/`, `desktop/`, `scripts/`, `.github/`).
**Cách làm:** skill `differential-review` (rủi ro theo diff, kịch bản tấn công cụ thể) + `ak:security` (bí mật, phụ thuộc, mẫu mã nguy hiểm), 3 agent review đọc mã + 1 agent kiểm thử; mọi phát hiện được kiểm lại bằng đọc mã hoặc chạy thật trước khi ghi.
**Kết luận:** không có lỗi Critical/High trong mã. 1 lỗi vượt ghim CA, 1 lỗi tường lửa mở toang khi mangle lỗi và 4 lỗi tính đúng/vận hành — đã sửa theo TDD. Mục 10 (vòng đời tường lửa gắn Docker, có từ trước) đã sửa theo quyết định của chủ dự án. Còn mở: mục 11 (ghi chú tài liệu). Nghiệm thu Docker trên mã cuối đạt (Box `b13d00d` 126/126, Desktop `119ec76` 71/71 — `reports/nghiem-thu-v1-docker.md`).

## Tóm tắt

| Nhóm | Critical | High | Medium | Low | Info |
|---|---|---|---|---|---|
| Bí mật / `.env` | 0 | 0 | 0 | 0 | 0 |
| Phụ thuộc | 0 | 0 | 0 | 0 | 1 |
| Mã (diff) | 0 | 0 | 6 | 5 | 1 |

## Phát hiện

| # | Mức | File | Mô tả | Kiểm chứng | Trạng thái |
|---|---|---|---|---|---|
| 1 | Medium | `desktop/ansible/roles/ai-cli/files/hoi` (`mo()`), bản giống hệt trong `onebee-bao-tinh-trang` | Ghim CA quyết định bằng `startswith("https://")` (phân biệt hoa thường) còn nhánh theo 308 dùng `urlsplit` (hạ chữ thường). Kẻ chen giữa LAN trả `308 Location: HTTPS://<IP-Box>/…` → lần mở sau dùng kho CA hệ điều hành, gửi khóa. Cùng gốc: `HOI_URL` viết `HTTPS://` không được ghim. Có từ trước a5401dd. | Tái hiện bằng test (FAIL trước khi sửa) | **Đã sửa** `1e31337` |
| 2 | Medium | `box/.../onebee-box.sh.j2` (`cmd_xoay_khoa`) | `VAO_DUOC` = SSH vào được, không phải playbook xong; playbook hỏng trên máy đang bật thì không nhắc `dong-bo-may <máy>`, máy giữ mật khẩu kho cũ (sao lưu 401 âm thầm). | Đọc mã + test FAIL trước khi sửa | **Đã sửa** `3a3ecda` |
| 3 | Medium | `box/.../docker-compose.yml.j2` | Open WebUI dùng `CORS_ALLOW_ORIGIN` cho cả Socket.IO (`SOCKETIO_CORS_ORIGINS`, v0.11.4). Ở chế độ HTTP chỉ 2 Origin được nhận → mở bằng tên DNS router, IP Tailscale trần, `localhost` qua đường hầm SSH: bắt tay WebSocket bị 403, chat thời gian thực hỏng không báo. Test chỉ kiểm vế chặn Origin lạ. | Chạy thật Open WebUI: Origin trong danh sách → `101`, `http://localhost:3000` và `http://onebee-box:3000` → `403` | **Đã sửa** `b13d00d` (biến `onebee_box_cors_them`, test chiều cho phép + WebSocket, tài liệu) |
| 4 | Medium | `desktop/.../onebee-chinh-sach-trinh-duyet.py`, `ket-noi-box/tasks/main.yml` | Gỡ CA cũ khỏi hồ sơ Firefox phụ thuộc file dấu ghi đè vô điều kiện sau `cai`: một lần gỡ hụt (thiếu certutil, home chưa mount) thì CA cũ ở lại vĩnh viễn; dấu chỉ nhớ 1 vân tay trước. | Đọc mã | **Đã sửa** `97b11f6` (gỡ tự lành theo vân tay CA hiện tại, không dựa vào dấu; không đụng CA đơn vị khác) |
| 5 | Low | `onebee-box.sh.j2` (`with_lock`) | Khóa lấy trước dấu nhắc xác nhận của `xoay-khoa` → để treo qua 23:00 thì sao lưu đêm (kèm gia hạn CA) bị bỏ không báo. | Đọc mã + test | **Đã sửa** `3a3ecda` (lấy khóa sau xác nhận) |
| 6 | Low | `onebee-box.sh.j2` (`cmd_dong_bo_may_da_chon`) | `die` khi không dựng được cấu hình → `xoay-khoa` thoát giữa chừng sau khi đã đổi mật khẩu; máy thiếu bí mật bị báo nhầm "đang tắt". | Test FAIL trước khi sửa | **Đã sửa** `3a3ecda` |
| 7 | Low | `onebee-chinh-sach-trinh-duyet.py` | `certutil -D` có thể xóa CA mới trước (cùng nickname) → số "đã gỡ" báo sai; test hiện có không chạy tới bộ lọc vân tay. CA mới được nạp lại khi Firefox khởi động (chính sách `Certificates.Install`). | Tái hiện với NSS Ubuntu 24.04 (agent review) | **Đã sửa** `97b11f6` |
| 9 | Medium | `box/.../box-firewall/files/onebee-tuong-lua` (`dung`) | `bat` gỡ hết quy tắc rồi dựng mangle TRƯỚC bước nhảy DOCKER-USER/INPUT; mangle lỗi (thiếu mô-đun, LXC) → `set -e` dừng khi chưa có bước nhảy nào: SSH/Samba/dịch vụ mở cho mọi mạng. Do 7fbc274 đưa vào. | Giả lập mangle lỗi (agent review + test FAIL trước khi sửa) | **Đã sửa** `96663cd` (dựng mangle sau cùng) |
| 10 | Medium | `onebee-tuong-lua.service` | `PartOf=docker.service` + `ExecStop=tat`: dừng/nâng cấp Docker gỡ mọi quy tắc (cả INPUT SSH/Samba và lọc Tailscale) tới khi Docker chạy lại. Có từ trước; 7fbc274 mở rộng phạm vi. | Ngữ nghĩa systemd (đọc unit + role); kiểm thật docker.io 29.1.3: Docker dùng lại `DOCKER-USER` có sẵn, giữ quy tắc qua dừng/khởi động lại | **Đã sửa** (chủ dự án chọn sửa trước phát hành): unit dựng `Before=docker.service`, bỏ `PartOf`, gỡ liên kết `docker.service.wants` cũ; unit test + bước runner dừng/bật Docker |
| 11 | Low | tài liệu tường lửa | Kết nối mới qua IPv6 tailnet bị DROP im lặng nếu chỉ khai địa chỉ 100.x; Tailscale SSH/`tailscale serve` xử lý trong tailscaled, không qua iptables. | Đọc mã + tài liệu Tailscale | Mở — bổ sung tài liệu |
| 12 | Low | `docs/kiem-thu-tren-may-that.md`, changelog, `cai-dat-onebee-box.md` | Số đo IPv6 (10,02 s / 0,01 s / ~20 s) không có file trong `reports/`; khẳng định "Windows không còn treo" khi B15 chưa chạy; sai số dòng `HOI_…`. | Đối chiếu mã + quy tắc dự án | **Đã sửa** `b819317`, `b13d00d` |
| 8 | Info | `hoi` | Không còn tự theo 302/303/307 (chặn mọi chuyển hướng); các endpoint đang gọi không chuyển hướng nên chưa ảnh hưởng. | Đọc mã | Ghi nhận |

## Đã kiểm, không có vấn đề
- **Bí mật:** không file `.env`/khóa/chứng chỉ nào được theo dõi; `.gitignore` chặn `.env`, `*.env`; không có mẫu khóa (AWS, GitHub, khóa riêng PEM…) trong mã hay **lịch sử git**; không có mật khẩu viết thẳng trong `box/`, `desktop/`, `scripts/`, `.github/`.
- **Mẫu mã nguy hiểm:** không `shell=True`, `os.system`, `eval`, `pickle`, `yaml.load`, `curl -k`, `verify=False`, `StrictHostKeyChecking=no`, quyền 777/666. Tên máy trạm kiểm `^[a-z0-9][a-z0-9-]{0,31}$` trước khi dùng trong lệnh.
- **CI:** `ci.yml` `contents: read`; `phat-hanh.yml` `contents: write` (cần để tạo bản phát hành); actions ghim SHA.
- **Phụ thuộc (Info):** công cụ CI ghim (`ansible-core 2.19.13`, `ansible-lint 26.9.0`, `yamllint 1.38.0`) không có lỗ hổng theo `pip-audit`; chỉ `pip`/`setuptools`/`wheel` hệ thống của image thử có cảnh báo (không thuộc sản phẩm). Image dịch vụ Box đã ghim tag + digest (Pha 1).
- **Tường lửa (7fbc274):** lọc kết nối MỚI từ `tailscale0` ở mangle PREROUTING chạy trước nat (cả cổng Docker qua DNAT) và trước `ts-input`; trả lời/kết nối ra ngoài là ESTABLISHED nên không bị ảnh hưởng; `bat` dựng lại từ đầu (`tat` xóa mọi bản nhảy) nên chạy nhiều lần không nhân đôi quy tắc. Giới hạn sẵn có: lưu lượng Tailscale xử lý trong tiến trình tailscaled (ví dụ Tailscale SSH) không đi qua iptables — thuộc ACL của Tailscale.
- **ae356da:** khối gia hạn CA không phụ thuộc biến của kho sao lưu; chưa gắn ổ vẫn báo LỖI như trước.
- **Không tự khóa chết:** bộ cài chỉ gọi các lệnh `onebee-box` không lấy khóa.

## Giới hạn
- Chưa chạy trên máy thật (Box Ubuntu, Mint Cinnamon, Windows): các kết luận về mạng/Tailscale dựa trên mã nguồn tailscaled 1.104 và mô phỏng trên kernel thật trong container.
- Không làm kiểm thử xâm nhập chủ động.

## Câu hỏi còn mở
- Chấp nhận việc phiên Firefox đang mở lúc xoay CA chỉ hết tin CA cũ sau khi khởi động lại Firefox (cần ghi vào hướng dẫn vận hành)?
