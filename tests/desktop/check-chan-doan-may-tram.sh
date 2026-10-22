#!/usr/bin/env bash
# shellcheck disable=SC2016  # thân các lệnh giả viết trong nháy đơn: biến phải mở rộng lúc lệnh giả chạy, không phải lúc tạo
# Kiểm thử lệnh máy trạm "onebee-chan-doan" mà không cần Box thật: Box giả ở 127.0.0.1 (cổng TCP thật mở bằng python3: Trợ lý AI,
# Samba 445, nhận sao lưu), ping/ip/systemctl/df GIẢ (trạng thái đặt bằng file trong $SIM). Mỗi kịch bản làm hỏng ĐÚNG 1 thứ → đúng dòng đó
# báo [CẢNH BÁO]/[LỖI], mã thoát đúng. Cần root (mở cổng 445), bash 4+, python3. Cách dùng: sudo tests/desktop/check-chan-doan-may-tram.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CMD="${HERE}/../../desktop/ansible/roles/quan-ly-tap-trung/files/onebee-chan-doan"
[[ ${EUID} -eq 0 ]] || { echo "Cần chạy bằng root (mở cổng 445 giả làm thư mục chung của Box)"; exit 2; }
T="$(mktemp -d)"
SIM="${T}/sim"
NGHE_PID=""
trap '[[ -z "${NGHE_PID}" ]] || kill "${NGHE_PID}" 2>/dev/null; rm -rf "${T}"' EXIT
fails=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; fails=$((fails + 1)); }
mkdir -p "${T}/bin" "${T}/bin-restic" "${T}/etc" "${T}/var"

gia() { printf '#!/usr/bin/env bash\n%s\n' "$2" >"$1"; chmod +x "$1"; }
gia "${T}/bin/ping" 'd="${!#}"; [[ -s "${SIM}/ping-${d}" ]] || { echo "3 packets transmitted, 0 received, 100% packet loss"; exit 1; }
a="$(cat "${SIM}/ping-${d}")"; echo "rtt min/avg/max/mdev = ${a}/${a}/${a}/0.000 ms"'
gia "${T}/bin/ip" '[[ -s "${SIM}/gateway" ]] && echo "default via $(cat "${SIM}/gateway") dev eth0 proto dhcp metric 100"; exit 0'
gia "${T}/bin/systemctl" '[[ ! -e "${SIM}/dung-${!#}" ]]'
gia "${T}/bin/df" 'p=40; [[ ! -s "${SIM}/df-home" ]] || p="$(cat "${SIM}/df-home")"
echo "Filesystem 1024-blocks Used Available Capacity Mounted on"; echo "/dev/sda2 100 ${p} $((100 - p)) ${p}% /home"'
gia "${T}/bin-restic/restic" 'exit 0'
export SIM NO_COLOR=1 ONEBEE_CONF="${T}/etc/may-tram.env" ONEBEE_HOI_CONF="${T}/etc/onebee-hoi.conf" ONEBEE_VAR="${T}/var"
PATH_CO_RESTIC="${T}/bin:${T}/bin-restic:${PATH}"

# Box giả: nghe các cổng TCP $@ trên 127.0.0.1 (nhận rồi đóng kết nối)
mo_cong() {
  [[ -z "${NGHE_PID}" ]] || { kill "${NGHE_PID}" 2>/dev/null; wait "${NGHE_PID}" 2>/dev/null; }
  python3 -c 'import selectors, socket, sys
sel = selectors.DefaultSelector()
for p in sys.argv[1:]:
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("127.0.0.1", int(p))); s.listen(); sel.register(s, selectors.EVENT_READ)
print("san-sang", flush=True)
while True:
    for k, _ in sel.select():
        k.fileobj.accept()[0].close()' "$@" >"${T}/nghe.log" 2>&1 &
  NGHE_PID=$!
  for _ in $(seq 50); do grep -q san-sang "${T}/nghe.log" && return; sleep 0.1; done
  echo "Không mở được cổng giả: $(cat "${T}/nghe.log")"; exit 1
}

moi_thu_khoe() {
  rm -rf "${SIM}"; mkdir -p "${SIM}"
  echo 192.168.1.1 >"${SIM}/gateway"; echo 0.5 >"${SIM}/ping-192.168.1.1"; echo 0.8 >"${SIM}/ping-127.0.0.1"
  printf 'MAY_TRAM=ketoan-01\r\nBOX_IP=127.0.0.1\r\nRESTIC_REPOSITORY=rest:http://ketoan-01:mk@127.0.0.1:18000/ketoan-01/\r\nRESTIC_PASSWORD=x\r\n' >"${ONEBEE_CONF}"
  printf '# Quản lý bởi OneBee OS\nHOI_URL=http://127.0.0.1:13000\nHOI_MODEL=onebee-tro-ly\n' >"${ONEBEE_HOI_CONF}"
  echo $(( $(date +%s) - 3 * 3600 )) >"${T}/var/sao-luu-cuoi"
  PATH="${PATH_CO_RESTIC}"
}

chay() { OUT="$(bash "${CMD}" 2>&1)"; RC=$?; }
# Các dòng không OK, dạng "MỨC:tên" nối bằng "; " (theo thứ tự in)
khong_ok() { sed -n 's/^  \[\(CẢNH BÁO\|LỖI\)\] *\([^:]*\):.*/\1:\2/p' <<<"${OUT}" | paste -sd ';' - | sed 's/;/; /g'; }
kich_ban() {
  local mo_ta="$1" rc_mong="$2" mong="$3" thuc
  chay
  thuc="$(khong_ok)"
  if [[ "${RC}" == "${rc_mong}" && "${thuc}" == "${mong}" ]]; then pass "${mo_ta}"
  else fail "${mo_ta} — mã thoát ${RC} (mong ${rc_mong}); không OK: '${thuc}' (mong '${mong}')"; while IFS= read -r d; do printf '      %s\n' "${d}"; done <<<"${OUT}"; fi
}

mo_cong 13000 445 18000
moi_thu_khoe
kich_ban "Mọi thứ khỏe → toàn [OK], mã thoát 0" 0 ""
if [[ "$(grep -c '^  \[OK\]' <<<"${OUT}")" == 9 && "$(grep -c '^[1-4]\. ' <<<"${OUT}")" == 4 ]] && grep -q '^KẾT LUẬN: máy và kết nối tới Box bình thường' <<<"${OUT}" \
   && grep -q 'Nhận sao lưu: Box mở cổng 18000' <<<"${OUT}" && grep -q 'Trợ lý AI: Box mở cổng 13000' <<<"${OUT}"; then
  pass "Đủ 4 hạng mục, 9 mục OK; cổng AI/sao lưu lấy từ cấu hình (file có \\r kiểu Windows)"
else fail "Bảng chữ khi mọi thứ khỏe sai"; echo "${OUT}"; fi

moi_thu_khoe; rm -f "${SIM}/ping-192.168.1.1"
kich_ban "Router không trả lời → LỖI router (Box vẫn kiểm)" 2 "LỖI:Cổng mạng (router)"
moi_thu_khoe; : >"${SIM}/gateway"
kich_ban "Máy chưa có mạng (không có gateway) → LỖI" 2 "LỖI:Cổng mạng (router)"
moi_thu_khoe; rm -f "${SIM}/ping-127.0.0.1"
kich_ban "Box không trả lời → LỖI Box, không kiểm dịch vụ trên Box" 2 "LỖI:OneBee Box; LỖI:Dịch vụ trên Box"
moi_thu_khoe; printf 'HOI_URL=http://127.0.0.1:13001\n' >"${ONEBEE_HOI_CONF}"
kich_ban "Box không mở cổng Trợ lý AI → chỉ LỖI Trợ lý AI" 2 "LỖI:Trợ lý AI"
mo_cong 13000 18000; moi_thu_khoe
kich_ban "Box không mở cổng 445 → chỉ LỖI thư mục chung" 2 "LỖI:Thư mục chung (Samba)"
mo_cong 13000 445 18000

moi_thu_khoe; rm -f "${ONEBEE_CONF}"
kich_ban "Nhân viên chạy không sudo (không đọc được may-tram.env): lấy Box từ hoi.conf, cổng sao lưu mặc định 8000" 2 "LỖI:Nhận sao lưu"
if grep -q 'Box 127.0.0.1 trả lời' <<<"${OUT}" && grep -q 'cổng 8000' <<<"${OUT}"; then pass "Địa chỉ Box lấy từ HOI_URL"; else fail "Không lấy địa chỉ Box từ HOI_URL"; fi
moi_thu_khoe; rm -f "${ONEBEE_CONF}" "${ONEBEE_HOI_CONF}"
kich_ban "Máy chưa nối Box (không có cấu hình) → LỖI kèm cách nối" 2 "LỖI:OneBee Box; LỖI:Dịch vụ trên Box"
if grep -q 'onebee-box them-may' <<<"${OUT}"; then pass "Gợi ý quản trị chạy them-may"; else fail "Thiếu gợi ý them-may"; fi

moi_thu_khoe; PATH="${T}/bin:/usr/bin:/bin"
kich_ban "Chưa cài restic → LỖI" 2 "LỖI:Phần mềm sao lưu (restic)"
moi_thu_khoe; : >"${SIM}/dung-onebee-sao-luu.timer"
kich_ban "Lịch sao lưu tắt → LỖI" 2 "LỖI:Lịch sao lưu hằng ngày"
moi_thu_khoe; echo $(( $(date +%s) - 30 * 3600 )) >"${T}/var/sao-luu-cuoi"
kich_ban "Lần sao lưu cuối cách 30 giờ → CẢNH BÁO, mã thoát 1" 1 "CẢNH BÁO:Lần sao lưu cuối"
moi_thu_khoe; rm -f "${T}/var/sao-luu-cuoi"
kich_ban "Chưa sao lưu lần nào → LỖI" 2 "LỖI:Lần sao lưu cuối"
moi_thu_khoe; echo 85 >"${SIM}/df-home"
kich_ban "Ổ /home 85% → CẢNH BÁO" 1 "CẢNH BÁO:Ổ chứa /home"
moi_thu_khoe; echo 95 >"${SIM}/df-home"
kich_ban "Ổ /home 95% → LỖI" 2 "LỖI:Ổ chứa /home"

echo "---"
echo "Kết quả: ${fails} mục không đạt"
exit $((fails > 0))
