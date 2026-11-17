---
phase: 3
title: "Chạy CI Box, xử lý C7 đến C11, sửa mô tả PR"
status: pending
priority: P1
effort: "1,5h"
dependencies: [1, 2]
---

# Phase 3: Chạy CI Box, xử lý C7 đến C11, sửa mô tả PR

## Goal
Chứng minh trên CI rằng C1 đến C11 đều đạt trên nhánh PR, sửa các lỗi lộ ra ở C7 đến C11 (vốn chưa chạy lần nào), và sửa mô tả PR #49 (L5).

## Files to Create / Modify
- Modify: chỉ những tệp mà lỗi lộ ra ở C7 đến C11 thật sự cần sửa. Mỗi lỗi một commit, ghi nguyên nhân vào thông điệp commit.
- Modify: mô tả PR #49 (qua `gh pr edit`).

## Tasks & Steps
1. Đẩy commit của Giai đoạn 1 và 2 lên `origin/feat/may-tram-di-cong-tac` (`git push`, không `--force`).
2. Chạy CI có bài Box: `gh workflow run ci.yml --ref feat/may-tram-di-cong-tac -f box=true`. Lấy run ID bằng `gh run list --branch feat/may-tram-di-cong-tac --event workflow_dispatch --limit 1`. Chờ bằng `gh run watch <ID> --exit-status` chạy nền (job Box mất khoảng 40 phút).
3. Trượt thì: `gh run view <ID> --log-failed`, tìm dòng `FAIL` đầu tiên, đọc khối kiểm đó và mã nó gọi, **chứng minh nguyên nhân** trước khi sửa. Sửa nguyên nhân, không nới bài kiểm. Chạy lại từ bước 2. Sau 3 vòng vẫn trượt thì dừng, ghi báo cáo và báo anh.
4. Trong log của lượt đạt, ghi lại cảnh báo conntrack (nếu có) để xác nhận L4 đã hết.
5. Sửa mô tả PR: viết lại thân bài vào một tệp tạm (tên lệnh trong backtick, không có ký tự `\t`), thêm mục "Kết quả CI Box" gồm link run và dòng `C1 đến C11 đạt`, rồi `gh pr edit 49 --body-file <tệp>`. Kiểm bằng `gh pr view 49` rằng không còn ký tự tab.
6. Đánh dấu ba giai đoạn `completed` trong `plan.md`. Ghi báo cáo ngắn vào `plans/reports/` (lỗi đã sửa, link run, những gì vẫn chưa kiểm).

## Verification
- `gh run view <ID> --json jobs --jq '.jobs[] | "\(.name) \(.conclusion)"'`: cả 4 job `success`.
- `gh run view <ID> --log | grep -cE 'PASS  C([1-9]|1[01]):'` cho ra 11 (C3 và C4 in chung một khối, đếm từng dòng PASS), và có dòng `TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT`.
- `gh pr view 49 --json body --jq .body | grep -P '\t'` không in gì.

## Risk & Rollback
- C10 chạy lại toàn bộ bộ cài Box, nên trượt ở đây có thể do task mới không lũy đẳng (`tu-xa-ap-dung`, bộ hẹn giờ, `samba-tu-xa.conf`). Xem dòng `changed:` trong `/root/cai-c10.log` mà bài kiểm in ra.
- Không gộp PR trong giai đoạn này. Gộp là quyết định của anh.
