---
phase: 5
title: "Giai đoạn 5: Kiểm thử tự động và chạy trên Box test"
status: todo
dependencies: [1, 2, 3, 4]
---

# Giai đoạn 5: Kiểm thử

## Việc làm

1. `tests/box/check-kho-ke-toan.sh` — bài kiểm Box đầu-cuối:
   - Tạo người `kkt-thu-kho` (thu_kho), `kkt-ke-toan` (ke_toan), `kkt-ql` (quan_ly), `kkt-nv` (nhan_vien).
   - Thủ kho tạo mặt hàng, nhập 100 kg giá 70.000 → tồn 100, bút toán Nợ 156 / Có 111 = 7.000.000.
   - Nhân viên gửi đơn 30 kg × 100.000, quản lý duyệt → phiếu xuất 30 kg, tồn 70, bút toán doanh thu và giá vốn cân.
   - Đơn 500 kg bị chặn khi duyệt, thông báo nêu tồn còn; đơn vẫn `CHO_DUYET`.
   - Số lượng âm / xuất quá tồn bị CSDL từ chối.
   - `kkt-nv` đọc sổ kế toán → 403; `kkt-ke-toan` đọc được nhưng duyệt đơn → 403; `kkt-thu-kho` không đọc được sổ kế toán.
   - Dọn người dùng và dữ liệu thử khi thoát.
2. `tests/box/test_onebee_kho_ke_toan.py` — kiểm tĩnh: tên tệp lược đồ, không bí mật trong tệp, mẫu trang có khu mới, nút CSV, lệnh gọi RPC đúng.
3. Chạy bộ cài lên Box test (192.168.100.127) và chạy cả hai bài kiểm; chạy lại bộ cài kiểm `changed=0 failed=0`.

## Kiểm chứng

- Hai bài kiểm Box đạt; bộ kiểm tĩnh đạt; CI xanh.
- `sudo onebee-box chan-doan` không thêm mục lỗi mới.
