---
phase: 7
title: "Giai đoạn 7: Kho tệp đối tượng có API và kiểm dịch mã độc"
status: todo
priority: P1
effort: "2.5d"
dependencies: [2, 4]
---

# Giai đoạn 7: Kho tệp đối tượng có API và kiểm dịch mã độc

Nhánh: `feat/box-kho-tep-va-kiem-dich`. Bắt đầu sau khi ADR 0006 đã gộp; công nghệ theo ADR.

## Mục tiêu
Cung cấp dịch vụ lưu trữ dữ liệu phi cấu trúc chạy ngầm có API (theo yêu cầu bắt buộc mục 3 Đề thi) gắn với trạm kiểm dịch mã độc tại biên mạng (theo nguyên lý iv mục 4 Đề thi), nối với sao lưu và khôi phục của Box.

## Điều cần biết
- Hiện Box mới có Samba chia sẻ thư mục mạng LAN cho người dùng đầu cuối, chưa có kho đối tượng/tệp có API cho ứng dụng tầng trên gọi vào.
- Bảng `tep_dinh_kem` đã được tạo từ giai đoạn 3 để ghi metadata (`ten_tep`, `loai_mime`, `kich_thuoc`, `khoa_luu_tru`, `trang_thai_quet`: `PENDING_SCAN`, `CLEAN`, `INFECTED`, `nguoi_tai_len`, `doi_tuong_gan`).
- Tuyến `/files/` trên Caddy đã đặt sau `forward_auth` ở giai đoạn 4.

## Nhiệm vụ

### Nhiệm vụ 7.1 — Role `box-kho-tep`: Kho đối tượng (SeaweedFS) và kiểm dịch (ClamAV)
- Các bước: thêm dịch vụ theo ADR 0006 vào `docker-compose.yml.j2` (image ghim tag + digest trong `group_vars/all.yml`, `no-new-privileges`, không công bố cổng ra LAN); cấu hình ClamAV (`clamd` hoặc cơ chế quét theo cấu hình tiết kiệm RAM đã chốt ở ADR 0006) nhận luồng tệp tải lên tại cửa ngõ trước khi xác nhận `CLEAN`.
- Kiểm chứng: test đơn vị đọc compose và cấu hình (không công bố cổng kho đối tượng ra ngoài, có giới hạn kích thước tệp, có biến cấu hình định danh); `tests/kiem-tra-mau-jinja.py` 0 lỗi.

### Nhiệm vụ 7.2 — Điểm cuối API `/files/` qua cổng Caddy
- Các bước: hoàn thiện luồng tải lên / tải xuống qua `/files/`: kiểm tra phiên SSO + vai trò -> nhận tệp -> quét ClamAV (hoặc đặt `PENDING_SCAN` rồi chuyển `CLEAN`/`INFECTED`) -> ghi vào SeaweedFS -> ghi metadata vào `tep_dinh_kem` qua PostgreSQL/PostgREST. Tệp `INFECTED` bị chặn tải xuống (403/423) và cách ly.
- Kiểm chứng: bài kiểm Box:
  1. Gọi `/files/` không phiên nhận 401.
  2. Tải lên tệp PDF sạch -> nhận 201 và bản ghi `tep_dinh_kem` có `trang_thai_quet = 'CLEAN'`, tải lại được đúng nội dung SHA-256.
  3. Tải lên tệp chứa chuỗi thử chuẩn `EICAR` -> bị từ chối hoặc gắn `INFECTED` và không tải xuống được.

### Nhiệm vụ 7.3 — Sao lưu, khôi phục và chẩn đoán
- Các bước: cập nhật `onebee-box-sao-luu.sh.j2` (`cmd_sao_luu`), `khoi-phuc-toan-bo`, và `onebee-box chan-doan` để bao gồm dữ liệu kho tệp và trạng thái dịch vụ kiểm dịch.
- Kiểm chứng: `check-khoi-phuc-toan-bo.sh` bổ sung bước tải lên 1 tệp qua `/files/` trước khi hỏng ổ, sau khôi phục tải lại được đúng tệp đó; lần cài hai `changed=0`.

## Todo
- [ ] 7.1 Role `box-kho-tep` (SeaweedFS + ClamAV)
- [ ] 7.2 Điểm cuối `/files/` qua cổng Caddy và kiểm dịch
- [ ] 7.3 Sao lưu, khôi phục và chẩn đoán

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| ClamAV làm tràn RAM trên máy 8 GB | OOM khi chạy cùng Ollama | Giảm tải bằng `clamscan` chạy từng lượt với cấu hình tối thiểu hoặc chạy theo lịch / bật cờ cấu hình theo kết quả đo ADR 0006. |
| Cập nhật chữ ký virus không có mạng ở môi trường kín | `freshclam` lỗi khi test offline | Cho phép dùng bộ chữ ký nạp sẵn khi đóng gói hoặc bỏ qua lỗi mạng nhưng giữ nguyên kiểm tra EICAR nội bộ. |

## Bảo mật
Không công bố cổng S3/Filer/ClamAV ra LAN. Chỉ chấp nhận tệp nằm trong danh sách đuôi/MIME cho phép (`.pdf`, `.png`, `.jpg`, `.txt`, `.docx`, `.xlsx`, `.odt`, `.ods`) và giới hạn dung lượng (mặc định 10 MB).

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.

