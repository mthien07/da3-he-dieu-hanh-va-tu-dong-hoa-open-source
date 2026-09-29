#!/usr/bin/env bash
# Kiểm tra hỗ trợ từ xa (onebee-ho-tro) — chạy bằng người dùng thường trong container đã cài OneBee OS.
# Cần: xvfb, xdotool, vncsnapshot (vncsnapshot đóng vai "máy kỹ thuật" kết nối VNC).
set -euo pipefail
export DISPLAY=:77
Xvfb :77 -screen 0 800x600x24 >/dev/null 2>&1 &
xv=$!
trap 'kill "${xv}" 2>/dev/null || true; pkill -u "$(id -u)" x11vnc 2>/dev/null || true' EXIT
sleep 2
out=$(mktemp)

bat_dau() {  # $1 = số giây chờ; in mã
  : >"${out}"
  ONEBEE_HO_TRO_CHO_GIAY="$1" onebee-ho-tro --khong-hoi >"${out}" 2>&1 &
  for _ in $(seq 20); do grep -q "Mã:" "${out}" && ss -ltn 'sport = :5900' | grep -q LISTEN && break; sleep 0.5; done
  grep -oP 'Mã:\s*\K[0-9]{8}' "${out}"
}
# Kỹ thuật kết nối bằng mã $1; người dùng trả lời hộp thoại bằng phím $2 (Return = Cho phép, Escape = Từ chối)
ket_noi() {
  x11vnc -storepasswd "$1" /tmp/ma-thu >/dev/null 2>&1
  timeout 40 vncsnapshot -passwd /tmp/ma-thu 127.0.0.1:0 /tmp/man-hinh.jpg >/tmp/snap.log 2>&1 &
  local snap=$! w=""
  for _ in $(seq 30); do w=$(xdotool search --name "Hỗ trợ từ xa" 2>/dev/null | tail -1); [[ -n "${w}" ]] && break; sleep 0.5; done
  [[ -n "${w}" ]] || { echo "FAIL  Không hiện hộp thoại hỏi người dùng khi có máy xin vào"; exit 1; }
  xdotool windowfocus --sync "${w}" 2>/dev/null || true
  xdotool key "$2"
  wait "${snap}"
}

ma=$(bat_dau 600) || { echo "FAIL  Không mở được phiên hỗ trợ: $(cat "${out}")"; exit 1; }
[[ ${#ma} -eq 8 ]] && grep -q "Địa chỉ:" "${out}" && echo "PASS  Người dùng bấm hỗ trợ → hiện địa chỉ + mã 8 số dùng 1 lần"
if ket_noi "${ma}" Escape; then echo "FAIL  Người dùng bấm Từ chối mà kỹ thuật vẫn vào được"; exit 1; fi
echo "PASS  Đúng mã nhưng người dùng bấm \"Từ chối\" → không vào được"
sai=$(printf '%08d' $(( (10#${ma} + 1) % 100000000 )))
if ket_noi "${sai}" Return; then echo "FAIL  Mã sai vẫn vào được"; exit 1; fi
grep -q "authentication failed" /tmp/snap.log || { echo "FAIL  Mã sai: $(cat /tmp/snap.log)"; exit 1; }
echo "PASS  Mã sai → không vào được"
ket_noi "${ma}" Return || { echo "FAIL  Đúng mã + người dùng cho phép mà không vào được: $(cat /tmp/snap.log)"; exit 1; }
[[ -s /tmp/man-hinh.jpg ]] && echo "PASS  Đúng mã + người dùng bấm \"Cho phép\" → kỹ thuật xem được màn hình"
sleep 3
if ss -ltn 'sport = :5900' | grep -q LISTEN; then echo "FAIL  Kỹ thuật thoát rồi mà vẫn mở cổng"; exit 1; fi
echo "PASS  Kỹ thuật ngắt kết nối → phiên hỗ trợ tự đóng (mã không dùng lại được)"

bat_dau 5 >/dev/null
sleep 12
if ss -ltn 'sport = :5900' | grep -q LISTEN; then echo "FAIL  Không ai vào mà phiên không tự đóng"; exit 1; fi
echo "PASS  Không ai vào trong thời gian chờ → phiên tự đóng"
