---
phase: 4
title: "Màn hình khởi động Plymouth"
status: completed
priority: P2
effort: "0.5d"
dependencies: [1]
---

# Giai đoạn 4: Màn hình khởi động Plymouth

## Mục tiêu
Máy trạm bật lên hiện logo OneBee (nền tối, logo, thanh tiến trình mảnh màu mật ong) thay màn hình khởi động của Mint. Máy đã cài chỉ cần chạy lại `onebee-install.sh`.

## Tệp được sửa
- Tạo: `desktop/ansible/roles/theme/files/plymouth/onebee.plymouth`, `onebee.script`, `logo.png`, `thanh-nen.png`, `thanh-tien-trinh.png`.
- Tạo: `desktop/ansible/roles/theme/tasks/man-hinh-khoi-dong.yml`; thêm một dòng `include_tasks` vào `tasks/main.yml`.
- Tạo: `tests/desktop/test_onebee_man_hinh_khoi_dong.py`; thêm mục kiểm vào `tests/desktop/verify-desktop-install.sh`.
- Không sửa: GRUB, hình nền, trang chủ Box.

## Các bước (test trước)
1. Test đơn vị đọc `man-hinh-khoi-dong.yml`: cài `plymouth` + `plymouth-themes`; chép chủ đề vào `/usr/share/plymouth/themes/onebee/`; đặt chủ đề mặc định bằng `update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth ... 150` rồi `--set`; chỉ chạy `update-initramfs -u` khi vừa đổi (đảm bảo lần 2 `changed=0`); bỏ qua cả khối khi máy không có `/usr/share/plymouth` (container CI); `.plymouth` trỏ đúng `ScriptFile`.
2. Chủ đề dạng `script` (không cần OpenGL, chạy được trên máy cũ): nền màu tối, logo giữa màn hình, thanh tiến trình mảnh dưới logo, mật ong `#F5A524`.
3. Máy ảo: `plymouthd --debug` + `plymouth show-splash` để xem thử không cần khởi động lại; sau đó khởi động lại thật một lần, chụp màn hình.
4. Lời nhắn cuối bộ cài nhắc: "Màn hình khởi động mới hiện ở lần bật máy kế tiếp."

## Kiểm chứng
- `pytest tests/desktop -q` đạt; `yamllint` + `ansible-lint` sạch; container Mint cài 2 lần, lần 2 `changed=0`.
- Máy ảo: ảnh chụp màn hình khởi động mới; máy vẫn vào được desktop.

## Rủi ro
- Chủ đề lỗi làm màn hình đen lúc khởi động (không làm hỏng khởi động). Hoàn tác: `update-alternatives --set default.plymouth <đường dẫn Mint>` rồi `update-initramfs -u`; ghi vào chú thích đầu tệp tác vụ.

## Todo
- [ ] Test trượt trước, đạt sau
- [ ] Chủ đề Plymouth + tác vụ Ansible
- [ ] Container 2 lần `changed=0`; ảnh chụp máy ảo
