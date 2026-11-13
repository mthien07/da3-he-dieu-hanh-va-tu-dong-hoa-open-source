#!/usr/bin/env bash
# Kiểm tra Trung tâm OneBee (onebee-trung-tam) — chạy bằng tài khoản thường trong container đã cài OneBee OS.
# Mở màn hình ảo Xvfb, dựng cửa sổ và mọi trang bằng --tu-kiem, và xác nhận --lan-dau không tự mở lại khi đã có file dấu.
set -euo pipefail

CFG="$(mktemp -d)"
export DISPLAY=:99 LANG=vi_VN.UTF-8

Xvfb :99 -screen 0 1280x800x24 >/dev/null 2>&1 &
xvfb_pid=$!
trap 'kill "${xvfb_pid}" 2>/dev/null || true; rm -rf "${CFG}"' EXIT
sleep 2

if out="$(onebee-trung-tam --tu-kiem 2>&1)" && [[ "${out}" == *"TU-KIEM-DAT"* ]]; then
  echo "PASS  Trung tâm OneBee dựng được đủ các trang"
else
  echo "FAIL  Trung tâm OneBee dựng được đủ các trang: ${out:-}"
  exit 1
fi

mkdir -p "${CFG}/onebee"
: >"${CFG}/onebee/trung-tam-da-xem"
if XDG_CONFIG_HOME="${CFG}" timeout 10 onebee-trung-tam --lan-dau; then
  echo "PASS  Đã xem rồi thì không tự mở lại"
else
  echo "FAIL  Đã xem rồi thì không tự mở lại"
  exit 1
fi
