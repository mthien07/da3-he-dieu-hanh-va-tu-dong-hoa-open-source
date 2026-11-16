---
phase: 3
title: "Máy trạm: hình nền OneBee hiện ngay sau khi cài"
status: completed
priority: P1
effort: "1d"
dependencies: [1]
---

# Giai đoạn 3: Máy trạm — hình nền OneBee hiện ngay sau khi cài

## Mục tiêu
Người chạy `sudo ./onebee-install.sh` trong phiên Cinnamon thấy màn hình nền OneBee mới ngay khi lệnh xong; các tài khoản khác thấy ở lần đăng nhập kế tiếp; người dùng tự đổi sau đó thì được giữ.

## Tệp được sửa
- Sửa: `desktop/ansible/roles/theme/files/onebee-wallpaper.svg`, `onebee-wallpaper.png` (thay bằng bản đã duyệt, cùng đường dẫn đích), `desktop/ansible/roles/theme/tasks/main.yml`.
- Tạo: `desktop/ansible/roles/theme/files/onebee-ap-giao-dien` (script áp giao diện một lần cho người dùng), `tests/desktop/test_onebee_ap_giao_dien.py`.
- Sửa: `desktop/onebee-install.sh` (bước cuối áp ngay cho phiên đang mở, đổi lời nhắn cuối), `tests/desktop/verify-desktop-install.sh` (thêm mục kiểm).
- Không sửa: `box/`, bố cục thanh tác vụ, phím tắt.

## Các bước
### 3.1 Chứng minh nguyên nhân (trước khi sửa)
Trên máy ảo Mint 22 có giao diện, tài khoản đã đăng nhập, cài bản hiện tại bằng terminal rồi ghi lại:
- `gsettings get org.cinnamon.desktop.background picture-uri` (trong phiên người dùng) trước và sau khi cài;
- `dconf read /org/cinnamon/desktop/background/picture-uri` (giá trị riêng của người dùng, nếu có);
- màn hình có đổi không, trước và sau đăng xuất/đăng nhập lại.
Ghi kết quả vào `plans/.../reports/`. Nếu nguyên nhân khác giả thuyết trong `plan.md` (giá trị người dùng đè mặc định / phiên chưa đọc lại schema) thì DỪNG, báo lại để chọn cách sửa.

### 3.2 Script áp giao diện một lần (test trước)
`onebee-ap-giao-dien` (bash, shellcheck sạch), chạy **bằng quyền người dùng** trong phiên của họ:
- Nếu `~/.local/state/onebee/giao-dien` chứa đúng phiên bản giao diện hiện tại → thoát, không đổi gì.
- Nếu chưa: `gsettings set org.cinnamon.desktop.background picture-uri 'file:///usr/share/backgrounds/onebee/onebee-wallpaper.png'` và `picture-options 'zoom'`, rồi ghi phiên bản vào tệp đánh dấu.
- Phiên bản giao diện là một hằng trong script (ví dụ `2`): lần sau đổi hình nền chỉ cần tăng số để áp lại một lần; còn lại người dùng tự đổi thì giữ.
Test `test_onebee_ap_giao_dien.py` chạy script với `gsettings` giả trong `PATH` và `HOME` tạm: lần 1 gọi `gsettings set` 2 lần + tạo tệp đánh dấu; lần 2 không gọi; tệp đánh dấu phiên bản cũ → áp lại.

### 3.3 Hai đường áp
- **Đăng nhập kế tiếp:** `/etc/xdg/autostart/onebee-ap-giao-dien.desktop` gọi script (mọi tài khoản, kể cả tài khoản tạo sau).
- **Ngay khi cài xong:** cuối `onebee-install.sh`, với mỗi phiên đồ họa đang mở (`loginctl list-sessions` → `Type` là `x11`/`wayland`, `Class=user`), chạy script bằng `runuser -u <người dùng>` với `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus`. Không có phiên đồ họa (máy chủ, container CI) → bỏ qua, không lỗi.
- Đổi lời nhắn cuối: "Đã áp giao diện OneBee. Khởi động lại máy để áp dụng ngôn ngữ và bộ gõ tiếng Việt."

### 3.4 Hình nền mới
- Thay `onebee-wallpaper.svg` và `onebee-wallpaper.png` (1920×1080) bằng bản đã duyệt; ghi lệnh xuất PNG từ SVG vào chú thích đầu SVG.
- Màn hình đăng nhập và màn hình khóa dùng cùng tệp nên tự đổi theo; kiểm lại ở giai đoạn 4.

### 3.5 Kiểm
- `~/.cache/onebee-kiem/bin/python -m pytest tests/desktop -q` đạt; `shellcheck desktop/onebee-install.sh desktop/ansible/roles/theme/files/onebee-ap-giao-dien`; `yamllint` + `ansible-lint` sạch.
- `verify-desktop-install.sh` thêm: có `/etc/xdg/autostart/onebee-ap-giao-dien.desktop`, script chạy được, PNG đúng kích thước.
- `tests/desktop/run-desktop-test-in-mint-container.sh`: cài 2 lần, lần 2 `changed=0`.

## Rủi ro
- `runuser` + D-Bus sai người dùng → đổi hình nền nhầm tài khoản. Chỉ lấy người dùng từ chính phiên `loginctl`, không từ `SUDO_USER`.
- Phiên Wayland thử nghiệm của Cinnamon: `gsettings` vẫn qua D-Bus, kiểm ở giai đoạn 4 nếu máy ảo có.

## Todo
- [ ] 3.1 Báo cáo nguyên nhân trên máy ảo
- [ ] 3.2 Script + test (trượt trước, đạt sau)
- [ ] 3.3 Autostart + bước áp ngay trong bộ cài
- [ ] 3.4 Hình nền mới
- [ ] 3.5 Lint, test, container 2 lần `changed=0`
