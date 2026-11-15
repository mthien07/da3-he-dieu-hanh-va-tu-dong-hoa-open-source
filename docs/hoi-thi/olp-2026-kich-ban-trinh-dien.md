# Kịch bản Trình diễn Trực tiếp 10 Phút (Live Demo Script) — OLP 2026

Tài liệu này hướng dẫn đội thi trình diễn trực tiếp **OneBee OS v1.3.0 (DX-OS Open-Core)** trước Hội đồng Giám khảo Khối Phần mềm nguồn mở — OLP 2026 trong thời lượng **10 phút**, chứng minh đầy đủ 4 trụ cột `[H]-[P]-[D]-[I]`, cơ chế chống sai sót **Poka-yoke**, cách ly mã độc **ClamAV**, và tính tự chủ **100% chuẩn OSI**.

---

## Chuẩn bị Trước Giờ Thi (2 phút trước khi lên bục)

1. Mở sẵn 2 cửa sổ trình duyệt (1 cửa sổ thường cho **Nhân viên `nhanvien1`**, 1 cửa sổ ẩn danh cho **Quản lý `quanly1`**) trỏ vào `https://onebee-box.local/so-dieu-hanh/`.
2. Mở sẵn 1 cửa sổ Terminal kết nối SSH vào OneBee Box để chạy lệnh kiểm chứng trực tiếp.
3. Chuẩn bị sẵn chuỗi văn bản kiểm thử **EICAR** để minh họa tải tệp nhiễm mã độc.

---

## Lịch trình 10 Phút Trình diễn

### Phút 00:00 – 01:30 | Mở đầu & Chứng minh 100% Giấy phép Mở Chuẩn OSI (PoF)
- **Thuyết trình**: Giới thiệu bài toán thực tế tại **Hợp tác xã Mật ong OneBee**: thiếu nhân sự IT chuyên trách, mạng chập chờn, cần một nền tảng chuyển đổi số vừa gọn nhẹ trên Mini PC vừa tuân thủ tuyệt đối định nghĩa Nguồn mở (OSI).
- **Thao tác trên Terminal**:
  ```bash
  python3 scripts/chen-giay-phep.py --kiem
  sudo onebee-box chan-doan
  ```
- **Điểm nhấn cho Giám khảo**:
  - 100% tệp mã nguồn đạt kiểm tra `SPDX-License-Identifier: MIT`.
  - Đã loại bỏ hoàn toàn công cụ fair-code cũ (Sustainable Use License) và `giao diện AI bên thứ ba` (giới hạn thương hiệu), thay bằng **Node-RED (`Apache-2.0`)** và **`onebee-ai-rag.py` (`MIT`)**.

### Phút 01:30 – 03:30 | Trụ cột `[H]` (Định danh SSO) & `[P]` (Tạo phiếu Nghiệp vụ)
- **Thao tác trên Trình duyệt 1 (`nhanvien1`)**:
  1. Truy cập `https://onebee-box.local/so-dieu-hanh/`, hệ thống tự động chuyển hướng sang cổng **Authelia SSO** (`/dangnhap/`).
  2. Đăng nhập bằng `nhanvien1` / `OneBee@2026`.
  3. Tại khung **`[H]`**, chỉ rõ định danh phiên hiện tại (`nhanvien1`, vai trò PostgreSQL RLS: `nhan_vien`).
  4. Tại khung **`[P]`**, tạo một phiếu **Đơn hàng (`DON_HANG`)**: *"Xuất 80 chai mật ong hoa nhãn đi TP.HCM — 12.000.000đ"*.
- **Điểm nhấn cho Giám khảo**:
  - Cầu nối `onebee-cau-noi.py` tự động đúc JWT HS256 sống 60 giây đẩy xuống PostgREST + PostgreSQL RLS.

### Phút 03:30 – 06:00 | Cơ chế Chống sai sót Poka-yoke 3 Lớp (Trọng tâm chấm điểm)
- **Bước 1 — Chặn tự duyệt phiếu của chính mình**:
  - Nếu một quản lý tự tạo phiếu, nút **Phê duyệt** trên giao diện sẽ bị khóa (`Poka-yoke: Không tự duyệt phiếu của mình`), đồng thời tầng Node-RED (`/webhook/onebee-phe-duyet`) và ràng buộc `CHECK (nguoi_duyet <> nguoi_tao)` trong PostgreSQL đều chặn cứng.
- **Bước 2 — Bắt buộc nhập lý do khi Từ chối**:
  - Chuyển sang **Trình duyệt 2 (`quanly1` — vai trò `quan_ly`)**.
  - Trong **Hàng đợi Phê duyệt Quản lý**, bấm nút **Từ chối** trên phiếu vừa tạo và để trống (hoặc gõ 1 ký tự) ở hộp thoại lý do -> Hệ thống từ chối ngay với thông báo Poka-yoke yêu cầu lý do tối thiểu 3 ký tự.
- **Bước 3 — Phê duyệt thành công**:
  - Bấm **Phê duyệt** trên phiếu `DH-20261115-001` -> Trạng thái chuyển sang `DA_DUYET` kèm tên người duyệt `quanly1` và dấu thời gian thực.

### Phút 06:00 – 07:45 | Trụ cột `[D]` (Kho Tệp S3 & Cách ly Mã độc ClamAV)
- **Thao tác trên Trình duyệt 1**:
  1. Tải lên một tệp văn bản hợp lệ `bien-ban-giao-nhan.txt` -> Hệ thống báo `CLEAN (ClamAV OK)` và lưu vào kho đối tượng **SeaweedFS**.
  2. Tải lên tệp `hoa-don-gia-mao.com` chứa chuỗi chữ ký kiểm thử **EICAR** (`X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*`).
- **Kết quả trực quan**:
  - Cổng tệp trả về cảnh báo đỏ **`INFECTED`**, cách ly tệp vào `/var/lib/onebee/kho-tep/quarantine`, ngăn không cho lưu vào SeaweedFS và khóa tải xuống trên bảng `[D]`.

### Phút 07:45 – 09:30 | Trụ cột `[I]` (Trợ lý AI RAG, Ẩn danh PII & Văn bản Nghị định 30)
- **Thao tác tại khung `[I]`**:
  1. **Hỏi đáp RAG nội bộ**: Nhập câu hỏi *"Quy trình xử lý khi máy trạm không sao lưu được?"* -> AI trả lời kèm trích dẫn tài liệu nội bộ của HTX.
  2. **Soạn thảo văn bản Nghị định 30/2020/NĐ-CP**: Chọn mẫu **Công văn (`cong-van`)**, nhập trích yếu *"Đề nghị hỗ trợ kiểm định chất lượng lô mật ong vụ thu đông"* -> Hệ thống sinh ngay khung quốc hiệu, tiêu ngữ, số ký hiệu và nội dung đúng chuẩn thể thức hành chính.
  3. **Tóm tắt ẩn danh PII**: Nhập đoạn báo cáo có chứa số điện thoại `0912345678` và email `khachhang@gmail.com` -> Hệ thống tự động che thành `[SDT_AN]` và `[EMAIL_AN]` trước khi gửi vào mô hình ngôn ngữ.

### Phút 09:30 – 10:00 | Kết luận & Khả năng Vận hành Ngoại tuyến Bền vững
- **Thao tác trên Terminal**:
  - Minh họa lệnh cứu hộ ngoại tuyến khi nhân viên quên điện thoại:
    ```bash
    sudo onebee-box ma-xac-minh nhanvien1
    ```
- **Lời kết**: OneBee OS v1.3.0 chứng minh một nền tảng số mở 100% chuẩn OSI vẫn đạt độ hoàn thiện nghiệp vụ cao, an toàn dữ liệu tận gốc (PostgreSQL RLS + ClamAV) và vừa vặn trên một thiết bị Mini PC giá rẻ cho hàng vạn HTX và doanh nghiệp siêu nhỏ Việt Nam.
