---
phase: 2
title: "Giai đoạn 2: Vai trò thu_kho, ke_toan xuyên suốt"
status: todo
dependencies: [1]
---

# Giai đoạn 2: Vai trò mới

## Việc làm

1. `box/ansible/group_vars/all.yml`: thêm `thu_kho`, `ke_toan` vào danh sách nhóm người dùng (`onebee_box_nhom_nguoi_dung`).
2. `box/ansible/roles/box-dinh-danh/files/onebee-cau-noi-danh-tinh.py`: `VAI_TRO` thứ tự ưu tiên `quan_ly, ke_toan, thu_kho, ky_thuat, nhan_vien`.
3. `box/ansible/roles/box-stack/templates/onebee-box.sh.j2`: dòng trợ giúp `them-nguoi` tự lấy danh sách nhóm từ biến; nhắc hai lớp chỉ khi nhóm khác `nhan_vien` (giữ nguyên).
4. Rà các chỗ liệt kê vai trò cứng (grep `ky_thuat`, `quan_ly` trong `box/`, `tests/`, `docs/`), cập nhật nơi cần.

## Kiểm chứng

- `sudo onebee-box them-nguoi thu-kho-1 thu_kho` tạo được; đăng nhập được; `/api/toi` trả `{"ten":"thu-kho-1","vai_tro":"thu_kho"}`.
- Người `ke_toan` đăng nhập, `/api/toi` trả `ke_toan`.
- `ansible-lint`/`yamllint` sạch; bộ cài chạy lại `changed=0`.
