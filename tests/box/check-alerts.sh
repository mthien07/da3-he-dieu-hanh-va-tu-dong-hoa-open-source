#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# check-alerts.sh — Kiểm thử tính năng cảnh báo chủ động qua Telegram và Node-RED Webhook
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
TEMPLATE_ALERT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-canh-bao.sh.j2"
WORKFLOW_QUY_TRINH="${ROOT}/box/ansible/roles/box-quy-trinh/templates/flows.json.j2"
DOC_FILE="${ROOT}/docs/huong-dan/cai-dat-thong-bao-telegram.md"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

echo "=== KIỂM TRA TASK 05: CẢNH BÁO SỰ CỐ CHỦ ĐỘNG (TELEGRAM / NODE_RED) ==="

# 1. Kiểm tra các tệp cần thiết
[[ -f "${TEMPLATE_ALERT}" ]] || fail "Thiếu file template onebee-canh-bao.sh.j2"
[[ -f "${WORKFLOW_QUY_TRINH}" ]] || fail "Thiếu file workflow flows.json.j2"
[[ -f "${DOC_FILE}" ]] || fail "Thiếu tài liệu hướng dẫn cai-dat-thong-bao-telegram.md"
pass "Tất cả các tệp mã nguồn và tài liệu tồn tại"

# 2. Kiểm tra nội dung template cảnh báo
grep -q "TELEGRAM_BOT_TOKEN" "${TEMPLATE_ALERT}" || fail "Template thiếu cấu hình TELEGRAM_BOT_TOKEN"
grep -q "api.telegram.org/bot" "${TEMPLATE_ALERT}" || fail "Template thiếu lệnh gọi Telegram Bot API"
grep -q "webhook/onebee-canh-bao" "${TEMPLATE_ALERT}" || fail "Template thiếu webhook gọi sang Node-RED"
pass "Template onebee-canh-bao.sh.j2 hỗ trợ đầy đủ Telegram Bot và Node-RED Webhook"

# 3. Kiểm tra workflow Node-RED
grep -q '/webhook/onebee-canh-bao' "${WORKFLOW_QUY_TRINH}" || fail "Workflow Node-RED thiếu webhook /webhook/onebee-canh-bao"
grep -q 'fn_10_canh_bao' "${WORKFLOW_QUY_TRINH}" || fail "Workflow Node-RED thiếu hàm xử lý fn_10_canh_bao"
grep -q 'muc_do' "${WORKFLOW_QUY_TRINH}" || fail "Workflow Node-RED thiếu trường muc_do"
pass "Workflow Node-RED định dạng dữ liệu chuẩn xác cho cảnh báo đa kênh (Telegram/Email)"

# 4. Kiểm tra onebee-box.sh.j2 tích hợp lệnh
BOX_SCRIPT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-box.sh.j2"
grep -q "canh-bao)" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh canh-bao"
grep -q "dat-telegram)" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh dat-telegram"
pass "onebee-box.sh.j2 đã tích hợp lệnh canh-bao và dat-telegram"

# 5. Kiểm thử giả lập script onebee-canh-bao (render và chạy với mock HTTP)
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

RENDERED_SCRIPT="${TMP_DIR}/onebee-canh-bao"
sed 's/{{ onebee_box_ten_don_vi }}/HTX Thu Nghiem/g; s/{{ onebee_box_ports.quy_trinh }}/59999/g' "${TEMPLATE_ALERT}" > "${RENDERED_SCRIPT}"
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

# Tạo telegram.env giả
SECRETS_DIR="${TMP_DIR}/secrets"
mkdir -p "${SECRETS_DIR}"
cat > "${SECRETS_DIR}/telegram.env" <<EOF
TELEGRAM_BOT_TOKEN="mock_bot_token_123"
TELEGRAM_CHAT_ID="mock_chat_id_456"
EOF

# Thay SECRETS đường dẫn trong script chạy thử
sed -i.bak "s|SECRETS=\"/etc/onebee-box/secrets\"|SECRETS=\"${SECRETS_DIR}\"|g" "${RENDERED_SCRIPT}"

PATH="${MOCK_BIN_DIR}:${PATH}" "${RENDERED_SCRIPT}" WARN "O dia gan day" "Phan vung /data dat 88%" >/dev/null

[[ -f "${MOCK_LOG}" ]] || fail "Script không gọi lệnh curl"
grep -q "api.telegram.org/botmock_bot_token_123" "${MOCK_LOG}" || fail "Curl không gọi đúng Telegram API bot token"
grep -q "chat_id=mock_chat_id_456" "${MOCK_LOG}" || fail "Curl không gửi đúng chat_id"
grep -q "59999/webhook/onebee-canh-bao" "${MOCK_LOG}" || fail "Curl không gửi đúng webhook Node-RED cổng 59999"
grep -q "O dia gan day" "${MOCK_LOG}" || fail "Payload không chứa tiêu đề cảnh báo"
pass "Giả lập gửi cảnh báo gọi đúng Telegram Bot API và Node-RED Webhook với dữ liệu chuẩn"

echo ""
echo "===> TẤT CẢ CÁC BÀI TEST TASK 05 ĐÃ ĐẠT (PASS)!"
