#!/usr/bin/env bash
# Kiểm tra xoay khóa (rà soát bảo mật Pha 4b) trên máy test, sau khi Box + máy trạm ketoan-01 chạy ở chế độ HTTP:
# xoay khóa máy (mật khẩu kho HTTP cũ hết hiệu lực, máy nhận mật khẩu mới qua dong-bo-may, sao lưu + hoi vẫn chạy)
# → xoay khóa Box (mật khẩu quản trị Trợ lý AI/n8n/biểu mẫu mới dùng được, cũ bị từ chối, dịch vụ chạy lại).
# Cách dùng: check-xoay-khoa.sh <container-Box> <container-máy-trạm>   (chưa chạy trên máy tác giả — cần Docker lồng)
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec -i "${BOX}" bash -euo pipefail -s; }      # đọc lệnh từ stdin (heredoc 'nháy đơn' → không phải thoát ký tự)
tram() { docker exec -i "${CLIENT}" bash -euo pipefail -s; }

echo "===== XOAY KHÓA: MÁY TRẠM ====="
box <<'EOF'
S=/etc/onebee-box/secrets
st() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
cp ${S}/may-ketoan-01-http /root/http-cu
cp ${S}/may-ketoan-01-hoi /root/hoi-cu 2>/dev/null || true
[ "$(st -u "ketoan-01:$(cat /root/http-cu)" http://127.0.0.1:8000/ketoan-01/)" != 401 ]
onebee-box xoay-khoa --may ketoan-01 --dong-y > /root/xoay-may.log 2>&1 || { tail -30 /root/xoay-may.log; exit 1; }
[ "$(st -u "ketoan-01:$(cat /root/http-cu)" http://127.0.0.1:8000/ketoan-01/)" = 401 ] || { echo 'FAIL  Mật khẩu kho HTTP cũ vẫn dùng được'; exit 1; }
[ "$(st -u "ketoan-01:$(cat ${S}/may-ketoan-01-http)" http://127.0.0.1:8000/ketoan-01/)" != 401 ] || { echo 'FAIL  Mật khẩu mới không dùng được'; exit 1; }
! grep -q "$(cat ${S}/may-ketoan-01-http)" /root/xoay-may.log /var/log/onebee-box/*.log || { echo 'FAIL  Mật khẩu mới lọt vào nhật ký'; exit 1; }
echo 'PASS  xoay-khoa --may: mật khẩu kho HTTP cũ bị từ chối (401), mật khẩu mới dùng được, không lọt vào nhật ký'
if [ -s /root/hoi-cu ]; then
  [ "$(st -H "Authorization: Bearer $(cat /root/hoi-cu)" http://127.0.0.1:3000/api/models)" != 200 ] || { echo 'FAIL  Khóa hoi cũ của máy vẫn dùng được'; exit 1; }
  echo 'PASS  Khóa hoi cũ của máy hết hiệu lực'
fi
EOF
tram <<'EOF'
onebee-sao-luu >/dev/null || { echo 'FAIL  Máy trạm không sao lưu được sau khi nhận mật khẩu mới'; exit 1; }
su - nhanvien -c 'hoi chào bạn, trả lời 1 câu' >/dev/null 2>&1 || { echo 'FAIL  hoi không chạy với khóa mới'; exit 1; }
echo 'PASS  Máy trạm nhận mật khẩu + khóa mới qua dong-bo-may: sao lưu và hoi vẫn chạy'
EOF

echo "===== XOAY KHÓA: BOX ====="
box <<'EOF'
S=/etc/onebee-box/secrets
st() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
cp ${S}/webui-admin-password /root/admin-cu
cp ${S}/n8n-owner-password /root/n8n-cu
onebee-box xoay-khoa --box --dong-y > /root/xoay-box.log 2>&1 || { tail -40 /root/xoay-box.log; exit 1; }
if cmp -s ${S}/webui-admin-password /root/admin-cu || cmp -s ${S}/n8n-owner-password /root/n8n-cu; then echo 'FAIL  Bí mật không đổi'; exit 1; fi
for _ in $(seq 40); do curl -s -m 5 http://127.0.0.1:3000/health | grep -q true && curl -s -m 5 http://127.0.0.1:5678/healthz | grep -q ok && break; sleep 3; done
signin() { st -X POST http://127.0.0.1:3000/api/v1/auths/signin -H 'Content-Type: application/json' -d "{\"email\":\"quantri@onebee.lan\",\"password\":\"$1\"}"; }
[ "$(signin "$(cat /root/admin-cu)")" != 200 ] || { echo 'FAIL  Mật khẩu quản trị Trợ lý AI cũ còn dùng được'; exit 1; }
[ "$(signin "$(cat ${S}/webui-admin-password)")" = 200 ] || { echo 'FAIL  Mật khẩu quản trị Trợ lý AI mới không dùng được'; exit 1; }
n8n_login() { st -X POST http://127.0.0.1:5678/rest/login -H 'Content-Type: application/json' -d "{\"emailOrLdapLoginId\":\"quantri@onebee.lan\",\"password\":\"$1\"}"; }
[ "$(n8n_login "$(cat /root/n8n-cu)")" != 200 ] || { echo 'FAIL  Mật khẩu chủ n8n cũ còn dùng được'; exit 1; }
[ "$(n8n_login "$(cat ${S}/n8n-owner-password)")" = 200 ] || { echo 'FAIL  Mật khẩu chủ n8n mới không dùng được'; exit 1; }
[ "$(st -u nhanvien:"$(cat ${S}/bieu-mau-nhanvien)" http://127.0.0.1:5678/form/onebee-ho-tro)" = 200 ] || { echo 'FAIL  Mật khẩu biểu mẫu mới không dùng được'; exit 1; }
onebee-box email-thu >/dev/null || { echo 'FAIL  Box không gửi được báo cáo qua n8n sau khi xoay khóa webhook'; exit 1; }
echo 'PASS  xoay-khoa --box: mật khẩu quản trị Trợ lý AI/chủ n8n/biểu mẫu mới dùng được, cũ bị từ chối; webhook n8n đồng bộ khóa mới'
EOF
