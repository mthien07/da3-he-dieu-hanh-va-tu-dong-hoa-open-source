#!/usr/bin/env bash
# check-offline-bundle.sh — Kiểm thử bộ kịch bản đóng gói và cài đặt offline từ USB
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
DONG_GOI="${ROOT}/scripts/dong-goi-usb-offline.sh"
CAI_OFFLINE="${ROOT}/scripts/cai-tu-usb-offline.sh"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

echo "=== KIỂM TRA BỘ KỊCH BẢN ĐÓNG GÓI USB OFFLINE ==="

# 1. Kiểm tra tồn tại và quyền thực thi
[[ -x "${DONG_GOI}" ]] || fail "Script ${DONG_GOI} không có quyền thực thi"
[[ -x "${CAI_OFFLINE}" ]] || fail "Script ${CAI_OFFLINE} không có quyền thực thi"
pass "Hai script đóng gói và cài đặt offline tồn tại và có quyền thực thi"

# 2. Kiểm tra shellcheck
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -e SC2016 "${DONG_GOI}" "${CAI_OFFLINE}" || fail "Shellcheck báo lỗi trên script offline"
  pass "Shellcheck kiểm tra sạch 100%"
fi

# 3. Chạy thử nghiệm giả lập đóng gói vào thư mục tạm
TMP_DEST="$(mktemp -d)"
trap 'rm -rf "${TMP_DEST}"' EXIT

# Chạy thử đóng gói (truyền --bo-qua-docker khi chạy test tự động)
"${DONG_GOI}" "${TMP_DEST}" --bo-qua-docker >/dev/null

[[ -d "${TMP_DEST}/images" ]] || fail "Không tạo thư mục images"
[[ -d "${TMP_DEST}/repo" ]] || fail "Không tạo thư mục repo"
[[ -x "${TMP_DEST}/cai-tu-usb-offline.sh" ]] || fail "Không sao chép cai-tu-usb-offline.sh vào gói đích"
[[ -f "${TMP_DEST}/CHECKSUMS.sha256" ]] || fail "Không sinh file CHECKSUMS.sha256"
pass "Quy trình đóng gói tạo cấu trúc gói USB offline hợp lệ"

echo ""
echo "===> TẤT CẢ CÁC BÀI TEST OFFLINE BUNDLE ĐÃ ĐẠT (PASS)!"
