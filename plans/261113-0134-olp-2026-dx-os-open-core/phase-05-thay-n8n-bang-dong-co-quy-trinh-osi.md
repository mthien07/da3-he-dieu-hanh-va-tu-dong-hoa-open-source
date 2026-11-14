---
phase: 5
title: "Giai đoạn 5: Thay n8n bằng động cơ quy trình giấy phép OSI + luồng phê duyệt"
status: todo
priority: P1
effort: "5d"
dependencies: [3]
---

# Giai đoạn 5: Thay n8n bằng động cơ quy trình giấy phép OSI + luồng phê duyệt

Nhánh: `feat/box-dong-co-quy-trinh-osi`. Giai đoạn nặng nhất: n8n đang được nhắc ở 74 tệp. Công nghệ theo ADR 0006.

## Mục tiêu
Không còn n8n trong bộ cài; mọi việc n8n đang làm vẫn chạy, **và có ít nhất một quy trình phê duyệt (Approval / BPMN)** phục vụ không gian [P], có test.

## Điều cần biết
- Có 12 tệp trong `box/ansible/roles/box-n8n/templates/workflows/` (10 quy trình và 2 mẫu dùng chung). Quy trình số 10 chưa từng được nhập lên Box.
- n8n đang làm 4 loại việc: (a) biểu mẫu web có xác thực (đơn hàng, tóm tắt PDF, báo hỗ trợ, xử lý yêu cầu, khảo sát); (b) nhận webhook từ Box và máy trạm (báo cáo sao lưu, tình trạng máy trạm có chữ ký HMAC, cảnh báo); (c) việc theo lịch (nhắc hạn thuế/BHXH, tổng hợp đơn hàng); (d) gửi thư.
- Hướng chuyển: (a) biểu mẫu thành trang của ứng dụng minh họa ghi thẳng vào API (giai đoạn 6), **không** nằm trong động cơ quy trình; (b), (c), (d) thành quy trình của động cơ mới, định nghĩa bằng tệp trong repo.
- Rất nhiều test Box dò chuỗi của n8n (`check-n8n-inside.sh`, `test_onebee_n8n_templates.py`, `verify-box-install.sh`, `check-https.sh`, `check-xoay-khoa.sh`).

## Nhiệm vụ

### Nhiệm vụ 5.1 — Bảng chuyển đổi từng quy trình
- Các bước: tạo `docs/adr/0007-thay-n8n.md` gồm bảng 10 dòng: quy trình cũ, việc nó làm, đầu vào, đầu ra, nơi mới (quy trình mới, trang ứng dụng, hoặc bỏ), test hiện có, test mới. Liệt kê 74 tệp bằng `git grep -il n8n -- . ':!plans'` và phân loại: sửa, xóa, giữ (nhật ký thay đổi, ADR cũ).
- Kiểm chứng: bảng có đủ 10 quy trình; danh sách tệp có đủ số dòng bằng kết quả lệnh `git grep`.

### Nhiệm vụ 5.2 — Role động cơ quy trình, các việc nền và luồng phê duyệt
- Các bước: role mới thay `box-n8n`; quy trình (b), (c), (d) viết thành tệp định nghĩa trong role; điểm nhận tình trạng máy trạm giữ nguyên kiểm chữ ký HMAC và ghi vào bảng `tinh_trang_may`; gửi thư qua cấu hình SMTP hiện có.
- Bổ sung quy trình phê duyệt trọng tâm cho không gian [P]: khi nhân viên gửi đơn hàng hoặc yêu cầu cần duyệt (`trang_thai_duyet = CHO_DUYET`), động cơ quy trình khởi tạo tiến trình, gửi thông báo tới nhóm `quan_ly`, chờ người quản lý bấm Duyệt hoặc Từ chối (từ chối tự động nếu người duyệt trùng người tạo — Poka-yoke), rồi cập nhật trạng thái (`DA_DUYET` / `TU_CHOI`) vào PostgreSQL và gửi email kết quả cho người tạo.
- Kiểm chứng: test đơn vị cho từng tệp quy trình (cú pháp, không có bí mật dạng rõ); bài kiểm Box mới `check-quy-trinh-inside.sh`: hộp thư giả nhận thư báo cáo sao lưu, thư nhắc hạn và thư thông báo phê duyệt; báo cáo máy trạm sai chữ ký bị từ chối; người tạo tự duyệt đơn của mình bị từ chối (403/400).

### Nhiệm vụ 5.3 — Máy trạm gửi về địa chỉ mới
- Các bước: `onebee-bao-tinh-trang` và `onebee-canh-bao` dùng địa chỉ mới; `them-may`/`dong-bo-may` in dòng cấu hình mới; máy trạm bản cũ nhận cấu hình mới qua `dong-bo-may`.
- Kiểm chứng: `check-quan-ly-tap-trung.sh` đạt với địa chỉ mới; test máy trạm liên quan đạt.

### Nhiệm vụ 5.4 — Gỡ n8n
- Các bước: xóa role `box-n8n`, dịch vụ trong compose, cổng 5678, biến liên quan; bộ cài gỡ container và giữ thư mục dữ liệu cũ dưới tên `n8n.da-thay-<ngày>`; cập nhật `LICENSES.md`, README, hướng dẫn, trang chủ Box, `onebee-box` (`in-khoa`, `xoay-khoa`, `chan-doan`), tường lửa.
- Kiểm chứng (đủ 3): `git grep -il n8n -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr'` không in gì; CI của PR xanh; lần chạy `box=true` xanh với lần cài hai `changed=0`.

## Todo
- [ ] 5.1 Bảng chuyển đổi
- [ ] 5.2 Role động cơ quy trình
- [ ] 5.3 Máy trạm dùng địa chỉ mới
- [ ] 5.4 Gỡ n8n

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Không kịp chuyển hết trước 27/11 | Đến 25/11 chưa xong 5.2 | Báo anh Thiện chọn: lùi ngày đóng băng, hoặc giữ n8n như thành phần tùy chọn tắt mặc định và ghi rõ trong hồ sơ. Không tự quyết. |
| Box đã cài nâng cấp lên mất lịch sử yêu cầu hỗ trợ | Sổ hỗ trợ trống sau nâng cấp | Dữ liệu đã vào CSDL ở giai đoạn 3 trước khi gỡ; thư mục n8n cũ được giữ. |
| Tóm tắt PDF phụ thuộc bước tách chữ của n8n | Không còn tách được PDF | Dùng `pdftotext` (poppler, GPL-2.0) trong một bước của quy trình hoặc của ứng dụng; ghi vào bảng 5.1. |

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
