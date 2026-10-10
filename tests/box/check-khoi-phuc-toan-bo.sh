#!/usr/bin/env bash
# Diễn tập hỏng ổ Box (chạy trên máy test): in khóa ra "giấy" → xóa sạch dữ liệu + khóa + cấu hình Box → cài lại Box
# → onebee-box khoi-phuc-toan-bo bằng khóa đã in → mật khẩu, tài khoản, sổ hỗ trợ trở lại; máy trạm sao lưu, hỏi AI,
# nhận cập nhật như cũ mà không phải cấu hình lại. (Giữ lại model AI đã tải để test đỡ tải lại ~4 GB.)
# Cách dùng: check-khoi-phuc-toan-bo.sh <container-Box> <container-máy-trạm>
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
tram() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
S=/etc/onebee-box/secrets

# Máy đã THU HỒI trước khi hỏng ổ: sau khôi phục không được "sống lại" dù bản sao lưu còn mật khẩu cũ của máy
box "onebee-box them-may tam-01 >/dev/null && onebee-box thu-hoi-may tam-01 --dong-y >/dev/null
  ! grep -q '^tam-01:' /srv/onebee/restic/.htpasswd"

box "onebee-box in-khoa > /root/khoa-in-ra-giay.txt
  cp ${S}/webui-admin-password /root/cu-webui; cp ${S}/n8n-owner-password /root/cu-n8n; cp ${S}/ca/root.sha256 /root/cu-ca-sha
  wc -l < /srv/onebee/ho-tro/yeu-cau.csv > /root/cu-so-yeu-cau
  onebee-box sao-luu > /root/sl-truoc-hong.log 2>&1 || { tail -20 /root/sl-truoc-hong.log; exit 1; }
  docker rm -f mailpit >/dev/null 2>&1 || true
  docker compose --project-directory /opt/onebee-box down >/dev/null 2>&1
  cd /srv/onebee && ls -A | grep -vx ollama | xargs rm -rf
  rm -rf /etc/onebee-box /opt/onebee-box
  echo 'PASS  (giả lập) Hỏng ổ Box: mất hết dữ liệu, khóa bí mật, cấu hình — còn bản in khóa và ổ sao lưu'"

box "/root/onebee-test/box/onebee-box-install.sh > /root/cai-lai.log 2>&1 || { tail -30 /root/cai-lai.log; exit 1; }
  ! cmp -s ${S}/webui-admin-password /root/cu-webui || { echo 'FAIL  Cài lại mà khóa không đổi — giả lập sai'; exit 1; }
  echo 'PASS  Cài lại Box trên ổ mới (khóa bí mật mới, dữ liệu trống)'
  onebee-box khoi-phuc-toan-bo /root/khoa-in-ra-giay.txt > /root/khoi-phuc.log 2>&1 || { tail -20 /root/khoi-phuc.log; exit 1; }
  /root/onebee-test/box/onebee-box-install.sh > /root/cai-lai-2.log 2>&1 || { tail -30 /root/cai-lai-2.log; exit 1; }
  cmp -s ${S}/webui-admin-password /root/cu-webui && cmp -s ${S}/n8n-owner-password /root/cu-n8n \
    || { echo 'FAIL  Khóa bí mật không trở lại như cũ'; exit 1; }
  cmp -s ${S}/ca/root.sha256 /root/cu-ca-sha || { echo 'FAIL  CA riêng sau khôi phục khác CA cũ — máy trạm sẽ không tin Box'; exit 1; }
  openssl verify -CApath /etc/ssl/certs ${S}/ca/inter.crt >/dev/null || { echo 'FAIL  Box không tin CA đã khôi phục'; exit 1; }
  code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:3000/api/v1/auths/signin -H 'Content-Type: application/json' \
    -d \"{\\\"email\\\":\\\"quantri@onebee.lan\\\",\\\"password\\\":\\\"\$(cat /root/cu-webui)\\\"}\")
  [ \"\${code}\" = 200 ] || { echo \"FAIL  Mật khẩu quản trị Trợ lý AI cũ không dùng được (\${code})\"; exit 1; }
  for _ in \$(seq 30); do curl -s -m 5 http://127.0.0.1:5678/healthz | grep -q ok && break; sleep 3; done
  code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:5678/rest/login -H 'Content-Type: application/json' \
    -d \"{\\\"emailOrLdapLoginId\\\":\\\"quantri@onebee.lan\\\",\\\"password\\\":\\\"\$(cat /root/cu-n8n)\\\"}\")
  [ \"\${code}\" = 200 ] || { echo \"FAIL  Mật khẩu chủ n8n cũ không dùng được (\${code})\"; exit 1; }
  [ \"\$(wc -l < /srv/onebee/ho-tro/yeu-cau.csv)\" = \"\$(cat /root/cu-so-yeu-cau)\" ] || { echo 'FAIL  Mất sổ yêu cầu hỗ trợ'; exit 1; }
  onebee-box khoi-phuc-thu | tail -1
  ! grep -q '^tam-01:' /srv/onebee/restic/.htpasswd || { echo 'FAIL  Máy đã thu hồi lại có quyền vào kho HTTP sau khôi phục'; exit 1; }
  [ ! -e /srv/onebee/may-da-cap/tam-01 ] && [ -e ${S}/thu-hoi/tam-01 ] || { echo 'FAIL  Máy đã thu hồi lại được nhận báo cáo sau khôi phục'; exit 1; }
  [ -e /srv/onebee/may-da-cap/ketoan-01 ] || { echo 'FAIL  Sau khôi phục, máy ketoan-01 mất chỗ nhận báo cáo tình trạng'; exit 1; }
  echo 'PASS  khoi-phuc-toan-bo bằng khóa in ra giấy: mật khẩu, tài khoản Trợ lý AI + n8n, sổ hỗ trợ trở lại như cũ'"

# Máy trạm không cấu hình gì thêm: vẫn sao lưu (kho mới), hỏi AI (khóa cũ), báo tình trạng, nhận cập nhật (khóa SSH cũ)
tram 'onebee-sao-luu >/dev/null
  su - nhanvien -c "hoi chào bạn, trả lời 1 câu" >/dev/null 2>&1 || { echo "FAIL  hoi sau khôi phục"; exit 1; }
  onebee-bao-tinh-trang >/dev/null
  echo "PASS  Máy trạm sau khôi phục Box: sao lưu, hỏi Trợ lý AI, báo tình trạng vẫn chạy — không phải cấu hình lại"'
box 'onebee-box cap-nhat-may ketoan-01 > /root/cap-nhat-sau.log 2>&1 || { tail -20 /root/cap-nhat-sau.log; exit 1; }
  echo "PASS  Box khôi phục vẫn cập nhật được máy trạm (khóa SSH + khóa máy trạm đã ghi nhận được lấy lại)"'
