#!/usr/bin/env bash
# Kiểm tra OneBee Box sau khi cài (chạy trên Box bằng root). Cần: curl, smbclient.
set -uo pipefail
fails=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then printf 'PASS  %s\n' "$d"; else printf 'FAIL  %s\n' "$d"; fails=$((fails + 1)); fi; }
http_code() { curl -s -o /dev/null -w '%{http_code}' -m 10 "$1"; }
# IP của Box (cùng cách check-https.sh lấy) — Origin hợp lệ của Trợ lý AI ở chế độ HTTP là http://<IP>:3000
BOX_IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
# In giá trị access-control-allow-origin dịch vụ Trợ lý AI trả cho Origin $1 (rỗng nếu không có); lỗi nếu không gọi được API hoặc không 200
cors_tra_ve() {
  local r; r="$(curl -si -m 10 http://127.0.0.1:3000/api/config -H "Origin: $1" | tr -d '\r')" || return 1
  grep -q '^HTTP/[0-9.]* 200' <<<"${r}" || return 1
  grep -i '^access-control-allow-origin:' <<<"${r}" | head -1 | sed 's/^[^:]*: *//' || true
}
cors_nguon_hop_le_duoc_chap_nhan() { [[ -n "${BOX_IP}" && "$(cors_tra_ve "http://${BOX_IP}:3000")" == "http://${BOX_IP}:3000" ]]; }
code_in() { local c; c="$(http_code "$1")"; shift; for want in "$@"; do [[ "${c}" == "${want}" ]] && return 0; done; return 1; }

check "Có file phiên bản Box" grep -q '^ONEBEE_EDITION=box$' /etc/onebee-release
check "Docker đang chạy và bật cùng máy" bash -c "systemctl is-active docker && systemctl is-enabled docker"
for c in onebee-portal onebee-ollama onebee-ai-rag onebee-n8n onebee-uptime-kuma onebee-rest-server; do
  check "Container ${c} đang chạy" bash -c "[ \"\$(docker inspect -f '{{.State.Running}}' ${c})\" = true ]"
done
check "Trang giới thiệu :80 hiển thị OneBee Box" bash -c "curl -s -m 10 http://127.0.0.1/ | grep -q 'OneBee Box'"
check "Trợ lý AI :3000 khỏe (/health)" bash -c "curl -s -m 10 http://127.0.0.1:3000/health | grep -q true"
check "n8n :5678 khỏe (/healthz)" bash -c "curl -s -m 10 http://127.0.0.1:5678/healthz | grep -q ok"
check "Uptime Kuma :3001 trả lời" code_in http://127.0.0.1:3001/ 200 302
# Uptime Kuma mở cổng web trước khi đọc xong CSDL (vừa khởi động lại) → thử lại tối đa 1 phút
check "Uptime Kuma: tài khoản quản trị tạo sẵn + 5 mục theo dõi (không còn \"ai mở trước thành quản trị\")" bash -c \
  "for lan in 1 2 3 4 5 6; do [ \$lan = 1 ] || sleep 10; docker exec -i -w /app -e KUMA_USER=quantri -e KUMA_PASS=\"\$(cat /etc/onebee-box/secrets/uptime-kuma-password)\" onebee-uptime-kuma node -e '
const s = require(\"socket.io-client\").io(\"http://127.0.0.1:3001\", {transports: [\"websocket\"]});
s.on(\"connect\", () => s.emit(\"needSetup\", (need) => { if (need) process.exit(1);
  s.once(\"monitorList\", (l) => process.exit(Object.keys(l).length >= 5 ? 0 : 2));
  s.emit(\"login\", {username: process.env.KUMA_USER, password: process.env.KUMA_PASS, token: \"\"}, (r) => { if (!r.ok) process.exit(3); }); }));
setTimeout(() => process.exit(4), 20000);' && exit 0; done; exit 1"
check "Giám sát mở ra LAN chỉ sau khi đã có tài khoản quản trị" bash -c \
  "[ -s /etc/onebee-box/secrets/uptime-kuma-da-co-quan-tri ] && ss -Htln | awk '{print \$4}' | grep -qx '0.0.0.0:3001'"
check "Trợ lý AI :3000 không cho Origin lạ đọc API kèm cookie (CORS giới hạn cả ở chế độ HTTP)" bash -c \
  "r=\$(curl -si -m 10 http://127.0.0.1:3000/api/config -H 'Origin: https://ke-la.example') && grep -q '^HTTP/[0-9.]* 200' <<<\"\$r\" \
   && ! grep -qi '^access-control-allow-origin: https://ke-la.example' <<<\"\$r\""
check "Trợ lý AI :3000 cho Origin hợp lệ (http://<IP Box>:3000) đọc API: access-control-allow-origin trả đúng Origin đó" cors_nguon_hop_le_duoc_chap_nhan
check "Kho sao lưu :8000 đòi mật khẩu (401)" code_in http://127.0.0.1:8000/ 401
check "Trang giới thiệu gửi kèm tiêu đề bảo mật (chống nhúng khung, không lộ tên máy chủ web)" bash -c \
  "h=\$(curl -sI -m 10 http://127.0.0.1/); grep -qi '^x-frame-options: DENY' <<<\"\$h\" && ! grep -qi '^server:' <<<\"\$h\""
check "n8n khóa chặt: không có nút chạy lệnh hệ thống, nút Code không đọc biến môi trường" bash -c \
  "docker exec onebee-n8n printenv NODES_EXCLUDE | grep -q executeCommand && docker exec onebee-n8n printenv N8N_BLOCK_ENV_ACCESS_IN_NODE | grep -qx true"
check "n8n: tắt mô-đun Agents và MCP, chặn nút Git (rà soát bảo mật 10/10)" bash -c \
  "docker exec onebee-n8n printenv N8N_DISABLED_MODULES | grep -qx agents && docker exec onebee-n8n printenv NODES_EXCLUDE | grep -q n8n-nodes-base.git \
   && docker exec onebee-n8n printenv N8N_MCP_ACCESS_ENABLED | grep -qx false"
check "Các image dịch vụ ghim theo digest (@sha256), n8n không còn dòng 2.40.x đã ngừng vá" bash -c \
  "for c in onebee-portal onebee-ollama onebee-n8n onebee-uptime-kuma onebee-rest-server; do docker inspect -f '{{.Config.Image}}' \$c | grep -q '@sha256:' || exit 1; done; \
   ! docker inspect -f '{{.Config.Image}}' onebee-n8n | grep -q ':2.40'"
check "Trợ lý AI chạy quyền tối thiểu (cap_drop ALL, read_only) và khóa đăng ký tự do" bash -c \
  "docker inspect -f '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}}' onebee-ai-rag | grep -q 'true \[ALL\]' \
   && curl -s -m 10 http://127.0.0.1:3000/api/config | grep -q '\"signup_enabled\": *false' \
   && [ \"\$(curl -s -o /dev/null -w '%{http_code}' -m 10 -X POST http://127.0.0.1:3000/api/v1/auths/signup -H 'Content-Type: application/json' -d '{}')\" = 403 ]"
ai_dang_nhap_va_mau_dung() {
  local t
  t="$(curl -s -m 20 -X POST http://127.0.0.1:3000/api/v1/auths/signin -H 'Content-Type: application/json' \
       -d "{\"email\":\"quantri@onebee.lan\",\"password\":\"$(cat /etc/onebee-box/secrets/ai-admin-password)\"}" \
       | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')" || return 1
  curl -s -m 20 -H "Authorization: Bearer ${t}" http://127.0.0.1:3000/ai/mau | python3 -c '
import json, sys
d = json.load(sys.stdin)
cmds = {p["command"] for p in d.get("prompts", [])}
assert {"to-trinh", "bien-ban", "hop-dong", "bao-cao"}.issubset(cmds), cmds'
}
check "Trợ lý AI: đăng nhập quản trị được và có đủ 4 mẫu hành chính NĐ 30" ai_dang_nhap_va_mau_dung
check "n8n chỉ ĐỌC được danh sách máy đã cấp (may-da-cap): gắn read-only, không tự thêm máy để nhận báo cáo giả" bash -c \
  "[ -d /srv/onebee/may-da-cap ] && [ \"\$(docker inspect -f '{{range .Mounts}}{{if eq .Destination \"/home/node/.n8n-files/may-da-cap\"}}{{.RW}}{{end}}{{end}}' onebee-n8n)\" = false ]"
check "Ollama KHÔNG mở cổng ra ngoài (11434)" bash -c "! curl -s -m 3 http://127.0.0.1:11434/ >/dev/null"
check "Ollama chạy được bên trong (Trợ lý AI gọi tới)" bash -c \
  "docker exec onebee-ai-rag python3 -c \"import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/version', timeout=10).read().decode())\" | grep -q version"
check "Trợ lý AI không chứa cấu hình gọi AI đám mây" bash -c "! grep -qi OPENAI_API_KEY /opt/onebee-box/.env"
check "CA riêng: thư mục 700, khóa 600, gốc + trung gian có ràng buộc tên critical (chỉ IP Box /32 + <mã>.onebee.internal)" bash -c \
  "cd /etc/onebee-box/secrets/ca && [ \$(stat -c %a .) = 700 ] && [ \$(stat -c %a root.key) = 600 ] && [ \$(stat -c %a inter.key) = 600 ] \
   && for c in root inter; do openssl x509 -in \$c.crt -noout -text | grep -A3 'Name Constraints: critical' | grep -q 'IP:.*/255.255.255.255' || exit 1; done \
   && openssl x509 -in root.crt -noout -text | grep -q 'DNS:kiem-thu.onebee.internal'"
check "CA riêng: Box tin CA của chính nó; chứng chỉ gốc công khai tại /onebee-ca.crt; khóa CA không gắn vào container nào" bash -c \
  "openssl verify -CApath /etc/ssl/certs /etc/onebee-box/secrets/ca/inter.crt >/dev/null \
   && curl -sf http://127.0.0.1/onebee-ca.crt | cmp - /etc/onebee-box/secrets/ca/root.crt \
   && ! docker inspect \$(docker ps -q) --format '{{range .Mounts}}{{.Source}} {{end}}' | grep -Eq 'secrets/ca(/| |\$)'"
check "onebee-box in-ca in vân tay đúng chứng chỉ gốc" bash -c \
  "onebee-box in-ca | grep -q \"\$(sha256sum < <(openssl x509 -in /etc/onebee-box/secrets/ca/root.crt -outform DER) | cut -d' ' -f1 | tr a-f A-F | sed 's/../&:/g; s/:\$//')\""
check "File .env chỉ root đọc (600)" bash -c "[ \"\$(stat -c %a /opt/onebee-box/.env)\" = 600 ]"
check "Thư mục bí mật chỉ root vào (700)" bash -c "[ \"\$(stat -c %a /etc/onebee-box/secrets)\" = 700 ]"
check "Khóa bí mật đã sinh, không để trống" bash -c "grep -Eq '^AI_RAG_SECRET_KEY=[A-Za-z0-9]{48}$' /opt/onebee-box/.env && grep -Eq '^N8N_ENCRYPTION_KEY=[A-Za-z0-9]{48}$' /opt/onebee-box/.env"

pw="$(cat /etc/onebee-box/secrets/samba-onebee 2>/dev/null)"
check "Samba đang chạy" systemctl is-active smbd
check "Thư mục chung: đăng nhập bằng mật khẩu thấy share 'chung'" bash -c "smbclient -L //127.0.0.1 -U 'onebee%${pw}' | grep -q chung"
check "Thư mục chung: KHÔNG cho khách vào" bash -c "! smbclient //127.0.0.1/chung -N -c ls"
check "Thư mục chung: ghi được file qua mạng" bash -c \
  "echo 'Hợp tác xã' > /tmp/smb-test.txt && smbclient //127.0.0.1/chung -U 'onebee%${pw}' -c 'put /tmp/smb-test.txt thu-nghiem.txt' && grep -q 'Hợp tác xã' /srv/onebee/chung/thu-nghiem.txt"
check "Lịch sao lưu Box đã bật" systemctl is-enabled onebee-box-sao-luu.timer
check "Có lệnh quản trị onebee-box" test -x /usr/local/sbin/onebee-box
check "Bật cập nhật bảo mật tự động" grep -q 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades
check "Tường lửa bật: chỉ mạng LAN cho phép vào dịch vụ của Box (dịch vụ Docker + Samba/SSH)" bash -c \
  "systemctl is-active onebee-tuong-lua && iptables -S DOCKER-USER | grep -q ONEBEE-LAN-DOCKER && [ \$(iptables -S INPUT | grep -c ONEBEE-LAN-BOX) = 2 ]"
check "Cổng dịch vụ chỉ mở IPv4 (cổng IPv6 của Docker đi vòng tường lửa)" bash -c \
  "! ss -Htln | awk '{print \$4}' | grep -Eq '^\\[::\\]:(80|3000|3001|5678|8000)\$'"

echo "----"
if [[ ${fails} -eq 0 ]]; then echo "KẾT QUẢ: Box đạt tất cả mục"; else echo "KẾT QUẢ: ${fails} mục KHÔNG đạt"; exit 1; fi
