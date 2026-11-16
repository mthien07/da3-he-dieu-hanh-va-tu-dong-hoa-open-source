#!/usr/bin/env bash
# Kiểm tra xoay khóa (rà soát bảo mật Pha 4b) trên máy test, sau khi Box + máy trạm ketoan-01 chạy ở chế độ HTTP:
# xoay khóa máy (mật khẩu kho HTTP cũ hết hiệu lực, khóa Trợ lý AI của máy cũ hết hiệu lực, máy nhận mật khẩu mới qua dong-bo-may,
# sao lưu vẫn chạy) → xoay khóa Box (mật khẩu chủ n8n/biểu mẫu mới dùng được, cũ bị từ chối, khóa phiên đăng nhập một lần đổi).
# Cách dùng: check-xoay-khoa.sh <container-Box> <container-máy-trạm>   (chưa chạy trên máy tác giả — cần Docker lồng)
set -euo pipefail
BOX="$1"; CLIENT="$2"
# Đọc lệnh từ heredoc ('nháy đơn' → không phải thoát ký tự) rồi chạy bằng -c, KHÔNG dùng 'bash -s': với -s, lệnh nào trong khối đọc stdin
# (vd 'su - nhanvien -c hoi …') sẽ nuốt nốt các dòng còn lại của khối → các dòng kiểm sau đó không chạy mà khối vẫn thoát 0 (đạt giả).
box() { docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$(cat)"; }

echo "===== XOAY KHÓA: MÁY TRẠM ====="
box <<'EOF'
S=/etc/onebee-box/secrets
st() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
cp ${S}/may-ketoan-01-http /root/http-cu
cp ${S}/may-ketoan-01-khoa /root/hoi-cu
[ "$(st -u "ketoan-01:$(cat /root/http-cu)" http://127.0.0.1:8000/ketoan-01/)" != 401 ]
onebee-box xoay-khoa --may ketoan-01 --dong-y > /root/xoay-may.log 2>&1 || { tail -30 /root/xoay-may.log; exit 1; }
[ "$(st -u "ketoan-01:$(cat /root/http-cu)" http://127.0.0.1:8000/ketoan-01/)" = 401 ] || { echo 'FAIL  Mật khẩu kho HTTP cũ vẫn dùng được'; exit 1; }
[ "$(st -u "ketoan-01:$(cat ${S}/may-ketoan-01-http)" http://127.0.0.1:8000/ketoan-01/)" != 401 ] || { echo 'FAIL  Mật khẩu mới không dùng được'; exit 1; }
! grep -q "$(cat ${S}/may-ketoan-01-http)" /root/xoay-may.log /var/log/onebee-box/*.log || { echo 'FAIL  Mật khẩu mới lọt vào nhật ký'; exit 1; }
echo 'PASS  xoay-khoa --may: mật khẩu kho HTTP cũ bị từ chối (401), mật khẩu mới dùng được, không lọt vào nhật ký'
# Khóa Trợ lý AI của máy: khóa cũ phải hết hiệu lực, khóa mới dùng được (gọi dịch vụ nội bộ, câu hỏi rỗng → 400 = đã xác thực)
[ "$(cat /root/hoi-cu)" != "$(cat ${S}/may-ketoan-01-khoa)" ] || { echo 'FAIL  Khóa Trợ lý AI của máy không đổi'; exit 1; }
IP_AI="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{$v.IPAddress}} {{end}}' onebee-ai-rag \
  | awk '{for (i = 1; i <= NF; i += 2) if ($i ~ /_ai$/) {print $(i + 1); exit}}')"
ai() { curl -s -o /dev/null -w '%{http_code}' -H "X-OneBee-Khoa: $1" -H 'Content-Type: application/json' \
         -d '{"cau_hoi":""}' "http://${IP_AI}:8092/ai/hoi"; }
[ "$(ai "$(cat /root/hoi-cu)")" = 401 ] || { echo 'FAIL  Khóa Trợ lý AI cũ của máy vẫn dùng được'; exit 1; }
[ "$(ai "$(cat ${S}/may-ketoan-01-khoa)")" = 400 ] || { echo 'FAIL  Khóa Trợ lý AI mới của máy không dùng được'; exit 1; }
! grep -qF "$(cat ${S}/may-ketoan-01-khoa)" /root/xoay-may.log || { echo 'FAIL  Khóa Trợ lý AI mới lọt vào nhật ký'; exit 1; }
echo 'PASS  Khóa Trợ lý AI cũ của máy hết hiệu lực, khóa mới dùng được, không lọt vào nhật ký'
EOF
tram <<'EOF'
onebee-sao-luu >/dev/null || { echo 'FAIL  Máy trạm không sao lưu được sau khi nhận mật khẩu mới'; exit 1; }
grep -q '^HOI_API_KEY=obk-' /etc/onebee-hoi.conf || { echo 'FAIL  Máy trạm không nhận khóa Trợ lý AI mới'; exit 1; }
echo 'PASS  Máy trạm nhận mật khẩu + khóa Trợ lý AI mới qua dong-bo-may: sao lưu vẫn chạy'
EOF

echo "===== XOAY KHÓA: BOX ====="
box <<'EOF'
S=/etc/onebee-box/secrets
st() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
cp ${S}/n8n-owner-password /root/n8n-cu
for f in authelia-session-secret cau-noi-jwt-secret authelia-storage-key; do cp "${S}/${f}" "/root/${f}-cu"; done
onebee-box xoay-khoa --box --dong-y > /root/xoay-box.log 2>&1 || { tail -40 /root/xoay-box.log; exit 1; }
cmp -s ${S}/n8n-owner-password /root/n8n-cu && { echo 'FAIL  Bí mật không đổi'; exit 1; }
for f in authelia-session-secret cau-noi-jwt-secret; do
  [ -s "${S}/${f}" ] && ! cmp -s "${S}/${f}" "/root/${f}-cu" || { echo "FAIL  xoay-khoa --box không đổi ${f}"; exit 1; }
done
cmp -s ${S}/authelia-storage-key /root/authelia-storage-key-cu || { echo 'FAIL  xoay-khoa --box đổi authelia-storage-key (mất mọi ghi danh hai lớp)'; exit 1; }
for ct in onebee-authelia onebee-cau-noi; do
  [ "$(docker inspect -f '{{.State.Running}}' "${ct}")" = true ] || { echo "FAIL  ${ct} không chạy lại sau xoay khóa"; exit 1; }
done
echo 'PASS  xoay-khoa --box: khóa phiên đăng nhập một lần và khóa ký JWT của cầu nối đổi; khóa CSDL định danh giữ nguyên; hai dịch vụ chạy lại'
for _ in $(seq 40); do curl -s -m 5 http://127.0.0.1:5678/healthz | grep -q ok && break; sleep 3; done
n8n_login() { st -X POST http://127.0.0.1:5678/rest/login -H 'Content-Type: application/json' -d "{\"emailOrLdapLoginId\":\"quantri@onebee.lan\",\"password\":\"$1\"}"; }
[ "$(n8n_login "$(cat /root/n8n-cu)")" != 200 ] || { echo 'FAIL  Mật khẩu chủ n8n cũ còn dùng được'; exit 1; }
[ "$(n8n_login "$(cat ${S}/n8n-owner-password)")" = 200 ] || { echo 'FAIL  Mật khẩu chủ n8n mới không dùng được'; exit 1; }
[ "$(st -u nhanvien:"$(cat ${S}/bieu-mau-nhanvien)" http://127.0.0.1:5678/form/onebee-ho-tro)" = 200 ] || { echo 'FAIL  Mật khẩu biểu mẫu mới không dùng được'; exit 1; }
onebee-box email-thu >/dev/null || { echo 'FAIL  Box không gửi được báo cáo qua n8n sau khi xoay khóa webhook'; exit 1; }
# Trợ lý AI không phụ thuộc mật khẩu quản trị dịch vụ cũ: sau xoay khóa vẫn nạp được tri thức
onebee-box nap-tri-thuc >/dev/null || { echo 'FAIL  xoay-khoa --box làm hỏng đường nạp tri thức'; exit 1; }
echo 'PASS  xoay-khoa --box: mật khẩu chủ n8n/biểu mẫu mới dùng được, cũ bị từ chối; webhook n8n đồng bộ khóa mới; Trợ lý AI vẫn chạy'
EOF
