#!/usr/bin/env bash
# mo-truy-cap-tu-xa — cầu nối TẠM để kỹ thuật OneBee cài tiếp một máy mới cài hệ điều hành ở nơi khác (khác mạng, chỉ có wifi):
#   1. Tailscale (mạng riêng mã hóa, đi xuyên NAT) + Tailscale SSH: kỹ thuật SSH bằng chính tài khoản Tailscale của mình —
#      không cần gửi khóa SSH hay mật khẩu máy qua tin nhắn.
#   2. Chia sẻ màn hình có sẵn của GNOME (RDP, Ubuntu 24.04): kỹ thuật xem và điều khiển phiên đang đăng nhập, không cần ai bấm.
#      Mật khẩu RDP sinh ngẫu nhiên, chỉ root đọc được (/root/onebee-truy-cap-tu-xa.txt) → kỹ thuật SSH vào rồi tự đọc.
# Người tại máy mở Terminal TRONG phiên đang đăng nhập rồi chạy:
#   sudo bash mo-truy-cap-tu-xa.sh         bật (in đường link đăng nhập Tailscale → gửi link cho kỹ thuật)
#   sudo bash mo-truy-cap-tu-xa.sh --tat   tắt khi cài xong: gỡ chia sẻ màn hình, trả lại khóa màn hình/ngủ, rời Tailscale
# Hỗ trợ lâu dài vẫn theo ADR 0004 (onebee-ho-tro: người dùng bấm Cho phép mỗi lần) — tắt cầu nối này khi bàn giao máy.
set -euo pipefail

FILE_MAT_KHAU="${ONEBEE_TRUY_CAP_FILE:-/root/onebee-truy-cap-tu-xa.txt}"
RDP_USER=onebee

log() { printf '[OneBee] %s\n' "$*"; }
die() { printf '[OneBee] LỖI: %s\n' "$*" >&2; exit 1; }

che_do=bat
case "${1:-}" in
  "") ;;
  --tat) che_do=tat ;;
  *) die "Cách dùng: sudo bash $0 [--tat]" ;;
esac
[[ $# -le 1 ]] || die "Cách dùng: sudo bash $0 [--tat]"
# Hỗ trợ kiểm thử: ONEBEE_TEST_EUID cho phép ghi đè EUID
test_euid="${ONEBEE_TEST_EUID:-}"
check_euid=${test_euid:-${EUID}}
[[ ${check_euid} -eq 0 ]] || die "Hãy chạy bằng quyền quản trị: sudo bash $0"

# Người đang ngồi máy: người gọi sudo, không có (kỹ thuật chạy qua SSH bằng root) thì lấy chủ phiên đồ họa đang mở
nguoi="${SUDO_USER:-}"
if [[ -z "${nguoi}" || "${nguoi}" == root ]]; then
  phien="$(loginctl show-seat seat0 -p ActiveSession --value 2>/dev/null || true)"
  [[ -n "${phien}" ]] && nguoi="$(loginctl show-session "${phien}" -p Name --value 2>/dev/null || true)"
fi
[[ -n "${nguoi}" && "${nguoi}" != root ]] || die "Không tìm thấy người dùng đang đăng nhập màn hình. Đăng nhập máy rồi chạy lại trong Terminal."
uid="$(id -u "${nguoi}")" || die "Không có tài khoản ${nguoi}"
nha="$(getent passwd "${nguoi}" | cut -d: -f6)"
# Hỗ trợ kiểm thử: ONEBEE_TEST_BUS_SOCKET cho phép ghi đè đường dẫn D-Bus
bus="${ONEBEE_TEST_BUS_SOCKET:-/run/user/${uid}/bus}"

# Chạy lệnh trong phiên của người dùng (GSettings, grdctl, systemd --user cần D-Bus phiên của họ)
as_user() { runuser -u "${nguoi}" -- env XDG_RUNTIME_DIR="/run/user/${uid}" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" "$@"; }
co_gnome() { [[ -S "${bus}" ]] && command -v gnome-shell >/dev/null && as_user gsettings list-schemas 2>/dev/null | grep -qx org.gnome.desktop.screensaver; }

tat() {
  if co_gnome && command -v grdctl >/dev/null; then
    as_user grdctl rdp disable || true
    as_user grdctl rdp clear-credentials || true
    as_user systemctl --user disable --now gnome-remote-desktop.service 2>/dev/null || true
    as_user gsettings reset org.gnome.desktop.screensaver lock-enabled || true
    as_user gsettings reset org.gnome.desktop.session idle-delay || true
    as_user gsettings reset org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type || true
    # cert sắp xóa → bỏ luôn cấu hình RDP trỏ vào nó (ghi chú: cũng xóa cấu hình Chia sẻ màn hình người dùng tự đặt trước đó, nếu có)
    for k in tls-cert tls-key view-only; do as_user gsettings reset org.gnome.desktop.remote-desktop.rdp "${k}" || true; done
    rm -f "${nha}/.local/share/onebee-rdp/tls.key" "${nha}/.local/share/onebee-rdp/tls.crt"
    rmdir "${nha}/.local/share/onebee-rdp" 2>/dev/null || true
    log "Đã tắt chia sẻ màn hình, trả lại khóa màn hình và chế độ ngủ."
  fi
  rm -f "${FILE_MAT_KHAU}"
  if command -v tailscale >/dev/null; then
    tailscale set --ssh=false 2>/dev/null || true
    tailscale logout 2>/dev/null || true
    log "Đã rời mạng Tailscale (kết nối của kỹ thuật ngắt ngay)."
  fi
  log "Xong. Kỹ thuật không còn vào được máy này."
}

[[ "${che_do}" == tat ]] && { tat; exit 0; }

# Hỗ trợ kiểm thử: ONEBEE_TEST_OS_RELEASE cho phép dùng file /etc/os-release giả
os_release_file="${ONEBEE_TEST_OS_RELEASE:-/etc/os-release}"
[[ -r "${os_release_file}" ]] || die "Không đọc được ${os_release_file}"
# shellcheck disable=SC1091,SC1090
. "${os_release_file}"
codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
[[ "${ID:-}" == ubuntu || " ${ID_LIKE:-} " == *" ubuntu "* ]] && [[ "${codename}" == noble ]] \
  || die "Chỉ hỗ trợ Ubuntu 24.04 / Linux Mint 22 (nền noble). Máy này: ${PRETTY_NAME:-không rõ}"
[[ "$(dpkg --print-architecture)" == amd64 ]] || die "Chỉ hỗ trợ máy 64-bit (amd64)"

export DEBIAN_FRONTEND=noninteractive
apt_opts=(-q -o DPkg::Lock::Timeout=600)

# 1. Tailscale từ kho chính thức (khóa ký riêng cho kho, không tin chung toàn hệ thống)
if ! command -v tailscale >/dev/null; then
  log "Đang cài Tailscale..."
  apt-get "${apt_opts[@]}" install -y --no-install-recommends curl ca-certificates >/dev/null
  install -d -m 0755 /usr/share/keyrings
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg" -o /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list" -o /etc/apt/sources.list.d/tailscale.list
  apt-get "${apt_opts[@]}" update >/dev/null
  apt-get "${apt_opts[@]}" install -y tailscale >/dev/null
fi
systemctl enable --now tailscaled >/dev/null
if tailscale ip -4 >/dev/null 2>&1; then
  tailscale set --ssh
else
  log "Bước quan trọng: ngay dưới đây hiện một đường link https://login.tailscale.com/... → GỬI LINK ĐÓ cho kỹ thuật OneBee qua Zalo."
  log "Kỹ thuật mở link bằng tài khoản Tailscale của mình là máy vào mạng. Cửa sổ này chờ đến khi xong — đừng đóng."
  tailscale up --ssh
fi
ip_ts="$(tailscale ip -4 2>/dev/null | head -n1 || true)"   # vừa vào tailnet có thể chưa có IP ngay — không dừng ở đây

# 2. Chia sẻ màn hình GNOME (RDP). Không phải GNOME (vd Mint Cinnamon) thì chỉ có SSH.
# grdctl ở chế độ người dùng cất mật khẩu RDP vào keyring "login" của GNOME: keyring đang khóa (máy tự đăng nhập, không gõ
# mật khẩu) thì grdctl hiện hộp thoại đòi mật khẩu hoặc lỗi → chờ tối đa 2 phút rồi bỏ qua RDP, vẫn giữ Tailscale SSH.
# Chỉ tắt khóa màn hình và ghi file mật khẩu SAU KHI đặt được mật khẩu RDP.
bat_man_hinh() {
  apt-get "${apt_opts[@]}" install -y --no-install-recommends gnome-remote-desktop openssl >/dev/null || return 1
  local thu_muc="${nha}/.local/share/onebee-rdp" mat_khau
  as_user install -d -m 0700 "${thu_muc}" || return 1
  as_user openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=onebee-$(hostname)" \
    -keyout "${thu_muc}/tls.key" -out "${thu_muc}/tls.crt" 2>/dev/null || return 1
  mat_khau="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-16)"
  as_user grdctl rdp set-tls-key "${thu_muc}/tls.key" 2>/dev/null || return 1
  as_user grdctl rdp set-tls-cert "${thu_muc}/tls.crt" 2>/dev/null || return 1
  log "Nếu máy hiện hộp thoại hỏi mật khẩu \"keyring\" / \"Login\": gõ mật khẩu đăng nhập máy rồi bấm Mở khóa."
  timeout 120 runuser -u "${nguoi}" -- env XDG_RUNTIME_DIR="/run/user/${uid}" DBUS_SESSION_BUS_ADDRESS="unix:path=${bus}" \
    grdctl rdp set-credentials "${RDP_USER}" "${mat_khau}" >/dev/null 2>&1 || return 2
  as_user grdctl rdp disable-view-only || return 1
  as_user grdctl rdp enable || return 1
  as_user systemctl --user enable --now gnome-remote-desktop.service >/dev/null 2>&1 || true
  # Kỹ thuật vào lúc không ai ngồi máy: không khóa màn hình, không tắt màn hình, cắm điện thì không ngủ (--tat trả lại)
  as_user gsettings set org.gnome.desktop.screensaver lock-enabled false || true
  as_user gsettings set org.gnome.desktop.session idle-delay 'uint32 0' || true
  as_user gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' || true
  (umask 077; printf 'RDP (chia sẻ màn hình của %s)\nĐịa chỉ: %s:3389\nTài khoản: %s\nMật khẩu: %s\n' \
    "${nguoi}" "${ip_ts:-<IP Tailscale>}" "${RDP_USER}" "${mat_khau}" >"${FILE_MAT_KHAU}")
}

man_hinh="chưa bật (không phải phiên GNOME — dùng SSH; sau khi cài OneBee Desktop dùng onebee-ho-tro)"
if co_gnome; then
  ma=0
  bat_man_hinh || ma=$?
  case "${ma}" in
    0) man_hinh="RDP ${ip_ts:-<IP Tailscale>}:3389 — mật khẩu: kỹ thuật SSH vào rồi chạy: sudo cat ${FILE_MAT_KHAU}" ;;
    2) man_hinh="CHƯA BẬT — keyring GNOME đang khóa (máy tự đăng nhập?). Đăng xuất, đăng nhập lại bằng mật khẩu rồi chạy lại script; SSH vẫn dùng được" ;;
    *) man_hinh="CHƯA BẬT — lỗi khi bật chia sẻ màn hình; SSH vẫn dùng được, kỹ thuật xem: grdctl status" ;;
  esac
fi

cat <<EOF

[OneBee] ĐÃ MỞ TRUY CẬP TỪ XA. Gửi cho kỹ thuật dòng này (không chứa mật khẩu):
   Máy: $(hostname)   IP Tailscale: ${ip_ts:-chưa có}
Kỹ thuật vào:
   SSH:        tailscale ssh ${nguoi}@$(hostname)   (hoặc root@ khi cần cài đặt)
   Màn hình:   ${man_hinh}
Đừng đăng xuất khỏi máy (chia sẻ màn hình dùng phiên đang mở). Cài xong: sudo bash $0 --tat
EOF
