#!/usr/bin/env bash
# Diễn tập hỏng ổ Box (chạy trên máy test): in khóa ra "giấy" → xóa sạch dữ liệu + khóa + cấu hình Box → cài lại Box
# → onebee-box khoi-phuc-toan-bo bằng khóa đã in → mật khẩu, tài khoản, sổ hỗ trợ, CSDL (dòng đánh dấu) trở lại; máy trạm sao lưu, hỏi AI,
# nhận cập nhật như cũ mà không phải cấu hình lại. (Giữ lại model AI đã tải để test đỡ tải lại ~4 GB.)
# Cách dùng: check-khoi-phuc-toan-bo.sh <container-Box> <container-máy-trạm>
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
box_stdin() { docker exec -i "${BOX}" bash -euo pipefail -s; }
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

# Tệp đánh dấu trong kho tệp (đối tượng trong SeaweedFS + metadata trong CSDL) — phải tải lại đúng SHA-256 sau khôi phục.
# Box đang ở chế độ HTTP nên gọi thẳng dịch vụ trong mạng Docker (tuyến /files/ chỉ tồn tại khi bật HTTPS).
box_stdin <<'EOF'
printf 'Tệp diễn tập khôi phục kho tệp\n' >/root/tep-khoi-phuc.txt
sha="$(sha256sum < /root/tep-khoi-phuc.txt | cut -d' ' -f1)"
du_lieu="$(base64 -w0 /root/tep-khoi-phuc.txt)"
docker exec -e DU_LIEU="${du_lieu}" onebee-cau-noi python3 -I -c '
import base64, os, urllib.request
du_lieu = base64.b64decode(os.environ["DU_LIEU"])
yeu_cau = urllib.request.Request("http://kho-tep:8080/tep-khoi-phuc.txt", data=du_lieu, method="PUT",
    headers={"Remote-User": "quantri", "Remote-Groups": "quan_ly",
             "Content-Type": "application/octet-stream", "Content-Length": str(len(du_lieu))})
print(urllib.request.urlopen(yeu_cau, timeout=60).read().decode())
' > /root/tep-khoi-phuc.json
id="$(python3 -c 'import json; print(json.load(open("/root/tep-khoi-phuc.json"))["tep"]["id"])')"
printf '%s %s\n' "${id}" "${sha}" > /root/tep-khoi-phuc.env
echo 'PASS  Tải 1 tệp vào kho tệp trước khi hỏng ổ (metadata ghi qua cầu nối bằng JWT, RLS)'
EOF

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

# Kho tệp sau khôi phục: metadata trong bản kết xuất CSDL + đối tượng trong thư mục SeaweedFS phải khớp lại đúng tệp đã tải lên
box_stdin <<'EOF'
id="$(cut -d' ' -f1 /root/tep-khoi-phuc.env)"; sha="$(cut -d' ' -f2 /root/tep-khoi-phuc.env)"
docker exec -e MA_TEP="${id}" onebee-cau-noi python3 -I -c '
import base64, os, urllib.request
yeu_cau = urllib.request.Request("http://kho-tep:8080/" + os.environ["MA_TEP"],
    headers={"Remote-User": "quantri", "Remote-Groups": "quan_ly"})
print(base64.b64encode(urllib.request.urlopen(yeu_cau, timeout=60).read()).decode())
' > /root/tep-khoi-phuc-tai.b64
base64 -d /root/tep-khoi-phuc-tai.b64 > /root/tep-khoi-phuc-tai.txt
[ "$(sha256sum < /root/tep-khoi-phuc-tai.txt | cut -d' ' -f1)" = "${sha}" ] \
  || { echo 'FAIL  Tệp trong kho tệp sau khôi phục khác SHA-256 bản gốc'; exit 1; }
echo 'PASS  Sau khôi phục toàn bộ: tệp trong kho tệp trở lại đúng SHA-256'
EOF

# Máy trạm không cấu hình gì thêm: vẫn sao lưu (kho mới), hỏi AI (khóa cũ), báo tình trạng, nhận cập nhật (khóa SSH cũ)
tram 'onebee-sao-luu >/dev/null
  su - nhanvien -c "hoi chào bạn, trả lời 1 câu" >/dev/null 2>&1 || { echo "FAIL  hoi sau khôi phục"; exit 1; }
  onebee-bao-tinh-trang >/dev/null
  echo "PASS  Máy trạm sau khôi phục Box: sao lưu, hỏi Trợ lý AI, báo tình trạng vẫn chạy — không phải cấu hình lại"'
box 'onebee-box cap-nhat-may ketoan-01 > /root/cap-nhat-sau.log 2>&1 || { tail -20 /root/cap-nhat-sau.log; exit 1; }
  echo "PASS  Box khôi phục vẫn cập nhật được máy trạm (khóa SSH + khóa máy trạm đã ghi nhận được lấy lại)"'
