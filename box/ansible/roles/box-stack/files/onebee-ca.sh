#!/usr/bin/env bash
# Sinh / gia hạn CA riêng của Box (rà soát bảo mật F3, Pha 3): gốc (10 năm) + trung gian (1 năm), cả hai ràng buộc tên (critical):
# chỉ được cấp chứng chỉ cho IP của Box (/32) và tên <mã đơn vị>.onebee.internal — lộ khóa CA cũng không giả được google.com hay router.
# Khóa GỐC chỉ nằm trong thư mục này (0700), KHÔNG gắn vào container nào; Caddy chỉ nhận chứng chỉ gốc + khóa trung gian.
# Cách dùng: [ONEBEE_PKI_OUT=<thư-mục>] onebee-ca.sh <thư-mục-ca> <mã-đơn-vị> <ip-box> [--xoay]
#   In "đã đổi" khi có tạo/gia hạn (để Ansible báo changed). Thoát 4 khi mã đơn vị/IP khác lần tạo CA (đổi = xoay CA: --xoay).
#   ONEBEE_PKI_OUT: chép riêng chứng chỉ gốc + chứng chỉ/khóa TRUNG GIAN vào đó (thư mục gắn vào container Caddy; KHÔNG chép khóa gốc);
#   thư mục này đổi nội dung cũng được tính là "đã đổi" (Caddy cần nạp lại).
set -euo pipefail

DIR="${1:?thiếu thư mục CA}"; MA="${2:?thiếu mã đơn vị}"; IP="${3:?thiếu IP Box}"; XOAY="${4:-}"
GOC_NGAY=3650; TRUNG_GIAN_NGAY=365; GIA_HAN_KHI_CON=60
die() { printf 'LỖI: %s\n' "$*" >&2; exit "${2:-1}"; }

[[ "${MA}" =~ ^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$ ]] || die "Mã đơn vị chỉ gồm chữ thường không dấu, số, gạch giữa (tối đa 32 ký tự)"
[[ "${IP}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || die "IP Box không hợp lệ: ${IP}"
DNS="${MA}.onebee.internal"
umask 077
mkdir -p "${DIR}"; chmod 0700 "${DIR}"
cd "${DIR}"
doi=0

if [[ -s ca.conf ]]; then
  # shellcheck disable=SC1091
  . ./ca.conf
  # --xoay luôn xoay (kể cả khi mã/IP không đổi — nghi lộ khóa CA); không có --xoay mà mã/IP lệch thì dừng
  if [[ "${XOAY}" == --xoay || "${CA_MA:-}" != "${MA}" || "${CA_IP:-}" != "${IP}" ]]; then
    if [[ "${XOAY}" != --xoay ]]; then
      die "CA đã tạo cho mã '${CA_MA:-?}' / IP '${CA_IP:-?}', nay khai '${MA}' / '${IP}'. Đổi mã hoặc IP = xoay CA (mọi máy phải nhận CA mới): đặt onebee_box_xoay_ca: true trong group_vars/all.yml, chạy bộ cài, rồi đặt lại false" 4
    fi
    mkdir -p "${DIR}.cu" ; mv root.crt root.key inter.crt inter.key ca.conf "${DIR}.cu/" 2>/dev/null || true
    mv "${DIR}.cu" "${DIR}.cu-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${DIR}"; chmod 0700 "${DIR}"
  fi
fi

NC="critical,permitted;IP:${IP}/255.255.255.255,permitted;DNS:${DNS}"
if [[ ! -s root.crt || ! -s root.key ]]; then
  openssl ecparam -name prime256v1 -genkey -noout -out root.key 2>/dev/null
  openssl req -new -x509 -key root.key -sha256 -days "${GOC_NGAY}" -subj "/O=OneBee Box ${MA}/CN=OneBee Box ${MA} Root CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:1" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "nameConstraints=${NC}" -out root.crt
  printf 'CA_MA=%s\nCA_IP=%s\n' "${MA}" "${IP}" >ca.conf
  doi=1
fi

# Trung gian: tạo mới nếu chưa có hoặc còn dưới ${GIA_HAN_KHI_CON} ngày (Caddy không tự gia hạn trung gian được cấp sẵn)
if [[ ! -s inter.crt || ! -s inter.key ]] || ! openssl x509 -in inter.crt -noout -checkend $((GIA_HAN_KHI_CON * 86400)) >/dev/null; then
  openssl ecparam -name prime256v1 -genkey -noout -out inter.key 2>/dev/null
  openssl req -new -key inter.key -sha256 -subj "/O=OneBee Box ${MA}/CN=OneBee Box ${MA} Intermediate CA" -out inter.csr
  printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nnameConstraints=%s\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid\n' \
    "${NC}" >inter.ext
  openssl x509 -req -in inter.csr -CA root.crt -CAkey root.key -CAcreateserial -days "${TRUNG_GIAN_NGAY}" -sha256 -extfile inter.ext -out inter.crt 2>/dev/null
  rm -f inter.csr inter.ext root.srl
  doi=1
fi

# Vân tay SHA-256 của chứng chỉ gốc — đối chiếu qua kênh ngoài (giấy in khóa, màn hình Box)
openssl x509 -in root.crt -outform DER | sha256sum | cut -d' ' -f1 >root.sha256
chmod 0644 root.crt inter.crt root.sha256   # chứng chỉ là công khai; chỉ khóa (.key) giữ 0600
if [[ -n "${ONEBEE_PKI_OUT:-}" ]]; then
  mkdir -p "${ONEBEE_PKI_OUT}"; chmod 0700 "${ONEBEE_PKI_OUT}"
  for f in root.crt inter.crt inter.key; do
    cmp -s "${f}" "${ONEBEE_PKI_OUT}/${f}" || { install -m 0600 "${f}" "${ONEBEE_PKI_OUT}/${f}"; doi=1; }
  done
  # Dọn khóa gốc nếu một phiên bản nào đó từng chép nhầm
  rm -f "${ONEBEE_PKI_OUT}/root.key"
fi
[[ "${doi}" -eq 0 ]] || echo "đã đổi"
exit 0
