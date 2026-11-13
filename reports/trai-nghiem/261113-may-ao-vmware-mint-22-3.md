# Kết quả phiếu kiểm trải nghiệm — máy ảo VMware Mint 22.3

> **Kiểm tự động trên máy ảo VMware, chưa có người xác nhận lại.** Mọi thao tác (gõ phím, bấm chuột) được gửi qua VNC của VMware
> và chấm bằng ảnh chụp màn hình cùng đầu ra lệnh. Mục về **cảm nhận** cần người nhìn lại trên máy thật: A4 (logo nút Bắt đầu có dễ nhận
> không), A5 (thanh tác vụ khi mở nhiều cửa sổ), A6 (khung đăng nhập đè lên logo hình nền), B1 (chỉ báo `vi`/`en` có đủ rõ với nhân viên
> không), D3 (bố cục trang Kiểm tra máy, chữ gợi ý có quá kỹ thuật không), G2 (chất lượng văn bản AI), H (trang chủ Box trên điện thoại).

```text
Ngày kiểm: 13–14/11/2026 (23:50 → 02:05)
Máy: máy ảo VMware Fusion "onebee-mint-22-3-kiem" (4 CPU, 8 GB RAM, ổ 40 GB, EFI), tên máy ketoan-01
Bản Mint: 22.3 Cinnamon (Zena), cài từ ISO chính thức (SHA-256 khớp sha256sum.txt), ngôn ngữ cài: Tiếng Việt
Commit đã cài: 09644a4
Người kiểm: kiểm tự động (chưa có người xác nhận)
Box thử: máy ảo VMware Ubuntu Server 24.04 (ảnh cloud chính thức), OneBee Box 1.2.0 cùng commit 09644a4, model gemma4:e2b-it-qat
```

## Môi trường và lệch so với phiếu
- Mạng: **NAT của VMware** (cả máy trạm và Box cùng mạng 192.168.72.0/24), không phải Bridged như phiếu ghi. `onebee.local` phân giải được
  qua mDNS trong mạng này. Không có điện thoại trong mạng, nên phần "từ điện thoại trong LAN" của nhóm H chưa kiểm.
- Màn hình: phiên Cinnamon mặc định 1280×800; đặt 1366×768 bằng `xrandr` trong phiên sau lần đăng nhập đầu (A1 chụp ở 1280×800,
  các mục còn lại ở 1366×768).
- Tài khoản: `quantri` (tạo lúc cài Mint, dùng để cài OneBee) và `kiemthu` — tài khoản thường **tạo sau khi cài OneBee, chưa đăng nhập
  lần nào trước A1**, thêm vào nhóm `sudo` cho mục F đúng như phiếu. Mật khẩu thử không ghi ở đây.
- File thử cho nhóm E tạo sẵn trên màn hình nền: `ZaloSetup.exe` và `PhanMemKeToanXYZ.exe` (đầu file `MZ`, máy nhận là
  `application/x-msdownload`), `thu-nghiem.AppImage` (bản chép `/usr/bin/true`, có quyền chạy, máy nhận là `application/vnd.appimage`).
- Ảnh chụp lưu ngoài repo, trên máy Mac của chủ máy: `plans/261112-0720-toi-uu-trai-nghiem-nguoi-dung/reports/anh-phieu-kiem/`
  (thư mục `plans/` của bản checkout chính). Tên ảnh ghi ở từng mục.

## Cài đặt (trước phiếu)
- **Lần 1 theo đúng tài liệu bị lỗi.** Mint cài bằng tiếng Việt đặt `LANG=vi_VN` (không có `.UTF-8`). Trong Terminal của phiên đồ họa,
  `cd ~/onebee && sudo ./desktop/onebee-install.sh` dừng ngay:
  ```text
  [OneBee] Phát hiện Linux Mint 22.3
  [OneBee] Bắt đầu cài đặt — nhật ký: /var/log/onebee/install-20261114-005247.log
  ERROR: Ansible requires the locale encoding to be UTF-8; Detected TCVN.
  [OneBee] LỖI: Cài đặt chưa xong (mã lỗi 1). Gửi file /var/log/onebee/install-20261114-005247.log cho kỹ thuật OneBee.
  ```
  Ảnh `00-cai-desktop-lan-dau-loi-locale.png`. Nguyên nhân thấy được: `/etc/default/locale` là `LANG="vi_VN"`; Python chuẩn hóa tên này
  thành `('vi_VN', 'TCVN')` dù glibc dùng UTF-8 (`LANG=vi_VN locale charmap` in `UTF-8`).
- Chạy tạm bằng `sudo LANG=vi_VN.UTF-8 LC_ALL=vi_VN.UTF-8 ./desktop/onebee-install.sh`: `ok=106 changed=59 unreachable=0 failed=0 skipped=41`,
  bộ cài đổi `/etc/default/locale` thành `LANG=vi_VN.UTF-8`.
- Vì sao lần chạy sau không lỗi: task "Đặt ngôn ngữ mặc định của hệ thống" của role `base` ghi `LANG=vi_VN.UTF-8` vào `/etc/default/locale`
  (biến `onebee_locale`); sau khi khởi động lại, phiên đăng nhập mang `LANG=vi_VN.UTF-8`, Python đọc ra UTF-8 nên Ansible chạy được. Chỉ lần cài
  đầu trên máy Mint cài bằng tiếng Việt bị chặn. Đã sửa ở bộ cài (xem bảng cuối file).
- Khởi động lại, **lần 2 chạy đúng lệnh tài liệu** (chưa nối Box):
  `localhost : ok=100 changed=0 unreachable=0 failed=0 skipped=45 rescued=0 ignored=0` (ảnh `03-cai-desktop-lan-2-tong-ket.png`).
- Sau khi nối Box (`/etc/onebee/may-tram.env` từ `sudo onebee-box them-may ketoan-01`): lần 3 `ok=127 changed=21 failed=0`,
  lần 4 `ok=125 changed=0 unreachable=0 failed=0 skipped=20`. Lần 3 có cảnh báo đúng thiết kế:
  `CẢNH BÁO: các tài khoản có quyền sudo: kiemthu, quantri.`
- Box: lần 1 `ok=118 changed=26 failed=0` (phải kéo trước ảnh Docker từng cái một vì CDN Docker Hub ngắt kết nối giữa chừng —
  `connection reset by peer`, lỗi mạng, không phải lỗi bộ cài); lần 2 `ok=107 changed=0 unreachable=0 failed=0 skipped=39`.

## A. Lần đầu đăng nhập (tài khoản thường vừa tạo)
- [x] A1 Đăng nhập lần đầu → cửa sổ "Trung tâm OneBee" tự mở trong 30 giây; không có cửa sổ "Welcome" của Mint.
  Phiên bắt đầu 01:02:46, `onebee-trung-tam --lan-dau` chạy lúc 01:02:53 (7 giây); không có tiến trình `mintwelcome`
  (`/etc/xdg/autostart/mintwelcome.desktop` đã chuyển thành `.distrib`). Ảnh `A1-10s.png`.
- [x] A2 Đóng cửa sổ, đăng xuất, đăng nhập lại → cửa sổ không tự mở nữa; mở được từ menu Bắt đầu → Trung tâm OneBee.
  40 giây sau khi đăng nhập lại chỉ có cửa sổ màn hình nền; có file `~/.config/onebee/trung-tam-da-xem`. Ảnh `A2-dang-nhap-lai-40s.png`,
  `A2-menu-bat-dau.png`, `A2-mo-tu-menu.png`.
- [x] A3 Chờ 15 phút → không có cửa sổ Trình quản lý cập nhật tự bật.
  Liệt kê cửa sổ lúc 21 phút (phiên 1) và 24 phút (phiên 2): không có cửa sổ cập nhật; `mintUpdate` chỉ chạy ở khay hệ thống.
- [x] A4 Nhìn góc trái dưới → nút menu có logo OneBee và chữ "Bắt đầu". Ảnh `A1-10s.png`. Cần người nhìn lại độ dễ nhận.
- [x] A5 Nhìn góc phải dưới → đồng hồ có giờ và ngày/tháng/năm; trên màn hình 1366×768 thanh tác vụ không bị chật.
  Đồng hồ `01:14 14/11/2026`; ở 1366×768 với 9 biểu tượng (6 ghim + 3 cửa sổ) còn trống nhiều. Ảnh `A5-1366x768-writer.png`,
  `B4-C16-terminal-ket-qua.png`. Chưa thử khi mở 8–10 cửa sổ cùng lúc — cần người nhìn lại.
- [x] A6 Đăng xuất → màn hình đăng nhập có hình nền OneBee. Ảnh `A6-man-hinh-dang-nhap-sau-dang-xuat.png`.
  Ghi chú cảm nhận: khung đăng nhập đè lên một phần logo hình nền.

## B. Gõ tiếng Việt
- [x] B0 Ngay sau khi đăng nhập, chưa bấm phím đổi bộ gõ, gõ `Howjp tacs xax` trong LibreOffice Writer → ra "Hợp tác xã".
  Ảnh `B0-writer-go-telex-mac-dinh.png`; file đã lưu `kiem-thu-go-tieng-viet.docx` chứa đúng chuỗi `Hợp tác xã`.
- [x] B1 Nhìn khay hệ thống → có chỉ báo bộ gõ; phân biệt được đang gõ Việt hay Anh. Chỉ báo chữ `vi` / `en`. Ảnh `B2-sau-super-space-1.png`.
- [x] B2 Bấm Super + Space → chỉ báo đổi. `vi` → `en` → `vi`; ở `en` gõ ra nguyên `Howjp tacs xax`. Ảnh `B2-sau-super-space-1.png`,
  `B2-sau-super-space-2.png`, `B2-go-lai-tieng-viet.png`.
- [x] B3 Gõ `Howjp tacs xax` trong LibreOffice Writer, Firefox, ô tìm kiếm của menu Bắt đầu → ra "Hợp tác xã" ở cả ba nơi.
  Ảnh `B0-writer-go-telex-mac-dinh.png`, `B3-firefox-thanh-dia-chi.png`, `B3-C3-menu-bat-dau-tim-kiem.png`.
- [x] B5 Bấm Super + Space sang tiếng Anh, gõ `onebee.local` vào thanh địa chỉ Firefox và gõ một mật khẩu thử vào ô mật khẩu → không bị thêm dấu.
  Ảnh `B5-firefox-tieng-anh-onebee-local.png`, `B5-o-mat-khau-tieng-anh.png`.
  **Ghi lại:** ở chế độ tiếng Việt, ô mật khẩu **có bị thêm dấu** — gõ ` tacs vieetj` vào ô `type=password` ra ` tác việt`
  (trang thử hiện giá trị ô). Ảnh `B5-o-mat-khau-tieng-viet.png`.
- [x] B4 Mở Terminal, ghi lại kết quả (ảnh `B4-C16-terminal-ket-qua.png`):
  ```text
  $ gsettings get org.cinnamon.desktop.input-sources sources
  [('ibus', 'Bamboo'), ('ibus', 'BambooUs')]
  $ pgrep -a ibus-daemon
  5768 /usr/bin/ibus-daemon --daemonize --xim
  ```

## C. Phím tắt
Bảng đầu của `docs/huong-dan/to-phim-tat.md` tại commit 09644a4 có 16 dòng, khớp C1–C16.
- [x] C1 Đổi gõ tiếng Việt ⇄ tiếng Anh: Super + Space. (xem B2)
- [x] C2 Gõ Telex: `aa aw ee oo ow uw dd as af ar ax aj asz` → `â ă ê ô ơ ư đ á à ả ã ạ a`. Ảnh `C2-telex.png`; nội dung có trong file .docx đã lưu.
- [x] C3 Mở menu Bắt đầu: phím Super (ảnh `B3-C3-menu-bat-dau-tim-kiem.png`) và nút Bắt đầu (ảnh `C3-nut-bat-dau.png`).
- [x] C4 Super + R và Alt + F2 → hộp "Chạy lệnh". Ảnh `C4-super-r.png`, `C4-alt-f2.png`.
- [x] C5 Super + E → Nemo mở thư mục "Nhà". Ảnh `C5-super-e.png`.
- [x] C6 Super + D → hiện màn hình nền; bấm lại → cửa sổ trở lại. Ảnh `C6-super-d-lan-1.png`, `C6-super-d-lan-2.png`.
- [x] C7 Super + L và Ctrl + Alt + L → khóa màn hình (mỗi tổ hợp thử từ trạng thái chưa khóa), mở lại bằng mật khẩu.
  Ảnh `C7-super-l-khoa.png`, `C7-ctrl-alt-l-khoa.png`, `C7-mo-khoa-2.png`.
- [x] C8 Alt + Tab → chuyển sang cửa sổ khác (Terminal lên trên Writer). Ảnh `C8-alt-tab-dang-giu.png`. Không chụp được hộp chọn cửa sổ khi giữ Alt.
- [x] C9 Ctrl + Shift + Esc → mở Trình theo dõi hệ thống. Ảnh `C9-ctrl-shift-esc.png`. Ghi chú: thẻ `Processes`, `Resources`, `File Systems` còn tiếng Anh.
- [x] C10 Ctrl + C / V / X / Z trong Writer: chép–dán một dòng, cắt, hoàn tác đều đúng. Ảnh `C10-sao-chep-dan.png`, `C10-cat.png`, `C10-hoan-tac.png`.
- [x] C11 Ctrl + S và Ctrl + Shift + S → hộp lưu, định dạng mặc định `Word 2007 (.docx)`; lưu xong không hỏi giữ định dạng. Ctrl + P → hộp "In".
  Ảnh `C11-ctrl-s.png`, `C11-ctrl-shift-s.png`, `C11-ctrl-p.png`. Ghi chú: tiêu đề hộp lưu là `Save`; hộp In còn `Printer`, `Range and Copies`, `Print`.
- [x] C12 Nút PDF trên thanh công cụ có thật (chữ gợi ý `Export Directly as PDF`), bấm → hộp "Xuất" với định dạng PDF. Ảnh `C12-nut-pdf.png`,
  `I-nut-pdf-chu-goi-y.png`. Đối chiếu nhóm I.
- [x] C13 F7 → hộp "Chính tả: Việt". Ảnh `C13-f7.png`.
- [x] C14 Print Screen → hộp "Chụp màn hình" đề xuất lưu `Hình chụp từ … .png` vào "Ảnh". Ảnh `C14-print-screen.png`.
- [x] C15 Super + Shift + S → chọn vùng, kéo, Ctrl + V dán ảnh vào Writer; Shift + Print Screen → chọn vùng rồi hộp lưu thành file.
  Ảnh `C15-super-shift-s-chon-vung.png`, `C15-dan-vung-vao-writer.png`, `C15-shift-print-sau.png`.
- [x] C16 Ctrl + Alt + T → mở Terminal. Ảnh `B4-C16-terminal-ket-qua.png`.

Cả nhóm C đạt trong phiên Cinnamon trên máy ảo; vì chưa có người xác nhận lại nên **chưa xóa** dòng ghi chú ở đầu tờ phím tắt.

## D. Trung tâm OneBee và tự phục vụ
- [x] D1 Bấm 6 ô của trang Bắt đầu → mở đúng thứ ghi trên ô.
  Chưa nối Box: Soạn văn bản → Writer mới; Bảng tính → Calc mới; Thư mục của tôi → Nemo "Nhà"; Thư mục chung → báo
  "Máy này chưa nối OneBee Box nên chưa có thư mục chung. Hãy báo kỹ thuật OneBee."; Trợ lý AI → báo "Máy này chưa kết nối OneBee Box
  nên chưa có Trợ lý AI…"; Cần giúp đỡ → trang Cần giúp đỡ. Sau khi nối Box: Thư mục chung → Nemo hỏi tài khoản cho chia sẻ "chung"
  (đúng thiết kế: tài khoản `onebee`), nhập xong mở được thư mục chung; Trợ lý AI → Firefox mở trang đăng nhập Trợ lý.
  Ảnh `D1-o1-…` đến `D1-o6-…`, `D1-o4-thu-muc-chung-da-mo.png`, `D1-o5-tro-ly-ai-da-noi-box.png`.
  Ghi chú bố cục: ở 1366×768 cửa sổ chỉ thấy đủ 4 ô, hàng ô "Trợ lý AI" và "Cần giúp đỡ" bị che một nửa, phải cuộn mới thấy (`D1-trung-tam-1366.png`).
- [ ] D2 Trang Phím tắt → nội dung trùng tờ phím tắt.
  Mọi dòng trên trang đều đúng chữ của tờ, nhưng trang **thiếu 2 dòng** của tờ: "Xuất PDF (Writer, Calc) — Nút PDF trên thanh công cụ" và
  "Mở cửa sổ dòng lệnh — Ctrl + Alt + T"; cũng không nhắc "Shift + Print Screen" và "nút Bắt đầu". Có thể là chủ ý (nguồn chung
  `onebee-cam-nang.json` chỉ có 13 mục) — cần người quyết. Ảnh `D2-trang-phim-tat.png`, `D2-trang-phim-tat-cuon.png`. Commit 09644a4.
- [x] D3 Kiểm tra máy → "Kiểm tra ngay": kết quả hiện trong khoảng 8 giây.
  Chưa nối Box: 7 mục (3 đạt, 4 lỗi), dòng "Có 4 mục lỗi…". Đã nối Box: **9 mục** (Cổng mạng, OneBee Box, Trợ lý AI, Thư mục chung,
  Nhận sao lưu, Phần mềm sao lưu, Lịch sao lưu, Lần sao lưu cuối, Ổ chứa /home), 8 đạt, 1 lỗi ("Máy chưa sao lưu lần nào" — đúng lúc đó).
  Ở 1366×768 không thấy cắt chữ, tràn khung hay chồng nút; danh sách cuộn trong khung. Ảnh `D3-kiem-tra-chua-noi-box-c.png`,
  `D3-kiem-tra-chua-noi-box-cuon.png`, `D3-da-noi-box-50s.png`, `D3-da-noi-box-cuon.png`.
  Cần người nhìn lại: gợi ý có lệnh kỹ thuật (`sudo onebee-box them-may <tên-máy>`, `journalctl -u onebee-sao-luu -n 30`); khi mạng tốt
  nhưng chưa nối Box, mục "Dịch vụ trên Box" vẫn gợi ý "Sửa phần Mạng ở trên trước".
- [x] D4 Ngắt card mạng máy ảo (`vmrun disconnectNamedDevice … ethernet0`), kiểm tra lại → "Cổng mạng (router): Máy chưa có mạng →
  Kiểm tra dây mạng (đèn ở cổng mạng) hoặc kết nối Wi-Fi của máy". Cắm lại, máy có mạng trở lại. Ảnh `D4-rut-mang.png`.
- [x] D5 **[cần Box]** "Báo cần hỗ trợ kèm kết quả này" → Firefox mở `…/form/onebee-ho-tro?may=ketoan-01&mo_ta=…`; ô "Máy" là `ketoan-01`,
  ô mô tả có "Tự kiểm tra máy: Lần sao lưu cuối: Máy chưa sao lưu lần nào". Ảnh `D5-bieu-mau-o-may.png`.
  Ghi chú: hai ô chọn hiện chữ tiếng Anh `Select an option ...`. Chưa bấm gửi biểu mẫu.
- [x] D6 **[cần Box]** Lần đầu trình duyệt hỏi tài khoản (`D5-D6-bao-ho-tro-lan-dau.png`), nhập `nhanvien` → vào biểu mẫu.
  Ghi lại: **Firefox có đề nghị lưu mật khẩu** (`D5-bieu-mau-sau-dang-nhap.png`); **lần mở sau trong cùng buổi không hỏi lại** (`D7-D6-menu-bao-ho-tro-lan-2.png`).
- [x] D7 **[cần Box]** Menu Bắt đầu → "Báo cần hỗ trợ (OneBee)" → biểu mẫu có sẵn `ketoan-01`. Ảnh `D7-menu-tim-onebee.png`, `D7-D6-menu-bao-ho-tro-lan-2.png`.
  Khi chưa nối Box, nút "Báo cần hỗ trợ" ở trang Cần giúp đỡ báo rõ lý do (`D-bao-can-ho-tro-chua-noi-box.png`).

## E. Trợ lý tập tin Windows
- [x] E1 Bấm đúp `ZaloSetup.exe` → hộp "Trợ lý tập tin Windows — OneBee OS": "Phát hiện: Zalo (Bản cài đặt Windows)… Dùng Zalo ngay trên trình duyệt
  (Zalo Web)"; bấm "Mở Zalo Web" → Firefox mở "Đăng nhập tài khoản Zalo". Ảnh `E1-zalosetup-hop-thoai.png`, `E1-mo-zalo-web.png`.
- [x] E2 **[cần Box]** Bấm đúp `PhanMemKeToanXYZ.exe` → hộp chọn chỉ có "Báo cần hỗ trợ (gửi yêu cầu cho kỹ thuật OneBee)" và "Đóng lại";
  chọn → biểu mẫu mở với Loại sự cố "Phần mềm chỉ chạy trên Windows", mô tả "Cần dùng file Windows: PhanMemKeToanXYZ.exe".
  Ảnh `E2-exe-la-hop-chon.png`, `E2-bieu-mau-loai-windows.png`. Ghi chú: nút của hộp chọn là `Cancel` / `OK` (tiếng Anh).
- [x] E3 Bấm đúp `thu-nghiem.AppImage` → không có hộp thoại "phần mềm Windows" (chương trình chạy và thoát ngay). Ảnh `E3-appimage.png`.
  Dùng file ELF đổi tên, chưa thử AppImage thật.

## F. Sao lưu
- [x] F1 Lệnh giả lập trễ 80 giờ rồi `systemctl --user start onebee-nhac-sao-luu.service` → thông báo "OneBee: máy chưa sao lưu 3 ngày",
  "Hãy để máy bật qua 12 giờ trưa. Nếu mai vẫn thấy thông báo này, mở Trung tâm OneBee → Cần giúp đỡ → Báo cần hỗ trợ." Ảnh `F1-thong-bao-sao-luu-tre.png`.
- [x] F2 Chạy lại → `rc=0`, không có thông báo lần hai (`F2-chay-lai-khong-thong-bao.png`). `sudo onebee-sao-luu` →
  `snapshot e854cebf saved`, `Sao lưu xong: 14/11/2026 01:46`; `/var/lib/onebee/sao-luu-cuoi` về đúng giờ thật (`F2-sao-luu-that.png`).
- [x] F3 `systemctl --user list-timers | grep onebee` → `onebee-nhac-sao-luu.timer` (lần chạy kế 02:08:36); `--all` cho cùng kết quả. Ảnh `F3-list-timers.png`.

## G. Trợ lý AI (cần Box)
Tài khoản nhân viên thử `nhanvien@onebee.lan` do quản trị tạo trên Box (theo tài liệu: đăng ký tự do đã tắt).
- [ ] G1 **[cần Box]** Bấm biểu tượng Trợ lý AI OneBee trên thanh tác vụ (mở thành một thẻ Firefox), đăng nhập → có dòng
  "THÔNG TIN Trợ lý AI có thể sai. Hãy đọc lại số liệu, tên, ngày tháng trước khi dùng…" nhưng **chỉ hiện 3 gợi ý mỗi lần**, không phải 4.
  Tải lại trang 6 lần: mỗi lần 3 trong 4 gợi ý, thứ tự và gợi ý bị ẩn thay đổi ("Soạn thông báo" vắng ở 4/6 lần). Cả 4 gợi ý có trong cấu hình.
  Ảnh `G1-goi-y-va-dong-nhac.png`, `G1-tai-lai-1.png`, `G1-tai-lai-2.png`. Commit 09644a4.
- [x] G2 **[cần Box]** Bấm "Lập biên bản họp" → câu mở đầu chèn vào ô nhập, chưa gửi (`G2-bam-goi-y-chen-cau.png`); viết tiếp "… hoạch thu hoạch lúa
  vụ mùa", gửi → nhận biên bản tiếng Việt có ngoặc vuông cho chỗ thiếu (`G2-tra-loi-120s.png`, `G2-tra-loi-xong.png`).
  Thời gian trên máy ảo (Box 4 CPU, không GPU, máy Mac đang chạy cả máy trạm): "Đang suy luận…" tới giây 75, chữ đầu tiên hiện giữa giây 75 và 90,
  trả lời xong khoảng 7 phút. **Không dùng làm số đo tốc độ.**
- [x] G3 **[cần Box]** Gõ `/` → mục "Prompt" có `bao-cao`, `hop-dong`, `bien-ban`, `to-trinh`. Ảnh `G3-go-gach-cheo.png`.
- [x] G5 Trợ lý "Tra cứu Luật HTX và Nghị định 30": bỏ qua — chưa có trong bản này.
- [ ] G4 **[cần Box]** Chữ tiếng Anh nhìn thấy (ảnh `G1-…`, `G2-tra-loi-90s.png`, `G3-…`, `G4-…`):
  - Đăng nhập: `Email`, `Open WebUI` (tiêu đề "Đăng nhập vào Open WebUI", tên thẻ trình duyệt); Firefox hỏi "Dịch trang này? … Dịch từ Tiếng Anh".
  - Hỏi một câu: `Gợi ý một số mẫu prompt`, `Thought` (nhãn phần suy luận), `Follow up`, khi gõ `/`: `Commands`, `Temporary`, `Prompt`.
  - Xem lại lịch sử: `Open WebUI`, `Folders`, `Chat`; menu người dùng: `Update your status`.
  - Đổi mật khẩu (Cài đặt → Tài khoản): `Personal`, `Basics`, `Keyboard`, `Preferences`, `Data`, `Data Controls`, `Usage`, `(Notification)`,
    `Upload Photo`, `Initials`, `Gravatar`, `Bio`, `Share your background and interests`, `Add optional profile context visible where profiles are shown.`,
    `Gender`, `Prefer not to say`, `Choose the gender value stored on your profile.`, `Birth Date`, `Set the birth date saved with your profile.`,
    `Set the display name shown across your account.`, `User Variables`, `No user variables configured.`, `Update the password used for email and password sign-in.`,
    `API Keys`, `Secrets`, `Show or hide sensitive account secrets.`; Cài đặt chung: `Choose the color theme used by the interface.`,
    `Choose the language used for interface text.`, `Set the default system prompt for new chats.`, `Model parameters`, `Show or hide custom generation parameters.`
    Chỉ mở ô đổi mật khẩu, chưa đổi thật.
  - Đăng xuất: không thấy chữ tiếng Anh mới (quay về trang đăng nhập ở trên).

## H. Trang chủ Box (`http://onebee.local` từ máy trạm) [cần Box]
Chưa kiểm từ điện thoại (không có điện thoại trong mạng thử).
- [ ] H1 Cẩm nang "Phím tắt hay dùng" không còn chữ "Mở Terminal" (đạt phần này), nhưng **không trùng hoàn toàn tờ phím tắt**: giống trang Phím tắt
  của Trung tâm, thiếu dòng "Xuất PDF — Nút PDF trên thanh công cụ" và "Mở cửa sổ dòng lệnh — Ctrl + Alt + T" (xem D2). Bằng chứng: chữ của trang
  lấy bằng `curl -s http://localhost/` trên Box; ảnh `H-trang-chu-box.png`.
- [x] H2 Mục "Soạn văn bản bằng Trợ lý AI" có 4 thẻ (`H2-muc-soan-van-ban.png`); bấm "Tóm tắt văn bản" → Trợ lý mở với
  `?models=onebee-tro-ly&q=Tóm tắt văn bản sau thành 5 ý chính…`, câu mở đầu điền sẵn, **không tự gửi** (`H2-sau-dang-nhap.png`).
  Ghi chú: thẻ mở `http://onebee.local:3000` còn biểu tượng Trợ lý trên máy trạm mở `http://192.168.72.50:3000`, nên dù đã đăng nhập ở một bên
  vẫn phải đăng nhập lại ở bên kia. Ở trang đăng nhập HTTP, Firefox hiện cảnh báo "Đây là kết nối không an toàn… Tìm hiểu thêm" che ô mật khẩu;
  bấm nhầm vào cảnh báo sẽ mở trang trợ giúp Mozilla (`H2-canh-bao-dang-nhap-khong-an-toan.png`).
- [x] H3 Sau `sudo onebee-box sao-luu` (máy trạm đã sao lưu lúc 01:46) → ô "Máy trạm đã sao lưu: 1/1 máy (trong 3 ngày)"; `trang-thai.json`
  chỉ có `{"tong": 1, "sao_luu_trong_han": 1}`, không có tên máy; chữ trang không có `ketoan-01`. Ảnh `H3-may-tram-da-sao-luu.png`.

## I. Xuất PDF
LibreOffice Writer trên máy này mở với **thanh công cụ chuẩn, không phải giao diện tab** (dù đã có `/usr/lib/libreoffice/share/registry/onebee-office-ribbon.xcd`
và hồ sơ người dùng không ghi đè). Ba cách đã thử:
- [ ] I1 Ghi lại cách nào có thật và tên đúng từng chữ:
  - Nút PDF trên thanh công cụ: **có**, chữ gợi ý `Export Directly as PDF`, mở hộp "Xuất" với định dạng PDF (`I-nut-pdf-chu-goi-y.png`, `C12-nut-pdf.png`).
  - "Tệp → Xuất dưới dạng → Xuất thành PDF": **không có đúng chữ này**. Có: menu **Tập tin → Export As → Xuất dạng PDF...**
    (cùng mục con `Export Directly as PDF`, `Export as EPUB...`, `Export Directly as EPUB`), và **Tập tin → Xuất...** (`I-menu-tap-tin.png`, `I-menu-export-as.png`).
  - "Tệp → Xuất ra PDF": **không có**. Trang chủ Box đang ghi "menu Tệp → Xuất ra PDF (File → Export as PDF)" → sai so với màn hình.
  Tờ phím tắt ghi "Nút PDF trên thanh công cụ" → khớp.

## J. Năm việc đầu tiên với người dùng thật
- [ ] J1–J5 bỏ qua: kiểm tự động, không có nhân viên thật.

## Ghi chú ngoài phiếu
- LibreOffice không mở giao diện tab (Ribbon) như `docs/huong-dan/cai-dat-onebee-os-desktop.md` ghi (ảnh `B0-writer-mo.png`, `A5-1366x768-writer.png`);
  lần đầu mở Writer có hộp "Mẹo của ngày" và thanh "Bạn hiện đang sử dụng LibreOffice phiên bản 24.2 lần đầu tiên".
- Chữ tiếng Anh ở ứng dụng nền: menu Writer `Styles`, `Table`, `Form`, `Open Remote...`, `Templates`, `Export As`, `Print Preview`, `Digital Signatures`;
  hộp đóng tài liệu `Save Document? … Don't Save / Save`; Firefox lần đầu mở trang chào tiếng Anh ("We love keeping you safe") và thẻ "Firefox Privacy Notice".
- Firefox gạch đỏ chữ tiếng Việt trong ô soạn của Trợ lý (kiểm chính tả của trình duyệt không có từ điển tiếng Việt) — `G2-bam-goi-y-chen-cau.png`.
- Sau khi nối Box, SSH vào máy trạm chỉ còn `onebee-quantri` (đúng thiết kế); kiểm phần còn lại qua VMware Tools.

## Mục không đạt và cách xử lý
Số mục không đạt trong A–I: 5 (D2, G1, G4, H1, I1), cộng 1 lỗi cài đặt ngoài phiếu. Theo rủi ro của plan, quá 5 mục thì dừng và báo; ở đây vừa đủ 5
nên ghi lại và báo. Nhóm B đạt toàn bộ. Sau khi anh Thiện quyết, các mục được xử lý trên nhánh `fix/muc-khong-dat-phieu-kiem-trai-nghiem`
(cột Trạng thái ghi commit); kết quả kiểm lại ở mục "Kiểm lại sau khi sửa".

| Mục | Điều đã thấy | Ảnh / log | Cách xử lý | Trạng thái |
|---|---|---|---|---|
| Cài đặt (ngoài phiếu) | Mint cài bằng tiếng Việt (`LANG=vi_VN`): `sudo ./desktop/onebee-install.sh` dừng với `ERROR: Ansible requires the locale encoding to be UTF-8; Detected TCVN.` | `00-cai-desktop-lan-dau-loi-locale.png` | Anh Thiện quyết sửa. Bộ cài Desktop, bộ cài Box (cả đường cài từ USB) và `onebee-box cap-nhat-may`/`dong-bo-may` gọi `ansible-playbook` với `LC_ALL=C.UTF-8` (có sẵn trong glibc); test `tests/desktop/test_onebee_locale_ansible.py`, lần cài đầu trong test container Desktop và Box chạy với `LANG=vi_VN` | đã sửa (commit 0e24e34) |
| D2 | Trang Phím tắt thiếu 2 dòng của tờ: "Xuất PDF — Nút PDF trên thanh công cụ", "Mở cửa sổ dòng lệnh — Ctrl + Alt + T" | `D2-trang-phim-tat.png`, `D2-trang-phim-tat-cuon.png` | Anh Thiện quyết: chủ ý, không sửa mã. "Mở cửa sổ dòng lệnh" cố ý không đưa cho nhân viên; "Xuất PDF — nút PDF" không phải phím tắt. Sửa phiếu D2: trang khớp 13 mục của nguồn chung | giới hạn đã biết: phiếu ghi quá chặt, đã sửa phiếu (commit c581b31) |
| G1 | Màn hình trò chuyện mới chỉ hiện 3 trong 4 gợi ý, đổi ngẫu nhiên mỗi lần tải | `G1-goi-y-va-dong-nhac.png`, `G1-tai-lai-1.png`, `G1-tai-lai-2.png` | Anh Thiện quyết: cách Open WebUI hiển thị, không sửa mã. Mã v0.11.4: `Suggestions.svelte` xáo thứ tự gợi ý mỗi lần tải (`sort(() => Math.random() - 0.5)`) và khung gợi ý cao cố định, ẩn thanh cuộn (`max-h-36 overflow-auto scrollbar-none`) nên thường thấy 3. Sửa phiếu G1 | giới hạn đã biết: Open WebUI hiện ngẫu nhiên một phần gợi ý mỗi lần tải; đã sửa phiếu (commit 16f2281) |
| G4 | Nhiều chữ tiếng Anh khi đăng nhập, hỏi, xem lịch sử, đổi mật khẩu (danh sách ở mục G4) | `G2-tra-loi-90s.png`, `G3-go-gach-cheo.png`, `G4-*.png` | Theo bảng 7.4: `box/ansible/roles/box-ai/files/giao-dien-tieng-viet.json` (40 chuỗi của G4), `enforce_settings` gửi thêm `I18N`, test với máy chủ giả. Khóa là đúng chuỗi giao diện gọi: chữ tiếng Anh gốc, riêng trang Cài đặt là khóa `settings.…` (vd "Bio" là `settings.personal.account.bio.label`); "Gợi ý một số mẫu prompt" là bản dịch sẵn của khóa `Suggested` | đã sửa (commit a918fe7); giới hạn đã biết: tên "Open WebUI" (biến `WEBUI_NAME`, không qua bản dịch, giấy phép hạn chế đổi tên), tên riêng "Gravatar", lời hỏi dịch trang của Firefox |
| H1 | Cẩm nang trang chủ Box thiếu 2 dòng của tờ phím tắt (như D2); phần "không còn Mở Terminal" đạt | `H-trang-chu-box.png`, chữ trang qua `curl` | Như D2. Sửa phiếu H1: cẩm nang trang chủ Box khớp 13 mục của nguồn chung | giới hạn đã biết: phiếu ghi quá chặt, đã sửa phiếu (commit c581b31) |
| I1 | Màn hình có "Tập tin → Export As → Xuất dạng PDF..." và nút `Export Directly as PDF`; không có "Tệp → Xuất ra PDF" như trang chủ Box ghi | `I-menu-tap-tin.png`, `I-menu-export-as.png`, `I-nut-pdf-chu-goi-y.png` | Theo bảng 7.4. Trang chủ Box (`index.html.j2`) nay ghi: nút **PDF** trên thanh công cụ (chữ gợi ý: Export Directly as PDF) hoặc menu **Tập tin → Export As → Xuất dạng PDF...**; test trong `tests/box/test_onebee_mdns_dashboard.py`. Tờ phím tắt đã đúng ("Nút PDF trên thanh công cụ"), không sửa. Lời dặn Trợ lý (`tro-ly-onebee-loi-dan.md`) **chưa sửa**: phải chấm lại nhóm 1 bằng Ollama | đã sửa (commit 2bf0371) ở trang chủ Box; lời dặn Trợ lý vẫn ghi "Tệp → Xuất dưới dạng → Xuất thành PDF", để đợt sau khi có máy chấm |

## Kiểm lại sau khi sửa (14/11/2026, cùng hai máy ảo, nhánh `fix/muc-khong-dat-phieu-kiem-trai-nghiem`)
Kiểm tự động như trên, chưa có người xác nhận.
- **Locale, máy Mint:** đặt lại `/etc/default/locale` thành `LANG="vi_VN"` như lúc mới cài; trong phiên `quantri`, `export LANG=vi_VN`
  (sudo giữ nguyên `LANG=vi_VN`), `sudo ./desktop/onebee-install.sh`:
  - bản cũ (commit 5f2993d): `ERROR: Ansible requires the locale encoding to be UTF-8; Detected TCVN.`, mã lỗi 1 — tái hiện đúng lỗi;
  - bản sửa, lần 1: `localhost : ok=125 changed=2 unreachable=0 failed=0 skipped=20` (đổi lại `LANG=vi_VN.UTF-8` trong `/etc/default/locale`
    và tạo thư mục chạy của sshd sau khởi động lại — task sẵn có);
  - bản sửa, lần 2 (vẫn `LANG=vi_VN`): `localhost : ok=125 changed=0 unreachable=0 failed=0 skipped=20`.
- **Locale, Box** (Ubuntu Server chỉ có locale `C.utf8`, `en_US.utf8`): `sudo LANG=vi_VN ./onebee-box-install.sh` — bản cũ:
  `ERROR: Ansible could not initialize the preferred locale: unsupported locale setting`; bản sửa lần 1 `ok=107 changed=5 failed=0`
  (cài file mới, đồng bộ Trợ lý), lần 2 `ok=107 changed=0 unreachable=0 failed=0 skipped=39`.
- **G4:** `/api/config` trên Box (chưa đăng nhập) trả đủ 40 bản dịch của `giao-dien-tieng-viet.json`. Trên máy Mint, Firefox cửa sổ riêng tư:
  trang đăng nhập "Thư điện tử"; màn hình mới "Gợi ý"; menu người dùng "Cập nhật trạng thái"; Cài đặt: "Cá nhân", "Cơ bản", "Phím tắt",
  "Tùy chọn", "Dữ liệu", "Quản lý dữ liệu", "Mức sử dụng", "Thông báo trên máy tính", các dòng mô tả; Tài khoản: "Tải ảnh lên",
  "Chữ cái đầu tên", "Giới thiệu", "Giới tính", "Không nêu", "Ngày sinh", "Biến của người dùng". Ảnh `G4-sau-sua-dang-nhap.png`,
  `G4-sau-sua-goi-y.png`, `G4-sau-sua-menu-nguoi-dung.png`, `G4-sau-sua-cai-dat-chung.png`, `G4-sau-sua-tai-khoan.png`.
  Còn tiếng Anh: "Open WebUI", "Gravatar", ô gợi ý "Nhập Email của bạn" (bản dịch sẵn của Open WebUI, ngoài danh sách G4).
  Chưa chụp lại: "Thought", "Follow up", "Commands", "Temporary", mục `/`, "Thư mục", "Cuộc trò chuyện", "Khóa API", "Thông tin bí mật"
  (có trong `/api/config` ở trên, chưa mở đúng màn hình đó).
- I1: chữ trang chủ Box đổi theo commit 2bf0371, kiểm bằng test; chưa mở lại trang trên máy ảo.

## Thấy thêm ngoài phiếu, để đợt sau
- LibreOffice không mở giao diện tab (Ribbon) dù đã có `/usr/lib/libreoffice/share/registry/onebee-office-ribbon.xcd`
  và hồ sơ người dùng không ghi đè (xem nhóm I và "Ghi chú ngoài phiếu").
- Thẻ "Soạn văn bản bằng Trợ lý AI" trên trang chủ Box mở `http://onebee.local:3000`, còn biểu tượng Trợ lý trên máy trạm mở theo IP
  (`http://192.168.72.50:3000`), nên đã đăng nhập ở một bên vẫn phải đăng nhập lại ở bên kia (xem H2).
- Ô mật khẩu bị thêm dấu khi đang ở chế độ gõ tiếng Việt (gõ ` tacs vieetj` ra ` tác việt`, xem B5).
