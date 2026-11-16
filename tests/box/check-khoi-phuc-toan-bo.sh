#!/usr/bin/env bash
# Diễn tập hỏng ổ Box (chạy trên máy test): in khóa ra "giấy" → xóa sạch dữ liệu + khóa + cấu hình Box → cài lại Box
# → onebee-box khoi-phuc-toan-bo bằng khóa đã in → mật khẩu, tài khoản, sổ hỗ trợ, CSDL (dòng đánh dấu) trở lại; máy trạm sao lưu, hỏi AI,
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

# Dòng đánh dấu trong CSDL (chế độ HTTP: ghi thẳng bằng psql, không qua cổng API) — phải còn nguyên sau khôi phục toàn bộ
box "dau=\"Dấu khôi phục \$(date +%s%N)\"; echo \"\${dau}\" > /root/cu-dau-csdl
  docker exec -i onebee-postgres psql -X -q -At -U postgres -d onebee -v ON_ERROR_STOP=1 -v dau=\"\${dau}\" >/dev/null <<'SQL'
INSERT INTO onebee.don_hang (khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, nguoi_tao, ghi_chu)
  VALUES ('Khách diễn tập', 'Hàng diễn tập', 1, 1, 1, 'quantri', :'dau');
SQL
  docker exec onebee-postgres psql -X -At -U postgres -d onebee -c 'SELECT count(*) FROM onebee.don_hang' > /root/cu-so-don-csdl"

box "onebee-box in-khoa > /root/khoa-in-ra-giay.txt
  cp ${S}/n8n-owner-password /root/cu-n8n; cp ${S}/ca/root.sha256 /root/cu-ca-sha
  cp /srv/onebee/ai-rag/khoa-hoi.json /root/cu-khoa-hoi.json; cp ${S}/may-ketoan-01-khoa /root/cu-khoa-may
  wc -l < /srv/onebee/ho-tro/yeu-cau.csv > /root/cu-so-yeu-cau
  onebee-box sao-luu > /root/sl-truoc-hong.log 2>&1 || { tail -20 /root/sl-truoc-hong.log; exit 1; }
  docker rm -f mailpit >/dev/null 2>&1 || true
  docker compose --project-directory /opt/onebee-box down >/dev/null 2>&1
  cd /srv/onebee && ls -A | grep -vx ollama | xargs rm -rf
  rm -rf /etc/onebee-box /opt/onebee-box
  echo 'PASS  (giả lập) Hỏng ổ Box: mất hết dữ liệu, khóa bí mật, cấu hình — còn bản in khóa và ổ sao lưu'"

box "/root/onebee-test/box/onebee-box-install.sh > /root/cai-lai.log 2>&1 || { tail -30 /root/cai-lai.log; exit 1; }
  ! cmp -s /srv/onebee/ai-rag/khoa-hoi.json /root/cu-khoa-hoi.json || { echo 'FAIL  Cài lại mà kho khóa Trợ lý AI không đổi — giả lập sai'; exit 1; }
  echo 'PASS  Cài lại Box trên ổ mới (khóa bí mật mới, dữ liệu trống)'
  onebee-box khoi-phuc-toan-bo /root/khoa-in-ra-giay.txt > /root/khoi-phuc.log 2>&1 || { tail -20 /root/khoi-phuc.log; exit 1; }
  /root/onebee-test/box/onebee-box-install.sh > /root/cai-lai-2.log 2>&1 || { tail -30 /root/cai-lai-2.log; exit 1; }
  cmp -s ${S}/n8n-owner-password /root/cu-n8n && cmp -s /srv/onebee/ai-rag/khoa-hoi.json /root/cu-khoa-hoi.json \
    || { echo 'FAIL  Khóa bí mật / kho khóa Trợ lý AI không trở lại như cũ'; exit 1; }
  cmp -s ${S}/ca/root.sha256 /root/cu-ca-sha || { echo 'FAIL  CA riêng sau khôi phục khác CA cũ — máy trạm sẽ không tin Box'; exit 1; }
  openssl verify -CApath /etc/ssl/certs ${S}/ca/inter.crt >/dev/null || { echo 'FAIL  Box không tin CA đã khôi phục'; exit 1; }
  # Khóa Trợ lý AI của máy đã cấp trước khi hỏng ổ vẫn dùng được (kho khóa khôi phục): câu hỏi rỗng → 400 = đã xác thực
  IP_AI=\$(docker inspect -f '{{range \$k, \$v := .NetworkSettings.Networks}}{{\$k}} {{\$v.IPAddress}} {{end}}' onebee-ai-rag \
    | awk '{for (i = 1; i <= NF; i += 2) if (\$i ~ /_ai\$/) {print \$(i + 1); exit}}')
  code=\$(curl -s -o /dev/null -w '%{http_code}' -H \"X-OneBee-Khoa: \$(cat ${S}/may-ketoan-01-khoa)\" -H 'Content-Type: application/json' \
    -d '{\"cau_hoi\":\"\"}' \"http://\${IP_AI}:8092/ai/hoi\")
  [ \"\${code}\" = 400 ] || { echo \"FAIL  Khóa Trợ lý AI của máy sau khôi phục không dùng được (\${code})\"; exit 1; }
  [ \"\$(docker exec onebee-postgres psql -X -q -U postgres -d onebee -Atc 'SELECT count(*) FROM onebee.tai_lieu_tri_thuc')\" -gt 0 ] \
    || { echo 'FAIL  Kho tri thức rỗng sau khôi phục toàn bộ'; exit 1; }
  echo 'PASS  Kho khóa Trợ lý AI khôi phục đúng: khóa của máy trạm cũ vẫn dùng được, kho tri thức còn nguyên'
  for _ in \$(seq 30); do curl -s -m 5 http://127.0.0.1:5678/healthz | grep -q ok && break; sleep 3; done
  code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:5678/rest/login -H 'Content-Type: application/json' \
    -d \"{\\\"emailOrLdapLoginId\\\":\\\"quantri@onebee.lan\\\",\\\"password\\\":\\\"\$(cat /root/cu-n8n)\\\"}\")
  [ \"\${code}\" = 200 ] || { echo \"FAIL  Mật khẩu chủ n8n cũ không dùng được (\${code})\"; exit 1; }
  [ \"\$(wc -l < /srv/onebee/ho-tro/yeu-cau.csv)\" = \"\$(cat /root/cu-so-yeu-cau)\" ] || { echo 'FAIL  Mất sổ yêu cầu hỗ trợ'; exit 1; }
  dau=\"\$(cat /root/cu-dau-csdl)\"
  [ \"\$(docker exec -i onebee-postgres psql -X -q -At -U postgres -d onebee -v dau=\"\${dau}\" <<<\"SELECT count(*) FROM onebee.don_hang WHERE ghi_chu = :'dau';\")\" = 1 ] \
    && [ \"\$(docker exec onebee-postgres psql -X -At -U postgres -d onebee -c 'SELECT count(*) FROM onebee.don_hang')\" = \"\$(cat /root/cu-so-don-csdl)\" ] \
    || { echo 'FAIL  Mất dòng đánh dấu / đơn hàng trong CSDL sau khôi phục toàn bộ'; exit 1; }
  docker exec onebee-cau-noi python3 -I -c \"import urllib.request; urllib.request.urlopen('http://postgrest:3001/ready', timeout=10)\" \
    || { echo 'FAIL  Dịch vụ dữ liệu (PostgREST) không nối được CSDL sau khôi phục (mật khẩu vai trò?)'; exit 1; }
  echo 'PASS  CSDL sau khôi phục toàn bộ: dòng đánh dấu ghi trước khi hỏng ổ còn nguyên, đủ số đơn hàng; PostgREST nối được CSDL'
  onebee-box khoi-phuc-thu | tail -1
  ! grep -q '^tam-01:' /srv/onebee/restic/.htpasswd || { echo 'FAIL  Máy đã thu hồi lại có quyền vào kho HTTP sau khôi phục'; exit 1; }
  [ ! -e /srv/onebee/may-da-cap/tam-01 ] && [ -e ${S}/thu-hoi/tam-01 ] || { echo 'FAIL  Máy đã thu hồi lại được nhận báo cáo sau khôi phục'; exit 1; }
  [ -e /srv/onebee/may-da-cap/ketoan-01 ] || { echo 'FAIL  Sau khôi phục, máy ketoan-01 mất chỗ nhận báo cáo tình trạng'; exit 1; }
  echo 'PASS  khoi-phuc-toan-bo bằng khóa in ra giấy: mật khẩu, tài khoản Trợ lý AI + n8n, sổ hỗ trợ trở lại như cũ'"

# Máy trạm không cấu hình gì thêm: vẫn sao lưu (kho mới), báo tình trạng, nhận cập nhật (khóa SSH cũ).
# Đường hỏi Trợ lý AI chỉ mở qua HTTPS nên kiểm ở check-https.sh (sau khôi phục, khóa máy vẫn dùng được).
tram 'onebee-sao-luu >/dev/null
  onebee-bao-tinh-trang >/dev/null
  echo "PASS  Máy trạm sau khôi phục Box: sao lưu và báo tình trạng vẫn chạy — không phải cấu hình lại"'
box 'onebee-box cap-nhat-may ketoan-01 > /root/cap-nhat-sau.log 2>&1 || { tail -20 /root/cap-nhat-sau.log; exit 1; }
  echo "PASS  Box khôi phục vẫn cập nhật được máy trạm (khóa SSH + khóa máy trạm đã ghi nhận được lấy lại)"'
