---
phase: 2
title: "hoi: tách thời gian chờ nối khỏi thời gian chờ trả lời"
status: completed
priority: P2
effort: "1,5h"
dependencies: []
---

# Phase 2: hoi: tách thời gian chờ nối khỏi thời gian chờ trả lời

## Goal
Không tới được Box thì `hoi` báo lỗi trong khoảng 10 giây. Câu trả lời dài của mô hình (tới 300 giây) vẫn nhận đủ.

## Files to Create / Modify
- Modify: `desktop/ansible/roles/ai-cli/files/hoi`
- Modify: `tests/desktop/test_onebee_hoi.py`

## Mã liên quan (đã đọc)
- `mo(req, timeout)` (dòng 39-59) gọi `build_opener(...).open(req, timeout=timeout)`. Thời gian chờ của `urllib` áp cho cả bước nối TCP lẫn từng lần đọc.
- `goi_api(..., timeout=300)` (dòng 115-133). `URLError` và `TimeoutError` đã có thông báo "Không kết nối được OneBee Box…".

## Tasks & Steps
1. **Bài kiểm trước** trong `test_onebee_hoi.py`:
   - `HOI_URL` trỏ tới một địa chỉ mà gói bị nuốt, không có trả lời. Cách chắc chắn trong CI: mở một socket nghe trên 127.0.0.1 với backlog 0 và không `accept`, lấp đầy hàng đợi bằng vài kết nối trước, để kết nối mới treo ở bước bắt tay. Nếu cách này không treo ổn định trên Linux thì dùng biến môi trường thử nghiệm trỏ `HOI_URL` tới `10.255.255.1` và chấp nhận chạy trong container. Đặt biến `ONEBEE_HOI_CHO_NOI=2` để bài kiểm nhanh.
   - Đòi: `hoi xin chào` thoát khác 0, in "Không kết nối được OneBee Box", trong dưới `ONEBEE_HOI_CHO_NOI + 3` giây.
   - Bài thứ hai: máy chủ giả nhận kết nối nhưng trả lời sau 4 giây (lớn hơn `ONEBEE_HOI_CHO_NOI=2`), `hoi` vẫn nhận đủ câu trả lời. Bài này chứng minh thời gian chờ nối không cắt câu trả lời chậm.
   - Chạy trên mã cũ: bài đầu trượt (chờ tới 300 giây; đặt `timeout` của `subprocess` để bài kiểm không treo CI).
2. **Sửa:** trong `mo()`, trước khi mở yêu cầu, nối thử TCP tới máy chủ và cổng của URL bằng `socket.create_connection((host, port), timeout=cho_noi)` rồi đóng ngay. `cho_noi` mặc định 10 giây, đọc từ `ONEBEE_HOI_CHO_NOI` nếu có (chỉ để kiểm). Nối thử trượt (`OSError`, `socket.timeout`) thì thoát với đúng thông báo "Không kết nối được OneBee Box…" đang có. Không đổi `timeout=300` của bước gửi và đọc.
3. Giữ nguyên ghim CA và luật chuyển hướng của `mo()`; nối thử chỉ là TCP, không gửi dữ liệu.

## Verification
- `python3 -m unittest tests.desktop.test_onebee_hoi -v` đạt (trong Linux), gồm hai bài mới.
- `shellcheck` không liên quan (tệp Python). `python3 -m py_compile desktop/ansible/roles/ai-cli/files/hoi`.

## Risk & Rollback
- Nối thử thêm một lần bắt tay TCP mỗi lần hỏi, khoảng vài mili giây trong LAN, chấp nhận được.
- Hoàn tác: `git revert`.
