# Kiểm thử 19/11/2026: sao lưu vào ổ Box, phòng ban, máy trạm xin vào

Nhánh `feat/sao-luu-vao-o-box`, chưa commit. Kết quả: **đạt hết**.

## Kiểm thử đơn vị và lint (container `onebee-kiem-gd1`)
- `tests/box`: đạt hết, 34 bài bỏ qua (thiếu công cụ trong image).
- `tests/desktop`: 246 bài đạt, 3 bài bỏ qua.
- Mẫu Jinja: 32 mẫu, 0 lỗi. yamllint, ansible-lint (Box, Desktop), shellcheck, SPDX đều sạch. Shellcheck các mẫu sau khi dựng: 4 cảnh báo cũ, không có cảnh báo mới.
- `check-diagnosis.sh`: 0 mục không đạt.

## Bài kiểm Box đầy đủ (Ubuntu 24.04 + systemd, máy trạm Mint 22.3)
Đạt toàn bộ, kết thúc "TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT", khoảng 260 mục. Có mục mới cho:
- sao lưu vào ổ dữ liệu Box (mặc định) và phương án phụ ổ ngoài;
- phòng ban: phòng khác và tài khoản chung không vào được thư mục phòng, cũng không thấy trong danh sách;
- máy trạm xin vào qua LAN: mã đối chiếu hai bên trùng, duyệt, máy kiểm chữ ký Box rồi giải mã cấu hình; từ chối kèm lý do;
- sao lưu riêng từng phòng, khôi phục riêng một phòng;
- khôi phục toàn bộ lấy lại thư mục, sổ, chia sẻ và mật khẩu Samba của phòng.

Cách chạy:
- Chạy liền một mạch tới giữa phần xin vào. Hai lỗi của chính bài kiểm làm dừng giữa chừng (dấu xuống dòng khi so mật khẩu; `grep` dưới `set -e`); đã sửa trong `tests/box/check-phong-ban-xin-vao.sh` rồi chạy tiếp phần còn lại trên container đã giữ (`ONEBEE_TEST_KEEP=1`).
- Máy `kt-02` (chỉ nhận cấu hình, không cài thật) làm chốt chặn HTTPS dừng; bài kiểm nay thu hồi máy này sau phần xin vào.

Điều kiện môi trường, không đổi gì trong repo:
- Model AI dùng `qwen3:0.6b`, vì Docker trên máy chỉ có 4 GB RAM; với gemma4 thì Ollama trả 503. CI chạy model mặc định.
- `packages.linuxmint.com` hôm nay trả trang của nhà cung cấp hosting thay cho kho Mint, nên bản chụp dùng để kiểm tắt kho Mint trong container máy trạm.

## Rà soát bảo mật
Một lỗi nghiêm trọng: cấu hình gửi xuống máy chưa được ký, nên kẻ đứng giữa chiếm được root máy mới. Đã sửa: Box ký bằng CA trung gian, máy kiểm chữ ký, id và n_w. Các mục khác đã sửa:
- gõ lại mã ở cả hai phía;
- chống CSRF;
- cảnh báo mỗi lần cấp, giới hạn 10 máy/24 giờ;
- yêu cầu bỏ dở hết hạn sau 10 phút;
- giữ kết quả để máy hỏi lại;
- `doi-mat-khau-phong`;
- đọc độ dài RSA từ khóa công khai.

Còn lại có chủ đích, ghi trong ADR 0009: chiếm được Node-RED thì vẫn tự duyệt được (đã giảm thiểu bằng cảnh báo và giới hạn).

## Chưa làm
- Chưa thử trên Box thật và máy Mint thật. Gắn CIFS `/mnt/phongban` và cài gói phần mềm của phòng chưa chạy thật, vì container không gắn được CIFS.
- Chưa thử duyệt trên web bằng trình duyệt thật (cần đăng nhập hai lớp); phần này có bài kiểm node và DOM giả.
- Bài `CaddyDinhDanhChet` (`test_onebee_caddy_sso.py`) có sẵn từ trước, thỉnh thoảng hỏng ngẫu nhiên vì thay chuỗi `:443` trúng cổng ngẫu nhiên. Không thuộc việc lần này.
