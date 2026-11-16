#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# kiem-bat-bien.sh — Bất biến bảo mật của OneBee Box (chạy trên Box bằng root, cả chế độ HTTP và HTTPS):
# chỉ Caddy công bố cổng; dịch vụ backend không lộ cổng; tuyến lõi (/api/, /files/, /ai/, /quy-trinh/) chỉ vào được
# sau đăng nhập một lần; trình soạn luồng không phiên thì không vào được; điểm nhận webhook tự kiểm X-OneBee-Key;
# cổng 5678 của công cụ quy trình cũ không còn mở.
# Biến môi trường: ONEBEE_HTTPS (1/0), ONEBEE_IP, ONEBEE_TEN_BOX, ONEBEE_CA.
# Cách dùng: kiem-bat-bien.sh
set -uo pipefail
fails=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; fails=$((fails + 1)); }

S=/etc/onebee-box/secrets
CA="${ONEBEE_CA:-${S}/ca/root.crt}"
HTTPS="${ONEBEE_HTTPS:-}"
if [[ -z "${HTTPS}" ]]; then
  if [[ -e "${S}/https-da-bat" ]]; then HTTPS=1; else HTTPS=0; fi
fi
IP="${ONEBEE_IP:-}"
if [[ -z "${IP}" ]]; then
  IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
fi
[[ -n "${IP}" ]] || fail "Không xác định được IP của Box (đặt ONEBEE_IP)"
TEN_BOX="${ONEBEE_TEN_BOX:-}"
if [[ -z "${TEN_BOX}" ]]; then
  TEN_BOX="$(python3 -c 'import json; print(json.load(open("/opt/onebee-box/quy-trinh/cau-hinh.json"))["api_goc"].split("://", 1)[1])' 2>/dev/null || true)"
fi
[[ -n "${TEN_BOX}" ]] || fail "Không xác định được tên Box (đặt ONEBEE_TEN_BOX)"

# ---------- 1. Chỉ Caddy công bố cổng ----------
DS="$(docker ps --filter label=com.docker.compose.project=onebee-box --format '{{.Names}}' 2>/dev/null || true)"
if [[ -z "${DS}" ]]; then
  fail "Không thấy container nào của dự án onebee-box"
else
  n=0
  for ct in ${DS}; do
    if [[ "${HTTPS}" = 0 ]]; then
      # HTTP nội bộ (chưa bật HTTPS): Caddy chưa đứng trước nên các dịch vụ người dùng vẫn tự công bố cổng của mình
      case "${ct}" in
        onebee-portal|onebee-rest-server|onebee-uptime-kuma) continue ;;
      esac
    else
      # HTTPS: Caddy là cửa duy nhất; chỉ portal (và rest-server theo thiết kế) được công bố cổng
      case "${ct}" in
        onebee-portal|onebee-rest-server) continue ;;
      esac
    fi
    n=$((n + 1))
    if [[ -z "$(docker port "${ct}" 2>/dev/null)" ]]; then
      pass "Container ${ct} không công bố cổng nào"
    else
      fail "Container ${ct} còn công bố cổng: $(docker port "${ct}")"
    fi
  done
  [[ ${n} -ge 5 ]] || fail "Chỉ kiểm được ${n} container backend (mong >= 5)"
fi

# ---------- 2. Cổng 5678 của công cụ quy trình cũ không còn ----------
if ss -Htln 2>/dev/null | awk '{print $4}' | grep -Eq ':(5678)$'; then
  fail "Cổng 5678 vẫn còn mở trên Box"
else
  pass "Cổng 5678 (công cụ quy trình cũ) không còn mở"
fi
if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -q '5678'; then
  fail "Còn container công bố cổng 5678"
else
  pass "Không container nào công bố cổng 5678"
fi

# ---------- 3. Tuyến theo chế độ ----------
if [[ "${HTTPS}" = 0 ]]; then
  # HTTP nội bộ: chỉ trang chủ + điểm nhận webhook (việc nền chạy không chờ bật HTTPS); tuyến lõi không tồn tại
  code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://${IP}/" 2>/dev/null || true)"
  if [[ "${code}" = 200 ]]; then
    pass "HTTP: Caddy phục vụ trang chủ (200)"
  else
    fail "HTTP: trang chủ trả ${code}"
  fi
  for duong in /api/ /files/ /ai/ /quy-trinh/; do
    code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://${IP}${duong}" 2>/dev/null || true)"
    if [[ "${code}" = 404 ]]; then
      pass "HTTP: ${duong} không tồn tại (404)"
    else
      fail "HTTP: ${duong} trả ${code} (mong 404)"
    fi
  done
  # Viết qua webhook không có khóa/máy chưa cấp → bị từ chối ngay tại tuyến, không ghi dữ liệu
  code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
    -d '{"ten":"kiem-bat-bien"}' "http://${IP}/webhook/onebee-tinh-trang" 2>/dev/null || true)"
  if [[ "${code}" = 403 ]]; then
    pass "HTTP: điểm nhận webhook từ chối yêu cầu không hợp lệ (403)"
  else
    fail "HTTP: /webhook/onebee-tinh-trang trả ${code} (mong 403)"
  fi
  code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://${IP}/webhook/suc-khoe" 2>/dev/null || true)"
  if [[ "${code}" = 200 ]]; then
    pass "HTTP: điểm nhận sức khỏe trả 200 (bộ cài/giám sát dùng được)"
  else
    fail "HTTP: /webhook/suc-khoe trả ${code} (mong 200)"
  fi
else
  c() { curl -s -m 10 --cacert "${CA}" --resolve "${TEN_BOX}:443:${IP}" "$@"; }
  ma_http() { c -o /dev/null -w '%{http_code}' "$@"; }
  # Gửi kèm Remote-User/Remote-Groups tự chế mà KHÔNG có phiên → Caddy xóa rồi forward_auth, phải 401
  for duong in /api/toi /files/x /quy-trinh/; do
    code="$(ma_http -H 'Accept: application/json' -H 'Remote-User: gia' -H 'Remote-Groups: quan_ly' \
      "https://${TEN_BOX}${duong}" 2>/dev/null || true)"
    if [[ "${code}" = 401 ]]; then
      pass "HTTPS: ${duong} tự gửi Remote-User mà không phiên → 401"
    else
      fail "HTTPS: ${duong} trả ${code} (mong 401)"
    fi
  done
  code="$(ma_http -X POST -H 'Accept: application/json' -H 'Remote-User: gia' -H 'Remote-Groups: quan_ly' \
    -H 'Content-Type: application/json' -d '{"cau_hoi":"thử"}' "https://${TEN_BOX}/ai/hoi" 2>/dev/null || true)"
  if [[ "${code}" = 401 ]]; then
    pass "HTTPS: /ai/hoi tự gửi Remote-User mà không phiên → 401"
  else
    fail "HTTPS: /ai/hoi trả ${code} (mong 401)"
  fi
  # Trình soạn luồng (nơi chạy mã tùy ý) không phiên: chuyển trang đăng nhập hoặc 401, không bao giờ 200
  code="$(ma_http "https://${TEN_BOX}/quy-trinh/" 2>/dev/null || true)"
  case "${code}" in
    302|303|401) pass "HTTPS: trình soạn luồng /quy-trinh/ không phiên không vào được (${code})" ;;
    *) fail "HTTPS: trình soạn luồng /quy-trinh/ trả ${code} (mong 302/401)" ;;
  esac
  if [[ -s "${S}/quy-trinh-webhook-key" ]]; then
    KEY="$(cat "${S}/quy-trinh-webhook-key")"
    code="$(ma_http -H "X-OneBee-Key: ${KEY}" "https://${TEN_BOX}/webhook/suc-khoe" 2>/dev/null || true)"
    if [[ "${code}" = 200 ]]; then
      pass "HTTPS: /webhook/suc-khoe với X-OneBee-Key đúng trả 200"
    else
      fail "HTTPS: /webhook/suc-khoe với khóa đúng trả ${code} (mong 200)"
    fi
    # Sai khóa bị từ chối tại điểm nhận có kiểm khóa (suc-khoe là điểm công khai cho bộ cài/giám sát)
    code="$(ma_http -X POST -H "X-OneBee-Key: sai" -H 'Content-Type: application/json' \
      -d '{"muc_do":"INFO","tieu_de":"kiem-bat-bien"}' "https://${TEN_BOX}/webhook/onebee-canh-bao" 2>/dev/null || true)"
    if [[ "${code}" = 403 ]]; then
      pass "HTTPS: điểm nhận có kiểm khóa từ chối X-OneBee-Key sai (403)"
    else
      fail "HTTPS: điểm nhận cảnh báo trả ${code} khi khóa sai (mong 403)"
    fi
  else
    fail "Thiếu ${S}/quy-trinh-webhook-key để kiểm điểm nhận webhook"
  fi
fi

# ---------- Kết luận ----------
echo "----"
if [[ ${fails} -eq 0 ]]; then
  echo "KẾT QUẢ: đạt tất cả bất biến bảo mật"
else
  echo "KẾT QUẢ: ${fails} bất biến KHÔNG đạt"
  exit 1
fi
