#!/usr/bin/env bash
# Kiểm tra tên onebee.local (mDNS) và trang chủ Dashboard cổng 80 (chạy trên Box bằng root, sau khi cài). Cần: avahi-utils, curl, python3.
# Cách dùng: check-mdns-dashboard.sh [tên-mdns]   (mặc định: onebee → onebee.local)
# Phân giải bằng avahi (không cần libnss-mdns trên Box), rồi gọi http://<tên>.local đúng tên miền bằng curl --resolve.
set -uo pipefail
TEN="${1:-onebee}.local"
fails=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then printf 'PASS  %s\n' "$d"; else printf 'FAIL  %s\n' "$d"; fails=$((fails + 1)); fi; }

check "avahi-daemon đang chạy và bật cùng máy" bash -c "systemctl is-active avahi-daemon && systemctl is-enabled avahi-daemon"

# avahi-daemon vừa khởi động lại có thể chưa xong bước dò trùng tên → thử lại tối đa 20 giây
ip=""
for _ in $(seq 1 10); do
  ip="$(avahi-resolve-host-name -4 "${TEN}" 2>/dev/null | awk '{print $2}')"
  [[ -n "${ip}" ]] && break
  sleep 2
done
check "mDNS phân giải ${TEN} → ${ip:-(không có)}" test -n "${ip}"

cong_mang="$(ip -4 route show default | awk '{print $5; exit}')"
check "${TEN} trỏ đúng IP của cổng mạng chính ${cong_mang} (không phải IP mạng Docker)" bash -c \
  "ip -4 -o addr show dev '${cong_mang}' | awk '{print \$4}' | cut -d/ -f1 | grep -qxF '${ip}'"
check "${TEN} không có địa chỉ IPv6 (Docker chỉ mở cổng IPv4)" bash -c "! avahi-resolve-host-name -6 '${TEN}' 2>/dev/null | grep -q ."
check "Quảng bá dịch vụ web _http._tcp cổng 80" bash -c "avahi-browse -rpt _http._tcp 2>/dev/null | grep -q '^=;.*;${TEN};.*;80;'"

trang="$(curl -s -m 10 --resolve "${TEN}:80:${ip:-127.0.0.1}" "http://${TEN}/")"
check "http://${TEN} trả trang có \"OneBee Box\"" grep -q 'OneBee Box' <<<"${trang}"

# Chế độ HTTPS: cổng 80 chỉ hướng dẫn cài CA (trang chủ ở https://<IP>/) → số liệu không đọc qua cổng 80
if grep -q 'id="trang-thai"' <<<"${trang}"; then
  check "Số liệu tình trạng mới (dưới 3 phút) và đủ mục" bash -c \
    "curl -s -m 10 --resolve '${TEN}:80:${ip:-127.0.0.1}' 'http://${TEN}/trang-thai.json' | python3 -c '
import datetime, json, sys
d = json.load(sys.stdin)
tuoi = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(d[\"cap_nhat\"])
assert tuoi.total_seconds() < 180, tuoi
assert set(d[\"dich_vu\"]) == {\"tro_ly_ai\", \"thu_muc_chung\", \"sao_luu\"}
assert 0 <= d[\"cpu_phan_tram\"] <= 100 and 0 <= d[\"ram_phan_tram\"] <= 100'"
  check "Lịch cập nhật số liệu đang bật" systemctl is-active onebee-trang-thai-web.timer
else
  echo "BỎ QUA  Số liệu tình trạng qua cổng 80 (Box đang bật HTTPS)"
fi

echo "---"
echo "Kết quả: ${fails} mục không đạt"
exit $((fails > 0))
