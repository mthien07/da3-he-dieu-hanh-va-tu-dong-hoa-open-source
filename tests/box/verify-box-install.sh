#!/usr/bin/env bash
# Kiểm tra OneBee Box sau khi cài (chạy trên Box bằng root). Cần: curl, smbclient.
set -uo pipefail
fails=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then printf 'PASS  %s\n' "$d"; else printf 'FAIL  %s\n' "$d"; fails=$((fails + 1)); fi; }
http_code() { curl -s -o /dev/null -w '%{http_code}' -m 10 "$1"; }
code_in() { local c; c="$(http_code "$1")"; shift; for want in "$@"; do [[ "${c}" == "${want}" ]] && return 0; done; return 1; }

check "Có file phiên bản Box" grep -q '^ONEBEE_EDITION=box$' /etc/onebee-release
check "Docker đang chạy và bật cùng máy" bash -c "systemctl is-active docker && systemctl is-enabled docker"
for c in onebee-portal onebee-ollama onebee-open-webui onebee-n8n onebee-uptime-kuma onebee-rest-server; do
  check "Container ${c} đang chạy" bash -c "[ \"\$(docker inspect -f '{{.State.Running}}' ${c})\" = true ]"
done
check "Trang giới thiệu :80 hiển thị OneBee Box" bash -c "curl -s -m 10 http://127.0.0.1/ | grep -q 'OneBee Box'"
check "Open WebUI :3000 khỏe (/health)" bash -c "curl -s -m 10 http://127.0.0.1:3000/health | grep -q true"
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
check "Open WebUI: tắt Functions/Tools; quản trị không đọc/xuất chat; tắt chia sẻ chat (biến môi trường)" bash -c \
  "for kv in ENABLE_PLUGINS ENABLE_ADMIN_CHAT_ACCESS ENABLE_ADMIN_EXPORT USER_PERMISSIONS_CHAT_SHARE ENABLE_COMMUNITY_SHARING; do \
     [ \"\$(docker exec onebee-open-webui printenv \$kv)\" = false ] || exit 1; done"

# Cài đặt lưu trong CSDL của Open WebUI (biến môi trường chỉ có tác dụng với bản cài mới) → hỏi qua API quản trị
webui_cai_dat_dung() {
  local t cfg perms
  t="$(curl -s -m 20 -X POST http://127.0.0.1:3000/api/v1/auths/signin -H 'Content-Type: application/json' \
       -d "{\"email\":\"quantri@onebee.lan\",\"password\":\"$(cat /etc/onebee-box/secrets/webui-admin-password)\"}" \
       | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')" || return 1
  cfg="$(curl -s -m 20 -H "Authorization: Bearer ${t}" http://127.0.0.1:3000/api/v1/auths/admin/config)"
  perms="$(curl -s -m 20 -H "Authorization: Bearer ${t}" http://127.0.0.1:3000/api/v1/users/default/permissions)"
  python3 - "${cfg}" "${perms}" <<'PY'
import json, sys
cfg, perms = json.loads(sys.argv[1]), json.loads(sys.argv[2])
ok = (cfg["ENABLE_SIGNUP"] is False and cfg["ENABLE_COMMUNITY_SHARING"] is False and cfg["JWT_EXPIRES_IN"] == "30d"
      and cfg["API_KEYS_ALLOWED_ENDPOINTS"] == "/api/chat/completions,/api/models"
      and perms["features"]["api_keys"] is True and perms["chat"]["share"] is False)
sys.exit(0 if ok else 1)
PY
}
check "Open WebUI (CSDL): không đăng ký tự do, không chia sẻ cộng đồng, phiên 30 ngày, nhân viên tạo được khóa API nhưng không chia sẻ chat" \
  webui_cai_dat_dung
check "n8n chỉ ĐỌC được danh sách máy đã cấp (may-da-cap): gắn read-only, không tự thêm máy để nhận báo cáo giả" bash -c \
  "[ -d /srv/onebee/may-da-cap ] && [ \"\$(docker inspect -f '{{range .Mounts}}{{if eq .Destination \"/home/node/.n8n-files/may-da-cap\"}}{{.RW}}{{end}}{{end}}' onebee-n8n)\" = false ]"
check "Ollama KHÔNG mở cổng ra ngoài (11434)" bash -c "! curl -s -m 3 http://127.0.0.1:11434/ >/dev/null"
check "Ollama chạy được bên trong (Open WebUI gọi tới)" bash -c "docker exec onebee-open-webui curl -s -m 10 http://ollama:11434/api/version | grep -q version"
check "Open WebUI không gọi AI đám mây (ENABLE_OPENAI_API=false)" \
  bash -c "docker exec onebee-open-webui printenv ENABLE_OPENAI_API | grep -qx false"
check "File .env chỉ root đọc (600)" bash -c "[ \"\$(stat -c %a /opt/onebee-box/.env)\" = 600 ]"
check "Thư mục bí mật chỉ root vào (700)" bash -c "[ \"\$(stat -c %a /etc/onebee-box/secrets)\" = 700 ]"
check "Khóa bí mật đã sinh, không để trống" bash -c "grep -Eq '^WEBUI_SECRET_KEY=[A-Za-z0-9]{48}$' /opt/onebee-box/.env && grep -Eq '^N8N_ENCRYPTION_KEY=[A-Za-z0-9]{48}$' /opt/onebee-box/.env"

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
