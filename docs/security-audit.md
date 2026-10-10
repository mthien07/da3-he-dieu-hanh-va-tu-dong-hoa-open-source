# Rà soát bảo mật OneBee OS (Desktop + Box)

- **Bản 1 — 10/10/2026:** đọc tĩnh mã nguồn tại commit `3061a08`, lịch sử git (39 commit), tra advisory của các image đã ghim.
- **Bản 2 — 10/10/2026:**
  - Đưa vào 4 quyết định của chủ dự án (mục 0).
  - Tra cứu sâu hơn bằng 9 agent chạy song song, chỉ đọc: mở từng advisory, đọc mã nguồn n8n/Open WebUI/Caddy, lập danh sách mọi chỗ trong repo phải sửa.
  - 2 vòng phản biện kế hoạch: một soi chỗ làm hỏng hoặc bỏ sót, một soi lỗ hổng trong chính thiết kế.
  - Người viết đã tự kiểm lại 4 khẳng định có ảnh hưởng lớn nhất trên mã nguồn gốc (đánh dấu ✔). Các khẳng định khác ghi "(agent)": agent đã đọc nguồn gốc, người viết chưa tự kiểm lại.

Chế độ **chỉ đọc**: chưa sửa code.
- **Không** chạy hệ thống, không quét bằng công cụ (trivy, npm audit…), không thử khai thác thật.

Quy ước:
- **XÁC NHẬN** = thấy trực tiếp trong code, hoặc phiên bản nằm trong dải ảnh hưởng ghi trên advisory chính thức.
- **NGHI NGỜ** = chưa chứng minh được.
- Mức độ (Cao/Trung/Thấp) là đánh giá của người rà soát theo bối cảnh: dịch vụ chỉ mở trong LAN, đơn vị nhỏ, không có người CNTT.
  - [Inference] Đây là suy luận, không phải điểm CVSS chính thức (trừ khi ghi rõ).
- Cách khai thác chỉ mô tả đủ để hiểu rủi ro.

## 0. Quyết định của chủ dự án (10/10/2026)

| # | Quyết định | Ảnh hưởng |
|---|---|---|
| QĐ1 | Nhân viên **không** có sudo trên máy trạm; chỉ quản trị/quản lý có | F2, F7, F10. Lưu ý N7: code và tài liệu hiện chưa bảo đảm điều này |
| QĐ2 | Mỗi khách hàng một tailnet riêng | F5, F14 |
| QĐ3 | Đưa HTTPS vào | F3 → Pha 3–4 |
| QĐ4 | Giữ Ansible + `onebee-quantri ALL=(root) NOPASSWD: ALL` | F4 = rủi ro chấp nhận |

## 1. Tóm tắt (bản 2)

| ID | Mức (cũ → mới) | Trạng thái | Vấn đề | Vị trí chính | Pha vá |
|---|---|---|---|---|---|
| F1 | Cao → **Trung** | XÁC NHẬN | n8n 2.40.7: dòng 2.40.x đã ngừng vá. 14 advisory ngày 30/9 không cái nào khai thác được ở cấu hình mặc định, trừ khả năng GHSA-29xw | `box/ansible/group_vars/all.yml:17` | 1 |
| F2 | Trung → Trung (giữ) | XÁC NHẬN | Khóa báo tình trạng dùng chung, gửi mỗi giờ qua HTTP → giả mạo máy khác, lái SSH của Box sang IP khác | `box-n8n/tasks/main.yml:16`, `06-nhan-tinh-trang-may-tram.json.j2:5,9`, `onebee-box.sh.j2:44,88,98` | 2 |
| F3 | Trung | XÁC NHẬN, đang vá (QĐ3) | HTTP không TLS cho mọi dịch vụ; cookie n8n không Secure | `docker-compose.yml.j2:38,68,74,116` | 3–4, 4b |
| F4 | Trung | **CHẤP NHẬN** (QĐ4) | Chiếm Box = root mọi máy trạm + đọc mọi bản sao lưu máy trạm | `quan-ly-tap-trung/tasks/main.yml:136` | kiểm soát bù 5.8 |
| F5 | Thấp (Trung nếu chung tailnet) → **Thấp** | XÁC NHẬN | Tường lửa chỉ lọc cổng mạng chính; `tailscale0` và card phụ không lọc | `onebee-tuong-lua:50-52` | 5 |
| F6 | Thấp | XÁC NHẬN | Image ghim theo tag; tag `caddy:2.11.4` đã bị đẩy lại ngày 23/9 (agent) | `group_vars/all.yml:13-19` | 1, 5 |
| F7 | Thấp | XÁC NHẬN | `onebee-sao-luu` nạp cấu hình bằng `source` | `backup-client/files/onebee-sao-luu:12` | 4 |
| F8 | Thấp | XÁC NHẬN | Samba: 1 tài khoản chung, không bắt buộc mã hóa | `samba/tasks/main.yml:52-65` | 5 |
| F9 | Thấp | XÁC NHẬN | Biểu mẫu n8n: 1 tài khoản Basic chung `nhanvien` (cũng là đường tải file của GHSA-29xw) | `credentials.json.j2:28-32` | 5 |
| F10 | Thấp → **CHẤP NHẬN** | XÁC NHẬN | Khóa `hoi` 0644 — chấp nhận vì khóa chỉ gọi được 2 endpoint (không dựa vào QĐ1) | `ai-cli/tasks/main.yml:19-31` | — |
| F11 | Thấp | XÁC NHẬN | Container chạy root, không `no-new-privileges`/`cap_drop` | `docker-compose.yml.j2` | 4 (Caddy), 5 |
| F12 | Thấp | XÁC NHẬN | `ENABLE_COMMUNITY_SHARING` bật; cài đặt lưu trong CSDL → biến môi trường không đổi được Box đã cài (agent) | `onebee-webui.py:25-26` | 1 |
| F13 | Thấp | XÁC NHẬN | Bộ cài không ký; GitHub Actions ghim theo tag | `README.md`, `.github/workflows/*.yml` | 5 |
| F14 | Thấp → **Thấp, chấp nhận** | XÁC NHẬN | VNC không mã hóa; dải 100.64/10 giờ chỉ còn tailnet của khách đó (QĐ2) | `onebee-ho-tro:32,41` | 5 (ACL) |
| S1 | Trung nếu đúng → **Thấp** | **XÁC NHẬN ✔, bị sandbox chặn** | Trang "Tóm tắt PDF" in HTML thô do AI sinh; CSP `sandbox` không có `allow-same-origin` → không lấy được phiên chủ n8n | `03-tom-tat-van-ban.json.j2:37-38` | 1 |
| S2 | Thấp–Trung → **ĐÓNG** | Không dính (agent) | Cả 26 advisory Open WebUI tháng 9 đều đã vá ở ≤ 0.11.4 | `group_vars/all.yml:16` | theo dõi |
| S3 | Thấp | NGHI NGỜ | Lọc công thức CSV chưa đủ | `_csv-js.j2:2`, `04-nhap-don-hang.json.j2:9` | 5 |
| S4 | Thấp | NGHI NGỜ | `\r` trong tiêu đề email | `07-yeu-cau-ho-tro.json.j2:12` | 5 |
| S5 | Thấp | **XÁC NHẬN** (agent) | Phiên Open WebUI sống 4 tuần (`JWT_EXPIRES_IN=4w`); không thu hồi được vì không có Redis | `docker-compose.yml.j2:39-59` | 1 |
| N1 | Thấp (khuếch đại F3) | XÁC NHẬN (agent) | Open WebUI bật sẵn `ENABLE_PLUGINS` → lấy được phiên quản trị = chạy Python trong container (root) | `docker-compose.yml.j2:39-59` | 1 |
| N2 | Thấp | XÁC NHẬN (agent) | n8n từ 2.41.1 bật sẵn mô-đun Agents (Box không dùng) — phát sinh khi nâng cấp | — | 1 |
| N3 | Thấp | XÁC NHẬN | IP Box tính 2 cách có thể lệch (Ansible `ansible_default_ipv4` vs shell `ip route get`) — quan trọng khi IP nằm trong chứng chỉ | `docker-compose.yml.j2:85`, `onebee-box-common.sh.j2:28-31` | 3 |
| N4 | Thấp | XÁC NHẬN ✔ | Tài liệu sai: khi "HOST IDENTIFICATION HAS CHANGED" bảo chạy lại `them-may`, nhưng lệnh này không đụng `known_hosts` | `docs/huong-dan/quan-ly-may-tram.md:39-40` | 1 |
| N5 | Thấp | XÁC NHẬN (agent) | Caddyfile gắn vào container kiểu từng file → `caddy reload` không thấy bản mới (Ansible ghi bằng đổi tên file) | `docker-compose.yml.j2:20` | 3 |
| N6 | Thấp | XÁC NHẬN | `onebee-kuma.js` chỉ thêm theo dõi khi chưa có tên đó → đổi URL theo dõi không có hiệu lực trên Box đã cài | `onebee-kuma.js:41-42` | 4 |
| N7 | **Trung** (vì F2/F7/F10 dựa vào QĐ1) | XÁC NHẬN ✔ | QĐ1 chưa được bảo đảm: tài liệu bảo giao tài khoản mẫu (tài khoản tạo lúc cài Mint, [Inference] có sudo) cho nhân viên; code không kiểm nhóm sudo | `docs/huong-dan/cai-hang-loat.md:51`, `desktop/` (không có kiểm tra) | 1 |

Vẫn không thấy lỗi injection lệnh hay SQL, không có secret thật trong repo hay lịch sử git (mục 4).

## 2. Lỗi đã xác nhận

### F1 — n8n 2.40.7 · Trung (bản 1: Cao) · XÁC NHẬN
- **Bằng chứng:** `box/ansible/group_vars/all.yml:17` ghim `n8nio/n8n:2.40.7`; cổng 5678 mở ra LAN (`docker-compose.yml.j2:68`).
- **Bản 2 — sửa nhận định của bản 1:**
  - [GHSA-3qcw-p65v-c7vq](https://github.com/n8n-io/n8n/security/advisories/GHSA-3qcw-p65v-c7vq) (DoS không cần đăng nhập, High 8.2): ✔ mã nguồn 2.40.7 chỉ ghi bản ghi OAuth khi tài nguyên là "first-party". Form Trigger chỉ là first-party khi `authentication === 'n8nUserAuth'` (`form-trigger-resource.resolver.ts`, `oauth-server.service.ts`).
    - Mọi biểu mẫu của Box dùng `basicAuth` (`03:20, 04:24, 07:24, 08:19, 09:21`) → **hiện không khai thác được**.
    - Bản 1 ghi "Cao, không cần đăng nhập" là đánh giá quá cao.
  - Đợt 30/9 có **14** advisory (không phải 10). Agent đã mở từng trang: chỉ [GHSA-29xw-66fq-4xc3](https://github.com/n8n-io/n8n/security/advisories/GHSA-29xw-66fq-4xc3) có thể xảy ra.
    - Cơ chế: XSS qua xem trước file nhị phân, High 7.2.
    - Đường đi [Inference]: ai giữ mật khẩu chung `nhanvien` tải file lên biểu mẫu tóm tắt PDF, sau đó chủ n8n mở xem trước file nhị phân trong lịch sử chạy.
  - Dòng 2.40.x dừng ở 2.40.7; bản vá chỉ ra cho 2.41.4+, 2.42.1+, 1.123.83 (agent). Từ 6/10 chỉ 2.42.x và 2.43.x còn nhận bản vá.
- **Tác động:** hiện thấp. Lý do vẫn để Trung: chạy dòng đã ngừng vá, và chỉ cần thêm 1 biểu mẫu `n8nUserAuth` là lỗi DoS khai thác được ngay.

### F2 — Khóa báo tình trạng dùng chung → giả mạo máy trạm · Trung · XÁC NHẬN
- **Bằng chứng:**
  - 1 khóa cho cả đơn vị: `box-n8n/tasks/main.yml:16-17`.
  - `them-may` in cùng khóa đó cho mọi máy: `onebee-box.sh.j2:44,55`.
  - Quy trình 06 lấy tên máy và IP từ nội dung yêu cầu (`06-nhan-tinh-trang-may-tram.json.j2:5,9`).
  - Box SSH tới IP đó (`onebee-may-tram.py:122-132` → `onebee-box.sh.j2:88-101`) với `StrictHostKeyChecking=accept-new` (`:98`).
  - Kiểm tra "đúng máy" (`cap-nhat-may-tram.yml:10-21`) đọc file trên chính máy đích → máy giả tự trả lời được.
- **Ai lấy được khóa:**
  - Người có root trên một máy trạm (theo QĐ1 là quản trị viên, người được tin — nhưng xem N7).
  - **Hoặc** bất kỳ ai nghe lén LAN: khóa đi dạng rõ trong header `X-OneBee-Key` mỗi giờ (F3).
- **Khai thác:**
  1. Giấu cảnh báo (bản vá, ổ đầy) của máy khác.
  2. Đặt IP của máy khác thành máy kẻ tấn công. Với máy chưa từng SSH, khóa host giả được ghim → máy thật bị từ chối cập nhật về sau.
  3. Tạo vô số file `<tên>.json` → đầy ổ.
  4. Không thu hồi được riêng một máy.
- **Vì sao giữ Trung sau QĐ1:** đường nghe lén vẫn còn tới khi có HTTPS. Kênh đẩy cấu hình dự kiến dùng cho đợt chuyển HTTPS (`dong-bo-may`) sẽ khuếch đại F2 nếu không vá F2 trước (mục 5.3). Hạ xuống Thấp sau Pha 2 + Pha 4.
- **Điểm tốt:** IP được kiểm bằng `ipaddress.IPv4Address` → không chèn được tham số Ansible.

### F3 — HTTP không TLS · Trung · XÁC NHẬN (đang vá theo QĐ3)
- **Bằng chứng:** Open WebUI `:3000`, n8n `:5678`, Uptime Kuma `:3001`, rest-server `:8000` đều HTTP (`docker-compose.yml.j2:38,68,105,116`); `N8N_SECURE_COOKIE: "false"` (`:74`); mật khẩu kho trong URL `rest:http://…` (`onebee-box.sh.j2:48`).
- **Khai thác:** giả mạo ARP trong LAN → đọc mật khẩu và phiên của quản trị Open WebUI, chủ n8n, Uptime Kuma, tài khoản biểu mẫu, mật khẩu HTTP kho sao lưu, khóa `hoi`, khóa tình trạng.
- **Bản 2 (agent, đọc mã Open WebUI v0.11.4):**
  - `ENABLE_PLUGINS` mặc định True (N1) → phiên quản trị bị lộ = tạo được Function = Python chạy phía máy chủ trong container (root). Bản 1 ghi [Unverified]; nay xác nhận.
  - JWT sống 4 tuần, không thu hồi được (S5).
- Restic vẫn mã hóa phía máy trạm → lộ mật khẩu HTTP chỉ cho đọc bản mã hóa hoặc đẩy rác làm đầy ổ.

### F4 — Box là điểm tập trung quyền · Trung · CHẤP NHẬN (QĐ4)
- `quan-ly-tap-trung/tasks/main.yml:136` `NOPASSWD: ALL`; Box giữ mật khẩu restic mọi máy (`onebee-box-sao-luu.sh.j2:25-31`).
- Chiếm root Box = root mọi máy trạm, đọc mọi bản sao lưu, và (sau Pha 3) cài được CA bất kỳ lên máy trạm.
- Giới hạn đã có: `from="<IP Box>"`, không forwarding, `AllowUsers onebee-quantri`. Kiểm soát bù: mục 5.8.

### F5 — Tường lửa chỉ lọc cổng mạng chính · Thấp · XÁC NHẬN
- Quy tắc gắn `-i "${ifc}"` (`onebee-tuong-lua:50-52`); Docker mở cổng trên `0.0.0.0`; tài liệu đã ghi (`cai-dat-onebee-box.md:24-25`).
- Theo QĐ2, tailnet chỉ gồm máy của khách đó + máy kỹ thuật. Nhưng tailnet mới mặc định cho mọi máy nói chuyện với nhau, và khách có thể thêm thiết bị cá nhân. Vì vậy vẫn sửa code (Pha 5), không chỉ ghi tài liệu.

### F6 — Image ghim theo tag · Thấp · XÁC NHẬN
- `group_vars/all.yml:13-19` không có `@sha256:`; không có Renovate hay lịch kiểm advisory.
- (agent) Docker Hub cho thấy `caddy:2.11.4` được đẩy lại ngày 23/9/2026 → tag không cố định.

### F7 — `onebee-sao-luu` nạp cấu hình bằng shell · Thấp · XÁC NHẬN
- `backup-client/files/onebee-sao-luu:12`: `. <(grep …)` → giá trị chứa `$(…)` sẽ được thực thi bằng root. Chỉ root ghi được file (QĐ1) → không leo quyền được; sửa cho sạch ở Pha 4.

### F8 — Samba · Thấp · XÁC NHẬN
- `samba/tasks/main.yml:14-20,52-65`: 1 tài khoản `onebee`; không đặt `smb encrypt`/`server min protocol`.
- (agent) Trên Samba 4.19, `server min protocol = SMB3` nghĩa là **chỉ** 3.1.1 → dùng `SMB3_00` nếu cần cho Windows 8.1.

### F9 — Biểu mẫu n8n dùng 1 tài khoản chung · Thấp · XÁC NHẬN
- `credentials.json.j2:28-32`. Không phân biệt người nhập. Đây cũng là đường tải file của GHSA-29xw (F1).

### F10 — Khóa `hoi` đọc được bởi mọi tài khoản máy trạm · CHẤP NHẬN
- `ai-cli/tasks/main.yml:19-31` (0644). Khóa chỉ gọi được `/api/chat/completions,/api/models` (`docker-compose.yml.j2:52-53`).
- Nhân viên chính là người dùng `hoi`. Chấp nhận vì phạm vi khóa hẹp, **không** phải vì QĐ1 (F10 là chuyện mã độc chạy dưới tài khoản thường, sudo không liên quan).

### F11 — Container chạy root · Thấp · XÁC NHẬN
- Không có `no-new-privileges`, `cap_drop`, `read_only`, `user:`.

### F12 — `ENABLE_COMMUNITY_SHARING` · Thấp · XÁC NHẬN
- Advisory [GHSA-vpq8-f445-hcq7](https://github.com/open-webui/open-webui/security/advisories/GHSA-vpq8-f445-hcq7) (High 8.1) đã vá ở 0.11.4.
- (agent) Cài đặt này lưu trong CSDL: phải đặt qua `ADMIN_CONFIG` trong `onebee-webui.py`, biến môi trường chỉ có tác dụng với bản cài mới.

### F13 — Chuỗi cung ứng bộ cài · Thấp · XÁC NHẬN
- `git clone` + `sudo`; `SHA256SUMS` cùng nơi với file, không chữ ký; Actions ghim `@v4`/`@v5`.

### F14 — VNC hỗ trợ từ xa · Thấp, chấp nhận
- `onebee-ho-tro:32,41`. Người dùng tự bật, mã 1 lần, bấm "Cho phép" từng kết nối, tự đóng sau 10 phút. QĐ2 thu hẹp dải 100.64/10 về tailnet của chính khách.

### S1 — HTML thô ở trang "Tóm tắt PDF" · Thấp · XÁC NHẬN ✔ (bị sandbox chặn)
- ✔ `formCompletionUtils.ts` (n8n 2.40.7): `responseText` **không** qua `sanitizeHtml`; template in `{{{responseText}}}` (triple-stash = HTML thô). `completionMessage` (kiểu `text`) thì có `sanitizeHtml`.
- ✔ Cùng file: đặt `Content-Security-Policy: getHtmlSandboxCSP()` khi `respondWith !== 'redirect'`.
  - (agent) Giá trị CSP là `sandbox allow-scripts …`, **không** có `allow-same-origin` → script chạy ở origin rỗng.
  - (agent) Cookie `n8n-auth` là httpOnly; CORS không cho kèm credentials.
  - → **Không** lấy được phiên chủ n8n. Giả thuyết của bản 1 bị bác.
- Còn lại: PDF có lệnh giấu khiến AI sinh HTML → lừa đảo, giả nội dung trên một URL người dùng tin, gửi nội dung trang ra ngoài. Cần cả PDF độc lẫn model làm theo.
- Mã này giống hệt từ 2.40.7 tới 2.43.0 → nâng n8n không sửa được S1.

### S5 — Thời hạn phiên Open WebUI · Thấp · XÁC NHẬN (agent)
- `JWT_EXPIRES_IN` mặc định `4w`; không có Redis → đăng xuất hay đổi mật khẩu không thu hồi được token.
- Cài đặt lưu trong CSDL (đặt qua `ADMIN_CONFIG`).

### N1–N7 — phát hiện mới ở bản 2
- **N1:** xem F3. Box không dùng Functions/Tools: Trợ lý đặt `builtin_tools: False` (`onebee-webui.py:113-118`).
- **N2:** (agent) PR #39328, có từ 2.41.1. Tắt bằng `N8N_DISABLED_MODULES=agents`.
- **N3:** `WEBHOOK_URL` và link email quy trình 07 dùng `ansible_default_ipv4`; `them-may` dùng `ip -4 route get 1.1.1.1`. Hai cách có thể ra 2 IP khác nhau (nhiều card mạng).
- **N4:** ✔ `quan-ly-may-tram.md:39-40` hướng dẫn sai; cách đúng nằm ở thông báo của `cap-nhat-may` (`onebee-box.sh.j2:104-105`: `ssh-keygen -R`).
- **N5:** (agent) Ansible ghi file mới bằng đổi tên → container vẫn thấy inode cũ.
- **N6:** `coSan.includes(m.name)` → giữ theo dõi cũ khi đổi URL.
- **N7:** ✔ `cai-hang-loat.md:51` "máy mẫu có sẵn tài khoản → đổi mật khẩu từng máy (`passwd`) hoặc tạo tài khoản riêng".
  - Không có bước nào tách tài khoản quản trị khỏi tài khoản nhân viên.
  - `desktop/` không kiểm nhóm `sudo`.
  - [Inference] Tài khoản tạo lúc cài Mint mặc định có sudo.

## 3. Lỗi nghi ngờ còn lại
- **S3 — CSV:** `_csv-js.j2:2`, `04-nhap-don-hang.json.j2:9` bỏ sót `\r` đầu chuỗi; quy trình 04 không `trim()`. [Unverified] Calc/Excel có hiểu `" =…"` là công thức không.
- **S4 — `\r` trong tiêu đề email:** `07-yeu-cau-ho-tro.json.j2:12`; `loai` đã giới hạn theo danh sách (`:7`). [Unverified] nodemailer nhiều khả năng tự lọc.

### Phụ thuộc đã tra (bản 2, agent, trang advisory gốc)
| Thành phần | Đang ghim | Mới nhất | Kết luận |
|---|---|---|---|
| n8n | 2.40.7 | 2.42.6 (stable), 2.43.x (beta) | Dòng 2.40 ngừng vá → nâng (F1) |
| Open WebUI | v0.11.4 | v0.11.4 | Không dính advisory nào tháng 8–9 (S2 đóng). Ghi chú phát hành nói một số bản vá có thể công bố muộn → theo dõi |
| Uptime Kuma | 2.5.5 | 2.5.6 (chỉ cập nhật phụ thuộc) | Không dính; GHSA-wf2j ảnh hưởng ≤ 2.5.3 |
| Caddy | 2.11.4 | 2.11.7 | Không dính khi chỉ phục vụ file tĩnh. 2.11.6+ đổi timeout mặc định → thử trước khi nâng (Pha 4) |
| rest-server | 0.14.0 | 0.14.0 | Repo không có advisory. Image build 5/2025 (Go/x-crypto cũ) → nên quét image |
| Ollama | 0.34.4 | 0.40.2 | Không có advisory trên repo. Các CVE 2026 (nguồn thứ cấp) đều dưới 0.34. Bản 0.40 tự chuyển định dạng model → nâng có kế hoạch |

## 4. Đã kiểm, không thấy vấn đề
- **Secret trong repo:** cả lịch sử git chỉ có giá trị giả trong test; `.gitignore` chặn `.env`; khóa sinh lúc cài, lưu `/etc/onebee-box/secrets` (0700), `.env` 0600.
- **Injection:** tên máy kiểm regex (`onebee-box.sh.j2:34,79` và n8n); IP kiểm bằng `ipaddress`; `htpasswd -i` qua stdin; biến shell trong ngoặc kép; không có SQL tự viết.
  - n8n tắt nút chạy lệnh/SSH, chặn đọc env, giới hạn thư mục file.
- **Xác thực:** tài khoản quản trị tạo sẵn, tắt đăng ký; Ollama không mở cổng; khóa API giới hạn endpoint; rest-server `--private-repos --append-only`; SSH chỉ khóa, không root.
- **Biểu mẫu kiểu `text`** (quy trình 04/07/08/09): (agent) đi qua sanitize-html, không còn đường script.
- **XSS trang tĩnh:** `index.html.j2` chỉ dùng `textContent`/`href`; `demo/index.html` thoát ký tự lệnh.
- **PPA ibus-bamboo:** khóa ký lưu sẵn, ghim ưu tiên chỉ cho gói `ibus-bamboo`.

## 5. Kế hoạch vá — bản 2 (chờ duyệt, CHƯA sửa code)

### 5.0 Quy ước chung
- Mỗi pha phát hành riêng được. Nâng cấp = chạy lại bộ cài; lần chạy thứ 2 phải ra `changed=0`.
- Mỗi pha: sửa → `tests/box/run-box-test-in-systemd-container.sh`, `tests/desktop/*`, unit test, lint → `docs/project-changelog.md` (+ ADR khi đổi thiết kế).
- **Test mới dùng chung:**
  - Test nâng cấp: cài commit cũ → cấp máy, tạo dữ liệu → cài bản mới → dữ liệu còn, biểu mẫu chạy, `changed=0`.
  - Ma trận lệch phiên bản: desktop cũ × Box mới, desktop mới × Box cũ.
  - Test khôi phục từ bản sao lưu chụp trước HTTPS.
- **Lint theo đúng bản ansible-core trên máy:** Ubuntu 24.04 có ansible-core 2.16 (agent), CI đang lint bằng 2.19 → ghim lint về 2.16 hoặc thêm kiểm phiên bản. Ví dụ: `meta: end_role` chỉ có từ 2.18.

### 5.1 Lộ trình

| Pha | Nội dung | Phụ thuộc | Máy trạm phải làm gì |
|---|---|---|---|
| 1 | n8n 2.42.6 + tăng cứng nhanh (S1, S5, F12, N1, N2, N4, N7, ghim digest) | — | Không |
| 2 | Báo tình trạng có chữ ký riêng từng máy; ghim khóa SSH có chứng minh; thu hồi máy; kênh đẩy cấu hình an toàn | 1 | Chạy lại bộ cài khi tiện (để ký báo cáo) |
| 3 | CA riêng mỗi Box (ràng buộc tên, root ngoài container); máy trạm tin CA. **Dịch vụ vẫn HTTP** | 2 | Không (Box đẩy) |
| 4 | Bật HTTPS: Caddy là cổng duy nhất, bỏ cổng backend, URL https, cookie Secure | 3 | Không (Box đẩy) |
| 4b | **Bắt buộc** xoay mọi mật khẩu/khóa từng đi qua HTTP; bỏ khóa chung | 4 | Không (Box đẩy) |
| 5 | P2: F5, F8, F9, F11, F13, S3/S4, nâng Ollama… | 1–4 | Tùy mục |

Box cài mới chưa có máy trạm: Pha 3 + 4 có hiệu lực ngay trong một lần cài.

### 5.2 Pha 1 — n8n 2.42.6 + tăng cứng nhanh
**Bản đích n8n:** `docker.io/n8nio/n8n:2.42.6@sha256:526daa38b68e923cc00c5280d18b4da5d489f115a73bdbf3b8e452b184197a9a` (agent).
- Bản này đã vá cả 14 advisory. Ngày làm: nếu có 2.42.x mới hơn thì lấy bản mới nhất và kiểm lại digest.
- Dự phòng ít thay đổi nhất: `2.41.7@sha256:bcef56dd…` — nhưng dòng 2.41 nhiều khả năng không còn được vá.

**Kiểm tương thích 2.40.7 → 2.42.6** (agent đối chiếu mã nguồn; vẫn phải chạy test trên Box):
- Không đổi: CLI `import:credentials`/`import:workflow`/`publish:workflow --id`; biến `N8N_INSTANCE_OWNER_*`; typeVersion mọi nút trong mẫu.
- 2.42.x: lúc nhập có kiểm chính sách, mục bị chặn chỉ in "Skipped … blocked by policy", [Inference] vẫn thoát mã 0 → thêm `failed_when: (stdout + stderr) is search('Skipped|blocked by policy')`.
- 2.41.0: biểu mẫu trả 415 cho POST không phải multipart (test đã dùng `curl -F`).
- `WEBHOOK_URL` lỗi thời từ 2.35 → đổi sang `N8N_WEBHOOK_URL`.
- Migration SQLite không quay lui được.

**Việc làm:**
1. `group_vars/all.yml`: n8n lên 2.42.6@digest; **mọi** image thêm `@sha256:` (digest index đa kiến trúc). Caddy giữ 2.11.4 ở pha này.
2. Môi trường n8n (`docker-compose.yml.j2`):
   - `N8N_DISABLED_MODULES: agents` (N2);
   - `NODES_EXCLUDE` thêm `n8n-nodes-base.git`;
   - `N8N_MCP_MANAGED_BY_ENV: "true"` + `N8N_MCP_ACCESS_ENABLED: "false"`;
   - `WEBHOOK_URL` → `N8N_WEBHOOK_URL` (vẫn http ở pha này).
3. **Tự sao n8n trước khi đổi image:** khi digest n8n đổi, box-stack dừng n8n và chép `${DATA}/n8n` → `${DATA}/n8n.truoc-<bản-cũ>`.
   - Không dựa vào `onebee-box sao-luu`: phản biện chỉ ra bản sao lưu buổi sáng bị lệnh dọn lúc 23:00 xóa mất, và Box chưa gắn ổ ngoài thì lệnh này không chạy.
   - Nếu có ổ ngoài: chụp thêm snapshot có tag `truoc-nang-cap`, thêm `--keep-tag truoc-nang-cap` vào chính sách dọn.
   - Nới thời gian chờ healthz khi migration.
4. **S1:** quy trình 03 đổi sang `respondWith: "text"` + `completionTitle`; `completionMessage` = câu trả lời đã thoát `& < >`.
   - Kết quả đi qua sanitize-html và khung `white-space: pre-line`.
   - Sửa luôn lỗi hiển thị dòng bị dồn.
   - Không bao giờ đặt `N8N_INSECURE_DISABLE_FORM_HTML_SANDBOX`.
5. **Open WebUI:**
   - Env: `ENABLE_PLUGINS: "false"` (N1, biến này chỉ đọc từ env).
   - `ADMIN_CONFIG` (`onebee-webui.py`) thêm `ENABLE_COMMUNITY_SHARING: False` và `JWT_EXPIRES_IN: "7d"` (F12, S5; đây là đường duy nhất đổi được Box đã cài). Mirror vào env cho bản cài mới.
6. **N7 (bảo đảm QĐ1):**
   - Bộ cài desktop cảnh báo khi có tài khoản người dùng (UID ≥ 1000) ngoài tài khoản quản trị đã khai báo nằm trong nhóm `sudo`/`admin`. Biến `onebee_tai_khoan_quan_tri`; tùy chọn dừng hẳn bằng cờ.
   - `onebee-bao-tinh-trang` gửi số tài khoản trong nhóm sudo; `onebee-box may-tram` cảnh báo khi > 1.
   - Sửa `cai-hang-loat.md` mục 2–3: nhân viên dùng tài khoản **Standard**, tài khoản quản trị giữ riêng.
7. **N4:** sửa `quan-ly-may-tram.md:39-40` (dùng `ssh-keygen -R … -f /etc/onebee-box/secrets/ssh/known_hosts`).
8. **Test:**
   - `verify-box-install.sh`: kiểm env mới của n8n và Open WebUI; `GET /api/v1/auths/admin/config` trả đúng 2 giá trị.
   - `check-n8n-inside.sh`:
     - `n8n export:workflow` → quy trình 03 có `respondWith=text` và biểu thức thoát HTML (không dựa vào AI lặp lại chuỗi độc — dễ chập chờn);
     - `curl -D -` trang completion có `content-security-policy: sandbox`, không có `allow-same-origin`.
   - `run-box-test…:50`: lệnh sed đổi sang `-slim` phải bỏ đuôi digest.
   - Test nâng cấp 2.40.7 → 2.42.6.
- **Hoàn tác:** dừng n8n → trả `${DATA}/n8n.truoc-<bản-cũ>` về chỗ cũ → ghim lại 2.40.7 → chạy bộ cài.
- **Rủi ro:** migration hỏng (đã có bản chép); `JWT_EXPIRES_IN=7d` buộc đăng nhập lại mỗi tuần; tắt Functions/Tools (Box không dùng).

### 5.3 Pha 2 — Báo tình trạng có chữ ký, ghim khóa SSH có chứng minh, thu hồi, kênh đẩy cấu hình
Bản thiết kế đầu bị phản biện chỉ ra 1 điểm chặn: dùng khóa riêng lưu băm trong n8n + tự ghim khóa host từ báo cáo do n8n ghi → n8n vẫn nằm trong chuỗi tin cậy, và "ghim lần đầu" vẫn là tin mù qua HTTP. Thiết kế dưới đây sửa điều đó. [Inference] Đây là đề xuất của người rà soát; cần duyệt.

**(a) Chữ ký báo cáo — đưa n8n ra khỏi chuỗi tin cậy**
- Bí mật dùng chung giữa máy trạm và Box đã có sẵn: `RESTIC_PASSWORD`.
  - Dán tay lúc cấp máy; restic **không bao giờ** gửi nó qua mạng.
  - Box giữ ở `secrets/may-<ten>-repo`.
- Khóa ký: `K = HMAC-SHA256(RESTIC_PASSWORD, "onebee-tinh-trang-v1")` (tách mục đích, không dùng thẳng mật khẩu).
- Máy trạm (`onebee-bao-tinh-trang`) gửi `{"ten", "du_lieu": "<JSON dạng chuỗi, có gui_luc>", "ky": hex(HMAC(K, du_lieu))}`. Ký trên chuỗi gốc → không lo khác biệt khi phân tích lại JSON.
- n8n (quy trình 06) **không giữ bí mật nào**. Chỉ:
  - kiểm dạng;
  - chỉ nhận tên có trong danh sách máy đã cấp — file `ten-da-cap.json` do Box ghi, gắn **chỉ đọc**; dùng `Object.prototype.hasOwnProperty`, chặn `ten=constructor`;
  - lưu nguyên văn vào `<ten>.json`.
- Box (`onebee-may-tram.py`, chạy root) tự kiểm chữ ký bằng bí mật trong `secrets/`:
  - kiểm `gui_luc` mới hơn lần đã nhận (chống phát lại) và không lệch quá xa đồng hồ Box;
  - sai chữ ký → **không dùng** dữ liệu, cảnh báo "báo cáo giả hoặc hỏng";
  - chưa ký (máy chạy mã desktop cũ) → hiện nhưng gắn nhãn "chưa ký", **không** dùng IP để SSH vào máy chưa ghim.
- Khóa chung `TINH_TRANG_KEY` chỉ còn là bộ lọc rác ở cửa n8n, không được tin cho việc gì → bỏ hẳn ở Pha 4b.
- Lợi ích: khóa không bao giờ đi qua mạng (hết đường nghe lén ngay ở Pha 2, không phải chờ TLS); n8n bị chiếm cũng không giả được báo cáo; máy cũ không cần cấp khóa mới.

**(b) Ghim khóa host bằng chứng minh nắm bí mật** (thay `accept-new`)
- Lần đầu vào một máy chưa ghim — chạy riêng một lượt `ansible-playbook`:
  - `ANSIBLE_SSH_ARGS` dùng `accept-new` với **file known_hosts tạm**, giới hạn đúng máy đó (tùy chọn theo từng máy trong inventory không ghi đè được tùy chọn toàn cục);
  - đọc `/etc/onebee/may-tram.env`;
  - **trên Box** (`no_log`) so `sha256(RESTIC_PASSWORD)` với `secrets/may-<ten>-repo`.
- Khớp → mới gộp dòng ghim vào `secrets/ssh/known_hosts`. Lệch → dừng, cảnh báo, không ghim, không đẩy gì.
- Các lượt sau: `StrictHostKeyChecking=yes`, `UpdateHostKeys=no`.
- Máy giả không biết `RESTIC_PASSWORD` → không qua được. Không có bí mật nào của Box bị gửi sang máy đích.
- Đợt chuyển đổi: **xác minh lại** mọi dòng ghim cũ do `accept-new` tạo bằng cùng cách chứng minh (có thể đã bị đầu độc theo F2).
- Lệnh mới: `onebee-box ghim-lai-may <ten>` (máy cài lại hệ điều hành) và tùy chọn `--ip <địa chỉ>` cho lần liên lạc đầu khi chưa có báo cáo.

**(c) Thu hồi máy — `onebee-box thu-hoi-may <ten>`**
- Xóa `may-<ten>-http`, dòng htpasswd, tài khoản Open WebUI `may-<ten>` (khóa `hoi`), dòng ghim, file tình trạng. Ghi dấu `may-<ten>-thu-hoi`.
- Giữ mật khẩu kho để còn khôi phục và dọn bản cũ.
- Một hàm liệt kê chung `may_da_cap` (bỏ máy đã thu hồi), dùng ở **mọi** nơi:
  - `gio_sao_luu_may`;
  - dựng lại htpasswd khi khôi phục;
  - `cap-nhat-may` (cả chế độ 1 máy);
  - `dong-bo-may`;
  - `ten-da-cap.json`;
  - báo cáo.
- Hàm `secret_co_san`: thiếu file thì **báo lỗi**, không tự sinh mới. Dùng ở mọi nơi trừ `them-may`. Hiện tại `secret()` tự sinh khóa mới khi thiếu → lặng lẽ "hồi sinh" máy đã thu hồi.
- Sau `khoi-phuc-toan-bo`: xóa lại tài khoản Open WebUI của các máy đã thu hồi.

**(d) Kênh đẩy cấu hình — `onebee-box dong-bo-may <ten>|--tat-ca`** (dùng quyền F4 đã chấp nhận)
- Tách `in_cau_hinh_may <ten>` **chỉ đọc**:
  - chỉ đọc bí mật có sẵn, kể cả khóa `hoi` (lưu `secrets/may-<ten>-hoi` lúc cấp);
  - **không** gọi `webui cap-khoa`, không ghi htpasswd.
  - Phản biện chỉ ra: dùng lại nguyên khối `them-may` thì Open WebUI trục trặc một lúc là xóa `hoi` trên mọi máy, và đẩy lại cấu hình sẽ "hồi sinh" máy đã thu hồi.
- Thiếu bất kỳ khóa nào → **bỏ qua máy đó**, không đẩy file thiếu. Bỏ qua máy đã thu hồi.
- Chỉ đẩy tới máy đã ghim theo (b), không bao giờ tin mù rồi đẩy bí mật.
- Playbook (mới, hoặc khối `tags: cau-hinh` trong `cap-nhat-may-tram.yml`), thứ tự:
  1. Kiểm `MAY_TRAM`.
  2. Ghi `/etc/onebee/may-tram.env` (`backup: true`, 0600, `no_log`).
  3. Đọc lại file.
  4. Từ Pha 3: chạy role `ket-noi-box`.
  5. Chạy `onebee-bao-tinh-trang` để kiểm cấu hình mới dùng được.
- Dấu "đã đồng bộ" lưu trong `${DATA}` (có sao lưu), không để ở `/var/lib`.
- `them-may` in thêm `ONEBEE_TOI_THIEU=<phiên bản desktop tối thiểu>`; bộ cài desktop từ bản này trở đi dừng rõ ràng khi mã của mình cũ hơn mức đó.
- **Log:** `/var/log/onebee-box` 0700, umask 077, `no_log` cho mọi task chạm `may-tram.env`/`hoi.conf`; logrotate giữ 90 ngày.

**File chính:**
- Box: `onebee-box.sh.j2`, `onebee-box-common.sh.j2`, `onebee-box-sao-luu.sh.j2`, `docker-compose.yml.j2` (mount chỉ đọc `ten-da-cap`), `06-nhan-tinh-trang-may-tram.json.j2`, `onebee-may-tram.py`, `cap-nhat-may-tram.yml` (+ playbook mới), `box-fleet/tasks/main.yml`.
- Desktop: `onebee-bao-tinh-trang` (ký báo cáo, ánh xạ lỗi rõ hơn).
- Docs: `quan-ly-may-tram.md`, `cai-hang-loat.md` (bắt buộc `ssh-keygen -A` cho máy nhân bản), ADR 0004.

**Test:**
- Unit: chữ ký đúng/sai/thiếu, phát lại `gui_luc` cũ, tên lạ, `constructor`, cập nhật các test cũ đang chờ "không cảnh báo".
- Box:
  - báo cáo ký bằng bí mật máy A gửi tên máy B → Box không dùng;
  - máy giả có `RESTIC_PASSWORD` khác → không ghim, không đẩy;
  - đổi khóa host máy thật → `cap-nhat-may` dừng, `known_hosts` không đổi;
  - `ghim-lai-may` → đạt;
  - tắt Open WebUI rồi `dong-bo-may` → `/etc/onebee-hoi.conf` không đổi;
  - thu hồi → khôi phục toàn bộ → mật khẩu cũ bị 401, `dong-bo-may --tat-ca` bỏ qua máy đó.
- Lần chạy thứ 2: `changed=0` (task ghi `ten-da-cap.json` chỉ báo đổi khi nội dung đổi).

### 5.4 Pha 3 — CA riêng mỗi Box (dịch vụ vẫn HTTP)
**Thiết kế đã sửa theo phản biện:**
- **Biến bắt buộc:**
  - `onebee_box_ma_don_vi` — nhãn DNS riêng mỗi khách, không mặc định theo hostname, chặn giá trị mặc định như `onebee-box`.
  - `onebee_box_dia_chi` — IP tĩnh, tính một lần, sửa N3.
  - Cả hai lưu cạnh CA (`secrets/ca/ca.conf`) và đọc lại ở các lần chạy và khi khôi phục.
- **Ràng buộc tên** (name constraints, critical):
  - IP: chỉ IP Box `/32` (+ IP Tailscale `/32` nếu dùng). **Không** dùng cả dải LAN: lộ khóa thì giả được router, NAS, camera.
  - DNS: `<ma_don_vi>.onebee.internal`. Bắt buộc có ràng buộc DNS, nếu không mọi tên miền đều mở.
  - Đổi IP Box = xoay CA. Đằng nào cũng phải đến từng máy vì `from=` trong `authorized_keys`.
- **Root nằm ngoài container:**
  - Ansible dùng openssl sinh root (pathlen:1, ràng buộc như trên, 10 năm) + intermediate (pathlen:0, cùng ràng buộc, 1 năm).
  - Caddy chỉ nhận root cert + **intermediate cert/key**. (agent) Caddy 2.11.4 cho phép bỏ khóa root; Caddy không tự gia hạn intermediate được cấp → bộ cài gia hạn khi còn < 60 ngày.
  - Cảnh báo "CA trung gian/gốc còn N ngày" trong `trang-thai` và email sao lưu (thêm vào payload quy trình 01).
  - Khóa root ở `secrets/ca/` (0700, chỉ root trên máy chủ), **không** gắn vào container nào. Nằm trong bản sao lưu Box (đã mã hóa bằng khóa `restic-box`).
- **Dữ liệu Caddy:** gắn `${DATA}/caddy:/data` và `/config`; gắn **cả thư mục** Caddyfile (sửa N5).
- **Box tin CA** (`update-ca-certificates`) để script và kiểm tra sức khỏe gọi `https://<IP>:<cổng>` — phương án B (5.5).
- **Khôi phục:** trước `restic restore` xóa các dấu của bản cài lại (`https-da-bat`…); sau restore: xóa `${DATA}/caddy/*`, `update-ca-certificates --fresh` với root cũ, dựng lại `ten-da-cap.json`.

**Máy trạm — role mới `ket-noi-box`** (Box dùng lại khi `dong-bo-may`):
- Dòng mới trong `may-tram.env`: `BOX_CA=<base64 DER, 1 dòng>`, `BOX_CA_VAN_TAY=<sha256>`.
- Kiểm trước khi cài:
  - vân tay khớp;
  - **và** chứng chỉ đúng là CA OneBee có ràng buộc: CA:TRUE; `nameConstraints` critical; IP duy nhất là `/32` = `BOX_IP` (± Tailscale); DNS dưới `.onebee.internal`; không loại tên khác.
  - Vân tay cùng kênh với chứng chỉ chỉ bắt lỗi chép, không chứng minh nguồn.
- Cài vào kho hệ thống → Python (`hoi`, `onebee-bao-tinh-trang`), curl, restic tin CA.
- **Firefox, cần thu hồi được:**
  - (agent) `Certificates.Install` ghi vào cert9.db của từng hồ sơ và **không gỡ** khi bỏ policy.
  - Ưu tiên: policy `SecurityDevices` nạp `p11-kit-trust.so` → Firefox đọc thẳng kho hệ thống, gỡ file là hết tin. [Unverified] đường dẫn module trên Mint 22 và việc NSS vẫn áp ràng buộc.
  - Dự phòng: `Certificates.Install` + `certutil -D` trên từng hồ sơ khi gỡ hoặc xoay CA.
  - Trộn với `/usr/lib/firefox/distribution/policies.json` (file ở `/etc` *thay thế* file kia); trộn danh sách bằng `list_merge='append_rp'`; xóa file `/etc` khi không còn mục OneBee.
- **Chromium/Chrome:** luôn ghi `/etc/chromium/policies/managed/` và `/etc/opt/chrome/policies/managed/` với `CACertificatesWithConstraints` (trình duyệt tự áp ràng buộc).
- **Cấu trúc Ansible 2.16:** khối `block`/`when` cho phần CA (không có `end_role`). Sinh `hoi.conf` và mục menu **ngoài** khối CA, để lỗi CA không chặn cấu hình khác.
- **Không** từ chối `rest:http://` chỉ vì có file CA (làm hỏng sao lưu toàn bộ máy ở Pha 3, khi hoàn tác, khi lệch phiên bản) — xem cờ `BOX_HTTPS` ở Pha 4.

**Thiết bị không do OneBee quản lý** (máy Windows của quản lý, laptop kỹ thuật, điện thoại):
- Vân tay CA chỉ đối chiếu qua kênh ngoài: in trong `in-khoa` (giấy), lệnh `onebee-box in-ca` trên màn hình Box, dòng cuối của bộ cài. **Không** hiện vân tay trên trang HTTP nào.
- Cổng :80 phục vụ file CA + trang hướng dẫn tĩnh (không chuyển hướng sang trang báo lỗi chứng chỉ).
- Ưu tiên chép CA bằng USB cho máy quản lý.
- [Unverified] Windows/macOS có áp ràng buộc tên cho root người dùng tự cài không → chưa khẳng định cùng mức bảo vệ.

**Test:**
- `verify-box-install.sh`: quyền `secrets/ca`; root và intermediate có `nameConstraints` critical; **chuỗi thật root → intermediate → lá** cho `www.google.com` và `10.0.0.5` phải bị từ chối bởi openssl, python ssl, curl, Go (restic) và `gnutls-cli` trên image Mint. Chỉ ghi "được bảo vệ" cho những client đã thử.
- Không container nào khác portal có file khóa; log không có `RESTIC_PASSWORD`.
- `check-khoi-phuc-toan-bo.sh`: root giống hệt sau khôi phục; xóa thêm `/var/lib/onebee-box`; thêm ca khôi phục từ bản chụp trước HTTPS.
- Desktop: sai vân tay / CA không ràng buộc → không cài, có cảnh báo; bỏ `BOX_CA` → gỡ sạch (kể cả Firefox); `changed=0`.

### 5.5 Pha 4 — Bật HTTPS
**Kiến trúc:**
- Caddy (container portal) là dịch vụ duy nhất mở cổng: 80 (CA + hướng dẫn), 443 (trang giới thiệu), 3000/5678/3001/8000 (TLS, giữ số cổng → URL chỉ đổi http thành https).
- Bỏ `ports:` của open-webui, n8n, uptime-kuma, rest-server.
- Bật theo thứ tự: backend trước, portal sau (tránh tranh cổng).

**Script và kiểm tra sức khỏe trên chính Box — chọn B:** gọi qua `https://<onebee_box_dia_chi>:<cổng>` với CA trong kho của Box.
- Một đường duy nhất, giống người dùng; không còn cổng backend nào mở.
- `N8N_PROXY_HOPS=1` an toàn vì n8n không còn tự mở cổng.
- Phương án lùi A: cổng `127.0.0.1` riêng — nếu thử thấy hairpin hoặc SNI có vấn đề.
- Kiểm tra sức khỏe phải kiểm nội dung trả về: Host không khớp site nào thì Caddy trả 200 rỗng (agent).

**Caddyfile** (agent tra mã Caddy 2.11.4):
- `default_sni <IP>` — **bắt buộc**: client nối bằng IP không gửi SNI, Caddy trong mạng bridge chỉ thấy IP container. [Unverified] trên máy thật.
- `servers :<cổng> { listener_wrappers { http_redirect, tls } protocols h1 h2 }` khai riêng từng cổng TLS. Không tắt h3 thì Chrome không tin CA tự thêm qua HTTP/3.
- `reverse_proxy … { stream_close_delay 5m }`; rest-server thêm `request_body { max_size 256MB }`.
- Không chèn header CSP lên site n8n (giữ sandbox của biểu mẫu).
- Site :3001 chỉ sinh sau khi Kuma có tài khoản quản trị. Trước đó, kiểm Kuma **bên trong container** (phản biện: nếu không, lần cài đầu sẽ hỏng vì không có gì nghe ở 3001).
- `caddy reload` chỉ chạy sau `compose up` và khi container không vừa được tạo lại.
- Caddy giữ 2.11.4@digest. Chỉ lên 2.11.7 sau khi thử `hoi` không stream (~5 phút), tóm tắt PDF, restic tải lớn (2.11.6+ có timeout idle mặc định 1 phút).

**Ứng dụng:**
- n8n: `N8N_PROTOCOL=https`, `N8N_HOST=<IP>`, `N8N_EDITOR_BASE_URL` = `N8N_WEBHOOK_URL` = `https://<IP>:5678/`, `N8N_PROXY_HOPS=1`, bỏ `N8N_SECURE_COOKIE=false`.
- Open WebUI: `WEBUI_SESSION_COOKIE_SECURE=true`, `WEBUI_AUTH_COOKIE_SECURE=true`, `CORS_ALLOW_ORIGIN=https://<IP>:3000` (lệch là WebSocket chat hỏng mà không báo); `WEBUI_URL` qua `ADMIN_CONFIG` (truyền giá trị qua env của hàm `webui()`); ghim subnet mạng compose + `FORWARDED_ALLOW_IPS`.
- Uptime Kuma: theo dõi nội bộ giữ `http://<dịch vụ>`; thêm theo dõi HTTPS; `onebee-kuma.js` thêm sửa-theo-tên (`editMonitor`) thay vì xóa rồi thêm (sửa N6, giữ `changed=0`); bật Trust Proxy khi 3001 không còn publish.
- rest-server: giữ `--private-repos --append-only`; **không** dùng `--proxy-auth-username`.
- Caddy container: `no-new-privileges`, `cap_drop: [ALL]`, `cap_add: [NET_BIND_SERVICE]` (F11 cho điểm vào).

**Máy trạm:**
- Box đẩy URL https + cờ `BOX_HTTPS=1` qua `dong-bo-may`. Máy ghi dấu bền `/var/lib/onebee/https-bat`.
- Khi có dấu: `hoi`, `onebee-bao-tinh-trang`, `onebee-sao-luu` từ chối `http://`. Chỉ cờ hoàn tác do Box đẩy mới xóa dấu.
- `onebee-sao-luu`: sửa F7 (đọc `while IFS='=' read`), đặt `RESTIC_CACERT` khi kho là https.
- Thông báo lỗi: 502/503/504 → "dịch vụ trên Box chưa chạy"; 301/308 → "cấu hình URL cũ — báo quản trị chạy `dong-bo-may`". Cập nhật test đang chờ câu "Không kết nối được OneBee Box".
- **Firefox chống hạ cấp** (HSTS vô tác dụng với IP):
  - `ManagedBookmarks` + `Homepage` dạng https;
  - tùy quyết định: `DisableSecurityBypass.InvalidCertificate=true` (mục 6);
  - in lại tờ phím tắt, tài liệu đào tạo với https.

**Chốt chặn và tự đồng bộ:**
- Còn máy đã cấp chưa đồng bộ CA → lần chạy này giữ HTTP và in danh sách máy (có biến bỏ qua).
- Dấu `https-da-bat` nằm trong `${SECRETS}` (có sao lưu); khôi phục xử lý như 5.4.
- Tự chạy `dong-bo-may --tat-ca` ở **cuối** bộ cài, trong box-fleet sau khi đã chép các công cụ mới.

**Tài liệu:** ADR 0002 (thay quyết định 5); ADR 0005 mới "HTTPS nội bộ — Caddy + CA ràng buộc tên". Ghi rõ rủi ro còn lại:
- sslstrip trên thiết bị không quản lý;
- cookie dùng chung giữa các cổng cùng IP (cùng "site");
- ràng buộc tên **chỉ** giới hạn thiệt hại khi lộ khóa CA mà Box chưa bị chiếm.

Cập nhật các hướng dẫn trong `docs/huong-dan/`, `README.md`, `tests/README.md`.

**Test:**
- `docker port` rỗng cho 4 backend;
- `openssl s_client -noservername -verify_ip` đạt;
- `curl -sI http://IP:3000` → 308;
- cookie có cờ Secure; Origin lạ không có CORS;
- CSP sandbox của biểu mẫu còn khi đi qua Caddy;
- `hoi` ~5 phút qua Caddy;
- nhánh chốt chặn; test nâng cấp từ trạng thái Pha 3;
- kiểm tay trên máy ảo: chat WebSocket, trình soạn n8n, Uptime Kuma, biểu mẫu 03 — Firefox không cảnh báo.

**Hoàn tác:** `onebee_box_https: false` → chạy bộ cài → `dong-bo-may --tat-ca` (đẩy cờ hoàn tác, URL http). Mẫu giữ nhánh HTTP ít nhất 1 bản phát hành.

### 5.6 Pha 4b — Xoay khóa bắt buộc (chạy khi máy cuối cùng đã đồng bộ HTTPS)
Lý do: QĐ3 nhằm chống nghe lén. Mọi thứ đã đi qua LAN dạng rõ trước khi có HTTPS vẫn còn hiệu lực.
- Theo từng máy (đẩy bằng `dong-bo-may`): mật khẩu htpasswd kho sao lưu, khóa `hoi`.
  - `RESTIC_PASSWORD` không cần đổi: chưa từng đi qua mạng.
- Phía Box:
  - mật khẩu biểu mẫu `nhanvien`/`kythuat`;
  - mật khẩu chủ n8n (`N8N_INSTANCE_OWNER_PASSWORD_HASH`);
  - mật khẩu quản trị Open WebUI và Uptime Kuma;
  - `WEBUI_SECRET_KEY` để hủy mọi JWT cũ. [Unverified] Khóa này còn mã hóa gì khác → thử trên Box thử trước.
- Bỏ hẳn `TINH_TRANG_KEY` và credential `onebeeTram000001` (xóa cả trong CSDL n8n, vì nhập lại không tự xóa).
- Lệnh: `onebee-box xoay-khoa [--may <ten>|--tat-ca] [--box]`; in lại `in-khoa` sau khi xoay.

### 5.7 Pha 5 — P2
| Mục | Việc |
|---|---|
| F5 | Sửa code tường lửa: áp chuỗi lọc cho mọi cổng mạng trừ `lo`/`docker*`/`br-*`, hoặc danh sách cho phép riêng `tailscale0` (IP 100.x của máy kỹ thuật). Tài liệu ACL Tailscale mẫu theo QĐ2 |
| F8 | `server min protocol = SMB3_00` + `server smb encrypt = required`, sau khi kiểm máy khách (mục 6) |
| F9 | Tài khoản biểu mẫu theo phòng/người, ghi người đăng nhập vào CSV; siết `N8N_CONTENT_SECURITY_POLICY` (giảm GHSA-29xw) |
| F11 | `no-new-privileges` mọi container; rest-server `cap_drop: [ALL]` + `read_only`; cân nhắc image Uptime Kuma `-rootless` |
| F13, F6 | Ký tag/bản phát hành (minisign/cosign); ghim GitHub Actions theo SHA; Renovate (regex manager cho `group_vars/all.yml`); lịch ghim lại n8n mỗi 1–2 tuần |
| S3, S4 | Thêm `\r` vào regex, `trim()` thống nhất (dùng `_csv-js.j2` cho quy trình 04), lọc `[\r\n]` khỏi tiêu đề email |
| Khác | Quét image rest-server; nâng Ollama 0.40.x có kế hoạch (tải lại model nếu lùi); thử tắt thêm mô-đun n8n không dùng; `onebee-box doi-ca` (xoay CA), `doi-khoa-quan-tri` (xoay khóa SSH quản trị) |

### 5.8 F4 (chấp nhận) — kiểm soát bù, đã sửa theo phản biện
Kiểm soát bù thật của F4:
- **Giảm bề mặt tấn công của Box:**
  - Pha 1: n8n vá, tắt Agents/MCP, `ENABLE_PLUGINS=false`.
  - Pha 4: không còn cổng backend, cookie Secure.
  - Pha 4–5: khóa container.
  - Pha 2: ghim khóa SSH có chứng minh.
- **Truy vết:** log `cap-nhat-may`/`dong-bo-may`/`xoay-khoa` (0700, 90 ngày). Hướng dẫn xem `journalctl _COMM=sudo`, `/var/log/auth.log` của `onebee-quantri` trên máy trạm.
- **Quy trình khi nghi Box bị chiếm:** `doi-khoa-quan-tri` → `doi-ca` → `xoay-khoa --tat-ca` → đổi mật khẩu kho. Có test gỡ CA khỏi Firefox (xem 5.4).
- **Minh bạch:** ADR 0004 + mục riêng tư trong `cai-dat-onebee-box.md` ghi rõ Box có root trên máy trạm, đọc được bản sao lưu, đẩy được cấu hình và CA. Giữ ít người có quyền quản trị Box.

**Không** tính là kiểm soát bù F4 (bản đầu ghi nhầm):
- Ràng buộc tên CA: chiếm Box = cài được CA bất kỳ lên máy trạm.
- Ghim khóa SSH: đây là kiểm soát cho F2.

## 6. Câu hỏi còn mở (cần chủ dự án quyết; có đề xuất mặc định)
1. **Mã đơn vị** (`onebee_box_ma_don_vi`, nhãn DNS của CA): quy tắc đặt? Đề xuất: viết tắt không dấu theo tên khách, ví dụ `htx-onebee`. Phải chốt trước khi Box sinh CA (đổi sau = xoay CA).
2. **Kỹ thuật mở giao diện Box qua Tailscale?** Có → thêm IP Tailscale `/32` vào ràng buộc + tên phụ `box.<ma>.onebee.internal` + dòng `/etc/hosts` trên máy kỹ thuật (IP 100.x trần không dùng được vì không có SNI).
3. **Bắt buộc IP tĩnh/đặt trước DHCP cho Box?** Đề xuất: bắt buộc (đổi IP = xoay CA + đến từng máy).
4. **Firefox máy trạm: chặn bấm "chấp nhận rủi ro" chứng chỉ** (`DisableSecurityBypass`)? Đề xuất: bật. Đánh đổi: router, máy in tự ký trong LAN cũng không mở được qua https lỗi.
5. **Khóa gốc CA:** để trên Box (`secrets/ca`, không vào container) hay cất USB ngoài Box? Đề xuất: để trên Box (F4 đã coi Box là điểm tin cậy; USB thêm thao tác mỗi năm khi gia hạn intermediate).
6. **Phiên Open WebUI** `JWT_EXPIRES_IN`: 7 ngày hay 24 giờ? Đề xuất: 7 ngày.
7. **Nhân viên có tài khoản web Open WebUI không?** Hướng dẫn hiện bảo quản trị tạo; nếu có thì advisory cần đăng nhập về sau sẽ áp dụng.
8. **Thư mục chung:** có máy Windows 8.1/Server 2012/macOS dùng không? (trước khi bắt buộc mã hóa SMB).
9. **Chạy mã (pyodide) trong Open WebUI:** giữ hay tắt? Đề xuất: giữ (chạy trong trình duyệt).

**Cần kiểm trên máy thật** (không phải quyết định, sẽ làm trong lúc triển khai):
- Firefox deb của Mint 22: có `distribution/policies.json` không, có đọc `/etc/firefox/policies` không, đường dẫn `p11-kit-trust.so`.
- Caddy trong mạng bridge: `default_sni` bắt buộc thật không; hairpin từ Box tới chính IP LAN.
- Caddy 2.11.4 nhận intermediate được cấp mà không có khóa root.
- Caddy 2.11.7 với timeout 1 phút.
- Hệ quả của việc đổi `WEBUI_SECRET_KEY`.
- n8n 2.42.x: mã thoát khi "Skipped"; Form Trigger có kiểm `acceptFileTypes` phía máy chủ không.
- `gnutls-cli`, Windows, macOS có áp ràng buộc tên trong chuỗi root → intermediate không.

## Nguồn chính
- n8n: [advisory list](https://github.com/n8n-io/n8n/security/advisories), [GHSA-3qcw-p65v-c7vq](https://github.com/n8n-io/n8n/security/advisories/GHSA-3qcw-p65v-c7vq), [GHSA-29xw-66fq-4xc3](https://github.com/n8n-io/n8n/security/advisories/GHSA-29xw-66fq-4xc3), mã nguồn tag `n8n@2.40.7`: `packages/cli/src/modules/oauth-server/`, `packages/nodes-base/nodes/Form/utils/formCompletionUtils.ts`, `packages/cli/templates/form-trigger-completion.handlebars`.
- Open WebUI: [advisory list](https://github.com/open-webui/open-webui/security/advisories), [GHSA-vpq8-f445-hcq7](https://github.com/open-webui/open-webui/security/advisories/GHSA-vpq8-f445-hcq7), [GHSA-f9xp-mfmq-x6cg](https://github.com/open-webui/open-webui/security/advisories/GHSA-f9xp-mfmq-x6cg).
- Uptime Kuma: [GHSA-wf2j-5mc7-5c4w](https://github.com/louislam/uptime-kuma/security/advisories/GHSA-wf2j-5mc7-5c4w).
- Caddy (agent): mã nguồn tag `v2.11.4` — `modules/caddypki/`, `modules/caddyhttp/httpredirectlistener.go`; [releases](https://github.com/caddyserver/caddy/releases).
- Firefox policy (agent): [mozilla/policy-templates](https://github.com/mozilla/policy-templates); Chromium: `docs/linux/cert_management.md`.
