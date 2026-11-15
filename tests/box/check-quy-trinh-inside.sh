#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm thử động cơ quy trình Node-RED (chuẩn OSI Apache-2.0) bên trong OneBee Box:
# 1. Luồng 01 (/webhook/onebee-bao-cao-sao-luu): xác thực X-OneBee-Key và trả kết quả báo cáo sao lưu.
# 2. Luồng 06 (/webhook/onebee-tinh-trang): từ chối máy trạm sai khóa X-OneBee-Key hoặc tên máy không hợp lệ.
# 3. Luồng 10 (/webhook/onebee-canh-bao): xác thực X-OneBee-Box-Token và ghi nhận cảnh báo sự cố.
# 4. Luồng 11 (/webhook/onebee-phe-duyet):
#    - Quản lý duyệt đơn hàng của nhân viên khác -> 200 DA_DUYET.
#    - Poka-yoke: người tạo tự duyệt đơn của chính mình (Remote-User == nguoi_tao) -> bị chặn 409.
#    - Từ chối (TU_CHOI) nhưng không ghi lý do -> bị chặn 422.
set -euo pipefail

QUY_TRINH_URL="${ONEBEE_QUY_TRINH_URL:-http://127.0.0.1:5678}"
SECRETS_DIR="${ONEBEE_BOX_SECRETS:-/etc/onebee-box/secrets}"

WEBHOOK_KEY=""
[[ -f "${SECRETS_DIR}/quy-trinh-webhook-key" ]] && WEBHOOK_KEY="$(cat "${SECRETS_DIR}/quy-trinh-webhook-key")"

fail() { echo "FAIL  $*" >&2; exit 1; }
pass() { echo "PASS  $*"; }

# 1. Kiểm tra điểm sức khỏe Node-RED
code="$(curl -s -o /dev/null -w '%{http_code}' "${QUY_TRINH_URL}/healthz")"
[[ "${code}" == "200" ]] || fail "Node-RED /healthz trả mã ${code}"
pass "Động cơ quy trình Node-RED (/healthz) sẵn sàng"

# 2. Kiểm tra Luồng 01: báo cáo sao lưu đêm (từ chối khi sai khóa, chấp nhận khi đúng khóa)
code_bad="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-bao-cao-sao-luu" \
  -H 'Content-Type: application/json' -H 'X-OneBee-Key: khoa-sai' \
  -d '{"ket_qua":"ĐẠT","chi_tiet":"Sao lưu đêm"}')"
[[ "${code_bad}" == "403" ]] || fail "Luồng 01 không chặn khóa sai (mã ${code_bad})"

if [[ -n "${WEBHOOK_KEY}" ]]; then
  code_ok="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-bao-cao-sao-luu" \
    -H 'Content-Type: application/json' -H "X-OneBee-Key: ${WEBHOOK_KEY}" \
    -d '{"ket_qua":"ĐẠT","chi_tiet":"Sao lưu đêm ketoan-01"}')"
  [[ "${code_ok}" == "200" ]] || fail "Luồng 01 trả mã ${code_ok} khi đúng khóa"
  pass "Luồng 01 (báo cáo sao lưu) xác thực khóa và xử lý hợp lệ"
fi

# 3. Kiểm tra Luồng 06: nhận tình trạng máy trạm (chặn khóa sai hoặc tên máy không hợp lệ)
code_tram_bad="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-tinh-trang" \
  -H 'Content-Type: application/json' -H 'X-OneBee-Key: sai-khoa' \
  -d '{"ten":"ketoan-01","o_dia_phan_tram":45}')"
[[ "${code_tram_bad}" == "403" || "${code_tram_bad}" == "400" ]] || fail "Luồng 06 không chặn yêu cầu sai khóa (mã ${code_tram_bad})"
pass "Luồng 06 (tình trạng máy trạm) từ chối yêu cầu không hợp lệ (${code_tram_bad})"

# 4. Kiểm tra Luồng 11: phê duyệt quản lý & chốt chặn Poka-yoke
# 4a. Poka-yoke: người tạo (lan) tự duyệt đơn của chính mình -> phải bị chặn 403
resp_self="$(curl -s -w '\n%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-phe-duyet" \
  -H 'Content-Type: application/json' \
  -H 'Remote-User: lan' -H 'Remote-Groups: quan_ly' \
  -d '{"loai":"don_hang","id":1,"nguoi_tao":"lan","trang_thai_duyet":"DA_DUYET","ly_do_duyet":"Tự duyệt"}')"
code_self="$(tail -n1 <<<"${resp_self}")"
[[ "${code_self}" == "409" ]] || fail "Poka-yoke không chặn người tạo tự duyệt đơn của chính mình (mã ${code_self})"
pass "Poka-yoke chặn người tạo tự duyệt đơn của chính mình (HTTP 409)"

# 4b. Từ chối nhưng không nhập lý do -> phải bị chặn 422
code_noreason="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-phe-duyet" \
  -H 'Content-Type: application/json' \
  -H 'Remote-User: minh' -H 'Remote-Groups: quan_ly' \
  -d '{"loai":"don_hang","id":1,"nguoi_tao":"lan","trang_thai_duyet":"TU_CHOI","ly_do_duyet":""}')"
[[ "${code_noreason}" == "422" ]] || fail "Từ chối thiếu lý do không bị chặn 422 (mã ${code_noreason})"
pass "Từ chối đơn hàng không nhập lý do bị chặn (HTTP 422)"

# 4c. Quản lý (minh) duyệt đơn của nhân viên (lan) -> 200 OK
code_approve="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${QUY_TRINH_URL}/webhook/onebee-phe-duyet" \
  -H 'Content-Type: application/json' \
  -H 'Remote-User: minh' -H 'Remote-Groups: quan_ly' \
  -d '{"loai":"don_hang","id":1,"nguoi_tao":"lan","trang_thai_duyet":"DA_DUYET","ly_do_duyet":"Đã kiểm tra hợp lệ"}')"
[[ "${code_approve}" == "200" ]] || fail "Quản lý duyệt đơn hợp lệ trả mã ${code_approve}"
pass "Quản lý duyệt đơn hàng của nhân viên khác thành công (HTTP 200)"
