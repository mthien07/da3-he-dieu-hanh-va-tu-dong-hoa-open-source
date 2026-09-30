# Hướng dẫn cài OneBee OS Desktop

Dành cho kỹ thuật viên OneBee. Thời gian: phụ thuộc tốc độ mạng (tải LibreOffice tiếng Việt, font, bộ gõ).

## 1. Chuẩn bị
- Máy tính **64-bit**. Máy 32-bit không cài được Linux Mint 22.
- Sao lưu dữ liệu trên máy trước khi cài lại hệ điều hành.
- USB ≥ 8 GB, file cài Linux Mint 22.3 Cinnamon tải từ trang chính thức linuxmint.com (kiểm tra mã SHA256 theo hướng dẫn trên trang).

## 2. Cài Linux Mint
Cài bình thường theo trình cài của Mint. Khi được hỏi, chọn ngôn ngữ Tiếng Việt, múi giờ Hồ Chí Minh.
Có mạng Internet khi cài OneBee (bước 3).

## 3. Chạy bộ cài OneBee
Mở Terminal (Ctrl + Alt + T), gõ lần lượt:
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee
sudo ./desktop/onebee-install.sh
```
Kết thúc thấy dòng `[OneBee] Hoàn tất.` → **khởi động lại máy**.
Nhật ký cài đặt nằm ở `/var/log/onebee/`.

## 4. Sau khi cài, máy có gì
| Hạng mục | Kết quả |
|---|---|
| Ngôn ngữ | Hệ thống, Firefox, LibreOffice tiếng Việt; kiểm tra chính tả tiếng Việt |
| Gõ tiếng Việt | IBus + Bamboo (Telex mặc định). Đổi tiếng Việt/tiếng Anh: phím tắt của IBus (mặc định Super + Space) |
| Font | File Word/Excel dùng Arial, Times New Roman, Calibri: thay bằng font cùng kích thước (Liberation, Carlito) → giữ bố cục. Cambria → Noto Serif (font thay cùng kích thước Caladea thiếu chữ tiếng Việt), bố cục có thể lệch nhẹ |
| LibreOffice | Lưu mặc định .docx / .xlsx / .pptx, không hỏi lại mỗi lần lưu |
| Giao diện | Hình nền OneBee (Cinnamon); bố cục kiểu Windows có sẵn của Mint |
| Cập nhật | Tự động nâng cấp và dọn gói thừa (mintupdate) |
| Sao lưu | Khi có `/etc/onebee/may-tram.env` (từ OneBee Box): tự sao lưu `/home` lên Box 12:00 hằng ngày — xem hướng dẫn cài Box |
| Múi giờ | Asia/Ho_Chi_Minh |
| Trợ lý AI | Lệnh `hoi` (khi có khóa từ Box) |
| Quản lý từ Box | Báo tình trạng mỗi giờ; Box cập nhật máy qua SSH — xem [quan-ly-may-tram.md](quan-ly-may-tram.md) |
| Menu OneBee | "Báo cần hỗ trợ (OneBee)" (mở biểu mẫu trên Box), "Cho phép hỗ trợ từ xa (OneBee)" |

## 5. Tùy chỉnh
Sửa `desktop/ansible/group_vars/all.yml` rồi chạy lại bộ cài (chạy lại nhiều lần an toàn), ví dụ:
- Dùng Unikey thay Bamboo: `onebee_input_method: unikey`
- Không đổi định dạng lưu mặc định của LibreOffice: `onebee_office_default_ms_formats: false`

## 6. Kiểm tra nhanh sau khi cài
```bash
sudo ./tests/desktop/verify-desktop-install.sh
```
Tất cả dòng phải là `PASS`.

## Giới hạn đã biết (v0.1)
- Bộ gõ và hình nền là **giá trị mặc định**: tài khoản đã tự chọn bộ gõ/hình nền trước khi cài OneBee giữ lựa chọn cũ.
  Nên cài OneBee ngay sau khi cài Mint mới, trước khi người dùng tùy chỉnh.
- Không gỡ riêng Writer/Calc/Impress: cấu hình định dạng mặc định của LibreOffice cần đủ cả 3.
- Chưa kiểm trên máy thật. Đã kiểm tự động trong container Linux Mint 22.3, gồm gõ Telex thật qua IBus trong
  màn hình ảo (xem `tests/README.md`). Chưa kiểm phiên Cinnamon thật: thanh bộ gõ, hình nền hiển thị, phím tắt.
- File Office có macro VBA hoặc bố cục phức tạp có thể hiển thị lệch — giữ bản gốc.
- Phần mềm chỉ chạy trên Windows (kê khai thuế, BHXH, ký số USB token…) chưa được hỗ trợ.
