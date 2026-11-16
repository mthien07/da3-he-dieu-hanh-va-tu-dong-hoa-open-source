---
phase: 5
title: "Kiểm trên máy ảo và gộp"
status: pending
priority: P1
effort: "0.5d"
dependencies: [2, 3, 4]
---

# Giai đoạn 5: Kiểm trên máy ảo và gộp

## Mục tiêu
Xác nhận trên máy thật/ảo rằng trang chủ mới chạy đúng trên Box và máy trạm hiện giao diện OneBee ngay sau khi cài; gộp vào nhánh tích hợp.

## Các bước
1. Người điều phối gộp PR giai đoạn 2, 3 và 4 vào `feat/giao-dien-toi-gian`; chạy toàn bộ `tests/box` và `tests/desktop` đơn vị.
2. CI `gh workflow run ci.yml --ref feat/giao-dien-toi-gian -f box=true` → xanh (bài kiểm Box đầy đủ vẫn đạt với trang chủ mới).
3. Máy ảo Mint 22 có giao diện (anh Thiện bật):
   - Phiên đã đăng nhập, chạy `sudo ./onebee-install.sh` trong terminal → chụp màn hình ngay khi lệnh xong: hình nền OneBee mới.
   - Đổi hình nền bằng Cài đặt, chạy lại bộ cài → hình nền của người dùng được giữ; lần 2 `changed=0`.
   - Tạo tài khoản thứ hai, đăng nhập → hình nền OneBee; khóa màn hình và đăng xuất → màn hình khóa, đăng nhập dùng hình mới.
4. Mở trang chủ Box trên máy trạm (Firefox) bằng `onebee.local` và bằng `https://box.<mã>.onebee.internal/` → chụp ảnh sáng và tối; số liệu cập nhật; thẻ Sổ điều hành mở được.
5. Ghi báo cáo + ảnh vào `plans/261116-2242-giao-dien-toi-gian-box-va-may-tram/reports/`; mở PR `feat/giao-dien-toi-gian` → `feat/dx-os-tich-hop` để anh duyệt. Không tự gộp vào `main`, không gắn tag.
6. Tắt máy ảo và dọn container/trình duyệt thử sau khi xin phép anh.

## Kiểm chứng
- CI `box=true` xanh; đủ ảnh chụp cho kết quả 5, 6, 7 của `plan.md`; anh Thiện duyệt PR.

## Todo
- [ ] Gộp 2 + 3, test đơn vị
- [ ] CI `box=true` xanh
- [ ] Máy ảo: áp ngay, giữ lựa chọn người dùng, tài khoản thứ hai, khóa/đăng nhập
- [ ] Trang chủ trên máy trạm, sáng/tối
- [ ] Báo cáo + PR chờ anh duyệt
