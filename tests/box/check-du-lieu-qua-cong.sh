#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm phân quyền tới cấp dòng TỪ ĐẦU ĐẾN CUỐI qua cổng API trên Box đã BẬT HTTPS: trình duyệt/ứng dụng → Caddy → Authelia (phiên)
# → cầu nối danh tính (JWT 60 giây) → PostgREST → RLS trong PostgreSQL. check-https.sh gọi bài này ngay sau check-sso-cong-api.sh
# (bài đó để lại tài khoản an, binh, kt và /root/sso; bài này tạo thêm chi, ghi danh hai lớp cho binh, rồi dọn /root/sso).
# Cách dùng: check-du-lieu-qua-cong.sh <container-Box>
set -euo pipefail
BOX="$1"
# Đọc lệnh từ heredoc rồi chạy bằng -c (như check-sso-cong-api.sh)
box() { docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; }

echo "===== DỮ LIỆU QUA CỔNG API: PHIÊN ====="
box <<'EOF'
. /root/sso/chung.sh
[ -s "${D}/mk-an" ] && [ -s "${D}/mk-binh" ] || { echo 'FAIL  Thiếu tài khoản an/binh của check-sso-cong-api.sh'; exit 1; }
out="$(onebee-box them-nguoi chi nhan_vien)" || { echo 'FAIL  them-nguoi chi nhan_vien'; exit 1; }
(umask 077; sed -n 's/^Mật khẩu tạm[^:]*: //p' <<<"${out}" >"${D}/mk-chi")
for u in an chi; do
  ok=""; for _ in $(seq 15); do [ "$(dang_nhap "${u}" "${D}/mk-${u}" "${D}/jar-${u}")" = 200 ] && { ok=1; break; }; sleep 2; done
  [ -n "${ok}" ] || { echo "FAIL  ${u} không đăng nhập được"; exit 1; }
done
# binh (quan_ly) phải qua hai lớp: ghi danh TOTP bằng mã xác minh từ onebee-box ma-xac-nhan (như kt trong check-sso-cong-api.sh)
[ "$(dang_nhap binh "${D}/mk-binh" "${D}/jar-binh")" = 200 ] || { echo 'FAIL  binh không đăng nhập được'; exit 1; }
[ "$(ma -b "${D}/jar-binh" -c "${D}/jar-binh" -X POST "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] || { echo 'FAIL  binh không xin được mã xác minh'; exit 1; }
sleep 1
(umask 077; printf '{"otc":"%s"}' "$(onebee-box ma-xac-nhan | sed -n 's/^Mã xác minh: //p')" >"${D}/otc.json")
[ "$(ma -b "${D}/jar-binh" -c "${D}/jar-binh" -X PUT -H 'Content-Type: application/json' -d @"${D}/otc.json" "https://${TEN}/dangnhap/api/user/session/elevation")" = 200 ] \
  || { echo 'FAIL  Mã xác minh của binh không được nhận'; exit 1; }
c -b "${D}/jar-binh" -c "${D}/jar-binh" -X PUT -H 'Content-Type: application/json' -d '{"algorithm":"SHA1","length":6,"period":30}' \
  "https://${TEN}/dangnhap/api/secondfactor/totp/register" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["base32_secret"])' \
  >"${D}/totp-binh" || { echo 'FAIL  binh không bắt đầu ghi danh TOTP được'; exit 1; }
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-binh")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-binh" -c "${D}/jar-binh" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" "https://${TEN}/dangnhap/api/secondfactor/totp/register")" = 200 ] \
  || { echo 'FAIL  Ghi danh TOTP của binh không xong'; exit 1; }
sleep $(( 31 - $(date +%s) % 30 ))   # mã đã dùng để ghi danh không dùng lại được → chờ bước thời gian kế
(umask 077; printf '{"token":"%s"}' "$(totp "${D}/totp-binh")" >"${D}/totp.json")
[ "$(ma -b "${D}/jar-binh" -c "${D}/jar-binh" -X POST -H 'Content-Type: application/json' -d @"${D}/totp.json" "https://${TEN}/dangnhap/api/secondfactor/totp")" = 200 ] \
  || { echo 'FAIL  Lớp hai (TOTP) của binh không qua'; exit 1; }
[ "$(c -b "${D}/jar-binh" "https://${TEN}/api/toi")" = '{"ten": "binh", "vai_tro": "quan_ly"}' ] || { echo 'FAIL  /api/toi của binh sai'; exit 1; }
EOF

echo "===== DỮ LIỆU QUA CỔNG API: PHÂN QUYỀN DÒNG ====="
box <<'EOF'
. /root/sso/chung.sh
J='Content-Type: application/json'
P='Prefer: return=representation'
# api <cookie|-> <phương thức> <đường dẫn> [thân JSON] → thân trả về vào ${D}/tl, in mã HTTP
api() {
  local jar=() than=()
  [ "$1" = - ] || jar=(-b "${D}/jar-$1")
  [ -z "${4:-}" ] || than=(-H "${J}" -H "${P}" -d "$4")
  c "${jar[@]}" -o "${D}/tl" -w '%{http_code}' -X "$2" -H 'Accept: application/json' "${than[@]}" "https://${TEN}/api/$3"
}
truong() { python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); d = d[0] if isinstance(d, list) else d; print(d[sys.argv[2]])' "${D}/tl" "$1"; }

[ "$(api - GET don_hang)" = 401 ] || { echo 'FAIL  /api/don_hang không phiên không nhận 401'; exit 1; }
echo 'PASS  /api/don_hang không phiên: 401'

DON='{"khach_hang":"Khách thử qua cổng","mat_hang":"Mật ong thử","so_luong_kg":3,"don_gia":100000,"thanh_tien":300000,"ngay_giao":"2026-12-01"}'
[ "$(api an POST don_hang "${DON}")" = 201 ] || { echo "FAIL  an gửi đơn hợp lệ không nhận 201: $(cat "${D}/tl")"; exit 1; }
id_an="$(truong id)"
[ "$(truong nguoi_tao) $(truong trang_thai_duyet)" = "an CHO_DUYET" ] || { echo "FAIL  Đơn của an sai người tạo/trạng thái: $(cat "${D}/tl")"; exit 1; }
echo "PASS  Phiên an (nhan_vien) gửi đơn hợp lệ: 201, người tạo an (từ JWT), chờ duyệt (đơn ${id_an})"

[ "$(api chi GET "don_hang?select=id,nguoi_tao")" = 200 ] || { echo "FAIL  chi đọc /api/don_hang lỗi: $(cat "${D}/tl")"; exit 1; }
python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); sys.exit(any(x["id"] == int(sys.argv[2]) or x["nguoi_tao"] != "chi" for x in d))' "${D}/tl" "${id_an}" \
  || { echo "FAIL  chi thấy đơn không phải của mình: $(cat "${D}/tl")"; exit 1; }
[ "$(api chi PATCH "don_hang?id=eq.${id_an}" '{"trang_thai_duyet":"DA_DUYET"}')" != 200 ] || { echo 'FAIL  chi (nhan_vien) duyệt được đơn'; exit 1; }
echo 'PASS  Phiên chi (nhan_vien khác) gọi /api/don_hang: 200, không thấy đơn của an; không duyệt được đơn'

DON_AM='{"khach_hang":"Khách thử qua cổng","mat_hang":"Mật ong thử","so_luong_kg":-3,"don_gia":100000,"thanh_tien":0,"ngay_giao":"2026-12-01"}'
[ "$(api an POST don_hang "${DON_AM}")" = 400 ] || { echo "FAIL  Đơn số lượng âm không nhận 400: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Phiên an gửi đơn có số lượng âm: 400 (ràng buộc trong CSDL)'

[ "$(api binh GET "don_hang?id=eq.${id_an}&select=id,nguoi_tao")" = 200 ] && [ "$(truong nguoi_tao)" = an ] \
  || { echo "FAIL  binh (quan_ly) không thấy đơn của an: $(cat "${D}/tl")"; exit 1; }
[ "$(api binh PATCH "don_hang?id=eq.${id_an}" '{"trang_thai_duyet":"DA_DUYET","ly_do_duyet":"Đủ hàng"}')" = 200 ] \
  || { echo "FAIL  binh duyệt đơn của an lỗi: $(cat "${D}/tl")"; exit 1; }
[ "$(truong trang_thai_duyet) $(truong nguoi_duyet)" = "DA_DUYET binh" ] && [ "$(truong thoi_gian_duyet)" != None ] \
  || { echo "FAIL  Sau duyệt: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  Phiên binh (quan_ly, hai lớp) thấy đơn của an và duyệt được: DA_DUYET, nguoi_duyet binh, có giờ duyệt'

[ "$(api binh POST don_hang "${DON}")" = 201 ] || { echo "FAIL  binh tạo đơn lỗi: $(cat "${D}/tl")"; exit 1; }
id_binh="$(truong id)"
ma_tu_duyet="$(api binh PATCH "don_hang?id=eq.${id_binh}" '{"trang_thai_duyet":"DA_DUYET"}')"
[ "${ma_tu_duyet}" = 400 ] && grep -q khong_tu_duyet "${D}/tl" || { echo "FAIL  binh tự duyệt đơn của mình không bị từ chối (${ma_tu_duyet}): $(cat "${D}/tl")"; exit 1; }
[ "$(api binh GET "don_hang?id=eq.${id_binh}&select=trang_thai_duyet")" = 200 ] && [ "$(truong trang_thai_duyet)" = CHO_DUYET ] \
  || { echo "FAIL  Đơn binh tự duyệt đã đổi trạng thái: $(cat "${D}/tl")"; exit 1; }
echo 'PASS  binh tự tạo một đơn rồi tự duyệt: bị từ chối (400, ràng buộc khong_tu_duyet: nguoi_duyet <> nguoi_tao), đơn vẫn chờ duyệt'
EOF

echo "===== DỮ LIỆU QUA CỔNG API: CHUYỂN SỔ CŨ, CỔNG ====="
box <<'EOF'
onebee-box chuyen-du-lieu >/root/chuyen-1.log 2>&1 || { cat /root/chuyen-1.log; echo 'FAIL  onebee-box chuyen-du-lieu lần 1'; exit 1; }
onebee-box chuyen-du-lieu >/root/chuyen-2.log 2>&1 || { cat /root/chuyen-2.log; echo 'FAIL  onebee-box chuyen-du-lieu lần 2'; exit 1; }
[ "$(awk 'NR > 1 && NF == 4' /root/chuyen-2.log | wc -l)" = 5 ] && [ "$(awk 'NR > 1 && NF == 4 {s += $3} END {print s + 0}' /root/chuyen-2.log)" = 0 ] \
  || { cat /root/chuyen-2.log; echo 'FAIL  chuyen-du-lieu lần hai vẫn nạp dòng mới'; exit 1; }
echo "PASS  onebee-box chuyen-du-lieu chạy hai lần: lần hai 0 dòng mới nạp ở cả 5 bảng ($(awk 'NR > 1 && NF == 4 {printf "%s=%s ", $1, $4}' /root/chuyen-2.log))"
for ct in onebee-postgres onebee-postgrest; do
  [ "$(docker inspect -f '{{.State.Running}}' "${ct}")" = true ] || { echo "FAIL  ${ct} không chạy"; exit 1; }
  [ -z "$(docker port "${ct}")" ] || { echo "FAIL  ${ct} công bố cổng: $(docker port "${ct}")"; exit 1; }
done
echo 'PASS  docker port onebee-postgres và onebee-postgrest rỗng (không công bố cổng nào)'
rm -rf /root/sso
EOF
