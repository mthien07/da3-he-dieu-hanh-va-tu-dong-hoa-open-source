# Phiếu kiểm trải nghiệm trên máy thật — bản 1.2.0

## Mục đích
Kiểm trong một phiên Cinnamon thật những gì nhân viên HTX sẽ thấy và bấm: lần đầu đăng nhập, gõ tiếng Việt, phím tắt, Trung tâm OneBee,
tự kiểm tra máy, báo cần hỗ trợ, nhắc sao lưu, Trợ lý AI và trang chủ Box. Bộ test tự động không chạy được phiên đồ họa thật, nên những gì
chỉ thấy bằng mắt nằm ở phiếu này. Phiếu bảo mật cũ (`docs/kiem-thu-tren-may-that.md`) là việc khác, không thay thế phiếu này.

Người làm phiếu không cần rành kỹ thuật: mỗi mục viết theo dạng **Làm gì → Phải thấy gì**. Không tự suy ra là đạt: chỉ đánh dấu khi đã thấy đúng.

## Môi trường
- Máy trạm: máy ảo Linux Mint 22.3 Cinnamon, mạng Bridged, cài OneBee Desktop từ bản cần kiểm (ghi commit vào kết quả). Máy ảo nên có màn hình 1366×768 để thử mục A5.
- Tài khoản thử: một tài khoản thường **vừa tạo** (chưa từng đăng nhập) và có thể dùng `sudo` ở Terminal cho mục F; mọi mục khác làm bằng chính tài khoản thường này.
- Box thử (cho các mục có ghi **[cần Box]**): máy ảo Ubuntu Server 24.04 đã cài OneBee Box, hoặc container giữ lại của
  `tests/box/run-box-test-in-systemd-container.sh` (`ONEBEE_TEST_KEEP=1`). Máy trạm phải đã nối Box (có `/etc/onebee-hoi.conf`) và gõ được `http://onebee.local`.
- Máy Dell tại đơn vị không bắt buộc; nếu vào được thì lặp lại nhóm A–F ở đó.
- Hướng dẫn dựng máy ảo: `docs/huong-dan/thu-nghiem-tren-may-ao.md`.

## Cách ghi
- Sao chép phiếu này thành file kết quả `reports/trai-nghiem/<năm-tháng-ngày>-<tên máy>.md` (xem `reports/trai-nghiem/README.md`), rồi làm trên bản sao.
- Đạt: đổi `[ ]` thành `[x]`.
- Không đạt: để `[ ]` và ghi ngay dưới mục điều đã thấy (đúng từng chữ trên màn hình), tên ảnh chụp nếu có, và `git rev-parse --short HEAD` của bản đã cài.
- Mục không áp dụng được trong bản này: ghi "bỏ qua" kèm lý do.
- Không ghi mật khẩu, khóa, tên người, nội dung file của đơn vị.
- Cuối file có bảng "Mục không đạt và cách xử lý": mỗi mục không đạt thêm một dòng.

## A. Lần đầu đăng nhập (tài khoản thường vừa tạo)
- [ ] A1 Đăng nhập lần đầu → cửa sổ "Trung tâm OneBee" tự mở trong 30 giây; không có cửa sổ "Welcome" của Mint.
- [ ] A2 Đóng cửa sổ, đăng xuất, đăng nhập lại → cửa sổ không tự mở nữa; mở được từ menu Bắt đầu → Trung tâm OneBee.
- [ ] A3 Chờ 15 phút → không có cửa sổ Trình quản lý cập nhật tự bật.
- [ ] A4 Nhìn góc trái dưới → nút menu có logo OneBee và chữ "Bắt đầu".
- [ ] A5 Nhìn góc phải dưới → đồng hồ có giờ và ngày/tháng/năm; trên màn hình 1366×768 thanh tác vụ không bị chật.
- [ ] A6 Đăng xuất → màn hình đăng nhập có hình nền OneBee.

## B. Gõ tiếng Việt
- [ ] B0 Ngay sau khi đăng nhập, chưa bấm phím đổi bộ gõ, gõ `Howjp tacs xax` trong LibreOffice Writer → ra "Hợp tác xã" (tiếng Việt là mặc định).
- [ ] B1 Nhìn khay hệ thống → có chỉ báo bộ gõ; phân biệt được đang gõ Việt hay Anh.
- [ ] B2 Bấm Super + Space → chỉ báo đổi.
- [ ] B3 Gõ `Howjp tacs xax` trong LibreOffice Writer, Firefox, ô tìm kiếm của menu Bắt đầu → ra "Hợp tác xã" ở cả ba nơi.
- [ ] B5 Bấm Super + Space sang tiếng Anh, gõ `onebee.local` vào thanh địa chỉ Firefox và gõ một mật khẩu thử vào ô mật khẩu → không bị thêm dấu.
  Ghi lại nếu ở chế độ tiếng Việt ô mật khẩu có bị thêm dấu không.
- [ ] B4 Mở Terminal, ghi lại kết quả của `gsettings get org.cinnamon.desktop.input-sources sources` và `pgrep -a ibus-daemon`.

## C. Phím tắt
Bấm thử từng dòng của bảng đầu trong `docs/huong-dan/to-phim-tat.md` → đúng việc ghi trong tờ. Mỗi dòng là một mục.
- [ ] C1 Đổi gõ tiếng Việt ⇄ tiếng Anh: Super + Space.
- [ ] C2 Gõ Telex: aa=â, aw=ă, ee=ê, oo=ô, ow=ơ, uw=ư, dd=đ · s=sắc, f=huyền, r=hỏi, x=ngã, j=nặng · z=xóa dấu.
- [ ] C3 Mở menu Bắt đầu: phím Super (và nút Bắt đầu góc trái dưới).
- [ ] C4 Chạy lệnh / mở nhanh chương trình: Super + R (và Alt + F2).
- [ ] C5 Mở thư mục cá nhân: Super + E.
- [ ] C6 Hiện màn hình nền / quay lại: Super + D.
- [ ] C7 Khóa màn hình: Super + L (và Ctrl + Alt + L).
- [ ] C8 Chuyển giữa các cửa sổ: Alt + Tab.
- [ ] C9 Quản lý tác vụ: Ctrl + Shift + Esc.
- [ ] C10 Sao chép / Dán / Cắt / Hoàn tác: Ctrl + C / V / X / Z.
- [ ] C11 Lưu / Lưu thành file khác / In: Ctrl + S / Ctrl + Shift + S / Ctrl + P.
- [ ] C12 Xuất PDF (Writer, Calc): nút PDF trên thanh công cụ (đối chiếu với kết quả nhóm I).
- [ ] C13 Kiểm tra chính tả: F7.
- [ ] C14 Chụp màn hình: phím Print Screen.
- [ ] C15 Chụp một vùng vào clipboard: Super + Shift + S, kéo chọn vùng, dán bằng Ctrl + V (Shift + Print Screen: chụp vùng lưu thành file).
- [ ] C16 Mở cửa sổ dòng lệnh: Ctrl + Alt + T.

Nếu tờ phím tắt đổi dòng, đổi theo số dòng của bảng đầu ở thời điểm kiểm. Cả nhóm C đạt mới được xóa dòng ghi chú "chưa kiểm trên phiên Cinnamon thật" ở đầu tờ phím tắt.

## D. Trung tâm OneBee và tự phục vụ
Mục D5–D7 cần máy đã nối Box **[cần Box]**: chưa nối Box thì lệnh báo cần hỗ trợ báo rõ lý do thay vì mở biểu mẫu.
- [ ] D1 Bấm lần lượt 6 ô của trang Bắt đầu (Soạn văn bản, Bảng tính, Thư mục của tôi, Thư mục chung của đơn vị, Trợ lý AI, Cần giúp đỡ) → mở đúng thứ ghi trên ô.
  Làm lần đầu khi máy chưa nối Box: ô thư mục chung báo rõ lý do. Làm lại sau khi nối Box: ô thư mục chung mở thư mục chung.
- [ ] D2 Trang Phím tắt → có đủ 13 mục của nguồn chung `onebee-cam-nang.json`, mỗi dòng đúng chữ của dòng tương ứng trên tờ phím tắt.
  Trang cố ý **không** có 2 dòng của tờ: "Xuất PDF — Nút PDF trên thanh công cụ" (không phải phím tắt) và
  "Mở cửa sổ dòng lệnh — Ctrl + Alt + T" (không đưa cho nhân viên); ghi chú phụ của tờ (Shift + Print Screen, nút Bắt đầu) không bắt buộc có.
- [ ] D3 Trang Kiểm tra máy → bấm "Kiểm tra ngay", trong khoảng 1 phút hiện lần lượt từng mục có biểu tượng đạt/cảnh báo/lỗi (9 mục khi máy tới được Box;
  Box không trả lời thì ít mục hơn). Ghi lại bố cục có bị cắt chữ, tràn khung hay chồng nút không, nhất là trên màn hình 1366×768.
  Đây là phần giao diện chưa kiểm được ngoài máy thật.
- [ ] D4 Rút dây mạng (hoặc tắt mạng máy ảo), kiểm tra lại → mục Mạng báo lỗi kèm gợi ý dễ hiểu. Cắm lại.
- [ ] D5 **[cần Box]** Bấm "Báo cần hỗ trợ kèm kết quả này" → trình duyệt mở biểu mẫu, ô "Máy" đã có tên máy, ô mô tả đã có tóm tắt.
- [ ] D6 **[cần Box]** Lần đầu mở biểu mẫu trình duyệt hỏi tài khoản → nhập tài khoản `nhanvien`; ghi lại: lần mở sau trong cùng buổi có hỏi lại không,
  trình duyệt có đề nghị lưu mật khẩu không.
- [ ] D7 **[cần Box]** Menu Bắt đầu → "Báo cần hỗ trợ (OneBee)" → mở biểu mẫu có sẵn tên máy.

## E. Trợ lý tập tin Windows
- [ ] E1 Bấm đúp một file tên `ZaloSetup.exe` → hộp thoại gợi ý Zalo Web; bấm nút → trình duyệt mở Zalo Web.
- [ ] E2 **[cần Box]** Bấm đúp một file `.exe` tên lạ → hộp chọn chỉ có lựa chọn làm được trên máy và "Báo cần hỗ trợ"; chọn nó → biểu mẫu mở với loại "Phần mềm chỉ chạy trên Windows".
- [ ] E3 Bấm đúp một chương trình Linux (ví dụ file `.AppImage`) → **không** hiện hộp thoại "phần mềm Windows".

## F. Sao lưu
Cần máy đã nối Box **[cần Box]**: máy chưa nối thì dịch vụ nhắc im lặng (đúng thiết kế) và F1 sẽ không hiện gì.
Đây là phần dịch vụ systemd mức người dùng chưa kiểm được ngoài máy thật.
- [ ] F1 Giả lập sao lưu trễ: `sudo sh -c 'echo $(( $(date +%s) - 80*3600 )) > /var/lib/onebee/sao-luu-cuoi'`, rồi bằng tài khoản thường chạy
  `systemctl --user start onebee-nhac-sao-luu.service` → hiện thông báo "OneBee: máy chưa sao lưu 3 ngày".
- [ ] F2 Chạy lại lệnh `systemctl --user start ...` → không hiện thông báo lần hai trong cùng ngày. Sau đó chạy `sudo onebee-sao-luu` để trả lại trạng thái thật.
  (Muốn thử lại F1 trong cùng ngày: xóa `~/.cache/onebee/nhac-sao-luu`.)
- [ ] F3 `systemctl --user list-timers | grep onebee` → có `onebee-nhac-sao-luu.timer`. Không thấy thì thử `systemctl --user list-timers --all | grep onebee` và ghi lại cả hai kết quả.

## G. Trợ lý AI (cần Box)
- [ ] G1 **[cần Box]** Bấm biểu tượng Trợ lý AI OneBee trên thanh tác vụ, đăng nhập tài khoản nhân viên → màn hình trò chuyện mới hiện các gợi ý
  tiếng Việt của OneBee (Open WebUI hiện ngẫu nhiên một phần mỗi lần tải, trong 4 gợi ý: Soạn tờ trình, công văn; Lập biên bản họp;
  Soạn thông báo; Tóm tắt văn bản), bấm được, và dòng nhắc "Trợ lý AI có thể sai".
- [ ] G2 **[cần Box]** Bấm một gợi ý → câu mở đầu được chèn vào ô nhập, chưa gửi; viết tiếp rồi gửi → nhận văn bản tiếng Việt.
- [ ] G3 **[cần Box]** Gõ `/` trong ô nhập → thấy 4 mẫu `to-trinh`, `bien-ban`, `hop-dong`, `bao-cao`.
- [ ] G5 Trợ lý "Tra cứu Luật HTX và Nghị định 30": **chưa có trong bản này, bỏ qua** (ghi "bỏ qua" ở mục này).
  Khi trợ lý này được làm, mục sẽ là: chọn nó ở ô chọn phía trên, hỏi "Mỗi thành viên chính thức có mấy phiếu biểu quyết?" → trả lời "một phiếu"; ghi lại thời gian chờ chữ đầu tiên.
- [ ] G4 **[cần Box]** Ghi lại **mọi chữ tiếng Anh** nhìn thấy khi: đăng nhập, hỏi một câu, xem lại lịch sử, đổi mật khẩu, đăng xuất.

## H. Trang chủ Box (mở `http://onebee.local` từ máy trạm và từ điện thoại trong LAN) **[cần Box]**
- [ ] H1 Cẩm nang "Phím tắt hay dùng" (mục Cẩm nang sử dụng) có đủ 13 mục của nguồn chung, giống trang Phím tắt ở D2 (cố ý không có
  2 dòng "Xuất PDF" và "Mở cửa sổ dòng lệnh" của tờ phím tắt); không còn chữ "Mở Terminal".
- [ ] H2 Mục "Soạn văn bản bằng Trợ lý AI" có 4 thẻ; bấm một thẻ → Trợ lý mở, câu mở đầu đã điền sẵn và **không tự gửi**.
- [ ] H3 Sau lần sao lưu đêm đầu tiên (hoặc sau `sudo onebee-box sao-luu`) → ô "Máy trạm đã sao lưu: x/y máy (trong 3 ngày)"; trang không lộ tên máy.

## I. Xuất PDF
Trong LibreOffice Writer (giao diện tab) thử 3 cách: nút PDF trên thanh công cụ; menu Tệp → Xuất dưới dạng → Xuất thành PDF; Tệp → Xuất ra PDF.
- [ ] I1 Ghi lại **cách nào có thật và tên đúng từng chữ trên màn hình**. (Tờ phím tắt đang ghi "nút PDF trên thanh công cụ", trang chủ Box đang ghi "Tệp → Xuất ra PDF".)

## J. Năm việc đầu tiên với người dùng thật (không bắt buộc, làm khi có 1–3 nhân viên)
Không hướng dẫn trước, bấm giờ từng việc, ghi "tự làm được / cần gợi ý / không làm được":
- [ ] J1 Gõ và lưu một câu tiếng Việt có dấu.
- [ ] J2 Mở một file Word trong thư mục chung.
- [ ] J3 Nhờ Trợ lý soạn một thông báo.
- [ ] J4 Báo cần hỗ trợ.
- [ ] J5 Kiểm tra máy đã sao lưu chưa.

Con số đo ở nhóm J chỉ được công bố khi đã có file kết quả trong `reports/trai-nghiem/`.

## Mục không đạt và cách xử lý
Mỗi mục không đạt một dòng. Cột "Trạng thái" chỉ dùng một trong: `chưa xử lý`, `đã sửa (nhánh/PR)`, `giới hạn đã biết`.
Nhóm B (gõ tiếng Việt) không đạt thì không phát hành.

| Mục | Điều đã thấy | Ảnh / log | Cách xử lý | Trạng thái |
|---|---|---|---|---|
| | | | | |
