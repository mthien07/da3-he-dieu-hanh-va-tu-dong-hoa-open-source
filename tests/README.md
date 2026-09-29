# Kiểm thử OneBee OS

Tất cả chạy trên máy có Docker. Mạng có proxy HTTPS tự ký: đặt `ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt`.

| Lệnh | Thời gian* | Kiểm tra gì |
|---|---|---|
| `tests/desktop/run-desktop-test-in-mint-container.sh` | ~2 phút | Cài Desktop trên Mint 22.3 2 lần (lần 2 không đổi gì), các mục verify + 4 mục LibreOffice qua UNO |
| `tests/desktop/run-desktop-extended-tests.sh` | ~10 phút | 5 kịch bản: chặn sai đầu vào; chờ khóa dpkg, giữ LC_*, nâng cấp cấu hình sao lưu v0.1, tự sửa cấu hình lệch; mở file Word tiếng Việt → PDF (font thay thế, không lẫn font, giữ dấu); chính tả; **gõ Telex thật qua IBus** (Bamboo và Unikey); systemd thật (timer chạy ngay); nền Ubuntu 24.04 |
| `tests/box/run-box-test-in-systemd-container.sh` | ~10 phút + tải ~6 GB | Cài Box 2 lần; dịch vụ/bảo mật; **Trợ lý OneBee** (tài khoản quản trị tạo sẵn, tắt đăng ký tự do, hỏi đáp tiếng Việt với model Gemma nhỏ nhất); **n8n qua email** (hộp thư giả lập Mailpit: email thử, nhắc hạn thuế, nhập + tổng hợp đơn hàng, tóm tắt PDF bằng AI, webhook/biểu mẫu đòi khóa); sao lưu Box ra ổ ngoài + khôi phục + email báo cáo; máy trạm Mint cài OneBee: sao lưu lên Box, **lệnh `hoi`** (khóa chỉ gọi được hỏi đáp; Box tắt Trợ lý thì báo dễ hiểu), không xóa được bản cũ; Box dọn được; bản giả mạo ngày tương lai; chưa gắn ổ ngoài thì từ chối; khởi động lại Box |
| `python3 -m unittest tests/ai/test_scoring_and_report.py` | vài giây | Công cụ chấm model: đọc bộ 40 câu, chấm ý bắt buộc/ý cấm (có phủ định), tổng hợp theo ngưỡng |
| `tests/ai/cham-diem-model.py --model <model> ...` | hàng giờ trên CPU | **Chấm chất lượng Trợ lý**: 40 câu × 3 lần, xuất báo cáo `reports/ai/` + phiếu chấm tay nhóm 2–3 |

\* đo trên máy thử nghiệm của nhóm, lần đầu tải image lâu hơn.

## Chưa kiểm được bằng container (phải thử máy ảo / máy thật)
- Phiên đăng nhập Cinnamon thật: thanh bộ gõ, hình nền hiển thị, phím tắt đổi bộ gõ (Super + Space) có đụng phím của Cinnamon không.
- Phần cứng thật: wifi, máy in, máy cũ yếu; **tốc độ AI trên CPU/GPU thật** (ngưỡng tốc độ chỉ xét trên máy Box thật).
- Mạng LAN thật: truy cập Box từ máy khác, Samba từ Windows; gửi email qua máy chủ thư thật của đơn vị.
