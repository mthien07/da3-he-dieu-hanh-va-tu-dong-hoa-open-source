#!/usr/bin/env bash
# Chạy BÊN TRONG máy/container đã cài OneBee OS, bằng tài khoản người dùng thường (không phải root).
# Mở màn hình ảo Xvfb + phiên D-Bus mới + IBus, gõ phím giả lập kiểu Telex vào ô nhập GTK,
# rồi so sánh chữ nhận được với chữ tiếng Việt mong đợi.
# Biến ONEBEE_TEST_ENGINE: Bamboo (mặc định) hoặc Unikey.
set -euo pipefail
export ENGINE="${ONEBEE_TEST_ENGINE:-Bamboo}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$(mktemp)"
export DISPLAY=:99 LANG=vi_VN.UTF-8
export GTK_IM_MODULE=ibus XMODIFIERS=@im=ibus QT_IM_MODULE=ibus

Xvfb :99 -screen 0 1280x800x24 >/dev/null 2>&1 &
xvfb_pid=$!
trap 'kill ${xvfb_pid} 2>/dev/null || true; rm -f "${OUT}"' EXIT
sleep 2

dbus-run-session -- bash -euo pipefail -c '
  # Giá trị người dùng MỚI nhận được qua dconf thật (không phải backend bộ nhớ)
  echo "preload-engines (dconf người dùng): $(gsettings get org.freedesktop.ibus.general preload-engines)"
  echo "hình nền Cinnamon (dconf người dùng): $(gsettings get org.cinnamon.desktop.background picture-uri 2>/dev/null || echo không-có-cinnamon)"
  ibus-daemon --daemonize --replace --xim
  sleep 3
  echo "engine có trong IBus: $(ibus list-engine | grep -ciE "bamboo|unikey")"
  python3 "'"${HERE}"'/entry-capture-app.py" "'"${OUT}"'" &
  app_pid=$!
  # Không có trình quản lý cửa sổ → tự đặt tiêu điểm bàn phím vào cửa sổ test
  win="$(xdotool search --sync --name "OneBee IME test" | head -n1 || true)"
  xdotool windowfocus --sync "${win}"
  xdotool mousemove --window "${win}" 20 10
  # IBus chỉ đổi bộ gõ khi ô nhập đã nhận tiêu điểm → thử lại tối đa 10 lần
  for _ in 1 2 3 4 5 6 7 8 9 10; do ibus engine "${ENGINE}" 2>/dev/null && break; sleep 1; done
  echo "engine đang dùng: $(ibus engine)"
  # Telex: Vieejt Nam -> Việt Nam ; Howjp tacs xax -> Hợp tác xã
  xdotool type --delay 150 "Vieejt Nam Howjp tacs xax "
  sleep 1
  xdotool key Return
  wait ${app_pid}
'

got="$(cat "${OUT}")"
want="Việt Nam Hợp tác xã"
echo "Gõ Telex nhận được: [${got}]"
if [[ "${got%% }" == "${want}" ]]; then echo "PASS  Gõ tiếng Việt Telex qua IBus + ${ENGINE}"; else echo "FAIL  Mong đợi [${want}]"; exit 1; fi
