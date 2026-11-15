#!/usr/bin/env bash
# shellcheck disable=SC2015,SC2016,SC2317,SC2329  # pass luôn thành công (A && pass || fail đúng nghĩa); lệnh docker giả viết trong nháy đơn; don chạy qua trap
# Kiểm lược đồ và phân quyền tới cấp dòng (RLS) của OneBee Box trên PostgreSQL THẬT: dựng một container từ đúng image đã ghim
# trong group_vars/all.yml (không mạng, không công bố cổng), áp dụng lược đồ bằng chính công cụ của bộ cài (onebee-luoc-do.sh),
# rồi đóng vai từng người dùng như dịch vụ dữ liệu làm (SET ROLE + set_config('request.jwt.claims', ...)).
# Nạp bộ sổ cũ mẫu bằng onebee-chuyen-du-lieu.py (docker exec … onebee-postgres được chuyển sang container của bài này).
# Container riêng của bài (tên có hậu tố PID) luôn bị xóa khi xong, kể cả khi lỗi. Cần: Docker, python3.
# Cách dùng: tests/box/check-csdl-rls.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
ROLE="${ROOT}/box/ansible/roles/box-du-lieu/files"
IMG="$(sed -n 's/^  postgres: *//p' "${ROOT}/box/ansible/group_vars/all.yml")"
[[ "${IMG}" == *@sha256:* ]] || { echo "FAIL  Không thấy image PostgreSQL ghim digest trong group_vars/all.yml"; exit 1; }
CT="onebee-kiem-csdl-$$"
T="$(mktemp -d)"
DOCKER="$(command -v docker)"
don() { "${DOCKER}" rm -f "${CT}" >/dev/null 2>&1 || true; rm -rf "${T}"; }
trap don EXIT
loi=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; loi=$((loi + 1)); }

"${DOCKER}" run -d --name "${CT}" --network none -e POSTGRES_DB=onebee \
  -e POSTGRES_PASSWORD="$(head -c 512 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 24)" "${IMG}" >/dev/null
# Máy chủ tạm lúc khởi tạo chỉ nghe socket: chờ tới khi nghe TCP (máy chủ thật)
for _ in $(seq 90); do "${DOCKER}" exec "${CT}" pg_isready -q -h 127.0.0.1 -U postgres -d onebee && break; sleep 1; done
"${DOCKER}" exec "${CT}" pg_isready -q -h 127.0.0.1 -U postgres -d onebee || { echo "FAIL  PostgreSQL không sẵn sàng"; "${DOCKER}" logs --tail 20 "${CT}"; exit 1; }

# Lệnh docker cho hai công cụ của Box: tên container onebee-postgres → container của bài này
mkdir -p "${T}/bin"
printf '#!/usr/bin/env bash\na=()\nfor x in "$@"; do [[ "${x}" == onebee-postgres ]] && x=%q; a+=("${x}"); done\nexec %q "${a[@]}"\n' "${CT}" "${DOCKER}" >"${T}/bin/docker"
chmod +x "${T}/bin/docker"
export PATH="${T}/bin:${PATH}"

# sql <vai trò> <tên đăng nhập> — chạy SQL (stdin) như một yêu cầu qua API của người đó; in kết quả (-At), lỗi ra stderr
sql() {
  { printf "SET ROLE %s;\nSELECT set_config('request.jwt.claims', '{\"sub\":\"%s\",\"role\":\"%s\"}', false) \\g /dev/null\n" "$1" "$2" "$1"; cat; } \
    | "${DOCKER}" exec -i "${CT}" psql -X -q -At -U postgres -d onebee -v ON_ERROR_STOP=1 2>&1
}
chu() { "${DOCKER}" exec -i "${CT}" psql -X -q -At -U postgres -d onebee -v ON_ERROR_STOP=1 "$@"; }

# ===== Áp dụng lược đồ có ghi sổ =====
mkdir -p "${T}/luoc-do"
cp "${ROLE}"/luoc-do/*.sql "${T}/luoc-do/"
out="$("${ROLE}/onebee-luoc-do.sh" "${T}/luoc-do" "${T}/ket-xuat" 2>&1)" || { echo "FAIL  Áp dụng lược đồ lỗi:"; echo "${out}"; exit 1; }
so_tep="$(find "${T}/luoc-do" -name '*.sql' | wc -l | tr -d ' ')"
if [[ "$(grep -c '^đã áp dụng ' <<<"${out}")" == "${so_tep}" && "$(chu -c 'SELECT count(*) FROM onebee.lich_su_luoc_do')" == "${so_tep}" \
      && ! -e "${T}/ket-xuat" ]]; then pass "Lược đồ: áp dụng ${so_tep} tệp, ghi đủ vào sổ (CSDL mới: không kết xuất)"
else fail "Lược đồ lần đầu: ${out}"; fi
out="$("${ROLE}/onebee-luoc-do.sh" "${T}/luoc-do" "${T}/ket-xuat" 2>&1)"
[[ -z "${out}" ]] && pass "Lược đồ: chạy lại không áp dụng gì (bộ cài báo không đổi)" || fail "Lược đồ chạy lại vẫn in: ${out}"

khong_rls="$(chu -c "SELECT string_agg(c.relname, ' ') FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'onebee' AND c.relkind IN ('r', 'p') AND NOT (c.relrowsecurity AND c.relforcerowsecurity)")"
so_bang="$(chu -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'onebee'")"
[[ -z "${khong_rls}" && "${so_bang}" -ge 9 ]] && pass "Mọi bảng (${so_bang}) của lược đồ onebee bật và ép RLS (ENABLE + FORCE)" \
  || fail "Bảng chưa bật/ép RLS: ${khong_rls} (tổng ${so_bang})"

# ===== Phân quyền tới cấp dòng (khẳng định của bài kiểm) =====
id_a="$(sql nhan_vien an <<'SQL'
INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, ngay_giao)
  VALUES ('Khách mẫu A', 'Mật ong mẫu', 2, 100000, 200000, '2026-11-20') RETURNING id;
SQL
)" || true
doc_lai="$(sql nhan_vien an <<<"SELECT nguoi_tao || ' ' || trang_thai_duyet FROM onebee.don_hang WHERE id = ${id_a:-0};")" || true
[[ "${id_a}" =~ ^[0-9]+$ && "${doc_lai}" == "an CHO_DUYET" ]] && pass "(a) nhan_vien an thêm được đơn và đọc lại được (người tạo an, chờ duyệt)" \
  || fail "(a) an thêm/đọc đơn: id='${id_a}' đọc='${doc_lai}'"

kq="$(sql nhan_vien chi <<<"SELECT count(*) FROM onebee.don_hang WHERE id = ${id_a:-0};")" || true
tong="$(sql nhan_vien chi <<<"SELECT count(*) FROM onebee.don_hang;")" || true
[[ "${kq}" == 0 && "${tong}" == 0 ]] && pass "(b) nhan_vien chi không thấy đơn của an" || fail "(b) chi thấy đơn của an: ${kq} / ${tong}"

kq="$(sql nhan_vien an <<<"UPDATE onebee.don_hang SET ghi_chu = 'sửa' WHERE id = ${id_a:-0};")" && rc=0 || rc=$?
kq2="$(sql nhan_vien an <<<"DELETE FROM onebee.don_hang WHERE id = ${id_a:-0};")" && rc2=0 || rc2=$?
[[ ${rc} -ne 0 && "${kq}" == *"permission denied"* && ${rc2} -ne 0 && "$(chu -c "SELECT ghi_chu IS NULL FROM onebee.don_hang WHERE id = ${id_a:-0}")" == t ]] \
  && pass "(c) nhan_vien sửa (và xóa) đơn bị từ chối" || fail "(c) nhan_vien sửa đơn: rc=${rc} ${kq} / xóa rc=${rc2} ${kq2}"

id_b="$(sql quan_ly binh <<<"INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien) VALUES ('Khách mẫu B', 'Sáp ong mẫu', 1, 50000, 50000) RETURNING id;")" || true
kq="$(sql quan_ly binh <<<"UPDATE onebee.don_hang SET trang_thai_duyet = 'DA_DUYET' WHERE id = ${id_b:-0};")" && rc=0 || rc=$?
[[ "${id_b}" =~ ^[0-9]+$ && ${rc} -ne 0 && "${kq}" == *'check constraint "khong_tu_duyet"'* && "$(chu -c "SELECT trang_thai_duyet FROM onebee.don_hang WHERE id = ${id_b:-0}")" == CHO_DUYET ]] \
  && pass "(d) quan_ly binh duyệt đơn của chính mình bị từ chối (ràng buộc nguoi_duyet <> nguoi_tao), đơn vẫn chờ duyệt" \
  || fail "(d) binh tự duyệt: id='${id_b}' rc=${rc} ${kq}"

kq="$(sql quan_ly lan <<SQL
UPDATE onebee.don_hang SET trang_thai_duyet = 'DA_DUYET', ly_do_duyet = 'Đủ hàng' WHERE id = ${id_a:-0}
  RETURNING trang_thai_duyet || ' ' || nguoi_duyet || ' ' || (thoi_gian_duyet IS NOT NULL);
SQL
)" || true
gia_mao="$(sql quan_ly lan <<<"UPDATE onebee.don_hang SET nguoi_duyet = 'ai-do' WHERE id = ${id_a:-0};")" && rc=0 || rc=$?
[[ "${kq}" == "DA_DUYET lan true" && ${rc} -ne 0 && "${gia_mao}" == *"permission denied"* ]] \
  && pass "(e) quan_ly lan duyệt được đơn của an; nguoi_duyet = lan, thoi_gian_duyet tự có; không tự đặt được nguoi_duyet" \
  || fail "(e) lan duyệt: '${kq}' / đặt nguoi_duyet: rc=${rc} ${gia_mao}"

kq="$(sql nhan_vien an <<<"INSERT INTO onebee.yeu_cau_ho_tro (may, loai, muc_do, mo_ta) VALUES ('ketoan-01', 'Gõ tiếng Việt', 'rat-gap', 'mẫu');")" && rc=0 || rc=$?
dung="$(sql nhan_vien an <<<"INSERT INTO onebee.yeu_cau_ho_tro (may, loai, muc_do, mo_ta) VALUES ('ketoan-01', 'Gõ tiếng Việt', 'gap', 'mẫu') RETURNING ma;")" || true
[[ ${rc} -ne 0 && "${kq}" == *'check constraint "muc_do_trong_danh_muc"'* && "${dung}" =~ ^[0-9]{6}-[0-9]{6}-[0-9]{2}$ ]] \
  && pass "(f) thêm yêu cầu hỗ trợ có mức độ ngoài danh mục bị từ chối (mức độ đúng danh mục thì nhận, mã dạng yyMMdd-HHmmss-NN)" \
  || fail "(f) mức độ ngoài danh mục: rc=${rc} ${kq} / hợp lệ: ${dung}"

# Thêm: kỹ thuật thấy mọi yêu cầu và ghi xử lý; khảo sát ẩn danh chỉ xem qua khung nhìn tổng hợp
kt="$(sql ky_thuat kt <<<"SELECT count(*) FROM onebee.yeu_cau_ho_tro;
INSERT INTO onebee.xu_ly_ho_tro (ma, cach_xu_ly, so_phut) VALUES ('${dung:-x}', 'Sửa cấu hình', 10) RETURNING nguoi_tao;")" || true
sql nhan_vien chi >/dev/null <<<"INSERT INTO onebee.khao_sat (diem_1, diem_2, diem_3, diem_4, diem_5, gop_y) VALUES (5, 4, 5, 4, 5, 'góp ý riêng');" || true
ks="$(sql quan_ly binh <<<"SELECT so_phieu || ' ' || diem_1 FROM onebee.khao_sat_tong_hop;")" || true
ks_bang="$(sql quan_ly binh <<<"SELECT gop_y FROM onebee.khao_sat;")" && rc=0 || rc=$?
ks_nv="$(sql nhan_vien chi <<<"SELECT count(*) FROM onebee.khao_sat_tong_hop;")" && rc2=0 || rc2=$?
[[ "${kt}" == $'1\nkt' && "${ks}" == "1 5.00" && ${rc} -ne 0 && "${ks_bang}" == *"permission denied"* && ${rc2} -ne 0 ]] \
  && pass "Kỹ thuật thấy mọi yêu cầu và ghi được xử lý; khảo sát: quản lý chỉ xem tổng hợp (không đọc được bảng, góp ý), nhân viên không xem" \
  || fail "Kỹ thuật/khảo sát: kt='${kt}' ks='${ks}' bảng: rc=${rc} ${ks_bang} / nv: rc=${rc2} ${ks_nv}"

# ===== Nạp sổ cũ mẫu =====
cp -R "${ROOT}/tests/box/fixtures/so-cu" "${T}/du-lieu"
dem_tep() { cat "$@" | grep -c . || true; }
mong="don_hang=$(dem_tep "${T}"/du-lieu/chung/don-hang/don-hang-*.csv) yeu_cau_ho_tro=$(dem_tep "${T}/du-lieu/ho-tro/yeu-cau.csv")"
mong="${mong} xu_ly_ho_tro=$(dem_tep "${T}/du-lieu/ho-tro/xu-ly.csv") khao_sat=$(dem_tep "${T}/du-lieu/ho-tro/khao-sat.csv")"
mong="${mong} tinh_trang_may=$(find "${T}/du-lieu/tinh-trang-may" -name '*.json' | wc -l | tr -d ' ')"
dem_bang() {
  chu -c "SELECT 'don_hang=' || (SELECT count(*) FROM onebee.don_hang WHERE nguon IS NOT NULL) || ' yeu_cau_ho_tro=' || (SELECT count(*) FROM onebee.yeu_cau_ho_tro WHERE nguon IS NOT NULL)
    || ' xu_ly_ho_tro=' || (SELECT count(*) FROM onebee.xu_ly_ho_tro WHERE nguon IS NOT NULL) || ' khao_sat=' || (SELECT count(*) FROM onebee.khao_sat WHERE nguon IS NOT NULL)
    || ' tinh_trang_may=' || (SELECT count(*) FROM onebee.tinh_trang_may)"
}
sum_goc="$(cd "${T}/du-lieu" && find . -type f | sort | xargs sha256sum)"
out1="$(python3 "${ROLE}/onebee-chuyen-du-lieu.py" "${T}/du-lieu" 2>&1)" && rc=0 || rc=$?
sau1="$(dem_bang)"
[[ ${rc} -eq 0 && "${sau1}" == "${mong}" && "$(chu -c "SELECT count(*) FROM onebee.don_hang WHERE nguon IS NOT NULL AND (nguoi_tao <> 'so-cu' OR trang_thai_duyet IS NOT NULL)")" == 0 ]] \
  && pass "(g) Nạp bộ sổ cũ mẫu: số dòng mỗi bảng bằng số dòng tệp mẫu (${mong}); người tạo so-cu, không có trạng thái duyệt" \
  || { fail "(g) Nạp sổ cũ: mã ${rc}, bảng '${sau1}', tệp '${mong}'"; echo "${out1}"; }
out2="$(python3 "${ROLE}/onebee-chuyen-du-lieu.py" "${T}/du-lieu" 2>&1)" && rc=0 || rc=$?
moi_nap="$(awk 'NR > 1 && NF == 4 {s += $3} END {print s + 0}' <<<"${out2}")"
so_dong_tk="$(awk 'NR > 1 && NF == 4' <<<"${out2}" | wc -l | tr -d ' ')"
[[ ${rc} -eq 0 && "$(dem_bang)" == "${sau1}" && "${moi_nap}" == 0 && "${so_dong_tk}" == 5 ]] \
  && pass "(h) Chạy lần hai: số dòng không đổi, mọi bảng 0 dòng mới nạp" || { fail "(h) Chạy lần hai: mã ${rc}, bảng '$(dem_bang)'"; echo "${out2}"; }
sum_sau="$(cd "${T}/du-lieu" && find . -type f ! -name '*.truoc-chuyen' | sort | xargs sha256sum)"
so_ban="$(find "${T}/du-lieu" -name '*.truoc-chuyen' | wc -l | tr -d ' ')"
[[ "${sum_sau}" == "${sum_goc}" && "${so_ban}" == 4 ]] && pass "Tệp sổ cũ không bị sửa; có bản .truoc-chuyen cho 4 tệp CSV" \
  || fail "Tệp sổ cũ bị đổi hoặc thiếu bản .truoc-chuyen (${so_ban})"
printf '2026-10-31 10:00,Khách lỗi,Hàng mẫu,không-phải-số,1,1,2026-11-01,\n' >>"${T}/du-lieu/chung/don-hang/don-hang-2026-10.csv"
truoc="$(dem_bang)"
out3="$(python3 "${ROLE}/onebee-chuyen-du-lieu.py" "${T}/du-lieu" 2>&1)" && rc=0 || rc=$?
[[ ${rc} -ne 0 && "${out3}" == *"don-hang-2026-10.csv"*"dòng 4"* && "$(dem_bang)" == "${truoc}" ]] \
  && pass "Tệp có dòng sai kiểu số: cả tệp bị từ chối, báo tên tệp + dòng 4, thoát mã khác 0" || { fail "Tệp có dòng lỗi: mã ${rc}"; echo "${out3}"; }

# ===== Sổ lược đồ: tệp mới (kết xuất trước), tệp cũ bị sửa (dừng) =====
printf 'CREATE TABLE onebee.thu_them (id bigserial PRIMARY KEY);\nALTER TABLE onebee.thu_them ENABLE ROW LEVEL SECURITY;\n' >"${T}/luoc-do/999-thu-them.sql"
out="$("${ROLE}/onebee-luoc-do.sh" "${T}/luoc-do" "${T}/ket-xuat" 2>&1)" && rc=0 || rc=$?
kx="${T}/ket-xuat/truoc-luoc-do-999-thu-them.dump"
[[ ${rc} -eq 0 && "${out}" == "đã áp dụng 999-thu-them.sql" && -s "${kx}" ]] && "${DOCKER}" exec -i "${CT}" pg_restore -l <"${kx}" | grep -q 'TABLE DATA onebee don_hang' \
  && pass "Lược đồ: tệp mới trên CSDL đã có dữ liệu → kết xuất truoc-luoc-do-999-thu-them.dump (có dữ liệu đơn hàng) rồi mới áp dụng" \
  || fail "Lược đồ tệp mới: mã ${rc} ${out}"
echo '-- sửa sau khi đã áp dụng' >>"${T}/luoc-do/001-khoi-tao.sql"
printf 'CREATE TABLE onebee.khong_duoc_chay (id int);\n' >"${T}/luoc-do/998-khong-duoc-chay.sql"
out="$("${ROLE}/onebee-luoc-do.sh" "${T}/luoc-do" "${T}/ket-xuat" 2>&1)" && rc=0 || rc=$?
[[ ${rc} -ne 0 && "${out}" == *"001-khoi-tao.sql đã áp dụng nhưng nội dung đã đổi"* \
   && "$(chu -c "SELECT count(*) FROM pg_tables WHERE tablename = 'khong_duoc_chay'")" == 0 ]] \
  && pass "Lược đồ: tệp đã áp dụng bị sửa → dừng với lỗi sha256, không chạy tệp nào" || fail "Lược đồ tệp bị sửa: mã ${rc} ${out}"

# ===== Kết xuất và khôi phục (như sao-luu / khoi-phuc-toan-bo) =====
truoc="$(dem_bang) $(chu -c 'SELECT count(*) FROM onebee.don_hang')"
"${DOCKER}" exec "${CT}" pg_dump -U postgres -d onebee -Fc >"${T}/onebee.dump"
chu -c "DELETE FROM onebee.tinh_trang_may; INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, nguoi_tao) VALUES ('sau', 'kết xuất', 1, 1, 1, 'quantri')" >/dev/null
kq="$("${DOCKER}" exec -i "${CT}" pg_restore -U postgres -d onebee --clean --if-exists --single-transaction <"${T}/onebee.dump" 2>&1)" && rc=0 || rc=$?
sau="$(dem_bang) $(chu -c 'SELECT count(*) FROM onebee.don_hang')"
an_sau="$(sql nhan_vien an <<<"SELECT count(*) FROM onebee.don_hang;")" || true
[[ ${rc} -eq 0 && "${sau}" == "${truoc}" && "${an_sau}" == 1 ]] \
  && pass "pg_restore --clean --if-exists từ bản kết xuất -Fc: dữ liệu trở lại đúng như lúc kết xuất, RLS vẫn hiệu lực" \
  || fail "Khôi phục kết xuất: mã ${rc} ${kq} — trước '${truoc}', sau '${sau}', an thấy ${an_sau}"

echo "---"
[[ ${loi} -eq 0 ]] && echo "Kết quả: mọi mục đạt" || echo "Kết quả: ${loi} mục không đạt"
exit $((loi > 0))
