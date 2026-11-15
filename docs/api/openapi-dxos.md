<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Đặc tả giao diện API & CLI — OneBee DX-OS Open-Core

Tài liệu đặc tả các nhóm giao diện HTTP qua cổng API **Caddy (`443`)** và các công cụ dòng lệnh tự phát triển trong hệ thống OneBee DX-OS (`v1.3.0`).

---

## 1. Quy ước chung trên Cổng API (`Caddy`)

- **Tên miền nội bộ:** `https://box.<ma_don_vi>.onebee.internal/` (LAN/Tailscale) hoặc tên miền thật `https://<onebee_box_domain>/` (chế độ chạy thử công khai).
- **Truy cập bằng IP LAN:** `https://<IP>/` chỉ phục vụ trang giới thiệu tĩnh và `/trang-thai.json`; mọi đường dẫn lõi (`/dangnhap*`, `/api/*`, `/files/*`, `/ai/*`, `/ai-cli/*`) chuyển hướng `308` sang tên miền hợp lệ.
- **Bảo vệ biên mạng (Zero-Trust):** Caddy xóa sạch mọi tiêu đề giả mạo từ máy khách (`Remote-User`, `Remote-Groups`, `Remote-Email`, `Remote-Name`, `X-OneBee-SSO`, `Proxy-Authorization`, và `Authorization` trên các tuyến không phải `/ai-cli/*`) trước khi chuyển tới `Authelia` hoặc backend.
- **Giới hạn kích thước yêu cầu:** `1 MB` cho `/api/*`, `/ai/*`, `/ai-cli/*`; `5 MB` ở chế độ chạy thử công khai; `256 MB` cho `/files/*` (khi triển khai nội bộ) và sao lưu máy trạm `rest-server`.

---

## 2. Nhóm giao diện Định danh & Dữ liệu tác nghiệp

### 2.1. `/dangnhap*` (`Authelia 4.39.28`)
- Đăng nhập một lần (SSO) theo 3 nhóm chuẩn hóa: `nhan_vien` (1 lớp), `ky_thuat` và `quan_ly` (2 lớp TOTP).
- Endpoint kiểm tra phiên nội bộ bởi Caddy: `GET /api/authz/forward-auth` trả `200` kèm `Remote-User`, `Remote-Groups`, `Remote-Email`, `Remote-Name`, hoặc `401` (`Accept: application/json`) / `302` trình duyệt.

### 2.2. `/api/toi` (`onebee-dinh-danh` — Cầu nối danh tính, MIT)
- **Phương thức:** `GET /api/toi` (bắt buộc qua `onebee_sso`).
- **Phản hồi (`200 OK`):**
  ```json
  { "ten": "nhanvien1", "vai_tro": "nhan_vien" }
  ```

### 2.3. `/api/*` (`onebee-dinh-danh` + `PostgREST 16.5`, MIT)
Cầu nối xác thực phiên SSO, cấp JWT ngắn hạn `ES256` (thời hạn `60s` chứa claim `role` = nhóm Authelia, `nguoi_tao` = `Remote-User`), chuyển tiếp tới PostgREST áp đặt **Row-Level Security (RLS)** theo từng dòng:
- `GET / POST / PATCH /api/don_hang`: Quản lý đơn hàng (`NHAP`, `CHO_DUYET`, `DA_DUYET`, `TU_CHOI`).
- `GET / POST / PATCH /api/yeu_cau_ho_tro`: Tiếp nhận & xử lý yêu cầu hỗ trợ kỹ thuật.
- `GET / POST /api/khao_sat`: Khảo sát mức độ hài lòng / phản hồi sau triển khai.
- `GET /api/tinh_trang_may`: Dữ liệu hội tụ từ `onebee-bao-tinh-trang` trên các máy trạm.
- `GET /api/tep_dinh_kem`: Siêu dữ liệu và trạng thái kiểm dịch tệp (`DANG_QUET`, `CLEAN`, `INFECTED`).

---

## 3. Nhóm giao diện Kho tệp & Kiểm dịch mã độc

### `/files/*` (`onebee-kho-tep` + `SeaweedFS 4.53` + `ClamAV 1.5.4`)
Mọi thao tác tải lên đi qua quy trình kiểm dịch đồng bộ trước khi lưu trữ chính thức:
- `POST /files/tai-len` *(SSO)*: Nhận `multipart/form-data`, chạy `clamscan --no-summary` (không dùng `clamd` thường trú để tối ưu RAM).
  - Nếu sạch (`exit 0`): lưu đối tượng vào SeaweedFS, cập nhật trạng thái `CLEAN` trong PostgreSQL, trả `201 Created` kèm `ma_tep`.
  - Nếu phát hiện mã độc (`exit 1`): xóa tệp tạm ngay, ghi trạng thái `INFECTED` vào log kiểm toán, trả `422 Unprocessable Entity`.
- `GET /files/tai-ve/<ma_tep>` *(SSO)*: Kiểm tra quyền sở hữu/phòng ban và trạng thái `CLEAN` trước khi stream từ SeaweedFS.

---

## 4. Nhóm giao diện Trợ lý AI & RAG nội bộ (`onebee-ai-rag.py`, MIT)

Dịch vụ thuần thư viện chuẩn Python 3.14 kết nối Ollama (`0.34.4`, `gemma4:e2b-it-qat`), sử dụng thuật toán tách đoạn theo tiêu đề Markdown + tìm kiếm BM25 kết hợp bigram tiếng Việt không dấu.

### 4.1. Tuyến trình duyệt qua SSO (`/ai/*`)
- `GET /ai` hoặc `GET /ai/`: Giao diện web tĩnh Trợ lý AI (hỗ trợ `?q=` điền sẵn câu gợi ý, zero tài nguyên ngoài).
- `GET /ai/health`: Kiểm tra trạng thái dịch vụ AI và kết nối Ollama (`200 OK` JSON).
- `GET /ai/mau`: Trả về danh sách mẫu soạn thảo hành chính (`prompts/*.json`) và gợi ý nhanh (`goi-y.json`).
- `POST /ai/hoi`:
  - **Đầu vào:** `{ "cau_hoi": "...", "lich_su": [...] }`
  - **Đầu ra:**
    ```json
    {
      "tra_loi": "...",
      "nguon": [{ "tieu_de": "Nghị định 30/2020/NĐ-CP", "doan": "..." }],
      "nhac_kiem_tra": "AI có thể sai sót, vui lòng đối chiếu lại văn bản gốc trước khi ký ban hành."
    }
    ```
- `POST /ai/tom-tat`:
  - Chỉ nhận số liệu tổng hợp điều hành (`so_don_tuan`, `ty_le_duyet`, `ho_tro_dang_mo`, `may_da_sao_luu`).
  - **Chốt chặn chống rò rỉ PII:** Tự động kiểm tra tên riêng, email, số điện thoại Việt Nam, số CCCD 12 chữ số — từ chối `400 Bad Request` nếu phát hiện dữ liệu định danh cá nhân trước khi gọi Ollama.

### 4.2. Tuyến máy trạm CLI (`/ai-cli/hoi`)
- Không qua trang đăng nhập cookie trình duyệt của Authelia; Caddy xóa toàn bộ `Remote-*` & `Cookie`, chỉ giữ `Authorization: Bearer <token>`.
- `onebee-ai-rag.py` đối chiếu băm **SHA-256** trong `/etc/onebee-box/secrets/ai-tokens.json`. Token sai hoặc bị thu hồi trả `401 Unauthorized`.

---

## 5. Nhóm giao diện Điều phối quy trình & Trang chủ trạng thái

- **`/quy-trinh/*` (`Node-RED 5.0.9`, SSO):** Quy trình phê duyệt đơn hàng 2 bước (`CHO_DUYET` -> `DA_DUYET`/`TU_CHOI`), nhắc hạn thuế/BHXH định kỳ và gửi thông báo SMTP qua `node-red-node-email`.
- **`GET /trang-thai.json`:** Số liệu công khai không cần phiên (`Cache-Control: no-store`) do timer `onebee-trang-thai-web` sinh mỗi phút: `%CPU`, `%RAM`, dung lượng ổ trống, trạng thái các dịch vụ lõi và tỷ lệ máy trạm sao lưu đúng hạn.

---

## 6. Giao diện dòng lệnh quản trị (`onebee-box` & `hoi`)

| Lệnh | Mục đích chính |
|---|---|
| `sudo onebee-box trang-thai` | Kiểm tra tình trạng dịch vụ Docker, ổ đĩa, hạn chứng chỉ CA |
| `sudo onebee-box chan-doan [--json]` | Tự kiểm 7 hạng mục sức khỏe hệ thống và gợi ý khắc phục |
| `sudo onebee-box them-may <ten>` | Cấp tài khoản sao lưu `rest-server`, khóa `hoi`, CA và cấu hình cho máy trạm mới |
| `sudo onebee-box them-nguoi <ten> <nhom>` | Tạo tài khoản Authelia theo nhóm `nhan_vien`, `ky_thuat` hoặc `quan_ly` |
| `sudo onebee-box xoay-khoa [--may <ten> \| --tat-ca] [--box]` | Xoay toàn bộ mật khẩu dịch vụ, khóa API CLI và khóa ký phiên |
| `hoi "<câu hỏi>"` / `hoi --dang-nhap` | Hỏi đáp Trợ lý AI trực tiếp từ terminal máy trạm qua `/ai-cli/hoi` (ghim CA Box) |
