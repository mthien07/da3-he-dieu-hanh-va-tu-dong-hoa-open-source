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
  # Lưu ra biến rồi mới grep: "sshd -T | grep -q" với pipefail có thể chết vì SIGPIPE (mã 141) khi grep thoát sớm
  t="$(sshd -T)"
  grep -qx "passwordauthentication no" <<<"${t}" && grep -qx "permitrootlogin no" <<<"${t}"
  grep -qx "allowusers onebee-quantri" <<<"${t}" && grep -qx "maxauthtries 3" <<<"${t}"
  echo "PASS  Máy trạm: tài khoản quản trị của Box (ẩn, chỉ nhận khóa từ IP Box), SSH tắt đăng nhập mật khẩu và root, chỉ cho tài khoản quản trị"
  grep -q "^Exec=xdg-open http://$(grep -oP "^BOX_IP=\K.*" /etc/onebee/may-tram.env):5678/form/onebee-ho-tro$" \
    /usr/share/applications/onebee-bao-ho-tro.desktop || { echo "FAIL  Thiếu mục menu Báo cần hỗ trợ"; exit 1; }
  echo "PASS  Menu máy trạm có \"Báo cần hỗ trợ (OneBee)\" mở đúng biểu mẫu trên Box"'

tram 'onebee-bao-tinh-trang'
box "f=${TT}/ketoan-01.json; [ -s \$f ] || { echo 'FAIL  Box chưa nhận tình trạng máy trạm'; exit 1; }
  python3 -c 'import json,sys; e=json.load(open(sys.argv[1])); assert e[\"ten\"]==\"ketoan-01\" and len(e.get(\"ky\",\"\"))==64, e; t=json.loads(e[\"du_lieu\"]); assert t[\"ip\"] and t[\"o_trong_phan_tram\"]>0 and t[\"phien_ban\"] and t[\"gui_luc\"], t' \$f
  echo 'PASS  Máy trạm gửi tình trạng CÓ CHỮ KÝ → Box lưu (tên, IP, phiên bản, ổ trống, gói chờ cập nhật)'"

box "key=\$(cat /etc/onebee-box/secrets/tinh-trang-key)
  code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H 'X-OneBee-Key: sai' -d '{\"ten\":\"ke-gia\"}')
  [ \"\${code}\" = 403 ] || { echo \"FAIL  Khóa sai vẫn gửi được (\${code})\"; exit 1; }
  curl -s -o /dev/null -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H \"X-OneBee-Key: \${key}\" \
    -H 'Content-Type: application/json' -d '{\"ten\":\"../../etc/x\"}' || true
  # Tên hợp lệ về dạng nhưng CHƯA CẤP (kẻ có khóa chung cũng không tạo được file): n8n chỉ nhận máy có file đánh dấu trong may-da-cap
  curl -s -o /dev/null -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H \"X-OneBee-Key: \${key}\" \
    -H 'Content-Type: application/json' -d \"{\\\"ten\\\":\\\"ke-gia\\\",\\\"du_lieu\\\":\\\"{}\\\",\\\"ky\\\":\\\"\$(printf '0%.0s' \$(seq 64))\\\"}\" || true
  [ \"\$(ls ${TT})\" = ketoan-01.json ] && [ ! -e /srv/onebee/etc ] || { echo 'FAIL  Tên máy bậy/khóa sai/máy chưa cấp vẫn ghi được file'; ls -R ${TT}; exit 1; }
  echo 'PASS  Khóa sai bị chặn (403); tên máy bậy (../) và máy CHƯA CẤP (kể cả có khóa chung) không ghi được file'
  # n8n lưu nguyên báo cáo của máy đã cấp nhưng Box tự kiểm chữ ký: bao bì sai chữ ký bị nêu thẳng trong bảng tình trạng
  cp ${TT}/ketoan-01.json /tmp/ketoan-01.json.tot
  curl -s -o /dev/null -X POST http://127.0.0.1:5678/webhook/onebee-tinh-trang -H \"X-OneBee-Key: \${key}\" \
    -H 'Content-Type: application/json' -d \"{\\\"ten\\\":\\\"ketoan-01\\\",\\\"du_lieu\\\":\\\"{}\\\",\\\"ky\\\":\\\"\$(printf 'a%.0s' \$(seq 64))\\\"}\" || true
  onebee-box may-tram | grep -A3 '^ketoan-01 ' | grep -q 'sai chữ ký' || { echo 'FAIL  Báo cáo sai chữ ký không bị nêu'; onebee-box may-tram; exit 1; }
  echo 'PASS  Báo cáo giả (sai chữ ký) của máy đã cấp bị Box phát hiện và nêu trong bảng tình trạng'"
tram 'onebee-bao-tinh-trang >/dev/null'   # máy báo lại bản thật

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
  grep -q "Đã ghim khóa SSH của ketoan-01" /tmp/cap-nhat.log || { echo "FAIL  Lần đầu vào máy không ghim khóa SSH sau khi chứng minh"; cat /tmp/cap-nhat.log; exit 1; }
  ssh-keygen -F ketoan-01 -f /etc/onebee-box/secrets/ssh/known_hosts >/dev/null || { echo "FAIL  Khóa SSH của máy chưa được ghim"; exit 1; }
  echo "PASS  Box cập nhật máy trạm qua SSH bằng 1 lệnh ($(( $(date +%s) - start ))s); lần đầu máy chứng minh biết mật khẩu kho sao lưu rồi mới ghim khóa SSH"
  onebee-box cap-nhat-may ketoan-01 > /tmp/cap-nhat-lan2.log 2>&1 || { tail -20 /tmp/cap-nhat-lan2.log; exit 1; }
  ! grep -q "Đã ghim khóa SSH" /tmp/cap-nhat-lan2.log || { echo "FAIL  Lần 2 lại ghim khóa"; exit 1; }
  echo "PASS  Lần 2: vào máy bằng khóa đã ghim (StrictHostKeyChecking=yes), không ghim lại"
  onebee-box dong-bo-may ketoan-01 > /tmp/dong-bo.log 2>&1 || { tail -20 /tmp/dong-bo.log; exit 1; }
  grep -Eq "ketoan-01 +: ok=[0-9]+ .*unreachable=0 +failed=0" /tmp/dong-bo.log || { tail -20 /tmp/dong-bo.log; exit 1; }
  ! grep -q "RESTIC_PASSWORD" /tmp/dong-bo.log /var/log/onebee-box/dong-bo-may-*.log || { echo "FAIL  Mật khẩu lọt vào nhật ký dong-bo-may"; exit 1; }
  echo "PASS  dong-bo-may: đẩy lại cấu hình xuống máy đã chứng minh, máy báo tình trạng thành công, nhật ký không chứa mật khẩu"
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

# Thu hồi máy: hết quyền vào kho HTTP, n8n ngừng nhận báo cáo, ghim SSH bị gỡ, máy biến khỏi bảng tình trạng; cấp lại được
box 'onebee-box thu-hoi-may kho-02 --dong-y >/dev/null
  ! grep -q "^kho-02:" /srv/onebee/restic/.htpasswd || { echo "FAIL  Máy thu hồi vẫn còn tài khoản kho HTTP"; exit 1; }
  [ ! -e /srv/onebee/may-da-cap/kho-02 ] || { echo "FAIL  Máy thu hồi vẫn còn trong danh sách n8n nhận báo cáo"; exit 1; }
  if onebee-box cap-nhat-may kho-02 >/dev/null 2>&1; then echo "FAIL  Vẫn cập nhật được máy đã thu hồi"; exit 1; fi
  ! onebee-box may-tram | grep -q "^kho-02 " || { echo "FAIL  Máy thu hồi vẫn nằm trong bảng tình trạng"; exit 1; }
  onebee-box them-may kho-02 >/dev/null
  [ -e /srv/onebee/may-da-cap/kho-02 ] || { echo "FAIL  Cấp lại máy không khôi phục chỗ nhận báo cáo"; exit 1; }
  echo "PASS  thu-hoi-may: máy hết quyền vào kho HTTP, hết chỗ báo tình trạng, không còn trong danh sách cập nhật; cấp lại được"'
