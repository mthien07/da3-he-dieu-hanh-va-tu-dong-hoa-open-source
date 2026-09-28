#!/usr/bin/env bash
# Chạy thử bộ cài OneBee OS Desktop trong container Linux Mint 22.3 (image linuxmintd/mint22.3-amd64).
# Kiểm tra: (1) cài được, (2) chạy lần 2 không thay đổi gì (idempotent), (3) verify-desktop-install.sh đạt,
# (4) LibreOffice thật sự đọc được cấu hình định dạng mặc định (qua UNO).
# Giới hạn: container không có phiên đồ họa/systemd thật — gõ phím, hiển thị, máy in phải thử trên VM/máy thật.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${ONEBEE_TEST_IMAGE:-linuxmintd/mint22.3-amd64}"
# Mạng có proxy HTTPS riêng (chứng chỉ tự ký): đặt ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt để container tin chứng chỉ đó
extra_ca=()
if [[ -n "${ONEBEE_TEST_EXTRA_CA:-}" ]]; then
  extra_ca=(-v "${ONEBEE_TEST_EXTRA_CA}:/usr/local/share/ca-certificates/onebee-test-extra.crt:ro")
fi

docker run --rm "${extra_ca[@]}" -v "${REPO_ROOT}:/onebee:ro" "${IMAGE}" bash -euo pipefail -c '
  export DEBIAN_FRONTEND=noninteractive
  if [ -f /usr/local/share/ca-certificates/onebee-test-extra.crt ]; then update-ca-certificates >/dev/null; fi
  # Mô phỏng thành phần có sẵn trên bản Mint Cinnamon cài đặt thật (image container rút gọn không có)
  apt-get update -q >/dev/null
  apt-get install -y -q mintupdate mint-artwork cinnamon-desktop-data libglib2.0-bin >/dev/null

  cp -r /onebee /tmp/onebee
  echo "===== LẦN 1: cài đặt ====="
  /tmp/onebee/desktop/onebee-install.sh | tee /tmp/run1.log
  echo "===== LẦN 2: kiểm tra idempotent ====="
  /tmp/onebee/desktop/onebee-install.sh | tee /tmp/run2.log
  if ! grep -Eq "changed=0 .*failed=0" /tmp/run2.log; then
    echo "LỖI: lần chạy thứ 2 vẫn có thay đổi hoặc lỗi"; grep -E "^(changed|localhost)" /tmp/run2.log; exit 1
  fi
  echo "===== KIỂM TRA KẾT QUẢ ====="
  /tmp/onebee/tests/desktop/verify-desktop-install.sh
  apt-get install -y -q python3-uno >/dev/null
  python3 /tmp/onebee/tests/desktop/check-libreoffice-default-formats.py
'
