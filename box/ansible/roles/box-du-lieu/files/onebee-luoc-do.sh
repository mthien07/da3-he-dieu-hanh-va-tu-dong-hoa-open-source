#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Áp dụng lược đồ CSDL của OneBee Box có ghi sổ (bảng onebee.lich_su_luoc_do: ten_tep, sha256, ap_dung_luc).
# - Chỉ chạy tệp NNN-*.sql chưa có trong sổ, theo thứ tự tên; mỗi tệp một giao dịch (lỗi thì hoàn tác cả tệp, dừng).
# - Tệp đã áp dụng mà nội dung đổi (sha256 khác sổ) → dừng với lỗi, không áp dụng gì: thay đổi lược đồ luôn là tệp mới có số tiếp theo.
# - CSDL đã có lược đồ (sổ không rỗng) → kết xuất toàn bộ ra <thư-mục-kết-xuất>/truoc-luoc-do-<tên tệp>.dump TRƯỚC khi áp dụng tệp mới.
# - In "đã áp dụng <tệp>" cho mỗi tệp mới (bộ cài báo changed theo dòng này); không có tệp mới thì không in gì.
# Nạp bằng quyền chủ CSDL trong container (docker exec ... psql -U postgres), không qua API.
# Cách dùng: onebee-luoc-do.sh <thư-mục-tệp-lược-đồ> <thư-mục-kết-xuất>   (ONEBEE_PG_CONTAINER: tên container, mặc định onebee-postgres)
set -euo pipefail
LUOC_DO="${1:?Cách dùng: onebee-luoc-do.sh <thư-mục-tệp-lược-đồ> <thư-mục-kết-xuất>}"
KET_XUAT="${2:?Cách dùng: onebee-luoc-do.sh <thư-mục-tệp-lược-đồ> <thư-mục-kết-xuất>}"
CT="${ONEBEE_PG_CONTAINER:-onebee-postgres}"

die() { printf 'LỖI: %s\n' "$*" >&2; exit 1; }
csdl() { docker exec -i "${CT}" psql -X -q -U postgres -d onebee -v ON_ERROR_STOP=1 "$@"; }

# Sổ lược đồ nằm trong lược đồ onebee như mọi bảng khác: bật và ép RLS, không cấp quyền cho vai trò nào
csdl >/dev/null <<'SQL' || die "Không nối được PostgreSQL trong container ${CT}"
SET client_min_messages = warning;
CREATE SCHEMA IF NOT EXISTS onebee;
CREATE TABLE IF NOT EXISTS onebee.lich_su_luoc_do (
  ten_tep text PRIMARY KEY,
  sha256 text NOT NULL,
  ap_dung_luc timestamp without time zone NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')
);
ALTER TABLE onebee.lich_su_luoc_do ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.lich_su_luoc_do FORCE ROW LEVEL SECURITY;
SQL
so="$(csdl -At -c 'SELECT ten_tep, sha256 FROM onebee.lich_su_luoc_do ORDER BY ten_tep' -F ' ')" || die "Không đọc được sổ lược đồ"

# Kiểm hết trước, áp dụng sau: một tệp cũ bị sửa thì không tệp mới nào được chạy
moi=()
for f in "${LUOC_DO}"/*.sql; do
  [[ -e "${f}" ]] || continue
  ten="$(basename "${f}")"
  [[ "${ten}" =~ ^[0-9]{3}-[a-z0-9-]+\.sql$ ]] || die "Tên tệp lược đồ không hợp lệ: ${ten} (dạng NNN-ten-viet-thuong.sql)"
  sha="$(sha256sum "${f}" | cut -d' ' -f1)"
  cu="$(awk -v t="${ten}" '$1 == t {print $2}' <<<"${so}")"
  if [[ -z "${cu}" ]]; then
    moi+=("${f}")
  elif [[ "${cu}" != "${sha}" ]]; then
    die "Tệp lược đồ ${ten} đã áp dụng nhưng nội dung đã đổi (sha256 trong sổ ${cu}, tệp hiện tại ${sha}). Không sửa tệp đã áp dụng: trả tệp về như cũ và đưa thay đổi vào tệp mới có số tiếp theo"
  fi
done

for f in ${moi[@]+"${moi[@]}"}; do
  ten="$(basename "${f}")"
  sha="$(sha256sum "${f}" | cut -d' ' -f1)"
  if [[ -n "${so}" ]]; then
    install -d -m 0700 "${KET_XUAT}"
    kx="${KET_XUAT}/truoc-luoc-do-${ten%.sql}.dump"
    docker exec "${CT}" pg_dump -U postgres -d onebee -Fc >"${kx}.moi" || { rm -f "${kx}.moi"; die "Không kết xuất được CSDL trước khi áp dụng ${ten} — chưa áp dụng gì"; }
    mv "${kx}.moi" "${kx}"
  fi
  { printf 'SET client_min_messages = warning;\nBEGIN;\n'
    cat "${f}"
    printf "\nINSERT INTO onebee.lich_su_luoc_do (ten_tep, sha256) VALUES ('%s', '%s');\nCOMMIT;\n" "${ten}" "${sha}"
    # Dịch vụ dữ liệu (PostgREST) nạp lại danh sách bảng/cột ngay, không phải khởi động lại
    printf "NOTIFY pgrst, 'reload schema';\n"
  } | csdl >/dev/null || die "Áp dụng ${ten} lỗi — đã hoàn tác tệp này, các tệp sau chưa chạy"
  echo "đã áp dụng ${ten}"
done
