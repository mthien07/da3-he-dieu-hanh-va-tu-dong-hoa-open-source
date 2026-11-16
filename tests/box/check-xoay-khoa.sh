#!/usr/bin/env bash
# Kiểm tra xoay khóa (rà soát bảo mật Pha 4b) trên máy test, sau khi Box + máy trạm ketoan-01 chạy ở chế độ HTTP:
# xoay khóa máy (mật khẩu kho HTTP cũ hết hiệu lực, máy nhận mật khẩu mới qua dong-bo-may, sao lưu + hoi vẫn chạy)
# → xoay khóa Box (mật khẩu quản trị Trợ lý AI và mật khẩu trình soạn luồng mới dùng được, cũ bị từ chối; khóa webhook
#   của động cơ quy trình đổi và khóa mới dùng được; dịch vụ chạy lại; email-thu vẫn gửi được).
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
cp ${S}/quy-trinh-soan-luong /root/soan-cu
cp ${S}/quy-trinh-soan-hash /root/soan-hash-cu
cp ${S}/quy-trinh-webhook-key /root/webhook-cu
cp ${S}/authelia-storage-key /root/authelia-storage-key-cu
for f in authelia-session-secret cau-noi-jwt-secret; do cp "${S}/${f}" "/root/${f}-cu"; done
onebee-box xoay-khoa --box --dong-y > /root/xoay-box.log 2>&1 || { tail -40 /root/xoay-box.log; exit 1; }
if cmp -s ${S}/webui-admin-password /root/admin-cu; then echo 'FAIL  Mật khẩu quản trị Trợ lý AI không đổi'; exit 1; fi
cmp -s ${S}/quy-trinh-soan-luong /root/soan-cu && { echo 'FAIL  Mật khẩu trình soạn luồng không đổi'; exit 1; }
[ -s ${S}/quy-trinh-soan-luong ] && [ -s ${S}/quy-trinh-soan-hash ] || { echo 'FAIL  Thiếu mật khẩu/bản băm trình soạn luồng sau xoay'; exit 1; }
grep -Eq '^\$2[aby]\$' ${S}/quy-trinh-soan-hash || { echo 'FAIL  Bản băm mật khẩu trình soạn luồng không phải bcrypt'; exit 1; }
cmp -s ${S}/quy-trinh-soan-hash /root/soan-hash-cu && { echo 'FAIL  Bản băm mật khẩu trình soạn luồng không đổi'; exit 1; }
cmp -s ${S}/quy-trinh-webhook-key /root/webhook-cu && { echo 'FAIL  Khóa webhook động cơ quy trình không đổi'; exit 1; }
for f in authelia-session-secret cau-noi-jwt-secret; do
  [ -s "${S}/${f}" ] && ! cmp -s "${S}/${f}" "/root/${f}-cu" || { echo "FAIL  xoay-khoa --box không đổi ${f}"; exit 1; }
done
cmp -s ${S}/authelia-storage-key /root/authelia-storage-key-cu || { echo 'FAIL  xoay-khoa --box đổi authelia-storage-key (mất mọi ghi danh hai lớp)'; exit 1; }
for ct in onebee-authelia onebee-cau-noi onebee-quy-trinh; do
  [ "$(docker inspect -f '{{.State.Running}}' "${ct}")" = true ] || { echo "FAIL  ${ct} không chạy lại sau xoay khóa"; exit 1; }
done
echo 'PASS  xoay-khoa --box: khóa phiên đăng nhập một lần và khóa ký JWT của cầu nối đổi; khóa CSDL định danh giữ nguyên; ba dịch vụ chạy lại'
for _ in $(seq 40); do curl -s -m 5 http://127.0.0.1:3000/health | grep -q true \
  && docker exec onebee-quy-trinh node -e "fetch('http://127.0.0.1:1880/webhook/suc-khoe').then(r => process.exit(r.status === 200 ? 0 : 1), () => process.exit(1))" && break; sleep 3; done
docker exec onebee-quy-trinh node -e "fetch('http://127.0.0.1:1880/webhook/suc-khoe').then(r => process.exit(r.status === 200 ? 0 : 1), () => process.exit(1))" \
  || { echo 'FAIL  Động cơ quy trình không sẵn sàng sau xoay khóa'; exit 1; }
code_sk=$(docker exec onebee-quy-trinh node -e '
const http = require("http");
http.get({host: "127.0.0.1", port: 1880, path: "/webhook/suc-khoe", headers: {"X-OneBee-Key": process.argv[1]}}, r => {
  let d = ""; r.on("data", c => d += c); r.on("end", () => console.log(r.statusCode));
}).on("error", () => console.log(0));' "$(cat ${S}/quy-trinh-webhook-key)")
[ "${code_sk}" = 200 ] || { echo "FAIL  /webhook/suc-khoe với khóa mới không trả 200 (mã ${code_sk})"; exit 1; }
signin() { st -X POST http://127.0.0.1:3000/api/v1/auths/signin -H 'Content-Type: application/json' -d "{\"email\":\"quantri@onebee.lan\",\"password\":\"$1\"}"; }
[ "$(signin "$(cat /root/admin-cu)")" != 200 ] || { echo 'FAIL  Mật khẩu quản trị Trợ lý AI cũ còn dùng được'; exit 1; }
[ "$(signin "$(cat ${S}/webui-admin-password)")" = 200 ] || { echo 'FAIL  Mật khẩu quản trị Trợ lý AI mới không dùng được'; exit 1; }
# Hòm thư giả lập phải sẵn sàng trước khi thử điểm nhận cảnh báo (điểm nhận gửi thư ngay trong yêu cầu)
docker rm -f mailpit >/dev/null 2>&1 || true
docker run -d --name mailpit --network onebee-box_default -p 127.0.0.1:8025:8025 axllent/mailpit:latest >/dev/null
for _ in $(seq 30); do curl -sf -m 3 http://127.0.0.1:8025/api/v1/messages >/dev/null && break; sleep 1; done
# Khóa webhook mới phải đã vào mô-đun quy trình (Node-RED chỉ giữ SHA-256): canh-bao bằng khóa mới trả 200, khóa cũ bị 403
code_ma=$(docker exec onebee-quy-trinh node -e '
const http = require("http");
const [key, body] = process.argv.slice(1);
const req = http.request({host: "127.0.0.1", port: 1880, path: "/webhook/onebee-canh-bao", method: "POST",
  headers: {"Content-Type": "application/json", "X-OneBee-Key": key, "Content-Length": Buffer.byteLength(body)}}, r => {
  let d = ""; r.on("data", c => d += c); r.on("end", () => console.log(r.statusCode));
});
req.on("error", () => console.log(0)); req.end(body);' "$(cat ${S}/quy-trinh-webhook-key)" '{"muc_do":"INFO","tieu_de":"Xoay khóa","noi_dung":"thử khóa mới"}')
[ "${code_ma}" = 200 ] || { echo "FAIL  Khóa webhook mới không dùng được (/webhook/onebee-canh-bao trả ${code_ma})"; exit 1; }
code_cu=$(docker exec onebee-quy-trinh node -e '
const http = require("http");
const [key, body] = process.argv.slice(1);
const req = http.request({host: "127.0.0.1", port: 1880, path: "/webhook/onebee-canh-bao", method: "POST",
  headers: {"Content-Type": "application/json", "X-OneBee-Key": key, "Content-Length": Buffer.byteLength(body)}}, r => {
  let d = ""; r.on("data", c => d += c); r.on("end", () => console.log(r.statusCode));
});
req.on("error", () => console.log(0)); req.end(body);' "$(cat /root/webhook-cu)" '{"muc_do":"INFO","tieu_de":"Xoay khóa","noi_dung":"thử khóa cũ"}')
[ "${code_cu}" = 403 ] || { echo "FAIL  Khóa webhook cũ vẫn dùng được (mã ${code_cu})"; exit 1; }
onebee-box email-thu >/dev/null || { echo 'FAIL  Box không gửi được email thử sau khi xoay khóa webhook'; exit 1; }
for _ in $(seq 30); do curl -s http://127.0.0.1:8025/api/v1/messages | grep -q "Email thử" && break; sleep 2; done
curl -s http://127.0.0.1:8025/api/v1/messages | grep -q "Email thử" || { echo 'FAIL  Không nhận được email thử sau khi xoay khóa'; exit 1; }
echo 'PASS  xoay-khoa --box: mật khẩu quản trị Trợ lý AI + mật khẩu soạn luồng mới dùng được (băm bcrypt mới), cũ bị từ chối; khóa webhook mới nhận (suc-khoe 200, canh-bao 200), khóa cũ bị chặn (403); email-thu vẫn gửi được'
EOF
