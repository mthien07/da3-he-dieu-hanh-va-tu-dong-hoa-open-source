---
title: "Spec kỹ thuật chi tiết cho đội thi — Giai đoạn 1, 5, 6, 7 (OLP 2026 DX-OS Open-Core)"
based_on:
  - docs/adr/0006-loi-dx-os-open-core.md
  - plans/261113-0134-olp-2026-dx-os-open-core/plan.md
  - origin/feat/box-dang-nhap-mot-lan-va-cong-api (Giai đoạn 4)
created: 2026-11-15
---

# Spec kỹ thuật chi tiết — Giai đoạn 1, 5, 6, 7 (OLP 2026 DX-OS Open-Core)

Tài liệu này là bản hướng dẫn thực hành trực tiếp cho các bạn nhận **Giai đoạn 1, 5, 6, 7**. Mọi công nghệ, tên dịch vụ, đường dẫn và quy ước đều lấy theo đúng **ADR 0006** đã duyệt trên `main` và code thực tế của **Giai đoạn 4** (`feat/box-dang-nhap-mot-lan-va-cong-api`) để 4 nhánh ghép vào nhau là chạy ngay, không lệch chuẩn, không sai đề OLP 2026.

---

## 1. Bức tranh tổng thể & 4 nguyên tắc không được làm sai

### 1.1. Kiến trúc 3 tầng theo Đề thi OLP 2026
1. **Tầng 1 — Nền tảng Dịch vụ Lõi số (Headless PaaS, KHÔNG có giao diện người dùng cuối):**
   - Toàn bộ nằm trên mạng Docker nội bộ của Box, **không mở cổng trực tiếp ra LAN** (trừ Caddy cổng `80`/`443`).
   - Thành phần đã chốt trong `docs/adr/0006-loi-dx-os-open-core.md`:
     - **Định danh SSO & 2FA:** Authelia `4.39.28` phục vụ tại đường dẫn con `/dangnhap`.
     - **Cổng API biên mạng (Zero-Trust):** Caddy `2.11.4` (`forward_auth` qua Authelia + xóa sạch header `Authorization`, `Cookie`, `Remote-*` do máy khách tự gửi).
     - **Cầu nối danh tính:** `onebee-cau-noi-danh-tinh.py` (Python 3.14, MIT) nhận `Remote-User`/`Remote-Groups` từ Caddy, ký JWT HS256 sống **60 giây** (`sub`, `role` ∈ `{quan_ly, ky_thuat, nhan_vien}`, `aud: onebee-api`) rồi chuyển tiếp.
     - **Dữ liệu cấu trúc + Vector + API tự sinh:** PostgreSQL `18` (`pgvector 0.8.7`) + PostgREST `v16.5` (RLS tới từng dòng).
     - **Kho tệp phi cấu trúc + Kiểm dịch biên mạng:** SeaweedFS `4.53` + ClamAV `1.5.4` (`clamscan` chạy từng lượt theo lô ~10s với `--network none`, **không** chạy `clamd` thường trú, **bỏ `libclamunrar`**).
     - **Động cơ quy trình:** Node-RED `5.0.9` + `node-red-node-email` `5.2.5` (Apache-2.0, thay `n8n`).
     - **AI cục bộ:** Ollama `0.34.4` + `gemma4:e2b-it-qat` (bỏ `Open WebUI`).
2. **Tầng 2 — Không gian Năng lực số H-P-D-I (Giao diện người dùng cuối):**
   - Duy nhất một ứng dụng web **"Sổ điều hành HTX"** (HTML + CSS + JS thuần, không tải thư viện từ Internet), đặt sau Caddy `forward_auth`.
   - Mọi thao tác đọc/ghi dữ liệu, tải tệp, hỏi AI đều đi qua cổng Caddy (`/api/*`, `/files/*`, `/ai/*`), tuyệt đối không nối thẳng DB hay container lõi.
3. **Luồng đi của một request chuẩn:**
   ```
   Trình duyệt / Máy trạm
     │  (HTTPS tới https://box.<mã>.onebee.internal/...)
     ▼
   Caddy (:443) ──[xóa Remote-*, Cookie/Auth giả]──► forward_auth ─► Authelia (:9091/dangnhap)
     │                                                                 │ (hợp lệ: trả Remote-User, Remote-Groups)
     ├── /dangnhap* ──────────────────────────────────────────────► Authelia (:9091)
     ├── /api/*     ──► cau-noi:8080 (ký JWT HS256 60s, bỏ /api) ──► PostgREST (:3000) ──► PostgreSQL (RLS)
     ├── /files/*   ──► dich-vu-tep (kiểm tra JWT/nhóm) ──────────► Vùng chờ ──(clamscan)──► SeaweedFS
     ├── /ai/*      ──► dich-vu-ai-rag (GĐ 8) ────────────────────► Ollama (:11434) + pgvector
     └── /so-dieu-hanh/* ─────────────────────────────────────────► Tệp tĩnh Web H-P-D-I (GĐ 6)
   ```
4. **Chuẩn PoF & Repo (`CLAUDE.md` — mất điểm hoặc rớt CI nếu vi phạm):**
   - Mọi tệp mã mới/sửa (`.py`, `.sh`, `.yml`, `.j2`, `.js`, `.html`, `.css`, `.sql`) phải có dòng `SPDX-License-Identifier: MIT` ở 5 dòng đầu.
   - Không còn dấu vết `n8n`, `open-webui`, `libclamunrar` trong bộ cài mặc định.
   - Image Docker mới phải ghim đủ `tag@sha256:...` trong `box/ansible/group_vars/all.yml`, chạy với `no-new-privileges: true`.
   - Ansible chạy lại lần 2 bắt buộc đạt `changed=0 failed=0`.
   - Commit tiếng Việt theo Conventional Commits (`feat(box): ...`, `fix(desktop): ...`), tuyệt đối không nhắc tên AI.

---

## 2. Giao tiếp API dùng chung (Contract giữa các giai đoạn)

Các bạn làm GĐ 5, 6, 7 bám chính xác từng tên đường dẫn, tên cột và mã HTTP dưới đây để khi ghép với GĐ 3, 4, 8 không phải sửa lại:

### 2.1. Định danh & Phiên người dùng (GĐ 4 đã làm sẵn)
- **Tên miền bắt buộc:** `https://box.<mã>.onebee.internal` (truy cập qua IP chỉ mở trang hướng dẫn dùng tên miền).
- **Lấy thông tin người dùng hiện tại (dùng cho `[H]` ở GĐ 6):**
  - `GET /api/toi` → Cầu nối trả trực tiếp `200 OK`:
    ```json
    { "ten": "an.nv", "vai_tro": "nhan_vien" }
    ```
  - Nếu chưa đăng nhập: Caddy trả `302` chuyển sang `/dangnhap/` (trình duyệt) hoặc `401` (API).
  - Nếu không thuộc nhóm nào trong `{quan_ly, ky_thuat, nhan_vien}`: `403`.

### 2.2. Dữ liệu cấu trúc `/api/*` (PostgREST + PostgreSQL RLS — GĐ 3)
*Lưu ý của cầu nối GĐ 4: thân request tối đa **1 MB** (`413` nếu vượt), cầu nối tự cắt tiền tố `/api` trước khi chuyển cho PostgREST.*

- **Các tài nguyên chính:**
  - `GET/POST/PATCH /api/don_hang`
  - `GET/POST/PATCH /api/yeu_cau_ho_tro`
  - `GET/POST /api/xu_ly_ho_tro`
  - `GET/POST /api/khao_sat`
  - `GET /api/tinh_trang_may` (chỉ đọc qua API; ghi từ Node-RED ở GĐ 5)
  - `GET /api/tep_dinh_kem` (metadata tệp gắn với đơn/yêu cầu)
- **Các cột phục vụ quy trình phê duyệt `[P]` trên `don_hang` và `yeu_cau_ho_tro`:**
  - `id` (uuid / bigserial), `nguoi_tao` (text, mặc định lấy từ claim `sub` của JWT), `ngay_tao` (timestamptz)
  - `trang_thai_duyet`: `'NHAP'` | `'CHO_DUYET'` | `'DA_DUYET'` | `'TU_CHOI'`
  - `nguoi_duyet` (text, nullable)
  - `ly_do_duyet` (text, nullable)
  - `thoi_gian_duyet` (timestamptz, nullable)
- **Ràng buộc Poka-yoke ở tầng CSDL (GĐ 6 chỉ cần bắt mã lỗi `400`/`403`/`409` của PostgREST để hiển thị tiếng Việt):**
  - `CHECK (nguoi_duyet IS DISTINCT FROM nguoi_tao)` → quản lý không bao giờ tự duyệt đơn của chính mình.
  - RLS: `nhan_vien` chỉ `SELECT`/`INSERT` dòng của mình (và chỉ sửa khi còn `'NHAP'`), không được chuyển sang `'DA_DUYET'`/`'TU_CHOI'`; `quan_ly` xem được tổng hợp và cập nhật duyệt.

### 2.3. Kho tệp & Kiểm dịch `/files/*` (GĐ 7 xây dựng, GĐ 6 gọi)
*Cảnh báo Caddyfile (xem `box/ansible/roles/box-stack/templates/Caddyfile.j2` ở GĐ 4): giữ nguyên tiền tố `/files/*` khi qua `forward_auth` rồi mới cắt hoặc chuyển tiếp tới dịch vụ tệp; không dùng `handle_path` bọc ngoài `forward_auth`.*

- **Tải tệp lên:** `POST /files/` (hoặc `PUT /files/<tên_tệp>`), `Content-Type: multipart/form-data` (trường `file`, kèm `doi_tuong_loai` ∈ `{'don_hang', 'yeu_cau_ho_tro'}` và `doi_tuong_id`).
  - Kiểm tra định dạng cho phép (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.docx`, `.xlsx`, `.odt`, `.ods`) và dung lượng ≤ **10 MB** (sai đuôi → `415`, quá dung lượng → `413`).
  - Ghi tạm vào vùng chờ quét (vd `/var/lib/onebee-kho-tep/cho-quet/`), tạo bản ghi trong bảng `tep_dinh_kem` với `trang_thai_quet = 'PENDING_SCAN'`, `nguoi_tai_len = sub`.
  - Trả về **`202 Accepted`**:
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "ten_tep": "bao_gia.pdf",
      "kich_thuoc": 102400,
      "trang_thai_quet": "PENDING_SCAN"
    }
    ```
- **Kiểm tra trạng thái quét:** `GET /api/tep_dinh_kem?id=eq.<id>` (hoặc `GET /files/<id>/trang-thai`).
  - Tác vụ nền chạy `clamscan --network none` theo lô mỗi ~10 giây:
    - Sạch → đẩy file vào SeaweedFS Filer (`/tep/<nguoi_tai_len>/<id>_<ten_tep>`), xóa bản tạm, cập nhật `trang_thai_quet = 'CLEAN'`, lưu `khoa_luu_tru` & `sha256`.
    - Có mã độc (vd chuỗi thử `EICAR`) → **không đẩy vào SeaweedFS**, chuyển file tạm vào vùng cách ly (chỉ root đọc) hoặc xóa, cập nhật `trang_thai_quet = 'INFECTED'`.
- **Tải tệp xuống:** `GET /files/<id>`
  - Kiểm tra quyền đọc qua JWT (chủ sở hữu `nguoi_tai_len`, hoặc `ky_thuat`/`quan_ly` đối với yêu cầu hỗ trợ/đơn hàng).
  - Nếu `trang_thai_quet == 'PENDING_SCAN'` → trả **`423 Locked`** (`{"loi": "Tệp đang chờ kiểm dịch, thử lại sau vài giây"}`).
  - Nếu `trang_thai_quet == 'INFECTED'` → trả **`403 Forbidden`** (`{"loi": "Tệp bị chặn do phát hiện mã độc"}`).
  - Nếu `trang_thai_quet == 'CLEAN'` → stream tệp từ SeaweedFS về kèm `Content-Disposition: attachment; filename="..."` và `X-Content-Type-Options: nosniff`.

### 2.4. Động cơ quy trình Node-RED (GĐ 5 xây dựng, GĐ 6 kích hoạt)
- **Tách biệt mạng:** Node-RED chạy trong mạng Docker nội bộ (`1880` không mở ra LAN, chỉ nhận webhook nội bộ từ Caddy/mạng Docker).
- **Webhook từ máy trạm (giữ tương thích máy trạm đang chạy):**
  - Nhận báo cáo tình trạng máy (`onebee-bao-tinh-trang`) và cảnh báo (`onebee-canh-bao`), **giữ nguyên kiểm chữ ký HMAC-SHA256** (`X-OneBee-Signature` / `X-OneBee-Key` theo cấu hình hiện tại), sai chữ ký trả `401`/`403`, hợp lệ ghi vào bảng `tinh_trang_may`.
- **Webhook luồng phê duyệt (nội bộ Docker, gọi từ ứng dụng hoặc trigger):**
  - `POST http://nodered:1880/noi-bo/phe-duyet/gui` (kèm `{ "loai": "don_hang", "id": "...", "nguoi_tao": "...", "tom_tat": "..." }`): gửi email thông báo tới địa chỉ của nhóm `quan_ly` (nếu `smtp_host` đã cấu hình).
  - `POST http://nodered:1880/noi-bo/phe-duyet/ket-qua` (kèm `{ "loai": "don_hang", "id": "...", "trang_thai_duyet": "DA_DUYET|TU_CHOI", "nguoi_duyet": "...", "ly_do_duyet": "..." }`): gửi email báo kết quả cho `nguoi_tao`.

### 2.5. Trợ lý AI `/ai/*` (GĐ 8 xây dựng, GĐ 6 gọi)
- `POST /ai/hoi` với body `{ "cau_hoi": "..." }` → trả `{ "tra_loi": "...", "nguon": [...], "nhac_kiem_tra": "..." }`.
- `POST /ai/tom-tat` với body `{ "so_don_tuan": 12, "ty_le_duyet": 0.75, "ho_tro_dang_mo": 3, "may_da_sao_luu": 8 }` (**tuyệt đối không gửi tên, email, SĐT nhân viên**) → trả `{ "tom_tat": "...", "nhac_kiem_tra": "AI có thể nhầm, quản lý cần kiểm tra lại số liệu gốc." }`.

---

## 3. Chi tiết công việc từng Giai đoạn

### Giai đoạn 1 — Vá điểm PoF: giấy phép và đóng gói *(Bắt đầu ngay)*
- **Nhánh làm việc:** `chore/giay-phep-tung-tep-va-dong-goi` (**PR #16 đang mở** — rebase lên `origin/main` mới nhất trước khi sửa tiếp).
- **Các bước chi tiết:**
  1. Rebase nhánh lên `origin/main`:
     - Xem log lỗi CI hiện tại của PR #16 ở `tests/box/test_onebee_caddy_https.py` (`port 5577347 is out of range` — kiểm tra xem sau khi rebase lên `origin/main` mới nhất còn lỗi không, hoặc do dòng comment SPDX chèn vào `Caddyfile.j2` làm lệch parser/test nào).
  2. Chạy `python3 scripts/chen-giay-phep.py --kiem` trên toàn bộ tệp mã mới sau rebase (đặc biệt các tệp mới từ PR #14, #15, #17, #18, #19, #20, #22) và chèn bổ sung `SPDX-License-Identifier: MIT` nếu thiếu.
  3. Sửa `README.md` (mục `## ⚖️ Giấy phép`): bổ sung 1 đoạn ngắn nêu rõ **mục đích giấy phép MIT** (cho phép mọi cá nhân, doanh nghiệp, cơ quan tự do dùng, xem mã, sửa đổi và phân phối lại, bảo đảm chủ quyền số và không bị nhà cung cấp khóa chặt).
  4. Kiểm thử **chạy bên ngoài thư mục mã nguồn** (PoF tiêu chí 4 trừ 5đ nếu không chạy được ngoài thư mục nguồn):
     - Chạy `scripts/dong-goi-ban-phat-hanh.sh 1.3.0-dev` (lưu ý đổi các chỗ ghi `1.2.0` sang `1.3.0-dev` hoặc `[Unreleased]` trong `CHANGELOG.md` vì `v1.2.0` đã phát hành).
     - Giải nén `dist/onebee-os-1.3.0-dev.tar.gz` sang `/tmp/kiem-ngoai`, kiểm tra có file `LICENSE` ở gốc và chạy thử `python3 scripts/chen-giay-phep.py --kiem` + `tests/desktop/test_onebee_phien_ban.py` từ `/tmp/kiem-ngoai` đều thoát mã 0 (xong nhớ `rm -rf dist /tmp/kiem-ngoai`).
  5. Mở **GitHub Issues** cho từng giai đoạn của kế hoạch OLP 2026 (dùng `gh issue create`) để ban giám khảo thấy bug tracker được dùng thật sự.
- **Lệnh kiểm chứng bắt buộc:**
  ```bash
  ~/.cache/onebee-kiem/bin/python -m unittest tests/desktop/test_onebee_giay_phep.py
  ~/.cache/onebee-kiem/bin/python -m unittest tests/desktop/test_onebee_phien_ban.py
  python3 scripts/chen-giay-phep.py --kiem
  python3 tests/kiem-tra-mau-jinja.py
  gh pr checks --watch
  ```

---

### Giai đoạn 5 — Thay n8n bằng Node-RED `5.0.9` + luồng phê duyệt *(Làm sau khi GĐ 3 có lược đồ CSDL)*
- **Nhánh làm việc:** tách mới `feat/box-dong-co-quy-trinh-osi` từ `origin/main` (kéo bản nháp ở nhánh local `docs/adr-0007-thay-n8n` vào làm cơ sở cho bước 1).
- **Hiện trạng các tệp cần biết:**
  - Role n8n cũ: `box/ansible/roles/box-n8n/` (gồm 10 tệp quy trình `01-bao-cao-sao-luu.json.j2` → `10-canh-bao-su-co.json.j2` và 2 mẫu dùng chung `_csv-js.j2`, `_gui-email.json.j2`).
  - Máy trạm gửi về n8n qua: `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-tinh-trang`, `box/ansible/roles/box-stack/templates/onebee-canh-bao.sh.j2`, `box/ansible/roles/box-fleet/files/dong-bo-may-tram.yml`.
  - Test cũ cần thay/cập nhật: `tests/box/check-n8n-inside.sh`, `tests/box/test_onebee_n8n_templates.py`, `tests/box/check-alerts.sh`, `tests/box/verify-box-install.sh`, `tests/box/check-https.sh`, `tests/box/check-xoay-khoa.sh`.
- **Các bước chi tiết:**
  1. Hoàn thiện `docs/adr/0007-thay-n8n.md`: bảng 10 dòng (quy trình cũ → việc làm → đầu vào/đầu ra → nơi mới: Node-RED flow hay Trang ứng dụng GĐ 6 → test tương ứng) + danh sách toàn bộ tệp tìm được từ `git grep -il n8n -- . ':!plans'`.
  2. Tạo role `box/ansible/roles/box-quy-trinh/` chạy `docker.io/nodered/node-red:5.0.9@sha256:2ccd38b4066648bd5e17430c50a2f8102c566a82fd4f2fc5c342e61664d6896f` (cài sẵn gói `node-red-node-email` `5.2.5`, khai báo trong `group_vars/all.yml`, `no-new-privileges: true`, không công bố cổng `1880` ra LAN).
  3. Viết các flow Node-RED bằng file JSON quản lý trong Git (deploy bằng Ansible, không sửa tay trên UI):
     - Nhóm nhận webhook + HMAC-SHA256 (`01` báo cáo sao lưu, `06` tình trạng máy trạm ghi vào PostgreSQL `tinh_trang_may`, `10` cảnh báo).
     - Nhóm chạy theo lịch (`02` nhắc hạn thuế/BHXH, `05` tổng hợp đơn hàng tuần).
     - Nhóm **phê duyệt mới** (mục 2.4).
     - *(Các form nhập `04`, `07`, `08`, `09` chuyển hẳn lên ứng dụng web GĐ 6, KHÔNG làm lại trong Node-RED; `03` tóm tắt PDF chuyển sang GĐ 6/8 dùng `pdftotext`.)*
  4. Cập nhật địa chỉ webhook mới trên máy trạm (`onebee-bao-tinh-trang`, `dong-bo-may-tram.yml`, `onebee-box them-may`) để máy trạm cũ tự nhận địa chỉ mới khi chạy `dong-bo-may`.
  5. Gỡ bỏ hoàn toàn role `box-n8n`, dịch vụ `n8n` trong `docker-compose.yml.j2`, cổng `5678` trong `box-firewall`, biến `n8n` trong `all.yml` & `onebee-box` (`in-khoa`, `xoay-khoa`, `chan-doan`). Nếu nâng cấp Box đã cài trước đó, giữ thư mục dữ liệu cũ thành `n8n.da-thay-<ngày>`.
- **Lệnh kiểm chứng bắt buộc:**
  - `git grep -il n8n -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr'` **không in ra dòng nào**.
  - Test đơn vị cho từng file flow JSON (cú pháp hợp lệ, không lộ mật khẩu SMTP).
  - Bài kiểm Box `check-quy-trinh-inside.sh` (hộp thư giả nhận đủ email báo cáo sao lưu, nhắc hạn, thông báo duyệt/từ chối; gửi tình trạng máy sai chữ ký HMAC bị từ chối).
  - `gh workflow run ci.yml --ref feat/box-dong-co-quy-trinh-osi -f box=true` xanh và lần cài hai `changed=0`.

---

### Giai đoạn 7 — Kho tệp SeaweedFS + Kiểm dịch ClamAV *(Làm sau khi có GĐ 4)*
- **Nhánh làm việc:** tách mới `feat/box-kho-tep-va-kiem-dich` từ `origin/main`.
- **Điểm cần hỏi anh Thiện trước khi code (đã ghi ở ADR 0006 QĐ1):** image ClamAV bỏ `libclamunrar` (1 lớp từ `FROM scratch` hoặc gói Debian `1.4.3+dfsg-1` trên `debian:trixie-slim`) sẽ **dựng cục bộ khi cài Box** bằng `Dockerfile` trong role hay **kéo từ GHCR**?
- **Các bước chi tiết:**
  1. Tạo role `box/ansible/roles/box-kho-tep/`:
     - Thêm dịch vụ `seaweedfs` (`docker.io/chrislusf/seaweedfs:4.53@sha256:ccad23e18639c8b98cee17e7100b95830a06077b56d8e5b006d6dcf8ec5e94a0`) chỉ nằm trong mạng Docker nội bộ (không mở cổng 8333/8888/9333 ra LAN).
     - Thiết lập tác vụ quét lô `clamscan` (systemd timer hoặc worker chạy tuần tự không song song, giới hạn 1 tiến trình để đỉnh RAM ≤ 962 MiB theo ADR 0006 QĐ5), lệnh quét chạy với `--network none` và mount thư mục chữ ký virus (`main.cvd`, `daily.cvd`, `bytecode.cvd`).
     - Thêm lệnh `onebee-box cap-nhat-chu-ky-virus <thư-mục>` (chép từ USB/LAN khi Box offline) và lịch `freshclam` khi có mạng.
  2. Viết dịch vụ `onebee-kho-tep.py` (Python 3.14 thư viện chuẩn, MIT) chạy sau Caddy:
     - Triển khai đúng contract ở mục 2.3 (`POST /files/`, `GET /files/<id>`, quét lô ~10s, ghi metadata bảng `tep_dinh_kem` qua PostgreSQL/PostgREST).
     - Nối tuyến `/files/*` trong `Caddyfile.j2` (đặt sau `forward_auth` giống `/api/*`).
  3. Cập nhật `onebee-box-sao-luu.sh.j2` (sao lưu cả dữ liệu SeaweedFS trong khi tạm dừng container), `khoi-phuc-toan-bo`, và `onebee-box-chan-doan.sh.j2`.
- **Lệnh kiểm chứng bắt buộc:**
  - Test đơn vị kiểm tra `docker-compose.yml.j2` (không công bố cổng SeaweedFS ra ngoài, có `no-new-privileges`), `tests/kiem-tra-mau-jinja.py` 0 lỗi.
  - Bài kiểm Box (`check-kho-tep-inside.sh`):
    - Gọi `/files/` không có phiên → `401`.
    - Tải tệp PDF sạch → `202` → sau tối đa 15s trạng thái thành `CLEAN` → `GET /files/<id>` trả `200` đúng SHA-256.
    - Tải tệp chứa chuỗi thử chuẩn `EICAR` (`X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*`) → trạng thái thành `INFECTED`, `GET /files/<id>` trả `403`.
  - Cập nhật `tests/box/check-khoi-phuc-toan-bo.sh`: tải 1 tệp qua `/files/` trước khi giả lập hỏng ổ, sau khi khôi phục vẫn tải lại được đúng tệp đó.
  - Chạy CI `box=true` xanh với lần cài hai `changed=0`.

---

### Giai đoạn 6 — Ứng dụng minh họa H-P-D-I "Sổ điều hành HTX" *(Làm sau GĐ 3, 4, 5, 7, 8)*
- **Nhánh làm việc:** tách mới `feat/ung-dung-so-dieu-hanh-htx` từ `origin/main`.
- **Lưu ý triển khai sớm:** trong lúc đợi API thật của GĐ 5, 7, 8 hoàn thiện, bạn làm GĐ 6 có thể dựng trước toàn bộ giao diện HTML/CSS/JS tĩnh và mock cấu trúc JSON khớp 100% mục 2 để khi ghép chỉ việc trỏ URL thật.
- **Các bước chi tiết:**
  1. Tạo bộ giao diện tĩnh trong role `box-stack` (phục vụ tại `/so-dieu-hanh/` qua Caddy sau `forward_auth`, tổng dung lượng mỗi trang **< 40 KB**, **0 liên kết CDN ngoài**, render mọi dữ liệu từ API bằng `textContent`, cấm tuyệt đối `innerHTML` với dữ liệu người dùng để chống XSS).
  2. Xây dựng đủ 4 không gian theo đúng khung H-P-D-I:
     - **[H] Con người số:** gọi `GET /api/toi` hiển thị tên, vai trò; có nút mở Thư mục chung (Samba/hướng dẫn), Kho tệp đã tải, Trợ lý AI và Đăng xuất (`/dangnhap/logout`).
     - **[P] Quy trình số:**
       - 3 biểu mẫu: **Đơn hàng** (cho phép chọn đính kèm tệp qua `POST /files/`, tự poll trạng thái kiểm dịch đến khi thấy `CLEAN` hoặc báo đỏ nếu `INFECTED`), **Yêu cầu hỗ trợ**, **Khảo sát hài lòng**. Kiểm hợp lệ ở trình duyệt và hiển thị thông báo tiếng Việt rõ ràng khi CSDL trả `400`/`403`.
       - Màn hình **Hàng đợi phê duyệt** (hiện cho `quan_ly`): liệt kê đơn `CHO_DUYET`, link tải tệp đính kèm `CLEAN`, nút **Duyệt** / **Từ chối** + ô lý do → gọi `PATCH /api/don_hang` và gọi webhook Node-RED báo email.
     - **[D] Dữ liệu số:** trang **Điều hành** (nhóm `nhan_vien` bấm vào phải nhận cảnh báo không có quyền / `403` từ API): hiển thị số đơn hàng theo tuần, tỷ lệ duyệt/từ chối, yêu cầu hỗ trợ đang mở, số máy trạm đã sao lưu (`/api/tinh_trang_may`), thống kê tệp sạch/nhiễm (`/api/tep_dinh_kem`). Dùng SVG/Canvas thuần nhẹ thay vì kéo thư viện nặng từ ngoài.
     - **[I] Trí tuệ số:** khung chat Trợ lý AI (gọi `/ai/hoi`, hiển thị câu trả lời + nguồn trích dẫn NĐ 30 + dòng nhắc kiểm tra) và nút **"Nhờ Trợ lý tóm tắt tuần này"** (gọi `/ai/tom-tat` chỉ gửi số liệu tổng hợp từ `[D]`, tuyệt đối không gửi tên/SĐT cá nhân).
  3. Nối vào hệ thống hiện có:
     - Cập nhật trang chủ Box (`box/ansible/roles/box-stack/templates/index.html.j2` từ PR #18) bỏ các thẻ biểu mẫu n8n & Open WebUI cũ, trỏ sang `/so-dieu-hanh/`.
     - Cập nhật `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-ho-tro` và lối tắt trên máy trạm trỏ đúng sang trang biểu mẫu mới.
- **Lệnh kiểm chứng bắt buộc:**
  - Test đơn vị HTML/JS: không link ngoài (`http://`/`https://` tới CDN), không dùng `innerHTML` với biến động, mỗi file < 40 KB.
  - Bài kiểm Box (`box=true`): chạy thông suốt kịch bản `chưa đăng nhập (chuyển tới /dangnhap)` → `nhan_vien tạo đơn + đính kèm tệp sạch (CLEAN)` → `nhan_vien vào trang điều hành nhận 403` → `nhan_vien tự duyệt đơn bị chặn` → `quan_ly duyệt đơn thành DA_DUYET` → `trang điều hành cập nhật số liệu` → `tóm tắt AI trả về tiếng Việt không chứa tên người`.
  - Chạy lại `tests/box/test_onebee_mdns_dashboard.py` và `tests/box/check-quan-ly-tap-trung.sh` đạt 100%.

---

## 4. Những lỗi hay gặp (cần tránh để khỏi mất công sửa lại)

| Lỗi hay vướng | Cách tránh |
|---|---|
| Dùng `handle_path /files/*` bọc ngoài `forward_auth` trong Caddy | **Cấm:** `handle_path` cắt tiền tố trước khi Authelia kiểm tra quy tắc URL. Dùng `handle /files/*` + `forward_auth`, cắt tiền tố ở bước sau hoặc trong app Python. |
| Quên dòng `SPDX-License-Identifier: MIT` ở file mới | Chạy `python3 scripts/chen-giay-phep.py --kiem` trước khi commit. |
| Đẩy nhánh mới nhưng viết theo `main` cũ | Luôn `git fetch origin` và tách nhánh từ `origin/main` mới nhất (đã có ADR 0006 + PR #18 + bản `v1.2.0`). |
| Quên tính lũy nghiệm Ansible (`changed=0` ở lần chạy 2) | Với lệnh shell/docker trong Ansible, luôn dùng `creates:`, `changed_when:`, hoặc kiểm tra trạng thái trước khi chạy. |
| Mở port nội bộ (`1880`, `5432`, `8333`, `8888`, `3000`, `11434`) ra `0.0.0.0` | Trong `docker-compose.yml.j2`, các dịch vụ lõi **không** khai báo `ports:` ra ngoài host (chỉ giao tiếp qua mạng Docker nội bộ với Caddy). |
