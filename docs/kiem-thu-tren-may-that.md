# Phiếu kiểm thử trên máy thật — Pha 1–5 rà soát bảo mật

Dành cho chủ dự án sau khi clone nhánh `claude/confident-gauss-ntiwuc`. Nơi viết code **không** có Docker daemon, ansible-core 2.16, Box/Mint/Windows thật,
nên mọi mục dưới đây **chưa từng chạy**. Nguồn: các khối "Trạng thái triển khai" Pha 1–5 trong `docs/security-audit.md`, ADR 0005, `tests/README.md`.

Cách dùng: làm theo thứ tự (rẻ, ít rủi ro trước). Mỗi mục: **(a)** môi trường · **(b)** lệnh · **(c)** mong đợi · **(d)** sai thì nghi ở đâu.
Đánh `[x]` khi đạt; không đạt thì ghi `git rev-parse --short HEAD`, lệnh, 30 dòng log cuối. Mục cuối file là các lỗi nghi ngờ tìm thấy khi đọc code.

```bash
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee && cd onebee
git checkout claude/confident-gauss-ntiwuc
```
Windows 10: chạy trong **WSL2** (Ubuntu), clone vào `~` (không vào `/mnt/c`), trước đó `git config --global core.autocrlf false` — CRLF làm hỏng script bash.

## Kết quả lần chạy 10–11/10/2026 (nhóm A)
Hai môi trường — ghi rõ để không lẫn:
- **cloud**: máy làm việc của Claude, Docker 29.8.2 **cgroup v1**, 2 CPU, 7 GB RAM, proxy HTTPS tự ký (`ONEBEE_TEST_EXTRA_CA`).
- **Mac**: MacBook Pro Intel của chủ dự án, **Docker Desktop 29.3.1, cgroup v2, 16 CPU, 15 GiB** cho Docker, mạng gia đình 0,2–2 MB/s. Không proxy.

| Mục | Nơi | Commit | Kết quả |
|---|---|---|---|
| A1.1 | cloud | `810e847` | Box `Ran 100 … OK (skipped=7)` (phiếu ghi 99), Desktop 39 OK, AI 17 OK, Jinja 23 mẫu 0 lỗi |
| A1.2 | cloud | `810e847` | Caddy v2.11.4 đúng digest: 7/7 OK |
| A2.1 | cloud | `810e847` | shellcheck 0.9.0, yamllint, ansible-lint 26.9.0 (core 2.19.13): đạt |
| A2.2 | cloud (container `ubuntu:24.04`, apt) | `810e847` | ansible-core **2.16.3**: syntax-check Box/Desktop/`dong-bo-may-tram.yml` đạt; ansible-lint 6.17.2 Box đạt |
| A2.3 | cloud | `810e847` | `Config validated successfully` |
| A3.1 | cloud **và** Mac | `810e847` | lần 1 `changed=36`, lần 2 `changed=0 failed=0`, verify "tất cả mục đạt", LibreOffice UNO đạt |
| A3 mở rộng | cloud | `810e847` | 5 kịch bản (guards, mint, unikey, systemd, ubuntu): **83 PASS / 0 FAIL** |
| A4.1 | Mac | `810e847` → `9a8b950` | Chạy với model sản phẩm `gemma4:e2b-it-qat`. Lần 1 FAIL ở lỗi test T1 → sửa, **chạy tiếp từ "LẦN 2" trên container giữ lại**; FAIL ở N11 → sửa → FAIL ở N12 (do bản sửa N11) → sửa → `TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT`. Lần chạy **runner gốc từ đầu** ở `9a8b950`: xem dòng cuối mục này |

Lỗi tìm được và đã sửa trong lần chạy này (chi tiết ở mục "Đã sửa sau khi lập phiếu này"): **N11, N12** (sản phẩm), **T1, T2** (script test). Lỗi mới còn mở: **N13**.
Kiểm thêm tay trên Box test (Mac): `n8n --version` = `2.42.6`; log n8n không có `blocked by policy|content-import|X-Forwarded`;
portal `[ALL] [CAP_NET_BIND_SERVICE] [no-new-privileges:true]`, rest-server `ro=true drop=[ALL]`, mọi dịch vụ `no-new-privileges`; máy thu hồi `kho-02` không còn trong `.htpasswd`.

Lần chạy runner gốc từ đầu ở `9a8b950` (Mac): **đang chạy — điền kết quả khi xong.**

---

## A. Bộ kiểm thử tự động có sẵn

### A1. Unit test (vài chục giây)
- [x] **A1.1 Unit Box + Desktop + mẫu Jinja**
  - (a) Linux/macOS/WSL2: `python3` ≥ 3.10, `pip install pyyaml jinja2`, `openssl`, `curl`, `node`, `htpasswd` (apt `apache2-utils`), `ssh-keygen` (`openssh-client`).
  - (b)
    ```bash
    python3 -m unittest discover -s tests/box -p 'test_*.py'
    python3 -m unittest discover -s tests/desktop -p 'test_*.py'
    python3 -m unittest tests/ai/test_scoring_and_report.py && python3 tests/kiem-tra-mau-jinja.py
    ```
  - (c) Box `Ran 99 tests … OK (skipped=7)` (7 bài Caddy bỏ qua khi chưa có caddy), Desktop `Ran 39 tests … OK`, `Đã kiểm 23 mẫu, 0 lỗi`.
    Các dòng `LỖI: ràng buộc tên …` in ra trong lúc chạy desktop là **đúng** (bài thử CA giả).
  - (d) Thiếu công cụ → bài bị skip chứ không lỗi; đếm lại số skip bằng `-v`.
- [x] **A1.2 Test Caddyfile với Caddy THẬT** (7 bài đang skip)
  - (a) Máy có Docker (lấy đúng binary từ image đã ghim digest, như CI).
  - (b)
    ```bash
    img="$(grep -oP '^  caddy: \K\S+' box/ansible/group_vars/all.yml)"
    docker create --name caddy-tmp "${img}" >/dev/null && docker cp caddy-tmp:/usr/bin/caddy /tmp/caddy && docker rm caddy-tmp >/dev/null
    ONEBEE_TEST_CADDY=/tmp/caddy python3 -m unittest -v tests/box/test_onebee_caddy_https.py
    ```
  - (c) 7 bài `ok` (IP không SNI, tên phụ Tailscale, chuỗi từ trung gian, 308, cổng 80 chỉ CA, CA lạ bị từ chối, chưa có site Kuma).
  - (d) `box/ansible/roles/box-stack/templates/Caddyfile.j2` (`default_sni` dòng 13, `http_redirect` dòng 29).

### A2. Lint (giống CI + bản ansible-core 2.16 của Ubuntu 24.04)
- [x] **A2.1 Như CI** — (a) Linux có `shellcheck`, Python 3.12. (b)
  ```bash
  pip install -r requirements-dev.txt
  shellcheck -e SC2016 desktop/*.sh desktop/ansible/roles/backup-client/files/onebee-sao-luu \
    desktop/ansible/roles/ho-tro-tu-xa/files/onebee-ho-tro box/ansible/roles/box-firewall/files/onebee-tuong-lua \
    box/*.sh box/ansible/roles/box-stack/files/onebee-ca.sh tests/desktop/*.sh tests/desktop/extended/*.sh tests/box/*.sh
  yamllint . && (cd box/ansible && ansible-lint site.yml) && (cd desktop/ansible && ansible-lint site.yml)
  ```
  (c) không lỗi (đã đạt ở nơi viết với ansible-core 2.19.13). (d) —
- [x] **A2.2 ansible-core 2.16 (bản trên Box/Mint thật)** — **chưa ai chạy**. CI vẫn lint bằng 2.19 (Pha 1 chưa ghim về 2.16).
  - (a) VM Ubuntu 24.04 hoặc Mint 22.x: `sudo apt install -y ansible-core ansible-lint` (2.16.x).
  - (b)
    ```bash
    ansible --version | head -1                      # phải là core 2.16.x
    (cd box/ansible && ansible-playbook --syntax-check site.yml && ansible-lint site.yml)
    (cd desktop/ansible && ansible-playbook --syntax-check site.yml)
    ANSIBLE_ROLES_PATH=desktop/ansible/roles ansible-playbook --syntax-check -i localhost, box/ansible/roles/box-fleet/files/dong-bo-may-tram.yml
    ```
  - (c) `playbook: …` không lỗi (cảnh báo "Could not match … may_tram" là bình thường).
  - (d) Từ khóa mới hơn 2.16 (`meta: end_role` chỉ có từ 2.18); biểu thức có `\\` trong Jinja (2.16 và 2.19 xử lý khác: `dong-bo-may-tram.yml:26-31`,
    `ket-noi-box/tasks/main.yml:22`, `box-stack/tasks/main.yml` khối chép n8n).
- [x] **A2.3 Renovate đọc được `renovate.json`** (Pha 5 chưa kiểm) — (a) có `npx`. (b) `npx --yes --package renovate -- renovate-config-validator renovate.json`
  (c) `Config validated successfully`. (d) `renovate.json` (regex manager cho `group_vars/all.yml`).

### A3. Desktop trong container Mint (Docker)
- [x] **A3.1** — (a) Docker, ~3 GB trống, mạng có proxy tự ký thì `export ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt`.
  (b) `tests/desktop/run-desktop-test-in-mint-container.sh` (~2 phút) rồi `tests/desktop/run-desktop-extended-tests.sh` (~10 phút; chạy riêng: `… mint systemd`).
  (c) dòng `changed=0 … failed=0` ở lần 2, verify đạt, không `LỖI:`. **Đây là lần đầu role `ket-noi-box`, `hoi` mới, `onebee-sao-luu` (F7) chạy bằng ansible-core 2.16
  của Mint** (bộ cài cài `ansible-core` từ apt). Container không có `/etc/onebee/may-tram.env` nên nhánh CA/HTTPS chỉ được thử ở A4.
  (d) `desktop/ansible/roles/ket-noi-box/tasks/main.yml`, `ai-cli/tasks/cau-hinh-hoi.yml`.

### A4. Box đầy đủ trong container systemd + Docker lồng (quan trọng nhất)
- [ ] **A4.1 Chạy** — (a) Linux có Docker (cgroup v2, chạy được `--privileged`), **≥ 30 GB trống** (image ~6 GB + model + volume), RAM ≥ 8 GB.
  Biến: `ONEBEE_TEST_EXTRA_CA` (proxy tự ký), `ONEBEE_TEST_MODEL` (mặc định `gemma4:e2b-it-qat`; `gemma3:1b` nhanh hơn, chỉ để thử kết nối),
  `ONEBEE_TEST_FULL_WEBUI=1` (image Open WebUI đầy đủ thay `-slim`), `ONEBEE_TEST_KEEP=1` (giữ container để xem), `ONEBEE_TEST_MINT_IMAGE`.
  (b)
  ```bash
  ONEBEE_TEST_KEEP=1 tests/box/run-box-test-in-systemd-container.sh 2>&1 | tee /tmp/box-test.log
  grep -E '^(PASS|FAIL)' /tmp/box-test.log | tail -40
  ```
  (c) ~50–70 phút; dòng cuối `TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT`. Script dừng ở FAIL đầu tiên.
  (d) Xem lại: `docker ps --format '{{.Names}}' | grep onebee-` → `docker exec -it onebee-box-test-<PID> bash`; log trong container Box: `/tmp/run1.log`, `/tmp/run2.log`,
  `/root/cai-*.log` (check-https), `/root/xoay-*.log`, `/root/khoi-phuc.log`, `/var/log/onebee-box/`, `/var/log/onebee/box-install-*.log`.
  Chạy lại riêng một phần trên container đã giữ: `tests/box/check-xoay-khoa.sh onebee-box-test-<PID> onebee-may-tram-test-<PID>` (các phần phụ thuộc trạng thái
  bước trước — chỉ chạy lại phần vừa hỏng). Dọn: `docker rm -f onebee-box-test-<PID> onebee-may-tram-test-<PID>; docker network rm onebee-test-net-<PID>;
  docker volume rm onebee-box-test-<PID>-docker onebee-box-test-<PID>-containerd onebee-box-test-<PID>-sao-luu`.

- [x] **A4.2 Những bước MỚI chưa từng chạy** (bản `1.0.0-rc.1` là lần chạy đạt cuối, trước toàn bộ Pha 1–5) — đánh dấu từng bước khi thấy `PASS`:
  - [x] Cài lần 1/lần 2 `changed=0` với mã đơn vị `kiem-thu`, CA, n8n 2.42.6, digest (lần đầu ansible 2.16 chạy toàn bộ role Box mới).
  - [x] `verify-box-install.sh`: env n8n (`N8N_DISABLED_MODULES`, `NODES_EXCLUDE` có git, MCP), image có `@sha256`, env Open WebUI = false, cài đặt trong CSDL
    (`/api/v1/auths/admin/config`, `/api/v1/users/default/permissions`), `may-da-cap` gắn read-only, 3 mục CA, `in-ca`.
  - [x] `check-n8n-inside.sh`: `n8n export:workflow --id=onebeeTomTat0001` có `respondWith=text` + thoát `< >`; trang kết quả có CSP `sandbox`, không `allow-same-origin`.
  - [x] Runner: `them-may` in đủ 11 tên dòng (+ `BOX_HTTPS`); máy Mint có CA đúng vân tay + chính sách Firefox/Chromium.
  - [x] `check-quan-ly-tap-trung.sh`: báo cáo **có chữ ký**; máy chưa cấp `ke-gia` không ghi được file (quy trình 06 dùng `fileSelector`); báo cáo sai chữ ký bị nêu;
    lần đầu ghim khóa SSH sau khi chứng minh, lần 2 không ghim lại; `dong-bo-may` không lộ mật khẩu vào log; thu hồi → cấp lại `kho-02`.
  - [x] `check-khoi-phuc-toan-bo.sh`: máy `tam-01` đã thu hồi không sống lại; CA giữ nguyên sau khôi phục; Box tin CA khôi phục.
  - [x] `check-https.sh` (toàn bộ): chốt chặn `kho-03`, bật, chỉ Caddy công bố cổng, TLS không SNI ở 5 cổng, 308, `/onebee-ca.crt`, cookie Secure, CORS, CSP biểu mẫu qua Caddy,
    `dong-bo-tro-ly` qua HTTPS, máy trạm sao lưu/hoi/báo cáo qua HTTPS, Firefox dấu trang https, chạy lại `changed=0` ở HTTPS, tắt → máy trạm về HTTP.
  - [x] `check-xoay-khoa.sh` (toàn bộ): mật khẩu kho cũ 401, khóa hoi cũ hết hạn, máy nhận khóa mới; `--box`: quản trị Open WebUI/n8n mới đăng nhập được, cũ bị từ chối, biểu mẫu, `email-thu`.
- [ ] **A4.3 Rủi ro trong chính script test** (FAIL ở đây có thể là lỗi của test, không phải sản phẩm):
  - *10–11/10 (Mac):* `check-https.sh:55` (CSP trang GET biểu mẫu) **đạt** — n8n có gửi CSP `sandbox` ở trang GET. Gặp thêm 2 lỗi test ngoài danh sách dưới: **T1, T2** (đã sửa).
    `check-https.sh:53` (CORS) vẫn có thể đạt giả nếu curl lỗi — chưa sửa; xem N13.
  - `check-https.sh:55` đòi CSP `sandbox` ở trang **GET biểu mẫu** `onebee-ho-tro`; Pha 1 mới đối chiếu mã nguồn cho trang **kết quả** (completion). FAIL → kiểm bằng tay
    `curl -si -u nhanvien:<mk> https://<IP>:5678/form/onebee-ho-tro | grep -i content-security` trên Box: nếu n8n vốn không gửi CSP ở trang GET thì sửa test, không phải Caddy.
  - `check-https.sh:53` dạng `! curl | grep -q` dưới `pipefail`: curl chết SIGPIPE → `!` thành đúng → bài **đạt giả** (chỉ che lỗi, không báo sai).
    `check-https.sh:73`, `check-quan-ly-tap-trung.sh:44` có `| grep -q`/`| head` sau pipefail — nguy cơ mã 141 như commit `3061a08` (đầu ra nhỏ nên thấp).
  - `check-https.sh:70` FAIL nếu `policies.json` của gói Firefox (được trộn vào `/etc/firefox/policies/policies.json`) có sẵn URL `http://` — container Mint không có Firefox nên không lộ ra; trên Mint thật xem C1.
  - `check-https.sh:12` lấy IP bằng `ip route get 1.1.1.1`, còn bộ cài dùng `ansible_default_ipv4` (`ca.yml:26`) — trong container trùng nhau; lệch thì mọi bài TLS FAIL.
  - `check-xoay-khoa.sh:35-51` chạy `--box` khi khóa tình trạng chung còn bật nhưng **không** chạy `dong-bo-may --tat-ca` sau đó → từ bước này máy trạm báo tình trạng bị 403
    (không bước nào sau kiểm nên không FAIL; đừng chạy lại `check-quan-ly-tap-trung.sh` trên container đó).
  - Bước "KHỞI ĐỘNG LẠI BOX" cuối runner gọi `http://127.0.0.1:3000` — cần `check-https.sh` đã tắt HTTPS xong; FAIL giữa chừng ở check-https làm hỏng cả các bước sau.

---

## B. Box thật / VM Ubuntu Server 24.04 (ansible-core 2.16 của Ubuntu)
(a) chung: VM `box` Ubuntu 24.04 (4 CPU, 8–12 GB RAM, 60 GB + ổ 20 GB làm ổ sao lưu), VM `ketoan-01` Mint 22.x, mạng **Bridged**; theo `docs/huong-dan/thu-nghiem-tren-may-ao.md`
(lưu ý file đó chưa nói phải khai mã đơn vị và còn ghi "9 dòng" — xem cuối file). Chụp snapshot VM trước mỗi nhóm.

- [ ] **B1. Cài lần đầu** — (b) `sudo ./box/onebee-box-install.sh` khi `onebee_box_ma_don_vi: ""` → dừng; rồi `sed -i 's/^onebee_box_ma_don_vi: .*/onebee_box_ma_don_vi: thu-vm/' box/ansible/group_vars/all.yml`,
  chạy lại. (c) lần 1 dừng ở assert "Chưa khai onebee_box_ma_don_vi"; lần 2 xong, có `CẢNH BÁO: chưa khai onebee_box_dia_chi` khi để trống IP; `sudo onebee-box in-ca` in vân tay;
  `sudo onebee-box trang-thai` có số ngày CA. (d) `box-stack/tasks/ca.yml:13-45`, `files/onebee-ca.sh`.
- [ ] **B2. Lần 2 `changed=0`** — (b) `sudo ./box/onebee-box-install.sh 2>&1 | tail -3` (c) `changed=0 … failed=0`. (d) `grep -B2 'changed:' /var/log/onebee/box-install-*.log | tail -30`;
  hay gặp: mode thư mục `portal` (`ca.yml:69` vs `main.yml`), `Ghi đường dẫn bộ cài` (`main.yml:207`), ghi `ten-da-cap`.
- [ ] **B3. Nâng cấp từ bản cũ** (Pha 1, 5.0 "test nâng cấp" — chưa làm):
  - (b) VM sạch: `git checkout 3061a08` (n8n 2.40.7, chưa vá) → cài Box, `them-may ketoan-01`, cài máy trạm, tạo dữ liệu (chat, 1 yêu cầu hỗ trợ, 1 đơn hàng, sao lưu).
    Rồi `git checkout -- box/ansible/group_vars/all.yml && git checkout claude/confident-gauss-ntiwuc`, khai mã đơn vị, chạy bộ cài. Lặp lại từ `9ac8eee` (Box Pha 2, chưa có CA).
  - (c) có `/srv/onebee/n8n.truoc-*` (bản chép trước khi đổi image), n8n migration xong, 9 quy trình còn và chạy, dữ liệu Open WebUI còn; CA sinh mới và **tự đẩy** xuống
    `ketoan-01` (`/var/lib/onebee/ket-noi-box` = vân tay); lần chạy kế `changed=0`; máy trạm bản desktop cũ vẫn sao lưu/báo tình trạng (ma trận lệch phiên bản).
  - (d) `box-stack/tasks/main.yml` khối chép n8n (`regex_findall` — [Inference] chưa thử trên 2.16), `box-fleet/tasks/main.yml:72-77`.
- [ ] **B4. n8n 2.42.6 thật** — (b) `docker exec onebee-n8n n8n --version`; trên Mint `sudo onebee-bao-tinh-trang`; trên Box `ls -l /srv/onebee/tinh-trang-may/`;
  mở n8n → Executions của quy trình `onebeeTinhTrang1`. (c) `2.42.6`; báo cáo ghi vào `<tên>.json`; tên chưa cấp → execution lỗi "No file(s) found" và không ghi file;
  `docker logs onebee-n8n 2>&1 | grep -iE 'blocked by policy|content-import|X-Forwarded'` rỗng. (d) `06-nhan-tinh-trang-may-tram.json.j2:54` (`fileSelector`), `box-n8n/tasks/main.yml:61-73`.
- [ ] **B5. Mật khẩu chủ n8n qua `N8N_INSTANCE_OWNER_MANAGED_BY_ENV`** — (b) `sudo onebee-box xoay-khoa --box --dong-y`, đăng nhập n8n bằng `n8n-owner-password` mới (in-khoa) và thử mật khẩu cũ.
  (c) mới vào được, cũ bị từ chối. (d) n8n chỉ áp hash lúc chưa có chủ → mật khẩu cũ còn: `docker-compose.yml.j2:149-153`, `onebee-box.sh.j2:355-357`.
- [ ] **B6. Open WebUI v0.11.4 thật**
  - (b) `sudo onebee-box xoay-khoa --box --dong-y` (đổi mật khẩu quản trị qua `POST /api/v1/auths/update/password`, đổi `WEBUI_SECRET_KEY`); trước đó đăng nhập web bằng 1 tài khoản nhân viên
    và để nhân viên có khóa riêng (`hoi --dang-nhap`, C5). Kiểm thêm: Bảng quản trị → Người dùng → mở chat của nhân viên.
  - (c) mật khẩu quản trị mới dùng được/cũ bị từ chối; **mọi phiên web phải đăng nhập lại**; khóa API riêng của nhân viên **vẫn dùng được** (`hoi xin chào`); quản trị không xem/xuất được chat
    của nhân viên; `WEBUI_URL` trong Cài đặt quản trị = `https://<IP>:3000` khi HTTPS. Ghi lại nếu đổi `WEBUI_SECRET_KEY` làm hỏng gì khác (câu hỏi mở Pha 4b).
  - (d) `onebee-webui.py:191-217` (`api_key`, `update/password`), `:76-77` (`WEBUI_URL`), `env.j2:2`.
- [ ] **B7. Uptime Kuma 2.5.5 sau Caddy** — (b) bật HTTPS (B8), mở `https://<IP>:3001`; Cài đặt → Reverse Proxy; `xoay-khoa --box` rồi đăng nhập bằng `uptime-kuma-password` mới.
  (c) bảng điều khiển nạp được (không báo "Cannot connect to the socket server" — WebSocket qua Caddy, kiểm Origin); Trust Proxy = Có; mật khẩu mới vào được.
  (d) `onebee-kuma.js:34-43` (`setSettings`), `:64-68` (`changePassword`), `Caddyfile.j2:91`, `box-stack/tasks/main.yml:390-399`.
- [ ] **B8. Caddy trong mạng bridge, bật/tắt HTTPS**
  - (b) chạy `sudo onebee-box dong-bo-may --tat-ca`, đặt `onebee_box_https: true`, chạy bộ cài; rồi trên **chính Box**:
    ```bash
    IP=<ip-box>; docker port onebee-portal; for c in onebee-open-webui onebee-n8n onebee-uptime-kuma onebee-rest-server; do echo "$c: $(docker port $c)"; done
    for p in 443 3000 5678 3001 8000; do openssl s_client -connect $IP:$p -noservername -verify_ip $IP -verify_return_error </dev/null 2>&1 | grep -m1 'Verification'; done
    curl -s -o /dev/null -w '%{http_code}\n' http://$IP:3000/ ; curl -sf https://$IP:3000/health; curl -sf https://$IP:5678/healthz
    docker inspect -f '{{.HostConfig.CapDrop}} {{.HostConfig.CapAdd}} {{.HostConfig.SecurityOpt}}' onebee-portal
    ```
  - (c) chỉ portal có cổng; 5× `Verification: OK` (default_sni + hairpin từ chính Box); `308`; health trả `true`/`ok`; `[ALL] [NET_BIND_SERVICE] [no-new-privileges:true]`;
    tắt (`onebee_box_https: false`) → backend có lại cổng, máy trạm `BOX_HTTPS=0`. Chạy lại bộ cài ở mỗi chế độ: `changed=0`.
  - (d) `Caddyfile.j2:13,29,32`; tranh cổng khi chuyển: `box-stack/tasks/main.yml:265` (dừng dịch vụ giữ cổng), `:293-301` (xóa chứng chỉ + restart / reload);
    Caddy không chạy với `cap_drop ALL` + file capability của binary: `docker-compose.yml.j2:33-35`.
- [ ] **B9. WebSocket/SSE qua Caddy** — (b) Firefox trên Mint: chat có stream ở `:3000`; mở trình soạn n8n `:5678`, chạy tay 1 quy trình; Kuma như B7; DevTools → Network lọc WS.
  (c) chữ chạy dần, kết quả thực thi n8n hiện ngay, không lỗi WS/CORS. (d) `CORS_ALLOW_ORIGIN` `docker-compose.yml.j2:97`; `N8N_PROXY_HOPS`/`N8N_EDITOR_BASE_URL` `:140-144`.
- [ ] **B10. Tải lớn / chờ lâu qua Caddy** — (b) trên Mint: `dd if=/dev/urandom of=/home/<nv>/lon.bin bs=1M count=3072 && sudo onebee-sao-luu`;
  `time hoi "viết bản kế hoạch 1500 chữ về sổ sách HTX"`; tóm tắt 1 PDF 20 trang qua biểu mẫu. (c) sao lưu xong không 413/502; hoi trả lời (lưu ý `hoi` tự cắt ở 300 s:
  `ai-cli/files/hoi:233`); trang tóm tắt hiện được. (d) `Caddyfile.j2:68,76,83` (`stream_close_delay`, `max_size 256MB`); không nâng Caddy ≥ 2.11.6 (timeout idle 1 phút).
- [ ] **B11. CSP biểu mẫu, cookie Secure, CORS bằng trình duyệt** — (b) mở `https://<IP>:5678/form/onebee-ho-tro`, gửi; DevTools → Storage → Cookies của `:3000` và `:5678`;
  `curl -si -X POST https://<IP>:5678/rest/login -H 'Content-Type: application/json' -d '{"emailOrLdapLoginId":"quantri@onebee.lan","password":"<n8n-owner-password>"}' | grep -i set-cookie`.
  (c) header `content-security-policy: sandbox …` (không `allow-same-origin`); cookie `token` (Open WebUI) và `n8n-auth` có Secure. (d) `docker-compose.yml.j2:95-97,140-144`; không thêm CSP ở Caddy cho n8n.
- [ ] **B12. Hardening container (F11)** — (b)
  ```bash
  docker inspect -f '{{.Name}} restart={{.RestartCount}} ro={{.HostConfig.ReadonlyRootfs}} drop={{.HostConfig.CapDrop}} {{.HostConfig.SecurityOpt}}' $(docker ps -q)
  sudo onebee-box them-may thu-02   # rồi trên 1 máy trạm mới dán cấu hình + chạy onebee-sao-luu (rest-server tạo kho mới khi read_only + cap_drop ALL)
  docker logs onebee-rest-server --tail 20; docker logs onebee-uptime-kuma --tail 20
  ```
  (c) mọi container `restart=0`, rest-server `ro=true drop=[ALL]`, kho mới tạo được, không `permission denied`. (d) `docker-compose.yml.j2:178-194` (rest-server), entrypoint Kuma (`setpriv`).
- [ ] **B13. Tường lửa thật (F5)** — (b)
  ```bash
  sudo iptables -S INPUT | head -5; sudo iptables -S FORWARD | head -5; sudo iptables -S DOCKER-USER; sudo ip6tables -S INPUT | head -4
  sudo onebee-tuong-lua xem
  # từ máy LAN:   nc -vz <IP> 3000; nc -vz <IP> 445        từ mạng khác (Wi-Fi khách/VLAN, điện thoại 4G qua Tailscale chưa khai): phải timeout
  sudo systemctl restart docker && sleep 20 && sudo iptables -S DOCKER-USER | head -3   # quy tắc tự dựng lại (PartOf=docker)
  ```
  (c) `-j ONEBEE-LAN-DOCKER`/`ONEBEE-LAN-BOX` đứng **đầu** DOCKER-USER/INPUT; LAN vào được, ngoài bị chặn; Box tự gọi `https://<IP>:3000` vẫn được.
  (d) `box-firewall/files/onebee-tuong-lua:44-61`, `onebee-tuong-lua.service` (chỉ `After=docker.service`).
- [ ] **B14. Tailscale thật** — (a) Box + laptop kỹ thuật cùng tailnet. (b) `onebee_box_tailscale_cho_phep: []` → từ laptop `nc -vz <100.x Box> 22` và `:3000`; khai IP laptop → chạy bộ cài → thử lại;
  rồi `sudo systemctl restart tailscaled; sudo iptables -S INPUT | head -4; sudo iptables -S FORWARD | head -4`; thử từ 1 thiết bị tailnet khác.
  (c) trống: bị chặn + bộ cài cảnh báo; khai: chỉ laptop đó vào được; **sau khi restart tailscaled, quy tắc OneBee vẫn đứng trước `ts-input`/`ts-forward`** hoặc thiết bị lạ vẫn bị chặn.
  (d) thứ tự chuỗi (xem "Nghi ngờ lỗi" N6); `box-firewall/tasks/main.yml` (cảnh báo tailscale0).
- [ ] **B15. Samba SMB 3.1.1 + mã hóa (F8)** — (b) Box: `testparm -s 2>/dev/null | grep -E 'server min protocol|smb encrypt'`; Windows 10: `\\<IP>\chung` (user `onebee`, mật khẩu
  `/etc/onebee-box/secrets/samba-onebee`), PowerShell `Get-SmbConnection | Select ServerName,ShareName,Dialect,Encrypted`; Mint: Nemo `smb://<IP>/chung`, chép 1 GB vào/ra;
  Box: `sudo smbstatus`; thử hạ cấp: `smbclient //<IP>/chung -U onebee -m SMB2` và `-m NT1`.
  (c) `SMB3_11` + `required`; Windows `Dialect 3.1.1 Encrypted True`; `smbstatus` cột Encryption có `AES-…`, Protocol `SMB3_11`; SMB2/NT1 bị từ chối. Máy quét cũ: ghi model,
  thử lại với `onebee_box_samba_smb3: false`. LAN có IPv6 toàn cầu: mở bằng **tên** `\\onebee-box` có chậm không (N7).
  (d) `samba/tasks/main.yml` (blockinfile `[global]`), `onebee-tuong-lua:82-86` (IPv6 chỉ fe80/fc00).
- [ ] **B16. Khôi phục từ bản sao lưu chụp TRƯỚC khi bật HTTPS** (5.0, chưa làm) — (b) sao lưu ở HTTP → bật HTTPS → giả lập hỏng ổ (E1) → khôi phục bằng bản cũ.
  (c) Box về HTTP, bộ cài lần 2 tự `dong-bo-may` đẩy `BOX_HTTPS=0`; máy trạm có dấu `https-bat` được gỡ dấu, sao lưu lại được. (d) `onebee-box-sao-luu.sh.j2:172` (xóa dấu trước restore), `box-fleet/tasks/main.yml:75`.

---

## C. Máy trạm thật Linux Mint 22.x (Firefox deb + Chromium/Chrome)
(a) chung: `ketoan-01` đã cài OneBee với cấu hình từ `them-may`, Box ở B. Mở Firefox/Chromium **một lần** trước khi kiểm (tạo hồ sơ).

- [ ] **C1. Firefox đọc chính sách** — (b) `ls /usr/lib/firefox/distribution/; cat /etc/firefox/policies/policies.json`; Firefox → `about:policies` (tab Active + Errors).
  (c) Active có `Certificates` (Install `…/onebee-box-ca.crt`), khi HTTPS có `Homepage`, `ManagedBookmarks`; tab Errors trống; chính sách sẵn có của gói (nếu có) vẫn còn.
  (d) `ket-noi-box/files/onebee-chinh-sach-trinh-duyet.py:80-100` (trộn gói); Mint đặt Firefox ở đường dẫn khác.
- [ ] **C2. CA đã vào hồ sơ + gỡ bằng certutil** — (b)
  ```bash
  dpkg -l libnss3-tools | tail -1                                  # certutil có sẵn không (không role nào cài — N3)
  P=$(ls -d ~/.mozilla/firefox/*.default* | head -1); certutil -L -d sql:$P | grep -i onebee
  sudo cp /etc/onebee/may-tram.env /root/env.bak && sudo sed -i '/^BOX_CA/d' /etc/onebee/may-tram.env && sudo ./desktop/onebee-install.sh | grep -i 'onebee\|certutil'
  certutil -L -d sql:$P | grep -i onebee; sudo cp /root/env.bak /etc/onebee/may-tram.env   # rồi trên Box: sudo onebee-box dong-bo-may ketoan-01
  ```
  (c) trước: có dòng `OneBee Box <mã> Root CA   CT,…`; sau gỡ: in "Đã gỡ N chứng chỉ OneBee khỏi hồ sơ Firefox", certutil không còn dòng OneBee; Chromium mất file chính sách.
  (d) tên nick khác mẫu (vd thêm `#2`): `onebee-chinh-sach-trinh-duyet.py:26` (`TEN_CHUNG_CHI`), `:103-116`; thiếu certutil → chỉ cảnh báo.
- [ ] **C3. Trình duyệt/thư viện tôn trọng nameConstraints** (Pha 3 chưa kiểm: Firefox, Chromium, Go/restic, gnutls)
  - (b) Trên Box (root) dựng 2 máy chủ thử ký bằng trung gian của Box: tên **ngoài** ràng buộc (9443) và tên **trong** (9444):
    ```bash
    D=/etc/onebee-box/secrets/ca; MA=$(. $D/ca.conf; echo "$CA_MA"); mkdir -p /root/thu-nc && cd /root/thu-nc
    for ten in thu-ngoai.example box.$MA.onebee.internal; do
      openssl ecparam -name prime256v1 -genkey -noout -out $ten.key
      openssl req -new -key $ten.key -subj "/CN=$ten" -out $ten.csr
      printf 'subjectAltName=DNS:%s\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n' $ten >$ten.ext
      openssl x509 -req -in $ten.csr -CA $D/inter.crt -CAkey $D/inter.key -set_serial 0x$(openssl rand -hex 8) -days 2 -sha256 -extfile $ten.ext -out $ten.crt
    done
    openssl s_server -accept 9443 -www -cert thu-ngoai.example.crt -key thu-ngoai.example.key -cert_chain $D/inter.crt &
    openssl s_server -accept 9444 -www -cert box.$MA.onebee.internal.crt -key box.$MA.onebee.internal.key -cert_chain $D/inter.crt &
    ```
    Máy trạm: thêm vào `/etc/hosts` dòng `<IP-box> thu-ngoai.example box.<mã>.onebee.internal`, rồi
    ```bash
    CA=/usr/local/share/ca-certificates/onebee-box-ca.crt
    curl -s https://box.<mã>.onebee.internal:9444/ | head -2; curl -sv https://thu-ngoai.example:9443/ 2>&1 | grep -iE 'subtree|verify|error'
    sudo apt install -y gnutls-bin; gnutls-cli --x509cafile $CA -p 9443 thu-ngoai.example </dev/null | grep -iE 'constraint|verified|fail'
    RESTIC_CACERT=$CA RESTIC_PASSWORD=x restic -r rest:https://thu-ngoai.example:9443/x snapshots 2>&1 | grep -i x509
    ```
    Firefox + Chromium + Chrome: mở `https://box.<mã>.onebee.internal:9444` và `https://thu-ngoai.example:9443` (Firefox tắt DNS qua HTTPS nếu không phân giải `/etc/hosts`).
  - (c) 9444 vào được không cảnh báo; 9443: curl lỗi 60 "permitted subtree violation", gnutls báo không hợp lệ, restic "not permitted by any constraint",
    Firefox `SEC_ERROR_CERT_NOT_IN_NAME_SPACE`, Chromium/Chrome lỗi chứng chỉ. Ghi client nào **không** chặn → không được ghi "được bảo vệ" cho client đó (ADR 0005).
    Dọn: `kill %1 %2; rm -rf /root/thu-nc`.
  - (d) `onebee-ca.sh:36-52` (ràng buộc ở cả gốc và trung gian); Chrome `chrome://policy` → `CACertificatesWithConstraints` trạng thái OK
    (định dạng `permitted_cidrs`/`permitted_dns_names`: `onebee-chinh-sach-trinh-duyet.py:96-99`); `chrome://certificate-manager` (Chrome ≥ 131) thấy CA do quản trị cài.
- [ ] **C4. Kho hệ thống / p11-kit** — (b) `trust list --filter=ca-anchors | grep -B1 -A3 -i onebee; python3 -c "import ssl,urllib.request;print(urllib.request.urlopen('https://<IP>:3000/health',context=ssl.create_default_context()).read())"`
  (c) có anchor OneBee; Python in `{"status":true}`. (d) `ket-noi-box/tasks/main.yml:96-108` (`update-ca-certificates --fresh`).
- [ ] **C5. `hoi` theo từng nhân viên, 2 tài khoản Linux, gõ thật (getpass)** — (b) quản trị tạo 2 tài khoản Trợ lý AI (Bảng quản trị → Người dùng). Trên Mint:
  ```bash
  sudo useradd -m nv1; sudo useradd -m nv2; sudo -iu nv1 hoi --dang-nhap     # gõ email/mật khẩu nv1 (không hiện)
  sudo -iu nv1 stat -c '%a %n' .config/onebee .config/onebee/hoi-khoa; sudo -iu nv1 hoi xin chào
  sudo -iu nv2 hoi --dan-khoa        # dán khóa SAI trước → không lưu; rồi khóa đúng tạo trên web (Cài đặt → Tài khoản → Khóa API)
  sudo -iu nv2 cat /home/nv1/.config/onebee/hoi-khoa                          # phải Permission denied
  ```
  Xóa tài khoản nv2 trên web → `sudo -iu nv2 hoi xin chào`. Ở chế độ HTTP: `sudo -iu nv1 hoi --dang-nhap`.
  (c) `700`/`600`; nv1 hỏi được và **không** có dòng "(Đang dùng khóa chung của máy…)"; khóa sai: "Khóa không dùng được … chưa lưu gì"; nv2 không đọc được khóa nv1;
  tài khoản bị xóa → "Khóa Trợ lý AI không hợp lệ hoặc đã bị thu hồi"; HTTP → "Từ chối đăng nhập: địa chỉ Trợ lý AI còn là http://". Phiên web của nv2 cũng hết hiệu lực (ghi lại).
  (d) `ai-cli/files/hoi:131-169` (GET/POST `/api/v1/auths/api_key` trên v0.11.4), `onebee-webui.py:27-29` (`API_KEYS_ALLOWED_ENDPOINTS`).
- [ ] **C6. SSH kiểu socket + `dong-bo-may` bằng ansible 2.16** — (b) Mint: `systemctl is-enabled ssh.socket; systemctl is-active ssh.socket; sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin|allowusers|maxauthtries)'`;
  Box: `sudo onebee-box cap-nhat-may ketoan-01` (2 lần), `sudo onebee-box dong-bo-may ketoan-01` (2 lần). (c) `enabled/active`, `no/no/onebee-quantri/3`; lần đầu "Đã ghim khóa SSH", lần 2 không;
  dong-bo lần 2 in "Cấu hình đã đúng, không đổi". (d) `quan-ly-tap-trung/tasks/main.yml:145`, `box-fleet/files/dong-bo-may-tram.yml`.
- [ ] **C7. Máy tắt lúc Box chuyển HTTPS rồi bật lại** — (b) tắt `ketoan-01` (đã nhận CA ở Pha 3) → bật HTTPS trên Box (`onebee_box_https_bo_qua_chot_chan: true` nếu chốt chặn) → bật máy:
  `hoi xin chào; sudo onebee-bao-tinh-trang; sudo onebee-sao-luu; grep -E '^(RESTIC_REPOSITORY|BOX_HTTPS)' /etc/onebee/may-tram.env | sed 's/:[^@]*@/:***@/'`; rồi Box `sudo onebee-box dong-bo-may ketoan-01`.
  (c) `hoi` và báo tình trạng chạy được nhờ theo 308 một lần sang https cùng máy chủ; `onebee-sao-luu` (restic) **ghi lại kết quả thật** (restic tự xử lý 308, không qua mã của hoi);
  sau `dong-bo-may`: `rest:https://…`, `BOX_HTTPS=1`, có `/var/lib/onebee/https-bat`. (d) `hoi:40-49`, `onebee-bao-tinh-trang:107-116`, `backup-client/files/onebee-sao-luu`.
- [ ] **C8. Hoàn tác HTTPS trên máy thật** — (b) `onebee_box_https: false` → bộ cài Box → trên Mint `cat /var/lib/onebee/https-bat; grep BOX_HTTPS /etc/onebee/may-tram.env`, Firefox `about:policies`.
  (c) không còn dấu, `BOX_HTTPS=0`, URL http; Firefox bỏ trang chủ/dấu trang https. (d) `ket-noi-box/tasks/main.yml:53-66`, `dong-bo-may-tram.yml` khối `rescue`.

---

## D. Thiết bị ngoài quản lý
- [ ] **D1. Cài CA thủ công sau khi đối chiếu vân tay** — (a) Windows 10/11, macOS, Android, iOS. (b) Tải `http://<IP>/onebee-ca.crt`; Box `sudo onebee-box in-ca`.
  Windows: `certutil -decode onebee-ca.crt ca.der && certutil -hashfile ca.der SHA256` → cài vào *Trusted Root* (máy cục bộ); macOS: `openssl x509 -in onebee-ca.crt -outform DER | shasum -a 256`
  → Keychain *System* → Always Trust; Android: Cài đặt → Bảo mật → Mã hóa & thông tin xác thực → Cài chứng chỉ CA; iOS: cài hồ sơ + bật trong *Certificate Trust Settings*.
  (c) vân tay khớp `in-ca` (bỏ dấu `:`, không phân biệt hoa thường); mở `https://<IP>:3000` không cảnh báo. (d) `onebee-box.sh.j2` `cmd_in_ca`; trang `huong-dan-ca.html.j2`.
- [ ] **D2. Windows/macOS/điện thoại có áp nameConstraints không** — (b) dùng 2 máy chủ thử của C3, thêm dòng hosts (`C:\Windows\System32\drivers\etc\hosts`, `/etc/hosts`);
  mở bằng Edge/Chrome (kho Windows), Safari, Chrome Android. (c) 9444 vào được, 9443 bị từ chối. Thiết bị nào **không** chặn → ghi vào ADR 0005 mục rủi ro (hiện [Unverified]).
- [ ] **D3. Laptop kỹ thuật qua Tailscale** — (b) laptop: `/etc/hosts` thêm `<100.x của Box> box.<mã>.onebee.internal`; `firefox -P` tạo hồ sơ `khach-<mã>`, chỉ nhập CA khách đó
  (Cài đặt → Chứng chỉ → Nhập, tin cho trang web); mở `https://box.<mã>.onebee.internal:3000`, `:5678`, `:3001`; thử `https://<100.x>:3000`; thử Box khách khác bằng IP LAN trong hồ sơ này.
  (c) tên phụ vào được cả 3 dịch vụ (cần B14 khai IP laptop); IP 100.x trần → cảnh báo chứng chỉ (đúng thiết kế); n8n qua tên phụ: ghi lại liên kết/biểu mẫu có trỏ về IP LAN không
  (`N8N_EDITOR_BASE_URL` = IP). (d) `Caddyfile.j2` tên phụ, `docker-compose.yml.j2:97,142-143`.

---

## E. Kịch bản thảm họa / vận hành trên Box có dữ liệu thật
- [ ] **E1. Hỏng ổ Box → khôi phục toàn bộ (ở chế độ HTTPS)** — (b) theo `thu-nghiem-tren-may-ao.md` mục 4 nhưng bật HTTPS trước; ghi trước:
  `sudo cat /etc/onebee-box/secrets/ca/root.sha256; openssl s_client -connect <IP>:3000 -noservername </dev/null 2>/dev/null | openssl x509 -noout -issuer -enddate`.
  Cài lại Ubuntu + Box (cùng mã đơn vị, IP) → `sudo onebee-box khoi-phuc-toan-bo ~/khoa.txt` → chạy lại bộ cài → `sudo onebee-box khoi-phuc-thu`.
  (c) vân tay CA **giống hệt**; `https-da-bat` trở lại; chứng chỉ lá mới do trung gian khôi phục ký (issuer đúng); máy trạm không cần làm gì: `hoi`, `onebee-sao-luu`, báo tình trạng chạy;
  máy đã thu hồi không sống lại. (d) `onebee-box-sao-luu.sh.j2:167-180`; `box-stack/tasks/main.yml:293-296`.
- [ ] **E2. Xoay CA (`onebee_box_xoay_ca`)** — (b) đổi `onebee_box_ma_don_vi` (hoặc IP) **không** bật cờ → chạy bộ cài; rồi bật `onebee_box_xoay_ca: true` → chạy; đặt lại `false` → chạy.
  Trên máy trạm: `cat /var/lib/onebee/ket-noi-box`, `certutil -L -d sql:$P | grep -i onebee`. Box: `ls -d /etc/onebee-box/secrets/ca.cu-*`.
  (c) lần 1 dừng với thông báo "đặt onebee_box_xoay_ca: true"; lần 2: CA cũ cất `ca.cu-*`, CA mới tự đẩy xuống máy bật; máy tắt: bật lên → `hoi` báo
  "CHỨNG CHỈ CỦA ONEBEE BOX KHÔNG HỢP LỆ" tới khi `dong-bo-may <tên>`. Ghi lại: Firefox **còn** CA cũ không (N2); xoay khi giữ nguyên mã/IP có tác dụng không (N1).
  (d) `onebee-ca.sh:23-34`, `ca.yml:71-79`, `box-fleet/tasks/main.yml:72-77`.
- [ ] **E3. Xoay khóa trên Box có dữ liệu thật** — (b) `sudo onebee-box xoay-khoa --tat-ca --box` (gõ `xoay khoa`), có 1 máy đang tắt; sau đó `sudo onebee-box dong-bo-may --tat-ca`; `sudo onebee-box in-khoa`.
  (c) máy bật nhận mật khẩu kho + khóa hoi mới và sao lưu được; máy tắt mất quyền sao lưu tới khi `dong-bo-may <tên>`; biểu mẫu chỉ nhận mật khẩu mới; báo tình trạng hết 403 sau
  `dong-bo-may --tat-ca`; log `/var/log/onebee-box/` không chứa mật khẩu; nhân viên phải đăng nhập web lại. (d) `onebee-box.sh.j2:330-402`.
- [ ] **E4. Thu hồi → cấp lại máy** — (b) `sudo onebee-box thu-hoi-may ketoan-01` → máy: `sudo onebee-sao-luu`, `hoi xin chào` → `sudo onebee-box sao-luu` →
  `sudo onebee-box them-may ketoan-01` → dán cấu hình mới, chạy bộ cài desktop → `sudo onebee-box cap-nhat-may ketoan-01`.
  (c) sau thu hồi: sao lưu 401, khóa máy hoi bị từ chối, máy biến khỏi `may-tram`; cấp lại: **mật khẩu kho mới**, kho cũ cất `/srv/onebee/restic/ketoan-01.cu-*`, ghim SSH lại sau khi chứng minh.
  (d) `onebee-box.sh.j2` `cmd_thu_hoi_may`, `cmd_them_may:108-118`.
- [ ] **E5. CA trung gian sắp hết hạn** — (b) giả lập trung gian còn 10 ngày (như `tests/box/test_onebee_box_shell.py::lam_trung_gian_sap_het_han`), trên Box:
  ```bash
  sudo -i; D=/etc/onebee-box/secrets/ca; . $D/ca.conf; cp -a $D/inter.crt /root/inter.crt.bak
  openssl req -new -key $D/inter.key -subj "/CN=cu" -out /tmp/i.csr
  printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nnameConstraints=critical,permitted;IP:%s/255.255.255.255,permitted;DNS:%s.onebee.internal\n' "$CA_IP" "$CA_MA" >/tmp/i.ext
  openssl x509 -req -in /tmp/i.csr -CA $D/root.crt -CAkey $D/root.key -set_serial 0x$(openssl rand -hex 8) -days 10 -extfile /tmp/i.ext -out $D/inter.crt
  onebee-box trang-thai | grep -i 'CA'; onebee-box gia-han-ca
  openssl s_client -connect $CA_IP:3000 -noservername -showcerts </dev/null 2>/dev/null | grep -A1 'Intermediate' | head -4
  ```
  Lặp lại khi **không gắn ổ sao lưu** và để lịch sao lưu đêm chạy (`journalctl -u 'onebee-box*' --since today`).
  (c) `trang-thai` hiện ~10 ngày; `gia-han-ca` in "đã đổi", Caddy khởi động lại và gửi trung gian mới (hạn ~1 năm); máy trạm không lỗi. Không ổ sao lưu: **không** tự gia hạn (N4).
  (d) `onebee-box-common.sh.j2:102-110` (`gia_han_ca`), `onebee-box-sao-luu.sh.j2:46-57`.

---

## F. Việc CHƯA làm (có lý do) và rủi ro còn lại
- [ ] Đã đọc và chấp nhận danh sách dưới đây (nguồn: "Trạng thái triển khai" Pha 1–5).

| Việc chưa làm | Lý do ghi trong kế hoạch |
|---|---|
| F9: tài khoản biểu mẫu theo phòng/người | Form Trigger chỉ có 1 credential basic-auth; theo người cần `n8nUserAuth` — quyết định thiết kế riêng, liên quan GHSA-3qcw |
| Siết `N8N_CONTENT_SECURITY_POLICY` | n8n tự đặt CSP sandbox cho biểu mẫu; chưa có bằng chứng cần thêm |
| `doi-khoa-quan-tri` (xoay khóa SSH quản trị) | cần giai đoạn 2 khóa song song trong `authorized_keys` (dong-bo-may đẩy bằng chính khóa đang xoay) |
| F13: ký bản phát hành (minisign/cosign) | chưa chọn công cụ và nơi giữ khóa ký |
| Cờ `ONEBEE_TOI_THIEU` (desktop tối thiểu) | hoãn từ Pha 2 |
| Snapshot restic tag `truoc-nang-cap` + `--keep-tag` | chỉ có bản chép cục bộ `n8n.truoc-*` (đủ hoàn tác n8n) |
| Nâng Ollama 0.40, quét image rest-server, tắt thêm mô-đun n8n | cần kế hoạch (lùi bản phải tải lại model) |
| Bỏ khóa máy `hoi` và khóa tình trạng chung | 2 biến chuyển tiếp mặc định `true` để máy desktop cũ không gãy |
| Xóa credential `onebeeTram000001` khỏi CSDL n8n | CLI n8n không có lệnh xóa credential — xóa tay trên giao diện |
| `xoay-khoa --box` không xoay Samba, `restic-box`, khóa SSH quản trị | thuộc Pha 5+ |
| Lệnh `onebee-box doi-ca` | thay bằng biến `onebee_box_xoay_ca` (xem N1) |
| Kuma `editMonitor`, ghim subnet + `FORWARDED_ALLOW_IPS`, cảnh báo CA trong email quy trình 01 | YAGNI / chưa có bằng chứng cần; cảnh báo CA nằm trong log sao lưu + `trang-thai` |
| `SecurityDevices`/p11-kit cho Firefox | dùng `Certificates.Install` + `certutil -D` |
| Mặc định `onebee_box_https: false` | đổi mặc định ở bản sau, sau khi phiếu này đạt |
| Ghim ansible-lint về ansible-core 2.16 trong CI | CI vẫn `ansible-core==2.19.13` (`requirements-dev.txt`) |
| Hạ sudo `NOPASSWD: ALL` của `onebee-quantri` | chấp nhận theo F4 |

**Rủi ro còn lại (chấp nhận/đã ghi):** chiếm Box = root mọi máy trạm + cài được CA tùy ý (F4); người dùng bấm qua cảnh báo chứng chỉ giả / gõ tay `http://` (không có HSTS cho IP, không bật
HTTPS-Only vì máy in); cookie dùng chung giữa các cổng cùng IP; JWT 30 ngày không thu hồi riêng lẻ (chỉ hủy tất cả bằng đổi `WEBUI_SECRET_KEY`); quản trị đặt lại mật khẩu nhân viên
rồi đọc chat; khóa máy `hoi` đọc được bởi mọi tài khoản trên máy (F10) tới khi đặt `onebee_box_hoi_khoa_may: false`; khóa SSH quản trị chưa xoay được; bản phát hành chưa ký;
thiết bị chưa kiểm C3/D2 có thể không áp ràng buộc tên; Caddy kẹt ở 2.11.4 tới khi thử timeout idle.

---

## Nghi ngờ lỗi cần xác nhận (đọc `git diff 1e0e7f4..HEAD`, Pha 4b/4c/5)
Ký hiệu: **XÁC NHẬN** = thấy rõ trong code (đã chạy thử nếu ghi), **NGHI NGỜ** = cần máy thật để biết.

- **N1 — XÁC NHẬN (đã chạy `onebee-ca.sh` thử): `onebee_box_xoay_ca: true` không xoay CA khi mã/IP giữ nguyên.** `group_vars/all.yml:119-122` nói dùng cả khi "nghi lộ khóa CA",
  nhưng `onebee-ca.sh:26-33` chỉ cất CA cũ khi `CA_MA`/`CA_IP` khác; giữ nguyên mã/IP + `--xoay` → không đổi gì, `rc=0`, vân tay như cũ. Hệ quả: không có đường xoay CA khi lộ khóa
  (quy trình F4 5.8 "doi-ca"). Sửa: biến một lần dạng chuỗi (vd `onebee_box_xoay_ca: "2026-10-10"`) lưu vào `ca.conf` (`CA_XOAY=`); khác giá trị đã lưu thì xoay, giữ tính idempotent.
- **N2 — XÁC NHẬN: xoay CA không gỡ CA cũ khỏi hồ sơ Firefox.** `ket-noi-box/tasks/main.yml:111-120` chỉ chạy `onebee-chinh-sach-trinh-duyet.py cai`; `go_khoi_ho_so_firefox`
  (`onebee-chinh-sach-trinh-duyet.py:103-116`) chỉ gọi trong `go` (`:119`, khi mất `BOX_CA`). `Certificates.Install` đã nạp CA cũ vào `cert9.db` và Firefox không tự gỡ → sau xoay vì lộ khóa,
  Firefox vẫn tin CA cũ. Thêm nữa `go` xóa theo **tên** `OneBee Box <mã> Root CA` — trùng tên với CA mới khi mã không đổi. Sửa: khi `/var/lib/onebee/ket-noi-box` (vân tay cũ) khác
  `BOX_CA_VAN_TAY` mới → xóa trong mọi hồ sơ chứng chỉ có SHA-256 = vân tay cũ (`certutil -L -n <nick> -a | openssl x509 -outform DER | sha256sum`), rồi mới cài.
- **N3 — NGHI NGỜ (cao): `certutil` không có trên máy trạm.** Không role nào cài `libnss3-tools` (`grep -rn libnss3-tools desktop/` rỗng) → `go` chỉ in cảnh báo, CA ở lại Firefox.
  Kiểm `dpkg -l libnss3-tools` trên Mint thật (C2). Sửa: thêm gói vào role `ket-noi-box`.
- **N4 — XÁC NHẬN: gia hạn CA trung gian "mỗi đêm" chỉ chạy khi đã gắn ổ sao lưu và đã `khoi-tao`.** `onebee-box-sao-luu.sh.j2:47-49` (`require_backup_disk`, `restic cat config || die`)
  đứng trước khối gia hạn `:52-57`; Box chưa gắn ổ → không gia hạn, không cảnh báo < 30 ngày; sau 1 năm HTTPS hỏng nếu không ai chạy bộ cài. Tài liệu nói ngược:
  `cai-dat-onebee-box.md:61`, ADR 0005 dòng 16. Sửa: đưa khối CA lên trước `require_backup_disk`, hoặc timer riêng `onebee-box gia-han-ca` hằng ngày.
- **N5 — XÁC NHẬN (mức thấp): `hoi --dan-khoa` với cấu hình còn `http://` khi Box đã HTTPS.** Lời gọi GET `/api/models` (`hoi:164`) được `urllib` **tự theo** 308 (Python ≥ 3.11)
  bằng ngữ cảnh SSL mặc định (mọi CA công cộng) tới bất kỳ máy chủ nào trong `Location`, kèm `Authorization` — đi vòng quy tắc "chỉ https cùng máy chủ, chỉ CA OneBee" của `mo()`
  (`hoi:40-49`; nhánh tự viết chỉ chạy cho POST). Tác động thấp (lời gọi đầu đã là http rõ). Sửa: `build_opener` với `HTTPRedirectHandler` không theo chuyển hướng + `HTTPSHandler(context=…)`.
  Cùng mẫu trong `onebee-bao-tinh-trang` chỉ dùng POST nên không bị.
- **N6 — NGHI NGỜ: Tailscale chen trước quy tắc OneBee.** `onebee-tuong-lua:58-60` chèn ở vị trí 1 khi chạy; `onebee-tuong-lua.service` chỉ `After=docker.service`, không theo `tailscaled`.
  tailscaled (khi khởi động/khởi động lại) cũng chèn `ts-input`/`ts-forward` lên đầu INPUT/FORWARD; nếu các chuỗi đó ACCEPT gói từ `tailscale0` thì thiết bị tailnet bất kỳ vào được Box,
  vô hiệu `onebee_box_tailscale_cho_phep`. Kiểm ở B14. Sửa (nếu đúng): unit thêm `After=tailscaled.service` + `PartOf`, hoặc chặn trong `ts-input` không được → dùng ACL Tailscale bắt buộc.
- **N7 — NGHI NGỜ: SSH/Samba qua IPv6 toàn cầu bị DROP** (`onebee-tuong-lua:84-85` chỉ cho `fe80::/10,fc00::/7`). LAN có IPv6 của nhà mạng → Windows mở `\\onebee-box` bằng IPv6 trước,
  bị DROP (timeout) rồi mới lùi IPv4 → chậm/"không vào được". Kiểm ở B15; sửa: cho phép tiền tố IPv6 của cổng mạng chính hoặc dùng REJECT thay DROP cho IPv6.
- **N8 — XÁC NHẬN (vận hành): `xoay-khoa --box` khi khóa tình trạng chung còn bật** xóa `tinh-trang-key` (`onebee-box.sh.j2:359`) nhưng bộ cài chỉ tự `dong-bo-may` khi CA/HTTPS đổi
  (`box-fleet/tasks/main.yml:75`) → mọi máy báo tình trạng bị 403 tới khi quản trị nhớ chạy `dong-bo-may --tat-ca` (chỉ có dòng "LƯU Ý"). Sửa: `cmd_xoay_khoa` tự gọi
  `dong-bo-may --tat-ca` khi `TINH_TRANG_KHOA_CHUNG=true` và `--box`.
- **N9 — XÁC NHẬN (thấp): `xoay-khoa --may <máy-đang-tắt>`** — mật khẩu kho đã đổi (`xoay_khoa_may`) rồi `cmd_dong_bo_may_da_chon` gặp `die "Không có máy nào để làm"`
  (`onebee-box.sh.j2:277`) → thoát mã 1 ngay, `|| warn …` ở `:400` không chạy được (die = `exit`), thông báo không nói "máy chưa nhận mật khẩu mới". `xoay-khoa` cũng không dùng `with_lock`
  (chạy trùng `sao-luu` 23:00 thì bộ cài tạo lại container đang bị `compose pause`).
- **N10 — Tài liệu không khớp code (XÁC NHẬN):**
  - `docs/huong-dan/cai-dat-onebee-box.md:91`, `thu-nghiem-tren-may-ao.md:38`: "9 dòng" — nay `them-may` in **12 dòng** (thêm `BOX_CA`, `BOX_CA_VAN_TAY`, `BOX_HTTPS`; không có `HOI_API_KEY`/`TINH_TRANG_KEY` khi tắt 2 biến chuyển tiếp).
  - `thu-nghiem-tren-may-ao.md` mục 1 không bảo khai `onebee_box_ma_don_vi` → bộ cài dừng ở `ca.yml:13-23`. `cai-dat-onebee-box.md:30` "bộ cài dừng nếu thiếu" — với `onebee_box_dia_chi` chỉ cảnh báo (`ca.yml:39-45`).
  - `quan-ly-may-tram.md:75-77` và chú thích `onebee-box.sh.j2:299-300`: "file sinh từ cấu hình do bộ cài desktop tạo lại — chạy lại bộ cài" — từ Pha 3 `dong-bo-may-tram.yml:126-140`
    đã tự chạy `cau-hinh-hoi`/`muc-menu`/`ket-noi-box`.
  - `cai-dat-onebee-box.md:61` + ADR 0005 dòng 16: "gia hạn tự động mỗi đêm" (xem N4). `security-audit.md` 5.8 nêu `doi-khoa-quan-tri`, `doi-ca` — chưa có lệnh này; dòng 42 còn ghi "Pha 2–5 vẫn là kế hoạch".
  - `group_vars/all.yml:119` "hoặc nghi lộ khóa CA" (xem N1).

- **N13 — XÁC NHẬN (Mac, chế độ HTTP): Open WebUI phản chiếu mọi `Origin` kèm `access-control-allow-credentials: true`.**
  `curl -si http://127.0.0.1:3000/api/config -H 'Origin: https://ke-la.example'` → `access-control-allow-origin: https://ke-la.example` + `allow-credentials: true`.
  `CORS_ALLOW_ORIGIN` chỉ đặt khi bật HTTPS (`docker-compose.yml.j2:94-97`); ở HTTP Open WebUI dùng mặc định. [Inference] tác động bị giới hạn bởi SameSite của cookie
  (chưa kiểm), nhưng một trang web lạ mở trên máy trạm có thể đọc API bằng phiên đăng nhập nếu cookie được gửi. Đề xuất: đặt `CORS_ALLOW_ORIGIN=http://<IP>:3000` cả ở chế độ HTTP.
  Kèm: `check-https.sh:53` (`! curl … | grep -qi`) đạt giả nếu curl lỗi — nên kiểm mã HTTP trước.

## Đã sửa sau khi lập phiếu này
- **N11 (sản phẩm, bắt được ở A4 trên Mac) — mật khẩu kho HTTP cũ / máy đã thu hồi vẫn vào được kho sao lưu thêm ≥ 30 giây.** rest-server 0.14 chỉ tự kiểm
  `.htpasswd` tối đa 30 giây/lần và nhớ mật khẩu đã đúng (`htpasswd.go`: `CheckInterval`, `PasswordCacheDuration`). Đo trên Box test: sau khi đổi mật khẩu, mật khẩu cũ vẫn `405`
  (vào được) quá 30 giây. Sửa (`6167d74`): `nap_lai_kho_http` (SIGHUP) sau `them-may`, `thu-hoi-may`, `xoay-khoa --may`, `khoi-phuc-toan-bo`; có test hồi quy trong `test_onebee_box_shell.py`.
- **N12 (sản phẩm, do bản sửa N11 đầu tiên) — `docker kill -s HUP` làm kho sao lưu không tự chạy lại sau khi khởi động lại Box.** Docker 29.1.3 ghi
  `HasBeenManuallyStopped=true` cho mọi `docker kill` → `restart: unless-stopped` không áp dụng; verify sau khởi động lại FAIL "Container onebee-rest-server đang chạy".
  Sửa (`29cabd8`): `docker exec onebee-rest-server kill -HUP 1` (đo: mật khẩu cũ `401` sau 1 giây, cờ vẫn `false`); test hồi quy cấm `docker kill`.
- **T1 (test) — runner grep tên task cũ** "Khởi động lại giám sát với cổng mới"; task đã đổi tên ở Pha 5 → FAIL giả ở lần cài 1 dù Kuma đã mở `0.0.0.0:3001`. Sửa `6cf688a`.
- **T2 (test) — `check-xoay-khoa.sh` đạt giả.** Khối máy trạm chạy bằng `docker exec -i … bash -s` + heredoc; `su - nhanvien -c hoi …` đọc stdin nên nuốt các dòng sau
  (dòng PASS "Máy trạm nhận mật khẩu + khóa mới…" chưa từng in) mà khối vẫn thoát 0. Sửa `9a8b950` (`bash -c "$(cat)"`); chạy lại trên Mac: dòng PASS đã in.
- **N1:** `onebee-ca.sh --xoay` nay luôn xoay (kể cả khi mã/IP không đổi) — có test `test_xoay_khi_ma_va_ip_khong_doi_van_xoay_de_ung_pho_lo_khoa`.
- **N3:** role `ket-noi-box` cài `libnss3-tools` (có `certutil`).
- **N10 (một phần):** hướng dẫn nói 12 dòng cấu hình và nhắc khai `onebee_box_ma_don_vi`/`onebee_box_dia_chi` trước khi cài. Phần còn lại (N2, N4–N9, lệnh `doi-ca`/`doi-khoa-quan-tri` chưa có) vẫn mở.
