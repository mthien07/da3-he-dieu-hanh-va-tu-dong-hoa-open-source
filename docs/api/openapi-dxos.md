<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Đặc tả giao diện API & CLI — OneBee DX-OS Open-Core

Tài liệu đặc tả các nhóm giao diện HTTP qua cổng API **Caddy (443)** và các công cụ dòng lệnh tự phát triển trong OneBee DX-OS (bản 1.3.0).
Mọi đường dẫn dưới đây là hành vi thật của mã trong repo tại thời điểm viết; lệnh kiểm tương ứng nằm ở [tests/box/](../../tests/box/).

---

## 1. Quy ước chung trên cổng API (Caddy)

- **Tên nội bộ:** `https://box.<mã-đơn-vị>.onebee.internal/` (chứng chỉ do CA riêng của Box cấp). Tuyến lõi chỉ tồn tại ở chế độ HTTPS trên tên này.
- **Vào bằng IP:** `https://<ip-box>/` chỉ phục vụ trang chủ công khai. Các đường `/so-dieu-hanh*`, `/dangnhap*`, `/api/*`, `/files/*`, `/ai/*` bị chuyển `308` sang tên nội bộ. Ở chế độ HTTP, các tuyến lõi trả `404`.
- **Bỏ danh tính giả:** trước mọi bước xác thực, Caddy xóa `Remote-User`, `Remote-Groups`, `Remote-Email`, `Remote-Name`, `Authorization`, `Proxy-Authorization` do máy khách gửi.
- **Giới hạn thân yêu cầu:** `/api/*` và `/ai/*` 1 MB; `/files/*` 11 MB ở Caddy (dịch vụ tự kiểm 10 MB và trả `413`); kho sao lưu `rest-server` 256 MB.
- **Mã lỗi chung:** `401` khi chưa có phiên, `403` khi sai nhóm, `404` khi đường dẫn không mở, `413` khi quá giới hạn, `503` khi dịch vụ phía sau chưa sẵn sàng.

Chỉ Caddy công bố cổng ra LAN. Không dịch vụ nào khác có `ports:`; mạng Docker tách `sso`, `api`, `csdl`.

---

## 2. Định danh và dữ liệu tác nghiệp

### 2.1. `/dangnhap/*` — Authelia 4.39.28
- Đăng nhập một lần theo ba nhóm: `nhan_vien` (một lớp), `ky_thuat` và `quan_ly` (hai lớp, TOTP).
- Caddy gọi `forward_auth` tới Authelia cho mọi tuyến lõi; Authelia trả danh tính trong `Remote-User`/`Remote-Groups` chỉ khi phiên hợp lệ.

### 2.2. `GET /api/toi` — cầu nối danh tính (MIT)
- Trả danh tính của phiên hiện tại, không gọi phía sau:
  ```json
  { "ten": "nhanvien1", "vai_tro": "nhan_vien" }
  ```
- Phương thức khác trả `405`; người không thuộc nhóm nào trả `403`.

### 2.3. `/api/<tài-nguyên>` — cầu nối danh tính + PostgREST 16.5
Cầu nối ký JWT **HS256** sống 60 giây (`sub` = tên đăng nhập, `role` = vai trò cao nhất), bỏ `Authorization`/`Cookie` của máy khách rồi chuyển tiếp tới PostgREST. PostgreSQL bật và ép **RLS** trên mọi bảng; quyền cuối cùng do chính sách theo `sub` quyết định.

| Đường dẫn | Nội dung |
|---|---|
| `/api/don_hang` | Đơn hàng có duyệt: `NHAP`, `CHO_DUYET`, `DA_DUYET`, `TU_CHOI`; ràng buộc `khong_tu_duyet` chặn tự duyệt |
| `/api/yeu_cau_ho_tro`, `/api/xu_ly_ho_tro` | Yêu cầu và lượt xử lý hỗ trợ kỹ thuật |
| `/api/khao_sat` | Khảo sát ẩn danh sau triển khai |
| `/api/khao_sat_tong_hop` | Khung nhìn tổng hợp phục vụ bảng điều hành |
| `/api/tinh_trang_may` | Tình trạng máy trạm do `onebee-bao-tinh-trang` gửi kèm chữ ký HMAC |
| `/api/tep_dinh_kem` | Siêu dữ liệu tệp: `DANG_QUET`, `CLEAN`, `INFECTED` |
| `/api/tai_lieu_tri_thuc`, `/api/lich_su_hoi_ai` | Tri thức nạp cho Trợ lý AI và lịch sử hỏi đáp |

Áp dụng `GET`, `POST`, `PATCH`, `DELETE` theo quyền của bảng; PostgREST trả mã lỗi chuẩn của nó.

---

## 3. Kho tệp và kiểm dịch (`onebee-kho-tep` + SeaweedFS 4.53 + ClamAV 1.5.4)

Caddy bỏ tiền tố `/files` trước khi chuyển tới dịch vụ. Mọi thao tác đều qua đăng nhập một lần.

| Đường dẫn | Việc |
|---|---|
| `GET /files/danh-sach` | Danh sách tệp người dùng được thấy (nhân viên: tệp của mình; quản lý/kỹ thuật: theo quyền) |
| `GET /files/<ma_tep>` | Tải tệp đã `CLEAN`; tệp `INFECTED` không tải được |
| `PUT /files/<ten_tep>` hoặc `POST /files/<ten_tep>` | Tải lên thân nhị phân. Quá 10 MB trả `413`; đuôi tệp ngoài danh mục cho phép trả `415`; nhiễm mã độc trả `422` và tệp bị cách ly |
| `GET /files/suc-khoe` | Tình trạng dịch vụ và SeaweedFS (chỉ gọi nội bộ) |

Tệp sạch: quét `clamscan` xong mới đẩy vào SeaweedFS, metadata ghi bằng chính JWT của người tải lên. Chữ ký ClamAV cập nhật ngoại tuyến bằng `onebee-box cap-nhat-chu-ky-clamav`.

---

## 4. Trợ lý AI và RAG (`onebee-ai-rag.py`, MIT)

Dịch vụ Python thuần thư viện chuẩn, nhúng câu hỏi bằng Ollama và tra `pgvector`; chỉ mở đúng hai đường ghi dưới `/ai/`.

### 4.1. Qua phiên đăng nhập một lần
- `POST /ai/hoi` — thân `{ "cau_hoi": "..." }`; trả:
  ```json
  {
    "tra_loi": "...",
    "nguon": [{ "nguon": "nghi-dinh-30.md", "tieu_de": "Nghị định 30/2020/NĐ-CP" }]
  }
  ```
  Câu trả lời luôn kèm lời nhắc đối chiếu văn bản gốc.
- `POST /ai/tom-tat` — thân `{ "noi_dung": "..." }`; trả `{ "tom_tat": "..." }`, giữ nguyên số liệu và ngày tháng có trong văn bản.
- Mọi đường khác dưới `/ai/` trả `404`, kể cả khi đã đăng nhập.

### 4.2. Máy trạm dùng khóa riêng (`hoi`)
- Cùng hai đường `POST /ai/hoi`, `POST /ai/tom-tat`, nhưng không có phiên cookie: máy trạm gửi `X-OneBee-Khoa: obk-<48 ký tự hex>`.
- Dịch vụ đối chiếu bản băm trong `/data/khoa-hoi.json`; khóa sai hoặc đã thu hồi trả `401`. Cấp/thu hồi: `onebee-box cap-khoa-hoi <tên>`, `go-khoa-hoi <tên>`.

---

## 5. Quy trình và giám sát

- `/quy-trinh/*` (Node-RED 5.0.9, sau đăng nhập một lần): trình soạn luồng có mật khẩu riêng ở lớp hai (`quy-trinh-soan-luong`).
- `POST /quy-trinh/webhook/onebee-phe-duyet` (sau đăng nhập một lần): điểm duyệt đơn của Sổ điều hành; người duyệt lấy từ `Remote-User`, trạng thái ghi qua PostgREST bằng JWT của chính người duyệt.
- `/webhook/*` (chỉ máy trong Box gọi): báo cáo sao lưu, cảnh báo, tình trạng máy trạm; mỗi tuyến tự kiểm `X-OneBee-Key` đọc được chỉ bởi root.
- `/giam-sat/` (sau đăng nhập một lần, nhóm `ky_thuat`, hai lớp): Uptime Kuma, không đòi đăng nhập lần hai.
- `GET /trang-thai.json`: số liệu công khai của trang chủ (CPU, RAM, ổ trống, dịch vụ lõi, tỷ lệ máy trạm sao lưu đúng hạn), do `onebee-trang-thai-web.timer` ghi mỗi phút, `Cache-Control: no-store`.

---

## 6. Dòng lệnh quản trị

| Lệnh | Việc |
|---|---|
| `sudo onebee-box trang-thai` | Tình trạng dịch vụ Docker, ổ đĩa, hạn chứng chỉ CA |
| `sudo onebee-box chan-doan [--json]` | Tự kiểm các hạng mục sức khỏe và gợi ý khắc phục |
| `sudo onebee-box them-may <ten>` / `thu-hoi-may <ten>` | Cấp hoặc thu hồi tài khoản sao lưu, khóa `hoi`, CA và cấu hình máy trạm |
| `sudo onebee-box them-nguoi <ten> <nhom>` / `xoa-nguoi` / `danh-sach-nguoi` | Quản lý tài khoản Authelia |
| `sudo onebee-box cap-khoa-hoi <ten>` / `go-khoa-hoi <ten>` | Cấp lại hoặc thu hồi khóa Trợ lý AI của một người |
| `sudo onebee-box xoay-khoa [--may <ten> \| --tat-ca] [--box]` | Xoay mật khẩu dịch vụ, khóa CLI và khóa ký phiên/JWT |
| `sudo onebee-box khoi-phuc-toan-bo [--dong-y]` | Khôi phục Box từ bản sao lưu trên ổ ngoài |
| `sudo onebee-box nap-tri-thuc` | Nạp tài liệu tri thức vào `pgvector` |
| `hoi "câu hỏi"` / `hoi --dang-nhap` | Hỏi Trợ lý AI từ terminal máy trạm qua khóa `obk-` |
