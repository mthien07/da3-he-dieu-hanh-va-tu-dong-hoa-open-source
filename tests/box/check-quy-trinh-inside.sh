#!/usr/bin/env bash
# check-quy-trinh-inside.sh — Kiểm động cơ quy trình Node-RED trên Box (chạy trên Box bằng root).
# Không cần cổng công bố: gọi thẳng Node-RED trong container (127.0.0.1:1880, httpNodeRoot /webhook) và gửi thư qua Mailpit giả lập.
#
# Cách dùng:
#   check-quy-trinh-inside.sh            Việc nền: hòm thư báo cáo sao lưu, thư nhắc hạn, điểm nhận tình trạng máy trạm
#                                        (máy chưa cấp bị từ chối; báo cáo sai chữ ký bị Box gắn nhãn).
#   check-quy-trinh-inside.sh phe-duyet  Phê duyệt đơn hàng: chạy khi Box đã bật HTTPS + đăng nhập một lần
#                                        (quản lý duyệt đơn người khác, tự duyệt bị chặn, từ chối thiếu lý do, không phiên).
set -euo pipefail

S=/etc/onebee-box/secrets
MAILPIT=http://127.0.0.1:8025
CHE_DO="${1:-co-ban}"
# Biến dọn dẹp dùng chung với trap EXIT (phải ở phạm vi toàn cục để trap còn thấy sau khi hàm kết thúc)
d=""; id_khac=""; id_tu=""

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

# ---------- Hòm thư giả lập ----------
subjects() {
  curl -s -m 5 "${MAILPIT}/api/v1/messages" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
for m in d.get("messages", []):
    print(m.get("Subject", ""))'
}
wait_mail() {
  local _
  for _ in $(seq 30); do
    subjects | grep -q "$1" && return 0
    sleep 2
  done
  echo "FAIL  Không nhận được email: $1"
  subjects || true
  exit 1
}
khoi_dong_mailpit() {
  docker rm -f mailpit >/dev/null 2>&1 || true
  docker run -d --name mailpit --network onebee-box_default -p 127.0.0.1:8025:8025 axllent/mailpit:latest >/dev/null \
    || fail "Không chạy được Mailpit giả lập (mạng onebee-box_default có tồn tại?)"
  for _ in $(seq 30); do
    curl -sf -m 3 "${MAILPIT}/api/v1/messages" >/dev/null && return 0
    sleep 1
  done
  fail "Hòm thư giả lập (Mailpit) không sẵn sàng"
}

# ---------- Gọi thẳng Node-RED trong container ----------
# qt <phương thức> <đường dẫn> <JSON tiêu đề> <thân> → in {"ma": <mã HTTP>, "than": "<thân>"}
qt() {
  docker exec onebee-quy-trinh node -e '
const http = require("http");
const [method, path, hdr, body] = process.argv.slice(1);
const headers = JSON.parse(hdr || "{}");
const du = body || "";
if (du) headers["Content-Length"] = Buffer.byteLength(du);
const req = http.request({host: "127.0.0.1", port: 1880, path: path, method: method, headers: headers}, r => {
  let d = "";
  r.on("data", c => d += c);
  r.on("end", () => console.log(JSON.stringify({ma: r.statusCode, than: d})));
});
req.on("error", e => console.log(JSON.stringify({ma: 0, loi: e.message})));
if (du) req.write(du);
req.end();
' "$@"
}
qt_ma() { qt "$@" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ma"])'; }
tieu_de_json() { python3 -c 'import json,sys; print(json.dumps(dict(a.split(": ", 1) for a in sys.argv[1:])))' "$@"; }

# =====================================================================
# Phần 1 — việc nền (chạy ở cả HTTP và HTTPS)
# =====================================================================
co_ban() {
  khoi_dong_mailpit
  pass "Hòm thư giả lập (Mailpit) sẵn sàng"

  local key tram_key hdr hdr_tram payload ma
  key="$(cat "${S}/quy-trinh-webhook-key")"
  hdr="$(tieu_de_json "X-OneBee-Key: ${key}" "Content-Type: application/json")"
  hdr_tram='{"Content-Type":"application/json"}'
  if [[ -s "${S}/tinh-trang-key" ]]; then
    tram_key="$(cat "${S}/tinh-trang-key")"
    hdr_tram="$(tieu_de_json "X-OneBee-Key: ${tram_key}" "Content-Type: application/json")"
  fi

  [[ "$(qt_ma GET /webhook/suc-khoe '{}' '')" = 200 ]] || fail "Node-RED không trả lời /webhook/suc-khoe"
  pass "Động cơ quy trình trong container khỏe (/webhook/suc-khoe trả 200)"

  [[ "$(qt_ma POST /webhook/onebee-canh-bao "$(tieu_de_json "X-OneBee-Key: sai" "Content-Type: application/json")" \
        '{"muc_do":"INFO","tieu_de":"Cảnh báo thử"}')" = 403 ]] \
    || fail "Điểm nhận cảnh báo không chặn khóa sai"
  pass "Webhook gửi cảnh báo chặn khóa sai (403)"

  [[ "$(qt_ma POST /webhook/khong-ton-tai '{"Content-Type":"application/json"}' '{}')" = 404 ]] \
    || fail "Đường dẫn lạ không trả 404"
  pass "Đường dẫn lạ dưới /webhook/ trả 404 (chỉ mở đúng danh sách điểm nhận)"

  payload='{"trang_thai":"DAT","noi_dung":"Sao lưu thử từ bài kiểm động cơ quy trình","may_tram":[{"ten":"kiem-thu-01","canh_bao":[]}]}'
  [[ "$(qt_ma POST /webhook/onebee-bao-cao-sao-luu "${hdr}" "${payload}")" = 200 ]] \
    || fail "Điểm nhận báo cáo sao lưu không nhận yêu cầu hợp lệ"
  wait_mail "Sao lưu ĐẠT"
  pass "Thư báo cáo sao lưu tới hòm thư quản trị (qua SMTP của Box)"

  [[ "$(qt_ma POST /webhook/onebee-nhac-han "${hdr}" '{"hom_nay":"2026-10-17"}')" = 200 ]] \
    || fail "Điểm nhận nhắc hạn không nhận yêu cầu hợp lệ"
  wait_mail "Nhắc hạn nộp: 1 việc — gần nhất còn 3 ngày"
  pass "Thư nhắc hạn nộp: ngày 17/10 → hạn 20/10, còn 3 ngày"

  ma="$(qt_ma POST /webhook/onebee-tinh-trang "${hdr_tram}" \
    "{\"ten\":\"chua-cap\",\"du_lieu\":\"{}\",\"ky\":\"$(printf '0%.0s' $(seq 64))\"}")"
  [[ "${ma}" = 403 ]] || fail "Máy chưa cấp không bị từ chối (mã ${ma})"
  [[ ! -e /srv/onebee/tinh-trang-may/chua-cap.json ]] || fail "Máy chưa cấp vẫn ghi được tệp tình trạng"
  pass "Máy trạm CHƯA CẤP bị từ chối (403), không ghi được tệp tình trạng"

  # Máy đã cấp gửi bao bì có chữ ký hỏng: động cơ quy trình lưu nguyên bao bì, Box tự kiểm chữ ký và gắn nhãn sai
  onebee-box them-may kiem-thu-01 >/dev/null 2>&1 || fail "Không cấp được máy kiểm thử kiem-thu-01"
  trap 'onebee-box thu-hoi-may kiem-thu-01 --dong-y >/dev/null 2>&1 || true' EXIT
  payload="$(python3 -c '
import json
ten = "kiem-thu-01"
print(json.dumps({"ten": ten, "du_lieu": json.dumps({"ten": ten, "gui_luc": 1}), "ky": "a" * 64}))')"
  [[ "$(qt_ma POST /webhook/onebee-tinh-trang "${hdr_tram}" "${payload}")" = 200 ]] \
    || fail "Máy đã cấp gửi báo cáo không được nhận"
  onebee-box may-tram | grep -A3 '^kiem-thu-01 ' | grep -q 'sai chữ ký' \
    || { echo 'FAIL  Báo cáo sai chữ ký không bị gắn nhãn'; onebee-box may-tram; exit 1; }
  pass "Báo cáo tình trạng sai chữ ký của máy đã cấp bị Box gắn nhãn 'sai chữ ký' trong bảng onebee-box may-tram"
  onebee-box thu-hoi-may kiem-thu-01 --dong-y >/dev/null || fail "Không thu hồi được máy kiểm thử kiem-thu-01"
  trap - EXIT
  [[ ! -e /srv/onebee/may-da-cap/kiem-thu-01 ]] || fail "Máy kiểm thử vẫn còn trong danh sách máy đã cấp"
}

# =====================================================================
# Phần 2 — phê duyệt đơn hàng (chỉ khi Box đã bật HTTPS + đăng nhập một lần)
# =====================================================================
phe_duyet() {
  local host ip ca out url code thu_co
  host="$(python3 -c 'import json; print(json.load(open("/opt/onebee-box/quy-trinh/cau-hinh.json"))["api_goc"].split("://", 1)[1])')"
  ip="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
  ca="${S}/ca/root.crt"
  [[ -e "${S}/https-da-bat" ]] || fail "Chạy chế độ phe-duyet khi Box đã bật HTTPS (đăng nhập một lần + tên Box)"
  d="$(mktemp -d /root/qt-phe-duyet.XXXXXX)"
  chmod 700 "${d}"

  c() { curl -s -m 20 --cacert "${ca}" --resolve "${host}:443:${ip}" "$@"; }
  ma() { c -o /dev/null -w '%{http_code}' "$@"; }
  don_dep() {
    [[ -z "${id_khac:-}${id_tu:-}" ]] || docker exec -i onebee-postgres psql -X -q -U postgres -d onebee -c \
      "DELETE FROM onebee.don_hang WHERE id IN (${id_khac:-0}, ${id_tu:-0})" >/dev/null 2>&1 || true
    onebee-box xoa-nguoi duyet >/dev/null 2>&1 || true
    [[ -z "${d}" ]] || rm -rf "${d}"
  }
  trap don_dep EXIT

  # Tài khoản quản lý riêng cho bài kiểm (không đụng tài khoản của các bài khác)
  if onebee-box danh-sach-nguoi 2>/dev/null | grep -q '^duyet '; then onebee-box xoa-nguoi duyet >/dev/null; fi
  out="$(onebee-box them-nguoi duyet quan_ly)" || fail "Không tạo được tài khoản quản lý duyet"
  (umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${d}/mk")
  [[ "$(wc -c <"${d}/mk")" = 17 ]] || fail "them-nguoi duyet không in mật khẩu tạm"

  # Đăng nhập một lớp → mã xác minh từ onebee-box → ghi danh TOTP → qua hai lớp (quan_ly)
  dang_nhap() {
    (umask 077; printf '{"username":"duyet","password":"%s","keepMeLoggedIn":false}' "$(cat "${d}/mk")" >"${d}/dn.json")
    rm -f "${d}/jar"
    ma -c "${d}/jar" -H 'Content-Type: application/json' -d @"${d}/dn.json" "https://${host}/dangnhap/api/firstfactor"
    rm -f "${d}/dn.json"
  }
  totp() {
    python3 - "${d}/totp" 0 <<'PY'
import base64, hashlib, hmac, struct, sys, time
khoa = open(sys.argv[1]).read().strip().upper()
k = base64.b32decode(khoa + "=" * (-len(khoa) % 8))
h = hmac.new(k, struct.pack(">Q", int(time.time()) // 30 + int(sys.argv[2])), hashlib.sha1).digest()
o = h[-1] & 15
print("%06d" % ((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1000000))
PY
  }
  local ok=""
  for _ in $(seq 15); do [[ "$(dang_nhap)" = 200 ]] && { ok=1; break; }; sleep 2; done
  [[ -n "${ok}" ]] || fail "Tài khoản duyet không đăng nhập được"
  [[ "$(ma -b "${d}/jar" -c "${d}/jar" -X POST "https://${host}/dangnhap/api/user/session/elevation")" = 200 ]] \
    || fail "duyet không xin được mã xác minh"
  sleep 1
  (umask 077; printf '{"otc":"%s"}' "$(onebee-box ma-xac-nhan | sed -n 's/^Mã xác minh: //p')" >"${d}/otc.json")
  [[ "$(ma -b "${d}/jar" -c "${d}/jar" -X PUT -H 'Content-Type: application/json' -d @"${d}/otc.json" \
        "https://${host}/dangnhap/api/user/session/elevation")" = 200 ]] || fail "Mã xác minh của duyet không được nhận"
  c -b "${d}/jar" -c "${d}/jar" -X PUT -H 'Content-Type: application/json' -d '{"algorithm":"SHA1","length":6,"period":30}' \
    "https://${host}/dangnhap/api/secondfactor/totp/register" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["base32_secret"])' >"${d}/totp" \
    || fail "duyet không bắt đầu ghi danh TOTP được"
  (umask 077; printf '{"token":"%s"}' "$(totp)" >"${d}/totp.json")
  [[ "$(ma -b "${d}/jar" -c "${d}/jar" -X POST -H 'Content-Type: application/json' -d @"${d}/totp.json" \
        "https://${host}/dangnhap/api/secondfactor/totp/register")" = 200 ]] || fail "Ghi danh TOTP của duyet không xong"
  sleep $(( 31 - $(date +%s) % 30 ))   # mã đã dùng để ghi danh không dùng lại được → chờ bước thời gian kế
  (umask 077; printf '{"token":"%s"}' "$(totp)" >"${d}/totp.json")
  [[ "$(ma -b "${d}/jar" -c "${d}/jar" -X POST -H 'Content-Type: application/json' -d @"${d}/totp.json" \
        "https://${host}/dangnhap/api/secondfactor/totp")" = 200 ]] || fail "Lớp hai (TOTP) của duyet không qua"

  # Dữ liệu thử: một đơn của người khác (an) và một đơn của chính duyet, ghi thẳng CSDL để không phụ thuộc phiên người khác
  thu_co=0
  if python3 -c 'import json,sys; sys.exit(0 if json.load(open("/opt/onebee-box/quy-trinh/cau-hinh.json"))["thu"]["host"] else 1)'; then
    khoi_dong_mailpit   # phải sẵn sàng TRƯỚC khi duyệt: mô-đun gửi thư ngay trong yêu cầu duyệt
    thu_co=1
  fi
  id_khac="$(docker exec -i onebee-postgres psql -X -q -At -U postgres -d onebee -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, nguoi_tao, trang_thai_duyet, ghi_chu)
VALUES ('Khách kiểm thử', 'Hàng kiểm thử', 1, 1, 1, 'an', 'CHO_DUYET', 'quy-trinh-phe-duyet-khac') RETURNING id;
SQL
)"
  id_tu="$(docker exec -i onebee-postgres psql -X -q -At -U postgres -d onebee -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, nguoi_tao, trang_thai_duyet, ghi_chu)
VALUES ('Khách kiểm thử', 'Hàng kiểm thử', 1, 1, 1, 'duyet', 'CHO_DUYET', 'quy-trinh-phe-duyet-tu') RETURNING id;
SQL
)"
  id_khac="${id_khac//[[:space:]]/}"; id_tu="${id_tu//[[:space:]]/}"
  [[ "${id_khac}" =~ ^[0-9]+$ && "${id_tu}" =~ ^[0-9]+$ ]] || fail "Không tạo được đơn kiểm thử trong CSDL"
  url="https://${host}/quy-trinh/webhook/onebee-phe-duyet"

  # 1. Không phiên → Caddy/Authelia trả 401 (Accept: application/json), không tới được động cơ quy trình
  code="$(ma -H 'Accept: application/json' -X POST -H 'Content-Type: application/json' \
    -d "{\"id\":${id_khac},\"trang_thai_duyet\":\"DA_DUYET\"}" "${url}")"
  [[ "${code}" = 401 ]] || fail "Gọi phê duyệt không phiên không bị chặn 401 (mã ${code})"
  pass "Gọi phê duyệt KHÔNG PHIÊN bị chặn (401)"

  # 2. Từ chối không ghi lý do → 400
  code="$(ma -b "${d}/jar" -H 'Accept: application/json' -X POST -H 'Content-Type: application/json' \
    -d "{\"id\":${id_khac},\"trang_thai_duyet\":\"TU_CHOI\"}" "${url}")"
  [[ "${code}" = 400 ]] || fail "Từ chối không lý do không trả 400 (mã ${code})"
  pass "Từ chối đơn KHÔNG GHI LÝ DO bị từ chối (400)"

  # 3. Tự duyệt đơn của chính mình → 403 (chặn sớm ở động cơ quy trình; ràng buộc CSDL là rào chắn cuối)
  code="$(ma -b "${d}/jar" -H 'Accept: application/json' -X POST -H 'Content-Type: application/json' \
    -d "{\"id\":${id_tu},\"trang_thai_duyet\":\"DA_DUYET\"}" "${url}")"
  [[ "${code}" = 403 ]] || fail "Tự duyệt đơn của mình không bị chặn 403 (mã ${code})"
  pass "Quản lý TỰ DUYỆT đơn của chính mình bị từ chối (403)"

  # 4. Quản lý duyệt đơn của người khác → 200 DA_DUYET, ghi đúng người duyệt trong CSDL
  code="$(c -b "${d}/jar" -o "${d}/tl" -w '%{http_code}' -H 'Accept: application/json' -X POST \
    -H 'Content-Type: application/json' -d "{\"id\":${id_khac},\"trang_thai_duyet\":\"DA_DUYET\",\"ly_do_duyet\":\"Đủ hàng\"}" "${url}")"
  [[ "${code}" = 200 ]] || { echo "FAIL  Duyệt đơn của người khác lỗi (mã ${code})"; cat "${d}/tl"; exit 1; }
  python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
assert d["id"] == int(sys.argv[2]) and d["trang_thai_duyet"] == "DA_DUYET" and d["nguoi_duyet"] == "duyet", d' \
    "${d}/tl" "${id_khac}" || { echo 'FAIL  Phản hồi duyệt đơn sai'; cat "${d}/tl"; exit 1; }
  [[ "$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee \
        -c "SELECT trang_thai_duyet || ' ' || nguoi_duyet FROM onebee.don_hang WHERE id = ${id_khac}")" = "DA_DUYET duyet" ]] \
    || fail "CSDL không ghi nhận DA_DUYET bởi duyet"
  pass "Quản lý duyệt đơn của người khác → DA_DUYET, ghi đúng người duyệt trong CSDL"

  # Thư thông báo kết quả duyệt gửi về hòm thư quản trị (bỏ qua khi Box chưa cấu hình SMTP)
  if [[ "${thu_co}" = 1 ]]; then
    wait_mail "Đơn hàng ${id_khac} đã được duyệt"
    pass "Thư thông báo phê duyệt đơn ${id_khac} tới hòm thư quản trị"
  fi
}

case "${CHE_DO}" in
  co-ban) co_ban ;;
  phe-duyet) phe_duyet ;;
  *) fail "Cách dùng: $0 [phe-duyet]" ;;
esac
