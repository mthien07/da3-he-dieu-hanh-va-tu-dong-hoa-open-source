#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm tra OneBee Box sau khi cài (chạy trên Box bằng root). Cần: curl, smbclient.
set -uo pipefail
fails=0
check() { local d="$1" ra; shift; if ra="$("$@" 2>&1)"; then printf 'PASS  %s\n' "$d"; else printf 'FAIL  %s\n' "$d"; [ -z "${ra}" ] || printf '      %s\n' "${ra}"; fails=$((fails + 1)); fi; }
http_code() { curl -s -o /dev/null -w '%{http_code}' -m 10 "$1"; }
code_in() { local c; c="$(http_code "$1")"; shift; for want in "$@"; do [[ "${c}" == "${want}" ]] && return 0; done; return 1; }
tro_ly_ai_tra_loi() { docker exec onebee-ai-rag python3 -I -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8092/suc-khoe', timeout=5)" >/dev/null 2>&1; }

check "Có file phiên bản Box" grep -q '^ONEBEE_EDITION=box$' /etc/onebee-release
check "Docker đang chạy và bật cùng máy" bash -c "systemctl is-active docker && systemctl is-enabled docker"
for c in onebee-portal onebee-ollama onebee-ai-rag onebee-quy-trinh onebee-uptime-kuma onebee-rest-server onebee-postgres onebee-postgrest \
         onebee-seaweedfs onebee-kho-tep; do
  check "Container ${c} đang chạy" bash -c "[ \"\$(docker inspect -f '{{.State.Running}}' ${c})\" = true ]"
done
check "Kho tệp và kiểm dịch không công bố cổng ra ngoài" bash -c \
  "[ -z \"\$(docker port onebee-seaweedfs)\" ] && [ -z \"\$(docker port onebee-kho-tep)\" ]"
check "Image ClamAV dựng cục bộ đã bỏ libclamunrar (không còn tệp UnRAR)" bash -c \
  "! docker run --rm --network none --entrypoint sh onebee/clamav-khong-unrar:1.5.4 -c 'find / -xdev -name \"libclamunrar*\"' | grep -q ."
check "Chữ ký ClamAV đã có trên Box (kiểm dịch quét được tệp thật)" bash -c \
  "ls /srv/onebee/clamav/*.cvd /srv/onebee/clamav/*.cld 2>/dev/null | grep -q ."
check "Tuyến /files/ không tồn tại ở chế độ HTTP (404)" code_in http://127.0.0.1/files/ 404
check "Ứng dụng Sổ điều hành có trang tĩnh trong portal (HTML, CSS, JS)" bash -c \
  "[ -s /opt/onebee-box/portal/site/so-dieu-hanh/index.html ] \
   && [ -s /opt/onebee-box/portal/site/so-dieu-hanh/so-dieu-hanh.css ] \
   && [ -s /opt/onebee-box/portal/site/so-dieu-hanh/so-dieu-hanh.js ]"
check "Tuyến /so-dieu-hanh/ không tồn tại ở chế độ HTTP (404)" code_in http://127.0.0.1/so-dieu-hanh/ 404
check "Trang giới thiệu :80 hiển thị OneBee Box" bash -c "curl -s -m 10 http://127.0.0.1/ | grep -q 'OneBee Box'"
check "Dịch vụ Trợ lý AI khỏe (/suc-khoe)" tro_ly_ai_tra_loi
check "Dịch vụ Trợ lý AI không công bố cổng ra LAN" bash -c "[ -z \"\$(docker port onebee-ai-rag)\" ]"
check "Kho tri thức đã nạp vào CSDL" bash -c "[ \"\$(docker exec onebee-postgres psql -X -q -U postgres -d onebee -Atc 'SELECT count(*) FROM onebee.tai_lieu_tri_thuc')\" -gt 0 ]"
check "Khóa Trợ lý AI chỉ lưu bản băm (không lưu khóa rõ)" bash -c \
  "k=\$(onebee-box cap-khoa-hoi kiem-verify 2>/dev/null) && ! grep -qF \"\$k\" /srv/onebee/ai-rag/khoa-hoi.json; rc=\$?; onebee-box go-khoa-hoi kiem-verify >/dev/null 2>&1; exit \$rc"
check "Động cơ quy trình (Node-RED) khỏe (/webhook/suc-khoe)" bash -c \
  "docker exec onebee-quy-trinh node -e \"require('http').get('http://127.0.0.1:1880/webhook/suc-khoe', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))\""
check "Uptime Kuma :3001 trả lời" code_in http://127.0.0.1:3001/ 200 302
# Uptime Kuma mở cổng web trước khi đọc xong CSDL (vừa khởi động lại) → thử lại tối đa 1 phút
check "Uptime Kuma: tài khoản quản trị tạo sẵn + 4 mục theo dõi (không còn \"ai mở trước thành quản trị\")" bash -c \
  "for lan in 1 2 3 4 5 6; do [ \$lan = 1 ] || sleep 10; docker exec -i -w /app -e KUMA_USER=quantri -e KUMA_PASS=\"\$(cat /etc/onebee-box/secrets/uptime-kuma-password)\" onebee-uptime-kuma node -e '
const s = require(\"socket.io-client\").io(\"http://127.0.0.1:3001\", {transports: [\"websocket\"]});
s.on(\"connect\", () => s.emit(\"needSetup\", (need) => { if (need) process.exit(1);
  s.once(\"monitorList\", (l) => process.exit(Object.keys(l).length >= 4 ? 0 : 2));
  s.emit(\"login\", {username: process.env.KUMA_USER, password: process.env.KUMA_PASS, token: \"\"}, (r) => { if (!r.ok) process.exit(3); }); }));
setTimeout(() => process.exit(4), 20000);' && exit 0; done; exit 1"
check "Giám sát mở ra LAN chỉ sau khi đã có tài khoản quản trị" bash -c \
  "[ -s /etc/onebee-box/secrets/uptime-kuma-da-co-quan-tri ] && ss -Htln | awk '{print \$4}' | grep -qx '0.0.0.0:3001'"
check "Kho sao lưu :8000 đòi mật khẩu (401)" code_in http://127.0.0.1:8000/ 401
check "Trang giới thiệu gửi kèm tiêu đề bảo mật (chống nhúng khung, không lộ tên máy chủ web)" bash -c \
  "h=\$(curl -sI -m 10 http://127.0.0.1/); grep -qi '^x-frame-options: DENY' <<<\"\$h\" && ! grep -qi '^server:' <<<\"\$h\""
check "Động cơ quy trình: trình soạn luồng có mật khẩu riêng (adminAuth), tách khỏi điểm nhận, không cài gói ngoài" bash -c \
  "grep -q 'adminAuth' /opt/onebee-box/quy-trinh/settings.js && grep -q \"httpNodeRoot: '/webhook'\" /opt/onebee-box/quy-trinh/settings.js \
   && grep -q \"httpAdminRoot: '/quy-trinh'\" /opt/onebee-box/quy-trinh/settings.js && grep -q 'allowInstall: false' /opt/onebee-box/quy-trinh/settings.js"
check "Động cơ quy trình không công bố cổng nào (Caddy là cửa duy nhất)" bash -c "[ -z \"\$(docker port onebee-quy-trinh)\" ]"
check "Các image dịch vụ ghim theo digest (@sha256)" bash -c \
  "for c in onebee-portal onebee-ollama onebee-ai-rag onebee-quy-trinh onebee-uptime-kuma onebee-rest-server onebee-seaweedfs; do \
     a=\$(docker inspect -f '{{.Config.Image}}' \$c 2>/dev/null) || { echo \"không đọc được image của \$c\"; exit 1; }; \
     case \"\$a\" in *@sha256:*) ;; *) echo \"\$c dùng image chưa ghim digest: \$a\"; exit 1 ;; esac; \
   done"
check "Động cơ quy trình chỉ ĐỌC được danh sách máy đã cấp (may-da-cap): gắn read-only, không tự thêm máy để nhận báo cáo giả" bash -c \
  "[ -d /srv/onebee/may-da-cap ] && [ \"\$(docker inspect -f '{{range .Mounts}}{{if eq .Destination \"/may-da-cap\"}}{{.RW}}{{end}}{{end}}' onebee-quy-trinh)\" = false ]"
check "Ollama KHÔNG mở cổng ra ngoài (11434)" bash -c "! curl -s -m 3 http://127.0.0.1:11434/ >/dev/null"
check "Ollama chạy được bên trong (dịch vụ Trợ lý AI gọi tới)" bash -c \
  "docker exec onebee-ai-rag python3 -I -c \"import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/version', timeout=10).read().decode())\" | grep -q version"
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
check "Khóa bí mật đã sinh, không để trống" bash -c "grep -Eq '^PGRST_DB_URI=postgres://xac_thuc:[A-Za-z0-9]+@postgres:5432/onebee$' /opt/onebee-box/.env"

pw="$(cat /etc/onebee-box/secrets/samba-onebee 2>/dev/null)"
check "Samba đang chạy" systemctl is-active smbd
check "Thư mục chung: đăng nhập bằng mật khẩu thấy share 'chung'" bash -c "smbclient -L //127.0.0.1 -U 'onebee%${pw}' | grep -q chung"
check "Thư mục chung: KHÔNG cho khách vào" bash -c "! smbclient //127.0.0.1/chung -N -c ls"
check "Thư mục chung: máy từ xa nối qua tệp hosts allow riêng (include)" bash -c \
  "grep -q 'include = /etc/onebee-box/samba-tu-xa.conf' /etc/samba/smb.conf && [ -f /etc/onebee-box/samba-tu-xa.conf ]"
check "Bộ hẹn giờ thu hồi lượt duyệt máy công tác hết hạn đã bật" systemctl is-enabled onebee-tu-xa-het-han.timer
check "Thư mục chung: ghi được file qua mạng" bash -c \
  "echo 'Hợp tác xã' > /tmp/smb-test.txt && smbclient //127.0.0.1/chung -U 'onebee%${pw}' -c 'put /tmp/smb-test.txt thu-nghiem.txt' && grep -q 'Hợp tác xã' /srv/onebee/chung/thu-nghiem.txt"
check "Lịch sao lưu Box đã bật" systemctl is-enabled onebee-box-sao-luu.timer
check "Có lệnh quản trị onebee-box" test -x /usr/local/sbin/onebee-box
check "Bật cập nhật bảo mật tự động" grep -q 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades
check "Tường lửa bật: chỉ mạng LAN cho phép vào dịch vụ của Box (dịch vụ Docker + Samba/SSH)" bash -c \
  "systemctl is-active onebee-tuong-lua && iptables -S DOCKER-USER | grep -q ONEBEE-LAN-DOCKER && [ \$(iptables -S INPUT | grep -c ONEBEE-LAN-BOX) = 2 ]"
check "Cổng dịch vụ chỉ mở IPv4 (cổng IPv6 của Docker đi vòng tường lửa)" bash -c \
  "! ss -Htln | awk '{print \$4}' | grep -Eq '^\\[::\\]:(80|3001|8000)\$'"

echo "----"
if [[ ${fails} -eq 0 ]]; then echo "KẾT QUẢ: Box đạt tất cả mục"; else echo "KẾT QUẢ: ${fails} mục KHÔNG đạt"; exit 1; fi
