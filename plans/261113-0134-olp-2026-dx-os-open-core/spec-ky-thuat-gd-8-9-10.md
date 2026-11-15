---
title: "Spec kỹ thuật chi tiết cho đội thi — Giai đoạn 8, 9, 10 (OLP 2026 DX-OS Open-Core)"
based_on:
  - docs/adr/0006-loi-dx-os-open-core.md
  - plans/261113-0134-olp-2026-dx-os-open-core/plan.md
  - plans/261113-0134-olp-2026-dx-os-open-core/spec-ky-thuat-gd-1-5-6-7.md
  - origin/feat/box-dang-nhap-mot-lan-va-cong-api (Giai đoạn 4)
created: 2026-11-15
---

# Spec kỹ thuật chi tiết — Giai đoạn 8, 9, 10 (OLP 2026 DX-OS Open-Core)

Tài liệu này tiếp nối `spec-ky-thuat-gd-1-5-6-7.md`, hướng dẫn chi tiết **3 giai đoạn cuối (8, 9, 10)** để hoàn thành gỡ Open WebUI, dựng bản chạy thử công khai trên Internet và hoàn thiện toàn bộ hồ sơ chấm điểm PoF + chung kết OLP 2026.

*(Lưu ý hiện trạng 15/11: Cả 3 giai đoạn **8, 9, 10** đều **chưa tạo nhánh và chưa có PR**. Khi bắt đầu làm giai đoạn nào thì tách nhánh mới từ `origin/main` mới nhất.)*

---

## Giai đoạn 8 — Gỡ Open WebUI: Trợ lý AI và RAG trên lõi *(Làm sau GĐ 3, 4)*

- **Nhánh làm việc:** `feat/go-open-webui-rag-tren-loi` (tách từ `origin/main`).
- **Mục tiêu:** Loại bỏ 100% `Open WebUI` (giấy phép có điều khoản thương hiệu ngoài OSI) khỏi bộ cài, thay bằng dịch vụ `onebee-ai-rag` (giấy phép **MIT**) chạy trên Python 3.14 + PostgreSQL (`pgvector 0.8.7`) + Ollama (`0.34.4`), phục vụ cả **Web H-P-D-I** (`/ai/*`) và **CLI `hoi`** trên máy trạm.

### 8.1. Thiết kế dịch vụ `onebee-ai-rag` (Python 3.14, giấy phép MIT)
- **Đóng gói:** dùng chung image đã ghim trong ADR 0006 (`docker.io/library/python:3.14.10-slim-trixie@sha256:9aaa474...`), không mở cổng ra LAN, đặt trong mạng Docker nội bộ cùng `caddy`, `postgres`, `ollama`.
- **Cơ sở dữ liệu tri thức (kết hợp GĐ 3):**
  - Bảng `tai_lieu_tri_thuc`: `id`, `nguon` (tên file), `tieu_de`, `noi_dung_doan`, `embedding` (`vector(384)` hoặc `vector(768)` nếu dùng model embedding, hoặc cột `tsv` `tsvector` tìm kiếm toàn văn tiếng Việt dự phòng nếu không kéo thêm model embedding).
  - Bảng `lich_su_hoi_ai`: lưu câu hỏi/câu trả lời theo `nguoi_tao` (bật RLS chỉ chủ sở hữu đọc được).
- **Kế thừa nguyên vẹn nội dung tốt đã có trên `main` (từ `box/ansible/roles/box-ai/files/`):**
  - Lời dặn hệ thống: `tro-ly-onebee-loi-dan.md`.
  - Gợi ý bấm nhanh: `goi-y.json`.
  - Kho mẫu soạn thảo hành chính: `prompts/` (`bao-cao.json`, `bien-ban.json`, `hop-dong.json`, `to-trinh.json`).
  - Kho tri thức pháp lý: `knowledge/` (`nghi-dinh-30-2020-nd-cp.md`, `luat-hop-tac-xa-2023.md`) + `/usr/local/share/onebee-box/knowledge` (nếu đơn vị có thêm tài liệu).
- **4 điểm cuối API bắt buộc (giữ contract với GĐ 6):**
  1. `POST /ai/hoi`:
     - Body: `{ "cau_hoi": "...", "lich_su": [...] }`
     - Luồng xử lý: truy xuất top 3–5 đoạn liên quan nhất từ `tai_lieu_tri_thuc` → ghép prompt kèm `tro-ly-onebee-loi-dan.md` → gọi `http://ollama:11434/api/chat` (`gemma4:e2b-it-qat`) → trả về:
       ```json
       {
         "tra_loi": "...",
         "nguon": [{ "tieu_de": "Nghị định 30/2020/NĐ-CP", "doan": "..." }],
         "nhac_kiem_tra": "AI có thể sai sót, vui lòng đối chiếu lại văn bản gốc trước khi ký ban hành."
       }
       ```
  2. `POST /ai/tom-tat`:
     - Body: chỉ nhận số liệu tổng hợp (`{ "so_don_tuan": 12, "ty_le_duyet": 0.75, "ho_tro_dang_mo": 3, "may_da_sao_luu": 8 }`).
     - **Kiểm tra chống rò rỉ PII:** từ chối (`400`) hoặc lọc sạch trước khi gửi Ollama nếu phát hiện trường chứa tên, email, SĐT; kết quả trả về luôn kèm dòng `nhac_kiem_tra`.
  3. `GET /ai/mau`: trả về danh sách `prompts/*.json` + `goi-y.json` cho giao diện Web `[I]` hiển thị nút bấm nhanh.
  4. `GET /ai/health`: kiểm tra kết nối PostgreSQL + Ollama.

### 8.2. Xử lý xác thực cho cả Web (SSO) và CLI `hoi` (Terminal)
*Điểm cực kỳ quan trọng khi tích hợp với `Caddyfile.j2` của GĐ 4:*
- **Với trình duyệt (từ Web H-P-D-I ở GĐ 6):** đi qua `import onebee_sso` (`forward_auth` qua Authelia) trên `https://box.<mã>.onebee.internal/ai/*` → Caddy chép `Remote-User` sang `onebee-ai-rag`.
- **Với lệnh `hoi` trên máy trạm (`desktop/ansible/roles/ai-cli/files/hoi`):** `hoi` chạy ở terminal, **không có cookie trình duyệt của Authelia** (nếu gọi vào tuyến `forward_auth` sẽ bị Caddy trả `302` chuyển sang trang `/dangnhap`!).
  - **Cách xử lý chuẩn:** mở tuyến `POST /ai-cli/hoi` trên Caddy (không qua `forward_auth` trình duyệt, nhưng **xóa sạch `Remote-*`**, chỉ chuyển tiếp `Authorization: Bearer <token>` tới `onebee-ai-rag`). Dịch vụ `onebee-ai-rag` tự kiểm tra token theo danh sách băm SHA-256 lưu trong `/etc/onebee-box/secrets/ai-tokens.json` (do `onebee-box` sinh và `onebee-box xoay-khoa` xoay được). Sai hoặc thiếu token → `401`.
  - Cập nhật `desktop/ansible/roles/ai-cli/files/hoi` gọi `POST /ai-cli/hoi` qua hàm `mo()` (giữ nguyên cơ chế **ghim CA nội bộ** của Box).

### 8.3. Gỡ bỏ hoàn toàn Open WebUI
1. Kiểm kê toàn bộ điểm nhắc tới Open WebUI trên `origin/main` (hiện có ~39 tệp, tiêu biểu: `box/ansible/group_vars/all.yml`, `box/ansible/roles/box-stack/templates/docker-compose.yml.j2`, `Caddyfile.j2`, `index.html.j2`, `onebee-box*.sh.j2`, `box/ansible/roles/box-ai/files/onebee-webui.py`, `LICENSES.md`, `README.md`, `tests/box/check-ai-chat-inside.sh`, `check-rag-prompts.sh`, `test_onebee_webui.py`...).
2. Xóa container `open-webui`, xóa `onebee-webui.py`, bỏ cổng `3000` (nếu không dịch vụ nào dùng).
3. **Bảo vệ dữ liệu Box đang chạy:** trong task Ansible nâng cấp, nếu phát hiện thư mục dữ liệu Open WebUI cũ đang tồn tại, **không xóa** mà đổi tên sang `open-webui.da-thay-<ngày>` (lịch sử chat cũ được giữ nguyên ở đó; chỉ nạp lại tài liệu tri thức sang `tai_lieu_tri_thuc`).
4. Cập nhật `LICENSES.md`: gỡ Open WebUI khỏi danh sách thành phần cài đặt, thêm `onebee-ai-rag` (MIT) và `pgvector` (PostgreSQL License).

### 8.4. Lệnh kiểm chứng bắt buộc (Giai đoạn 8)
- `git grep -il "open.webui\|open_webui\|openwebui" -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr' ':!reports'` **không in ra dòng nào**.
- `python3 -m unittest` test hàm chia đoạn văn bản, chống PII trong `/ai/tom-tat`, kiểm tra token CLI `hoi` (`test_onebee_hoi.py`).
- Bài kiểm Box (`box=true`): `/ai/hoi` không phiên nhận `401`; với phiên SSO hoặc token `hoi` hợp lệ trả tiếng Việt có trích dẫn NĐ 30; `check-rag-prompts.sh` & `check-ai-chat-inside.sh` xanh; lần cài hai `changed=0`.

---

## Giai đoạn 9 — Bản chạy thử công khai trên host Internet *(Làm 9.1 sớm, 9.3 sau GĐ 6)*

- **Nhánh làm việc:** `feat/ban-chay-thu-cong-khai-host` (tách từ `origin/main`).
- **Mục tiêu:** Đáp ứng mục 6 của Đề thi (*khuyến khích vận hành thử nghiệm trên Internet để người dùng/BGK trải nghiệm*), tăng điểm **Tiêu chí 8, 9, 11** tại chung kết.

### 9.1. Nguyên tắc an toàn & tách biệt bắt buộc
- **Tuyệt đối tách biệt:** Host demo chỉ dùng dữ liệu giả lập; **không** dùng chung mật khẩu, khóa ký JWT, khóa CA hay kết nối tới Box thật của đơn vị.
- **Không commit bí mật:** Chỉ đưa file mẫu `box/ansible/inventory.demo.ini.example` vào repo; file `inventory.demo.ini` thật và khóa SSH giữ ngoài Git (hoặc trong `.gitignore`).
- **HTTPS thật (Let's Encrypt):** Khi bật biến `onebee_box_che_do_demo: true` và khai báo `onebee_box_domain: <tên-miền-thật>`, `Caddyfile.j2` chuyển sang dùng tên miền thật để Caddy tự xin chứng chỉ Let's Encrypt (giám khảo mở trình duyệt là vào thẳng, không bị cảnh báo CA tự ký).

### 9.2. Các bước triển khai chi tiết
1. **Hạ tầng (anh Thiện chuẩn bị trước ở bước 9.1):**
   - Thuê VPS Ubuntu 24.04 LTS (tối thiểu 4 vCPU, 8 GB RAM, 80 GB SSD), trỏ bản ghi DNS `A` từ tên miền vào IP VPS.
   - Bật tường lửa UFW trên VPS: **chỉ mở `22`, `80`, `443`** (tất cả cổng nội bộ `5432`, `1880`, `8333`, `11434`, `8000` khóa hoàn toàn).
2. **Chế độ demo trong bộ cài Ansible:**
   - Thêm biến `onebee_box_che_do_demo: false` (mặc định tắt ở `all.yml`).
   - Khi `true`:
     - Trên ứng dụng Web H-P-D-I (GĐ 6), hiện thanh nhắc màu nhẹ ở đầu trang: *"Bản chạy thử công khai OLP 2026 — Dữ liệu giả lập, tự đặt lại lúc 03:00 mỗi ngày"* + hộp hướng dẫn **3 tài khoản dùng thử** (`nhanvien1`, `kythuat1`, `quanly1` kèm mật khẩu công khai cho BGK thử 1 chạm; ghi rõ giới hạn upload demo ≤ 5 MB).
     - Trên host 8 GB RAM, cho phép đặt `onebee_ai_model: "qwen2.5:1.5b"` (hoặc model nhẹ hơn theo `inventory.demo.ini`) nếu `gemma4:e2b-it-qat` phản hồi > 60s trên CPU VPS.
     - Caddy bật rate-limit nhẹ cho `/ai/*` và `/files/*` để tránh người lạ spam bản công khai.
3. **Dữ liệu giả lập & Tự đặt lại mỗi đêm:**
   - Tạo `scripts/nap-du-lieu-demo.sql` (chạy lặp lại được — idempotent): xóa dữ liệu rác cũ, nạp sẵn ~5 đơn hàng (đủ trạng thái `NHAP`, `CHO_DUYET`, `DA_DUYET`, `TU_CHOI`), 3 yêu cầu hỗ trợ, 2 khảo sát, 3 máy trạm mẫu trong `tinh_trang_may`, 2 tệp PDF mẫu `CLEAN` trong SeaweedFS.
   - Cài systemd timer `onebee-demo-reset.timer` chạy lúc `03:00` hằng ngày gọi script nạp lại dữ liệu demo.

### 9.3. Lệnh kiểm chứng bắt buộc (Giai đoạn 9)
Từ máy tính cá nhân bên ngoài mạng (hoặc GitHub Actions):
1. `curl -fsSI https://<tên-miền>/` → trả `200 OK`, chứng chỉ TLS hợp lệ (không tự ký).
2. `nc -zv -w 3 <ip-host> 5432 11434 1880 8333` → đều bị từ chối/timeout (port nội bộ đã đóng).
3. `curl -s -o /dev/null -w "%{http_code}" https://<tên-miền>/api/don_hang` → trả `401` (hoặc `302` tới `/dangnhap/`).
4. Thử tay trọn vòng trên trình duyệt: đăng nhập `nhanvien1` → tạo đơn + đính kèm tệp → chờ `CLEAN` → đăng nhập `quanly1` duyệt đơn → vào trang Điều hành `[D]` thấy số liệu tăng → bấm Tóm tắt `[I]` nhận kết quả tiếng Việt.

---

## Giai đoạn 10 — Tài liệu kiến trúc, tự chấm PoF, phát hành và nộp bài *(Trước 03/12)*

- **Nhánh làm việc:** `docs/ho-so-olp-2026` (tách từ `origin/main` sau khi GĐ 1, 6, 9 cơ bản ổn).
- **Mục tiêu:** Giám khảo mở kho mã là chấm ngay **50/50 điểm PoF** (chấm trước chung kết 7–9/12) và có đủ tài liệu thuyết phục cho **50/50 điểm sản phẩm** tại buổi chung kết 10/12.

### 10.1. Bộ tài liệu bắt buộc phải tạo/cập nhật
1. **`docs/kien-truc-dx-os.md`** (dùng **chính xác thuật ngữ của Đề thi**):
   - Sơ đồ **3 tầng**: `Tầng Nền tảng Dịch vụ Lõi số` (Headless PaaS), `Tầng Không gian Năng lực số` (H-P-D-I), `Tầng Nền tảng Kinh doanh số` (định hướng mở rộng).
   - Bảng ánh xạ dịch vụ lõi bắt buộc của Đề thi ↔ Thành phần thực tế của OneBee DX-OS ↔ Giấy phép OSI.
   - **Bảng đối chiếu 4 nguyên lý thiết kế (Mục 4 Đề thi)** — *ghi trung thực cái đã chạy thật vs cái chỉ là định hướng*:
     - **(i) Tách dữ liệu nóng/lạnh:** Đã chạy thật: PostgreSQL OLTP (nóng) vs restic 2 tầng bất biến (lạnh); Định hướng: Lakehouse (Apache Iceberg).
     - **(ii) Hội tụ IT/OT & Bản sao số:** Đã chạy thật: dữ liệu trạng thái máy trạm (`onebee-bao-tinh-trang`) hội tụ về chung CSDL tác nghiệp; Định hướng: cảm biến IoT / NGSI-LD.
     - **(iii) Quản trị dữ liệu & chất lượng:** Đã chạy thật: ràng buộc `CHECK`, phân quyền dòng RLS, PostgREST tự sinh OpenAPI, nhật ký truy vết; Định hướng: OpenMetadata.
     - **(iv) Zero-Trust + GitOps + Kiểm dịch biên mạng:** Đã chạy thật: Caddy `forward_auth` + Authelia + JWT 60s + `clamscan` kiểm dịch tệp tại `/files/` + Ansible idempotent (`changed=0`).
2. **`docs/olp-2026-tu-cham-pof.md`** — Bảng tự chấm chi tiết đủ **6 tiêu chí PoF (50đ)** và **từng dòng trừ điểm trong Thể lệ**, mỗi dòng trỏ thẳng tới **đường dẫn tệp + lệnh kiểm tra thật**:
   - Tiêu chí 1 (5đ): Repo GitHub công khai, web viewer, commit history, issue tracker đang hoạt động.
   - Tiêu chí 2 (10đ): Giấy phép `MIT` ghi trong từng tệp mã, thông báo mục đích giấy phép ở `README.md`, bản sao toàn văn `LICENSE`, 100% thành phần dùng giấy phép OSI (`LICENSES.md`).
   - Tiêu chí 3 (5đ): Có GitHub Release theo phiên bản (`v1.3.0`), định dạng mở `.tar.gz`.
   - Tiêu chí 4 (10đ): Hướng dẫn cài từ mã nguồn (`docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md`), cấu hình qua biến Ansible (`group_vars/all.yml`, không sửa cứng header), dùng công cụ mở chuẩn, **chạy được ngoài thư mục mã nguồn**.
   - Tiêu chí 5 (10đ): Liệt kê rõ thư viện phụ thuộc (`LICENSES.md`, `requirements-dev.txt`), **không phát hành kèm gói/Docker image của dự án khác** trong GitHub Release dự thi, không sửa mã thư viện đính kèm.
   - Tiêu chí 6 (10đ): Bug tracker có issue mở/đóng thật, `CHANGELOG.md` ở gốc repo, `README.md` và tài liệu hướng dẫn khớp 100% thực tế.
3. **`docs/api/openapi-dxos.md` & `ROADMAP.md`:**
   - Mô tả chi tiết các nhóm endpoint `/api/`, `/files/`, `/ai/`, `/quy-trinh/` (tiêu chí 10: công cụ & tài liệu kỹ thuật kèm theo).
   - `ROADMAP.md` nêu định hướng phát triển sau cuộc thi (tiêu chí 10 & 11).
4. **Rà soát tài liệu cài đặt & `README.md`:**
   - Sửa `README.md`: mở đầu định vị rõ **DX-OS Open-Core**, gắn link bản chạy thử công khai `https://<tên-miền>/`, link tới `docs/kien-truc-dx-os.md` và `ROADMAP.md` (hỏi anh Thiện giữ hay bỏ dòng Hội thi Tây Ninh).
   - Cập nhật `docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md` và `docs/huong-dan/quan-ly-may-tram.md` theo đúng các dịch vụ mới (Authelia, PostgreSQL, SeaweedFS, Node-RED, `onebee-ai-rag`).

### 10.2. Kịch bản chung kết 15 phút & Nộp bài
1. **`docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md`** (tổng thời lượng **≤ 15 phút**, đủ 4 phần theo Mục 6 Đề thi):
   - Phần 1 (3 phút): Bài toán doanh nghiệp/HTX & giải pháp kiến trúc 3 tầng DX-OS Open-Core + lựa chọn công nghệ OSI.
   - Phần 2 (3 phút): Tính năng nền tảng lõi chạy ngầm (SSO, API tự sinh RLS, kho tệp kiểm dịch, Node-RED).
   - Phần 3 (7 phút): Live Demo trọn vòng `H → P → D → I` trên bản chạy thử công khai + máy trạm `hoi` (kèm **1 video quay sẵn 3–5 phút** dự phòng mất mạng tại hội trường).
   - Phần 4 (2 phút): Định hướng phát triển & thu hút cộng đồng (`ROADMAP.md`).
2. **`docs/hoi-thi/olp-2026-thu-nop-bai.md`:** Soạn sẵn đúng mẫu thư ở Mục 5 Đề thi (để trống tên đội, 3 thành viên, giảng viên hướng dẫn để anh Thiện điền).
3. **Đóng gói phát hành `v1.3.0` (việc cuối cùng — anh Thiện duyệt tag/release):**
   - Đổi `[Unreleased]` thành `[1.3.0]` trong `CHANGELOG.md`, cập nhật `onebee_version` trong `box/ansible/group_vars/all.yml`.
   - Chạy thử `scripts/dong-goi-ban-phat-hanh.sh 1.3.0` → giải nén sang `/tmp/kiem-ngoai-thu-muc` kiểm thử chạy được ngoài thư mục gốc.
   - **Kiểm tra an toàn PoF:** trên GitHub Release `v1.3.0`, **CHỈ** đính kèm file mã nguồn `.tar.gz` + `SHA256SUMS` do `phat-hanh.yml` sinh ra — **tuyệt đối không** đính kèm gói USB offline chứa Docker image/`.deb` của bên thứ ba (tránh bị trừ 5đ ở tiêu chí 5).
   - Anh Thiện gửi email nộp bài tới `olpvietnam@vaip.vn`, `thuky@vfossa.vn` **trước 17:00 Chủ nhật ngày 06/12/2026**.

### 10.3. Lệnh kiểm chứng bắt buộc (Giai đoạn 10)
```bash
# 1. Không còn dấu vết n8n và Open WebUI trong bộ cài
git grep -il "n8n\|open.webui\|openwebui" -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr' ':!reports'

# 2. Tài liệu kiến trúc dùng đúng tên 3 tầng và đủ 4 nguyên lý
grep -c "Tầng Nền tảng Dịch vụ Lõi số\|Tầng Không gian Năng lực số" docs/kien-truc-dx-os.md
grep -c "Zero-Trust\|hội tụ\|nóng" docs/kien-truc-dx-os.md

# 3. Đóng gói và kiểm tra hoạt động ngoài thư mục nguồn
scripts/dong-goi-ban-phat-hanh.sh 1.3.0
mkdir -p /tmp/kiem-ngoai && tar xzf dist/onebee-os-1.3.0.tar.gz -C /tmp/kiem-ngoai
(cd /tmp/kiem-ngoai/onebee-os-1.3.0 && test -f LICENSE && python3 scripts/chen-giay-phep.py --kiem)
rm -rf dist /tmp/kiem-ngoai
```
