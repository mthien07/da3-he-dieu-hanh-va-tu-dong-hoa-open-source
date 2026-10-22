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
| LibreOffice | Lưu mặc định .docx / .xlsx / .pptx, không hỏi lại mỗi lần lưu. Thanh công cụ dạng tab (Ribbon) như Word/Excel/PowerPoint; đổi lại ở Xem → Giao diện người dùng. Bộ biểu tượng Colibre (kiểu giống Microsoft Office); đổi ở Công cụ → Tùy chọn → LibreOffice → Xem |
| Giao diện | Hình nền OneBee (Cinnamon). Thanh tác vụ ở đáy màn hình: nút **Bắt đầu** có logo OneBee bên trái (phím Super), ghim sẵn Nemo, Firefox, Writer, Calc, Impress, Trợ lý AI; khay hệ thống + nút hiện màn hình nền bên phải. Nút thu nhỏ/phóng to/đóng ở góc phải cửa sổ. Rê chuột lên ứng dụng trên thanh tác vụ thấy ảnh thu nhỏ cửa sổ. Màn hình nền có Máy tính, Thùng rác, Thư mục cá nhân và (khi đã nối Box) lối tắt **Chia sẻ nội bộ (OneBee Box)** tới `smb://<IP Box>/chung`. Thư mục màu vàng (bộ biểu tượng Mint-Y-Sand). Nemo ẩn file ẩn, nhấp đúp để mở. Phím Win+E / D / L / R, Win+Shift+S (chụp vùng vào clipboard), Ctrl+Shift+Esc (Quản lý tác vụ) — xem [to-phim-tat.md](to-phim-tat.md) |
| Cập nhật | Tự động nâng cấp và dọn gói thừa (mintupdate) |
| Sao lưu | Khi có `/etc/onebee/may-tram.env` (từ OneBee Box): tự sao lưu `/home` lên Box 12:00 hằng ngày — xem hướng dẫn cài Box |
| Múi giờ | Asia/Ho_Chi_Minh |
| Trợ lý AI | Lệnh `hoi` (khi có khóa từ Box); mục **Trợ lý AI OneBee** trên thanh tác vụ/menu mở giao diện web của Trợ lý (cần máy đã kết nối Box) |
| Quản lý từ Box | Báo tình trạng mỗi giờ; Box cập nhật máy qua SSH — xem [quan-ly-may-tram.md](quan-ly-may-tram.md) |
| Menu OneBee | "Báo cần hỗ trợ (OneBee)" (mở biểu mẫu trên Box), "Cho phép hỗ trợ từ xa (OneBee)" |
| Trợ lý file Windows | Tự động bắt file `.exe` / `.msi` khi bấm đúp; gợi ý ứng dụng Linux tương đương (Zalo Web, Chromium, IBus Bamboo, PDF Viewer, VLC, hỗ trợ từ xa) hoặc hỗ trợ chạy WINE / máy ảo kế toán |

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
- Bộ gõ, hình nền, phím tắt, biểu tượng màn hình nền, nút menu và ứng dụng ghim sẵn là **giá trị mặc định**: tài khoản đã tự chọn/đổi các mục này trước khi cài OneBee giữ lựa chọn cũ.
  Nên cài OneBee ngay sau khi cài Mint mới, trước khi người dùng tùy chỉnh.
- Không gỡ riêng Writer/Calc/Impress: cấu hình định dạng mặc định của LibreOffice cần đủ cả 3.
- Chưa kiểm trên máy thật. Đã kiểm tự động trong container Linux Mint 22.3, gồm gõ Telex thật qua IBus trong
  màn hình ảo (xem `tests/README.md`). Chưa kiểm phiên Cinnamon thật: thanh bộ gõ, hình nền hiển thị, phím tắt,
  thanh tác vụ ghim sẵn, giao diện Ribbon hiển thị. Nút Bắt đầu dùng logo OneBee (biểu tượng `onebee-logo`); người dùng đã tự chọn biểu tượng menu riêng thì giữ lựa chọn của họ.
- Ctrl+Shift+Esc là phím tùy chỉnh đặt làm mặc định qua CSDL dconf hệ thống (`/etc/dconf/db/local.d/50-onebee-phim-tat`): người dùng tự thêm phím tùy chỉnh trong Cài đặt vẫn giữ được phím này; xóa đi thì không tự thêm lại.
- Lối tắt Chia sẻ nội bộ chỉ đặt một lần cho mỗi tài khoản (lúc đăng nhập); người dùng xóa thì không đặt lại; Box đổi IP thì lối tắt tự cập nhật.
- Win+L khóa màn hình nên phím Super+L mặc định của Cinnamon (bảng gỡ lỗi Looking Glass cho lập trình viên) bị gỡ; kỹ thuật vẫn mở bằng Alt+F2 → gõ `lg`.
- File Office có macro VBA hoặc bố cục phức tạp có thể hiển thị lệch — giữ bản gốc.
- Phần mềm chỉ chạy trên Windows (kê khai thuế, BHXH, ký số USB token…) chưa được hỗ trợ.
