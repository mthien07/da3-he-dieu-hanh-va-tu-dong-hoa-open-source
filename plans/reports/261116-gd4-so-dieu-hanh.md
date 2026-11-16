# Báo cáo Giai đoạn 4 — Ứng dụng Sổ điều hành H-P-D-I

## Trạng thái

Xong phần mã và kiểm thử đơn vị trên nhánh `feat/dx-os-gd4-so-dieu-hanh`. Chưa chạy bài kiểm Box thật (`check-so-dieu-hanh.sh`, `run-box-test-in-systemd-container.sh`) vì môi trường tác giả không chạy Docker; cửa cuối còn lại là CI `box=true`/máy ảo. Chưa gộp vào nhánh tích hợp, chưa push.

## Tệp sửa

Mới:
- `box/ansible/roles/box-stack/templates/so-dieu-hanh.html.j2`
- `box/ansible/roles/box-stack/files/so-dieu-hanh.css`
- `box/ansible/roles/box-stack/files/so-dieu-hanh.js`
- `tests/box/test_onebee_so_dieu_hanh.py`
- `tests/box/check-so-dieu-hanh.sh`

Sửa:
- `box/ansible/roles/box-stack/tasks/main.yml` — tạo thư mục `portal/site/so-dieu-hanh` trước khi sinh trang; sinh HTML, chép CSS/JS.
- `box/ansible/roles/box-stack/templates/Caddyfile.j2` — tuyến `/so-dieu-hanh/` sau `forward_auth`, CSP chặt; vào bằng IP chuyển 308 sang tên; HTTP trả 404; SSO tạm tắt trả 503.
- `box/ansible/roles/box-dinh-danh/templates/configuration.yml.j2` — hai luật Authelia cho trang: `ky_thuat` + `quan_ly` hai lớp, `nhan_vien` một lớp.
- `box/ansible/roles/box-stack/templates/index.html.j2` — thẻ Sổ điều hành thay hai thẻ biểu mẫu n8n (đơn hàng, báo hỗ trợ); chế độ HTTP chỉ hiện lời nhắc bật HTTPS.
- `desktop/ansible/roles/quan-ly-tap-trung/tasks/muc-menu.yml` — mục menu "Báo cần hỗ trợ" mở `https://<BOX_TEN>/so-dieu-hanh/` khi `BOX_HTTPS=1`; chế độ HTTP gỡ mục cũ.
- `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-ho-tro` — mở ứng dụng kèm `may`, `loai`, `mo_ta`; trang tự điền sẵn.
- `desktop/ansible/roles/ket-noi-box/files/onebee-chinh-sach-trinh-duyet.py` — dấu trang Firefox/Chrome thay hai biểu mẫu n8n bằng một dấu trang Sổ điều hành.
- `tests/box/check-https.sh` — gọi `check-so-dieu-hanh.sh` trong phần HTTPS; kiểm mục menu máy trạm.
- `tests/box/check-quan-ly-tap-trung.sh` — phần lối vào: chế độ HTTP không còn mục menu trỏ 5678/biểu mẫu cũ.
- `tests/box/verify-box-install.sh` — kiểm ba tệp trang trong portal và `/so-dieu-hanh/` trả 404 ở HTTP.
- `tests/box/run-box-test-in-systemd-container.sh` — ghi nhận bài kiểm ứng dụng chạy trong phần HTTPS của `check-https.sh`.
- `tests/box/test_onebee_mdns_dashboard.py` — kỳ vọng lối vào trang chủ đổi từ biểu mẫu n8n sang ứng dụng.

## Cách kiểm

Đã chạy trên macOS bằng `/tmp/onebee-venv`, không Docker:
- `python -m unittest tests.box.test_onebee_so_dieu_hanh tests.box.test_onebee_mdns_dashboard tests.box.test_onebee_caddy_sso` → 76 test OK, 21 skip vì thiếu Caddy thật.
- `python -m unittest` nhóm định danh, compose HTTPS và ba test desktop liên quan → OK.
- `python tests/kiem-tra-mau-jinja.py` → 32 mẫu, 0 lỗi.
- `node --check box/ansible/roles/box-stack/files/so-dieu-hanh.js` → OK.
- `shellcheck -e SC2016 tests/box/*.sh` → rc 0; `bash -n` các script đã sửa → OK.
- `yamllint .` → rc 0.
- `ansible-lint box/ansible/site.yml desktop/ansible/site.yml` → 0 failure, 0 warning.
- Kích thước trang với tên đơn vị mẫu: HTML 10.355 + CSS 3.407 + JS 26.423 = 40.185 byte (dưới 40 KiB).
- `check-so-dieu-hanh.sh` có 12 dòng PASS, phủ: chưa đăng nhập chuyển trang đăng nhập; gửi đơn kèm PDF 201 + tệp CLEAN + đơn CHO_DUYET; mức độ ngoài danh mục 400; nhân viên B không thấy đơn A; tự duyệt bị từ chối; quản lý duyệt DA_DUYET; nhân viên đọc bảng điều hành 403; quản lý nhận số liệu khớp CSDL; tóm tắt tuần chỉ có số liệu tổng hợp và Trợ lý trả chữ tiếng Việt; trang tĩnh sau đăng nhập có CSP chặt.

Chưa chạy: `tests/box/check-so-dieu-hanh.sh` trên Box Linux, `tests/box/run-box-test-in-systemd-container.sh`, `gh workflow run ci.yml -f box=true`.

## Khối cần chèn khi gộp

Giữ nguyên các khối sau khi giải xung đột với Giai đoạn 1–3:
- `Caddyfile.j2`: khối `@so_dieu_hanh` + `redir` trong site IP; khối `@so_dieu_hanh` + `handle` sau `handle /dangnhap*` trong site tên; khối 503 trong nhánh SSO tạm tắt; matcher + `respond 404` trong site `:80` chế độ HTTP.
- `configuration.yml.j2`: hai luật `^/so-dieu-hanh([/?].*)?$` đặt trước các luật `^/(api|files|ai)/`.
- `box-stack/tasks/main.yml`: mục thư mục `portal/site/so-dieu-hanh` trong vòng lặp tạo thư mục; hai task sinh trang và chép CSS/JS đặt sau task sinh trang chủ.
- `index.html.j2`: thẻ Sổ điều hành trong "Truy cập nhanh"; đã bỏ hai thẻ biểu mẫu n8n (đơn hàng, báo hỗ trợ).
- `muc-menu.yml` + `onebee-bao-ho-tro` + dấu trang Firefox: mục "Báo cần hỗ trợ" chỉ ghi khi `BOX_HTTPS=1` và `BOX_TEN` hợp lệ; chế độ HTTP gỡ mục cũ.
- `check-https.sh`: lời gọi `check-so-dieu-hanh.sh` đặt sau `check-sso-cong-api.sh`, trước `check-du-lieu-qua-cong.sh`; khối kiểm menu máy trạm nằm trong `tram "..."` của phần MÁY TRẠM.
- `verify-box-install.sh`, `run-box-test-in-systemd-container.sh`, `test_onebee_mdns_dashboard.py`: giữ các kỳ vọng mới.

## Câu hỏi mở

1. `tep_dinh_kem` của Giai đoạn 2 hiện chưa có cột `doi_tuong_gan` và chưa cấp UPDATE. Trang đang ghi `doi_tuong_gan` dạng best-effort (lỗi bỏ qua) và ghi tên tệp vào `ghi_chu`; cần Giai đoạn 2 bổ sung cột/quyền hoặc chốt cách ghi chú này.
2. Giao kèo hỏi AI dùng `/ai/hoi` và `/ai/tom-tat` theo mã Giai đoạn 3, thay cho `/ai/api/chat` trong câu chữ đặc tả Giai đoạn 4; đã cập nhật unit test và cấm `/ai/api/chat`.
3. `run-box-test-in-systemd-container.sh` hiện gọi gián tiếp qua `check-https.sh` (đúng lúc HTTPS bật). Nếu muốn lời gọi trực tiếp trong run-box thì phải thêm hook trong `check-https.sh` trước khối tắt HTTPS.
4. `check-so-dieu-hanh.sh` xóa/tạo lại tài khoản `sdlh-nv-a`, `sdlh-nv-b`, `sdlh-ql` mỗi lần chạy; `check-kho-tep-inside.sh` của Giai đoạn 2 dùng `a1`, `b1` nhưng không xóa trước, có thể hỏng khi chạy lại trên cùng Box — cần bên Giai đoạn 2 xử lý.
5. Cần chạy CI `box=true`/máy ảo để xác nhận Caddy thật, Authelia thật, kho tệp + Trợ lý AI và các dòng PASS trên Box Linux.
