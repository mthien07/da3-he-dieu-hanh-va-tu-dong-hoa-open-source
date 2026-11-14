---
phase: 4
title: "Giai đoạn 4: Định danh SSO và cổng API"
status: todo
priority: P1
effort: "3d"
dependencies: [2]
---

# Giai đoạn 4: Định danh SSO và cổng API

Nhánh: `feat/box-dang-nhap-mot-lan-va-cong-api`. Chạy song song với giai đoạn 3. Công nghệ theo ADR 0006.

## Mục tiêu
Một tài khoản cho mọi dịch vụ của Box, có xác thực hai lớp; mọi lời gọi API đi qua một cửa có kiểm tra danh tính.

## Điều cần biết
- Hiện mỗi dịch vụ tự giữ mật khẩu: giám sát, biểu mẫu (tài khoản chung `nhanvien`, `kythuat`), Samba (Open WebUI sẽ bị gỡ hoàn toàn ở giai đoạn 8).
- Caddy đã là dịch vụ duy nhất công bố cổng khi bật HTTPS (`Caddyfile.j2`), có CA nội bộ ràng buộc tên (ADR 0005). SSO cần HTTPS: giai đoạn này đặt `onebee_box_https: true` làm mặc định cho bản dự thi.
- Lệnh `hoi` trên máy trạm đang dùng khóa API của Open WebUI; việc chuyển `hoi` sang cổng `/ai/` dùng khóa/token mới sẽ làm ở giai đoạn 8.

## Nhiệm vụ

### Nhiệm vụ 4.1 — Dịch vụ định danh
- Các bước: thêm dịch vụ theo ADR; người dùng và nhóm (`nhan_vien`, `ky_thuat`, `quan_ly`) khai trong tệp do bộ cài quản lý; lệnh `onebee-box them-nguoi <tên> <nhóm>` in mật khẩu tạm một lần; bật TOTP cho nhóm `ky_thuat`, `quan_ly`.
- Kiểm chứng: test đơn vị cấu hình (không mật khẩu dạng rõ trong mẫu; khóa ký sinh vào thư mục bí mật); bài kiểm Box: đăng nhập sai bị từ chối, đúng nhận phiên.

### Nhiệm vụ 4.2 — Cổng API trên Caddy (Zero-Trust)
- Các bước:
  - Tuyến `/api/` chuyển tới PostgREST sau khi xác thực chuyển tiếp (`forward_auth`); chuyển danh tính thành JWT có chữ ký thực mà PostgREST kiểm; giới hạn kích thước thân yêu cầu; nhật ký truy cập có mã người dùng, không có nội dung.
  - Chuẩn bị sẵn tuyến `/files/` (cho giai đoạn 7) và `/ai/` (chuyển tiếp tới Ollama/dịch vụ RAG cho giai đoạn 8) đều đi qua `forward_auth` hoặc bearer token xác thực.
- Kiểm chứng: bài kiểm Box: gọi `/api/don_hang` và `/ai/` không phiên nhận 401; gọi kèm JWT giả mạo chữ ký nhận 401; phiên `nhan_vien` chỉ thấy dòng của mình; phiên `quan_ly` thấy tổng hợp.

### Nhiệm vụ 4.3 — Giám sát và dịch vụ sẵn có sau SSO
- Các bước: trang giám sát (Uptime Kuma) đặt sau `forward_auth` nhóm `ky_thuat`; giữ lối vào trang chủ Box công khai tối thiểu trang chào đăng nhập (không lộ dữ liệu nội bộ).
- Kiểm chứng: bài kiểm Box: mở trang giám sát khi chưa có phiên bị chuyển trang đăng nhập, khi đã có phiên `ky_thuat` vào được không hỏi mật khẩu lần nữa; lần cài hai `changed=0`.

### Nhiệm vụ 4.4 — Tài liệu và xoay khóa
- Các bước: `cai-dat-onebee-box.md`, `quan-ly-may-tram.md` thêm mục tài khoản; `xoay-khoa --box` xoay khóa ký của dịch vụ định danh; `in-khoa` không in mật khẩu người dùng.
- Kiểm chứng: `check-xoay-khoa.sh` bổ sung: sau xoay khóa, phiên cũ bị từ chối.

## Todo
- [ ] 4.1 Dịch vụ định danh
- [ ] 4.2 Cổng API
- [ ] 4.3 Giám sát dùng SSO và chuẩn bị tuyến `/files/`, `/ai/`
- [ ] 4.4 Tài liệu và xoay khóa

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Khóa cả đơn vị ngoài cửa khi dịch vụ định danh hỏng | Không ai đăng nhập được | Lệnh `onebee-box tat-sso-tam` (chỉ root trên Box) đưa các dịch vụ về đăng nhập riêng; có test. |
| Thiết bị ngoài quản lý chưa tin CA | Cảnh báo chứng chỉ | Dùng lại trang hướng dẫn cài CA đã có; ghi vào kịch bản trình diễn. |

## Bảo mật
Đây là giai đoạn nhạy cảm nhất: phải qua `code-reviewer` (hoặc `/ak:code-review`) trước khi gộp. Không ghi mật khẩu, khóa, mã TOTP vào nhật ký hay kho mã.

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
