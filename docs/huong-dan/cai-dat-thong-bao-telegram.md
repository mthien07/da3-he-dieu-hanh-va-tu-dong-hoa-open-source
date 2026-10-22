# Hướng dẫn cài đặt Cảnh báo Sự cố qua Telegram cho OneBee Box

OneBee Box hỗ trợ gửi cảnh báo tức thời (sao lưu hoàn tất, ổ cứng gần đầy, mất nguồn, quá nhiệt, sự cố mạng) trực tiếp vào điện thoại của quản trị viên hoặc nhóm kỹ thuật thông qua Telegram Bot hoàn toàn miễn phí.

---

## 1. Tạo Bot Telegram (mất 2 phút)

1. Mở ứng dụng Telegram trên điện thoại hoặc máy tính, tìm kiếm **`@BotFather`** (có tích xanh).
2. Nhấn **Start** (hoặc gửi `/start`), sau đó gửi lệnh:
   ```text
   /newbot
   ```
3. Đặt tên hiển thị cho bot (Ví dụ: `OneBee Box Long An Alert`).
4. Đặt username cho bot kết thúc bằng chữ `bot` (Ví dụ: `OneBeeLongAn_bot`).
5. BotFather sẽ gửi lại một chuỗi mã **HTTP API Token** có dạng:
   ```text
   7123456789:AAHxyz...abc123456
   ```
   > ⚠️ **Lưu ý:** Giữ bí mật mã Token này.

---

## 2. Lấy Chat ID nhận thông báo

### Cách 1: Nhận tin nhắn cá nhân
1. Tìm bot vừa tạo trên Telegram và nhấn **Start** để kích hoạt cuộc trò chuyện với bot.
2. Tìm bot **`@userinfobot`**, nhấn **Start** ➔ Bot này sẽ trả về số `Id` của bạn (Ví dụ: `123456789`).

### Cách 2: Nhận tin nhắn vào Nhóm Quản trị HTX
1. Tạo một nhóm chat trên Telegram và thêm Bot vừa tạo vào nhóm.
2. Thêm bot **`@RawDataBot`** vào nhóm để lấy `chat.id` của nhóm (thường bắt đầu bằng dấu trừ, ví dụ: `-1001987654321`). Sau khi lấy xong có thể xoá `@RawDataBot` khỏi nhóm.

---

## 3. Cấu hình trên OneBee Box

Đăng nhập SSH vào OneBee Box bằng tài khoản quản trị và chạy:

```bash
sudo onebee-box dat-telegram
```

Hệ thống sẽ hỏi:
1. `Nhập Telegram Bot Token (từ @BotFather):` Dán Token ở Bước 1.
2. `Nhập Telegram Chat ID (hoặc Group ID nhận tin):` Dán Chat ID ở Bước 2.

Hệ thống sẽ tự động lưu cấu hình bảo mật vào `/etc/onebee-box/secrets/telegram.env` và bắn thử ngay một tin nhắn kiểm tra tới Telegram của bạn:

> ℹ️ **[THÔNG BÁO — HTX Nông nghiệp Số 1]**  
> **Kiểm tra kết nối Telegram**  
> Thời gian: 15:30:00 22/10/2026  
> OneBee Box đã kết nối thành công với bot Telegram này.

---

## 4. Kiểm tra gửi thông báo thủ công từ dòng lệnh

Bạn có thể tự gửi cảnh báo kiểm tra bằng lệnh:

```bash
# Thông báo bình thường
sudo onebee-box canh-bao INFO "Sao lưu thành công" "Toàn bộ 5 máy trạm đã sao lưu an toàn."

# Cảnh báo chú ý
sudo onebee-box canh-bao WARN "Dung lượng ổ cứng cao" "Phân vùng /data đã dùng 87%."

# Báo động khẩn cấp
sudo onebee-box canh-bao CRIT "Ổ cứng gần đầy nghiêm trọng" "Phân vùng /data đã dùng 96%!"
```
