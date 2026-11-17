# Chẩn đoán: tải lên kho tệp treo trên Box thật (17/11/2026)

Kết quả ngắn: **không tái hiện được** ở trạng thái Box hiện tại. Mọi đường tải lên đều trả 201 sau 12 đến 15 giây. Lỗi treo chỉ xảy ra trong khoảng 16:42 đến 16:47, khi Box đang bị cài qua lại giữa hai nhánh mã. Không chứng minh được nguyên nhân, nên không sửa theo phỏng đoán. Thay vào đó, kho tệp nay ghi thời gian từng chặng cho mỗi lượt tải lên, để lần sau có số liệu.

## Hiện tượng (16:42 đến 16:47)

Ba lượt `PUT /files/...` (tệp `.txt`, `Content-Type: text/plain`, sau đăng nhập một lần) không nhận byte nào. Nhật ký `onebee-kho-tep` ghi `BrokenPipeError` ở `do_PUT` (ghi trả lời) lúc 09:42:53, 09:45:53 và 09:46:42 UTC. Mỗi lượt kết thúc đúng bằng giới hạn chờ của máy khách (20, 120, 60 giây): kho tệp xử lý xong, nhưng máy khách đã bỏ đi.

## Số đo lúc 20:00 đến 20:15 (Box: 4 CPU, khoảng 10 GB RAM)

| Phép đo | Kết quả |
|---|---|
| `clamscan` một lượt trong container kho tệp | 13 giây, mã 0 |
| Gọi thẳng kho tệp (bỏ qua Caddy) với `text/plain`+`.txt`, `application/pdf`+`.txt`, `text/plain`+`.pdf` | Cả ba 201, khoảng 15 giây |
| Qua Caddy, có đăng nhập một lần, ba tổ hợp trên | Cả ba 201, khoảng 14 giây |
| Qua Caddy, PDF `application/pdf` | 201 sau 12,3 giây |

## Đã loại

- Thời gian quét quá dài: 13 giây, thấp hơn mọi giới hạn chờ.
- Kiểu nội dung hay đuôi tệp: cả ba tổ hợp đều đạt ở cả hai đường.
- Cấu hình Caddy cho `/files/`: giống hệt nhau giữa nhánh `main` và nhánh sổ kho; container `onebee-portal` lúc treo và lúc đạt là một (khởi động 08:49 UTC).
- Đọc thân yêu cầu: `_doc_than` xử lý đúng cả `Content-Length` lẫn chunked; mọi lời gọi phụ thuộc có giới hạn 15, 60 hoặc 180 giây.

## Còn lại (không dựng lại được)

Thứ duy nhất khác giữa lúc treo và lúc đạt là `onebee-cau-noi` (cầu nối danh tính) và `onebee-authelia`: hai container này được tạo lại lúc 10:03 UTC, sau các lượt treo, bởi lượt cài bản sổ kho và kế toán. Trong khoảng 15:52 đến 16:20, Box được cài qua lại giữa bản sổ kho (có lược đồ 006 đến 008) và bản `main`, có một lượt bị ngắt giữa chừng. Nhật ký của cầu nối cũ mất theo container.

## Đã làm

- Kho tệp ghi một dòng cho mỗi lượt tải lên: `PUT /<tên> nguoi=<…> ma=<…> doc=…s quet=…s luu=…s metadata=…s tong=…s`.
- Máy khách bỏ đi trước khi có trả lời thì ghi một dòng "máy khách đã ngắt trước khi nhận trả lời", không đổ traceback.
- Bài kiểm `test_nhat_ky_tung_chang_va_may_khach_ngat_giua_chung`.

## Dữ liệu thử còn trên Box

Tài khoản `chandoan-kho` và `chandoan-kho2` đã xoá. Còn 7 tệp thử (mã 2 đến 8, mỗi tệp vài chục byte) trong kho tệp, chưa xoá vì kho tệp không có lệnh xoá: phải xoá dòng trong cơ sở dữ liệu và sao lưu trước.
