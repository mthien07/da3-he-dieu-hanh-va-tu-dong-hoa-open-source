---
phase: 2
title: "Viết lại C6 và mở rộng C7 giữ kết nối thật"
status: completed
priority: P1
effort: "2h"
dependencies: []
---

# Phase 2: Viết lại C6 và mở rộng C7 giữ kết nối thật

## Goal
C6 và C7 phải chứng minh bằng một kết nối **thật sự đang mở** rằng thu hồi tay và hết hạn đều cắt nó trong 5 giây (sửa L1, L3).

## Files to Create / Modify
- Modify: `tests/box/run-box-test-in-systemd-container.sh` (khối C6 dòng 363-390 và khối C7 dòng 392-400, chạy trong container)
- Modify: `tests/README.md` (chỉ khi mô tả C6/C7 trong đó thay đổi)

## Bối cảnh cần biết
- Tường lửa chặn bằng DROP, nên khi kết nối bị cắt, phía máy xa không nhận RST mà chỉ **không có phản hồi**. Tiêu chí "đứt" vì vậy là: lượt trao đổi kế tiếp trên chính kết nối đó không nhận được phản hồi trong 5 giây. Không dựa vào chuyện tiến trình tự thoát.
- Mã C6 hiện tại sai vì `curl --config -` không bao giờ bắt đầu tải (xem L1 trong `plan.md`). Không dùng lại cách đó.
- Các biến có sẵn trong khối: `${TEN_BOX}`, `${CA}`, `${PW_SMB}`, không gian mạng `may-xa` (IP 100.64.0.7), Box ở 100.64.0.1.

## Tasks & Steps
1. **Thêm một công cụ giữ kết nối HTTPS** viết bằng Python, ghi ra `/root/giu-ket-noi-https.py` bằng heredoc ngay trước C6 (trong phần chạy trong container). Hành vi:
   - Tham số: IP, cổng, tên Box, tệp CA, tệp tín hiệu.
   - Mở TCP, bọc TLS bằng `ssl.create_default_context(cafile=CA)` với `server_hostname=TEN_BOX`, gửi `GET / HTTP/1.1` có `Host` và `Connection: keep-alive`, đọc hết phản hồi theo `Content-Length` (hoặc đọc tới khi có `\r\n\r\n` rồi thêm phần thân nếu cần), in `MO` rồi `flush`. Gửi thêm một yêu cầu y hệt trên cùng kết nối, đọc được phản hồi thì in `SONG0` (chứng minh Caddy giữ kết nối, xem Risk). Điều kiện trước khi thu hồi ở C6 và C7 đòi có cả `MO` lẫn `SONG0`.
   - Chờ tới khi tệp tín hiệu xuất hiện (tối đa 60 giây). Sau đó đặt `settimeout(5)`, gửi lại đúng yêu cầu đó, rồi đọc. Có phản hồi thì in `SONG`. Gặp `socket.timeout`, `ConnectionResetError`, `ssl.SSLError` hoặc đọc được rỗng thì in `DUT`. Thoát 0.
2. **Viết lại C6:**
   - Chạy công cụ ở bước 1 trong `may-xa` ở nền, ghi ra `/root/c6-https.out`.
   - Mở phiên Samba thật: `mkfifo /root/c6-smb.in`. Chạy `smbclient //100.64.0.1/chung -U "onebee%${PW_SMB}" -m SMB3 -t 3 < /root/c6-smb.in > /root/c6-smb.out 2>&1` trong `may-xa` ở nền, mở `exec 7>/root/c6-smb.in` để giữ đầu ghi, rồi `echo ls >&7`.
   - **Điều kiện trước khi thu hồi** (chờ tối đa 10 giây): `/root/c6-https.out` có `MO`, và `/root/c6-smb.out` có đúng một dòng `blocks available`. Không đạt thì in `FAIL  C6: chưa giữ được kết nối HTTPS hoặc phiên Samba trước khi thu hồi` và thoát 1.
   - Ghi `t0`, chạy `onebee-box thu-hoi-tu-xa may-thu`, rồi `touch` tệp tín hiệu và `echo ls >&7`.
   - Chờ tối đa 8 giây cho `/root/c6-https.out` có `DUT` hoặc `SONG`. Đạt khi: có `DUT`; `(now - t0) <= 8` (5 giây chờ phản hồi cộng thời gian lệnh thu hồi); và sau 5 giây `/root/c6-smb.out` vẫn chỉ có **một** dòng `blocks available`.
   - Kiểm thêm: `conntrack -L -s 100.64.0.7 2>/dev/null | grep -c ESTABLISHED` bằng 0. Kết nối mới tới 443 hết giờ (giữ đoạn `/dev/tcp` hiện có).
   - **Dọn trong mọi nhánh** (đạt hay trượt): `exec 7>&-`, `kill` các PID nền, `rm -f` fifo, tệp tín hiệu và tệp `.out`. Viết thành một hàm `don_c6` gọi trước mỗi `exit 1` và ở cuối.
   - Câu PASS giữ nghĩa cũ: `PASS  C6: Sau thu-hoi-tu-xa, kết nối HTTPS và phiên Samba đang mở không còn phản hồi trong ${dt}s; kết nối mới hết giờ`.
3. **Mở rộng C7:** sau `duyet-tu-xa ... --ngay 1` và trước khi sửa `HET_HAN`, chạy công cụ ở bước 1 ở nền và chờ `MO`. Sửa `HET_HAN=1000`, chạy `onebee-box tu-xa-ap-dung`, `touch` tệp tín hiệu, chờ kết quả: phải là `DUT`. Giữ nguyên hai kiểm cũ (tệp lượt bị xoá, kết nối mới hết giờ). Thêm câu `FAIL  C7: kết nối đang mở vẫn sống sau khi lượt hết hạn` cho trường hợp `SONG`.
4. `shellcheck tests/box/run-box-test-in-systemd-container.sh` sạch (CI chạy shellcheck trên `tests/box/*.sh`).
5. Nếu `tests/README.md` có mô tả C6/C7 thì sửa cho khớp.

## Verification
- `shellcheck tests/box/run-box-test-in-systemd-container.sh`, `bash -n` cùng tệp.
- Kiểm riêng công cụ Python trên Mac trước khi đưa lên CI, để biết nó phân biệt đúng hai trường hợp:
  - Chạy một máy chủ HTTPS nhỏ cục bộ (`python3 -m http.server` bọc TLS bằng chứng chỉ tự ký) rồi chạy công cụ: thấy `MO` rồi `SONG`.
  - Chạy với một proxy TCP cục bộ chuyển tiếp tới máy chủ đó, nhận được tín hiệu thì ngừng chuyển tiếp nhưng không đóng socket: thấy `DUT` sau khoảng 5 giây.
  - Kiểm xong thì tắt máy chủ và proxy bằng đúng PID của chúng.
- Kiểm thật nằm ở Giai đoạn 3 (CI Box). C7 mới chạy trên mã chưa sửa L2 phải trượt. Muốn xác nhận riêng điều này thì chạy CI một lần trên commit chỉ có Giai đoạn 2, trước khi gộp Giai đoạn 1.

## Risk & Rollback
- Công cụ phụ thuộc Caddy giữ kết nối keep-alive (mặc định có, thời gian chờ nghỉ dài). Nếu lượt yêu cầu đầu bị đóng kết nối thì điều kiện `MO` vẫn đạt nhưng lần hai sẽ ra `DUT` giả. Bước `SONG0` ở bước 1 chặn trường hợp này.
- Hoàn tác: `git revert` commit của giai đoạn này.
