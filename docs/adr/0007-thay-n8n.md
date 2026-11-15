# ADR 0007 — Thay thế n8n (Fair-code) bằng động cơ quy trình Node-RED chuẩn OSI (Apache-2.0)

- **Trạng thái:** Đã chấp nhận (15/11/2026)
- **Liên quan:** [ADR 0006 — Chốt lõi DX-OS open-core bằng số đo](0006-loi-dx-os-open-core.md), `plans/261113-0134-olp-2026-dx-os-open-core/phase-05-thay-n8n-bang-dong-co-quy-trinh-osi.md`

## Bối cảnh

Trong OneBee Box v1.0–v1.2, thành phần tự động hóa quy trình sử dụng `n8n` (Sustainable Use License — *fair-code*, không thuộc danh mục giấy phép nguồn mở chuẩn OSI). Theo thể lệ OLP 2026 (tiêu chí *Philosophy of Openness — PoF* và yêu cầu thành phần lõi chuẩn OSI) cũng như định hướng thương mại hóa không ràng buộc giấy phép cho các hợp tác xã, toàn bộ các thành phần trong lõi DX-OS phải mang giấy phép OSI-approved.

Tại [ADR 0006 (QĐ6)](0006-loi-dx-os-open-core.md), nhóm đã đo đạc thực nghiệm ba ứng viên chuẩn OSI trên máy ảo giới hạn tài nguyên (4 vCPU, ngân sách RAM tăng thêm toàn lõi ≤ 1,5 GB):
- **Node-RED 5.0.9** (`Apache-2.0`): RAM rảnh `66,87–71,36 MiB`, khởi động `2,0 giây`, hoàn thành cả 5 bài thử chuẩn (lịch hẹn, webhook HMAC, gọi Ollama + ghi PostgreSQL, tạm dừng chờ quản lý duyệt, gửi email SMTP).
- **Flowable REST 8.0.0** (`Apache-2.0`): RAM rảnh `371,6 MiB` → vượt ngân sách 1,5 GB khi chạy kèm ClamAV.
- **Kestra 2.0.10** (`Apache-2.0`): RAM rảnh `848,6 MiB`, tự tải plugin lúc khởi động → không phù hợp Box ngoại tuyến 8 GB RAM.

## Quyết định

1. **Gỡ bỏ hoàn toàn `n8n` (`box-n8n`)** khỏi `docker-compose.yml.j2`, `box/ansible/site.yml`, `group_vars/all.yml` và toàn bộ script máy trạm/Box.
2. **Thay bằng `Node-RED 5.0.9` (`box-quy-trinh`)** kết hợp với cơ sở dữ liệu cấu trúc **PostgreSQL + PostgREST** (`box-du-lieu`) và ứng dụng **Sổ điều hành HTX** (`so-dieu-hanh`).
3. **Bổ sung luồng phê duyệt có con người (Human-in-the-loop Approval + Poka-yoke):**
   - Mọi đơn hàng hoặc đề xuất hỗ trợ/mua sắm mới tạo có trạng thái `CHO_DUYET`.
   - Quy trình tạm dừng chờ người thuộc nhóm `quan_ly` duyệt (`DA_DUYET`) hoặc từ chối (`TU_CHOI` kèm lý do bắt buộc).
   - **Chốt chặn Poka-yoke ở cả 3 tầng** (Giao diện Sổ điều hành, Quy trình `/webhook/onebee-phe-duyet`, và Ràng buộc `CHECK` + RLS trong PostgreSQL): người tạo đơn (`nguoi_tao`) **không bao giờ** được tự duyệt đơn của chính mình (`nguoi_duyet <> nguoi_tao`), kể cả khi người đó có vai trò `quan_ly`.

## Bảng ánh xạ 10 quy trình cũ sang kiến trúc mới (+ quy trình thứ 11)

| Mã | Quy trình cũ (n8n) | Việc đang làm | Đầu vào | Đầu ra | Đích mới | Test hiện có | Test mới |
|---|---|---|---|---|---|---|---|
| `01` | `01-bao-cao-sao-luu` | Nhận báo cáo sao lưu đêm và gửi email | `POST /webhook/onebee-bao-cao-sao-luu` (JSON + `X-OneBee-Key`) | Email SMTP báo kết quả sao lưu | Động cơ quy trình Node-RED (`01-bao-cao-sao-luu`) | `check-n8n-inside.sh` | `check-quy-trinh-inside.sh` + `test_onebee_dxos_core.py` |
| `02` | `02-nhac-han-bao-cao-thue` | Lịch 07:30 hằng ngày nhắc hạn thuế/BHXH/báo cáo | Lịch hẹn `onebee_box_lich_han` | Email nhắc trước `[7, 3, 1, 0]` ngày | Động cơ quy trình Node-RED (`02-nhac-han-bao-cao-thue`) | `check-n8n-inside.sh` | `check-quy-trinh-inside.sh` + `test_onebee_dxos_core.py` |
| `03` | `03-tom-tat-van-ban` | Nhận văn bản hoặc tệp PDF, gọi Ollama tóm tắt | Văn bản / PDF tải lên | Bản tóm tắt tiếng Việt | Khung `[I]` Sổ điều hành gọi thẳng `/ai/tom-tat` (`onebee-ai-rag.py`) + luồng `03-tom-tat-van-ban` | `test_onebee_n8n_workflows.py` | `test_onebee_dxos_core.py` |
| `04` | `04-nhap-don-hang` | Biểu mẫu nhập đơn hàng vào CSV | Thông tin đơn hàng, số tiền, tệp đính kèm | Bản ghi `api.don_hang` (`CHO_DUYET`) + dòng CSV | Biểu mẫu `[P]` Sổ điều hành → `POST /api/don_hang` + luồng duyệt `11-phe-duyet-quan-ly` | `test_onebee_n8n_workflows.py` | `test_onebee_dxos_core.py` + `check-quy-trinh-inside.sh` |
| `05` | `05-tong-hop-don-hang` | Lịch sáng thứ Hai tổng hợp đơn hàng tuần | Bảng `api.don_hang` / `don-hang.csv` | Email báo cáo tổng hợp đơn hàng tuần | Động cơ quy trình Node-RED (`05-tong-hop-don-hang`) đọc PostgreSQL | `test_onebee_n8n_workflows.py` | `test_onebee_dxos_core.py` |
| `06` | `06-nhan-tinh-trang-may-tram` | Nhận báo cáo tình trạng từ máy trạm | `POST /webhook/onebee-tinh-trang` (JSON + chữ ký HMAC / `X-OneBee-Key`) | `/data/tinh-trang-may/<ten>.json` + bảng `api.tinh_trang_may` | Động cơ quy trình Node-RED (`06-nhan-tinh-trang-may-tram`) | `test_onebee_may_tram.py` | `test_onebee_may_tram.py` + `check-quy-trinh-inside.sh` |
| `07` | `07-yeu-cau-ho-tro` | Biểu mẫu nhân viên gửi yêu cầu hỗ trợ kỹ thuật | Máy trạm, loại sự cố, mức độ, mô tả | Bản ghi `api.yeu_cau_ho_tro` + `yeu-cau.csv` + email báo kỹ thuật | Biểu mẫu `[P]` Sổ điều hành + luồng `07-yeu-cau-ho-tro` | `test_onebee_bao_ho_tro.py` | `test_onebee_bao_ho_tro.py` + `test_onebee_dxos_core.py` |
| `08` | `08-xu-ly-yeu-cau` | Kỹ thuật viên ghi kết quả xử lý hỗ trợ | Mã yêu cầu, người xử lý, cách xử lý, số phút | Bản ghi `api.xu_ly_ho_tro` + cập nhật `DA_XU_LY` + `xu-ly.csv` | Mục kỹ thuật `[P]` Sổ điều hành (`POST /api/xu_ly_ho_tro`) + luồng `08-xu-ly-yeu-cau` | `test_onebee_bao_cao_tuan.py` | `test_onebee_bao_cao_tuan.py` + `test_onebee_dxos_core.py` |
| `09` | `09-khao-sat-hai-long` | Khảo sát mức độ hài lòng ẩn danh (1–5 sao) | Điểm 1–5, góp ý (ẩn danh, không gắn `Remote-User`) | Bản ghi `api.khao-sat` + `khao-sat.csv` | Biểu mẫu khảo sát `[P]` Sổ điều hành (`POST /api/khao_sat`) + luồng `09-khao-sat-hai-long` | `test_onebee_bao_cao_tuan.py` | `test_onebee_bao_cao_tuan.py` + `test_onebee_dxos_core.py` |
| `10` | `10-canh-bao-su-co` | Nhận cảnh báo sự cố chủ động từ `onebee-canh-bao` | `POST /webhook/onebee-canh-bao` + `X-OneBee-Box-Token` | Email khẩn cấp + nhật ký cảnh báo | Động cơ quy trình Node-RED (`10-canh-bao-su-co`) | `test_onebee_n8n_workflows.py` | `test_onebee_dxos_core.py` + `check-quy-trinh-inside.sh` |
| `11` | *(Mới)* `11-phe-duyet-quan-ly` | Quản lý duyệt/từ chối đơn hàng & đề xuất (`CHO_DUYET`) | `POST /webhook/onebee-phe-duyet` (`loai`, `id`, `trang_thai_duyet`, `ly_do_duyet`) | Cập nhật `DA_DUYET`/`TU_CHOI` trong PostgreSQL + gửi thông báo kết quả | Động cơ quy trình Node-RED (`11-phe-duyet-quan-ly`) kèm Poka-yoke (`nguoi_duyet <> nguoi_tao`) | *(Chưa có)* | `test_onebee_dxos_core.py` + `check-quy-trinh-inside.sh` |

### Ghi chú kỹ thuật chuyển đổi

- **Xử lý trích xuất văn bản PDF (`pdftotext`):** Trước đây `box/ansible/roles/box-n8n/Dockerfile` cài `poppler-utils` (`pdftotext`) bên trong ảnh container n8n để phục vụ quy trình `03-tom-tat-van-ban`. Trong kiến trúc mới, việc trích xuất văn bản từ tệp `.pdf`, `.docx`, `.odt`, `.txt`, `.md` và ẩn danh hóa PII trước khi gọi Ollama đã được chuyển hoàn toàn sang dịch vụ **`box/ansible/roles/box-ai/files/onebee-ai-rag.py`** (tuyến `/ai/tom-tat`) và công cụ nạp tri thức trên máy chủ Box. Do đó image `nodered/node-red` giữ nguyên bản gốc chính thức, không cần build Dockerfile riêng.
- **Danh mục tệp thay thế / cập nhật:**
  - *Xóa bỏ:* `box/ansible/roles/box-n8n/` (toàn bộ role, `Dockerfile`, và 10 tệp `.json.j2` cũ).
  - *Tạo mới:* `box/ansible/roles/box-quy-trinh/` (`tasks/main.yml`, `templates/flows.json.j2`, `templates/settings.js.j2`, `templates/_csv-js.j2`), `tests/box/check-quy-trinh-inside.sh`.
  - *Cập nhật:* `box/ansible/site.yml`, `box/ansible/group_vars/all.yml`, `box/ansible/roles/box-stack/templates/docker-compose.yml.j2`, `Caddyfile.j2`, `onebee-canh-bao.sh.j2`, `onebee-box-common.sh.j2`, `onebee-box-sao-luu.sh.j2`, `onebee-box-chan-doan.sh.j2`, `onebee-box-may-tram.sh.j2`, `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-tinh-trang`, `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-ho-tro`.

## Hệ quả

- **100% giấy phép chuẩn OSI:** Toàn bộ ngăn xếp OneBee Box không còn bất kỳ thành phần fair-code hay giới hạn thương hiệu nào.
- **Tương thích ngược với máy trạm:** Các máy trạm chạy `onebee-bao-tinh-trang` hoặc `onebee-bao-ho-tro` giữ nguyên cấu trúc dữ liệu gửi lên; `onebee-bao-cao-tuan.py` đọc được cả từ PostgreSQL lẫn tệp CSV.
