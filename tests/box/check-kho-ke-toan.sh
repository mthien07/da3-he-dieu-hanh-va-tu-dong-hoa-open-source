#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm kho và kế toán trên Box thật: thủ kho tạo mặt hàng và nhập kho qua API (hàm them_nhap_kho), nhân viên gửi đơn,
# quản lý duyệt → CSDL tự sinh phiếu xuất kho và bút toán doanh thu + giá vốn cân Nợ = Có; duyệt đơn vượt tồn bị chặn
# kèm lời báo tiếng Việt; quyền đọc/ghi của bốn vai trò đúng thiết kế.
# Cách dùng: tests/box/check-kho-ke-toan.sh <container-Box>   (repo đã chép vào /root/onebee-test trong Box)
#             sudo tests/box/check-kho-ke-toan.sh local       (chạy thẳng trên Box thật, không cần container lồng)
set -euo pipefail
BOX="$1"
box() {
  if [[ "${BOX}" == local ]]; then bash -euo pipefail -c "$(cat)"; else docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; fi
}

# ---------------------------------------------------------------------------------------------------
# Tài khoản kiểm, helper đăng nhập và dọn dẹp (chạy dù đạt hay lỗi)
# ---------------------------------------------------------------------------------------------------
echo "===== KHO KẾ TOÁN: CHUẨN BỊ TÀI KHOẢN ====="
box <<'EOF'
install -d -m 0700 /root/kkt
cat >/root/kkt/don.sh <<'DON'
#!/usr/bin/env bash
rm -rf /root/kkt
for u in kkt-nv kkt-thu-kho kkt-ke-toan kkt-ql; do onebee-box xoa-nguoi "$u" >/dev/null 2>&1 || true; done
docker exec -i onebee-postgres psql -X -q -U postgres -d onebee >/dev/null 2>&1 <<'SQL' || true
DELETE FROM onebee.but_toan_dong WHERE but_toan_id IN (
  SELECT id FROM onebee.but_toan
   WHERE chung_tu IN (SELECT 'don_hang:' || id FROM onebee.don_hang WHERE nguoi_tao LIKE 'kkt-%')
      OR chung_tu IN (SELECT 'phieu_kho:' || id FROM onebee.phieu_kho WHERE nguoi_tao LIKE 'kkt-%'));
DELETE FROM onebee.but_toan
 WHERE chung_tu IN (SELECT 'don_hang:' || id FROM onebee.don_hang WHERE nguoi_tao LIKE 'kkt-%')
    OR chung_tu IN (SELECT 'phieu_kho:' || id FROM onebee.phieu_kho WHERE nguoi_tao LIKE 'kkt-%');
DELETE FROM onebee.phieu_kho_dong WHERE phieu_id IN (
  SELECT id FROM onebee.phieu_kho
   WHERE nguoi_tao LIKE 'kkt-%' OR don_hang_id IN (SELECT id FROM onebee.don_hang WHERE nguoi_tao LIKE 'kkt-%'));
DELETE FROM onebee.phieu_kho
 WHERE nguoi_tao LIKE 'kkt-%' OR don_hang_id IN (SELECT id FROM onebee.don_hang WHERE nguoi_tao LIKE 'kkt-%');
DELETE FROM onebee.don_hang WHERE nguoi_tao LIKE 'kkt-%';
DELETE FROM onebee.mat_hang WHERE ma LIKE 'KKT-%';
SQL
DON
chmod +x /root/kkt/don.sh

cat >/root/kkt/chung.sh <<'CHUNG'
IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
TEN="box.$(sed -n 's/^onebee_box_ma_don_vi: *//p' /root/onebee-test/box/ansible/group_vars/all.yml | tr -d '"')".onebee.internal
CA=/etc/onebee-box/secrets/ca/root.crt
D=/root/kkt
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
# Người thuộc nhóm hai lớp: xin mã xác minh, ghi danh TOTP, chờ sang khung 30 giây rồi qua lớp hai
hai_lop() {
  local u="$1" jar="${D}/jar-$1" code=""
  # Authelia giới hạn số lần xin nâng phiên (bucket 1): chạy lại bài kiểm nhiều lần liền có thể bị 429 — chờ rồi thử lại
  for _ in $(seq 6); do
    code="$(ma -b "${jar}" -c "${jar}" -X POST "https://${TEN}/dangnhap/api/user/session/elevation")"
    [ "${code}" = 200 ] && break
    sleep 30
  done
  [ "${code}" = 200 ] || { echo "${code}"; return 0; }
  sleep 1
  (umask 077; printf '{"otc":"%s"}' "$(onebee-box ma-xac-nhan | sed -n 's/^Mã xác minh: //p')" >"${D}/otc.json")
  ma -b "${jar}" -c "${jar}" -X PUT -H 'Content-Type: application/json' -d @"${D}/otc.json" \
    "https://${TEN}/dangnhap/api/user/session/elevation" >/dev/null
  c -b "${jar}" -c "${jar}" -X PUT -H 'Content-Type: application/json' -d '{"algorithm":"SHA1","length":6,"period":30}' \
    "https://${TEN}/dangnhap/api/secondfactor/totp/register" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["base32_secret"])' >"${D}/totp-$u"
  (umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-$u")" >"${D}/totp.json")
  ma -b "${jar}" -c "${jar}" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" \
    "https://${TEN}/dangnhap/api/secondfactor/totp/register" >/dev/null
  sleep $(( 31 - $(date +%s) % 30 ))
  (umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-$u")" >"${D}/totp.json")
  ma -b "${jar}" -c "${jar}" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" \
    "https://${TEN}/dangnhap/api/secondfactor/totp"
}
CHUNG

. /root/kkt/chung.sh
for u in kkt-nv kkt-thu-kho kkt-ke-toan kkt-ql; do onebee-box xoa-nguoi "${u}" >/dev/null 2>&1 || true; done
for u in "kkt-nv nhan_vien" "kkt-thu-kho thu_kho" "kkt-ke-toan ke_toan" "kkt-ql quan_ly"; do
  set -- ${u}
  out="$(onebee-box them-nguoi "$1" "$2")" || { echo "FAIL  them-nguoi $1 $2"; exit 1; }
  (umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${D}/mk-$1")
  [ -s "${D}/mk-$1" ] || { echo "FAIL  them-nguoi $1 không in mật khẩu tạm"; exit 1; }
done
[ "$(dang_nhap kkt-nv "${D}/mk-kkt-nv" "${D}/jar-kkt-nv")" = 200 ] || { echo 'FAIL  kkt-nv không đăng nhập được'; exit 1; }
for u in kkt-thu-kho kkt-ke-toan kkt-ql; do
  for _ in $(seq 15); do [ "$(dang_nhap "$u" "${D}/mk-$u" "${D}/jar-$u")" = 200 ] && break; sleep 2; done
  [ "$(hai_lop "$u")" = 200 ] || { echo "FAIL  ${u} không qua được lớp hai"; exit 1; }
done
[ "$(c -b "${D}/jar-kkt-thu-kho" "https://${TEN}/api/toi")" = '{"ten": "kkt-thu-kho", "vai_tro": "thu_kho"}' ] \
  || { echo 'FAIL  /api/toi của kkt-thu-kho sai'; exit 1; }
[ "$(c -b "${D}/jar-kkt-ke-toan" "https://${TEN}/api/toi")" = '{"ten": "kkt-ke-toan", "vai_tro": "ke_toan"}' ] \
  || { echo 'FAIL  /api/toi của kkt-ke-toan sai'; exit 1; }
echo 'PASS  Bốn tài khoản kiểm (nhân viên, thủ kho, kế toán, quản lý) đăng nhập đúng vai trò'
EOF
don_dep() {
  if [[ "${BOX}" == local ]]; then bash /root/kkt/don.sh >/dev/null 2>&1 || true
  else docker exec "${BOX}" bash /root/kkt/don.sh >/dev/null 2>&1 || true; fi
}
trap don_dep EXIT

# ---------------------------------------------------------------------------------------------------
# Thủ kho: tạo mặt hàng + nhập 100 kg qua API
# ---------------------------------------------------------------------------------------------------
echo "===== KHO KẾ TOÁN: TẠO MẶT HÀNG VÀ NHẬP KHO ====="
box <<'EOF'
. /root/kkt/chung.sh
code="$(c -b "${D}/jar-kkt-thu-kho" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
        -d '{"ma":"KKT-MATONG","ten":"Mật ong kiểm thử","don_vi":"kg","gia_ban":100000}' "https://${TEN}/api/mat_hang")"
[ "${code}" = 201 ] || { echo "FAIL  thủ kho tạo mặt hàng không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
id_mh="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"])' "${D}/tl")"
echo "${id_mh}" >"${D}/id-mat-hang"
code="$(c -b "${D}/jar-kkt-thu-kho" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d "{\"p_ngay\":null,\"p_dien_gia\":\"Nhập kiểm thử\",\"p_dong\":[{\"mat_hang_id\":${id_mh},\"so_luong\":100,\"don_gia\":70000}]}" \
        "https://${TEN}/api/rpc/them_nhap_kho")"
[ "${code}" = 200 ] || { echo "FAIL  nhập kho không nhận 200 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
grep -q 'PN-' "${D}/tl" || { echo "FAIL  phản hồi nhập kho thiếu số phiếu: $(cat "${D}/tl")"; exit 1; }
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"])' "${D}/tl" >"${D}/id-phieu"
echo 'PASS  Thủ kho tạo thẻ kho và ghi phiếu nhập 100 kg qua API'
EOF

# ---------------------------------------------------------------------------------------------------
# Tồn kho, bút toán nhập kho, quyền đọc sổ
# ---------------------------------------------------------------------------------------------------
echo "===== KHO KẾ TOÁN: TỒN KHO VÀ BÚT TOÁN NHẬP ====="
box <<'EOF'
. /root/kkt/chung.sh
id_mh="$(cat "${D}/id-mat-hang")"
ton="$(c -b "${D}/jar-kkt-thu-kho" "https://${TEN}/api/ton_kho?mat_hang_id=eq.${id_mh}&select=ton,gia_von")"
python3 - "${ton}" <<'PY' || { echo "FAIL  tồn kho sau nhập sai: ${ton}"; exit 1; }
import json, sys
x = json.loads(sys.argv[1])[0]
assert float(x["ton"]) == 100 and float(x["gia_von"]) == 70000, x
PY
id_phieu="$(cat "${D}/id-phieu")"
so="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c \
  "SELECT tai_khoan || ' ' || no || ' ' || co FROM onebee.but_toan_dong d JOIN onebee.but_toan b ON b.id = d.but_toan_id WHERE b.chung_tu = 'phieu_kho:${id_phieu}' ORDER BY d.id")"
[ "${so}" = $'156 7000000.00 0.00\n111 0.00 7000000.00' ] || { echo "FAIL  bút toán nhập kho sai: ${so}"; exit 1; }
# Kế toán vẫn đọc được sổ qua API (kiểm quyền, không kiểm toàn bộ nội dung)
[ "$(ma -b "${D}/jar-kkt-ke-toan" "https://${TEN}/api/so_nhat_ky?select=so_hieu&limit=1")" = 200 ] \
  || { echo 'FAIL  kế toán không đọc được sổ qua API'; exit 1; }
[ "$(ma -b "${D}/jar-kkt-nv" "https://${TEN}/api/so_nhat_ky?select=so_hieu")" = 403 ] || { echo 'FAIL  nhân viên đọc được sổ kế toán'; exit 1; }
[ "$(ma -b "${D}/jar-kkt-thu-kho" "https://${TEN}/api/so_nhat_ky?select=so_hieu")" = 403 ] || { echo 'FAIL  thủ kho đọc được sổ kế toán'; exit 1; }
[ "$(ma -b "${D}/jar-kkt-ke-toan" -X PATCH -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
      -d '{"trang_thai_duyet":"DA_DUYET"}' "https://${TEN}/api/don_hang?id=eq.0")" = 403 ] || { echo 'FAIL  kế toán sửa được đơn hàng'; exit 1; }
echo 'PASS  Tồn 100 kg, bút toán Nợ 156 / Có 111 = 7.000.000; nhân viên và thủ kho không đọc được sổ, kế toán không duyệt đơn'
EOF

# ---------------------------------------------------------------------------------------------------
# Bán hàng: nhân viên gửi đơn, quản lý duyệt → phiếu xuất + bút toán
# ---------------------------------------------------------------------------------------------------
echo "===== KHO KẾ TOÁN: DUYỆT ĐƠN SINH PHIẾU XUẤT VÀ BÚT TOÁN ====="
box <<'EOF'
. /root/kkt/chung.sh
id_mh="$(cat "${D}/id-mat-hang")"
(umask 077; printf '{"khach_hang":"HTX Kiểm Thử","mat_hang":"Mật ong kiểm thử","mat_hang_id":%s,"so_luong_kg":30,"don_gia":100000,"thanh_tien":3000000}' "${id_mh}" >"${D}/don.json")
code="$(c -b "${D}/jar-kkt-nv" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
        -d @"${D}/don.json" "https://${TEN}/api/don_hang")"
[ "${code}" = 201 ] || { echo "FAIL  nhân viên gửi đơn không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
id_don="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"])' "${D}/tl")"
(umask 077; printf '{"id":%s,"trang_thai_duyet":"DA_DUYET","ly_do_duyet":""}' "${id_don}" >"${D}/duyet.json")
code="$(c -b "${D}/jar-kkt-ql" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/duyet.json" "https://${TEN}/quy-trinh/webhook/onebee-phe-duyet")"
[ "${code}" = 200 ] || { echo "FAIL  quản lý duyệt đơn không nhận 200 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
ton="$(c -b "${D}/jar-kkt-thu-kho" "https://${TEN}/api/ton_kho?mat_hang_id=eq.${id_mh}&select=ton")"
python3 - "${ton}" <<'PY' || { echo "FAIL  tồn sau duyệt sai: ${ton}"; exit 1; }
import json, sys
assert float(json.loads(sys.argv[1])[0]["ton"]) == 70, sys.argv[1]
PY
phieu="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c \
  "SELECT loai || ':' || so_luong FROM onebee.phieu_kho p JOIN onebee.phieu_kho_dong d ON d.phieu_id = p.id WHERE p.don_hang_id = ${id_don}")"
[ "${phieu}" = 'XUAT:30' ] || { echo "FAIL  phiếu xuất của đơn sai: ${phieu}"; exit 1; }
so="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c \
  "SELECT tai_khoan || ' ' || no || ' ' || co FROM onebee.but_toan_dong d JOIN onebee.but_toan b ON b.id = d.but_toan_id WHERE b.chung_tu = 'don_hang:${id_don}' ORDER BY d.id")"
[ "${so}" = $'131 3000000.00 0.00\n511 0.00 3000000.00\n632 2100000.00 0.00\n156 0.00 2100000.00' ] \
  || { echo "FAIL  bút toán duyệt đơn sai: ${so}"; exit 1; }
can="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c \
  "SELECT sum(no) = sum(co) FROM onebee.but_toan_dong d JOIN onebee.but_toan b ON b.id = d.but_toan_id WHERE b.chung_tu = 'don_hang:${id_don}'")"
[ "${can}" = t ] || { echo "FAIL  bút toán duyệt đơn không cân"; exit 1; }
echo 'PASS  Duyệt đơn 30 kg: phiếu xuất 30 kg, tồn 70, doanh thu 3.000.000 và giá vốn 2.100.000, mọi bút toán cân'
EOF

# ---------------------------------------------------------------------------------------------------
# Chặn duyệt khi thiếu tồn và chặn dữ liệu kho sai
# ---------------------------------------------------------------------------------------------------
echo "===== KHO KẾ TOÁN: CHẶN KHI THIẾU TỒN VÀ DỮ LIỆU SAI ====="
box <<'EOF'
. /root/kkt/chung.sh
id_mh="$(cat "${D}/id-mat-hang")"
(umask 077; printf '{"khach_hang":"HTX Lớn","mat_hang":"Mật ong kiểm thử","mat_hang_id":%s,"so_luong_kg":500,"don_gia":100000,"thanh_tien":50000000}' "${id_mh}" >"${D}/don-lon.json")
code="$(c -b "${D}/jar-kkt-nv" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
        -d @"${D}/don-lon.json" "https://${TEN}/api/don_hang")"
[ "${code}" = 201 ] || { echo "FAIL  gửi đơn 500 kg không nhận 201 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
id_lon="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d[0] if isinstance(d,list) else d; print(d["id"])' "${D}/tl")"
(umask 077; printf '{"id":%s,"trang_thai_duyet":"DA_DUYET","ly_do_duyet":""}' "${id_lon}" >"${D}/duyet-lon.json")
code="$(c -b "${D}/jar-kkt-ql" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d @"${D}/duyet-lon.json" "https://${TEN}/quy-trinh/webhook/onebee-phe-duyet")"
[ "${code}" = 400 ] || { echo "FAIL  duyệt đơn vượt tồn không bị chặn (mã ${code}): $(cat "${D}/tl")"; exit 1; }
grep -q 'Không đủ tồn kho' "${D}/tl" || { echo "FAIL  lời báo thiếu tồn không rõ: $(cat "${D}/tl")"; exit 1; }
tt="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c "SELECT trang_thai_duyet FROM onebee.don_hang WHERE id = ${id_lon}")"
[ "${tt}" = 'CHO_DUYET' ] || { echo "FAIL  đơn vượt tồn đã đổi trạng thái: ${tt}"; exit 1; }
code="$(c -b "${D}/jar-kkt-thu-kho" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d "{\"p_ngay\":null,\"p_dien_gia\":\"Số âm\",\"p_dong\":[{\"mat_hang_id\":${id_mh},\"so_luong\":-5,\"don_gia\":1000}]}" \
        "https://${TEN}/api/rpc/them_nhap_kho")"
[ "${code}" = 400 ] && grep -q 'Số lượng nhập' "${D}/tl" || { echo "FAIL  nhập số lượng âm không bị 400 (mã ${code}): $(cat "${D}/tl")"; exit 1; }
code="$(c -b "${D}/jar-kkt-nv" -o "${D}/tl" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d "{\"p_ngay\":null,\"p_dien_gia\":\"Nhân viên\",\"p_dong\":[{\"mat_hang_id\":${id_mh},\"so_luong\":5,\"don_gia\":1000}]}" \
        "https://${TEN}/api/rpc/them_nhap_kho")"
[ "${code}" = 403 ] || { echo "FAIL  nhân viên gọi được hàm nhập kho (mã ${code}): $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Duyệt đơn vượt tồn bị chặn (đơn vẫn CHO_DUYET), nhập số âm bị 400, nhân viên không gọi được hàm nhập kho'
EOF
