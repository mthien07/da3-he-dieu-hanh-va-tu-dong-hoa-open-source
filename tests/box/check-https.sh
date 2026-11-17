#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm tra bật/tắt HTTPS (rà soát bảo mật F3, Pha 4) trên máy test, SAU khi Box và máy trạm ketoan-01 đã chạy ở chế độ HTTP:
# chốt chặn máy chưa nhận CA → bật HTTPS → Caddy là nơi duy nhất công bố cổng, TLS đúng CA riêng, http:// bị chuyển 308, cookie Secure, CORS,
# trình soạn luồng Node-RED không vào được khi chưa phiên, điểm nhận webhook tự kiểm X-OneBee-Key, bất biến bảo mật (kiem-bat-bien.sh),
# máy trạm sao lưu/hỏi AI/báo tình trạng qua HTTPS → đăng nhập một lần + cổng API (check-sso-cong-api.sh) → phê duyệt đơn qua động cơ quy trình
# → Sổ điều hành H-P-D-I: gửi đơn kèm tệp, kiểm dịch, duyệt, bảng điều hành, tóm tắt (check-so-dieu-hanh.sh) → phân quyền dòng qua cổng API
# (check-du-lieu-qua-cong.sh) → kho tệp: tải lên, kiểm dịch ClamAV, tải lại đúng SHA-256, tệp nhiễm bị chặn (check-kho-tep-inside.sh)
# → chạy lại bộ cài không đổi gì → tắt HTTPS lại về HTTP.
# Cách dùng: check-https.sh <container-Box> <container-máy-trạm>   (chưa chạy trên máy tác giả — cần Docker lồng, xem tests/README.md)
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
GV=/root/onebee-test/box/ansible/group_vars/all.yml
cai() { box "/root/onebee-test/box/onebee-box-install.sh > /root/cai-$1.log 2>&1 || { tail -40 /root/cai-$1.log; exit 1; }"; }
IP="$(box "ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if (\$i == \"src\") {print \$(i + 1); exit}}'")"
MA_DON_VI="$(box "sed -n 's/^onebee_box_ma_don_vi: *//p' ${GV} | tr -d '\"'")"
TEN_BOX="box.${MA_DON_VI}.onebee.internal"
TEN="${TEN_BOX}"
CA=/etc/onebee-box/secrets/ca/root.crt

echo "===== HTTPS: CHỐT CHẶN — MÁY CHƯA NHẬN CA THÌ GIỮ HTTP ====="
box "onebee-box them-may kho-03 >/dev/null     # máy cấp rồi nhưng chưa đồng bộ CA (không ai chạy dong-bo-may cho nó)
  sed -i -E 's#^onebee_box_https: .*#onebee_box_https: true#' ${GV}"
cai chot-chan
box "grep -q 'CHƯA BẬT HTTPS' /root/cai-chot-chan.log && grep -q 'kho-03' /root/cai-chot-chan.log || { echo 'FAIL  Không báo máy chưa nhận CA'; exit 1; }
  [ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Vẫn bật HTTPS khi còn máy chưa nhận CA'; exit 1; }
  docker exec onebee-quy-trinh node -e \"fetch('http://127.0.0.1:1880/webhook/suc-khoe').then(r => process.exit(r.status === 200 ? 0 : 1), () => process.exit(1))\" \
    || { echo 'FAIL  Dịch vụ HTTP bị ảnh hưởng'; exit 1; }
  echo 'PASS  Còn máy chưa nhận CA (kho-03) → bộ cài giữ HTTP, nêu tên máy, dịch vụ vẫn chạy'"

echo "===== HTTPS: BẬT ====="
# Máy giả của các bài kiểm trước (kho-02...) không có máy thật để nhận CA → thu hồi hết, chỉ giữ ketoan-01 (máy thật) đã đồng bộ
box "for m in kho-02 kho-03; do onebee-box thu-hoi-may \$m --dong-y >/dev/null 2>&1 || true; done
  [ -z \"\$(onebee-box may-chua-nhan-ca | grep -v '^ketoan-01\$')\" ] || { echo 'FAIL  Còn máy khác ngoài ketoan-01 chưa nhận CA'; onebee-box may-chua-nhan-ca; exit 1; }
  onebee-box dong-bo-may ketoan-01 > /root/dong-bo-ca.log 2>&1 || { tail -20 /root/dong-bo-ca.log; exit 1; }
  [ \"\$(cat /etc/onebee-box/secrets/ca-da-dong-bo/ketoan-01)\" = \"\$(cat /etc/onebee-box/secrets/ca/root.sha256)\" ]"
cai bat-https
box "[ -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Chưa có dấu HTTPS'; exit 1; }
  for c in onebee-ai-rag onebee-quy-trinh onebee-uptime-kuma onebee-rest-server onebee-ollama onebee-seaweedfs onebee-kho-tep; do
    [ -z \"\$(docker port \$c)\" ] || { echo \"FAIL  \$c còn công bố cổng: \$(docker port \$c)\"; exit 1; }
  done
  p=\$(docker port onebee-portal | awk '{print \$1}' | sort | tr '
' ' ')
  for x in 80/tcp 443/tcp 3001/tcp 8000/tcp; do grep -q \"\$x\" <<<\"\$p\" || { echo \"FAIL  Caddy thiếu cổng \$x (\$p)\"; exit 1; }; done
  echo 'PASS  Chỉ Caddy công bố cổng (80, 443, 3001, 8000); các dịch vụ backend không còn cổng nào'
  for port in 443 3001 8000; do
    openssl s_client -connect ${IP}:\${port} -noservername -verify_ip ${IP} -verify_return_error -CAfile ${CA} </dev/null 2>&1 \
      | grep 'Verification: OK' >/dev/null || { echo \"FAIL  TLS cổng \$port không đạt (nối bằng IP, không SNI)\"; exit 1; }
  done
  echo 'PASS  TLS đúng ở mọi cổng khi nối bằng IP (không SNI), chuỗi tới CA riêng của Box'
  curl -sf http://${IP}/onebee-ca.crt | cmp - ${CA}
  echo 'PASS  Cổng 80 phục vụ chứng chỉ gốc'
  key=\$(cat /etc/onebee-box/secrets/quy-trinh-webhook-key)
  code=\$(curl -s -o /dev/null -m 10 -w '%{http_code}' --cacert ${CA} --resolve ${TEN_BOX}:443:127.0.0.1 \
    -H \"X-OneBee-Key: \${key}\" https://${TEN_BOX}/webhook/suc-khoe)
  [ \"\${code}\" = 200 ] || { echo \"FAIL  /webhook/suc-khoe qua tên Box không trả 200 (\${code})\"; exit 1; }
  echo 'PASS  Điểm nhận /webhook/suc-khoe trả 200 qua tên Box với CA riêng và X-OneBee-Key'
  # Trình soạn luồng chạy mã tùy ý: không phiên thì phải bị chặn (302 sang trang đăng nhập, hoặc 401) — không bao giờ 200
  ed=\$(curl -s -o /dev/null -m 10 -w '%{http_code}' --cacert ${CA} --resolve ${TEN_BOX}:443:127.0.0.1 https://${TEN_BOX}/quy-trinh/)
  case \"\${ed}\" in
    302|303|401) ;;
    *) echo \"FAIL  Trình soạn luồng /quy-trinh/ không phiên trả \${ed} (mong 302/401)\"; exit 1 ;;
  esac
  echo 'PASS  Trình soạn luồng /quy-trinh/ không phiên không vào được (302/401, không phải 200)'"

box "khoa=\$(onebee-box cap-khoa-hoi kiem-https 2>/dev/null)
  [ \"\${#khoa}\" = 52 ] || { echo 'FAIL  Không cấp được khóa Trợ lý AI'; exit 1; }
  # Khóa API đi tuyến riêng (không cần phiên đăng nhập một lần): xác thực xong mới kiểm thân → câu hỏi rỗng trả 400
  ma=\$(curl -s -o /tmp/ai-rong.json -w '%{http_code}' --cacert ${CA} \
    --resolve ${TEN}:443:${IP} -H 'Content-Type: application/json' -H \"X-OneBee-Khoa: \${khoa}\" \
    -d '{\"cau_hoi\":\"\"}' https://${TEN}/ai/hoi)
  [ \"\${ma}\" = 400 ] || { echo \"FAIL  /ai/hoi với khóa đúng không trả 400 khi câu hỏi rỗng (mã \${ma})\"; cat /tmp/ai-rong.json; exit 1; }
  ma=\$(curl -s -o /dev/null -w '%{http_code}' --cacert ${CA} \
    --resolve ${TEN}:443:${IP} -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{\"cau_hoi\":\"\"}' https://${TEN}/ai/hoi)
  [ \"\${ma}\" = 401 ] || { echo \"FAIL  /ai/hoi không khóa/phiên không trả 401 (mã \${ma})\"; exit 1; }
  ma=\$(curl -s -o /dev/null -w '%{http_code}' --cacert ${CA} \
    --resolve ${TEN}:443:${IP} -H 'Content-Type: application/json' -H \"X-OneBee-Khoa: \${khoa}\" \
    -d '{}' https://${TEN}/ai/api/chat)
  [ \"\${ma}\" = 404 ] || { echo \"FAIL  Đường khác dưới /ai/ không trả 404 (mã \${ma})\"; exit 1; }
  onebee-box go-khoa-hoi kiem-https >/dev/null
  echo 'PASS  /ai/ chỉ mở đường hỏi đáp: khóa đúng xác thực được, thiếu khóa 401, đường khác 404'
  onebee-box nap-tri-thuc >/dev/null
  so=\$(docker exec onebee-postgres psql -X -q -U postgres -d onebee -Atc 'SELECT count(*) FROM onebee.tai_lieu_tri_thuc')
  [ \"\${so}\" -gt 0 ] || { echo 'FAIL  onebee-box nap-tri-thuc không nạp được tri thức qua HTTPS'; exit 1; }
  echo 'PASS  onebee-box nap-tri-thuc vẫn chạy sau khi bật HTTPS (dịch vụ Trợ lý AI + CSDL sẵn sàng)'"

echo "===== HTTPS: BẤT BIẾN BẢO MẬT (CỔNG + TUYẾN LÕI) ====="
box "ONEBEE_HTTPS=1 ONEBEE_IP=${IP} ONEBEE_TEN_BOX=${TEN_BOX} ONEBEE_CA=${CA} /root/onebee-test/tests/box/kiem-bat-bien.sh"

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
  echo 'PASS  Firefox được đặt trang chủ + dấu trang https'
  grep -q '^HO_TRO_URL=https://box\.[a-z0-9-]*\.onebee\.internal/so-dieu-hanh/$' /etc/onebee-ho-tro.conf \
    || { echo 'FAIL  Mục menu Báo cần hỗ trợ không trỏ ứng dụng Sổ điều hành trên tên Box'; cat /etc/onebee-ho-tro.conf 2>/dev/null; exit 1; }
  grep -qx 'Exec=onebee-bao-ho-tro' /usr/share/applications/onebee-bao-ho-tro.desktop \
    || { echo 'FAIL  Thiếu mục menu Báo cần hỗ trợ'; exit 1; }
  echo 'PASS  Menu máy trạm \"Báo cần hỗ trợ\" mở Sổ điều hành trên tên Box qua HTTPS'"
box "onebee-box may-tram | grep -A3 '^ketoan-01 ' | head -4"

echo "===== HTTPS: ĐĂNG NHẬP MỘT LẦN + CỔNG API ====="
"$(dirname "$0")/check-sso-cong-api.sh" "${BOX}"

echo "===== HTTPS: PHÊ DUYỆT ĐƠN QUA ĐỘNG CƠ QUY TRÌNH ====="
box '/root/onebee-test/tests/box/check-quy-trinh-inside.sh phe-duyet'

echo "===== HTTPS: SỔ ĐIỀU HÀNH H-P-D-I ====="
"$(dirname "$0")/check-so-dieu-hanh.sh" "${BOX}"

echo "===== HTTPS: DỮ LIỆU QUA CỔNG API (PHÂN QUYỀN DÒNG) ====="
"$(dirname "$0")/check-du-lieu-qua-cong.sh" "${BOX}"

echo "===== HTTPS: KHO TỆP + KIỂM DỊCH CLAMAV ====="
box "/root/onebee-test/tests/box/check-kho-tep-inside.sh"

echo "===== HTTPS: CHẠY LẠI BỘ CÀI KHÔNG ĐỔI GÌ ====="
cai lan-2-https
box "grep -Eq 'changed=0 .*failed=0' /root/cai-lan-2-https.log || { grep -B2 'changed:' /root/cai-lan-2-https.log | head -30; echo 'FAIL  Chạy lại ở chế độ HTTPS còn thay đổi'; exit 1; }
  echo 'PASS  Chạy lại bộ cài ở chế độ HTTPS: changed=0'"

echo "===== HTTPS: TẮT (HOÀN TÁC) ====="
box "sed -i -E 's#^onebee_box_https: .*#onebee_box_https: false#' ${GV}"
cai tat-https
# Chạy với pipefail: không "curl | grep -q" (grep thoát sớm, curl nhận SIGPIPE, ống trượt tùy thời điểm).
# Node-RED vừa được tạo lại khi đổi chế độ: chờ tới 60 giây (start_period của healthcheck) thay vì kiểm một lần.
box "[ ! -e /etc/onebee-box/secrets/https-da-bat ] || { echo 'FAIL  Còn dấu HTTPS'; exit 1; }
  for _ in \$(seq 30); do
    docker exec onebee-quy-trinh node -e \"fetch('http://127.0.0.1:1880/webhook/suc-khoe').then(r => process.exit(r.status === 200 ? 0 : 1), () => process.exit(1))\" && break
    sleep 2
  done || true
  docker exec onebee-quy-trinh node -e \"fetch('http://127.0.0.1:1880/webhook/suc-khoe').then(r => process.exit(r.status === 200 ? 0 : 1), () => process.exit(1))\" \
    || { echo 'FAIL  Động cơ quy trình không trả lời ở HTTP sau 60 giây'; exit 1; }
  curl -sf -m 10 http://127.0.0.1/ | grep 'OneBee Box' >/dev/null \
    || { echo 'FAIL  Trang chủ không chạy lại ở HTTP'; exit 1; }
  echo 'PASS  Tắt HTTPS: dịch vụ chạy lại ở HTTP, dấu HTTPS bị xóa'"
tram "grep -q '^BOX_HTTPS=0' /etc/onebee/may-tram.env && [ ! -e /var/lib/onebee/https-bat ] && grep -q '^RESTIC_REPOSITORY=rest:http://' /etc/onebee/may-tram.env \
    || { echo 'FAIL  Máy trạm không lùi về HTTP'; exit 1; }
  onebee-sao-luu >/dev/null
  echo 'PASS  Hoàn tác: máy trạm nhận cờ BOX_HTTPS=0, xóa dấu bền, sao lưu lại qua HTTP'"
