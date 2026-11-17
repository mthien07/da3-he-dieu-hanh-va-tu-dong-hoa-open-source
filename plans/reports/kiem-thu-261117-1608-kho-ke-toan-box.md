# Kiểm thử kho và kế toán trên Box test

- Thời điểm: 17/11/2026, 15:00–16:10 (giờ Việt Nam)
- Box: 192.168.100.127 (`box.test.onebee.internal`), mã đơn vị `test`
- Nhánh: `feat/box-kho-ke-toan` (worktree `.worktrees/kho-ke-toan`)
- Người thực hiện: Dương Minh Thiện

## Kết quả

Bài kiểm `sudo tests/box/check-kho-ke-toan.sh local` chạy trên Box thật, qua HTTPS:

```
PASS  Bốn tài khoản kiểm (nhân viên, thủ kho, kế toán, quản lý) đăng nhập đúng vai trò
PASS  Thủ kho tạo thẻ kho và ghi phiếu nhập 100 kg qua API
PASS  Tồn 100 kg, bút toán Nợ 156 / Có 111 = 7.000.000; nhân viên và thủ kho không đọc được sổ, kế toán không duyệt đơn
PASS  Duyệt đơn 30 kg: phiếu xuất 30 kg, tồn 70, doanh thu 3.000.000 và giá vốn 2.100.000, mọi bút toán cân
PASS  Duyệt đơn vượt tồn bị chặn (đơn vẫn CHO_DUYET), nhập số âm bị 400, nhân viên không gọi được hàm nhập kho
```

Kiểm trực tiếp trên CSDL thật (psql, cùng dữ liệu) cũng cho: tồn 70, phiếu `NHAP:100` và `XUAT:30`,
tổng Nợ = tổng Có; duyệt đơn 500 kg báo `Không đủ tồn kho: mặt hàng "Mật ong kiểm thử Box" còn 70, cần 500`
và đơn vẫn `CHO_DUYET`.

Dữ liệu kiểm được dọn sạch sau khi chạy (0 đơn, 0 mặt hàng, 0 phiếu, không còn tài khoản `kkt-*`).

Chạy lại bộ cài ngay sau đó: `ok=160 changed=0 failed=0` — lần hai không đổi gì.

## Kiểm giao diện bằng trình duyệt tự động (Playwright, 20:01–20:03)

Đăng nhập sẵn bốn phiên rồi bấm thật từng nút: **16/16 đạt** — thêm mặt hàng, ghi phiếu nhập,
xuất CSV tồn kho và sổ kho, gửi đơn, duyệt đơn, tồn còn 40, thấy bút toán 131/511, xuất CSV
nhật ký và cân đối, ẩn/hiện nút Kho – Kế toán theo vai trò. Ảnh chụp ở `docs/huong-dan/anh/kho-ke-toan/`,
gắn vào `docs/huong-dan/dung-so-kho-va-ke-toan.md`.

Trong lúc chụp phát hiện bảng tồn kho bị bóp cột trong thẻ hẹp: sửa CSS cho thẻ Tồn kho chiếm trọn hàng
và cột số căn phải; chụp lại bộ ảnh sau khi sửa.

## Lỗi gặp khi kiểm và cách xử lý

| Lỗi | Nguyên nhân | Xử lý |
|---|---|---|
| Cài đặt dừng: chưa khai `onebee_box_ma_don_vi` | Bản sao repo trên Box dùng giá trị mẫu | Đặt `test` cho bản sao trên Box (không đưa vào mã nguồn) |
| `PGRST202`: không khớp hàm `them_nhap_kho` | Lời gọi chỉ gửi `p_dien_gia`, `p_dong`; hàm không có giá trị mặc định | Thêm `008-nhap-kho-tham-so-mac-dinh.sql` (tạo lại hàm với DEFAULT) |
| Bài kiểm báo sai thứ tự tài khoản | Kỳ vọng so sánh chưa sắp xếp tuple | Sửa kỳ vọng trong bài kiểm (dữ liệu thật vẫn đúng) |
| Lớp hai TOTP hỏng: `no TOTP configuration`, thiếu mã xác minh | Authelia giới hạn số lần xin nâng phiên (bucket 1) khi chạy lại bài kiểm liền nhau | Bài kiểm chờ và thử lại khi gặp 429; khởi động lại `onebee-authelia` để xoá bộ đếm trong bộ nhớ |
| `onebee-quy-trinh` unhealthy sau khi cài bản nhánh | Nhánh tách từ 1.3.0, thiếu bản vá healthcheck của 1.3.1 (image đọc `/data/settings.js`) | Cherry-pick `540cc39` (healthcheck riêng, gọi `/quy-trinh/auth/login`) vào nhánh; cài lại → healthy |
| Playwright không chờ được do CSP `script-src 'self'` | `wait_for_function` chèn eval vào trang | Chờ bằng `page.evaluate` trong vòng lặp (bộ kiểm UI) |
| Bảng tồn kho bị bóp/cắt cột | Thẻ hẹp 3 cột chứa bảng 7 cột | CSS: thẻ Tồn kho chiếm trọn hàng, cột số căn phải; chụp lại ảnh |

## Thay đổi trên Box test

- Đã bật HTTPS (`onebee_box_https: true`) để kiểm API và trang Sổ điều hành.
- `may-mint` chưa đồng bộ CA và chưa báo tình trạng trong 2 giờ, nên lần bật HTTPS dùng
  `onebee_box_https_bo_qua_chot_chan: true`. Khi máy đó hoạt động lại, chạy
  `sudo onebee-box dong-bo-may may-mint` để đưa CA xuống máy.
- Cấu hình riêng (`ma_don_vi: test`, HTTPS) nằm trong bản sao repo ở `/root/onebee-test`, không vào mã nguồn.
- Sao lưu trước khi đổi lược đồ: `/tmp/onebee-truoc-kho-20261117-1504.dump`; bộ cài tự kết xuất CSDL
  trước mỗi tệp lược đồ mới (`/srv/onebee/postgres-ket-xuat/truoc-luoc-do-*.dump`).

## Chưa kiểm

- Bấm nút Xuất CSV trên trình duyệt thật (chỉ kiểm tĩnh mã trang và định dạng CSV trong bài kiểm đơn vị).
- Hiển thị khu Kho/Kế toán theo vai trò trên trình duyệt (kiểm qua API và đăng nhập; chưa chụp màn hình).
- Chạy `check-so-dieu-hanh.sh` (bài cũ) trên Box thật sau khi thêm bước chuẩn bị tồn kho; mới chạy bộ kiểm tĩnh.
- Máy trạm `may-mint` nhận cấu hình mới và CA.
