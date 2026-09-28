# Kiểm thử OneBee OS

Tất cả chạy trên máy có Docker. Mạng có proxy HTTPS tự ký: đặt `ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt`.

| Lệnh | Thời gian* | Kiểm tra gì |
|---|---|---|
| `tests/desktop/run-desktop-test-in-mint-container.sh` | ~2 phút | Cài Desktop trên Mint 22.3 2 lần (lần 2 không đổi gì), 33 mục + 4 mục LibreOffice qua UNO |
| `tests/desktop/run-desktop-extended-tests.sh` | ~10 phút | 5 kịch bản: chặn sai đầu vào; chờ khóa dpkg, giữ LC_*, tự sửa cấu hình lệch; mở file Word tiếng Việt → PDF (font thay thế, không lẫn font, giữ dấu); chính tả; **gõ Telex thật qua IBus** (Bamboo và Unikey); systemd thật (timer chạy ngay); nền Ubuntu 24.04 |
| `tests/box/run-box-test-in-systemd-container.sh` | ~8 phút + tải ~6 GB | 46 mục: cài Box 2 lần; 26 mục dịch vụ/bảo mật; AI hỏi đáp thật (model thử 0.5b); sao lưu Box ra ổ ngoài + khôi phục; máy trạm Mint cài OneBee sao lưu lên Box, khôi phục, **không xóa được** bản cũ; Box dọn được; phát hiện bản giả mạo ngày tương lai; chưa gắn ổ ngoài thì từ chối; khởi động lại Box dịch vụ tự lên |

\* đo trên máy thử nghiệm của nhóm, lần đầu tải image lâu hơn.

## Chưa kiểm được bằng container (phải thử máy ảo / máy thật)
- Phiên đăng nhập Cinnamon thật: thanh bộ gõ, hình nền hiển thị, phím tắt đổi bộ gõ (Super + Space) có đụng phím của Cinnamon không.
- Phần cứng thật: wifi, máy in, máy cũ yếu; tốc độ AI trên CPU/GPU thật.
- Mạng LAN thật: truy cập Box từ máy khác, Samba từ Windows.
