#!/usr/bin/env bash
# Kiểm tra kho tệp của OneBee Box (chạy TRONG Box, khi HTTPS + đăng nhập một lần đang bật; check-https.sh gọi sau
# check-du-lieu-qua-cong.sh): không phiên → 401; PDF sạch → 201, metadata tep_dinh_kem CLEAN do chính người tải ghi
# (JWT + RLS), tải lại đúng SHA-256; EICAR → 422, metadata INFECTED, không tải xuống được; đuôi ngoài danh mục → 415;
# tệp 11 MB → 413; nhân viên khác không đọc được metadata lẫn tệp của người tải (dịch vụ 404, RLS qua cổng API trả rỗng).
# Cần: curl, python3, onebee-box (dựng tài khoản tạm a1/b1), chữ ký ClamAV (tải sẵn hoặc tự tải khi Box có Internet).
set -euo pipefail
GV=/root/onebee-test/box/ansible/group_vars/all.yml
IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
TEN="box.$(sed -n 's/^onebee_box_ma_don_vi: *//p' "${GV}" | tr -d '"').onebee.internal"
CA=/etc/onebee-box/secrets/ca/root.crt
D=/root/kho-tep-kiem
install -d -m 0700 "${D}"
trap 'rm -rf "${D}"' EXIT
c() { curl -s -m 60 --cacert "${CA}" --resolve "${TEN}:443:${IP}" "$@"; }
ma() { c -o /dev/null -w '%{http_code}' "$@"; }
psql_box() { docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c "$1"; }
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; exit 1; }

echo "===== KHO TỆP: CHUẨN BỊ ====="
# Chưa có chữ ký (bộ cài không có Internet): thử tải một lần; vẫn thiếu thì dừng với hướng dẫn nộp ngoại tuyến
if ! compgen -G "/srv/onebee/clamav/*.cvd" >/dev/null && ! compgen -G "/srv/onebee/clamav/*.cld" >/dev/null; then
  docker run --rm -v /srv/onebee/clamav:/var/lib/clamav --entrypoint freshclam \
    onebee/clamav-khong-unrar:1.5.4 --datadir=/var/lib/clamav >/dev/null 2>&1 || true
fi
compgen -G "/srv/onebee/clamav/*.cvd" >/dev/null || compgen -G "/srv/onebee/clamav/*.cld" >/dev/null \
  || fail "Chưa có chữ ký ClamAV — nộp ngoại tuyến: sudo onebee-box cap-nhat-chu-ky-clamav <thư mục chữ ký>"
pass "Chữ ký ClamAV đã có — dịch vụ kiểm dịch quét được tệp thật"

# Hai nhân viên thường (một lớp): a1 tải tệp, b1 thử đọc tệp của a1
for u in a1 b1; do
  out="$(onebee-box them-nguoi "${u}" nhan_vien)"
  (umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${D}/mk-${u}")
  [ -s "${D}/mk-${u}" ] || fail "them-nguoi ${u} không in mật khẩu tạm"
done
dang_nhap() {
  (umask 077; printf '{"username":"%s","password":"%s","keepMeLoggedIn":false}' "$1" "$(cat "$2")" >"${D}/dn.json")
  c -o /dev/null -w '%{http_code}' -c "$3" -H 'Content-Type: application/json' -d @"${D}/dn.json" \
    "https://${TEN}/dangnhap/api/firstfactor"
  rm -f "${D}/dn.json"
}
for u in a1 b1; do
  ok=""; for _ in $(seq 15); do
    [ "$(dang_nhap "${u}" "${D}/mk-${u}" "${D}/jar-${u}")" = 200 ] && { ok=1; break; }; sleep 2
  done   # Authelia đọc lại tệp người dùng ngay ở yêu cầu kế tiếp
  [ -n "${ok}" ] || fail "${u} không đăng nhập được"
done
pass "Tạo hai tài khoản nhân viên a1, b1 và đăng nhập được (một lớp)"

echo "===== KHO TỆP: PHIÊN VÀ KIỂM DỊCH ====="
[ "$(ma -H 'Accept: application/json' "https://${TEN}/files/khong-co")" = 401 ] \
  || fail "/files/ không phiên không trả 401"
[ "$(ma -H 'Accept: application/json' -H 'Remote-User: a1' -H 'Remote-Groups: nhan_vien' "https://${TEN}/files/1")" = 401 ] \
  || fail "Tự gửi Remote-User mà không phiên vẫn qua được"
pass "Không phiên: /files/ 401 (kể cả tự gửi Remote-User) — forward_auth chặn trước khi tới dịch vụ"

# PDF sạch: tải lên, metadata CLEAN ghi qua cầu nối bằng JWT của a1, tải lại đúng SHA-256
cat >"${D}/bao-cao.pdf" <<'PDF'
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
sha="$(sha256sum <"${D}/bao-cao.pdf" | cut -d' ' -f1)"
ma_up="$(c -b "${D}/jar-a1" -o "${D}/up.json" -w '%{http_code}' -X PUT -H 'Content-Type: application/pdf' \
  --data-binary @"${D}/bao-cao.pdf" "https://${TEN}/files/bao-cao.pdf")"
[ "${ma_up}" = 201 ] || fail "PDF sạch không nhận 201 (mã ${ma_up}): $(head -c 300 "${D}/up.json")"
id="$(python3 - "${D}/up.json" "${sha}" <<'PY'
import json, sys
tep = json.load(open(sys.argv[1], encoding="utf-8"))["tep"]
assert tep["trang_thai_quet"] == "CLEAN", tep
assert tep["sha256"] == sys.argv[2], tep
print(tep["id"])
PY
)" || fail "Metadata tệp sạch không đúng: $(head -c 300 "${D}/up.json")"
dong="$(psql_box "SELECT trang_thai_quet || ' ' || nguoi_tao FROM onebee.tep_dinh_kem WHERE id = ${id}")"
[ "${dong}" = "CLEAN a1" ] || fail "Dòng tep_dinh_kem sai (mong 'CLEAN a1', thấy '${dong}')"
ma_tai="$(c -b "${D}/jar-a1" -o "${D}/tai.pdf" -w '%{http_code}' "https://${TEN}/files/${id}")"
[ "${ma_tai}" = 200 ] || fail "Tải lại tệp sạch không nhận 200 (mã ${ma_tai})"
[ "$(sha256sum <"${D}/tai.pdf" | cut -d' ' -f1)" = "${sha}" ] || fail "Tệp tải lại khác SHA-256 bản gốc"
pass "PDF sạch: tải lên 201, metadata CLEAN (người tạo a1 lấy từ JWT, ghi qua cầu nối), tải lại đúng SHA-256"

# EICAR: phải bị chặn, metadata INFECTED, không tải xuống được
printf '%s' 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' >"${D}/eicar.txt"
ma_virus="$(c -b "${D}/jar-a1" -o "${D}/virus.json" -w '%{http_code}' -X PUT -H 'Content-Type: text/plain' \
  --data-binary @"${D}/eicar.txt" "https://${TEN}/files/eicar.txt")"
[ "${ma_virus}" = 422 ] || fail "Tệp EICAR không bị chặn (mã ${ma_virus}): $(head -c 300 "${D}/virus.json")"
id_virus="$(psql_box "SELECT id FROM onebee.tep_dinh_kem WHERE ten_tep = 'eicar.txt' ORDER BY id DESC LIMIT 1")"
[ -n "${id_virus}" ] || fail "Tệp nhiễm không có dòng metadata"
[ "$(psql_box "SELECT trang_thai_quet FROM onebee.tep_dinh_kem WHERE id = ${id_virus}")" = INFECTED ] \
  || fail "Tệp nhiễm không được đánh dấu INFECTED"
[ "$(ma -b "${D}/jar-a1" "https://${TEN}/files/${id_virus}")" = 422 ] || fail "Vẫn tải xuống được tệp nhiễm"
pass "EICAR: bị chặn 422, metadata INFECTED, tải xuống bị chặn 422"

# Đuôi ngoài danh mục và quá giới hạn dung lượng: không có dòng metadata
printf 'MZ' >"${D}/ma.exe"
[ "$(c -b "${D}/jar-a1" -o /dev/null -w '%{http_code}' -X PUT --data-binary @"${D}/ma.exe" \
  "https://${TEN}/files/ma.exe")" = 415 ] || fail "Đuôi .exe không bị từ chối 415"
[ "$(psql_box "SELECT count(*) FROM onebee.tep_dinh_kem WHERE ten_tep = 'ma.exe'")" = 0 ] \
  || fail "Tệp sai định dạng vẫn ghi metadata"
pass "Đuôi ngoài danh mục (.exe): 415, không ghi metadata"

head -c 11534336 /dev/zero >"${D}/qua-lon.txt"   # 11 MiB
[ "$(c -b "${D}/jar-a1" -o /dev/null -w '%{http_code}' -X PUT --data-binary @"${D}/qua-lon.txt" \
  "https://${TEN}/files/qua-lon.txt")" = 413 ] || fail "Tệp 11 MB không bị từ chối 413"
[ "$(psql_box "SELECT count(*) FROM onebee.tep_dinh_kem WHERE ten_tep = 'qua-lon.txt'")" = 0 ] \
  || fail "Tệp quá lớn vẫn ghi metadata"
pass "Tệp 11 MB: 413, không ghi metadata"

# Nhân viên b1 không đọc được metadata lẫn tệp của a1: dịch vụ trả 404, RLS qua cổng API trả danh sách rỗng
ds_b="$(c -b "${D}/jar-b1" "https://${TEN}/files/")"
python3 -c 'import json, sys
ds = json.load(sys.stdin)["tep"]
assert all(tep["id"] != int(sys.argv[1]) for tep in ds), ds' "${id}" <<<"${ds_b}" || fail "b1 thấy tệp của a1 trong danh sách: ${ds_b:0:300}"
[ "$(ma -b "${D}/jar-b1" "https://${TEN}/files/${id}")" = 404 ] || fail "b1 tải được tệp của a1"
[ "$(c -b "${D}/jar-b1" "https://${TEN}/api/tep_dinh_kem?id=eq.${id}&select=id")" = "[]" ] \
  || fail "RLS: b1 đọc được metadata tệp của a1 qua cổng API"
[ "$(c -b "${D}/jar-a1" "https://${TEN}/api/tep_dinh_kem?id=eq.${id}&select=id")" = "[{\"id\":${id}}]" ] \
  || fail "RLS: a1 không đọc được metadata tệp của chính mình"
pass "Nhân viên b1 không đọc được metadata lẫn tệp của a1 (dịch vụ 404; RLS qua cổng API trả rỗng)"

echo "TẤT CẢ BƯỚC KIỂM THỬ KHO TỆP ĐẠT"
