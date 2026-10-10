#!/usr/bin/env bash
# Kiểm thử OneBee Box trong container "Ubuntu 24.04 + systemd" (cần Docker, chạy --privileged để có Docker lồng).
# Các bước: cài 2 lần (idempotent) → verify 26 mục → AI hỏi đáp thật → sao lưu/khôi phục Box ra "ổ ngoài"
# → máy trạm Mint 22.3 cài OneBee OS Desktop, sao lưu lên Box + khôi phục + thử xóa bản cũ (phải bị chặn)
# → quản lý tập trung (báo tình trạng, cập nhật qua SSH) → email báo cáo → Box dọn bản cũ
# → tường lửa: máy trong LAN vào được, máy ngoài mạng cho phép bị chặn
# → diễn tập hỏng ổ Box: cài lại + khôi phục toàn bộ bằng khóa in ra giấy
# → bản giả mạo ngày tương lai bị phát hiện → chưa gắn ổ ngoài thì từ chối → khởi động lại Box, dịch vụ tự lên.
# Biến: ONEBEE_TEST_EXTRA_CA (CA proxy), ONEBEE_TEST_FULL_WEBUI=1 (dùng image Open WebUI đầy đủ thay bản slim),
#       ONEBEE_TEST_KEEP=1 (giữ container để xem lại).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE=onebee-test-ubuntu-systemd
ID="$$"; NET="onebee-test-net-${ID}"; BOX="onebee-box-test-${ID}"; CLIENT="onebee-may-tram-test-${ID}"
# Dạng ${ca_opts[@]+"${ca_opts[@]}"} bên dưới: mảng rỗng vẫn chạy với set -u trên bash 3.2 (macOS)
ca_opts=()
[[ -z "${ONEBEE_TEST_EXTRA_CA:-}" ]] || ca_opts=(-v "${ONEBEE_TEST_EXTRA_CA}:/usr/local/share/ca-certificates/onebee-test-extra.crt:ro")

cleanup() {
  [[ "${ONEBEE_TEST_KEEP:-0}" == 1 ]] && { echo "Giữ lại container ${BOX}"; return; }
  docker rm -f "${BOX}" "${CLIENT}" >/dev/null 2>&1 || true
  docker network rm "${NET}" >/dev/null 2>&1 || true
  docker volume rm "${BOX}-docker" "${BOX}-containerd" "${BOX}-sao-luu" >/dev/null 2>&1 || true
}
trap cleanup EXIT
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
# Chờ systemd khởi động xong hẳn (running hoặc degraded) — tránh đụng lúc hệ thống còn dọn /tmp
wait_systemd() {
  for _ in $(seq 60); do
    docker exec "${BOX}" timeout 5 systemctl is-system-running --wait 2>/dev/null | grep -Eq 'running|degraded' && return 0
    sleep 2
  done
  return 1
}

echo "===== Chuẩn bị máy Box giả lập ====="
docker build -q -t "${IMAGE}" -f "${REPO_ROOT}/tests/box/Dockerfile.ubuntu-systemd" "${REPO_ROOT}/tests/box" >/dev/null
docker network create "${NET}" >/dev/null
# /mnt/onebee-sao-luu là volume riêng = "ổ ngoài" khác thiết bị với /srv
docker run -d --name "${BOX}" --hostname onebee-box --network "${NET}" --privileged --cgroupns=host \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw --tmpfs /run --tmpfs /run/lock \
  -v "${BOX}-docker:/var/lib/docker" -v "${BOX}-containerd:/var/lib/containerd" \
  -v "${BOX}-sao-luu:/mnt/onebee-sao-luu" \
  -v "${REPO_ROOT}:/onebee:ro" ${ca_opts[@]+"${ca_opts[@]}"} "${IMAGE}" >/dev/null
wait_systemd
box 'update-ca-certificates >/dev/null 2>&1; rm -rf /root/onebee-test; cp -r /onebee /root/onebee-test'
if [[ "${ONEBEE_TEST_FULL_WEBUI:-0}" != 1 ]]; then
  # Bản slim (không kèm model nhúng) để test nhanh, đỡ tốn ổ; chức năng hỏi đáp như bản đầy đủ
  # Image ghim kèm digest (@sha256:…) là của bản đầy đủ → bản slim dùng tag, bỏ digest
  box "sed -i -E 's#(open_webui: .*open-webui:v[0-9.]+)(@sha256:[0-9a-f]+)?\$#\\1-slim#' /root/onebee-test/box/ansible/group_vars/all.yml"
fi
# Model AI: mặc định đúng model sản phẩm (ADR 0003); ONEBEE_TEST_MODEL=gemma3:1b để test nhanh phần kết nối.
# Tải sau khi cài (container Ollama cần tin CA proxy của môi trường test)
TEST_MODEL="${ONEBEE_TEST_MODEL:-gemma4:e2b-it-qat}"
box "sed -i -E 's#^onebee_box_ai_model: .*#onebee_box_ai_model: ${TEST_MODEL}#; s#^onebee_box_ai_models: .*#onebee_box_ai_models: []#' \
     /root/onebee-test/box/ansible/group_vars/all.yml"
# Mã đơn vị bắt buộc (CA riêng của Box); IP lấy tự động từ cổng mạng của container Box
box "sed -i -E 's#^onebee_box_ma_don_vi: .*#onebee_box_ma_don_vi: kiem-thu#' /root/onebee-test/box/ansible/group_vars/all.yml"
# Email: gửi vào hộp thư giả lập Mailpit (khởi chạy trong check-n8n-inside.sh)
box "sed -i -E 's#^  smtp_host: .*#  smtp_host: \"mailpit\"#; s#^  smtp_port: .*#  smtp_port: 1025#; s#^  smtp_starttls: .*#  smtp_starttls: false#' \
     /root/onebee-test/box/ansible/group_vars/all.yml"

echo "===== LẦN 1: cài đặt ====="
box '/root/onebee-test/box/onebee-box-install.sh > /tmp/run1.log 2>&1 || { tail -40 /tmp/run1.log; exit 1; }; tail -3 /tmp/run1.log'
box 'grep -q "Khởi động lại giám sát với cổng mới" /tmp/run1.log || { echo "FAIL  Lần cài đầu không mở giám sát theo 2 bước"; exit 1; }
     echo "PASS  Lần cài đầu: giám sát chỉ mở trong Box tới khi có tài khoản quản trị, rồi mới mở ra LAN"'
echo "===== LẦN 2: kiểm tra idempotent ====="
box '/root/onebee-test/box/onebee-box-install.sh > /tmp/run2.log 2>&1
     grep -Eq "changed=0 .*failed=0" /tmp/run2.log || { grep -B2 "changed:" /tmp/run2.log | head -30; echo "FAIL  Lần 2 còn thay đổi"; exit 1; }
     echo "PASS  Chạy lần 2 không thay đổi gì"'

echo "===== KIỂM TRA DỊCH VỤ ====="
box 'apt-get install -y -q smbclient python3 >/dev/null 2>&1; /root/onebee-test/tests/box/verify-box-install.sh'
echo "===== SSH VÀO BOX CHỈ BẰNG KHÓA ====="
box 'for i in 1 2 3; do apt-get update -q >/dev/null 2>&1 && apt-get install -y -q openssh-server >/dev/null 2>&1 && break; sleep 15; done
     systemctl enable --now ssh.socket >/dev/null 2>&1 || systemctl enable --now ssh >/dev/null 2>&1
     useradd -m -s /bin/bash kythuat
     /root/onebee-test/box/onebee-box-install.sh > /tmp/ssh1.log 2>&1 || { tail -30 /tmp/ssh1.log; exit 1; }
     mkdir -p /run/sshd; t="$(sshd -T 2>&1)"   # sshd -T cần /run/sshd (SSH kiểu socket có thể chưa tạo)
     [ ! -e /etc/ssh/sshd_config.d/10-onebee-box.conf ] && grep -qx "passwordauthentication yes" <<<"${t}" \
       || { echo "FAIL  Chưa có khóa quản trị mà đã tắt đăng nhập mật khẩu: $(ls /etc/ssh/sshd_config.d/) $(grep -iE "^passwordauth|missing|error" <<<"${t}")"; exit 1; }
     grep -q "Chưa có khóa SSH cho tài khoản quản trị Box" /tmp/ssh1.log || { echo "FAIL  Không cảnh báo chưa có khóa SSH"; exit 1; }
     echo "PASS  Chưa có khóa SSH của quản trị → giữ đăng nhập mật khẩu + cảnh báo (không tự khóa mình ở ngoài)"
     su - kythuat -c "mkdir -p ~/.ssh && ssh-keygen -q -t ed25519 -N \"\" -f ~/.ssh/id_ed25519 && cp ~/.ssh/id_ed25519.pub ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
     /root/onebee-test/box/onebee-box-install.sh > /tmp/ssh2.log 2>&1 || { tail -30 /tmp/ssh2.log; exit 1; }
     mkdir -p /run/sshd; t="$(sshd -T 2>&1)"
     grep -qx "passwordauthentication no" <<<"${t}" && grep -qx "permitrootlogin no" <<<"${t}" \
       || { echo "FAIL  Có khóa quản trị rồi mà SSH vẫn nhận mật khẩu hoặc root: $(grep -iE "^passwordauth|^permitroot|missing|error" <<<"${t}")"; exit 1; }
     su - kythuat -c "ssh -o BatchMode=yes -o StrictHostKeyChecking=no kythuat@127.0.0.1 true" \
       || { echo "FAIL  Quản trị không SSH vào Box được bằng khóa"; exit 1; }
     out=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o PreferredAuthentications=password kythuat@127.0.0.1 true 2>&1 || true)
     grep -q "Permission denied (publickey)" <<<"${out}" || { echo "FAIL  SSH vào Box vẫn nhận mật khẩu: ${out}"; exit 1; }
     echo "PASS  Có khóa quản trị → SSH vào Box chỉ bằng khóa, không cho root; quản trị vào được bằng khóa"'
echo "===== AI HỎI ĐÁP THẬT ====="
box "ONEBEE_TEST_MODEL=${TEST_MODEL} /root/onebee-test/tests/box/check-ai-chat-inside.sh"
echo "===== QUY TRÌNH n8n QUA EMAIL ====="
box '/root/onebee-test/tests/box/check-n8n-inside.sh'
echo "===== SAO LƯU BOX RA Ổ NGOÀI + KHÔI PHỤC ====="
box 'if onebee-box sao-luu > /root/sl0.log 2>&1; then echo "FAIL  sao-luu chạy khi chưa tạo kho"; exit 1; fi
     grep -q "Chưa tạo kho" /root/sl0.log || { cat /root/sl0.log; exit 1; }
     echo "PASS  Chưa tạo kho sao lưu thì sao-luu từ chối (không tự tạo kho)"
     onebee-box khoi-tao | tail -1
     onebee-box khoi-phuc-thu | tail -1 | tee /root/kp.txt; grep -q "^ĐẠT" /root/kp.txt || exit 1
     echo "PASS  Sao lưu/khôi phục Box"
     onebee-box in-khoa > /root/khoa.txt
     grep -q "^restic-box=[A-Za-z0-9]\{32\}$" /root/khoa.txt || { echo "FAIL  in-khoa"; exit 1; }
     echo "PASS  in-khoa in đủ khóa để cất ngoài Box"'

echo "===== MÁY TRẠM SAO LƯU LÊN BOX ====="
box 'onebee-box them-may ketoan-01 | grep -E "^[A-Z_]+=" > /tmp/ketoan-01.env
     [ "$(grep -c -E "^(MAY_TRAM|BOX_IP|RESTIC_REPOSITORY|RESTIC_PASSWORD|HOI_URL|HOI_API_KEY|TINH_TRANG_URL|TINH_TRANG_KEY|QUAN_TRI_SSH_KEY|BOX_CA|BOX_CA_VAN_TAY)=." /tmp/ketoan-01.env)" = 11 ] \
       || { echo "FAIL  them-may thiếu dòng cấu hình"; cat /tmp/ketoan-01.env | sed "s/=.*/=***/"; exit 1; }
     echo "PASS  Cấp cho máy ketoan-01: sao lưu, khóa Trợ lý AI, báo tình trạng, khóa SSH quản trị (11 dòng cấu hình, gồm CA riêng của Box)"'
# Máy trạm thật: Linux Mint 22.3 + bộ cài OneBee OS Desktop, có sẵn file cấu hình sao lưu lấy từ Box
docker run -d --name "${CLIENT}" --network "${NET}" -v "${REPO_ROOT}:/onebee:ro" ${ca_opts[@]+"${ca_opts[@]}"} \
  "${ONEBEE_TEST_MINT_IMAGE:-linuxmintd/mint22.3-amd64}" sleep infinity >/dev/null
docker exec -i "${CLIENT}" bash -c 'mkdir -p /etc/onebee && cat > /etc/onebee/may-tram.env' \
  < <(docker exec "${BOX}" cat /tmp/ketoan-01.env)
docker exec "${CLIENT}" bash -euo pipefail -c '
  export DEBIAN_FRONTEND=noninteractive
  if [ -f /usr/local/share/ca-certificates/onebee-test-extra.crt ]; then update-ca-certificates >/dev/null 2>&1; fi
  cp -r /onebee /root/onebee-test
  /root/onebee-test/desktop/onebee-install.sh > /root/desktop.log 2>&1 || { tail -30 /root/desktop.log; exit 1; }
  [ "$(stat -c %a /etc/onebee/may-tram.env)" = 600 ] || { echo "FAIL  Bộ cài không khóa quyền file cấu hình sao lưu"; exit 1; }
  [ -e /etc/systemd/system/timers.target.wants/onebee-sao-luu.timer ] || { echo "FAIL  Chưa bật lịch sao lưu"; exit 1; }
  echo "PASS  Cài OneBee OS Desktop trên máy trạm: tự bật lịch sao lưu, khóa quyền file cấu hình (600)"
  # CA riêng của Box được kiểm rồi cài: kho hệ thống, Firefox (chính sách), Chromium/Chrome; vân tay khớp bản Box in
  vt="$(grep -oP "^BOX_CA_VAN_TAY=\K.*" /etc/onebee/may-tram.env)"
  [ "$(openssl x509 -in /usr/local/share/ca-certificates/onebee-box-ca.crt -outform DER | sha256sum | cut -d" " -f1)" = "${vt}" ] \
    || { echo "FAIL  CA trên máy trạm không khớp vân tay Box"; exit 1; }
  grep -q onebee-box-ca.crt /etc/firefox/policies/policies.json && [ -s /etc/chromium/policies/managed/onebee-box.json ] \
    || { echo "FAIL  Thiếu chính sách CA cho Firefox/Chromium"; exit 1; }
  echo "PASS  Máy trạm tin CA riêng của Box: vân tay khớp, đã vào kho hệ thống + chính sách Firefox + Chromium"
  mkdir -p /home/nv && echo "Báo cáo quý III — Hợp tác xã OneBee" > /home/nv/bao-cao.txt
  sum=$(sha256sum < /home/nv/bao-cao.txt)
  onebee-sao-luu | tail -1
  echo "PASS  Máy trạm sao lưu /home lên Box"
  [ "$(stat -c %a /etc/onebee-hoi.conf)" = 644 ] || { echo "FAIL  Chưa tạo /etc/onebee-hoi.conf"; exit 1; }
  [ "$(stat -c %a /etc/onebee)" = 700 ] || { echo "FAIL  /etc/onebee (mật khẩu sao lưu) không còn chỉ root vào"; exit 1; }
  useradd -m nhanvien
  ans=$(su - nhanvien -c "hoi Làm sao để lưu văn bản thành file PDF?" 2>/tmp/hoi.err) \
    || { echo "FAIL  Lệnh hoi lỗi: $(cat /tmp/hoi.err)"; exit 1; }
  [ -n "${ans}" ] || { echo "FAIL  Lệnh hoi không có câu trả lời"; exit 1; }
  echo "PASS  Nhân viên trên máy trạm hỏi Trợ lý bằng lệnh hoi: ${ans:0:80}..."
  . <(grep ^HOI_ /etc/onebee-hoi.conf)
  code=$(curl -s -o /dev/null -w "%{http_code}" "${HOI_URL}/api/v1/auths/" -H "Authorization: Bearer ${HOI_API_KEY}")
  [ "${code}" = 403 ] || { echo "FAIL  Khóa máy trạm gọi được API ngoài hỏi đáp (mã ${code})"; exit 1; }
  echo "PASS  Khóa của máy trạm chỉ gọi được hỏi đáp (API khác bị chặn 403)"
  rm /home/nv/bao-cao.txt
  set -a; . <(grep ^RESTIC_ /etc/onebee/may-tram.env); set +a
  restic restore latest --target /tmp/kp --include /home/nv/bao-cao.txt >/dev/null
  [ "$(sha256sum < /tmp/kp/home/nv/bao-cao.txt)" = "${sum}" ] || { echo "FAIL  File khôi phục khác bản gốc"; exit 1; }
  echo "PASS  Máy trạm khôi phục đúng file đã xóa"
  # Tạo bản thứ 2 rồi thử xóa bản cũ: kho chỉ-thêm phải từ chối, vẫn còn đủ 2 bản
  echo "sửa đổi" >> /home/nv/ghi-chu.txt; restic backup --tag onebee-may-tram /home >/dev/null
  restic forget --keep-last 1 --prune >/dev/null 2>&1 || true
  n=$(restic snapshots --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
  [ "${n}" = 2 ] || { echo "FAIL  Máy trạm xóa được bản sao lưu cũ (còn ${n} bản)"; exit 1; }
  echo "PASS  Máy trạm KHÔNG xóa được bản sao lưu (chế độ chỉ-thêm, chống mã độc tống tiền)"'

echo "===== QUẢN LÝ TẬP TRUNG MÁY TRẠM ====="
"${REPO_ROOT}/tests/box/check-quan-ly-tap-trung.sh" "${BOX}" "${CLIENT}"
box 'onebee-box sao-luu > /root/sl.log 2>&1 || { tail -20 /root/sl.log; exit 1; }
     grep -q "onebee-may-tram" /root/sl.log || { echo "FAIL  onebee-box sao-luu không chạy chính sách dọn cho kho máy trạm"; exit 1; }
     echo "PASS  onebee-box sao-luu chạy chính sách giữ bản cho cả kho máy trạm"
     for _ in $(seq 20); do curl -s "http://127.0.0.1:8025/api/v1/search?query=ketoan-01" | grep -q "Sao lưu ĐẠT" && break; sleep 2; done
     curl -s "http://127.0.0.1:8025/api/v1/search?query=ketoan-01" | grep -q "Sao lưu ĐẠT" || { echo "FAIL  Không có email báo cáo sao lưu"; exit 1; }
     curl -s "http://127.0.0.1:8025/api/v1/search?query=kho-02" | grep -Eq "[0-9]+ máy trạm cần xử lý" \
       || { echo "FAIL  Email báo cáo không nêu máy cần xử lý (kho-02)"; exit 1; }
     echo "PASS  Sao lưu xong → email báo cáo tình trạng từng máy trạm, nêu máy cần xử lý (kho-02)"
     # Box (có mật khẩu kho, truy cập trực tiếp ổ) xóa được bản cũ — việc máy trạm bị chặn ở trên
     export RESTIC_REPOSITORY=/srv/onebee/restic/ketoan-01 RESTIC_PASSWORD="$(cat /etc/onebee-box/secrets/may-ketoan-01-repo)"
     restic forget --keep-last 1 --prune >/dev/null
     n=$(restic snapshots --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
     [ "${n}" = 1 ] || { echo "FAIL  Box không dọn được kho máy trạm (còn ${n} bản)"; exit 1; }
     echo "PASS  Box dọn được bản cũ trong kho máy trạm (máy trạm thì không)"'

echo "===== TƯỜNG LỬA: CHỈ MẠNG LAN CHO PHÉP VÀO BOX ====="
# Máy trạm cùng mạng với Box → vào được. Đổi danh sách cho phép sang mạng khác (giả lập máy trạm ở Wi-Fi khách)
# → bị chặn cả dịch vụ Docker (AI, trang giới thiệu, kho sao lưu) lẫn dịch vụ trên Box (thư mục chung).
box_ip="$(docker exec "${BOX}" hostname -I | awk '{print $1}')"
thu_cong() {  # in các cổng của Box mà máy trạm kết nối được
  docker exec "${CLIENT}" bash -c "for p in 80 3000 3001 8000 445; do timeout 3 bash -c \"exec 3<>/dev/tcp/${box_ip}/\$p\" 2>/dev/null && printf '%s ' \$p; done; true"
}
mo="$(thu_cong)"
[[ "${mo}" == "80 3000 3001 8000 445 " ]] || { echo "FAIL  Máy trạm trong LAN không vào được đủ cổng (mở: ${mo})"; exit 1; }
echo "PASS  Máy trạm trong mạng LAN vào được: trang giới thiệu, Trợ lý AI, giám sát, kho sao lưu, thư mục chung"
box 'cp /etc/onebee-box/tuong-lua.conf /root/tuong-lua.conf.bak
     echo "LAN_CHO_PHEP=\"10.255.255.0/24\"" > /etc/onebee-box/tuong-lua.conf
     systemctl restart onebee-tuong-lua'
mo="$(thu_cong)"
box 'cp /root/tuong-lua.conf.bak /etc/onebee-box/tuong-lua.conf; systemctl restart onebee-tuong-lua'
[[ -z "${mo}" ]] || { echo "FAIL  Máy ngoài mạng cho phép vẫn vào được cổng: ${mo}"; exit 1; }
echo "PASS  Máy ngoài mạng cho phép (vd Wi-Fi khách) bị chặn hết: AI, trang giới thiệu, kho sao lưu, thư mục chung"
box 'curl -s -m 10 http://127.0.0.1:3000/health | grep -q true || { echo "FAIL  Box tự gọi dịch vụ của mình bị chặn"; exit 1; }'
[[ "$(thu_cong)" == "80 3000 3001 8000 445 " ]] || { echo "FAIL  Mở lại tường lửa nhưng máy trạm chưa vào lại được"; exit 1; }
echo "PASS  Box tự gọi dịch vụ của mình không bị chặn; trả lại danh sách cũ → máy trạm vào lại được"

echo "===== TẮT TRỢ LÝ AI → LỆNH hoi BÁO LỖI DỄ HIỂU ====="
box 'compose_dir=/opt/onebee-box; docker compose --project-directory $compose_dir stop open-webui >/dev/null 2>&1'
docker exec "${CLIENT}" bash -c 'out=$(su - nhanvien -c "hoi xin chào" 2>&1); rc=$?
  [ ${rc} -ne 0 ] && grep -q "Không kết nối được OneBee Box" <<<"${out}" || { echo "FAIL  hoi khi Box tắt: ${out}"; exit 1; }
  echo "PASS  Box tắt Trợ lý → hoi báo \"Không kết nối được OneBee Box\" (không treo, không lỗi khó hiểu)"'
box 'docker compose --project-directory /opt/onebee-box start open-webui >/dev/null 2>&1'

echo "===== MÁY TRẠM SAU KHI BOX DỌN + CHỐNG BẢN GIẢ MẠO NGÀY TƯƠNG LAI ====="
docker exec "${CLIENT}" bash -euo pipefail -c '
  echo "lần 3" >> /home/nv/ghi-chu.txt; onebee-sao-luu >/dev/null
  echo "PASS  Máy trạm vẫn sao lưu được sau khi Box dọn kho"
  set -a; . <(grep ^RESTIC_ /etc/onebee/may-tram.env); set +a
  restic backup --time "2031-01-01 00:00:00" --tag gia-mao /home >/dev/null
  echo "PASS  (giả lập) Kẻ xấu tạo bản sao lưu mang ngày tương lai"'
box 'n0=$(RESTIC_REPOSITORY=/srv/onebee/restic/ketoan-01 RESTIC_PASSWORD="$(cat /etc/onebee-box/secrets/may-ketoan-01-repo)" restic snapshots --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
     onebee-box sao-luu > /root/sl2.log 2>&1 || { tail -20 /root/sl2.log; exit 1; }
     grep -q "ngày tương lai" /root/sl2.log || { echo "FAIL  Không phát hiện bản ngày tương lai"; exit 1; }
     n1=$(RESTIC_REPOSITORY=/srv/onebee/restic/ketoan-01 RESTIC_PASSWORD="$(cat /etc/onebee-box/secrets/may-ketoan-01-repo)" restic snapshots --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
     [ "${n0}" = "${n1}" ] || { echo "FAIL  Box vẫn dọn kho có bản giả mạo (${n0} → ${n1})"; exit 1; }
     echo "PASS  Box phát hiện bản ngày tương lai, KHÔNG dọn kho đó (${n1} bản giữ nguyên)"'

echo "===== HỎNG Ổ BOX → CÀI LẠI + KHÔI PHỤC TOÀN BỘ ====="
"${REPO_ROOT}/tests/box/check-khoi-phuc-toan-bo.sh" "${BOX}" "${CLIENT}"

echo "===== BẬT / TẮT HTTPS (CA riêng + Caddy) ====="
"${REPO_ROOT}/tests/box/check-https.sh" "${BOX}" "${CLIENT}"

echo "===== CHƯA GẮN Ổ SAO LƯU ====="
box 'umount /mnt/onebee-sao-luu
     if onebee-box sao-luu > /root/sl3.log 2>&1; then echo "FAIL  Vẫn sao lưu khi chưa gắn ổ"; exit 1; fi
     grep -q "Chưa gắn ổ sao lưu" /root/sl3.log || { cat /root/sl3.log; exit 1; }
     [ -z "$(ls -A /mnt/onebee-sao-luu)" ] || { echo "FAIL  Đã ghi vào ổ hệ thống"; exit 1; }
     echo "PASS  Chưa gắn ổ ngoài thì từ chối sao lưu, không ghi vào ổ hệ thống"'

echo "===== KHỞI ĐỘNG LẠI BOX ====="
docker restart "${BOX}" >/dev/null
wait_systemd
box 'for _ in $(seq 60); do curl -s -m 5 http://127.0.0.1:3000/health | grep -q true && curl -s -m 5 http://127.0.0.1:5678/healthz | grep -q ok && break; sleep 5; done
     /root/onebee-test/tests/box/verify-box-install.sh | tail -1'
echo "PASS  Sau khởi động lại, dịch vụ tự chạy lại"
echo "TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT"
