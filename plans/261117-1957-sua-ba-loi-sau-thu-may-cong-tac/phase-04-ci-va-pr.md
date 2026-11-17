---
phase: 4
title: "CI, nhật ký thay đổi, PR"
status: pending
priority: P1
effort: "1h"
dependencies: [1, 2, 3]
---

# Phase 4: CI, nhật ký thay đổi, PR

## Goal
Gộp ba bản sửa vào `main` sau khi CI `box=true` đạt cả 4 job.

## Files to Create / Modify
- Modify: `CHANGELOG.md` (mục `[Unreleased]`, nhóm "Sửa")
- Modify: `plans/reports/261117-kiem-thu-may-di-cong-tac.md` (đánh dấu ba phát hiện đã sửa, dẫn PR)

## Tasks & Steps
1. Thêm ba dòng "Sửa:" vào `[Unreleased]` của `CHANGELOG.md`, mỗi dòng nói hành vi người dùng thấy (không nói tên hàm).
2. Mở PR từ `fix/ba-loi-sau-thu-may-cong-tac` vào `main`. Mô tả nêu ba lỗi, nguyên nhân đã chứng minh, cách sửa và bằng chứng (số đo trên Box thật cho L1).
3. `gh workflow run ci.yml --ref fix/ba-loi-sau-thu-may-cong-tac -f box=true`; chờ bằng `gh run watch`.
4. Trượt thì đọc `--log-failed`, chứng minh nguyên nhân rồi mới sửa. Trượt do mạng bên ngoài (ví dụ PPA Launchpad) thì chạy lại một lần và ghi vào mô tả PR.
5. Đạt cả 4 job thì báo anh Thiện; gộp khi anh đồng ý, theo kiểu commit gộp `Gộp #<số>: …`.

## Verification
- `gh run view <ID> --json jobs` cho 4 job `success`.
- `gh pr view <số> --json state` là `MERGED` sau khi gộp.

## Risk & Rollback
- Hoàn tác sau gộp: `git revert -m 1 <commit gộp>`.
