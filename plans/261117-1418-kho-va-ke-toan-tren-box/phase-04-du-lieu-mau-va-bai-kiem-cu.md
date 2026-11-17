---
phase: 4
title: "Giai đoạn 4: Dữ liệu mẫu và cập nhật bài kiểm cũ"
status: todo
dependencies: [1]
---

# Giai đoạn 4: Dữ liệu mẫu và bài kiểm cũ

## Việc làm

1. `scripts/nap-du-lieu-demo.sql`: thêm mặt hàng mẫu (Mật ong, Gạo, Cà phê…) và phiếu nhập tồn đầu, chạy lại không tạo trùng; số dòng các bảng cũ không đổi (`5,3,1,3,3`).
2. `tests/box/check-so-dieu-hanh.sh`: trước bước duyệt đơn, tạo mặt hàng "Mật ong" và nhập đủ tồn (psql trực tiếp trên Box); thêm ghi chú vì sao.
3. `tests/box/test_onebee_ban_demo.py` nếu số dòng dữ liệu mẫu đổi: cập nhật kỳ vọng tương ứng.

## Kiểm chứng

- `python3 -m unittest` của bộ kiểm tĩnh đạt.
- Bài kiểm Box `check-so-dieu-hanh.sh` đạt trên Box test.
