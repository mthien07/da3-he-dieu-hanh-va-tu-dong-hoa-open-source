#!/usr/bin/env bash
# OneBee Box — bộ cài máy chủ nội bộ, chạy trên Ubuntu Server 24.04 LTS (64-bit).
# Cách dùng:  sudo ./onebee-box-install.sh
# Chạy lại nhiều lần an toàn (cũng là cách nâng cấp sau khi sửa box/ansible/group_vars/all.yml).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYBOOK_DIR="${SCRIPT_DIR}/ansible"
LOG_DIR="/var/log/onebee"
LOG_FILE="${LOG_DIR}/box-install-$(date +%Y%m%d-%H%M%S).log"

log() { printf '[OneBee Box] %s\n' "$*"; }
die() { printf '[OneBee Box] LỖI: %s\n' "$*" >&2; exit 1; }

[[ ${EUID} -eq 0 ]] || die "Hãy chạy bằng quyền quản trị: sudo $0"
[[ $# -eq 0 ]] || die "Script không nhận tham số. Cách dùng: sudo $0"
[[ -r /etc/os-release ]] || die "Không đọc được /etc/os-release"
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]] \
  || die "Chỉ hỗ trợ Ubuntu Server 24.04 LTS. Máy này: ${PRETTY_NAME:-không rõ}"
[[ "$(dpkg --print-architecture)" == "amd64" ]] || die "Chỉ hỗ trợ máy 64-bit (amd64)"
[[ -d /run/systemd/system ]] || die "Máy chưa chạy systemd — không cài được dịch vụ nền"

export DEBIAN_FRONTEND=noninteractive
apt_opts=(-q -o DPkg::Lock::Timeout=600)
ansible_pkgs=(ansible-core python3-apt)
if ! dpkg-query -W -f='${Status}\n' "${ansible_pkgs[@]}" 2>/dev/null | grep -c 'install ok installed' | grep -qx "${#ansible_pkgs[@]}"; then
  log "Đang cài ansible-core từ kho chính thức..."
  apt-get "${apt_opts[@]}" update
  apt-get "${apt_opts[@]}" install -y --no-install-recommends "${ansible_pkgs[@]}"
fi

mkdir -p "${LOG_DIR}"
log "Bắt đầu cài đặt (lần đầu tải khoảng vài GB image) — nhật ký: ${LOG_FILE}"
cd "${PLAYBOOK_DIR}"
set +e
ANSIBLE_CONFIG="${PLAYBOOK_DIR}/ansible.cfg" ansible-playbook site.yml 2>&1 | tee "${LOG_FILE}"
status=${PIPESTATUS[0]}
set -e

if [[ ${status} -eq 0 ]]; then
  log "Hoàn tất. Mở trình duyệt vào http://$(hostname -I | awk '{print $1}')/ để xem các dịch vụ."
  log "Việc tiếp theo: gắn ổ sao lưu rồi chạy 'sudo onebee-box khoi-phuc-thu'; cấp sao lưu cho máy trạm: 'sudo onebee-box them-may <tên>'."
else
  die "Cài đặt chưa xong (mã lỗi ${status}). Gửi file ${LOG_FILE} cho kỹ thuật OneBee."
fi
