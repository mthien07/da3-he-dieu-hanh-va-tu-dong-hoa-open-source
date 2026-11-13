#!/usr/bin/env bash
# Kiểm tra Trợ lý AI thật trên Box: model Gemma nạp vào Ollama → đăng nhập tài khoản quản trị tạo sẵn
# → "Trợ lý OneBee" có lời dặn tiếng Việt → hỏi 1 câu → nhận câu trả lời tiếng Việt; đăng ký tự do đã tắt.
set -euo pipefail
MODEL="${ONEBEE_TEST_MODEL:-gemma4:e2b-it-qat}"
API=http://127.0.0.1:3000
SECRETS=/etc/onebee-box/secrets

# Chỉ trong môi trường test có proxy HTTPS tự ký: cho container Ollama tin CA của proxy
EXTRA_CA=/usr/local/share/ca-certificates/onebee-test-extra.crt
if [[ -f "${EXTRA_CA}" ]] && ! docker exec onebee-ollama test -f "${EXTRA_CA}"; then
  docker cp "${EXTRA_CA}" onebee-ollama:"${EXTRA_CA}"
  docker exec onebee-ollama update-ca-certificates >/dev/null 2>&1
  docker restart onebee-ollama >/dev/null
fi
# Mạng chập chờn → thử lại tối đa 5 lần; lỗi thì in vài dòng cuối (trước đây giấu hết, chỉ thấy EXIT=1)
for lan in 1 2 3 4 5; do
  docker exec onebee-ollama ollama pull "${MODEL}" > /tmp/ollama-pull.log 2>&1 && break
  [[ ${lan} -lt 5 ]] || { echo "FAIL  Tải model ${MODEL} (5 lần): $(tr '\r' '\n' < /tmp/ollama-pull.log | grep -v '^ *$' | tail -2)"; exit 1; }
  echo "Tải model lần ${lan} lỗi, thử lại sau 30 giây"; sleep 30
done
echo "PASS  Tải model ${MODEL} vào Ollama"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API}/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d '{"name":"Người lạ","email":"nguoila@onebee.lan","password":"KhongDuocVao-2026"}')
[[ "${code}" != 200 ]] || { echo "FAIL  Người lạ vẫn tự đăng ký được (có thể chiếm quyền quản trị)"; exit 1; }
echo "PASS  Đăng ký tự do đã tắt (người lạ nhận mã ${code})"

token="$(curl -s -m 30 -X POST "${API}/api/v1/auths/signin" -H 'Content-Type: application/json' \
  -d "{\"email\":\"quantri@onebee.lan\",\"password\":\"$(cat ${SECRETS}/webui-admin-password)\"}" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("token","") if d.get("role")=="admin" else "")')"
[[ -n "${token}" ]] || { echo "FAIL  Đăng nhập tài khoản quản trị tạo sẵn"; exit 1; }
echo "PASS  Tài khoản quản trị tạo sẵn đăng nhập được (mật khẩu trong in-khoa)"

system="$(curl -s -m 30 "${API}/api/v1/models/model?id=onebee-tro-ly" -H "Authorization: Bearer ${token}" \
  | python3 -c 'import json,sys; print((json.load(sys.stdin).get("params") or {}).get("system",""))')"
grep -q "Trợ lý OneBee" <<<"${system}" || { echo "FAIL  Chưa có Trợ lý OneBee với lời dặn"; exit 1; }
echo "PASS  Có \"Trợ lý OneBee\" với lời dặn tiếng Việt"
curl -s -m 30 "${API}/api/v1/models/model?id=onebee-tro-ly" -H "Authorization: Bearer ${token}" | python3 -c '
import json, sys
m = json.load(sys.stdin)
p, cap = m.get("params") or {}, (m.get("meta") or {}).get("capabilities") or {}
assert "{{CURRENT_DATE}}" in p.get("system", ""), "lời dặn thiếu ngày hôm nay"
assert cap.get("builtin_tools") is False, "chưa tắt công cụ có sẵn của Open WebUI"' \
  || { echo "FAIL  Trợ lý OneBee: lời dặn/công cụ chưa đúng"; exit 1; }
echo "PASS  Trợ lý biết ngày hôm nay; tắt công cụ có sẵn (web trả lời giống lệnh hoi, không gọi nhầm \"tạo lịch\")"

answer="$(curl -s -m 300 -X POST "${API}/api/chat/completions" -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' \
  -d '{"model":"onebee-tro-ly","stream":false,"messages":[{"role":"user","content":"Làm sao để lưu văn bản thành file PDF?"}]}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])')"
echo "Câu trả lời của AI (${MODEL}, 150 ký tự đầu): ${answer:0:150}"
# Chỉ kiểm chuỗi kỹ thuật chạy được (có câu trả lời tiếng Việt). Chất lượng chấm bằng tests/ai/cham-diem-model.py.
grep -q "[ạảãàáâậầấẩẫăắằặẳẵêếềệểễôốồộổỗơớờợởỡưứừựửữđ]" <<<"${answer}" \
  || { echo "FAIL  Không có câu trả lời tiếng Việt"; exit 1; }
echo "PASS  Hỏi đáp tiếng Việt qua Trợ lý OneBee → Ollama chạy tại chỗ"

pw_nv="$(python3 -c 'import secrets, string; print("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20)))')"
id_nv="$(curl -s -m 30 -X POST "${API}/api/v1/auths/add" -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Nhân viên thử\",\"email\":\"nv-thu@onebee.lan\",\"password\":\"${pw_nv}\",\"role\":\"user\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')"
[[ -n "${id_nv}" ]] || { echo "FAIL  Tạo tài khoản nhân viên thử"; exit 1; }
token_nv="$(curl -s -m 30 -X POST "${API}/api/v1/auths/signin" -H 'Content-Type: application/json' \
  -d "{\"email\":\"nv-thu@onebee.lan\",\"password\":\"${pw_nv}\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')"
[[ -n "${token_nv}" ]] || { echo "FAIL  Đăng nhập tài khoản nhân viên thử"; exit 1; }

curl -s -m 30 "${API}/api/v1/prompts/" -H "Authorization: Bearer ${token_nv}" | python3 -c '
import json, sys
ds = json.load(sys.stdin)
cmds = {p.get("command", "").lstrip("/") for p in ds if isinstance(p, dict)}
assert {"to-trinh", "bien-ban", "hop-dong", "bao-cao"} <= cmds, f"thiếu mẫu: {cmds}"' \
  || { echo "FAIL  Nhân viên chưa thấy đủ 4 mẫu soạn văn bản"; exit 1; }
echo "PASS  Nhân viên thấy đủ 4 mẫu soạn văn bản"

curl -s -m 30 "${API}/api/v1/models/model?id=onebee-tro-ly" -H "Authorization: Bearer ${token}" | python3 -c '
import json, sys
m = json.load(sys.stdin)
sp = (m.get("meta") or {}).get("suggestion_prompts") or []
assert len(sp) == 4, f"số gợi ý: {len(sp)}"' \
  || { echo "FAIL  Trợ lý OneBee chưa có đủ 4 gợi ý tiếng Việt"; exit 1; }
echo "PASS  Trợ lý OneBee có 4 gợi ý tiếng Việt"

curl -s -m 30 "${API}/api/v1/configs/banners" -H "Authorization: Bearer ${token_nv}" | python3 -c '
import json, sys
ds = json.load(sys.stdin)
assert any(isinstance(b, dict) and b.get("id") == "onebee-ai-co-the-sai" for b in ds), "thiếu băng nhắc"' \
  || { echo "FAIL  Nhân viên chưa thấy băng nhắc AI có thể sai"; exit 1; }
echo "PASS  Nhân viên thấy băng nhắc AI có thể sai"

curl -s -m 30 "${API}/api/v1/auths/admin/config" -H "Authorization: Bearer ${token}" | python3 -c '
import json, sys
cfg = json.load(sys.stdin)
ui = cfg.get("DEFAULT_INTERFACE_SETTINGS") or {}
assert ui.get("insertSuggestionPrompt") is True, "chưa bật insertSuggestionPrompt"' \
  || { echo "FAIL  Chưa bật mặc định chèn gợi ý vào ô nhập"; exit 1; }
echo "PASS  Mặc định chèn gợi ý vào ô nhập để người dùng viết tiếp"

# Bản dịch bổ sung nằm trong /api/config, đọc được cả khi chưa đăng nhập (trang đăng nhập cũng dùng)
curl -s -m 30 "${API}/api/config" | python3 -c '
import json, sys
i18n = json.load(sys.stdin).get("i18n") or {}
mong = json.load(open("/usr/local/lib/onebee-box/giao-dien-tieng-viet.json"))["vi-VN"]
vi = i18n.get("vi-VN") or {}
thieu = [k for k, v in mong.items() if vi.get(k) != v]
assert not thieu, f"thiếu bản dịch: {thieu[:5]}"' \
  || { echo "FAIL  Open WebUI chưa có bản dịch giao diện tiếng Việt bổ sung"; exit 1; }
echo "PASS  Giao diện Trợ lý có bản dịch tiếng Việt bổ sung (cả trang đăng nhập)"

curl -s -m 30 -X DELETE "${API}/api/v1/users/${id_nv}" -H "Authorization: Bearer ${token}" >/dev/null
