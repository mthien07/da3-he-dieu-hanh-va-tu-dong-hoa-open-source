#!/usr/bin/env bash
# Kiểm tra bộ trợ lý file cài đặt Windows (.exe, .msi) và gợi ý ứng dụng thay thế (Task 03)
# In PASS/FAIL từng mục, thoát mã 1 nếu có lỗi.
set -uo pipefail

fails=0
check() { # check "mô tả" lệnh...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "$desc"
  else
    printf 'FAIL  %s\n' "$desc"
    fails=$((fails + 1))
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HELPER_SRC="${ROOT_DIR}/desktop/scripts/onebee-windows-app-helper"
DESKTOP_SRC="${ROOT_DIR}/desktop/assets/onebee-exe-handler.desktop"
INSTALL_SRC="${ROOT_DIR}/desktop/onebee-install.sh"

printf '=== KIỂM TRA TASK 03: WINDOWS APP HELPER (.EXE INTERCEPTOR) ===\n'

# 1. Kiểm tra tồn tại và quyền thực thi của các tệp nguồn
check "File trợ lý script tồn tại và có quyền thực thi" test -x "${HELPER_SRC}"
check "File desktop entry tồn tại" test -f "${DESKTOP_SRC}"

# 2. Kiểm tra nội dung file desktop entry
check "Desktop entry khai báo đúng kiểu Application" grep -q '^Type=Application' "${DESKTOP_SRC}"
check "Desktop entry gọi lệnh onebee-windows-app-helper" grep -Eq '^Exec=onebee-windows-app-helper' "${DESKTOP_SRC}"
check "Desktop entry đăng ký MIME application/x-msdos-program" grep -q 'application/x-msdos-program' "${DESKTOP_SRC}"
check "Desktop entry đăng ký MIME application/x-msi" grep -q 'application/x-msi' "${DESKTOP_SRC}"

# 3. Tạo thư mục tạm để kiểm thử các tình huống nhận diện file .exe / .msi
TMP_TEST_DIR="$(mktemp -d)"
# shellcheck disable=SC2064
trap 'rm -rf "${TMP_TEST_DIR}"' EXIT

touch "${TMP_TEST_DIR}/ZaloSetup-23.01.01.exe"
touch "${TMP_TEST_DIR}/GoogleChromeStandaloneSetup64.exe"
touch "${TMP_TEST_DIR}/UniKeyNT4.3RC5.exe"
touch "${TMP_TEST_DIR}/FoxitPDFReader121_L10N_Setup.exe"
touch "${TMP_TEST_DIR}/vlc-3.0.20-win64.exe"
touch "${TMP_TEST_DIR}/UltraViewer_setup_6.6.exe"
touch "${TMP_TEST_DIR}/MISA_SME_2023_Setup.msi"
touch "${TMP_TEST_DIR}/phan-mem-chuyen-dung-khong-ro.exe"

# 4. Kiểm tra trợ lý bắt và phân loại chính xác các ứng dụng phổ biến
# Dùng cờ --detect hoặc chế độ CLI không có DISPLAY
if [[ -x "${HELPER_SRC}" ]]; then
  # Zalo
  check "Nhận diện Zalo và gợi ý Zalo Web / Native" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/ZaloSetup-23.01.01.exe' | grep -qi 'zalo'"

  # Chrome
  check "Nhận diện Chrome và gợi ý Chromium / Firefox" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/GoogleChromeStandaloneSetup64.exe' | grep -qiE 'chrome|chromium|firefox'"

  # Unikey
  check "Nhận diện Unikey và gợi ý IBus Bamboo" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/UniKeyNT4.3RC5.exe' | grep -qiE 'ibus|bamboo|unikey'"

  # Foxit Reader
  check "Nhận diện Foxit Reader và gợi ý Trình xem PDF Linux" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/FoxitPDFReader121_L10N_Setup.exe' | grep -qiE 'pdf|foxit|evince'"

  # VLC
  check "Nhận diện VLC và gợi ý phiên bản VLC Linux" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/vlc-3.0.20-win64.exe' | grep -qi 'vlc'"

  # UltraViewer
  check "Nhận diện UltraViewer và gợi ý công cụ hỗ trợ từ xa OneBee" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/UltraViewer_setup_6.6.exe' | grep -qiE 'ultraviewer|onebee-ho-tro|hỗ trợ'"

  # Ứng dụng chưa nhận diện được (kế toán, app lạ): gợi ý WINE / Máy ảo / Hỗ trợ kỹ thuật
  check "Nhận diện ứng dụng Windows khác và gợi ý WINE / Hỗ trợ OneBee" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --detect '${TMP_TEST_DIR}/MISA_SME_2023_Setup.msi' | grep -qiE 'wine|kỹ thuật|máy ảo'"

  # Kiểm tra chạy chế độ CLI fallback khi không có DISPLAY mà không truyền cờ --detect (không bị treo hay crash)
  check "Chạy an toàn ở chế độ CLI fallback khi không có DISPLAY" \
    bash -c "env DISPLAY= '${HELPER_SRC}' --cli '${TMP_TEST_DIR}/ZaloSetup-23.01.01.exe'"

  # Kiểm tra phản hồi khi không có tham số đầu vào
  check "Báo lỗi hợp lệ khi không truyền file tham số" \
    bash -c "if '${HELPER_SRC}' >/dev/null 2>&1; then false; else true; fi"
else
  printf 'FAIL  File helper chưa tồn tại hoặc chưa cấp quyền +x\n'
  fails=$((fails + 1))
fi

# 5. Kiểm tra tích hợp trong desktop/onebee-install.sh
check "onebee-install.sh có bước cài đặt helper vào /usr/local/bin" \
  grep -Eq 'onebee-windows-app-helper.*(/usr/local/bin|install|cp)' "${INSTALL_SRC}"

check "onebee-install.sh có bước cài đặt desktop entry vào /usr/share/applications" \
  grep -Eq 'onebee-exe-handler.desktop.*(/usr/share/applications|install|cp)' "${INSTALL_SRC}"

check "onebee-install.sh có cập nhật MIME database hoặc xdg-mime" \
  grep -Eq 'update-desktop-database|xdg-mime' "${INSTALL_SRC}"

if [[ ${fails} -eq 0 ]]; then
  printf '\n===> TẤT CẢ CÁC BÀI TEST TASK 03 ĐÃ ĐẠT (PASS)!\n'
  exit 0
else
  printf '\n===> CÓ %d BÀI TEST THẤT BẠI (FAIL)!\n' "${fails}"
  exit 1
fi
