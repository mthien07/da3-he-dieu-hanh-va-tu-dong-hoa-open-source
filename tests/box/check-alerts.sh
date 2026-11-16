#!/usr/bin/env bash
# check-alerts.sh — Kiểm thử tính năng cảnh báo chủ động qua Telegram và động cơ quy trình (Node-RED)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
TEMPLATE_ALERT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-canh-bao.sh.j2"
FLOW_QUY_TRINH="${ROOT}/box/ansible/roles/box-quy-trinh/templates/flows.json.j2"
MODULE_QUY_TRINH="${ROOT}/box/ansible/roles/box-quy-trinh/files/onebee-quy-trinh.js"
DOC_FILE="${ROOT}/docs/huong-dan/cai-dat-thong-bao-telegram.md"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

echo "=== KIỂM TRA TASK 05: CẢNH BÁO SỰ CỐ CHỦ ĐỘNG (TELEGRAM / NODE-RED) ==="

# 1. Kiểm tra các tệp cần thiết
[[ -f "${TEMPLATE_ALERT}" ]] || fail "Thiếu file template onebee-canh-bao.sh.j2"
[[ -f "${FLOW_QUY_TRINH}" ]] || fail "Thiếu luồng mẫu flows.json.j2 của động cơ quy trình"
[[ -f "${MODULE_QUY_TRINH}" ]] || fail "Thiếu mô-đun xử lý onebee-quy-trinh.js"
[[ -f "${DOC_FILE}" ]] || fail "Thiếu tài liệu hướng dẫn cai-dat-thong-bao-telegram.md"
pass "Tất cả các tệp mã nguồn và tài liệu tồn tại"

# 2. Kiểm tra nội dung template cảnh báo
grep -q "TELEGRAM_BOT_TOKEN" "${TEMPLATE_ALERT}" || fail "Template thiếu cấu hình TELEGRAM_BOT_TOKEN"
grep -q "api.telegram.org/bot" "${TEMPLATE_ALERT}" || fail "Template thiếu lệnh gọi Telegram Bot API"
grep -q "webhook/onebee-canh-bao" "${TEMPLATE_ALERT}" || fail "Template thiếu webhook gọi sang động cơ quy trình"
grep -q "X-OneBee-Key" "${TEMPLATE_ALERT}" || fail "Template thiếu khóa X-OneBee-Key khi gọi webhook"
grep -q -- "--resolve" "${TEMPLATE_ALERT}" || fail "Template thiếu --resolve trỏ tên Box về chính Box"
pass "Template onebee-canh-bao.sh.j2 hỗ trợ đầy đủ Telegram Bot và webhook động cơ quy trình"

# 3. Kiểm tra luồng và mô-đun xử lý của động cơ quy trình
grep -q "/onebee-canh-bao" "${FLOW_QUY_TRINH}" || fail "Luồng Node-RED thiếu điểm nhận /onebee-canh-bao"
grep -q "canh-bao" "${FLOW_QUY_TRINH}" || fail "Luồng Node-RED thiếu hàm xử lý canh-bao"
grep -q "soanCanhBao" "${MODULE_QUY_TRINH}" || fail "Mô-đun quy trình thiếu hàm soạn cảnh báo"
grep -q "'canh-bao':" "${MODULE_QUY_TRINH}" || fail "Mô-đun quy trình thiếu điểm nhận canh-bao"
pass "Động cơ quy trình có điểm nhận onebee-canh-bao và hàm soạn cảnh báo đa kênh (Telegram/Email)"

# 4. Kiểm tra onebee-box.sh.j2 tích hợp lệnh
BOX_SCRIPT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-box.sh.j2"
grep -q "canh-bao)" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh canh-bao"
grep -q "dat-telegram)" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh dat-telegram"
pass "onebee-box.sh.j2 đã tích hợp lệnh canh-bao và dat-telegram"

# 5. Kiểm thử giả lập script onebee-canh-bao (render và chạy với mock HTTP)
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

RENDERED_SCRIPT="${TMP_DIR}/onebee-canh-bao"
# Render bằng Jinja như bộ cài Ansible (mẫu có cả biến đơn và biểu thức ghép tên Box)
python3 -c 'import jinja2' 2>/dev/null || { echo "Cần python3 với jinja2 (pip install -r requirements-dev.txt)"; exit 2; }
python3 - "${TEMPLATE_ALERT}" "${RENDERED_SCRIPT}" <<'PY'
import sys
from pathlib import Path
from jinja2 import Environment
nguon, dich = sys.argv[1:]
nd = Environment(keep_trailing_newline=True).from_string(Path(nguon).read_text(encoding="utf-8")).render(
    onebee_box_ten_don_vi="HTX Thu Nghiem", onebee_box_ma_don_vi="kiem-thu")
Path(dich).write_text(nd, encoding="utf-8")
PY
chmod +x "${RENDERED_SCRIPT}"

# Chạy thử với mock curl
MOCK_BIN_DIR="${TMP_DIR}/bin"
mkdir -p "${MOCK_BIN_DIR}"
MOCK_LOG="${TMP_DIR}/curl_mock.log"

cat > "${MOCK_BIN_DIR}/curl" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "${MOCK_LOG}"
exit 0
EOF
chmod +x "${MOCK_BIN_DIR}/curl"

# Tạo telegram.env giả và khóa webhook của động cơ quy trình
SECRETS_DIR="${TMP_DIR}/secrets"
mkdir -p "${SECRETS_DIR}"
cat > "${SECRETS_DIR}/telegram.env" <<EOF
TELEGRAM_BOT_TOKEN="mock_bot_token_123"
TELEGRAM_CHAT_ID="mock_chat_id_456"
EOF
printf '%s' 'khoa-thu' > "${SECRETS_DIR}/quy-trinh-webhook-key"
# Chế độ HTTPS: Box gọi webhook qua tên Box với CA riêng (mock curl chỉ ghi lại tham số, không cần chứng chỉ thật)
mkdir -p "${SECRETS_DIR}/ca"
printf '%s' 'ca-thu' > "${SECRETS_DIR}/ca/root.crt"
printf '%s' '1' > "${SECRETS_DIR}/https-da-bat"

# Thay SECRETS đường dẫn trong script chạy thử
sed -i.bak "s|SECRETS=\"/etc/onebee-box/secrets\"|SECRETS=\"${SECRETS_DIR}\"|g" "${RENDERED_SCRIPT}"

PATH="${MOCK_BIN_DIR}:${PATH}" "${RENDERED_SCRIPT}" WARN "O dia gan day" "Phan vung /data dat 88%" >/dev/null

[[ -f "${MOCK_LOG}" ]] || fail "Script không gọi lệnh curl"
grep -q "api.telegram.org/botmock_bot_token_123" "${MOCK_LOG}" || fail "Curl không gọi đúng Telegram API bot token"
grep -q "chat_id=mock_chat_id_456" "${MOCK_LOG}" || fail "Curl không gửi đúng chat_id"
grep -q "https://box.kiem-thu.onebee.internal/webhook/onebee-canh-bao" "${MOCK_LOG}" || fail "Curl không gửi đúng webhook động cơ quy trình trên tên Box"
grep -q -- "--cacert" "${MOCK_LOG}" || fail "Curl không tin CA riêng của Box"
grep -q -- "--resolve box.kiem-thu.onebee.internal:443:127.0.0.1" "${MOCK_LOG}" || fail "Curl không trỏ tên Box về chính Box"
grep -q "X-OneBee-Key: khoa-thu" "${MOCK_LOG}" || fail "Curl không gửi khóa X-OneBee-Key"
grep -q "O dia gan day" "${MOCK_LOG}" || fail "Payload không chứa tiêu đề cảnh báo"
pass "Giả lập gửi cảnh báo gọi đúng Telegram Bot API và webhook Node-RED (tên Box, CA riêng, X-OneBee-Key) với dữ liệu chuẩn"

echo ""
echo "===> TẤT CẢ CÁC BÀI TEST TASK 05 ĐÃ ĐẠT (PASS)!"
