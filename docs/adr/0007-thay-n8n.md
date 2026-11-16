# ADR 0007 — Thay n8n bằng động cơ quy trình Node-RED

- Ngày: 16/11/2026 · Trạng thái: Đã chấp nhận
- Liên quan: [ADR 0006](0006-loi-dx-os-open-core.md) QĐ1 (ghim image), QĐ2 (lõi chỉ trên tên `box.<mã>.onebee.internal`), QĐ6 (chọn Node-RED 5.0.9),
  QĐ7 (thông báo của trang đăng nhập khi chưa có SMTP); [ADR 0005](0005-https-noi-bo-caddy-ca-rang-buoc-ten.md) (Caddy là dịch vụ duy nhất công bố cổng)

## Bối cảnh
n8n dùng Sustainable Use License (fair-code), không phải giấy phép OSI. Lõi DX-OS phải toàn OSI (ADR 0006). QĐ6 đã chọn Node-RED 5.0.9
(Apache-2.0) bằng số đo: RAM rảnh 66,87–71,36 MiB, làm được cả năm việc mẫu.

Kiến trúc nền đã có trước quyết định này:
- Định danh: Authelia sau `forward_auth` của Caddy; Caddy xóa `Remote-*` và `Authorization` do máy khách gửi; cầu nối danh tính ký JWT 60 giây
  cho PostgREST; chỉ Caddy nối tới được cầu nối (mạng `sso`), chỉ cầu nối nối tới được PostgREST (mạng `api`).
- Dữ liệu: lược đồ `onebee` trong PostgreSQL (`box-du-lieu/files/luoc-do/`), RLS trên mọi bảng; bảng `onebee.don_hang` có trạng thái duyệt,
  trigger ghi người duyệt từ JWT và ràng buộc `khong_tu_duyet` (`nguoi_duyet <> nguoi_tao`).
- Sổ CSV cũ (đơn hàng, hỗ trợ, khảo sát) và JSON tình trạng máy được `onebee-box chuyen-du-lieu` chuyển vào CSDL.

## Quyết định
1. Gỡ role `box-n8n`, dịch vụ `n8n`, cổng 5678. Thêm role `box-quy-trinh` (đặt sau `box-du-lieu`), dịch vụ `quy-trinh`
   (`nodered/node-red:5.0.9`, ghim tag + digest, không sửa image, **không có `ports:`**).
2. Hai lớp chặn trình soạn luồng (nơi chạy mã tùy ý):
   - Caddy: tuyến `/quy-trinh/` chỉ có ở chế độ HTTPS, trên tên Box, sau `forward_auth`; luật Authelia chỉ cho nhóm `ky_thuat`, hai lớp.
   - Node-RED: `adminAuth` bật, tài khoản `kythuat`, mật khẩu sinh vào thư mục bí mật (`quy-trinh-soan-luong`), Node-RED chỉ thấy bản băm bcrypt.
   - Trình soạn (`httpAdminRoot: /quy-trinh`) tách khỏi điểm nhận (`httpNodeRoot: /webhook`). Cấu hình (`settings.js`, mã luồng, khóa) gắn chỉ đọc.
3. Điểm nhận và ai gọi được:

   | Điểm nhận (trong Node-RED) | Ai gọi, qua đâu | Xác thực |
   |---|---|---|
   | `/webhook/onebee-tinh-trang` | Máy trạm, qua Caddy: `http://<IP>/` (HTTP) hoặc `https://<IP>/` (HTTPS) | Khóa lọc `X-OneBee-Key` khi `onebee_box_khoa_tinh_trang_chung: true`; chỉ máy có tệp đánh dấu trong `may-da-cap/` (gắn chỉ đọc); chữ ký HMAC do `onebee-may-tram.py` kiểm |
   | `/webhook/onebee-phe-duyet` | Quản lý, qua Caddy `https://box.<mã>.onebee.internal/quy-trinh/webhook/onebee-phe-duyet` | `forward_auth`, luật Authelia: nhóm `quan_ly`, hai lớp |
   | `/webhook/onebee-bao-cao-sao-luu`, `onebee-nhac-han`, `onebee-tong-hop-don-hang`, `onebee-canh-bao` | Chỉ lệnh `onebee-box` trên Box, nối thẳng IP container trong mạng Docker | `X-OneBee-Key` (khóa `quy-trinh-webhook-key`; Node-RED chỉ giữ SHA-256 của khóa) |
   | `/webhook/suc-khoe` | Bộ cài, Uptime Kuma, kiểm thử | Không (chỉ trả `{"ok": true}`) |

4. Phê duyệt đơn hàng: người duyệt lấy từ `Remote-User` do `forward_auth` gắn, không nhận từ thân yêu cầu. Node-RED không giữ khóa ký JWT và
   không nối được tới cầu nối (mạng `default`). Nó ghi trạng thái bằng cách gọi lại Caddy `https://box.<mã>.onebee.internal/api/don_hang`
   kèm **cookie phiên của chính người duyệt** → Authelia kiểm phiên → cầu nối ký JWT của người duyệt → PostgREST → RLS, trigger và ràng buộc
   `khong_tu_duyet` là rào chắn cuối. Node-RED chặn sớm (tự duyệt → 403, từ chối không lý do → 400, đơn đã xử lý → 409) để báo lỗi rõ.
5. Thư SMTP: image Node-RED chính chủ không có nút gửi thư; không cài thêm gói npm lúc cài (Box có thể không có Internet, ADR 0006 nói phải
   đóng gói sẵn `node-red-node-email`). Thay vào đó mô-đun `onebee-quy-trinh.js` của repo (chỉ dùng thư viện chuẩn Node.js `net`, `tls`)
   gửi thư theo RFC 5321/5322: `STARTTLS` hoặc TLS ngay (cổng 465), `AUTH PLAIN`, tiêu đề và thân UTF-8. Cấu hình lấy từ `onebee_box_email`.
6. Tổng hợp đơn hàng đọc từ CSDL: Node-RED không có quyền đọc CSDL. Lệnh `onebee-box tong-hop-don-hang` (lịch systemd 17:00) đọc
   `onebee.don_hang` bằng quyền chủ CSDL trong container PostgreSQL, gửi danh sách đơn trong ngày cho Node-RED soạn thư — như báo cáo sao lưu.
7. Trang đăng nhập (Authelia) khi Box có SMTP: tài khoản tạo bằng `onebee-box them-nguoi` mang địa chỉ thư nội bộ không có thật
   (`<tên>@<mã>.onebee.internal`), nên mặc định vẫn giữ `notifier.filesystem` (QĐ7, mã xác minh đọc bằng `onebee-box ma-xac-nhan`).
   Đặt `onebee_box_email.gui_ma_dang_nhap: true` thì chuyển sang `notifier.smtp` kèm `disable_startup_check: true`: máy chủ thư chưa
   sẵn sàng lúc khởi động không làm Authelia dừng (mất đăng nhập).
8. Gỡ dịch vụ cũ trên Box đang chạy: bộ cài tìm container của dự án `onebee-box` không còn trong `docker-compose.yml`, xóa container,
   đổi tên thư mục dữ liệu `<dịch vụ>` thành `<dịch vụ>.da-thay-<YYYYMMDD>` (giữ để tra cứu, xóa tay khi không cần). Cùng cơ chế sẽ dùng
   khi gỡ dịch vụ khác. Vì địa chỉ báo tình trạng đổi, bộ cài đẩy lại cấu hình xuống mọi máy trạm đã cấp ngay lần đó.

## Bảng chuyển đổi 10 quy trình
| Mã | Quy trình n8n | Việc đang làm | Đầu vào → đầu ra | Đích mới | Test cũ | Test mới |
|---|---|---|---|---|---|---|
| 01 | Báo cáo sao lưu | Gửi thư kết quả sao lưu đêm + tình trạng từng máy trạm | `onebee-box sao-luu` → thư | Node-RED `onebee-bao-cao-sao-luu` | `check-n8n-inside.sh`, `run-box-test-…` (thư "Sao lưu ĐẠT") | `check-quy-trinh-inside.sh`, `run-box-test-…` |
| 02 | Nhắc hạn báo cáo, thuế | Lịch 7:30 + gọi tay; nhắc trước 7, 3, 1, 0 ngày | `onebee_box_lich_han` → thư | Node-RED: lịch 7:30 + `onebee-nhac-han` | `check-n8n-inside.sh` | `check-quy-trinh-inside.sh` |
| 03 | Tóm tắt văn bản PDF | Biểu mẫu tải PDF, AI tóm tắt | PDF → trang kết quả | Trang "Hỏi AI" của ứng dụng Sổ điều hành qua `/ai/` (giai đoạn Trợ lý AI và ứng dụng) | `check-n8n-inside.sh` | Bài kiểm của ứng dụng (`check-so-dieu-hanh.sh`) |
| 04 | Nhập đơn hàng | Biểu mẫu ghi dòng CSV vào thư mục chung | Đơn → CSV | Trang gửi đơn của ứng dụng → `POST /api/don_hang` (`CHO_DUYET`); không ghi CSV nữa | `check-n8n-inside.sh` | `check-du-lieu-qua-cong.sh` (đã có), `check-so-dieu-hanh.sh` |
| 05 | Tổng hợp đơn hàng | 17:00 đọc CSV tháng, thư tổng hợp trong ngày | CSV → thư | `onebee-box tong-hop-don-hang` (lịch 17:00) đọc `onebee.don_hang` → Node-RED `onebee-tong-hop-don-hang` | `check-n8n-inside.sh` | `check-quy-trinh-inside.sh` |
| 06 | Nhận tình trạng máy trạm | Chỉ nhận máy đã cấp, lưu nguyên bao bì có chữ ký | Máy trạm → `tinh-trang-may/<tên>.json` | Node-RED `onebee-tinh-trang` qua Caddy (cổng 80/443) | `test_onebee_n8n_templates.py`, `check-quan-ly-tap-trung.sh` | `test_onebee_quy_trinh.py`, `check-quy-trinh-inside.sh`, `check-quan-ly-tap-trung.sh` |
| 07 | Báo cần hỗ trợ | Biểu mẫu, ghi `yeu-cau.csv`, thư cho kỹ thuật | Yêu cầu → CSV + thư | Trang "Báo cần hỗ trợ" của ứng dụng → `POST /api/yeu_cau_ho_tro` | `check-n8n-inside.sh` | `check-so-dieu-hanh.sh` |
| 08 | Xử lý yêu cầu (kỹ thuật) | Biểu mẫu kỹ thuật, ghi `xu-ly.csv` | Kết quả → CSV | Trang kỹ thuật của ứng dụng → `POST /api/xu_ly_ho_tro` | `check-n8n-inside.sh` | `check-so-dieu-hanh.sh` |
| 09 | Khảo sát hài lòng | Biểu mẫu ẩn danh, ghi `khao-sat.csv` | Điểm → CSV | Trang khảo sát của ứng dụng → `POST /api/khao_sat` | `check-n8n-inside.sh` | `check-so-dieu-hanh.sh` |
| 10 | Cảnh báo sự cố | `onebee-canh-bao` gửi Telegram + n8n (luồng 10 có trong repo nhưng chưa từng được nhập) | Cảnh báo → (không có) | Node-RED `onebee-canh-bao` → thư | `check-alerts.sh` | `check-alerts.sh`, `check-quy-trinh-inside.sh` |
| mới | Phê duyệt đơn hàng | — | Quản lý duyệt/từ chối → `onebee.don_hang` | Node-RED `onebee-phe-duyet` sau `forward_auth` | — | `check-quy-trinh-inside.sh phe-duyet` |

Biểu mẫu 03, 04, 07, 08, 09 không đưa sang Node-RED: dữ liệu ghi vào CSDL qua API, giao diện là các trang của ứng dụng Sổ điều hành.
Từ khi gỡ n8n tới khi có ứng dụng, các tuyến `/api/` vẫn nhận được những dữ liệu này (đã kiểm ở `check-du-lieu-qua-cong.sh`), chưa có trang nhập.
Sổ CSV cũ giữ nguyên chỗ cũ; `onebee-box chuyen-du-lieu` vẫn chuyển được vào CSDL; nhật ký tuần đọc từ CSDL.

## Kiểm kê tệp nhắc n8n (`git grep -il n8n -- . ':!plans'`, 16/11/2026)
- **Xóa:** `box/ansible/roles/box-n8n/` (toàn bộ), `tests/box/check-n8n-inside.sh` (thay bằng `check-quy-trinh-inside.sh`),
  `tests/box/test_onebee_n8n_templates.py` (thay bằng `test_onebee_quy_trinh.py`).
- **Sửa (mã):** `box/ansible/site.yml`, `group_vars/all.yml`, `box-stack/` (`tasks/main.yml`, `tasks/ca.yml`, `docker-compose.yml.j2`, `Caddyfile.j2`,
  `env.j2`, `index.html.j2`, `onebee-box.sh.j2`, `onebee-box-common.sh.j2`, `onebee-box-sao-luu.sh.j2`, `onebee-box-chan-doan.sh.j2`,
  `onebee-canh-bao.sh.j2`), `box-fleet/` (`tasks/main.yml`, `onebee-may-tram.py`, `onebee-bao-cao-tuan.py`), `box-firewall/files/onebee-tuong-lua`,
  `samba/tasks/main.yml`, `box-ai/files/tro-ly-onebee-loi-dan.md`, `desktop/ansible/roles/ket-noi-box/files/onebee-chinh-sach-trinh-duyet.py`,
  `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-ho-tro`, `…/onebee-bao-tinh-trang`, `renovate.json`, `.github/workflows/ci.yml`,
  `.github/ISSUE_TEMPLATE/bao-loi.yml`, `LICENSES.md`, `README.md`, `demo/index.html`.
- **Sửa (bài kiểm, chỉ phần n8n, giữ nguyên ý kiểm):** `tests/README.md`, `tests/box/` `check-alerts.sh`, `check-diagnosis.sh`, `check-https.sh`,
  `check-khoi-phuc-toan-bo.sh`, `check-quan-ly-tap-trung.sh`, `check-sso-cong-api.sh`, `check-xoay-khoa.sh`, `run-box-test-in-systemd-container.sh`,
  `verify-box-install.sh`, `test_onebee_bao_cao_tuan.py`, `test_onebee_box_shell.py`, `test_onebee_caddy_https.py`, `test_onebee_caddy_sso.py`,
  `test_onebee_compose_https.py`, `test_onebee_dinh_danh.py`, `test_onebee_du_lieu.py`, `test_onebee_may_tram.py`, `test_onebee_mdns_dashboard.py`.
- **Sửa (tài liệu):** `docs/huong-dan/*.md`, `docs/hoi-thi/*.md`, `docs/kinh-doanh/*.md`, `docs/kiem-thu-tren-may-that.md`, `docs/security-audit.md`,
  `docs/tong-ket-ra-soat-bao-mat.md`, `docs/project-changelog.md`, `reports/nghiem-thu-v1-docker.md` (tài liệu lịch sử: gọi là "công cụ quy trình cũ").
- **Giữ:** `docs/adr/0002`, `0004`, `0005`, `0006` (quyết định đã ghi, không viết lại lịch sử) và ADR này;
  `box/ansible/roles/box-du-lieu/files/luoc-do/001-khoi-tao.sql` — tệp lược đồ đã áp dụng, bộ cài kiểm SHA-256 và dừng nếu nội dung đổi,
  nên không được sửa kể cả lời chú thích.

## Hệ quả
- Lõi Box không còn thành phần fair-code. Không còn cổng 5678; Node-RED không công bố cổng nào.
- Máy trạm báo tình trạng tới `http(s)://<IP Box>/webhook/onebee-tinh-trang` (dòng `TINH_TRANG_URL` mới). Máy đang tắt khi nâng cấp Box
  báo tình trạng lỗi cho tới khi chạy `sudo onebee-box dong-bo-may <tên>`.
- Mô-đun gửi thư là mã của repo phải tự bảo trì (khoảng 150 dòng, chỉ thư viện chuẩn). Đổi lại không cần gói npm nào lúc cài.
- Ở chế độ HTTP không có trình soạn luồng và không duyệt được đơn (B3: lõi chỉ ở HTTPS). Các việc nền (thư sao lưu, nhắc hạn, tổng hợp đơn,
  tình trạng máy trạm, cảnh báo) chạy ở cả hai chế độ.
- Chỉnh luồng bằng trình soạn rồi bấm Deploy thì có hiệu lực ngay, nhưng lần chạy bộ cài sau ghi đè bằng bản mẫu của repo
  (như n8n trước đây). Muốn giữ luồng riêng: sửa mẫu `box-quy-trinh/templates/flows.json.j2`.
