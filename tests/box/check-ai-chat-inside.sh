#!/usr/bin/env bash
# Kiểm tra chuỗi AI thật trên Box: tải model nhỏ vào Ollama → tạo tài khoản quản trị Open WebUI qua API
# → hỏi 1 câu tiếng Việt → nhận câu trả lời. Model mặc định chỉ để thử (chưa phải model chọn cho sản phẩm).
set -euo pipefail
MODEL="${ONEBEE_TEST_MODEL:-qwen2.5:0.5b}"
API=http://127.0.0.1:3000

# Chỉ trong môi trường test có proxy HTTPS tự ký: cho container Ollama tin CA của proxy
EXTRA_CA=/usr/local/share/ca-certificates/onebee-test-extra.crt
if [[ -f "${EXTRA_CA}" ]] && ! docker exec onebee-ollama test -f "${EXTRA_CA}"; then
  docker cp "${EXTRA_CA}" onebee-ollama:"${EXTRA_CA}"
  docker exec onebee-ollama update-ca-certificates >/dev/null 2>&1
  docker restart onebee-ollama >/dev/null
fi
docker exec onebee-ollama ollama pull "${MODEL}" >/dev/null 2>&1
echo "PASS  Tải model thử ${MODEL} vào Ollama"

token="$(curl -s -m 30 -X POST "${API}/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d '{"name":"Quản trị OneBee","email":"quantri@onebee.lan","password":"KiemThu-OneBee-2026"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')"
[[ -n "${token}" ]] || { echo "FAIL  Tạo tài khoản quản trị Open WebUI"; exit 1; }
echo "PASS  Tạo tài khoản quản trị đầu tiên trên Open WebUI"

if ! curl -s -m 60 "${API}/api/models" -H "Authorization: Bearer ${token}" | grep -q "${MODEL}"; then
  echo "FAIL  Open WebUI không thấy model"; exit 1
fi
echo "PASS  Open WebUI thấy model trong Ollama"

answer="$(curl -s -m 300 -X POST "${API}/api/chat/completions" -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"${MODEL}\",\"stream\":false,\"messages\":[{\"role\":\"user\",\"content\":\"Thủ đô của Việt Nam là thành phố nào? Trả lời ngắn.\"}]}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])')"
echo "Câu trả lời của AI: ${answer}"
# Chỉ kiểm chuỗi kỹ thuật chạy được (có câu trả lời tiếng Việt). Độ ĐÚNG của câu trả lời phụ thuộc model
# → chấm ở Phase 3. Model 0.5b dùng để thử từng trả lời sai "TP. Hồ Chí Minh" (28/9/2026).
grep -q "[ạảãàáâậầấẩẫăắằặẳẵêếềệểễôốồộổỗơớờợởỡưứừựửữđ]" <<<"${answer}" \
  || { echo "FAIL  Không có câu trả lời tiếng Việt"; exit 1; }
echo "PASS  Hỏi đáp tiếng Việt qua Open WebUI → Ollama chạy tại chỗ"
