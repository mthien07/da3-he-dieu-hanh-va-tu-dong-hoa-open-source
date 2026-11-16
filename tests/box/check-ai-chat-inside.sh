#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Kiểm tra Trợ lý AI thật trên Box: tải model trả lời + model nhúng → nạp kho tri thức vào PostgreSQL
# → cấp khóa tạm → hỏi qua đường /ai/hoi (Caddy khi đã bật HTTPS, dịch vụ khi còn HTTP) → có câu trả lời tiếng Việt
# kèm nguồn tham khảo và dòng nhắc kiểm tra → khóa sai/thiếu bị từ chối, đường khác 404 → thu hồi khóa tạm.
set -euo pipefail
MODEL="${ONEBEE_TEST_MODEL:-gemma4:e2b-it-qat}"
EMBED="${ONEBEE_TEST_EMBED_MODEL:-nomic-embed-text:v1.5}"
SECRETS=/etc/onebee-box/secrets
GV=/root/onebee-test/box/ansible/group_vars/all.yml

# Chỉ trong môi trường test có proxy HTTPS tự ký: cho container Ollama tin CA của proxy
EXTRA_CA=/usr/local/share/ca-certificates/onebee-test-extra.crt
if [[ -f "${EXTRA_CA}" ]] && ! docker exec onebee-ollama test -f "${EXTRA_CA}"; then
  docker cp "${EXTRA_CA}" onebee-ollama:"${EXTRA_CA}"
  docker exec onebee-ollama update-ca-certificates >/dev/null 2>&1
  docker restart onebee-ollama >/dev/null
fi

pull_model() {
  local ten="$1" lan
  for lan in 1 2 3 4 5; do
    docker exec onebee-ollama ollama pull "${ten}" > /tmp/ollama-pull.log 2>&1 && return 0
    [[ ${lan} -lt 5 ]] || { echo "FAIL  Tải model ${ten} (5 lần): $(tr '\r' '\n' < /tmp/ollama-pull.log | grep -v '^ *$' | tail -2)"; exit 1; }
    echo "Tải model ${ten} lần ${lan} lỗi, thử lại sau 30 giây"; sleep 30
  done
}
pull_model "${MODEL}"
pull_model "${EMBED}"
echo "PASS  Tải model trả lời ${MODEL} và model nhúng ${EMBED} vào Ollama"

onebee-box nap-tri-thuc > /tmp/nap-tri-thuc.log 2>&1 || { tail -20 /tmp/nap-tri-thuc.log; echo "FAIL  Nạp kho tri thức"; exit 1; }
so_doan="$(docker exec onebee-postgres psql -X -q -U postgres -d onebee -Atc 'SELECT count(*) FROM onebee.tai_lieu_tri_thuc')"
[[ "${so_doan}" =~ ^[0-9]+$ && "${so_doan}" -gt 0 ]] || { echo "FAIL  Kho tri thức rỗng sau khi nạp"; exit 1; }
echo "PASS  Nạp ${so_doan} đoạn tri thức vào PostgreSQL"

khoa="$(onebee-box cap-khoa-hoi kiem-thu 2>/dev/null)"
[[ "${khoa}" =~ ^obk-[0-9a-f]{48}$ ]] || { echo "FAIL  Không cấp được khóa tạm cho kiểm thử"; exit 1; }
don_khoa() { onebee-box go-khoa-hoi kiem-thu >/dev/null 2>&1 || true; }
trap don_khoa EXIT
echo "PASS  Cấp khóa Trợ lý AI tạm cho kiểm thử (thu hồi khi xong)"

# Gọi /ai/hoi. HTTPS đã bật: đi đúng đường người dùng (Caddy + CA riêng, khóa API miễn đăng nhập một lần).
# Còn HTTP: gọi thẳng dịch vụ trong container (tuyến /ai/ chỉ tồn tại ở chế độ HTTPS).
if [[ -e "${SECRETS}/https-da-bat" ]]; then
  TEN="box.$(sed -n 's/^onebee_box_ma_don_vi: *//p' "${GV}" | tr -d '"').onebee.internal"
  IP="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") {print $(i + 1); exit}}')"
  goi_ai() {
    local duong_dan="$1" khoa_dung="$2" tep="$3"
    local -a td=(-H 'Content-Type: application/json' -H 'Accept: application/json')
    [[ -z "${khoa_dung}" ]] || td+=(-H "X-OneBee-Khoa: ${khoa_dung}")
    curl -s -o "${tep}" -w '%{http_code}' --cacert "${SECRETS}/ca/root.crt" --resolve "${TEN}:443:${IP}" \
      "${td[@]}" -d '{"cau_hoi":"Thể thức văn bản hành chính gồm những gì?"}' "https://${TEN}${duong_dan}"
  }
else
  goi_ai() {
    local duong_dan="$1" khoa_dung="$2" tep="$3" kq
    kq="$(AI_DUONG="${duong_dan}" AI_KHOA="${khoa_dung}" docker exec -e AI_DUONG -e AI_KHOA onebee-ai-rag python3 -I -c '
import json, os, sys, urllib.error, urllib.request
td = {"Content-Type": "application/json"}
if os.environ.get("AI_KHOA"):
    td["X-OneBee-Khoa"] = os.environ["AI_KHOA"]
req = urllib.request.Request("http://127.0.0.1:8092" + os.environ["AI_DUONG"],
                             data=json.dumps({"cau_hoi": "Thể thức văn bản hành chính gồm những gì?"}).encode(),
                             headers=td)
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        print(r.status); sys.stdout.write(r.read().decode())
except urllib.error.HTTPError as e:
    print(e.code); sys.stdout.write(e.read().decode())
')"
    printf '%s' "${kq#*$'\n'}" > "${tep}"
    printf '%s' "${kq%%$'\n'*}"
  }
fi

ma="$(goi_ai /ai/hoi "${khoa}" /tmp/ai-tra-loi.json)"
[[ "${ma}" = 200 ]] || { cat /tmp/ai-tra-loi.json; echo "FAIL  /ai/hoi trả mã ${ma}"; exit 1; }
python3 - /tmp/ai-tra-loi.json <<'PY' || exit 1
import json, re, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
tl = d.get("tra_loi") or ""
assert re.search(r"[ạảãàáâậầấẩẫăắằặẳẵêếềệểễôốồộổỗơớờợởỡưứừựửữđ]", tl), "câu trả lời không phải tiếng Việt"
assert "kiểm tra lại" in tl.lower(), "thiếu dòng nhắc kiểm tra lại"
assert d.get("nguon"), "không trích được nguồn từ kho tri thức"
PY
echo "PASS  /ai/hoi trả câu trả lời tiếng Việt, có nguồn tham khảo và dòng nhắc kiểm tra lại"

ma="$(goi_ai /ai/hoi "" /tmp/ai-khong-khoa.json)"
[[ "${ma}" = 401 ]] || { echo "FAIL  /ai/hoi không có khóa mà không bị từ chối (mã ${ma})"; exit 1; }
echo "PASS  /ai/hoi thiếu khóa bị từ chối (401)"

ma="$(goi_ai /ai/api/chat "${khoa}" /tmp/ai-duong-khac.json)"
[[ "${ma}" = 404 ]] || { echo "FAIL  Đường khác dưới /ai/ không trả 404 (mã ${ma})"; exit 1; }
echo "PASS  Đường khác dưới /ai/ trả 404"

ma="$(goi_ai /ai/hoi "obk-$(printf '0%.0s' $(seq 48))" /tmp/ai-khoa-sai.json)"
[[ "${ma}" = 401 ]] || { echo "FAIL  Khóa sai không bị từ chối (mã ${ma})"; exit 1; }
echo "PASS  Khóa Trợ lý AI sai bị từ chối (401)"

echo "PASS  Trợ lý AI chạy thật trên Box: nạp tri thức, hỏi đáp có nguồn, khóa API riêng từng người"
