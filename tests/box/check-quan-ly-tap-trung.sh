#!/usr/bin/env bash
# Kiểm tra quản lý tập trung (chạy trên máy test, sau khi máy trạm ketoan-01 đã cài OneBee OS với cấu hình từ Box):
# máy trạm báo tình trạng → Box in bảng + cảnh báo; khóa sai/tên bậy bị chặn; Box cập nhật máy trạm qua SSH;
# SSH máy trạm chỉ nhận khóa của Box từ IP của Box, không nhận mật khẩu.
# Cách dùng: check-quan-ly-tap-trung.sh <container-Box> <container-máy-trạm>
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
TT=/srv/onebee/tinh-trang-may

# Container máy trạm không chạy systemd → bật sshd bằng tay (máy thật: ssh.socket do bộ cài bật)
tram 'mkdir -p /run/sshd && /usr/sbin/sshd
  grep -q "^from=\"$(grep -oP "^BOX_IP=\K.*" /etc/onebee/may-tram.env)\"," /var/lib/onebee-quantri/.ssh/authorized_keys
  [ "$(id -u onebee-quantri)" -lt 1000 ] && [ "$(stat -c %a /etc/sudoers.d/onebee-quantri)" = 440 ]
  sshd -T | grep -qx "passwordauthentication no" && sshd -T | grep -qx "permitrootlogin no"
  echo "PASS  Máy trạm: tài khoản quản trị của Box (ẩn, chỉ nhận khóa từ IP Box), SSH tắt đăng nhập mật khẩu và root"
  grep -q "^Exec=xdg-open http://$(grep -oP "^BOX_IP=\K.*" /etc/onebee/may-tram.env):5678/form/onebee-ho-tro$" \
    /usr/share/applications/onebee-bao-ho-tro.desktop || { echo "FAIL  Thiếu mục menu Báo cần hỗ trợ"; exit 1; }
  echo "PASS  Menu máy trạm có \"Báo cần hỗ trợ (OneBee)\" mở đúng biểu mẫu trên Box"'

tram 'onebee-bao-tinh-trang'
box "f=${TT}/ketoan-01.json; [ -s \$f ] || { echo 'FAIL  Box chưa nhận tình trạng máy trạm'; exit 1; }
  python3 -c 'import json,sys; t=json.load(open(sys.argv[1])); assert t[\"ten\"]==\"ketoan-01\" and t[\"ip\"] and t[\"o_trong_phan_tram\"]>0 and t[\"phien_ban\"], t' \$f
  echo 'PASS  Máy trạm gửi tình trạng → Box lưu (tên, IP, phiên bản, ổ trống, gói chờ cập nhật)'"

box "key=\$(cat /etc/onebee-box/secrets/tinh-trang-key)
  code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H 'X-OneBee-Key: sai' -d '{\"ten\":\"ke-gia\"}')
  [ \"\${code}\" = 403 ] || { echo \"FAIL  Khóa sai vẫn gửi được (\${code})\"; exit 1; }
  curl -s -o /dev/null -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H \"X-OneBee-Key: \${key}\" \
    -H 'Content-Type: application/json' -d '{\"ten\":\"../../etc/x\"}' || true
  [ \"\$(ls ${TT})\" = ketoan-01.json ] && [ ! -e /srv/onebee/etc ] || { echo 'FAIL  Tên máy bậy/khóa sai vẫn ghi được file'; ls -R ${TT}; exit 1; }
  echo 'PASS  Khóa sai bị chặn (403), tên máy bậy (../) không ghi được file'"

# Máy kho-02: đã cấp nhưng chưa từng sao lưu, chưa báo tình trạng → phải bị nêu tên
box 'onebee-box them-may kho-02 >/dev/null
  onebee-box may-tram > /tmp/may-tram.txt; cat /tmp/may-tram.txt
  grep -A3 "^kho-02 " /tmp/may-tram.txt | grep -q "chưa từng sao lưu" || { echo "FAIL  Không cảnh báo máy chưa sao lưu"; exit 1; }
  grep -q "^ketoan-01 .*sao lưu .*ổ trống" /tmp/may-tram.txt || { echo "FAIL  Thiếu tình trạng ketoan-01"; exit 1; }
  echo "PASS  onebee-box may-tram: nêu đúng máy chưa sao lưu (kho-02), tóm tắt máy đang ổn"'

tram 'touch /var/run/reboot-required; onebee-bao-tinh-trang >/dev/null'
box 'onebee-box may-tram | grep -A4 "^ketoan-01 " | grep -q "cần khởi động lại" || { echo "FAIL  Không báo cần khởi động lại"; exit 1; }
  echo "PASS  Máy trạm cần khởi động lại sau cập nhật → Box cảnh báo"'
tram 'rm -f /var/run/reboot-required'

box 'start=$(date +%s)
  onebee-box cap-nhat-may ketoan-01 > /tmp/cap-nhat.log 2>&1 || { tail -30 /tmp/cap-nhat.log; exit 1; }
  grep -Eq "ketoan-01 +: ok=[0-9]+ .*unreachable=0 +failed=0" /tmp/cap-nhat.log || { tail -30 /tmp/cap-nhat.log; exit 1; }
  echo "PASS  Box cập nhật máy trạm qua SSH bằng 1 lệnh ($(( $(date +%s) - start ))s)"
  if onebee-box cap-nhat-may kho-02 > /tmp/cap-nhat2.log 2>&1; then echo "FAIL  Máy chưa báo địa chỉ mà vẫn chạy"; exit 1; fi
  grep -q "chưa báo tình trạng" /tmp/cap-nhat2.log || { cat /tmp/cap-nhat2.log; exit 1; }
  echo "PASS  Máy chưa báo tình trạng (chưa biết địa chỉ) → báo rõ, không treo"'

# Khóa của Box dùng từ nơi khác (không phải IP Box) → bị từ chối; đăng nhập bằng mật khẩu → bị từ chối
docker exec "${BOX}" cat /etc/onebee-box/secrets/ssh/quan-tri | docker exec -i "${CLIENT}" bash -c 'umask 077; cat > /tmp/khoa-box'
tram 'if ssh -i /tmp/khoa-box -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 onebee-quantri@127.0.0.1 true 2>/dev/null; then
    echo "FAIL  Khóa của Box dùng được từ máy khác"; exit 1; fi
  rm -f /tmp/khoa-box
  out=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o PreferredAuthentications=password,keyboard-interactive \
        -o ConnectTimeout=5 nhanvien@127.0.0.1 true 2>&1 || true)
  grep -q "Permission denied (publickey)" <<<"${out}" || { echo "FAIL  SSH vẫn hỏi mật khẩu: ${out}"; exit 1; }
  echo "PASS  Lấy được khóa của Box cũng không vào được từ máy khác; SSH không nhận mật khẩu"'
