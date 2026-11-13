# Kết quả kiểm trải nghiệm trên máy thật

Mỗi lần kiểm là một file `<năm-tháng-ngày>-<tên máy>.md` (ví dụ `2026-11-20-mint-22-3-vm1.md`), làm từ bản sao của phiếu `docs/kiem-thu-trai-nghiem-may-that.md`.
Không đưa vào đây tên người, email, mật khẩu, địa chỉ nội bộ thật hay nội dung file của đơn vị; ảnh chụp phải che các thông tin đó.
Mục không đạt phải có dòng trong bảng "Mục không đạt và cách xử lý" cuối file; trạng thái `chưa xử lý` chỉ là tạm, phải đổi trước khi phát hành.
Con số đo (nhóm J) chỉ được công bố khi đã có file ở đây.

Mẫu đầu file:

```text
Ngày kiểm: <ngày/tháng/năm>
Máy: <tên máy ảo hoặc máy thật>
Bản Mint: <ví dụ 22.3 Cinnamon>
Commit đã cài: <git rev-parse --short HEAD>
Người kiểm: <chức danh hoặc mã, không ghi họ tên>
Box thử: <ví dụ Ubuntu Server 24.04 VM, hoặc container giữ lại>
```
