#!/usr/bin/env bash
# OneBee OS Desktop — bộ cài chạy trên Linux Mint 22.x (nền Ubuntu 24.04 "noble").
# Cách dùng:  sudo ./onebee-install.sh
# Chạy lại nhiều lần an toàn: lần sau chỉ sửa những gì bị lệch so với chuẩn OneBee.
# Script cài ansible-core từ kho chính thức rồi chạy playbook tại chỗ (localhost).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYBOOK_DIR="${SCRIPT_DIR}/ansible"
LOG_DIR="/var/log/onebee"
LOG_FILE="${LOG_DIR}/install-$(date +%Y%m%d-%H%M%S).log"

log() { printf '[OneBee] %s\n' "$*"; }
die() { printf '[OneBee] LỖI: %s\n' "$*" >&2; exit 1; }

# 1. Phải chạy bằng quyền root (sudo)
[[ ${EUID} -eq 0 ]] || die "Hãy chạy bằng quyền quản trị: sudo $0"

# 2. Kiểm tra hệ điều hành: Linux Mint 22.x hoặc nền Ubuntu 24.04 (noble), 64-bit
[[ -r /etc/os-release ]] || die "Không đọc được /etc/os-release"
# shellcheck disable=SC1091
. /etc/os-release
codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
if [[ "${ID:-}" == "linuxmint" && "${VERSION_ID:-}" == 22* ]]; then
  log "Phát hiện ${PRETTY_NAME:-Linux Mint}"
elif [[ "${codename}" == "noble" ]]; then
  log "CẢNH BÁO: không phải Linux Mint (${PRETTY_NAME:-?}) — chạy trên nền Ubuntu 24.04, giao diện có thể khác"
else
  die "Chỉ hỗ trợ Linux Mint 22.x (nền Ubuntu 24.04). Máy này: ${PRETTY_NAME:-không rõ}"
fi
[[ "$(dpkg --print-architecture)" == "amd64" ]] || die "Chỉ hỗ trợ máy 64-bit (amd64)"

# 3. Không nhận tham số
[[ $# -eq 0 ]] || die "Script không nhận tham số. Cách dùng: sudo $0"

# 4. Cài ansible-core + thư viện Python mà các module apt/deb822 cần (nếu chưa có gói)
#    Máy mới cài thường đang tự cập nhật ngầm → chờ khóa dpkg tối đa 10 phút thay vì báo lỗi ngay.
export DEBIAN_FRONTEND=noninteractive
apt_opts=(-q -o DPkg::Lock::Timeout=600)
ansible_pkgs=(ansible-core python3-apt python3-debian)
if ! dpkg-query -W -f='${Status}\n' "${ansible_pkgs[@]}" 2>/dev/null | grep -c 'install ok installed' | grep -qx "${#ansible_pkgs[@]}"; then
  log "Đang cài ansible-core từ kho chính thức..."
  apt-get "${apt_opts[@]}" update
  apt-get "${apt_opts[@]}" install -y --no-install-recommends "${ansible_pkgs[@]}"
fi

# 5. Chạy playbook, ghi log
mkdir -p "${LOG_DIR}"
log "Bắt đầu cài đặt — nhật ký: ${LOG_FILE}"
cd "${PLAYBOOK_DIR}"
set +e
ANSIBLE_CONFIG="${PLAYBOOK_DIR}/ansible.cfg" ansible-playbook site.yml 2>&1 | tee "${LOG_FILE}"
status=${PIPESTATUS[0]}
set -e

if [[ ${status} -eq 0 ]]; then
  log "Hoàn tất. Hãy khởi động lại máy để áp dụng ngôn ngữ, bộ gõ tiếng Việt và giao diện."
else
  die "Cài đặt chưa xong (mã lỗi ${status}). Gửi file ${LOG_FILE} cho kỹ thuật OneBee."
fi
