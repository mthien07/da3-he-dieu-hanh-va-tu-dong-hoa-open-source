#!/usr/bin/env bash
# Kiểm tra bật/tắt HTTPS (rà soát bảo mật F3, Pha 4) trên máy test, SAU khi Box và máy trạm ketoan-01 đã chạy ở chế độ HTTP:
# chốt chặn máy chưa nhận CA → bật HTTPS → Caddy là nơi duy nhất công bố cổng, TLS đúng CA riêng, http:// bị chuyển 308, cookie Secure, CORS,
# CSP sandbox của biểu mẫu n8n còn nguyên, máy trạm sao lưu/hỏi AI/báo tình trạng qua HTTPS → đăng nhập một lần + cổng API
# (check-sso-cong-api.sh) → phân quyền dòng qua cổng API (check-du-lieu-qua-cong.sh) → chạy lại bộ cài không đổi gì → tắt HTTPS lại về HTTP.
# Cách dùng: check-https.sh <container-Box> <container-máy-trạm>   (chưa chạy trên máy tác giả — cần Docker lồng, xem tests/README.md)
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
GV=/root/onebee-test/box/ansible/group_vars/all.yml
cai() { box "/root/onebee-test/box/onebee-box-install.sh > /root/cai-$1.log 2>&1 || { tail -40 /root/cai-$1.log; exit 1; }"; }
IP="$(box "ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if (\$i == \"src\") {print \$(i + 1); exit}}'")"
TEN="box.$(box "sed -n 's/^onebee_box_ma_don_vi: *//p' ${GV} | tr -d '\"'").onebee.internal"

echo "===== HTTPS: CHỐT CHẶN — MÁY CHƯA NHẬN CA THÌ GIỮ HTTP ====="
box "onebee-box them-may kho-03 >/dev/null     # máy cấp rồi nhưng chưa đồng bộ CA (không ai chạy dong-bo-may cho nó)
  sed -i -E 's#^onebee_box_https: .*#onebee_box_https: true#' ${GV}"
cai chot-chan
box "grep -q 'CHƯA BẬT HTTPS' /root/cai-chot-chan.log && grep -q 'kho-03' /root/cai-chot-chan.log || { echo 'FAIL  Không báo máy chưa nhận CA'; exit 1; }
  [ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Vẫn bật HTTPS khi còn máy chưa nhận CA'; exit 1; }
  curl -sf -m 10 http://127.0.0.1:5678/healthz | grep -q ok || { echo 'FAIL  Dịch vụ HTTP bị ảnh hưởng'; exit 1; }
  echo 'PASS  Còn máy chưa nhận CA (kho-03) → bộ cài giữ HTTP, nêu tên máy, dịch vụ vẫn chạy'"

echo "===== HTTPS: BẬT ====="
# Máy giả của các bài kiểm trước (kho-02...) không có máy thật để nhận CA → thu hồi hết, chỉ giữ ketoan-01 (máy thật) đã đồng bộ
box "for m in kho-02 kho-03; do onebee-box thu-hoi-may \$m --dong-y >/dev/null 2>&1 || true; done
  [ -z \"\$(onebee-box may-chua-nhan-ca | grep -v '^ketoan-01\$')\" ] || { echo 'FAIL  Còn máy khác ngoài ketoan-01 chưa nhận CA'; onebee-box may-chua-nhan-ca; exit 1; }
  onebee-box dong-bo-may ketoan-01 > /root/dong-bo-ca.log 2>&1 || { tail -20 /root/dong-bo-ca.log; exit 1; }
  [ \"\$(cat /etc/onebee-box/secrets/ca-da-dong-bo/ketoan-01)\" = \"\$(cat /etc/onebee-box/secrets/ca/root.sha256)\" ]"
cai bat-https
box "[ -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Chưa có dấu HTTPS'; exit 1; }
  for c in onebee-ai-rag onebee-n8n onebee-uptime-kuma onebee-rest-server onebee-ollama; do
    [ -z \"\$(docker port \$c)\" ] || { echo \"FAIL  \$c còn công bố cổng: \$(docker port \$c)\"; exit 1; }
  done
  p=\$(docker port onebee-portal | awk '{print \$1}' | sort | tr '\n' ' ')
  for x in 80/tcp 443/tcp 3001/tcp 5678/tcp 8000/tcp; do grep -q \"\$x\" <<<\"\$p\" || { echo \"FAIL  Caddy thiếu cổng \$x (\$p)\"; exit 1; }; done
  echo 'PASS  Chỉ Caddy công bố cổng (80, 443, 3001, 5678, 8000); các dịch vụ backend không còn cổng nào'
  for port in 443 5678 3001 8000; do
    openssl s_client -connect ${IP}:\${port} -noservername -verify_ip ${IP} -verify_return_error -CAfile /etc/onebee-box/secrets/ca/root.crt </dev/null 2>&1 \
      | grep -q 'Verification: OK' || { echo \"FAIL  TLS cổng \$port không đạt (nối bằng IP, không SNI)\"; exit 1; }
  done
  echo 'PASS  TLS đúng ở mọi cổng khi nối bằng IP (không SNI), chuỗi tới CA riêng của Box'
  [ \"\$(curl -s -o /dev/null -w '%{http_code}' http://${IP}:443/)\" = 308 ] || { echo 'FAIL  http:// tới cổng TLS không bị chuyển 308'; exit 1; }
  curl -sf http://${IP}/onebee-ca.crt | cmp - /etc/onebee-box/secrets/ca/root.crt
  echo 'PASS  http://IP:443 → 308 sang https; cổng 80 phục vụ chứng chỉ gốc'
  curl -sf -m 10 https://${IP}:5678/healthz | grep -q ok || { echo 'FAIL  n8n không trả lời qua HTTPS'; exit 1; }
  [ \"\$(curl -s -o /dev/null -m 3 -w '%{http_code}' http://127.0.0.1:443/)\" = 308 ] || { echo 'FAIL  127.0.0.1:443 không phải cổng Caddy (308)'; exit 1; }"

box "khoa=\$(onebee-box cap-khoa-hoi kiem-https 2>/dev/null)
  [ \"\${#khoa}\" = 52 ] || { echo 'FAIL  Không cấp được khóa Trợ lý AI'; exit 1; }
  # Khóa API đi tuyến riêng (không cần phiên đăng nhập một lần): xác thực xong mới kiểm thân → câu hỏi rỗng trả 400
  ma=\$(curl -s -o /tmp/ai-rong.json -w '%{http_code}' --cacert /etc/onebee-box/secrets/ca/root.crt \
    --resolve ${TEN}:443:${IP} -H 'Content-Type: application/json' -H \"X-OneBee-Khoa: \${khoa}\" \
    -d '{\"cau_hoi\":\"\"}' https://${TEN}/ai/hoi)
  [ \"\${ma}\" = 400 ] || { echo \"FAIL  /ai/hoi với khóa đúng không trả 400 khi câu hỏi rỗng (mã \${ma})\"; cat /tmp/ai-rong.json; exit 1; }
  ma=\$(curl -s -o /dev/null -w '%{http_code}' --cacert /etc/onebee-box/secrets/ca/root.crt \
    --resolve ${TEN}:443:${IP} -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{\"cau_hoi\":\"\"}' https://${TEN}/ai/hoi)
  [ \"\${ma}\" = 401 ] || { echo \"FAIL  /ai/hoi không khóa/phiên không trả 401 (mã \${ma})\"; exit 1; }
  ma=\$(curl -s -o /dev/null -w '%{http_code}' --cacert /etc/onebee-box/secrets/ca/root.crt \
    --resolve ${TEN}:443:${IP} -H 'Content-Type: application/json' -H \"X-OneBee-Khoa: \${khoa}\" \
    -d '{}' https://${TEN}/ai/api/chat)
  [ \"\${ma}\" = 404 ] || { echo \"FAIL  Đường khác dưới /ai/ không trả 404 (mã \${ma})\"; exit 1; }
  onebee-box go-khoa-hoi kiem-https >/dev/null
  curl -si -m 10 https://${IP}:5678/form/onebee-ho-tro -u nhanvien:\"\$(cat /etc/onebee-box/secrets/bieu-mau-nhanvien)\" | grep -i '^content-security-policy:' | grep -qi sandbox \
    || { echo 'FAIL  Biểu mẫu n8n mất CSP sandbox khi đi qua Caddy'; exit 1; }
  echo 'PASS  /ai/ chỉ mở đường hỏi đáp: khóa đúng xác thực được, thiếu khóa 401, đường khác 404; biểu mẫu n8n vẫn có CSP sandbox'
  onebee-box nap-tri-thuc >/dev/null
  so=\$(docker exec onebee-postgres psql -X -q -U postgres -d onebee -Atc 'SELECT count(*) FROM onebee.tai_lieu_tri_thuc')
  [ \"\${so}\" -gt 0 ] || { echo 'FAIL  onebee-box nap-tri-thuc không nạp được tri thức qua HTTPS'; exit 1; }
  echo 'PASS  onebee-box nap-tri-thuc vẫn chạy sau khi bật HTTPS (dịch vụ Trợ lý AI + CSDL sẵn sàng)'"

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

echo "===== HTTPS: ĐĂNG NHẬP MỘT LẦN + CỔNG API ====="
"$(dirname "$0")/check-sso-cong-api.sh" "${BOX}"

echo "===== HTTPS: DỮ LIỆU QUA CỔNG API (PHÂN QUYỀN DÒNG) ====="
"$(dirname "$0")/check-du-lieu-qua-cong.sh" "${BOX}"

echo "===== HTTPS: CHẠY LẠI BỘ CÀI KHÔNG ĐỔI GÌ ====="
cai lan-2-https
box "grep -Eq 'changed=0 .*failed=0' /root/cai-lan-2-https.log || { grep -B2 'changed:' /root/cai-lan-2-https.log | head -30; echo 'FAIL  Chạy lại ở chế độ HTTPS còn thay đổi'; exit 1; }
  echo 'PASS  Chạy lại bộ cài ở chế độ HTTPS: changed=0'"

echo "===== HTTPS: TẮT (HOÀN TÁC) ====="
box "sed -i -E 's#^onebee_box_https: .*#onebee_box_https: false#' ${GV}"
cai tat-https
box "[ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Còn dấu HTTPS'; exit 1; }
  curl -sf -m 10 http://127.0.0.1:5678/healthz | grep -q ok && curl -sf -m 10 http://127.0.0.1/ | grep -q 'OneBee Box' \
    || { echo 'FAIL  Dịch vụ HTTP không chạy lại'; exit 1; }
  echo 'PASS  Tắt HTTPS: dịch vụ chạy lại ở HTTP, dấu HTTPS bị xóa'"
tram "grep -q '^BOX_HTTPS=0' /etc/onebee/may-tram.env && [ ! -e /var/lib/onebee/https-bat ] && grep -q '^RESTIC_REPOSITORY=rest:http://' /etc/onebee/may-tram.env \
    || { echo 'FAIL  Máy trạm không lùi về HTTP'; exit 1; }
  onebee-sao-luu >/dev/null
  echo 'PASS  Hoàn tác: máy trạm nhận cờ BOX_HTTPS=0, xóa dấu bền, sao lưu lại qua HTTP'"
