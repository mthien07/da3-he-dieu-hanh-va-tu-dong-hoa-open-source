---
phase: 1
title: "Giai đoạn 1: Lược đồ kho + kế toán, RPC nhập kho, trigger duyệt đơn"
status: todo
dependencies: []
---

# Giai đoạn 1: Lược đồ kho + kế toán

## Việc làm

1. `box/ansible/roles/box-du-lieu/files/luoc-do/006-kho-va-ke-toan.sql`:
   - `onebee.mat_hang` (mã, tên, đơn vị, giá vốn bình quân, giá bán, tồn tối thiểu, còn dùng).
   - `ALTER TABLE onebee.don_hang ADD COLUMN mat_hang_id bigint REFERENCES onebee.mat_hang(id)` (đơn cũ để trống, khớp theo tên).
   - `onebee.phieu_kho` (NHAP/XUAT, số phiếu tự sinh `PN-`/`PX-`, ngày, diễn giải, `don_hang_id` duy nhất cho phiếu xuất) và `onebee.phieu_kho_dong`.
   - Trigger `kiem_ton_kho` chặn xuất quá tồn: khoá dòng `mat_hang` (`FOR UPDATE`), so tồn thực, báo lỗi tiếng Việt nêu tên hàng, tồn còn, số cần.
   - `onebee.tai_khoan` + nạp sẵn 111, 112, 131, 156, 331, 411, 511, 632, 642.
   - `onebee.but_toan`, `onebee.but_toan_dong` (mỗi dòng đúng một bên Nợ hoặc Có).
   - Hàm nội bộ `onebee_noi_bo.ghi_but_toan(ngày, diễn giải, chứng từ, mảng dòng jsonb)` — kiểm cân Nợ = Có, chặn gọi từ ngoài (`REVOKE … FROM PUBLIC`).
   - Hàm `onebee.them_nhap_kho(ngày, diễn giải, mảng dòng jsonb)` cho thủ kho: một giao dịch, cập nhật giá vốn bình quân gia quyền, sinh bút toán Nợ 156 / Có 111.
   - Trigger `don_hang_hoan_tat` (AFTER UPDATE, DA_DUYET): tìm mặt hàng, sinh phiếu xuất + bút toán doanh thu (Nợ 131 / Có 511) và giá vốn (Nợ 632 / Có 156) cùng giao dịch; mặt hàng chưa có trong danh mục → chặn duyệt với lời báo `mat_hang_chua_co`.
   - Khung nhìn: `onebee.ton_kho`, `onebee.so_kho`, `onebee.so_nhat_ky`, `onebee.bang_can_doi`.
   - Bật + ép RLS cho mọi bảng mới.
2. `007-phan-quyen-kho-ke-toan.sql`: vai trò `thu_kho`, `ke_toan` (tạo có điều kiện như 002, vai trò là của cụm nên không nằm trong kết xuất), thừa hưởng `nhan_vien`, cấp quyền bảng/khung nhìn/hàm theo bảng quyết định trong plan.

## Kiểm chứng

- `psql` trên Box: áp `006`, `007` không lỗi; `\d onebee.phieu_kho` đúng.
- Thử tay: nhập 100 kg, duyệt đơn 30 kg → tồn 70, 2 bút toán cân; đơn 500 kg bị chặn.
- `onebee-luoc-do.sh` chạy lại không áp tệp nào (ghi sổ đúng).

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Sửa tệp lược đồ đã áp dụng | Chỉ tạo tệp mới; 006/007 chưa từng áp nên còn sửa được trước khi chạy trên Box |
| Trigger duyệt làm hỏng luồng duyệt cũ | Bài kiểm cũ được cập nhật ở giai đoạn 4 (tạo mặt hàng + tồn trước khi duyệt) |
