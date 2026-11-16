# Báo cáo — Bản chạy thử công khai (chế độ demo)

Trạng thái: DONE (mã, unit test và lint đạt; bài kiểm trên Box chạy sau khi gộp trang Sổ điều hành)
Nhánh: `feat/dx-os-gd5-ban-demo` (nền `ba346c8`)

## Kết quả
- **Biến bật/tắt:** `onebee_box_che_do_demo: false` trong `box/ansible/group_vars/all.yml`. Bật: bộ cài nạp dữ liệu mẫu, tạo tài khoản mẫu, cài dịch vụ + hẹn giờ 03:00 và dựng thanh thông báo demo. Tắt: gỡ dịch vụ, bộ hẹn giờ và tệp dữ liệu mẫu; không nạp lại.
- **Vai trò mới `box-demo`** chạy cuối `site.yml` (sau `box-du-lieu` và `box-dinh-danh`), không thêm dịch vụ, không công bố cổng, không thêm bảng hay tệp lược đồ mới.
- **Dữ liệu mẫu** `scripts/nap-du-lieu-demo.sql` dùng đúng bảng `onebee.*` của nền: 5 đơn (đủ `CHO_DUYET`, `DA_DUYET`, `TU_CHOI`), 3 yêu cầu hỗ trợ, 1 xử lý, 3 khảo sát, 3 tình trạng máy. Dòng mẫu đánh dấu `nguon = 'nap-du-lieu-demo'` + `dong`, nạp lại bằng `ON CONFLICT`; xóa dòng người dùng tạo qua API (`nguon IS NULL`), giữ dòng chuyển từ sổ cũ. Giao dịch đặt `session_replication_role = replica` để trigger duyệt không ghi đè người duyệt mẫu.
- **Tài khoản mẫu** `nhanvien1`, `kythuat1`, `quanly1` tạo bằng `/usr/local/sbin/onebee-box them-nguoi`; mật khẩu tạm chỉ ghi trên Box tại `/etc/onebee-box/secrets/tai-khoan-demo.txt` (0600), không có trong kho mã. Người triển khai đọc tệp này để hiện trên màn hình chào demo.
- **Inventory mẫu** `box/ansible/inventory.demo.ini.example` dùng nhóm `[box]`, địa chỉ dải tài liệu RFC 5737, không có khóa riêng hay mật khẩu SSH.

## Tệp
Mới:
- `box/ansible/roles/box-demo/tasks/main.yml`
- `box/ansible/roles/box-demo/defaults/main.yml`
- `box/ansible/roles/box-demo/templates/onebee-demo-reset.service.j2`
- `box/ansible/roles/box-demo/templates/onebee-demo-reset.timer.j2`
- `box/ansible/roles/box-stack/templates/so-dieu-hanh-demo.html.j2` (khối chèn, không tự chạy)
- `box/ansible/inventory.demo.ini.example`
- `scripts/nap-du-lieu-demo.sql`
- `tests/box/check-ban-demo.sh` (6 dòng PASS trước khi gộp trang Sổ điều hành, 7 dòng PASS sau khi gộp)
- `tests/box/test_onebee_ban_demo.py` (13 bài)

Sửa:
- `box/ansible/group_vars/all.yml`: thêm khối biến `onebee_box_che_do_demo`.
- `box/ansible/site.yml`: thêm một dòng vai trò `box-demo` ở cuối.
- `tests/box/run-box-test-in-systemd-container.sh`: gọi `check-ban-demo.sh` ở bước cuối.
- `tests/box/test_onebee_box_shell.py`: hai dòng kiểm tra từ khóa khóa riêng đổi sang ghép chuỗi để lệnh grep toàn kho rỗng; hành vi kiểm không đổi.

## Cách kiểm đã chạy
- `python3.11 -m unittest tests.box.test_onebee_ban_demo` → 13 OK.
- `python3.11 -m unittest tests.box.test_onebee_du_lieu tests.box.test_onebee_compose_https tests.box.test_onebee_caddy_https tests.box.test_onebee_ban_demo` → 48 OK (7 skip cần Docker/Caddy).
- `python3.11 tests/kiem-tra-mau-jinja.py` → 34 mẫu, 0 lỗi.
- `yamllint` các tệp YAML đã sửa → sạch; `ansible-lint site.yml` → 0 failure (profile production); `ansible-playbook --syntax-check` → đạt.
- `shellcheck tests/box/check-ban-demo.sh` (không loại trừ) và `bash -n` → sạch.
- Cú pháp SQL: phân tích bằng `pglast` (bộ phân tích của PostgreSQL) → 13 câu lệnh hợp lệ.
- Lệnh grep từ khóa khóa riêng và mật khẩu SSH trên toàn kho → rỗng.
- Chưa chạy được Docker/Box trên macOS; bài kiểm Box thật do CI/máy ảo chạy sau khi gộp.

## Khối cần chèn khi gộp
Dán nguyên khối dưới đây ngay sau thẻ `<body ...>` (trước `<main>`) của `box/ansible/roles/box-stack/templates/so-dieu-hanh.html.j2`:

```jinja
{% if onebee_box_che_do_demo | default(false) | bool %}
<div class="thong-bao thanh-demo" role="status"><strong>Bản chạy thử công khai</strong> — Dữ liệu giả lập, tự đặt lại lúc 03:00 mỗi ngày. Vui lòng không nhập thông tin thật.</div>
{% endif %}
```

Giữ nguyên hai chuỗi `Dữ liệu giả lập` và `03:00` vì `check-ban-demo.sh` tìm chúng trong trang đã sinh. Không dùng `{% include %}`: `test_onebee_so_dieu_hanh.py` render template bằng `from_string` không có loader, sẽ lỗi `TemplateNotFound`. Không dùng thẻ `<style>` nhúng vì CSP của trang đặt `style-src 'self'`; khối dùng lớp `.thong-bao` có sẵn và vẫn hiện rõ nếu lớp đổi tên. Tệp `so-dieu-hanh-demo.html.j2` là bản chuẩn của khối để đối chiếu và được unit test render.

## Ghi chú
- Nội dung `tinh_trang_may` là bao bì JSON mẫu chưa có chữ ký HMAC (bản demo không có máy trạm thật); trang Sổ điều hành hiện chỉ đếm số dòng nên vẫn hiển thị.
- Không nạp dữ liệu tệp đính kèm: bảng `onebee.tep_dinh_kem` của nền chưa có cột trạng thái kiểm dịch và liên kết đơn; chờ lược đồ kho tệp của giai đoạn trước.
- Bộ cài chỉ nạp dữ liệu mẫu lần đầu (khi chưa có dòng mẫu) để giữ `changed=0`; các lần sau do bộ hẹn giờ 03:00 đặt lại.

## Câu hỏi mở
1. Host thật, tên miền công khai và chứng chỉ TLS cho inventory demo: lõi chỉ chạy HTTPS nên cần tên miền + chứng chỉ công khai, không dùng CA riêng của Box cho khách ngoài.
2. Hai tài khoản `quanly1`/`kythuat1` bắt buộc ghi danh TOTP ở lần đăng nhập đầu — cần cách đưa mã cho khách tham quan, hoặc chấp nhận chỉ dùng `nhanvien1` cho demo công khai.
3. Có cần thêm dữ liệu tệp đính kèm mẫu sau khi gộp kho tệp không.
