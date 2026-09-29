#!/usr/bin/env bash
# Kiểm tra quy trình n8n trên Box (chạy trên Box bằng root, sau check-ai-chat-inside.sh):
# hộp thư giả lập Mailpit nhận email; chủ n8n tạo sẵn; nhắc hạn; nhập + tổng hợp đơn hàng; tóm tắt PDF bằng AI.
set -euo pipefail
N8N=http://127.0.0.1:5678
S=/etc/onebee-box/secrets
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY="X-OneBee-Key: $(cat ${S}/n8n-webhook-key)"
FORM_AUTH="nhanvien:$(cat ${S}/bieu-mau-nhanvien)"
subjects() { curl -s http://127.0.0.1:8025/api/v1/messages | python3 -c 'import json,sys; [print(m["Subject"]) for m in json.load(sys.stdin)["messages"]]'; }
wait_mail() { for _ in $(seq 30); do subjects | grep -q "$1" && return 0; sleep 2; done; echo "FAIL  Không nhận được email: $1"; subjects; exit 1; }

docker rm -f mailpit >/dev/null 2>&1 || true
docker run -d --name mailpit --network onebee-box_default -p 127.0.0.1:8025:8025 axllent/mailpit:latest >/dev/null
for _ in $(seq 30); do curl -s http://127.0.0.1:8025/api/v1/messages >/dev/null && break; sleep 1; done
echo "PASS  Hộp thư giả lập (Mailpit) sẵn sàng"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST ${N8N}/rest/login -H 'Content-Type: application/json' \
  -d "{\"emailOrLdapLoginId\":\"quantri@onebee.lan\",\"password\":\"$(cat ${S}/n8n-owner-password)\"}")
[[ "${code}" == 200 ]] || { echo "FAIL  Chủ n8n tạo sẵn không đăng nhập được (${code})"; exit 1; }
echo "PASS  Chủ n8n tạo sẵn đăng nhập được (không còn \"ai mở trước thành chủ\")"

onebee-box email-thu >/dev/null
wait_mail "Email thử — cấu hình email đã dùng được"
echo "PASS  onebee-box email-thu → email tới hộp thư quản trị"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST ${N8N}/webhook/onebee-nhac-han -H 'X-OneBee-Key: sai-khoa' -d '{}')
[[ "${code}" == 403 ]] || { echo "FAIL  Webhook nhận khóa sai (${code})"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' ${N8N}/form/onebee-don-hang)
[[ "${code}" == 401 ]] || { echo "FAIL  Biểu mẫu đơn hàng không đòi mật khẩu (${code})"; exit 1; }
echo "PASS  Webhook sai khóa bị chặn (403), biểu mẫu đòi mật khẩu nhân viên (401)"

curl -s -X POST ${N8N}/webhook/onebee-nhac-han -H "${KEY}" -H 'Content-Type: application/json' -d '{"hom_nay":"2026-10-17"}' >/dev/null
wait_mail "Nhắc hạn nộp: 1 việc — gần nhất còn 3 ngày"
echo "PASS  Nhắc hạn thuế: ngày 17/10 → email \"hạn 20/10, còn 3 ngày\""

curl -s -u "${FORM_AUTH}" -X POST ${N8N}/form/onebee-don-hang -F 'field-0=Siêu thị A' -F 'field-1=Xoài' \
  -F 'field-2=500' -F 'field-3=30000' -F 'field-4=2026-10-05' -F 'field-5=Giao sáng' >/dev/null
curl -s -u "${FORM_AUTH}" -X POST ${N8N}/form/onebee-don-hang -F 'field-0=Quán C' -F 'field-1=Bưởi' \
  -F 'field-2=100' -F 'field-3=25000' -F 'field-4=2026-10-06' >/dev/null
sleep 3
f="/srv/onebee/chung/don-hang/don-hang-$(date +%Y-%m).csv"
[[ "$(grep -c 'Siêu thị A\|Quán C' "${f}")" == 2 ]] || { echo "FAIL  File đơn hàng: $(cat "${f}" 2>&1)"; exit 1; }
[[ "$(stat -c %G "$(dirname "${f}")")" == onebee ]] || { echo "FAIL  Nhân viên (nhóm onebee) không đọc được thư mục đơn hàng"; exit 1; }
echo "PASS  Nhập 2 đơn qua biểu mẫu → ghi vào thư mục chung (don-hang/$(basename "${f}"))"

curl -s -X POST ${N8N}/webhook/onebee-tong-hop-don-hang -H "${KEY}" >/dev/null
wait_mail "Đơn hàng hôm nay: 2 đơn — 17.500.000 đồng"
echo "PASS  Tổng hợp đơn trong ngày → email \"2 đơn — 17.500.000 đồng\""

read -r wait_path wait_query < <(curl -s -u "${FORM_AUTH}" -X POST ${N8N}/form/onebee-tom-tat \
  -F "field-0=@${HERE}/fixtures/bao-cao-quy-3-mau.pdf;type=application/pdf" -F 'field-1=3' \
  | python3 -c 'import json,sys,urllib.parse as u; p=u.urlparse(json.load(sys.stdin)["formWaitingUrl"]); print(p.path, p.query)')
# Giống trình duyệt: hỏi trạng thái cho tới khi AI trả lời xong (mở trang chờ lúc đang chạy thì n8n giữ kết nối mãi)
st=""
for _ in $(seq 180); do
  st=$(curl -s -m 10 -u "${FORM_AUTH}" "${N8N}${wait_path}/n8n-execution-status?${wait_query}")
  [[ "${st}" == form-waiting || "${st}" == success ]] && break
  [[ "${st}" == error || "${st}" == crashed ]] && { echo "FAIL  Quy trình tóm tắt lỗi (${st})"; exit 1; }
  sleep 5
done
[[ "${st}" == form-waiting || "${st}" == success ]] || { echo "FAIL  AI tóm tắt quá 15 phút (trạng thái: ${st})"; exit 1; }
summary=$(curl -s -m 60 -u "${FORM_AUTH}" "${N8N}${wait_path}?${wait_query}" | python3 -c '
import html, re, sys
t = re.sub(r"<style.*?</style>|<script.*?</script>", "", sys.stdin.read(), flags=re.S)
print(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip())')
echo "Bản tóm tắt AI (200 ký tự đầu): ${summary:0:200}"
grep -q "xoài" <<<"${summary,,}" || { echo "FAIL  Bản tóm tắt không nói về nội dung PDF"; exit 1; }
echo "PASS  Tóm tắt PDF bằng AI nội bộ qua biểu mẫu n8n"
