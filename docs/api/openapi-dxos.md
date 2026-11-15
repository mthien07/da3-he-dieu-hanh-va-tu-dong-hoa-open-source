# Đặc tả Giao diện Lập trình Ứng dụng Mở (OpenAPI 3.0) — OneBee DX-OS v1.3.0

Toàn bộ dịch vụ trong **OneBee Box v1.3.0** giao tiếp qua chuẩn HTTP/REST JSON mở, đứng sau cổng **Caddy HTTPS + Authelia ForwardAuth SSO**. Tài liệu này mô tả các điểm cuối (endpoints) chính để tích hợp hoặc thay thế từng mô-đun độc lập (Anti-Vendor Lock-in).

---

## 1. Xác thực & Ngữ cảnh Người dùng (`/api/me`)

Khi người dùng đã đăng nhập qua Authelia (`/dangnhap/`), Caddy xác thực phiên qua ForwardAuth và đính kèm các header `Remote-User`, `Remote-Groups`, `Remote-Name`, `Remote-Email` tới dịch vụ **Cầu nối JWT (`onebee-cau-noi.py`)**.

- **`GET /api/me`**
  - **Mô tả**: Trả về định danh hiện tại, vai trò PostgreSQL RLS (`nhan_vien`, `ky_thuat`, `quan_ly`) và thông tin đơn vị.
  - **Phản hồi mẫu (`200 OK`)**:
    ```json
    {
      "user": "quanly1",
      "name": "Bà Nguyễn Thị Quản Lý",
      "email": "quanly1@onebee.local",
      "groups": ["quan_ly"],
      "role": "quan_ly",
      "don_vi": "htx-onebee"
    }
    ```

---

## 2. Dữ liệu Có cấu trúc & RLS (`/api/phieu_nghiep_vu`, `/api/may_tram`)

Cầu nối `onebee-cau-noi.py` tự động ký JWT HS256 có thời hạn **60 giây** chứa `role` và `don_vi`, sau đó chuyển tiếp (reverse-proxy) sang **PostgREST 12.2.12** kết nối trực tiếp **PostgreSQL 16**.

- **`GET /api/phieu_nghiep_vu?order=tao_luc.desc`**
  - **Mô tả**: Truy vấn danh sách phiếu nghiệp vụ (`DON_HANG`, `HO_TRO`, `KHAO_SAT`). Được lọc tự động bởi chính sách Row-Level Security (RLS) của PostgreSQL.
- **`POST /api/phieu_nghiep_vu`**
  - **Mô tả**: Tạo phiếu nghiệp vụ mới (chỉ gán được `trang_thai = 'CHO_DUYET'` và `nguoi_duyet = null`).
  - **Nội dung gửi (`application/json`)**:
    ```json
    {
      "ma_phieu": "DH-20261115-009",
      "loai_phieu": "DON_HANG",
      "tieu_de": "Đơn đặt 50 thùng mật ong hoa cà phê",
      "noi_dung": "Giao tại kho Bảo Lộc trước ngày 20/11",
      "so_tien_vnd": 25000000,
      "muc_do": "cao"
    }
    ```
- **`GET /api/may_tram?order=cap_nhat_luc.desc`**
  - **Mô tả**: Danh sách máy trạm Ubuntu của HTX kèm chỉ số RAM, đĩa, uptime và trạng thái sao lưu Restic gần nhất.

---

## 3. Quy trình Nghiệp vụ & Phê duyệt Poka-yoke (`/webhook/*`)

Do **Node-RED (`box-quy-trinh`)** đảm nhiệm. Các luồng dành cho máy trạm dùng khóa `X-OneBee-Key`; luồng phê duyệt quản lý dùng định danh SSO (`Remote-User`, `Remote-Groups`).

- **`POST /webhook/onebee-phe-duyet`** *(Bảo vệ bởi Authelia ForwardAuth — yêu cầu nhóm `quan_ly`)*
  - **Mô tả**: Phê duyệt (`DA_DUYET`) hoặc từ chối (`TU_CHOI`) một phiếu đang ở trạng thái `CHO_DUYET`.
  - **Ràng buộc Poka-yoke**:
    1. Trả về `403 Forbidden` nếu `Remote-User` trùng với `nguoi_tao` của phiếu (`khong_duoc_tu_duyet_phieu_cua_chinh_minh`).
    2. Trả về `422 Unprocessable Entity` nếu `trang_thai == "TU_CHOI"` nhưng `ly_do_quyet_dinh` dưới 3 ký tự (`tu_choi_phai_co_ly_do_toi_thieu_3_ky_tu`).
  - **Nội dung gửi (`application/json`)**:
    ```json
    {
      "ma_phieu": "DH-20261115-001",
      "trang_thai": "DA_DUYET",
      "ly_do_quyet_dinh": "Đã kiểm tra tồn kho đủ 120 chai."
    }
    ```
- **`POST /webhook/onebee-tinh-trang`** / **`POST /webhook/onebee-su-co`** / **`POST /webhook/onebee-ho-tro`**
  - **Mô tả**: Tiếp nhận báo cáo định kỳ từ máy trạm, báo cáo sự cố và phiếu hỗ trợ, đồng thời ghi vào cả CSV lịch sử (đã khử CSV Injection) và bảng PostgreSQL tương ứng.

---

## 4. Kho Tệp S3 & Quét Mã độc ClamAV (`/files/*`)

Do dịch vụ **`onebee-kho-tep.py`** điều phối cùng **ClamAV** và **SeaweedFS**.

- **`POST /files/upload`**
  - **Mô tả**: Tải tệp đính kèm lên (dạng `multipart/form-data` hoặc JSON base64 `{"ten_tep": "...", "noi_dung_base64": "...", "phieu_id": 1}`).
  - **Quy trình xử lý**:
    1. Ghi vào vùng đệm tạm và chạy `clamscan --no-summary`.
    2. Nếu phát hiện mã độc (hoặc chuỗi kiểm thử EICAR): chuyển tệp vào `/var/lib/onebee/kho-tep/quarantine`, ghi bản ghi `trang_thai_quet = 'INFECTED'` vào bảng `tep_dinh_kem`, và trả về **`422 Unprocessable Entity`**.
    3. Nếu tệp sạch (`CLEAN`): đẩy lên kho đối tượng **SeaweedFS** và trả về **`201 Created`** kèm `ma_tep` và `sha256`.
- **`GET /files/list`**
  - **Mô tả**: Liệt kê danh sách tệp đính kèm và trạng thái quét ClamAV (`CLEAN` / `INFECTED` / `PENDING_SCAN`).
- **`GET /files/download/<ma_tep>`**
  - **Mô tả**: Tải xuống tệp đã qua kiểm dịch (`CLEAN`). Từ chối tải xuống (`403 Forbidden`) nếu tệp ở trạng thái `INFECTED`.

---

## 5. Trợ lý AI Nội bộ, RAG & Văn bản Nghị định 30 (`/ai/*` & `/v1/*`)

Do dịch vụ **`onebee-ai-rag.py` (MIT)** cung cấp, kết nối trực tiếp tới **Ollama** nội bộ và cơ sở dữ liệu tri thức SQLite FTS5.

- **`POST /ai/hoi`**
  - **Mô tả**: Đặt câu hỏi tiếng Việt có tra cứu kho tài liệu nội bộ (RAG) của HTX.
  - **Nội dung gửi**: `{"cau_hoi": "Quy trình bảo quản mật ong xuất khẩu như thế nào?"}`
- **`POST /ai/tom-tat`**
  - **Mô tả**: Tóm tắt văn bản hoặc báo cáo vận hành tuần sau khi đã tự động che ẩn thông tin định danh cá nhân (email, số điện thoại, CCCD — PII Masking).
- **`GET /ai/mau`** & **`POST /ai/mau`**
  - **Mô tả**: Liệt kê và sinh dự thảo văn bản hành chính theo chuẩn thể thức **Nghị định 30/2020/NĐ-CP** (`cong-van`, `thong-bao`, `to-trinh`, `bien-ban`) kết hợp điền thông tin từ AI nội bộ.
- **`POST /v1/chat/completions`** & **`GET /v1/models`**
  - **Mô tả**: Giao diện tương thích chuẩn OpenAI API phục vụ công cụ dòng lệnh `hoi` trên máy trạm OneBee Desktop.
