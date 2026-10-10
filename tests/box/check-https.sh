#!/usr/bin/env bash
# Kiểm tra bật/tắt HTTPS (rà soát bảo mật F3, Pha 4) trên máy test, SAU khi Box và máy trạm ketoan-01 đã chạy ở chế độ HTTP:
# chốt chặn máy chưa nhận CA → bật HTTPS → Caddy là nơi duy nhất công bố cổng, TLS đúng CA riêng, http:// bị chuyển 308, cookie Secure, CORS,
# CSP sandbox của biểu mẫu n8n còn nguyên, máy trạm sao lưu/hỏi AI/báo tình trạng qua HTTPS → tắt HTTPS lại về HTTP.
# Cách dùng: check-https.sh <container-Box> <container-máy-trạm>   (chưa chạy trên máy tác giả — cần Docker lồng, xem tests/README.md)
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
GV=/root/onebee-test/box/ansible/group_vars/all.yml
cai() { box "/root/onebee-test/box/onebee-box-install.sh > /root/cai-$1.log 2>&1 || { tail -40 /root/cai-$1.log; exit 1; }"; }
IP="$(box "ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if (\$i == \"src\") {print \$(i + 1); exit}}'")"

echo "===== HTTPS: CHỐT CHẶN — MÁY CHƯA NHẬN CA THÌ GIỮ HTTP ====="
box "onebee-box them-may kho-03 >/dev/null     # máy cấp rồi nhưng chưa đồng bộ CA (không ai chạy dong-bo-may cho nó)
  sed -i -E 's#^onebee_box_https: .*#onebee_box_https: true#' ${GV}"
cai chot-chan
box "grep -q 'CHƯA BẬT HTTPS' /root/cai-chot-chan.log && grep -q 'kho-03' /root/cai-chot-chan.log || { echo 'FAIL  Không báo máy chưa nhận CA'; exit 1; }
  [ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Vẫn bật HTTPS khi còn máy chưa nhận CA'; exit 1; }
  curl -sf -m 10 http://127.0.0.1:3000/health | grep -q true || { echo 'FAIL  Dịch vụ HTTP bị ảnh hưởng'; exit 1; }
  echo 'PASS  Còn máy chưa nhận CA (kho-03) → bộ cài giữ HTTP, nêu tên máy, dịch vụ vẫn chạy'"

echo "===== HTTPS: BẬT ====="
box "onebee-box thu-hoi-may kho-03 --dong-y >/dev/null
  onebee-box dong-bo-may ketoan-01 > /root/dong-bo-ca.log 2>&1 || { tail -20 /root/dong-bo-ca.log; exit 1; }
  [ \"\$(cat /etc/onebee-box/secrets/ca-da-dong-bo/ketoan-01)\" = \"\$(cat /etc/onebee-box/secrets/ca/root.sha256)\" ]"
cai bat-https
box "[ -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Chưa có dấu HTTPS'; exit 1; }
  for c in onebee-open-webui onebee-n8n onebee-uptime-kuma onebee-rest-server onebee-ollama; do
    [ -z \"\$(docker port \$c)\" ] || { echo \"FAIL  \$c còn công bố cổng: \$(docker port \$c)\"; exit 1; }
  done
  p=\$(docker port onebee-portal | awk '{print \$1}' | sort | tr '\n' ' ')
  for x in 80/tcp 443/tcp 3000/tcp 3001/tcp 5678/tcp 8000/tcp; do grep -q \"\$x\" <<<\"\$p\" || { echo \"FAIL  Caddy thiếu cổng \$x (\$p)\"; exit 1; }; done
  echo 'PASS  Chỉ Caddy công bố cổng (80, 443, 3000, 3001, 5678, 8000); 4 dịch vụ backend không còn cổng nào'
  for port in 443 3000 5678 3001 8000; do
    openssl s_client -connect ${IP}:\${port} -noservername -verify_ip ${IP} -verify_return_error -CAfile /etc/onebee-box/secrets/ca/root.crt </dev/null 2>&1 \
      | grep -q 'Verification: OK' || { echo \"FAIL  TLS cổng \$port không đạt (nối bằng IP, không SNI)\"; exit 1; }
  done
  echo 'PASS  TLS đúng ở mọi cổng khi nối bằng IP (không SNI), chuỗi tới CA riêng của Box'
  [ \"\$(curl -s -o /dev/null -w '%{http_code}' http://${IP}:3000/)\" = 308 ] || { echo 'FAIL  http:// tới cổng TLS không bị chuyển 308'; exit 1; }
  curl -sf http://${IP}/onebee-ca.crt | cmp - /etc/onebee-box/secrets/ca/root.crt
  echo 'PASS  http://IP:3000 → 308 sang https; cổng 80 phục vụ chứng chỉ gốc'
  curl -sf -m 10 https://${IP}:3000/health | grep -q true && curl -sf -m 10 https://${IP}:5678/healthz | grep -q ok \
    || { echo 'FAIL  Dịch vụ không trả lời qua HTTPS'; exit 1; }
  ! curl -s -m 3 http://127.0.0.1:3000/ >/dev/null 2>&1 || { echo 'FAIL  Cổng backend 127.0.0.1:3000 vẫn mở'; exit 1; }"

box "pw=\$(cat /etc/onebee-box/secrets/webui-admin-password)
  hdr=\$(curl -si -m 20 -X POST https://${IP}:3000/api/v1/auths/signin -H 'Content-Type: application/json' \
    -d \"{\\\"email\\\":\\\"quantri@onebee.lan\\\",\\\"password\\\":\\\"\${pw}\\\"}\")
  grep -i '^set-cookie:' <<<\"\${hdr}\" | grep -qi 'secure' || { echo 'FAIL  Cookie đăng nhập Open WebUI thiếu cờ Secure'; echo \"\${hdr}\" | head -20; exit 1; }
  ! curl -si -m 10 https://${IP}:3000/api/config -H 'Origin: https://ke-la.example' | grep -qi 'access-control-allow-origin: https://ke-la.example' \
    || { echo 'FAIL  Origin lạ được CORS cho phép'; exit 1; }
  curl -si -m 10 https://${IP}:5678/form/onebee-ho-tro -u nhanvien:\"\$(cat /etc/onebee-box/secrets/bieu-mau-nhanvien)\" | grep -i '^content-security-policy:' | grep -qi sandbox \
    || { echo 'FAIL  Biểu mẫu n8n mất CSP sandbox khi đi qua Caddy'; exit 1; }
  echo 'PASS  Cookie đăng nhập Open WebUI có Secure; Origin lạ không được CORS; biểu mẫu n8n vẫn có CSP sandbox'
  onebee-box dong-bo-tro-ly >/dev/null
  echo 'PASS  onebee-box dong-bo-tro-ly chạy được qua HTTPS (Box tin CA của chính nó)'"

echo "===== HTTPS: MÁY TRẠM ====="
tram "grep -q '^RESTIC_REPOSITORY=rest:https://' /etc/onebee/may-tram.env && grep -q '^BOX_HTTPS=1' /etc/onebee/may-tram.env && [ -e /var/lib/onebee/https-bat ] \
    || { echo 'FAIL  dong-bo-may tự động không đẩy cấu hình https xuống máy trạm'; cat /etc/onebee/may-tram.env | sed 's/=.*/=***/'; exit 1; }
  grep -q 'https://' /etc/onebee-hoi.conf
  echo 'PASS  Sau khi Box bật HTTPS, máy trạm nhận URL https + cờ BOX_HTTPS=1 + dấu bền (tự đồng bộ cuối bộ cài)'
  echo 'lần https' >> /home/nv/ghi-chu.txt; onebee-sao-luu >/dev/null
  su - nhanvien -c 'hoi chào bạn, trả lời 1 câu' >/dev/null 2>&1 || { echo 'FAIL  hoi qua HTTPS'; exit 1; }
  onebee-bao-tinh-trang >/dev/null
  echo 'PASS  Máy trạm sao lưu (restic rest:https), hỏi Trợ lý AI và báo tình trạng qua HTTPS, chỉ tin CA riêng của Box'
  grep -q 'http://' /etc/firefox/policies/policies.json && { echo 'FAIL  Chính sách Firefox còn địa chỉ http'; exit 1; }
  grep -q ManagedBookmarks /etc/firefox/policies/policies.json || { echo 'FAIL  Thiếu dấu trang https của Firefox'; exit 1; }
  echo 'PASS  Firefox được đặt trang chủ + dấu trang https'"
box "onebee-box may-tram | grep -A3 '^ketoan-01 ' | head -4"

echo "===== HTTPS: CHẠY LẠI BỘ CÀI KHÔNG ĐỔI GÌ ====="
cai lan-2-https
box "grep -Eq 'changed=0 .*failed=0' /root/cai-lan-2-https.log || { grep -B2 'changed:' /root/cai-lan-2-https.log | head -30; echo 'FAIL  Chạy lại ở chế độ HTTPS còn thay đổi'; exit 1; }
  echo 'PASS  Chạy lại bộ cài ở chế độ HTTPS: changed=0'"

echo "===== HTTPS: TẮT (HOÀN TÁC) ====="
box "sed -i -E 's#^onebee_box_https: .*#onebee_box_https: false#' ${GV}"
cai tat-https
box "[ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Còn dấu HTTPS'; exit 1; }
  curl -sf -m 10 http://127.0.0.1:3000/health | grep -q true && curl -sf -m 10 http://127.0.0.1:5678/healthz | grep -q ok \
    || { echo 'FAIL  Dịch vụ HTTP không chạy lại'; exit 1; }
  echo 'PASS  Tắt HTTPS: dịch vụ chạy lại ở HTTP, dấu HTTPS bị xóa'"
tram "grep -q '^BOX_HTTPS=0' /etc/onebee/may-tram.env && [ ! -e /var/lib/onebee/https-bat ] && grep -q '^RESTIC_REPOSITORY=rest:http://' /etc/onebee/may-tram.env \
    || { echo 'FAIL  Máy trạm không lùi về HTTP'; exit 1; }
  onebee-sao-luu >/dev/null
  echo 'PASS  Hoàn tác: máy trạm nhận cờ BOX_HTTPS=0, xóa dấu bền, sao lưu lại qua HTTP'"
