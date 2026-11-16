#!/usr/bin/env bash
# Kiểm tra đăng nhập một lần (Authelia) + cổng API trên Box đã BẬT HTTPS (check-https.sh gọi bài này sau khi bật, trước khi tắt):
# tạo tài khoản (mật khẩu tạm không vào nhật ký) → đăng nhập sai/đúng → /api/toi có/không phiên → JWT giả bị bỏ → /ai/ đòi phiên
# → trang giám sát: chưa phiên thì sang trang đăng nhập, nhân viên 403, kỹ thuật qua hai lớp (ghi danh TOTP bằng mã xác minh) vào được
# không phải đăng nhập Uptime Kuma lần nữa → tat-sso-tam / bat-sso-lai → không container nào của SSO công bố cổng
# → xoay-khoa --box làm cookie phiên cũ hết hiệu lực.
# Tài khoản an, binh, kt và thư mục /root/sso (mật khẩu tạm, cookie, khóa TOTP của kt) để lại cho check-du-lieu-qua-cong.sh — bài đó dọn.
# Cách dùng: check-sso-cong-api.sh <container-Box>
set -euo pipefail
BOX="$1"
# Đọc lệnh từ heredoc rồi chạy bằng -c (xem check-xoay-khoa.sh: 'bash -s' để lệnh đọc stdin nuốt các dòng còn lại)
box() { docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; }

# Tiện ích dùng chung trên Box: tên Box trỏ về IP của chính Box (như dòng /etc/hosts của máy trạm), chỉ tin CA riêng của Box.
# Mật khẩu/mã chỉ nằm trong /root/sso (0700) và được đưa cho curl qua tệp (-d @tệp), không nằm trên dòng lệnh
box <<'EOF'
install -d -m 0700 /root/sso
cat >/root/sso/chung.sh <<'CHUNG'
IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
TEN="box.$(sed -n 's/^onebee_box_ma_don_vi: *//p' /root/onebee-test/box/ansible/group_vars/all.yml | tr -d '"')".onebee.internal
CA=/etc/onebee-box/secrets/ca/root.crt
D=/root/sso
c() { curl -s -m 20 --cacert "${CA}" --resolve "${TEN}:443:${IP}" --resolve "${TEN}:3001:${IP}" "$@"; }
ma() { c -o /dev/null -w '%{http_code}' "$@"; }
# dang_nhap <tên> <tệp mật khẩu> <tệp cookie> → mã HTTP của bước một lớp
dang_nhap() {
  (umask 077; printf '{"username":"%s","password":"%s","keepMeLoggedIn":false}' "$1" "$(cat "$2")" >"${D}/dn.json")
  rm -f "$3"
  ma -c "$3" -H 'Content-Type: application/json' -d @"${D}/dn.json" "https://${TEN}/dangnhap/api/firstfactor"
  rm -f "${D}/dn.json"
}
# mã TOTP (RFC 6238, SHA1, 6 số, 30 giây) từ khóa base32 trong tệp $1, lệch $2 bước thời gian
totp() {
  python3 - "$1" "${2:-0}" <<'PY'
import base64, hashlib, hmac, struct, sys, time
k = base64.b32decode(open(sys.argv[1]).read().strip().upper() + "=" * (-len(open(sys.argv[1]).read().strip()) % 8))
h = hmac.new(k, struct.pack(">Q", int(time.time()) // 30 + int(sys.argv[2])), hashlib.sha1).digest()
o = h[-1] & 15
print("%06d" % ((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1000000))
PY
}
CHUNG
EOF

echo "===== ĐĂNG NHẬP MỘT LẦN: TÀI KHOẢN ====="
box <<'EOF'
. /root/sso/chung.sh
for u in "an nhan_vien" "binh quan_ly" "kt ky_thuat"; do
  set -- ${u}
  out="$(onebee-box them-nguoi "$1" "$2")" || { echo "FAIL  them-nguoi $1 $2"; exit 1; }
  (umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${D}/mk-$1")
  [ "$(wc -c <"${D}/mk-$1")" = 17 ] || { echo "FAIL  them-nguoi $1 không in đúng một mật khẩu tạm 16 ký tự"; exit 1; }
done
onebee-box danh-sach-nguoi | grep -q '^an  *nhan_vien' || { echo 'FAIL  danh-sach-nguoi thiếu an'; exit 1; }
for u in an binh kt; do
  ! grep -rqF "$(cat "${D}/mk-${u}")" /var/log/onebee-box /etc/onebee-box/secrets /srv/onebee/authelia 2>/dev/null \
    || { echo "FAIL  Mật khẩu tạm của ${u} lọt vào nhật ký / thư mục bí mật / dữ liệu định danh"; exit 1; }
done
! onebee-box in-khoa | grep -qF "$(cat "${D}/mk-an")" || { echo 'FAIL  in-khoa in mật khẩu người dùng'; exit 1; }
echo 'PASS  them-nguoi an (nhan_vien), binh (quan_ly), kt (ky_thuat): mật khẩu tạm in một lần, không có trong /var/log/onebee-box, bí mật, in-khoa'
EOF

box <<'EOF'
. /root/sso/chung.sh
(umask 077; echo 'sai-mat-khau-123' >"${D}/mk-sai")
[ "$(dang_nhap an "${D}/mk-sai" "${D}/jar-sai")" = 401 ] || { echo 'FAIL  Đăng nhập sai mật khẩu không bị từ chối'; exit 1; }
ok=""; for _ in $(seq 15); do [ "$(dang_nhap an "${D}/mk-an" "${D}/jar-an")" = 200 ] && { ok=1; break; }; sleep 2; done   # Authelia đọc lại tệp người dùng
[ -n "${ok}" ] && grep -q 'authelia_session' "${D}/jar-an" || { echo 'FAIL  Đăng nhập đúng không nhận cookie phiên'; exit 1; }
grep -P "^#HttpOnly_\.?\Q${TEN}\E\t" "${D}/jar-an" | grep -q authelia_session || { echo 'FAIL  Cookie phiên không đặt cho đúng tên Box / thiếu HttpOnly'; exit 1; }
echo 'PASS  Đăng nhập sai mật khẩu bị từ chối (401); đúng mật khẩu nhận cookie phiên HttpOnly cho tên Box'
EOF

echo "===== ĐĂNG NHẬP MỘT LẦN: CỔNG API ====="
box <<'EOF'
. /root/sso/chung.sh
[ "$(ma -H 'Accept: application/json' "https://${TEN}/api/toi")" = 401 ] || { echo 'FAIL  /api/toi không phiên không nhận 401'; exit 1; }
[ "$(ma -H 'Accept: application/json' -H 'Remote-User: binh' -H 'Remote-Groups: quan_ly' "https://${TEN}/api/toi")" = 401 ] \
  || { echo 'FAIL  Tự gửi Remote-User mà không phiên vẫn qua'; exit 1; }
toi="$(c -b "${D}/jar-an" -H 'Remote-User: binh' -H 'Remote-Groups: quan_ly' "https://${TEN}/api/toi")"
[ "${toi}" = '{"ten": "an", "vai_tro": "nhan_vien"}' ] || { echo "FAIL  /api/toi có phiên an trả: ${toi}"; exit 1; }
[ "$(ma "https://${IP}/api/toi")" = 308 ] && [ "$(ma "https://${IP}/")" = 200 ] || { echo 'FAIL  Vào bằng IP: tuyến lõi không chuyển sang tên / trang chủ hỏng'; exit 1; }
echo 'PASS  /api/toi: không phiên 401 (kể cả tự gửi Remote-User), phiên an trả tên an, vai trò nhan_vien; vào bằng IP chỉ có trang chủ'
EOF

box <<'EOF'
. /root/sso/chung.sh
jwt="$(python3 - <<'PY'
import base64, hashlib, hmac, json, os, time
b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=").decode()
d = b(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
t = b(json.dumps({"sub": "binh", "role": "quan_ly", "aud": "onebee-api", "iat": int(time.time()), "exp": int(time.time()) + 60}).encode())
print(f"{d}.{t}." + b(hmac.new(os.urandom(32), f"{d}.{t}".encode(), hashlib.sha256).digest()))
PY
)"
(umask 077; printf 'Authorization: Bearer %s\n' "${jwt}" >"${D}/jwt-gia.hdr")
[ "$(ma -H 'Accept: application/json' -H @"${D}/jwt-gia.hdr" "https://${TEN}/api/toi")" = 401 ] \
  || { echo 'FAIL  JWT tự ký bằng khóa sai mà không phiên vẫn qua'; exit 1; }
toi="$(c -b "${D}/jar-an" -H @"${D}/jwt-gia.hdr" "https://${TEN}/api/toi")"
[ "${toi}" = '{"ten": "an", "vai_tro": "nhan_vien"}' ] || { echo "FAIL  JWT giả đổi được danh tính: ${toi}"; exit 1; }
echo 'PASS  Authorization: Bearer <JWT tự ký bằng khóa sai>: không phiên 401; có phiên thì bị bỏ, danh tính vẫn là của phiên'
EOF

box <<'EOF'
. /root/sso/chung.sh
# Chỉ hai đường /ai/hoi và /ai/tom-tat; không phiên, không khóa → 401 (đăng nhập một lần); có phiên → dịch vụ nhận
# Remote-User rồi mới kiểm câu hỏi (rỗng → 400). Tự gửi Remote-User không phiên vẫn 401.
[ "$(ma -X POST -H 'Accept: application/json' -H 'Content-Type: application/json' -d '{}' "https://${TEN}/ai/hoi")" = 401 ] \
  || { echo 'FAIL  /ai/hoi không phiên không nhận 401'; exit 1; }
[ "$(ma -X POST -H 'Accept: application/json' -H 'Content-Type: application/json' -H 'Remote-User: binh' -H 'Remote-Groups: quan_ly' \
    -d '{}' "https://${TEN}/ai/hoi")" = 401 ] || { echo 'FAIL  Tự gửi Remote-User tới /ai/hoi mà không phiên vẫn qua'; exit 1; }
[ "$(ma -X POST -b "${D}/jar-an" -H 'Content-Type: application/json' -d '{}' "https://${TEN}/ai/hoi")" = 400 ] \
  || { echo 'FAIL  /ai/hoi có phiên không tới được dịch vụ (câu hỏi rỗng phải trả 400)'; exit 1; }
# Khóa API đi tuyến riêng, không cần phiên; khóa sai bị từ chối 401
khoa="$(onebee-box cap-khoa-hoi sso-thu 2>/dev/null)"
[ "$(ma -X POST -H 'Content-Type: application/json' -H "X-OneBee-Khoa: ${khoa}" -d '{}' "https://${TEN}/ai/hoi")" = 400 ] \
  || { echo 'FAIL  /ai/hoi với khóa API đúng không tới được dịch vụ'; exit 1; }
[ "$(ma -X POST -H 'Content-Type: application/json' -H "X-OneBee-Khoa: obk-000000000000000000000000000000000000000000000000" -d '{}' "https://${TEN}/ai/hoi")" = 401 ] \
  || { echo 'FAIL  /ai/hoi với khóa API sai không nhận 401'; exit 1; }
onebee-box go-khoa-hoi sso-thu >/dev/null 2>&1 || true
for x in "POST /ai/api/chat" "GET /ai/api/tags" "DELETE /ai/api/delete" "POST /ai/api/pull"; do
  set -- ${x}
  [ "$(ma -X "$1" -b "${D}/jar-an" -d '{}' "https://${TEN}$2")" = 404 ] || { echo "FAIL  $1 $2 không trả 404 (có phiên)"; exit 1; }
done
[ "$(ma -b "${D}/jar-an" "https://${TEN}/files/x")" = 404 ] || { echo 'FAIL  /files/ có phiên không trả 404 (tệp không tồn tại)'; exit 1; }
echo 'PASS  /ai/hoi: không phiên/khóa sai 401, có phiên hoặc khóa đúng tới được dịch vụ (câu hỏi rỗng 400); đường khác dưới /ai/ 404; API quản trị Ollama (tags, delete, pull) 404 kể cả có phiên; /files/ có phiên tới được dịch vụ kho tệp (404)'
EOF

echo "===== ĐĂNG NHẬP MỘT LẦN: TRANG GIÁM SÁT ====="
box <<'EOF'
. /root/sso/chung.sh
loc="$(c -o /dev/null -w '%{http_code} %{redirect_url}' "https://${TEN}:3001/dashboard")"
grep -Eq "^30[23] https://${TEN}/dangnhap/" <<<"${loc}" || { echo "FAIL  Giám sát chưa phiên không chuyển tới trang đăng nhập: ${loc}"; exit 1; }
[ "$(ma -b "${D}/jar-an" "https://${TEN}:3001/dashboard")" = 403 ] || { echo 'FAIL  Nhân viên vào được trang giám sát'; exit 1; }
# Kỹ thuật: một lớp → ghi danh TOTP (mã xác minh lấy bằng onebee-box ma-xac-nhan, như quản trị làm) → hai lớp
ma_kt=""; for _ in 1 2 3; do ma_kt="$(dang_nhap kt "${D}/mk-kt" "${D}/jar-kt")"; [ "${ma_kt}" = 200 ] && break; sleep 2; done
[ "${ma_kt}" = 200 ] || { echo "FAIL  kt không đăng nhập được (mã ${ma_kt})"; exit 1; }
loc="$(c -b "${D}/jar-kt" -o /dev/null -w '%{http_code}' "https://${TEN}:3001/dashboard")"
[ "${loc}" != 200 ] || { echo 'FAIL  Kỹ thuật mới qua một lớp đã vào được giám sát'; exit 1; }
[ "$(ma -b "${D}/jar-kt" -c "${D}/jar-kt" -X POST "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] || { echo 'FAIL  Không xin được mã xác minh'; exit 1; }
sleep 1
(umask 077; printf '{"otc":"%s"}' "$(onebee-box ma-xac-nhan | sed -n 's/^Mã xác minh: //p')" >"${D}/otc.json")
[ "$(ma -b "${D}/jar-kt" -c "${D}/jar-kt" -X PUT -H 'Content-Type: application/json' -d @"${D}/otc.json" "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] \
  || { echo 'FAIL  Mã xác minh từ onebee-box ma-xac-nhan không được nhận'; exit 1; }
c -b "${D}/jar-kt" -c "${D}/jar-kt" -X PUT -H 'Content-Type: application/json' -d '{"algorithm":"SHA1","length":6,"period":30}' \
  "https://${TEN}/dangnhap/api/secondfactor/totp/register" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["base32_secret"])' \
  >"${D}/totp-kt" || { echo 'FAIL  Không bắt đầu ghi danh TOTP được'; exit 1; }
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-kt")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-kt" -c "${D}/jar-kt" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" "https://${TEN}/dangnhap/api/secondfactor/totp/register")" = 200 ] \
  || { echo 'FAIL  Ghi danh TOTP không xong'; exit 1; }
sleep $(( 31 - $(date +%s) % 30 ))   # mã đã dùng để ghi danh không dùng lại được → chờ bước thời gian kế
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-kt")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-kt" -c "${D}/jar-kt" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" "https://${TEN}/dangnhap/api/secondfactor/totp")" = 200 ] \
  || { echo 'FAIL  Lớp hai (TOTP) không qua'; exit 1; }
[ "$(ma -b "${D}/jar-kt" "https://${TEN}:3001/giam-sat/dashboard")" = 200 ] || { echo 'FAIL  Kỹ thuật đã qua hai lớp không vào được giám sát'; exit 1; }
sid="$(c -b "${D}/jar-kt" "https://${TEN}:3001/socket.io/?EIO=4&transport=polling" | sed -n 's/.*"sid":"\([^"]*\)".*/\1/p')"
c -b "${D}/jar-kt" -X POST -H 'Content-Type: text/plain;charset=UTF-8' -d 40 "https://${TEN}:3001/socket.io/?EIO=4&transport=polling&sid=${sid}" >/dev/null
sleep 2
ev="$(c -b "${D}/jar-kt" "https://${TEN}:3001/socket.io/?EIO=4&transport=polling&sid=${sid}")"
grep -q autoLogin <<<"${ev}" && ! grep -q loginRequired <<<"${ev}" || { echo "FAIL  Uptime Kuma vẫn đòi đăng nhập riêng: ${ev:0:200}"; exit 1; }
[ -e /etc/onebee-box/secrets/uptime-kuma-tat-dang-nhap-rieng ] || { echo 'FAIL  Thiếu dấu Kuma tắt đăng nhập riêng'; exit 1; }
echo 'PASS  Giám sát: chưa phiên → trang đăng nhập; nhân viên 403; kỹ thuật một lớp chưa vào được; ghi danh TOTP bằng mã từ ma-xac-nhan, qua hai lớp thì vào thẳng (Kuma autoLogin)'
EOF

echo "===== ĐĂNG NHẬP MỘT LẦN: TẠM TẮT / BẬT LẠI ====="
box <<'EOF'
. /root/sso/chung.sh
onebee-box tat-sso-tam >"${D}/tat.log" 2>&1 || { tail -30 "${D}/tat.log"; echo 'FAIL  tat-sso-tam'; exit 1; }
grep -q 'CẢNH BÁO' "${D}/tat.log" || { echo 'FAIL  tat-sso-tam không cảnh báo'; exit 1; }
[ "$(ma -b "${D}/jar-an" "https://${TEN}/api/toi")" = 503 ] && [ "$(ma -H 'Remote-User: an' -H 'Remote-Groups: quan_ly' "https://${TEN}/api/toi")" = 503 ] \
  || { echo 'FAIL  SSO tạm tắt mà /api/ không trả 503'; exit 1; }
[ ! -e /etc/onebee-box/secrets/uptime-kuma-tat-dang-nhap-rieng ] || { echo 'FAIL  SSO tạm tắt mà Kuma vẫn tắt đăng nhập riêng'; exit 1; }
sid="$(c "https://${IP}:3001/socket.io/?EIO=4&transport=polling" | sed -n 's/.*"sid":"\([^"]*\)".*/\1/p')"
c -X POST -H 'Content-Type: text/plain;charset=UTF-8' -d 40 "https://${IP}:3001/socket.io/?EIO=4&transport=polling&sid=${sid}" >/dev/null
sleep 2
ev="$(c "https://${IP}:3001/socket.io/?EIO=4&transport=polling&sid=${sid}")"
grep -q loginRequired <<<"${ev}" || { echo "FAIL  SSO tạm tắt mà Kuma mở không cần đăng nhập: ${ev:0:200}"; exit 1; }
onebee-box bat-sso-lai >"${D}/bat.log" 2>&1 || { tail -30 "${D}/bat.log"; echo 'FAIL  bat-sso-lai'; exit 1; }
[ ! -e /etc/onebee-box/secrets/sso-tam-tat ] || { echo 'FAIL  Còn dấu sso-tam-tat'; exit 1; }
[ "$(ma -H 'Accept: application/json' "https://${TEN}/api/toi")" = 401 ] || { echo 'FAIL  Sau bat-sso-lai /api/toi không phiên không 401'; exit 1; }
[ "$(dang_nhap an "${D}/mk-an" "${D}/jar-an")" = 200 ] || { echo 'FAIL  Sau bat-sso-lai không đăng nhập được'; exit 1; }
toi="$(c -b "${D}/jar-an" "https://${TEN}/api/toi")"
[ "${toi}" = '{"ten": "an", "vai_tro": "nhan_vien"}' ] || { echo "FAIL  Sau bat-sso-lai /api/toi trả: ${toi}"; exit 1; }
echo 'PASS  tat-sso-tam: tuyến lõi 503 (không mở toang), Kuma đòi đăng nhập riêng; bat-sso-lai: /api/toi lại 401 khi không phiên, an trả đúng'
EOF

box <<'EOF'
# Cầu nối còn ở mạng riêng api (chỉ nó và dịch vụ dữ liệu PostgREST)
for x in "onebee-authelia onebee-box_sso " "onebee-cau-noi onebee-box_api onebee-box_sso "; do
  ct="${x%% *}"
  [ "$(docker inspect -f '{{.State.Running}}' "${ct}")" = true ] || { echo "FAIL  ${ct} không chạy"; exit 1; }
  [ -z "$(docker port "${ct}")" ] || { echo "FAIL  ${ct} công bố cổng: $(docker port "${ct}")"; exit 1; }
  m="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "${ct}")"
  [ "${m}" = "${x#* }" ] || { echo "FAIL  ${ct} nằm ngoài mạng riêng: ${m}"; exit 1; }
done
# Động cơ quy trình (trình soạn luồng chạy mã tùy ý) nằm ở mạng default: không phân giải/không nối được tới cầu nối và dịch vụ định danh
for dich in http://cau-noi:8080/api/toi http://authelia:9091/api/health; do
  docker exec onebee-quy-trinh node -e "fetch('${dich}', {signal: AbortSignal.timeout(5000)}).then(() => process.exit(0), () => process.exit(7))" && rc=0 || rc=$?
  [ "${rc}" = 7 ] || { echo "FAIL  động cơ quy trình gọi thẳng được ${dich} (mã ${rc})"; exit 1; }
done
echo 'PASS  onebee-authelia, onebee-cau-noi không công bố cổng (docker port rỗng), chỉ ở mạng sso (cầu nối thêm mạng api); động cơ quy trình không gọi thẳng được cầu nối'
EOF

echo "===== ĐĂNG NHẬP MỘT LẦN: XOAY KHÓA ====="
box <<'EOF'
. /root/sso/chung.sh
S=/etc/onebee-box/secrets
cp "${S}/authelia-storage-key" "${D}/storage-key-cu"
cp "${S}/authelia-session-secret" "${D}/session-cu"
[ "$(ma -b "${D}/jar-an" "https://${TEN}/api/toi")" = 200 ] || { echo 'FAIL  Phiên an hết hiệu lực trước khi xoay khóa'; exit 1; }
onebee-box xoay-khoa --box --dong-y >"${D}/xoay.log" 2>&1 || { tail -40 "${D}/xoay.log"; echo 'FAIL  xoay-khoa --box'; exit 1; }
for _ in $(seq 30); do docker exec onebee-authelia wget -q -O /dev/null http://127.0.0.1:9091/dangnhap/api/health && break; sleep 2; done
! cmp -s "${S}/authelia-session-secret" "${D}/session-cu" && cmp -s "${S}/authelia-storage-key" "${D}/storage-key-cu" \
  || { echo 'FAIL  xoay-khoa --box: khóa phiên không đổi hoặc khóa CSDL bị đổi'; exit 1; }
[ "$(ma -H 'Accept: application/json' -b "${D}/jar-an" "https://${TEN}/api/toi")" = 401 ] || { echo 'FAIL  Cookie phiên cũ vẫn dùng được sau xoay-khoa --box'; exit 1; }
[ "$(dang_nhap an "${D}/mk-an" "${D}/jar-an")" = 200 ] || { echo 'FAIL  Sau xoay khóa không đăng nhập lại được'; exit 1; }
echo 'PASS  xoay-khoa --box: cookie phiên cũ nhận 401, đăng nhập lại được; khóa CSDL định danh (ghi danh hai lớp) giữ nguyên'
EOF
