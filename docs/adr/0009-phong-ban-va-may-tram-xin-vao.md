# ADR 0009 — Phòng ban và máy trạm xin vào Box

- Ngày: 19/11/2026 · Trạng thái: Đề xuất. Đã kiểm thử đơn vị và kiểm trong container; chưa thử trên Box thật và máy Mint thật.
- Hướng dẫn dùng: [phong-ban-va-may-xin-vao.md](../huong-dan/phong-ban-va-may-xin-vao.md)

## Bối cảnh
Đơn vị có nhiều phòng (kế toán, kho, …), mỗi phòng cần một chỗ để tài liệu riêng mà phòng khác không xem được, và mỗi phòng dùng
phần mềm khác nhau. Trước đây chỉ có một thư mục chung với một mật khẩu Samba chung. Cấp máy trạm theo chiều Box đẩy xuống:
quản trị chạy `them-may` trên Box, chép cấu hình (có mật khẩu kho sao lưu) sang máy trạm bằng tay, rồi chạy lại bộ cài.
Bước chép tay vừa chậm vừa dễ lộ bí mật (USB, tin nhắn).

## Quyết định
1. **Phòng ban là một sổ trên Box** (`/srv/onebee/phong-ban-so/<mã>.json`: tên hiển thị và danh sách gói apt), tạo bằng dòng lệnh
   (`them-phong`). Mỗi máy thuộc nhiều nhất một phòng.
2. **Cách ly bằng tài khoản Samba riêng từng phòng** (`pb-<mã>`, mật khẩu sinh tự động). Chia sẻ `[pb-<mã>]` đặt
   `valid users = pb-<mã>`, kèm `access based share enum = yes` để phòng khác không thấy cả tên chia sẻ (đã thử trên Samba của
   Ubuntu 24.04). Chỉ máy của phòng mới nhận mật khẩu phòng. Trên máy trạm, thư mục phòng gắn bằng systemd automount CIFS
   (SMB 3.1.1, mã hóa) tại `/mnt/phongban`; mọi tài khoản trên máy đó đều dùng được.
3. **Máy trạm xin vào, người thật duyệt.** Cổng 80 nhận yêu cầu không cần đăng nhập, nhưng Box không cấp gì khi chưa có người nhóm
   `quan_ly`/`ky_thuat` bấm Duyệt trên Sổ điều hành (sau đăng nhập một lần hai lớp), hoặc chạy `duyet-may` trên Box. Hai điểm duyệt
   lấy danh tính qua `/api/toi` (cầu nối danh tính), không tin tiêu đề `Remote-*`.
4. **Chống đứng giữa bằng cam kết + mã đối chiếu 6 số** (kiểu so số của Bluetooth). Box gửi cam kết băm của số ngẫu nhiên `n_b`
   trước, máy trạm mới gửi `n_w`, rồi Box mới lộ `n_b`. Mã = băm(id, khóa máy, vân tay CA, n_w, n_b). Kẻ đứng giữa phải chốt số của
   mình trước khi thấy số của bên kia, nên chỉ có xác suất 1/10⁶ làm hai mã trùng nhau. Mã khớp thì cả khóa của máy lẫn CA của Box đều đúng.
5. **Cấu hình ký rồi mã hóa riêng cho máy**: Box (root) ký `may-tram.env` bằng CA trung gian của Box (CMS), kèm `id` và `n_w` của yêu cầu,
   rồi mã hóa (RSA-OAEP-SHA256 + AES-256-GCM) tới chứng chỉ tự ký máy gửi lên. Máy kiểm chữ ký bằng đúng CA đã dùng để so mã, kiểm `id`/`n_w`
   (không dùng lại được cấu hình của yêu cầu khác) và `BOX_CA_VAN_TAY`. Không có chữ ký thì kẻ đứng giữa tự mã hóa được cấu hình giả
   (khóa SSH quản trị của nó) tới chứng chỉ công khai của máy — lỗi này tìm ra khi rà soát và đã sửa trước khi phát hành.
   Hai bên đều phải **gõ lại mã**: máy trạm gõ mã thấy trên web Box (chống Box giả qua mDNS), người duyệt gõ mã thấy trên máy trạm.
6. **Root không tin Node-RED**: Node-RED (uid 1000) chỉ ghi tệp yêu cầu/quyết định. Root (`onebee-xin-vao.path` → `xu-ly-xin-vao`)
   kiểm lại mọi trường, tự tính lại băm khóa, cam kết và vân tay CA, rồi mới cấp như `them-may`.
7. **Sao lưu theo phòng**: mỗi phòng một bản chụp restic riêng (nhãn `phong-<mã>`), khôi phục riêng một phòng vào thư mục
   `khoi-phuc-<ngày-giờ>` của phòng đó. Sổ phòng ban nằm trong bản chụp dữ liệu Box; `khoi-phuc-toan-bo` dựng lại tài khoản và chia sẻ.

## Phương án đã cân nhắc
| Phương án | Vì sao chưa chọn |
|---|---|
| Quyền theo từng người (tài khoản đăng nhập một lần cho Samba) | Samba không đọc tài khoản của Authelia; phải đồng bộ mật khẩu hai nơi. Để sau, khi cần phân quyền trong cùng phòng |
| Thư mục phòng nằm trong kho tệp web `/files/` | Không gắn được như ổ đĩa; người dùng quen thư mục mạng |
| Máy gửi mã bí mật một lần do Box in ra (thay cho so mã) | Vẫn phải chép tay sang máy trạm, chính là bước muốn bỏ |
| Tin CA tải qua HTTP mà không so mã | Máy giả làm Box trong LAN chiếm được máy mới |
| Tạo phòng ban trên web | Không có trong yêu cầu ("tạo phòng ban thủ công"); tạo trên Box ít bề mặt tấn công hơn |

## Rủi ro còn lại (chấp nhận, đã ghi)
- **Người duyệt không so mã** mà chép mã từ chính màn hình mình: web, dòng lệnh và máy trạm đều bắt gõ lại mã, nhưng không ép được người thật nhìn sang máy kia.
- **Chiếm được Node-RED** (uid 1000) thì tự ghi được quyết định duyệt: root kiểm lại mọi trường, cảnh báo mỗi lần cấp, giới hạn 10 máy/24 giờ.
  Hướng tốt hơn về sau: ghi quyết định qua API CSDL (RLS, người duyệt lấy theo JWT) để root đọc từ CSDL.
- **Mất máy của phòng**: máy cũ biết mật khẩu Samba của phòng → `thu-hoi-may` nhắc chạy `doi-mat-khau-phong <mã>`, lệnh này đẩy mật
  khẩu mới xuống các máy còn lại.
- **Mọi tài khoản trên cùng một máy** dùng được thư mục phòng (máy là đơn vị phân quyền, không phải người).
- **Ngập yêu cầu qua cổng 80**: tối đa 20 yêu cầu đang chờ, mỗi yêu cầu ≤ 8 KB, thân ≤ 64 KB ở Caddy, yêu cầu bỏ dở hết hạn sau 10 phút, tự xóa sau 24 giờ.
- **Giả yêu cầu duyệt từ trang khác (CSRF)**: điểm duyệt chỉ nhận JSON có `Origin` đúng tên Box hoặc `Sec-Fetch-Site: same-origin`.
- **Sao lưu vào ổ Box** (mặc định từ 19/11/2026): hỏng ổ Box là mất cả bản chụp các phòng; cần ổ ngoài nếu muốn chống hỏng ổ.
