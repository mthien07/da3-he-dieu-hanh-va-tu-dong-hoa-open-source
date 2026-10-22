#!/usr/bin/env bash
# cai-tu-usb-offline.sh — Tự động cài đặt OneBee Box từ gói offline (USB)
# Không cần kết nối Internet.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_TAR="${HERE}/images/onebee-docker-images.tar.gz"
REPO_DIR="${HERE}/repo"

if [[ ${EUID} -ne 0 ]]; then
  echo "LỖI: Vui lòng chạy bằng quyền quản trị (root): sudo $0" >&2
  exit 1
fi

echo "=== BẮT ĐẦU CÀI ĐẶT ONEBEE BOX TỪ GÓI OFFLINE (USB) ==="

# 1. Kiểm tra tính toàn vẹn nếu có file CHECKSUMS.sha256
if [[ -f "${HERE}/CHECKSUMS.sha256" ]] && command -v sha256sum >/dev/null 2>&1; then
  echo "--> Đang kiểm tra tính toàn vẹn gói cài đặt..."
  (cd "${HERE}" && sha256sum --check --status CHECKSUMS.sha256) || {
    echo "CẢNH BÁO: Checksum có sự khác biệt hoặc một số file bị sửa đổi. Vẫn tiếp tục cài..."
  }
fi

# 2. Nạp Docker images từ file nén
if [[ -f "${IMAGES_TAR}" ]]; then
  echo "--> Đang nạp Docker images vào hệ thống (mất 1-2 phút)..."
  gzip -dc "${IMAGES_TAR}" | docker load
  echo "✓ Đã nạp thành công các Docker images offline."
else
  echo "Lưu ý: Không tìm thấy ${IMAGES_TAR}. Bỏ qua bước nạp ảnh offline (sẽ tải online nếu có mạng)."
fi

# 3. Kích hoạt bộ cài chính của OneBee Box
INSTALL_SCRIPT="${REPO_DIR}/box/onebee-box-install.sh"
if [[ -f "${INSTALL_SCRIPT}" ]]; then
  echo "--> Khởi động bộ cài đặt OneBee Box..."
  chmod +x "${INSTALL_SCRIPT}"
  cd "${REPO_DIR}/box"
  exec ./onebee-box-install.sh "$@"
else
  echo "LỖI: Không tìm thấy kịch bản cài đặt ${INSTALL_SCRIPT}!" >&2
  exit 1
fi
