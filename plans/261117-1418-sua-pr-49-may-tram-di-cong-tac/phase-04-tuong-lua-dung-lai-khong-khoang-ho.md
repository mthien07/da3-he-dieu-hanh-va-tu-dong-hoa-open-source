---
phase: 4
title: "Tường lửa: dựng lại không có khoảng hở"
status: completed
priority: P1
effort: "1h"
dependencies: []
---

# Phase 4: Tường lửa: dựng lại không có khoảng hở

## Goal
`onebee-tuong-lua bat` thay bộ luật đang chạy mà không lúc nào INPUT, DOCKER-USER hay mangle PREROUTING thiếu bước nhảy tới một chuỗi lọc hoàn chỉnh (sửa L6).

## Files to Create / Modify
- Modify: `box/ansible/roles/box-firewall/files/onebee-tuong-lua`
- Modify: `tests/box/test_onebee_tuong_lua.py`

## Tasks & Steps
1. **Bài kiểm trước:** iptables giả kiểm sau MỖI lệnh rằng từng điểm lọc (INPUT tcp, INPUT udp, DOCKER-USER, mangle PREROUTING) còn bước nhảy tới chuỗi `ONEBEE-*` có dòng cuối DROP/REJECT; thiếu thì ghi `ho.log`. Bài `test_dung_lai_khong_co_khoang_ho` dựng một lần, bật kiểm, rồi thu hồi và duyệt lại máy công tác; đòi không có `ho.log`, kết quả cuối giống lần đầu và không sót chuỗi `-MOI`. Trên mã cũ bài này phải trượt.
2. **Đổi bộ luật kiểu dựng mới rồi gỡ cũ** (`doi_bo`): dựng bộ tạm hậu tố `-MOI` và chèn bước nhảy lên đầu, gỡ bộ chính, dựng lại bộ chính tên cũ, gỡ bộ tạm. Lúc hai bộ cùng có bước nhảy, gói phải được cả hai cho qua, nên trong lúc đổi chỉ có thể chặt hơn, không bao giờ hở. Tên chuỗi cuối cùng giữ nguyên nên bài kiểm tích hợp và lệnh `xem` không phải đổi.
3. Giữ nguyên tắc cũ: filter (cả IPv4 lẫn IPv6) dựng trước mangle, nên mangle lỗi thì LAN vẫn được lọc. `tat` gỡ cả bộ tạm còn sót.

## Verification
- `python3 -m unittest tests.box.test_onebee_tuong_lua` (trong Linux): đạt hết, gồm bài khoảng hở và bài "mangle lỗi vẫn chặn LAN".
- Chạy với iptables thật trong container `--cap-add NET_ADMIN`: dựng, thu hồi, duyệt lại cho ra `iptables-save` giống hệt; không còn chuỗi `-MOI`; `tat` gỡ sạch.
- `shellcheck -e SC2016` sạch.

## Risk & Rollback
- Tên chuỗi tạm dài nhất `ONEBEE-LAN-DOCKER-MOI` (21 ký tự), dưới giới hạn 28 của iptables.
- Hoàn tác: `git revert` commit của giai đoạn này.
