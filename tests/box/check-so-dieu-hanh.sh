#!/usr/bin/env bash
# Kiểm ứng dụng Sổ điều hành H-P-D-I trên Box đã BẬT HTTPS và đăng nhập một lần:
# chưa đăng nhập bị chuyển sang trang đăng nhập; nhân viên gửi đơn kèm PDF qua kho tệp (CLEAN) → đơn CHO_DUYET;
# mức độ ngoài danh mục → 400; nhân viên khác không đọc được đơn; tự duyệt bị từ chối; quản lý duyệt → DA_DUYET;
# nhân viên không đọc được bảng điều hành (403); quản lý nhận số liệu khớp CSDL; tóm tắt tuần chỉ gửi số liệu tổng hợp
# (kiểm trên mã trang đã cài) và Trợ lý trả lời tiếng Việt; trang tĩnh phục vụ sau đăng nhập với CSP chặt.
# check-https.sh gọi bài này trong phần HTTPS (sau check-sso-cong-api.sh), trước khi chạy lại bộ cài.
# Cách dùng: check-so-dieu-hanh.sh <container-Box>
set -euo pipefail
BOX="$1"
box() { docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; }
# Xóa mật khẩu tạm, cookie phiên, khóa TOTP của bài kiểm dù đạt hay lỗi
trap 'docker exec "${BOX}" rm -rf /root/sdlh >/dev/null 2>&1 || true' EXIT

# ---------------------------------------------------------------------------------------------------
# Tài khoản kiểm và phiên đăng nhập (mật khẩu/mã chỉ trong /root/sdlh, quyền 700)
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: PHIÊN ĐĂNG NHẬP ====="
box <<'EOF'
install -d -m 0700 /root/sdlh
cat >/root/sdlh/chung.sh <<'CHUNG'
IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
TEN="box.$(sed -n 's/^onebee_box_ma_don_vi: *//p' /root/onebee-test/box/ansible/group_vars/all.yml | tr -d '"')".onebee.internal
CA=/etc/onebee-box/secrets/ca/root.crt
D=/root/sdlh
c() { curl -s -m 30 --cacert "${CA}" --resolve "${TEN}:443:${IP}" "$@"; }
ma() { c -o /dev/null -w '%{http_code}' "$@"; }
dang_nhap() {
  (umask 077; printf '{"username":"%s","password":"%s","keepMeLoggedIn":false}' "$1" "$(cat "$2")" >"${D}/dn.json")
  rm -f "$3"
  ma -c "$3" -H 'Content-Type: application/json' -d @"${D}/dn.json" "https://${TEN}/dangnhap/api/firstfactor"
  rm -f "${D}/dn.json"
}
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

. /root/sdlh/chung.sh
for u in sdlh-nv-a sdlh-nv-b sdlh-ql; do onebee-box xoa-nguoi "${u}" >/dev/null 2>&1 || true; done
for u in "sdlh-nv-a nhan_vien" "sdlh-nv-b nhan_vien" "sdlh-ql quan_ly"; do
  set -- ${u}
  out="$(onebee-box them-nguoi "$1" "$2")" || { echo "FAIL  them-nguoi $1 $2"; exit 1; }
  (umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${D}/mk-$1")
  [ -s "${D}/mk-$1" ] || { echo "FAIL  them-nguoi $1 không in mật khẩu tạm"; exit 1; }
done

for u in sdlh-nv-a sdlh-nv-b; do
  ok=""; for _ in $(seq 15); do [ "$(dang_nhap "${u}" "${D}/mk-${u}" "${D}/jar-${u}")" = 200 ] && { ok=1; break; }; sleep 2; done
  [ -n "${ok}" ] || { echo "FAIL  ${u} không đăng nhập được"; exit 1; }
done
[ "$(dang_nhap sdlh-ql "${D}/mk-sdlh-ql" "${D}/jar-sdlh-ql")" = 200 ] || { echo 'FAIL  sdlh-ql không đăng nhập được'; exit 1; }
[ "$(ma -b "${D}/jar-sdlh-ql" -c "${D}/jar-sdlh-ql" -X POST "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] \
  || { echo 'FAIL  sdlh-ql không xin được mã xác minh'; exit 1; }
sleep 1
(umask 077; printf '{"otc":"%s"}' "$(onebee-box ma-xac-nhan | sed -n 's/^Mã xác minh: //p')" >"${D}/otc.json")
[ "$(ma -b "${D}/jar-sdlh-ql" -c "${D}/jar-sdlh-ql" -X PUT -H 'Content-Type: application/json' -d @"${D}/otc.json" \
      "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] || { echo 'FAIL  mã xác minh của sdlh-ql không được nhận'; exit 1; }
c -b "${D}/jar-sdlh-ql" -c "${D}/jar-sdlh-ql" -X PUT -H 'Content-Type: application/json' -d '{"algorithm":"SHA1","length":6,"period":30}' \
  "https://${TEN}/dangnhap/api/secondfactor/totp/register" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["base32_secret"])' >"${D}/totp-ql" \
  || { echo 'FAIL  sdlh-ql không bắt đầu ghi danh TOTP được'; exit 1; }
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-ql")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-sdlh-ql" -c "${D}/jar-sdlh-ql" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" \
      "https://${TEN}/dangnhap/api/secondfactor/totp/register")" = 200 ] || { echo 'FAIL  ghi danh TOTP của sdlh-ql không xong'; exit 1; }
sleep $(( 31 - $(date +%s) % 30 ))
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-ql")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-sdlh-ql" -c "${D}/jar-sdlh-ql" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" \
      "https://${TEN}/dangnhap/api/secondfactor/totp")" = 200 ] || { echo 'FAIL  lớp hai TOTP của sdlh-ql không qua'; exit 1; }
[ "$(c -b "${D}/jar-sdlh-nv-a" "https://${TEN}/api/toi")" = '{"ten": "sdlh-nv-a", "vai_tro": "nhan_vien"}' ] \
  || { echo 'FAIL  /api/toi của sdlh-nv-a sai'; exit 1; }
[ "$(c -b "${D}/jar-sdlh-ql" "https://${TEN}/api/toi")" = '{"ten": "sdlh-ql", "vai_tro": "quan_ly"}' ] \
  || { echo 'FAIL  /api/toi của sdlh-ql sai'; exit 1; }
echo 'PASS  Ba tài khoản kiểm: hai nhân viên một lớp, quản lý qua hai lớp; /api/toi trả đúng tên và vai trò'
EOF

# ---------------------------------------------------------------------------------------------------
# Chưa đăng nhập: trang nằm sau forward_auth
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: CHƯA ĐĂNG NHẬP ====="
box <<'EOF'
. /root/sdlh/chung.sh
loc="$(c -o /dev/null -w '%{http_code} %{redirect_url}' "https://${TEN}/so-dieu-hanh/")"
grep -Eq "^30[23] https://${TEN}/dangnhap/" <<<"${loc}" \
  || { echo "FAIL  /so-dieu-hanh/ chưa đăng nhập không chuyển tới trang đăng nhập: ${loc}"; exit 1; }
echo 'PASS  Chưa đăng nhập mở /so-dieu-hanh/: chuyển sang trang đăng nhập một lần'
EOF

# ---------------------------------------------------------------------------------------------------
# Nhân viên gửi đơn kèm PDF: kho tệp kiểm dịch CLEAN, đơn vào CHO_DUYET
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: GỬI ĐƠN KÈM TỆP ====="
box <<'EOF'
. /root/sdlh/chung.sh
(umask 077; cat >"${D}/bao-gia.pdf" <<'PDF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF
PDF
)
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' -X POST --data-binary @"${D}/bao-gia.pdf" \
        -H 'Content-Type: application/pdf' "https://${TEN}/files/sdlh-bao-gia.pdf")"
[ "${code}" = 201 ] || { echo "FAIL  tải PDF sạch qua /files/ không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
docsach="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); t=d["tep"] if isinstance(d,dict) and "tep" in d else d; print(t["id"], t["trang_thai_quet"])' "${D}/tl")"
id_tep="${docsach%% *}"; trang_thai_tep="${docsach#* }"
[ "${trang_thai_tep}" = CLEAN ] || { echo "FAIL  tệp PDF không đạt CLEAN (${trang_thai_tep}): $(cat "${D}/tl")"; exit 1; }
(umask 077; printf '{"khach_hang":"HTX Bình Minh","mat_hang":"Mật ong","so_luong_kg":3,"don_gia":100000,"thanh_tien":300000,"ngay_giao":"2026-12-01"}' >"${D}/don.json")
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
        -d @"${D}/don.json" "https://${TEN}/api/don_hang")"
[ "${code}" = 201 ] || { echo "FAIL  gửi đơn không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
id_don="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"], d["nguoi_tao"], d["trang_thai_duyet"])' "${D}/tl")"
[ "${id_don}" = "$(printf '%s sdlh-nv-a CHO_DUYET' "${id_don%% *}")" ] || { echo "FAIL  đơn sai người tạo/trạng thái: ${id_don}"; exit 1; }
printf '%s\n%s\n' "${id_tep}" "${id_don%% *}" >"${D}/id-don-a"
echo "PASS  Nhân viên gửi đơn kèm PDF: tệp ${id_tep} CLEAN, đơn ${id_don%% *} CHO_DUYET, người tạo lấy từ JWT"
EOF

# ---------------------------------------------------------------------------------------------------
# Mức độ ngoài danh mục bị CSDL từ chối
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: KIỂM DỮ LIỆU ====="
box <<'EOF'
. /root/sdlh/chung.sh
(umask 077; printf '{"loai":"Máy in / máy quét","muc_do":"khan-cap","mo_ta":"Thử mức độ ngoài danh mục"}' >"${D}/ht.json")
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/ht.json" "https://${TEN}/api/yeu_cau_ho_tro")"
[ "${code}" = 400 ] && grep -q muc_do_trong_danh_muc "${D}/tl" \
  || { echo "FAIL  mức độ ngoài danh mục không bị 400 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Mức độ ngoài danh mục: 400 (ràng buộc muc_do_trong_danh_muc trong CSDL)'
EOF

# ---------------------------------------------------------------------------------------------------
# RLS: nhân viên khác không đọc được đơn
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: PHÂN QUYỀN DÒNG ====="
box <<'EOF'
. /root/sdlh/chung.sh
{ read -r id_tep; read -r id_a; } <"${D}/id-don-a"
code="$(c -b "${D}/jar-sdlh-nv-b" -o "${D}/tl" -w '%{http_code}' "https://${TEN}/api/don_hang?id=eq.${id_a}&select=id,nguoi_tao")"
[ "${code}" = 200 ] || { echo "FAIL  nhân viên B đọc đơn lỗi (mã ${code}): $(cat "${D}/tl")"; exit 1; }
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d == [] else 1)' "${D}/tl" \
  || { echo "FAIL  nhân viên B thấy đơn của nhân viên A: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Nhân viên B không thấy đơn của nhân viên A (RLS lọc theo người tạo)'
EOF

# ---------------------------------------------------------------------------------------------------
# Tự duyệt và quản lý duyệt qua động cơ quy trình
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: DUYỆT ĐƠN ====="
box <<'EOF'
. /root/sdlh/chung.sh
{ read -r id_tep; read -r id_a; } <"${D}/id-don-a"
(umask 077; printf '{"khach_hang":"HTX Bình Minh","mat_hang":"Mật ong","so_luong_kg":1,"don_gia":100000,"thanh_tien":100000}' >"${D}/don-ql.json")
code="$(c -b "${D}/jar-sdlh-ql" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
        -d @"${D}/don-ql.json" "https://${TEN}/api/don_hang")"
[ "${code}" = 201 ] || { echo "FAIL  quản lý tạo đơn của mình không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
id_ql="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"])' "${D}/tl")"

duyet() {
  (umask 077; printf '{"id":%s,"trang_thai_duyet":"%s","ly_do_duyet":"%s"}' "$1" "$2" "${3:-}" >"${D}/phe-duyet.json")
  c -b "${D}/jar-sdlh-ql" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
    -d @"${D}/phe-duyet.json" "https://${TEN}/quy-trinh/webhook/onebee-phe-duyet"
}
code="$(duyet "${id_ql}" DA_DUYET 'Tự duyệt thử')"
[ "${code}" = 403 ] || { echo "FAIL  quản lý tự duyệt đơn của mình không bị từ chối (mã ${code}): $(cat "${D}/tl")"; exit 1; }
code="$(c -b "${D}/jar-sdlh-ql" -o "${D}/tl" -w '%{http_code}' "https://${TEN}/api/don_hang?id=eq.${id_ql}&select=trang_thai_duyet")"
[ "${code}" = 200 ] && grep -q CHO_DUYET "${D}/tl" || { echo "FAIL  đơn tự duyệt đã đổi trạng thái: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Quản lý tự duyệt đơn của chính mình: bị từ chối 403, đơn vẫn CHO_DUYET'

(umask 077; printf '{"id":%s,"trang_thai_duyet":"DA_DUYET","ly_do_duyet":""}' "${id_a}" >"${D}/nv-tu-duyet.json")
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/nv-tu-duyet.json" "https://${TEN}/quy-trinh/webhook/onebee-phe-duyet")"
[ "${code}" = 403 ] || { echo "FAIL  nhân viên tự duyệt đơn của mình không bị từ chối (mã ${code}): $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Nhân viên gọi điểm duyệt cho đơn của chính mình: bị từ chối 403 (ngoài nhóm duyệt và chặn tự duyệt)'

code="$(duyet "${id_a}" DA_DUYET 'Đủ chứng từ')"
[ "${code}" = 200 ] || { echo "FAIL  quản lý duyệt đơn của nhân viên không nhận 200 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("trang_thai_duyet") == "DA_DUYET" and d.get("nguoi_duyet") == "sdlh-ql" else 1)' "${D}/tl" \
  || { echo "FAIL  sau duyệt trạng thái/người duyệt sai: $(cat "${D}/tl")"; exit 1; }
printf '%s\n' "${id_ql}" >"${D}/id-don-ql"
echo 'PASS  Quản lý duyệt đơn của nhân viên: 200, DA_DUYET, người duyệt lấy từ phiên đăng nhập'
EOF

# ---------------------------------------------------------------------------------------------------
# Bảng điều hành: nhân viên 403, quản lý nhận số liệu khớp CSDL
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: BẢNG ĐIỀU HÀNH ====="
box <<'EOF'
. /root/sdlh/chung.sh
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' "https://${TEN}/api/khao_sat_tong_hop?select=tuan,so_phieu")"
[ "${code}" = 403 ] || { echo "FAIL  nhân viên đọc khung nhìn tổng hợp không nhận 403 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Nhân viên mở bảng điều hành: 403 (không có quyền trên khung nhìn tổng hợp trong CSDL)'

(umask 077; printf '{"diem_1":4,"diem_2":5,"diem_3":4,"diem_4":5,"diem_5":4,"gop_y":"Máy chạy ổn"}' >"${D}/ks.json")
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/ks.json" "https://${TEN}/api/khao_sat")"
[ "${code}" = 201 ] || { echo "FAIL  nhân viên gửi khảo sát không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
code="$(c -b "${D}/jar-sdlh-ql" -o "${D}/tl" -w '%{http_code}' "https://${TEN}/api/khao_sat_tong_hop?select=tuan,so_phieu")"
[ "${code}" = 200 ] || { echo "FAIL  quản lý đọc khung nhìn tổng hợp lỗi (mã ${code}): $(cat "${D}/tl")"; exit 1; }
so_phieu_api="$(python3 -c 'import json,sys; print(sum(x["so_phieu"] for x in json.load(open(sys.argv[1]))))' "${D}/tl")"
so_phieu_db="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c 'SELECT count(*) FROM onebee.khao_sat')"
[ "${so_phieu_api}" = "${so_phieu_db}" ] || { echo "FAIL  số phiếu khảo sát lệch: API ${so_phieu_api}, CSDL ${so_phieu_db}"; exit 1; }

code="$(c -b "${D}/jar-sdlh-ql" -o "${D}/tl" -w '%{http_code}' "https://${TEN}/api/don_hang?select=trang_thai_duyet")"
[ "${code}" = 200 ] || { echo "FAIL  quản lý đọc đơn hàng lỗi (mã ${code}): $(cat "${D}/tl")"; exit 1; }
don_api="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("%d|%d|%d" % (sum(1 for x in d if x["trang_thai_duyet"]=="CHO_DUYET"), sum(1 for x in d if x["trang_thai_duyet"]=="DA_DUYET"), sum(1 for x in d if x["trang_thai_duyet"]=="TU_CHOI")))' "${D}/tl")"
don_db="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c "SELECT count(*) FILTER (WHERE trang_thai_duyet='CHO_DUYET'), count(*) FILTER (WHERE trang_thai_duyet='DA_DUYET'), count(*) FILTER (WHERE trang_thai_duyet='TU_CHOI') FROM onebee.don_hang")"
[ "${don_api}" = "${don_db}" ] || { echo "FAIL  số đơn theo trạng thái lệch: API [${don_api}], CSDL [${don_db}]"; exit 1; }
echo 'PASS  Quản lý nhận số liệu khớp CSDL: số phiếu khảo sát và số đơn theo trạng thái'
EOF

# ---------------------------------------------------------------------------------------------------
# Tóm tắt tuần: mã trang thật chỉ gửi số liệu tổng hợp; Trợ lý trả lời tiếng Việt
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: TÓM TẮT TUẦN ====="
box <<'EOF'
. /root/sdlh/chung.sh
docker cp /opt/onebee-box/portal/site/so-dieu-hanh/so-dieu-hanh.js onebee-quy-trinh:/tmp/sdlh.js >/dev/null
docker exec onebee-quy-trinh node -e '
const vm = require("vm"), fs = require("fs");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync("/tmp/sdlh.js", "utf8"), ctx);
const ban = {
  don_hang: { tong: 7, cho_duyet: 2, da_duyet: 4, tu_choi: 1 },
  ho_tro: { tong: 2, gap: 1 },
  may_tram: 3,
  tep: { tong: 5, sach: 4, nhiem: 1 },
  khao_sat: [{ tuan: "2026-11-09", so_phieu: 4, diem_tb: 4.5, ten: "Nguyễn Văn An", gop_y: "gọi 0912345678" }],
  nguoi_tao: "Nguyễn Văn An", khach_hang: "HTX Bình Minh", ghi_chu: "gọi 0912345678",
  ten_tep: "bao-gia-nguyen-van-an.pdf", nguoi_bao: "Trần Thị Bình", nguoi_dung: "sdlh-ql"
};
process.stdout.write(vm.runInContext("taoLoiNhacTomTat(" + JSON.stringify(ban) + ")", ctx));
' >"${D}/noi-dung.txt" || { echo 'FAIL  chạy mã trang trong node để dựng lời nhắc tóm tắt'; exit 1; }
docker exec -u 0 onebee-quy-trinh rm -f /tmp/sdlh.js   # tệp do docker cp ghi bằng root; Node-RED chạy uid 1000
grep -q "tiếng Việt" "${D}/noi-dung.txt" && grep -q "không bịa" "${D}/noi-dung.txt" \
  || { echo 'FAIL  lời nhắc tóm tắt thiếu dặn dò tiếng Việt/không bịa'; cat "${D}/noi-dung.txt"; exit 1; }
! grep -Eq "Nguyễn|Bình Minh|0912345678|bao-gia|Trần Thị Bình|sdlh-ql" "${D}/noi-dung.txt" \
  || { echo 'FAIL  lời nhắc tóm tắt còn tên người/số điện thoại/tên tệp'; cat "${D}/noi-dung.txt"; exit 1; }
grep -q '"don_hang"' "${D}/noi-dung.txt" || { echo 'FAIL  lời nhắc tóm tắt thiếu số liệu'; cat "${D}/noi-dung.txt"; exit 1; }
python3 - "${D}/noi-dung.txt" <<'PY'
import json, sys
noi_dung = open(sys.argv[1], encoding="utf-8").read()
json.dump({"noi_dung": noi_dung}, open("/root/sdlh/tom-tat.json", "w", encoding="utf-8"), ensure_ascii=False)
PY
code="$(c -b "${D}/jar-sdlh-ql" -m 300 -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/tom-tat.json" "https://${TEN}/ai/tom-tat")"
[ "${code}" = 200 ] || { echo "FAIL  Trợ lý tóm tắt không nhận 200 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); t=d.get("tom_tat"); sys.exit(0 if isinstance(t, str) and t.strip() else 1)' "${D}/tl" \
  || { echo "FAIL  Trợ lý không trả bản tóm tắt: $(cat "${D}/tl")"; exit 1; }
# Bỏ dòng nhắc cố định của dịch vụ để kiểm chính câu tóm tắt của mô hình (không tính dòng nhắc tiếng Việt có sẵn)
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["tom_tat"].replace("Trợ lý có thể sai — hãy kiểm tra lại văn bản gốc trước khi dùng.", ""), end="")' \
  "${D}/tl" >"${D}/tom-tat-chu.txt"
grep -q "[ạảãàáâậầấẩẫăắằặẳẵêếềệểễôốồộổỗơớờợởỡưứừựửữđ]" "${D}/tom-tat-chu.txt" \
  || { echo "FAIL  bản tóm tắt không có chữ tiếng Việt: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Tóm tắt tuần: mã trang chỉ dựng số liệu tổng hợp (không tên/số điện thoại/tên tệp), Trợ lý trả chữ tiếng Việt'
EOF

# ---------------------------------------------------------------------------------------------------
# Trang tĩnh sau đăng nhập + CSP
# ---------------------------------------------------------------------------------------------------
echo "===== SỔ ĐIỀU HÀNH: TRANG TĨNH ====="
box <<'EOF'
. /root/sdlh/chung.sh
code="$(c -b "${D}/jar-sdlh-nv-a" -o "${D}/trang.html" -w '%{http_code}' "https://${TEN}/so-dieu-hanh/")"
[ "${code}" = 200 ] || { echo "FAIL  nhân viên mở /so-dieu-hanh/ không nhận 200 (mã ${code})"; exit 1; }
for x in 'id="khu-h"' 'id="khu-p"' 'id="khu-d"' 'id="khu-i"' 'so-dieu-hanh.js' 'so-dieu-hanh.css'; do
  grep -q "${x}" "${D}/trang.html" || { echo "FAIL  trang thiếu ${x}"; exit 1; }
done
hdr="$(c -b "${D}/jar-sdlh-nv-a" -o /dev/null -D - "https://${TEN}/so-dieu-hanh/" | tr -d '\r')"
grep -qi "content-security-policy:.*default-src 'none'" <<<"${hdr}" || { echo 'FAIL  trang thiếu CSP default-src none'; head -20 <<<"${hdr}"; exit 1; }
grep -qi "content-security-policy:.*script-src 'self'" <<<"${hdr}" || { echo 'FAIL  trang thiếu CSP script-src self'; exit 1; }
! grep -qi 'unsafe-inline\|unsafe-eval' <<<"${hdr}" || { echo 'FAIL  CSP còn unsafe-inline/unsafe-eval'; exit 1; }
grep -qi '^x-content-type-options: nosniff' <<<"${hdr}" || { echo 'FAIL  trang thiếu X-Content-Type-Options nosniff'; exit 1; }
[ "$(ma -b "${D}/jar-sdlh-nv-a" "https://${TEN}/so-dieu-hanh/so-dieu-hanh.js")" = 200 ] || { echo 'FAIL  không tải được mã trang'; exit 1; }
[ "$(ma -b "${D}/jar-sdlh-nv-a" "https://${TEN}/so-dieu-hanh/so-dieu-hanh.css")" = 200 ] || { echo 'FAIL  không tải được kiểu trang'; exit 1; }
echo 'PASS  Trang tĩnh phục vụ sau đăng nhập: đủ bốn khu H/P/D/I, CSS/JS cùng gốc 200, CSP chặt không unsafe-inline'
EOF
