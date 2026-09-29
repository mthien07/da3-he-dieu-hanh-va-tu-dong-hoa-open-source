# Code review — Phase 04 (quản lý tập trung, hỗ trợ từ xa, đo đạc)

Phạm vi: `git diff main...HEAD` trên `feat/phase-04-cai-hang-loat-quan-ly-tap-trung` (2 commit wip; không có thay đổi chưa commit).
Không chạy docker. Đã kiểm: parse/render Jinja cho mọi `.j2` thay đổi, render thử bằng `ansible -m template`, `bash -n` +
shellcheck các script, `py_compile`, unit test `tests/box/test_onebee_may_tram.py` (6/6 đạt), đọc mã x11vnc (LibVNC/x11vnc)
và OpenSSH 9.6p1 để kiểm hành vi `-timeout`/`-once`/`sshd -t`.

## Tóm tắt

| # | Mức | Vị trí | Vấn đề |
|---|---|---|---|
| 1 | CRITICAL (đã xác nhận) | `box/ansible/roles/box-stack/templates/onebee-box.sh.j2:76` | `${#ten[@]}` mở comment Jinja `{#` → cài Box lỗi |
| 2 | CRITICAL (đã xác nhận) | `onebee-box.sh.j2` (them-may, dòng `QUAN_TRI_SSH_KEY=`) + `desktop/.../backup-client/files/onebee-sao-luu:11` | Dòng khóa SSH có dấu cách, `onebee-sao-luu` source file → exit 127 → mọi máy trạm ngừng sao lưu |
| 3 | MEDIUM | `onebee-box.sh.j2` `cmd_cap_nhat_may` + `onebee-may-tram.py` `kho` + `them-may` `ssh-keygen -R` | Địa chỉ SSH lấy từ báo cáo tự khai (khóa chung, không kiểm độ cũ) + `accept-new` → ghim nhầm host key / cập nhật nhầm máy |
| 4 | MEDIUM | `box-fleet/tasks/main.yml`, `group_vars/all.yml` (`onebee_box_ssh_dir`) | Khóa SSH quản trị không nằm trong bản sao lưu Box / `in-khoa` → dựng lại Box là mất quyền vào mọi máy trạm |
| 5 | LOW (có thể xảy ra) | `desktop/.../quan-ly-tap-trung/tasks/main.yml:89-91` | `sshd -t` báo lỗi "Missing privilege separation directory: /run/sshd" khi chưa có /run/sshd → bộ cài dừng |
| 6 | LOW | `onebee-box.sh.j2` `ANSIBLE_SSH_ARGS` | Không có SSH keepalive → máy trạm ngủ/mất mạng giữa chừng thì `cap-nhat-may` có thể treo lâu |
| 7 | LOW | `06-nhan-tinh-trang-may-tram.json.j2` | Ai có khóa chung cũng tạo được số file `<tên>.json` không giới hạn |
| 8 | LOW | `quan-ly-tap-trung/tasks/main.yml:66-68` | Bỏ qua cấu hình SSH mà không báo gì khi `BOX_IP` là tên miền / khóa sai định dạng |
| 9 | LOW | `tests/do-dac/do-may.py` `mo_ung_dung` | LibreOffice/Firefox đang mở sẵn thì số "tự đo" ra ~0 giây |
| 10 | LOW | `onebee-box-sao-luu.sh.j2` `gio_sao_luu_may` | restic lỗi (ví dụ kho đang khóa lúc prune) bị báo thành "chưa từng sao lưu" |

## Chi tiết

### 1. CRITICAL — Jinja coi `{#` là mở comment, template onebee-box không render được
`onebee-box.sh.j2:76`: `[[ ${#ten[@]} -gt 0 ]] || die ...`. Trong file `.j2`, `{#` mở comment Jinja, mà không có `#}` nào đóng lại.
Đã xác nhận: `jinja2.Environment().parse()` → `TemplateSyntaxError: Missing end of comment tag`; và
`ansible localhost -m template -a src=.../onebee-box.sh.j2` → `Task failed: Syntax error in template: Missing end of comment tag`.
**Hậu quả:** bộ cài Box dừng ở role box-stack (cài mới lẫn cài lại). Test tích hợp đang chạy sẽ hỏng ở bước này.
**Sửa:** tránh chuỗi `{#`, ví dụ `[[ -n "${ten[*]:-}" ]] || die ...` hoặc `(( ${{ '{#' }}ten[@]} > 0 ))`. Thêm vào CI một bước
parse mọi `*.j2` (`python3 -c 'import jinja2,sys; [jinja2.Environment().parse(open(f).read()) for f in sys.argv[1:]]' $(git ls-files '*.j2')`).

### 2. CRITICAL — `QUAN_TRI_SSH_KEY=` không có ngoặc, làm hỏng lúc bash source `may-tram.env`
`them-may` in ra `QUAN_TRI_SSH_KEY=ssh-ed25519 AAAAC3... onebee-box-<host>` (không có ngoặc). `onebee-sao-luu` (đang chạy với
`set -euo pipefail`) chạy `set -a; . /etc/onebee/may-tram.env`, nên bash hiểu dòng này là "chạy lệnh `AAAAC3...` với biến
QUAN_TRI_SSH_KEY=ssh-ed25519" → `command not found`, exit 127 → script thoát trước khi gọi `restic`. Đã chạy thử với đúng
`set -euo pipefail` → `exit=127`.
**Hậu quả:** mọi máy trạm dán cấu hình Phase 4 đều **ngừng sao lưu hằng ngày**, lỗi xảy ra âm thầm (một unit systemd bị failed).
Box sẽ báo "quá 3 ngày chưa sao lưu" sau 3 ngày. Test tích hợp cũng hỏng ở `onebee-sao-luu | tail -1`
(`run-box-test-in-systemd-container.sh` ~dòng 103) và ở `set -a; . /etc/onebee/may-tram.env` (dòng 116, 155).
(`check-quan-ly-tap-trung.sh:14` vẫn đạt, vì trong `$(...)` không kế thừa `-e`.)
**Sửa (nên làm cả hai):**
- `onebee-sao-luu`: đừng source cả file. Chỉ nạp các dòng RESTIC_ và bỏ CR:
  `set -a; . <(grep -E '^RESTIC_(REPOSITORY|PASSWORD)=' "${CONF}" | tr -d '\r'); set +a`. Cách này cũng sửa luôn lỗi dán file
  CRLF, vốn có từ Phase 2 (RESTIC_PASSWORD bị dính `\r`). Hai test ở dòng 116/155 sửa tương tự.
- Hoặc/và `them-may` in giá trị có ngoặc: `QUAN_TRI_SSH_KEY="ssh-ed25519 ..."`. `onebee-bao-tinh-trang` đã tự bỏ `"`, nhưng
  regex Ansible `^([A-Z_]+)=(.*?)\s*$` thì giữ lại ngoặc → phải đổi thành `^([A-Z_]+)="?(.*?)"?\s*$`, nếu không thì
  `is match('ssh-ed25519 ')` sai và khối SSH bị bỏ qua mà không báo gì.

### 3. MEDIUM — Box SSH tới IP do máy trạm tự khai; `accept-new` ghim host key theo kiểu TOFU (tin lần đầu)
`cmd_cap_nhat_may` lấy `ansible_host` từ `<tên>.json`. File này ai giữ khóa chung `TINH_TRANG_KEY` cũng ghi được (ADR đã nêu),
và `kho` không kiểm `nhan_luc` (báo cáo cũ bao lâu vẫn dùng). Host key được ghim theo `HostKeyAlias=<tên>` với
`StrictHostKeyChecking=accept-new`, còn `them-may` luôn chạy `ssh-keygen -R <tên>` (xóa khóa đã ghim) mỗi lần in lại cấu hình.
Các tình huống cụ thể:
- **DHCP:** máy `kho-02` tắt nhiều ngày, IP cũ đã cấp cho `ketoan-01`. Lần đầu chạy `cap-nhat-may kho-02` (hoặc lần đầu sau khi
  `them-may`), known_hosts chưa có khóa nào → `accept-new` ghim khóa của **ketoan-01** dưới tên `kho-02`. Vì mọi máy tin cùng một
  khóa Box, playbook chạy trên nhầm máy mà vẫn báo `ok`. Khi `kho-02` thật xuất hiện lại thì gặp "REMOTE HOST IDENTIFICATION HAS
  CHANGED" cho tới khi chạy lại `them-may` và dán lại cấu hình.
- **Giả mạo:** root trên một máy trạm (người dùng Mint mặc định có sudo) POST `{"ten":"kho-02","ip":"<IP của nó>"}` → Box kết nối
  tới máy đó và ghim khóa của nó. Khóa riêng của Box không bị lộ (xác thực bằng khóa công khai), nhưng máy thật bị chặn cập nhật
  và báo cáo tình trạng thì sai lệch.
**Sửa:** (a) `kho` bỏ qua báo cáo cũ hơn ~2 giờ (hoặc NGUONG_IM_LANG_GIO) kèm cảnh báo "địa chỉ cũ". (b) Thêm task đầu playbook
kiểm tên máy: `command: grep -qx 'MAY_TRAM={{ inventory_hostname }}' /etc/onebee/may-tram.env` (failed_when khác 0). Như vậy
không cập nhật nhầm máy, dù khóa sai vẫn đã bị ghim. (c) Tốt nhất: khóa gửi tình trạng riêng cho từng máy, ví dụ
`TINH_TRANG_KEY = HMAC(master, ten)`; n8n Code tính lại HMAC (cần `NODE_FUNCTION_ALLOW_BUILTIN=crypto`), hoặc Box lưu hash từng
máy. Máy trạm gửi kèm `/etc/ssh/ssh_host_ed25519_key.pub` để Box ghi known_hosts từ đó, thay cho TOFU. (d) `them-may` chỉ xóa
known_hosts khi có cờ riêng (ví dụ `--cai-lai`), đừng xóa mỗi lần in lại cấu hình.

### 4. MEDIUM — Khóa SSH quản trị không có trong bản sao lưu Box
`onebee_box_ssh_dir=/etc/onebee-box/ssh` nằm ngoài `${SECRETS}` (`/etc/onebee-box/secrets`). `cmd_sao_luu` chỉ sao lưu `${SECRETS}`,
còn `in-khoa` cũng chỉ in `${SECRETS}/*`. Khi ổ Box hỏng và phải cài lại rồi khôi phục, bộ cài sinh khóa mới, trong khi mọi máy trạm
vẫn chỉ tin khóa cũ (`authorized_keys`). Kết quả: `cap-nhat-may` bị từ chối trên cả đơn vị, phải `them-may` + dán cấu hình + chạy
lại bộ cài trên từng máy.
**Sửa:** thêm `${SSH_DIR}` vào `restic backup` của Box (hoặc để khóa trong `${SECRETS}/ssh/`). Nếu khôi phục được thì dùng lại
khóa cũ, tức task `creates:` phải chạy sau bước khôi phục. Ghi quy trình vào tài liệu khôi phục Box.

### 5. LOW (có thể xảy ra, chưa kiểm được trên máy thật) — `sshd -t` cần /run/sshd
OpenSSH 9.6p1 `sshd.c:1986` gọi `fatal("Missing privilege separation directory")` **trước** `if (test_flag) exit(0)` (dòng 2004).
Trên Ubuntu 24.04/Mint 22 chạy theo kiểu socket-activation, `/run/sshd` do `ssh.service` (RuntimeDirectory) tạo ra khi có kết nối
đầu tiên. Máy vừa cài `openssh-server`, hoặc môi trường chroot/container, có thể chưa có thư mục này, và `sshd -t` làm bộ cài dừng
(test đã phải `mkdir -p /run/sshd` trước khi chạy `sshd -T`).
**Sửa:** thêm task `ansible.builtin.file: path=/run/sshd state=directory mode=0755` trước `sshd -t` (vô hại, idempotent).

### 6. LOW — `cap-nhat-may` không có keepalive
`ANSIBLE_SSH_ARGS` chỉ có `ConnectTimeout`. Nếu máy trạm ngủ hoặc mất mạng giữa lúc `apt dist-upgrade` (có thể kéo dài nhiều phút),
kết nối TCP treo mà không lỗi và `--tat-ca` bị kẹt. **Sửa:** thêm `-o ServerAliveInterval=30 -o ServerAliveCountMax=6`.

### 7. LOW — Webhook cho tạo không giới hạn tên
Regex tên chặn được path traversal nhưng không giới hạn số lượng: ai có khóa chung cũng tạo được vô số `<tên>.json`, làm đầy
`/srv/onebee` và inode. **Sửa:** khi `them-may`, Box ghi file đánh dấu (ví dụ `tinh-trang-may/.cap/<tên>`) và n8n chỉ ghi khi có
file đó (thêm 1 node đọc file hoặc kiểm tra trong Code node), hoặc chấp nhận rủi ro và ghi vào ADR.

### 8. LOW — Khối SSH bị bỏ qua mà không báo
`when: ... BOX_IP is match('^[0-9.]+$')`. Nếu `onebee_box_address` được đặt là tên miền, hoặc khóa bị dán lệch (xem #2), thì
máy trạm không cài `onebee-quantri` và không có dòng báo nào; lỗi chỉ lộ ra khi `cap-nhat-may` báo unreachable/permission denied.
**Sửa:** thêm task `debug`/`fail` khi `QUAN_TRI_SSH_KEY` có mặt mà điều kiện sai.

### 9. LOW — `do-may.py` đo sai khi ứng dụng đang mở
`mo_ung_dung` tìm cửa sổ theo tên ngay sau khi Popen. Nếu Firefox/LibreOffice đã mở sẵn (process mới chuyển yêu cầu cho instance
cũ rồi thoát), cửa sổ cũ khớp ngay → ~0.2 s, và `killpg` không đóng được cửa sổ mới. **Sửa:** trước khi mở, nếu đã có cửa sổ khớp
thì trả `""` và thêm ghi chú "ứng dụng đang mở — không đo".

### 10. LOW — Lỗi restic bị báo thành "chưa từng sao lưu"
`gio_sao_luu_may`: `restic snapshots ... | python3 ... || echo null`. Nếu kho đang bị khóa độc quyền (prune lúc 23:00) hoặc
đọc lỗi thì in `null` → `may-tram` và email báo "chưa từng sao lưu lên Box". Logic này có từ Phase 3, nhưng nay lộ ra qua lệnh
`may-tram` chạy tay bất kỳ lúc nào. **Sửa:** phân biệt "lỗi đọc kho" (ví dụ in `loi`) với "chưa có snapshot"; có thể thêm `--no-lock`.

## Các điểm đã kiểm là ổn
- Inventory: tên máy qua regex `^[a-z0-9][a-z0-9-]{0,31}$`, còn IP được `ipaddress.IPv4Address` kiểm cả ở n8n lẫn `kho`, nên không
  chèn được gì vào INI/shell. Test đơn vị có ca `ip="10.0.0.7; rm -rf /"`.
- n8n 06: `{{ '{{' }} $json.ten {{ '}}' }}` render ra `{{ $json.ten }}`; JSON sau render hợp lệ; `to_json` escape đúng mã JS.
- Không lộ bí mật qua `ps`/log: khóa tình trạng đi trong header (Python) và `curl -H @file`; x11vnc dùng `-passwdfile rm:`;
  chuỗi `-accept` chỉ nội suy `$RFB_CLIENT_IP` (IP do x11vnc tự lấy).
- x11vnc: theo mã nguồn, `-timeout` vẫn đóng phiên khi chỉ có client bị từ chối (`No valid client after t+3 secs`). Mặc định
  `neverShared + dontDisconnect + connect_once` → sau khi đã chấp nhận 1 client thì client khác bị từ chối trước cả hộp thoại hỏi.
  Sai mã hoặc bị từ chối không làm đóng phiên.
- Ansible idempotent: `user password:"!"`, các copy, `systemctl enable` có `creates`, `try-restart` chỉ chạy khi đổi cấu hình
  sshd; `visudo -cf` validate; `sudoers` 0440; `sshd_config.d/10-*` đứng trước `50-cloud-init.conf` nên được ưu tiên.
- Mảng bash rỗng `"${may[@]}"` dưới `set -u` không lỗi (bash 5.2); `PIPESTATUS[0]` lấy trong `set +e`.
- Parser cấu hình mới (regex Ansible, Python) chịu được CRLF và dòng trùng (dòng sau thắng).


## Đã xử lý (29/9)
| # | Việc | Cách xử lý |
|---|---|---|
| 1 | `{#` trong template Jinja | Đổi sang `[[ -n "${ten[*]:-}" ]]`; đã parse lại toàn bộ `*.j2` |
| 2 | Dòng khóa SSH làm hỏng `onebee-sao-luu` | `onebee-sao-luu` chỉ nạp dòng `RESTIC_` (bỏ `\r`); `them-may` đặt khóa trong ngoặc kép; Ansible bỏ ngoặc khi đọc |
| 3 | IP cũ/giả → cập nhật nhầm máy | `kho` chỉ lấy báo cáo ≤ 2 giờ; playbook kiểm `MAY_TRAM` đúng tên trước khi làm; `them-may` không còn xóa known_hosts |
| 4 | Khóa SSH Box không có trong bản sao lưu | Chuyển vào `/etc/onebee-box/secrets/ssh` (đã được sao lưu) |
| 5 | `sshd -t` thiếu `/run/sshd` | Tạo `/run/sshd` trước khi kiểm |
| 6 | Không có keepalive | Thêm `ServerAliveInterval=30`, `ServerAliveCountMax=6` |
| 7 | Tạo nhiều file tình trạng | Ghi nhận rủi ro trong ADR 0004 (tên giới hạn, báo cáo bỏ qua tên chưa cấp) |
| 8 | Bỏ qua SSH không báo | Thêm thông báo khi `QUAN_TRI_SSH_KEY`/`BOX_IP` sai dạng |
| 9 | Ứng dụng đang mở → đo ~0 giây | Bỏ trống số đo nếu cửa sổ đã có sẵn |
| 10 | Lỗi đọc kho = "chưa từng sao lưu" | Tách "không đọc được kho"; thêm cảnh báo bản sao lưu ghi ngày tương lai (lúc test phát hiện) |

Kiểm lại: test Box 67 mục ĐẠT, desktop mở rộng 79 mục ĐẠT, unit test 8/8.
