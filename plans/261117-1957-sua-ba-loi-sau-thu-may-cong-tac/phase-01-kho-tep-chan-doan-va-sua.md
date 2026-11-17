---
phase: 1
title: "Kho tệp: chẩn đoán trên Box thật rồi sửa"
status: completed
priority: P1
effort: "4h"
dependencies: []
---

# Phase 1: Kho tệp: chẩn đoán trên Box thật rồi sửa

## Goal
Tìm đúng nguyên nhân khiến `PUT /files/...` treo trên Box thật (HTTPS bật), chứng minh bằng số đo, rồi sửa đúng nguyên nhân đó.

## Files to Create / Modify
- Modify (tùy nguyên nhân): `box/ansible/roles/box-kho-tep/files/onebee-kho-tep.py`, `box/ansible/roles/box-kho-tep/tasks/main.yml`, khối `kho-tep` trong `box/ansible/roles/box-stack/templates/docker-compose.yml.j2`, tuyến `/files/` trong `box/ansible/roles/box-stack/templates/Caddyfile.j2`
- Modify: `tests/box/test_onebee_kho_tep.py` (bài kiểm hồi quy)
- Create: `plans/reports/<ngày>-chan-doan-kho-tep-treo.md`

## Mã liên quan (đã đọc)
- `onebee-kho-tep.py` dòng 45-61: `quet_noi_dung` chạy `clamscan --no-summary --database=/var/lib/clamav <tệp>` với `timeout=180`.
- Dòng 34: `KHOA_QUET = threading.Lock()`, chỉ một lượt quét tại một thời điểm.
- Dòng 109: gọi cầu nối danh tính, `timeout=15`. Dòng 150, 156: SeaweedFS, `timeout=60`.
- Dòng 375: `ThreadingHTTPServer`.

## Số đo đã có (17/11/2026, Box thật, bản cài sổ kho và kế toán)
- `clamscan` một lượt trong container `onebee-kho-tep`: 13 giây, mã 0. Box có 4 CPU, khoảng 10 GB RAM; bộ chữ ký 108 MB.
- Đăng nhập một lần rồi `PUT` PDF 15 byte (`application/pdf`) qua LAN: 201 sau 12,3 giây (byte đầu cũng 12,3 giây), tải lại đúng.
- Container `onebee-kho-tep` và `onebee-seaweedfs` chạy liên tục từ 16/11 20:22 UTC, không được tạo lại khi Box đổi HTTP sang HTTPS; `onebee-cau-noi` và `onebee-authelia` được tạo lại lúc 17/11 10:03 UTC (sau các lượt treo).
- Ba lượt treo hồi chiều (tệp `.txt`, `Content-Type: text/plain`): nhật ký kho tệp ghi `BrokenPipeError` ở `do_PUT` dòng 351 lúc 09:42:53, 09:45:53, 09:46:42 UTC. Thời gian từ lúc gửi tới lúc kho tệp xử lý xong bằng đúng giới hạn chờ của client (20, 120, 60 giây). Kho tệp đã chờ một thứ chỉ kết thúc khi kết nối đóng.
- Đã đọc luồng `do_PUT` → `_doc_than` → `luu_va_quet`: đọc thân xử lý cả `Content-Length` lẫn chunked; quét, cầu nối, SeaweedFS đều có giới hạn 15/60/180 giây. Chưa tìm thấy chỗ nào chờ kết nối đóng.
- Giả thuyết còn lại, theo thứ tự thử: (a) cách Caddy chuyển thân yêu cầu khi client gửi `text/plain` (ví dụ bỏ `Content-Length` mà không dùng chunked, nên `_doc_than` đọc 0 byte hoặc một lời gọi `rfile` chờ tới EOF); (b) cầu nối danh tính cũ treo ở một lời gọi không giới hạn thời gian phía nó; (c) khóa quét bị một lượt trước giữ.

## Tasks & Steps
0. **Lượt thử đầu tiên** (cần anh cho phép tạo tài khoản thử): đăng nhập rồi `PUT` cùng một nội dung với ba tổ hợp `text/plain` + `.txt`, `application/pdf` + `.txt`, `text/plain` + `.pdf`, mỗi lượt `-m 45`. Treo ở tổ hợp nào thì đó là đường cần đào. Đồng thời bật `tcpdump -i any -A port 8080` trong không gian mạng của container kho tệp để xem đúng tiêu đề Caddy gửi (`Content-Length`, `Transfer-Encoding`). Cả ba đều đạt thì giả thuyết (b) hoặc (c) mạnh hơn: tái hiện bằng cách tạo lại trạng thái cầu nối cũ trong CI.
1. **Hẹn giờ dùng Box thật** với anh Thiện (DeepSeek đang dùng). Chỉ đo, không cài, cho tới khi biết nguyên nhân.
2. **Đo từng chặng**, ghi lệnh và đầu ra vào báo cáo:
   - `time` một lượt `clamscan` trong container `onebee-kho-tep` trên tệp nhỏ, đo RAM đỉnh (`/usr/bin/time -v` nếu có; không có thì theo dõi `docker stats` trong lúc chạy).
   - Đăng nhập một lần rồi `PUT` một tệp 1 KB qua LAN (`curl --resolve` tới IP LAN, CA của Box), ghi `time_total`; cùng lúc theo dõi `docker logs -f onebee-kho-tep`, `docker top onebee-kho-tep` (có tiến trình `clamscan` nào đang chạy, chạy bao lâu).
   - Kiểm khóa quét có bị một lượt cũ giữ không: `docker top` có `clamscan` treo từ trước không; khởi động lại container rồi thử lại một lượt.
   - Gọi thẳng cầu nối danh tính và SeaweedFS từ trong container kho tệp (cùng URL như mã) để đo thời gian.
   - Xem nhật ký Caddy cho yêu cầu đó (mã trả, thời gian, có ngắt vì `read_timeout` hay `response_header_timeout` không).
   - So với CI: cùng lệnh tải lên trong `tests/box/check-kho-tep-inside.sh` chạy trên CI đạt 201; ghi điểm khác giữa hai môi trường (bản ClamAV, kích thước bộ chữ ký, Box chuyển HTTP sang HTTPS khi container kho tệp không được tạo lại, biến môi trường của container).
3. **Kết luận nguyên nhân** bằng số đo. Chưa chứng minh được thì dừng, ghi rõ các giả thuyết đã loại và hỏi anh Thiện.
4. **Chọn cách sửa theo nguyên nhân.** Nếu là thời gian quét thì hỏi anh Thiện ba hướng trong `plan.md` (Câu hỏi còn mở 1). Nếu là cấu hình cũ (container không được tạo lại khi đổi HTTP sang HTTPS) thì sửa task để tạo lại container khi cấu hình đổi. Nếu là khóa quét bị giữ thì sửa cách giải phóng khóa khi `clamscan` hết giờ hoặc khi client ngắt.
5. **Bài kiểm hồi quy** trong `tests/box/test_onebee_kho_tep.py` tái hiện đúng nguyên nhân (ví dụ `clamscan` giả chạy chậm, cầu nối giả không trả lời, hoặc client ngắt giữa chừng) và đòi hành vi mới. Chạy trên mã cũ phải trượt.
6. Sửa mã, chạy bài kiểm, rồi thử lại trên Box thật theo tiêu chí 1 của `plan.md`.

## Verification
- `python3 -m unittest tests.box.test_onebee_kho_tep -v` (trong Linux) đạt, gồm bài hồi quy mới.
- Trên Box thật: `PUT` PDF 1 MB trả 201 dưới 60 giây; `GET` lại đúng SHA-256; EICAR vẫn bị chặn 422.
- Báo cáo chẩn đoán có số đo từng chặng.

## Risk & Rollback
- Đổi sang `clamd` hay quét nền là đổi kiến trúc (QĐ5): chỉ làm khi anh Thiện chốt.
- Hoàn tác: `git revert`; trên Box chạy lại bộ cài bản trước.
