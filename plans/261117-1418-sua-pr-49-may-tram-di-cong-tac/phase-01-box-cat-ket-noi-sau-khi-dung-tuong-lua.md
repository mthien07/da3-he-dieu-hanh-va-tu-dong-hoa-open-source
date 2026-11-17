---
phase: 1
title: "Box: cắt kết nối sau khi dựng lại tường lửa khi hết hạn"
status: completed
priority: P1
effort: "1h"
dependencies: []
---

# Phase 1: Box: cắt kết nối sau khi dựng lại tường lửa khi hết hạn

## Goal
Lượt duyệt hết hạn phải cắt được kết nối đang mở, giống như thu hồi tay (sửa L2), và cảnh báo conntrack chỉ hiện khi thật sự có lỗi (L4).

## Files to Create / Modify
- Modify: `box/ansible/roles/box-stack/templates/onebee-box-tu-xa.sh.j2`
- Modify: `tests/box/test_onebee_tu_xa.py`

## Tasks & Steps
1. **Viết bài kiểm trước (phải trượt trên mã hiện tại).** Trong `test_onebee_tu_xa.py`, sửa hai lệnh giả `conntrack` và `onebee-tuong-lua` để mỗi lần gọi ghi thêm một dòng vào cùng một tệp `${SIM}/thu-tu.log` (`conntrack <tham số>`, `tuong-lua <tham số>`). Thêm hàm `thu_tu()` đọc tệp đó. Trong `test_het_han_tu_thu_hoi` và `test_thu_hoi`, khẳng định dòng `tuong-lua bat` đứng **trước** dòng `conntrack -D -s 100.64.0.7`. Chạy: `test_het_han_tu_thu_hoi` phải trượt, `test_thu_hoi` phải đạt.
2. **Sửa `tu_xa_ap_dung`.** Trong vòng lặp, khi lượt hết hạn: xoá tệp, ghi log, `echo`, đặt `doi=1`, và **thêm IP vào một mảng** `ip_cat` thay vì gọi `conntrack -D` ngay. Sau khối `if [[ ${doi} -eq 1 ]]` (sau `onebee-tuong-lua bat` và `smbcontrol`), lặp `ip_cat` và gọi hàm cắt kết nối ở bước 3. Kết quả là chỉ cắt kết nối khi luật mới đã chặn IP đó.
3. **Gom cắt kết nối vào một hàm** `cat_ket_noi_tu_xa <ip>` dùng chung cho `thu_hoi_tu_xa_thuc` và `tu_xa_ap_dung`:
   - Không có lệnh `conntrack` (`command -v conntrack` trượt): `warn` như câu hiện có.
   - Có lệnh: chạy `conntrack -D -s "${ip}"` và bỏ qua mã thoát khi thông báo là `0 flow entries have been deleted`. Chỉ `warn` khi lỗi khác. Cách đọc: giữ stderr vào biến, so khớp chuỗi `flow entries have been deleted`.
   - Sửa lệnh giả `conntrack` trong bài kiểm để mô phỏng được cả trường hợp "0 mục, mã thoát 1" (đặt tệp `${SIM}/conntrack-rong`), rồi thêm một bài kiểm: thu hồi khi conntrack báo 0 mục thì **không** in "Không chạy được conntrack".
4. Sửa dòng chú thích đầu tệp (dòng 8-9) nếu còn nói khác thứ tự mới. Không đổi phần khác của tệp.

## Verification
- `python3 -m unittest tests.box.test_onebee_tu_xa -v`: đạt hết, gồm cả hai bài kiểm thứ tự và bài kiểm "0 mục". Nếu macOS trượt vì `date -d` của BSD thì chạy trong Linux: `docker run --rm -v "$PWD":/src -w /src python:3.12 bash -c 'pip -q install jinja2 pyyaml && python3 -m unittest tests.box.test_onebee_tu_xa -v'`, hoặc dựa vào job "Kiểm tra cú pháp" của CI.
- Ghi vào báo cáo của giai đoạn: chạy bài kiểm thứ tự trên mã **trước** khi sửa thì trượt.
- `python3 -m unittest discover -s tests/box -p 'test_*.py'`: không hỏng bài kiểm nào khác.

## Risk & Rollback
- Rủi ro thấp: chỉ đổi thứ tự lệnh trong một hàm. Hoàn tác bằng `git revert` commit của giai đoạn này.
