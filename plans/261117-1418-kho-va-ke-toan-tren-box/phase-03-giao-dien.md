---
phase: 3
title: "Giai đoạn 3: Giao diện khu Kho và khu Kế toán, xuất CSV"
status: todo
dependencies: [1, 2]
---

# Giai đoạn 3: Giao diện

## Việc làm

1. `box/ansible/roles/box-stack/templates/so-dieu-hanh.html.j2`: thêm hai khu
   - **Kho** (thấy khi vai trò là `thu_kho` hoặc `quan_ly`): bảng tồn kho, form nhập kho (mặt hàng, số lượng, đơn giá, ngày, diễn giải), danh sách phiếu kho gần đây, nút *Xuất CSV*.
   - **Kế toán** (thấy khi vai trò là `ke_toan` hoặc `quan_ly`): sổ nhật ký (lọc ngày), bảng cân đối tài khoản, nút *Xuất CSV*.
   - Biểu mẫu đơn hàng: ô "Mặt hàng" thành danh sách chọn từ `/api/mat_hang`, vẫn gửi kèm `mat_hang` (tên) để tương thích.
2. `files/so-dieu-hanh.js`: hàm tải tồn kho, gửi nhập kho qua `POST /api/rpc/them_nhap_kho`, đọc `so_nhat_ky`/`bang_can_doi`, kiểm dữ liệu phía trình duyệt, xuất CSV (UTF-8 BOM, dấu `;` cho LibreOffice Việt Nam, tên tệp có ngày), thông báo lỗi tiếng Việt cho các mã lỗi mới.
3. `files/so-dieu-hanh.css`: kiểu bảng và khu mới theo phong cách hiện có.

## Kiểm chứng

- Trang tải không tài nguyên ngoài, không `innerHTML` với dữ liệu người dùng; dưới 40 KB mỗi trang (bài kiểm tĩnh hiện có).
- Nhân viên không thấy khu Kho/Kế toán; thủ kho thấy Kho, không thấy Kế toán; kế toán ngược lại; quản lý thấy cả hai.
- Tải CSV mở bằng LibreOffice: tiếng Việt đúng, số dòng khớp dữ liệu đang xem.
