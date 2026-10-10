# Rà soát bảo mật OneBee OS (Desktop + Box) — 10/10/2026

Chế độ **chỉ đọc**: không sửa code. Đọc tĩnh mã nguồn trên nhánh hiện tại (commit `3061a08`), lịch sử git (39 commit),
tra cứu advisory của các image đã ghim. **Không** chạy hệ thống, không quét bằng công cụ (trivy, npm audit…), không thử khai thác thật.

Quy ước:
- **XÁC NHẬN** = thấy trực tiếp trong code (hoặc phiên bản nằm trong dải ảnh hưởng ghi trên advisory chính thức).
- **NGHI NGỜ** = chưa chứng minh được; cần kiểm thêm (ghi rõ cần kiểm gì).
- Mức độ (Cao/Trung/Thấp) là **đánh giá của người rà soát** theo bối cảnh: dịch vụ chỉ mở trong LAN, đơn vị nhỏ, không có người CNTT.
  [Inference] Mức độ là suy luận, không phải điểm CVSS chính thức (trừ khi ghi rõ).
- Cách khai thác mô tả ở mức đủ để hiểu rủi ro, không phải hướng dẫn tấn công.

## 1. Tóm tắt

| ID | Mức | Trạng thái | Vấn đề | Vị trí chính |
|---|---|---|---|---|
| F1 | Cao | XÁC NHẬN | n8n 2.40.7 nằm trong dải ảnh hưởng advisory 30/9/2026 (có lỗi không cần đăng nhập) | `box/ansible/group_vars/all.yml:17` |
| F2 | Trung | XÁC NHẬN | Khóa báo tình trạng dùng chung mọi máy trạm → giả mạo máy khác, lái SSH của Box sang IP khác | `box-n8n/tasks/main.yml:16`, `06-nhan-tinh-trang-may-tram.json.j2:5`, `onebee-box.sh.j2:44,88,98` |
| F3 | Trung | XÁC NHẬN | Mọi dịch vụ web + kho sao lưu chạy HTTP không TLS; cookie n8n không Secure | `docker-compose.yml.j2:38,68,74,116`, `onebee-box.sh.j2:48` |
| F4 | Trung | XÁC NHẬN (thiết kế) | Chiếm Box = root mọi máy trạm + đọc mọi bản sao lưu máy trạm | `quan-ly-tap-trung/tasks/main.yml:136`, `onebee-box-sao-luu.sh.j2:25-31` |
| F5 | Thấp (Trung nếu dùng chung tailnet) | XÁC NHẬN | Tường lửa chỉ lọc cổng mạng chính; card phụ / VPN không lọc | `onebee-tuong-lua:50-52` |
| F6 | Thấp | XÁC NHẬN | Image Docker ghim theo tag, không theo digest; không có quy trình theo dõi CVE image | `group_vars/all.yml:13-19` |
| F7 | Thấp | XÁC NHẬN | `onebee-sao-luu` nạp cấu hình bằng `source` (giá trị bị shell thực thi) | `backup-client/files/onebee-sao-luu:12` |
| F8 | Thấp | XÁC NHẬN | Thư mục chung Samba: 1 tài khoản cho mọi người, không bắt buộc mã hóa | `samba/tasks/main.yml:52-65` |
| F9 | Thấp | XÁC NHẬN | Biểu mẫu n8n: 1 tài khoản Basic chung `nhanvien` | `credentials.json.j2:28-32` |
| F10 | Thấp | XÁC NHẬN | Khóa `hoi` để file 0644 — mọi tài khoản trên máy trạm dùng được | `ai-cli/tasks/main.yml:19-31` |
| F11 | Thấp | XÁC NHẬN | Container chạy root, không `no-new-privileges`/`cap_drop` | `docker-compose.yml.j2` |
| F12 | Thấp | XÁC NHẬN | Open WebUI chưa tắt `ENABLE_COMMUNITY_SHARING` (mặc định bật) | `docker-compose.yml.j2:39-59` |
| F13 | Thấp | XÁC NHẬN | Cài bằng `git clone` + `sudo`, không kiểm chữ ký; GitHub Actions ghim theo tag | `README.md`, `.github/workflows/*.yml` |
| F14 | Thấp | XÁC NHẬN | VNC hỗ trợ từ xa không mã hóa; cho phép cả dải 100.64.0.0/10 | `ho-tro-tu-xa/files/onebee-ho-tro:32,41` |
| S1 | Trung (nếu đúng) | NGHI NGỜ | Trang kết quả "Tóm tắt PDF" có thể hiển thị HTML do AI sinh (XSS qua prompt injection trong PDF) | `03-tom-tat-van-ban.json.j2:37-38` |
| S2 | Thấp–Trung | NGHI NGỜ | Các advisory Open WebUI 27–28/9/2026 khác chưa kiểm dải phiên bản cho v0.11.4 | `group_vars/all.yml:16` |
| S3 | Thấp | NGHI NGỜ | Lọc công thức CSV chưa đủ (bỏ sót `\r`, khoảng trắng đầu ở quy trình đơn hàng) | `_csv-js.j2:2`, `04-nhap-don-hang.json.j2:9` |
| S4 | Thấp | NGHI NGỜ | Tiêu đề email còn ký tự `\r` đơn lẻ từ dữ liệu biểu mẫu | `07-yeu-cau-ho-tro.json.j2:12` |
| S5 | Thấp | NGHI NGỜ | Phiên đăng nhập Open WebUI có thể không hết hạn (chưa đặt `JWT_EXPIRES_IN`) | `docker-compose.yml.j2:39-59` |

Không tìm thấy lỗi injection lệnh/SQL đã xác nhận; không có secret thật trong repo hay lịch sử git (xem mục 4).

## 2. Lỗi đã xác nhận

### F1 — n8n 2.40.7 dính advisory 30/9/2026 · Cao · XÁC NHẬN
- **Bằng chứng:** `box/ansible/group_vars/all.yml:17` ghim `docker.io/n8nio/n8n:2.40.7`; cổng 5678 mở ra LAN
  (`box-stack/templates/docker-compose.yml.j2:68`).
- Advisory chính thức của n8n (đăng 30/9/2026), đã mở từng trang:
  - [GHSA-3qcw-p65v-c7vq](https://github.com/n8n-io/n8n/security/advisories/GHSA-3qcw-p65v-c7vq) — "Unauthenticated Unbounded OAuth Client
    Persistence via the Authorize Endpoint", High, CVSS v4 8.2, **không cần tài khoản**, ảnh hưởng `< 2.41.4`, vá ở 2.41.4 / 2.42.1.
  - [GHSA-29xw-66fq-4xc3](https://github.com/n8n-io/n8n/security/advisories/GHSA-29xw-66fq-4xc3) — Stored XSS qua xem trước file nhị phân,
    High 7.2, cần tài khoản member; ảnh hưởng `< 2.41.4`. Box chỉ có tài khoản chủ → [Inference] khó áp dụng ở cấu hình mặc định.
  - 8 advisory còn lại trong đợt (SQL injection nút MSSQL, Git node, Chat Trigger, Send-and-Wait, MCP…): **chưa mở từng trang để xem dải
    phiên bản**. [Inference] Các quy trình mẫu chỉ dùng nút code/form/formTrigger/webhook/readWriteFile/httpRequest/emailSend/
    extractFromFile/scheduleTrigger → phần lớn nhiều khả năng không chạm tới, nhưng chưa kiểm.
- **Cách khai thác:** máy bất kỳ trong LAN (máy nhân viên nhiễm mã độc, Wi-Fi khách chung mạng) gửi liên tục yêu cầu tới endpoint authorize
  OAuth của n8n → bảng dữ liệu phình ra → n8n chậm/ngừng: mất email báo cáo sao lưu, biểu mẫu hỗ trợ, nhận tình trạng máy trạm.
- **Tác động:** mất sẵn sàng (không lộ dữ liệu theo advisory).

### F2 — Khóa báo tình trạng dùng chung → giả mạo máy trạm · Trung · XÁC NHẬN
- **Bằng chứng:**
  - 1 khóa duy nhất cho cả đơn vị: `box/ansible/roles/box-n8n/tasks/main.yml:16-17` (`tinh-trang-key`); `onebee-box them-may` in cùng
    khóa đó cho mọi máy (`box-stack/templates/onebee-box.sh.j2:44,55`).
  - Quy trình n8n lấy tên máy từ nội dung yêu cầu, không gắn khóa ↔ tên máy:
    `box-n8n/templates/workflows/06-nhan-tinh-trang-may-tram.json.j2:5` (`const ten = String(b.ten …)`), IP cũng do máy gửi lên (`:9`).
  - Box dùng IP này để SSH: `box-fleet/files/onebee-may-tram.py:122-132` (lệnh `kho`) → `onebee-box.sh.j2:88-101`
    với `StrictHostKeyChecking=accept-new` (`:98`).
  - Kiểm tra "đúng máy" (`box-fleet/files/cap-nhat-may-tram.yml:10-21`) đọc `/etc/onebee/may-tram.env` **trên chính máy đích** → máy giả
    tự ghi được file này.
- **Cách khai thác:** người có quyền root trên 1 máy trạm (đọc được `/etc/onebee/may-tram.env`, quyền 0600) — [Inference] ở đơn vị nhỏ
  thường chính nhân viên là tài khoản quản trị đầu tiên của Linux Mint — lấy `TINH_TRANG_KEY` rồi gửi tình trạng mang tên máy khác:
  1. Giấu cảnh báo: báo `bao_mat_cho: 0`, ổ còn trống… cho máy `ketoan-01` → email hằng ngày và `onebee-box may-tram` báo "ỔN".
  2. Lái cập nhật: đặt `ip` của `ketoan-01` thành IP máy kẻ tấn công. Lần `cap-nhat-may` kế tiếp Box SSH tới đó. Nếu Box chưa từng SSH vào
     `ketoan-01`, khóa host của máy giả được ghim dưới tên `ketoan-01` → về sau máy thật bị từ chối (không cập nhật được), kết quả báo
     "Đã cập nhật xong" là giả. [Inference] Khóa riêng của Box không bị lộ (SSH chỉ dùng khóa để ký xác thực).
  3. Gửi vô số tên máy hợp lệ theo regex → mỗi tên 1 file `<ten>.json` → đầy ổ/inode thư mục `tinh-trang-may`.
  4. Không thu hồi được riêng 1 máy: lộ khóa ở 1 máy = phải đổi khóa cho cả đơn vị.
- **Điểm tốt đã có:** IP được kiểm bằng `ipaddress.IPv4Address` trước khi ghi vào inventory → **không** chèn được tham số Ansible.

### F3 — HTTP không TLS cho toàn bộ dịch vụ · Trung · XÁC NHẬN (rủi ro đã chấp nhận trong ADR 0002)
- **Bằng chứng:** Open WebUI `:3000`, n8n `:5678`, Uptime Kuma `:3001`, rest-server `:8000` đều HTTP
  (`docker-compose.yml.j2:38,68,105,116`); `N8N_SECURE_COOKIE: "false"` (`:74`); mật khẩu kho sao lưu nằm trong URL `rest:http://…`
  (`onebee-box.sh.j2:48`); `docs/adr/0002-nen-tang-onebee-box.md:13` ghi "HTTP trong LAN, không TLS ở v0.1".
- **Cách khai thác:** máy trong LAN giả mạo ARP (đứng giữa máy quản trị và Box) → đọc được mật khẩu/phiên của quản trị Open WebUI, chủ n8n,
  Uptime Kuma, tài khoản biểu mẫu `nhanvien`/`kythuat`, mật khẩu HTTP kho sao lưu máy trạm (Basic auth).
  - Phiên chủ n8n → xem mật khẩu SMTP, sửa quy trình (vd quy trình nhận tình trạng ở F2).
  - [Unverified] Quản trị Open WebUI thêm được "Functions" (mã Python chạy trong container Open WebUI) — tính năng có ở các bản Open WebUI
    đã biết, chưa kiểm riêng v0.11.4.
  - Dữ liệu sao lưu restic vẫn mã hóa phía máy trạm → lộ mật khẩu HTTP chỉ cho phép đọc bản mã hóa / đẩy rác làm đầy ổ.

### F4 — Box là điểm tập trung quyền · Trung · XÁC NHẬN (thiết kế)
- **Bằng chứng:** `desktop/ansible/roles/quan-ly-tap-trung/tasks/main.yml:136` `onebee-quantri ALL=(root) NOPASSWD: ALL`;
  Box giữ mật khẩu restic của mọi máy trạm (`/etc/onebee-box/secrets/may-*-repo`, dùng ở `onebee-box-sao-luu.sh.j2:25-31`).
- **Tác động:** ai chiếm được root trên Box (qua F3 + lỗi container, lộ khóa SSH quản trị, v.v.) có root trên mọi máy trạm và đọc được mọi bản
  sao lưu `/home`. Đã có giới hạn tốt: `from="<IP Box>"`, `no-agent-forwarding`, `no-port-forwarding` (`:127`), `AllowUsers onebee-quantri`.

### F5 — Tường lửa chỉ lọc cổng mạng chính · Thấp (Trung nếu dùng chung tailnet) · XÁC NHẬN
- **Bằng chứng:** quy tắc gắn `-i "${ifc}"` (`box-firewall/files/onebee-tuong-lua:50-52`), `ifc` = cổng có đường ra mặc định; Docker mở cổng
  trên `0.0.0.0`. Tài liệu đã ghi (`docs/huong-dan/cai-dat-onebee-box.md:24-25`).
- **Cách khai thác:** Box có card mạng thứ 2 hoặc tham gia Tailscale/WireGuard → mọi máy trên mạng đó vào thẳng mọi dịch vụ.
  [Speculation] Nếu kỹ thuật OneBee dùng **một tailnet chung cho nhiều khách hàng**, máy của khách A thấy được Box của khách B.

### F6 — Image ghim theo tag, chưa có quy trình theo dõi CVE · Thấp · XÁC NHẬN
- `group_vars/all.yml:13-19` ghim theo tag (vd `n8n:2.40.7`), không có `@sha256:`; không có Renovate/Dependabot hay lịch kiểm advisory.
  F1 là ví dụ: image cũ đi 1 đợt vá mà không ai báo. Tag có thể bị đẩy lại nếu registry/tài khoản nhà phát hành bị chiếm.

### F7 — `onebee-sao-luu` nạp cấu hình bằng shell · Thấp · XÁC NHẬN
- `desktop/ansible/roles/backup-client/files/onebee-sao-luu:12`: `. <(grep -E '^RESTIC_(REPOSITORY|PASSWORD)=' … )` → giá trị chứa `$(…)` hoặc
  dấu `` ` `` sẽ được thực thi bằng root. File chỉ root ghi được và mật khẩu sinh ngẫu nhiên chữ+số → rủi ro thấp; vẫn nên đọc như dữ liệu.

### F8 — Samba dùng 1 tài khoản chung, không bắt buộc mã hóa · Thấp · XÁC NHẬN
- `samba/tasks/main.yml:14-20,52-65`: 1 tài khoản `onebee` cho cả đơn vị; không đặt `smb encrypt`/`server min protocol`.
  [Inference] Mặc định Samba trên Ubuntu 24.04 không bắt buộc mã hóa → nội dung file đi trên LAN có thể đọc được khi bị nghe lén (cùng kiểu F3);
  không truy vết được ai xóa/sửa file; lộ 1 mật khẩu = lộ cả thư mục.

### F9 — Biểu mẫu n8n dùng 1 tài khoản chung · Thấp · XÁC NHẬN
- `box-n8n/templates/credentials.json.j2:28-32` — `nhanvien` dùng cho đơn hàng, báo hỗ trợ, tóm tắt PDF, khảo sát; trường "Người báo" tự khai.
  Không phân biệt được ai nhập đơn hàng sai/giả. Mật khẩu 12 ký tự ngẫu nhiên → dò mật khẩu không khả thi [Inference].

### F10 — Khóa `hoi` đọc được bởi mọi tài khoản máy trạm · Thấp · XÁC NHẬN (đã chủ ý)
- `desktop/ansible/roles/ai-cli/tasks/main.yml:19-31` (`/etc/onebee-hoi.conf`, 0644). Khóa chỉ gọi được `/api/chat/completions,/api/models`
  (`docker-compose.yml.j2:52-53`). Mã độc chạy dưới tài khoản người dùng dùng được AI nhân danh máy đó; không lộ dữ liệu người khác [Inference].

### F11 — Container chạy root, chưa khóa thêm · Thấp · XÁC NHẬN
- `docker-compose.yml.j2`: không có `security_opt: [no-new-privileges:true]`, `cap_drop`, `read_only`, `user:` cho caddy/ollama/open-webui/
  uptime-kuma/rest-server. Lỗi RCE trong 1 dịch vụ → dễ leo thang hơn.

### F12 — `ENABLE_COMMUNITY_SHARING` chưa tắt · Thấp · XÁC NHẬN
- Không có biến này trong `docker-compose.yml.j2:39-59`. Advisory
  [GHSA-vpq8-f445-hcq7](https://github.com/open-webui/open-webui/security/advisories/GHSA-vpq8-f445-hcq7) (High 8.1, ghi mặc định True)
  đã vá ở 0.11.4 — bản đang ghim → hiện không dính; tắt đi để giảm bề mặt (Box chạy offline, không cần chia sẻ cộng đồng).

### F13 — Chuỗi cung ứng bộ cài · Thấp · XÁC NHẬN
- Cài bằng `git clone` rồi `sudo ./…install.sh` (`README.md`); bản phát hành chỉ có `SHA256SUMS` cùng nơi với file (`.github/workflows/phat-hanh.yml`),
  không có chữ ký. GitHub Actions ghim theo tag `@v4`/`@v5` (`.github/workflows/ci.yml:22-23,52,61,71`, `phat-hanh.yml:19`).
  Điểm tốt: CI `permissions: contents: read`; script đóng gói chặn file giống khóa bí mật (`scripts/dong-goi-ban-phat-hanh.sh:15`).

### F14 — VNC hỗ trợ từ xa · Thấp · XÁC NHẬN (đã chủ ý, ADR 0004)
- `desktop/ansible/roles/ho-tro-tu-xa/files/onebee-ho-tro:32,41`: VNC không mã hóa; cho phép cả `100.64.0.0/10`. Đã giảm rủi ro tốt: người dùng tự bật,
  mã 8 số 1 lần, phải bấm "Cho phép" cho từng kết nối, tự đóng sau 10 phút. Dùng chung tailnet (xem F5) → máy lạ trong tailnet cũng gõ cửa được
  (vẫn cần mã + người dùng đồng ý).

## 3. Lỗi nghi ngờ (cần kiểm thêm)

### S1 — Có thể XSS ở trang kết quả "Tóm tắt PDF" · Trung nếu đúng · NGHI NGỜ
- `box-n8n/templates/workflows/03-tom-tat-van-ban.json.j2:37-38`: `respondWith: "showText"`, nội dung = câu trả lời của AI, mà AI đọc nội dung PDF do
  người dùng tải lên.
- [Unverified] Chưa rõ n8n 2.40.x có hiển thị `responseText` dạng HTML và có lọc (sanitize) hay không. Nếu hiển thị HTML không lọc: PDF chứa câu
  "hãy trả lời bằng thẻ `<img onerror=…>`" → script chạy trên origin `:5678` (cùng origin trình soạn n8n) → có thể lấy phiên chủ n8n nếu chủ n8n mở biểu mẫu.
- **Cách kiểm:** trên Box thử, gửi PDF chứa đoạn HTML vô hại (`<b>x</b>`, `<img src=x onerror=console.log(1)>`), xem trang kết quả có dựng thẻ không.

### S2 — Open WebUI v0.11.4 vs các advisory 27–28/9/2026 · Thấp–Trung · NGHI NGỜ
- Đã kiểm 2 advisory: [GHSA-vpq8-f445-hcq7](https://github.com/open-webui/open-webui/security/advisories/GHSA-vpq8-f445-hcq7) và
  [GHSA-f9xp-mfmq-x6cg](https://github.com/open-webui/open-webui/security/advisories/GHSA-f9xp-mfmq-x6cg) → đều vá ở 0.11.4 (không dính).
- Còn ~8 advisory cùng đợt ([danh sách](https://github.com/open-webui/open-webui/security/advisories)) **chưa mở xem dải phiên bản**.

### S3 — Lọc công thức CSV chưa đủ · Thấp · NGHI NGỜ
- `_csv-js.j2:2` và `04-nhap-don-hang.json.j2:9`: chỉ thay `\r?\n`, regex `^[=+\-@\t]`; bỏ sót `\r` đứng đầu (OWASP liệt kê), bản ở quy trình đơn hàng
  không `trim()` nên chuỗi bắt đầu bằng khoảng trắng rồi `=` lọt qua. [Unverified] Chưa thử LibreOffice Calc/Excel có hiểu `" =…"` là công thức không.

### S4 — `\r` trong tiêu đề email · Thấp · NGHI NGỜ
- `07-yeu-cau-ho-tro.json.j2:12` đưa `safe(j.loai)` vào subject; `loai` đã bị giới hạn theo danh sách (`:7`) nên khó lợi dụng. [Unverified] nodemailer
  (n8n dùng) nhiều khả năng tự lọc ký tự xuống dòng trong header.

### S5 — Thời hạn phiên Open WebUI · Thấp · NGHI NGỜ
- Chưa đặt `JWT_EXPIRES_IN`. [Unverified] Giá trị mặc định của v0.11.4 chưa tra; nếu phiên không hết hạn thì token bị lộ (F3) dùng được lâu dài.

### Phụ thuộc khác đã tra (không thấy lỗi đang mở)
- Uptime Kuma 2.5.5: advisory mới nhất [GHSA-wf2j-5mc7-5c4w](https://github.com/louislam/uptime-kuma/security/advisories/GHSA-wf2j-5mc7-5c4w)
  (DoS không cần đăng nhập) ảnh hưởng `<= 2.5.3`, vá 2.5.4 → **không dính**.
- Caddy 2.11.4: các bản vá 2.11.x gồm nhiều lỗi FastCGI/forward_auth; Box chỉ dùng `file_server` tĩnh. [Unverified] nguồn thứ cấp.
- Ollama 0.34.4, rest-server 0.14.0: không tìm thấy CVE nào ghi dải phiên bản chứa 2 bản này. [Unverified] chỉ tra nguồn thứ cấp, chưa đối chiếu NVD.
- Gói hệ điều hành (Docker từ kho Ubuntu, Samba, OpenSSH, restic…): cập nhật bằng unattended-upgrades — không đánh giá CVE từng gói.

## 4. Đã kiểm, không thấy vấn đề
- **Secret trong repo:** quét toàn bộ lịch sử git (39 commit) theo mẫu khóa riêng/token/mật khẩu → chỉ có giá trị giả trong test
  (`tests/desktop/run-desktop-extended-tests.sh:53`). `.gitignore` chặn `.env`. Mọi khóa sinh lúc cài, lưu `/etc/onebee-box/secrets` (0700), `.env` 0600.
- **Injection:** tên máy kiểm regex ở cả Box (`onebee-box.sh.j2:34,79`) lẫn n8n; IP kiểm bằng `ipaddress`; `htpasswd -i` qua stdin; biến shell đều
  được đặt trong ngoặc kép; không có SQL tự viết; n8n tắt nút chạy lệnh/SSH, chặn đọc biến môi trường, giới hạn thư mục file (`docker-compose.yml.j2:81-83`).
- **Xác thực:** tài khoản quản trị Open WebUI/n8n/Uptime Kuma tạo sẵn, tắt đăng ký tự do; Uptime Kuma chỉ mở ra LAN sau khi có tài khoản; Ollama không mở cổng;
  khóa API Open WebUI giới hạn endpoint; webhook nội bộ có header key; rest-server `--private-repos --append-only`; SSH Box/máy trạm chỉ dùng khóa,
  không root, `MaxAuthTries 3`.
- **XSS trang tĩnh:** `index.html.j2` chỉ dùng `textContent`/`href` từ `location.hostname`; `demo/index.html` thoát ký tự lệnh người dùng (`escapeHtml`).
- **PPA ibus-bamboo:** khóa ký lưu sẵn, ghim ưu tiên chỉ cho gói `ibus-bamboo` (`vietnamese/tasks/ibus-bamboo.yml`).

## 5. Kế hoạch vá theo thứ tự ưu tiên (chờ duyệt — CHƯA sửa code)

Mỗi bước: sửa → chạy kiểm tự động hiện có (`tests/box/run-box-test-in-systemd-container.sh`, `tests/desktop/*`, unit test, lint) → cập nhật
`docs/project-changelog.md` (+ ADR khi đổi thiết kế).

### Ưu tiên 0 — làm ngay
1. **F1 · Nâng n8n ≥ 2.41.4** (`box/ansible/group_vars/all.yml:17`).
   - Mở hết 10 advisory 30/9/2026 xác nhận bản đích đã vá; đọc ghi chú phát hành 2.40 → 2.41 (đổi tên biến môi trường, CLI `import:*`/`publish:workflow`).
   - Kiểm: test Box (nhập quy trình, biểu mẫu, webhook tình trạng, email thử).
2. **F2 · Khóa tình trạng riêng từng máy + ghim khóa host SSH.**
   - Box: `them-may` sinh `may-<ten>-tinh-trang`; ghi bảng `ten → sha256(khóa)` vào thư mục n8n đọc được (vd `tinh-trang-may/.khoa.json`, quyền uid 1000).
   - n8n (quy trình 06): đọc bảng, so khóa trong header với `ten` trong nội dung; tên chưa cấp → từ chối (hết tạo file tùy ý).
   - Box: bỏ `StrictHostKeyChecking=accept-new`; ghim khóa host lúc cấp máy (máy trạm in vân tay khóa host khi cài, quản trị dán vào lệnh mới trên Box,
     hoặc `cap-nhat-may` lần đầu hỏi xác nhận vân tay).
   - Tương thích: máy trạm cũ còn khóa chung → giai đoạn chuyển tiếp nhận cả 2, in cảnh báo; tài liệu `quan-ly-may-tram.md`.
   - Kiểm: thêm test Box — gửi tình trạng tên máy khác bằng khóa của máy A phải bị từ chối; `cap-nhat-may` tới IP có khóa host lạ phải dừng.

### Ưu tiên 1 — trước khi phát hành 1.0.0
3. **F3 · TLS trong LAN** (đổi ADR 0002).
   - Caddy làm cổng duy nhất: `tls internal` (CA riêng mỗi Box) cho Open WebUI, n8n, Uptime Kuma, rest-server; container chỉ mở trong mạng Docker
     (bỏ `0.0.0.0:` ở `docker-compose.yml.j2`); `N8N_SECURE_COOKIE=true`, `WEBHOOK_URL=https://…`.
   - Máy trạm: bộ cài Desktop cài chứng chỉ CA của Box (kèm vân tay trong `may-tram.env` để kiểm); `hoi`, `onebee-bao-tinh-trang`, restic dùng `https`
     (restic `--cacert`).
   - Rủi ro: đổi URL người dùng quen dùng, trình duyệt cần tin CA (Firefox có kho riêng) → làm có giai đoạn chuyển tiếp.
4. **F6 · Theo dõi CVE image:** ghim thêm digest (`image:tag@sha256:…`), thêm Renovate (regex manager cho `group_vars/all.yml`) hoặc lịch kiểm advisory
   hằng tháng ghi vào `docs/`; ghim GitHub Actions theo SHA (F13).
5. **S1 · Kiểm XSS trang tóm tắt** (xem cách kiểm ở S1). Nếu dính: chuyển `respondWith` sang dạng chữ thuần hoặc thoát HTML câu trả lời trong nút Code trước khi hiển thị.
6. **S2 · Đối chiếu nốt advisory Open WebUI**; tắt `ENABLE_COMMUNITY_SHARING` (F12); đặt `JWT_EXPIRES_IN` (S5, vd `7d`).
7. **F5 · Tường lửa:** lọc theo dải nguồn trên mọi cổng mạng trừ `lo`/`docker*` (hoặc liệt kê cổng tin cậy rõ ràng); tài liệu: mỗi khách hàng 1 tailnet
   hoặc ACL Tailscale chỉ cho máy kỹ thuật vào Box của khách đó.

### Ưu tiên 2 — tăng cứng
8. **F4 · Thu hẹp quyền Box trên máy trạm:** thay `NOPASSWD: ALL` bằng 1 lệnh cố định (`/usr/local/sbin/onebee-cap-nhat`: apt update/dist-upgrade/flatpak/
   báo tình trạng) + `command=` trong `authorized_keys`; `cap-nhat-may` gọi lệnh đó qua SSH thay vì Ansible. Đánh đổi: mất linh hoạt của Ansible → cần quyết định.
9. **F11 · Khóa container:** `no-new-privileges`, `cap_drop: [ALL]` cho dịch vụ không cần (portal, rest-server), `read_only` khi được; thử từng dịch vụ.
10. **F8 · Samba:** `server min protocol = SMB3`, `smb encrypt = required` cho thư mục chung (kiểm máy Windows còn sót trong đơn vị);
    cân nhắc tài khoản riêng từng người.
11. **F7 · `onebee-sao-luu`:** đọc `RESTIC_*` bằng `while IFS='=' read` (không `source`), giống cách `onebee-bao-tinh-trang` đã làm.
12. **S3/S4 · CSV, email:** thêm `\r` vào regex, `trim()` thống nhất (dùng chung `_csv-js.j2` cho quy trình 04), thay mọi `[\r\n]` trong subject.
13. **F9 · Biểu mẫu:** (tùy chọn) tài khoản riêng từng phòng/người, ghi tên tài khoản đăng nhập vào CSV.
14. **F13 · Phát hành:** ký tag/bản phát hành (minisign/cosign hoặc tag GPG), hướng dẫn kiểm chữ ký trước khi `sudo`.

## 6. Câu hỏi chưa giải quyết
- Nhân viên ở đơn vị có quyền `sudo` trên máy trạm của mình không? (quyết định mức độ thật của F2, F10).
- Kỹ thuật OneBee dùng 1 tailnet chung cho mọi khách hàng hay mỗi khách 1 tailnet? (F5, F14).
- Có chấp nhận đổi sang HTTPS (F3) trong 1.0.0 không, hay giữ HTTP và ghi rõ rủi ro trong hợp đồng/tài liệu?
- F4: giữ Ansible + `NOPASSWD: ALL` hay chuyển sang lệnh cố định?
- n8n 2.41 có thay đổi phá vỡ nào với CLI nhập quy trình (`import:credentials`, `publish:workflow`) không — cần chạy test Box thật để biết.
