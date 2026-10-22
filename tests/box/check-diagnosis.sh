#!/usr/bin/env bash
# shellcheck disable=SC2016  # thân các lệnh giả viết trong nháy đơn: biến phải mở rộng lúc lệnh giả chạy, không phải lúc tạo
# Kiểm thử lệnh "onebee-box chan-doan" (7 hạng mục: mạng, tài nguyên, Docker, Trợ lý AI, Samba, sao lưu, chứng chỉ) mà KHÔNG cần Box thật:
# dựng các mẫu .j2 thành lệnh trong thư mục tạm, thay ping/ip/docker/systemctl/restic/mountpoint/runuser/df/tailscale bằng bản GIẢ
# (trạng thái đặt bằng file trong $SIM), openssl và CA riêng của Box là THẬT (onebee-ca.sh).
# Mỗi kịch bản: mọi dịch vụ sống → toàn [OK], mã thoát 0; tắt/làm hỏng ĐÚNG 1 thứ → đúng mục đó báo cảnh báo/lỗi, các mục khác vẫn OK.
# Cần: bash 4+, python3 + jinja2 + pyyaml, openssl (Linux). Trên máy khác: chạy trong container Ubuntu 24.04 có các gói trên.
# Cách dùng: tests/box/check-diagnosis.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "${T}"' EXIT
SIM="${T}/sim"
fails=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; fails=$((fails + 1)); }

python3 -c 'import jinja2, yaml' 2>/dev/null || { echo "Cần python3 với jinja2 + pyyaml (pip install jinja2 pyyaml)"; exit 2; }
mkdir -p "${T}"/{lib,bin,secrets,ssh,box,proc,sim,log} "${T}/data/chung" "${T}/mnt/onebee-sao-luu/restic-box"

# ---- Dựng lệnh onebee-box từ mẫu (như bộ cài Ansible), đường dẫn máy thật → thư mục tạm, bỏ kiểm quyền root ----
python3 - "${ROOT}" "${T}" <<'PY'
import json, os, shlex, sys
import jinja2, yaml
root, t = sys.argv[1:]
tpl = os.path.join(root, "box/ansible/roles/box-stack/templates")
v = yaml.safe_load(open(os.path.join(root, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
v.update(onebee_box_secrets=f"{t}/secrets", onebee_box_ssh_dir=f"{t}/ssh", onebee_box_data=f"{t}/data", onebee_box_dir=f"{t}/box",
         onebee_box_backup_repo=f"{t}/mnt/onebee-sao-luu/restic-box", onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="kiem-thu")
env = jinja2.Environment(keep_trailing_newline=True)
env.filters.update(to_json=lambda x: json.dumps(x, ensure_ascii=False), quote=shlex.quote, bool=bool)
def sua(s):
    return (s.replace("/usr/local/lib/onebee-box", f"{t}/lib").replace("/var/log/onebee-box", f"{t}/log")
             .replace("/run/onebee-box.lock", f"{t}/onebee-box.lock").replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||"))
for src, dst in (("onebee-box-common.sh.j2", "lib/common.sh"), ("onebee-box-sao-luu.sh.j2", "lib/sao-luu.sh"),
                 ("onebee-box-chan-doan.sh.j2", "lib/chan-doan.sh"), ("onebee-box.sh.j2", "bin/onebee-box")):
    with open(os.path.join(tpl, src), encoding="utf-8") as f:
        out = sua(env.from_string(f.read()).render(**v))
    with open(os.path.join(t, dst), "w", encoding="utf-8") as f:
        f.write(out)
PY
[[ -s "${T}/lib/chan-doan.sh" ]] || { echo "FAIL  Không dựng được lệnh từ mẫu"; exit 1; }
cp "${ROOT}/box/ansible/roles/box-stack/files/onebee-ca.sh" "${T}/lib/onebee-ca.sh"
"${T}/lib/onebee-ca.sh" "${T}/secrets/ca" kiem-thu 127.0.0.1 >/dev/null 2>&1 || { echo "FAIL  Không tạo được CA thử"; exit 1; }
printf 'mat-khau-kho-box' >"${T}/secrets/restic-box"

# ---- Lệnh GIẢ ----
gia() { printf '#!/usr/bin/env bash\n%s\n' "$2" >"${T}/bin/$1"; chmod +x "${T}/bin/$1"; }
# ping: $SIM/ping-<đích> chứa thời gian trả lời trung bình (ms); không có file = mất gói
gia ping 'd="${!#}"; [[ -s "${SIM}/ping-${d}" ]] || { echo "3 packets transmitted, 0 received, 100% packet loss"; exit 1; }
a="$(cat "${SIM}/ping-${d}")"; echo "3 packets transmitted, 3 received, 0% packet loss"; echo "rtt min/avg/max/mdev = ${a}/${a}/${a}/0.000 ms"'
gia ip '[[ -s "${SIM}/gateway" ]] && echo "default via $(cat "${SIM}/gateway") dev eth0 proto dhcp src 127.0.0.1 metric 100"; exit 0'
gia tailscale '[[ "$1" == status ]] || exit 2; [[ ! -e "${SIM}/tailscale-dung" ]] || { echo "Tailscale is stopped."; exit 1; }; echo "100.64.0.1 box linux -"'
# df -P <thư mục>: $SIM/df-<tên> chứa % đã dùng (mặc định 40)
gia df 'd="${!#}"; k="${d//\//_}"; p=40; [[ ! -s "${SIM}/df${k}" ]] || p="$(cat "${SIM}/df${k}")"
echo "Filesystem 1024-blocks Used Available Capacity Mounted on"; echo "/dev/sda1 100000000 $((p * 1000000)) $(((100 - p) * 1000000)) ${p}% ${d}"'
gia systemctl 'u="${!#}"; [[ ! -e "${SIM}/dung-${u}" ]] || exit 3; [[ "$*" == *--quiet* ]] || echo active'
gia mountpoint '[[ ! -e "${SIM}/o-sao-luu-chua-gan" ]]'
gia runuser 'while [[ $# -gt 0 && "$1" != -- ]]; do shift; done; shift; [[ ! -e "${SIM}/chung-khong-ghi" ]] || exit 1; exec "$@"'
gia restic '[[ -s "${RESTIC_PASSWORD_FILE:-}" && "${RESTIC_REPOSITORY:-}" == */restic-box ]] || { echo "Fatal: thiếu mật khẩu/kho" >&2; exit 1; }
[[ ! -e "${SIM}/restic-chua-tao" ]] || { echo "Fatal: unable to open config file: no such file" >&2; exit 10; }
cat "${SIM}/restic-snapshots"'
# docker: $SIM/docker-tat = dịch vụ docker ngừng; $SIM/ct-<tên> = "<Status> [<Health>]" (mặc định running); $SIM/ct-<tên>-mat = không có container
# docker exec onebee-open-webui curl ... ollama:11434 → in thân + dòng "<mã HTTP> <giây>" từ $SIM/ai (mặc định "200 1.2"); ghi lại tham số
gia docker '[[ ! -e "${SIM}/docker-tat" ]] || { echo "Cannot connect to the Docker daemon" >&2; exit 1; }
case "$1" in
  info) echo ok ;;
  inspect) shift; echo "[" ; sep=""; rc=0
    for c in "$@"; do
      [[ ! -e "${SIM}/ct-${c}-mat" ]] || { echo "Error: No such object: ${c}" >&2; rc=1; continue; }
      read -r st he <<<"$(cat "${SIM}/ct-${c}" 2>/dev/null || echo running)"
      h=""; [[ -z "${he:-}" ]] || h=",\"Health\":{\"Status\":\"${he}\"}"
      printf "%s{\"Name\":\"/%s\",\"State\":{\"Status\":\"%s\"%s}}\n" "${sep}" "${c}" "${st}" "${h}"; sep=","
    done; echo "]"; exit "${rc}" ;;
  exec) printf "%s\n" "$*" >>"${SIM}/docker-exec.log"
    st="$(cat "${SIM}/ct-$2" 2>/dev/null || echo running)"
    [[ "${st}" == running* && ! -e "${SIM}/ct-$2-mat" ]] || { echo "Error response from daemon: container $2 is not running" >&2; exit 1; }
    read -r ma giay <<<"$(cat "${SIM}/ai" 2>/dev/null || echo "200 1.2")"
    [[ "${ma}" == 200 ]] && printf "{\"response\":\"ok\",\"done\":true}" || printf "{\"error\":\"model not found\"}"
    printf "\n%s %s" "${ma}" "${giay}"; [[ "${ma}" != 000 ]] || exit 28 ;;
  *) exit 0 ;;
esac'
export SIM PATH="${T}/bin:${PATH}" ONEBEE_PROC="${T}/proc" NO_COLOR=1

# ---- Trạng thái "mọi thứ khỏe" ----
moi_thu_khoe() {
  rm -rf "${SIM}"; mkdir -p "${SIM}"
  echo 192.168.1.1 >"${SIM}/gateway"
  echo 0.4 >"${SIM}/ping-192.168.1.1"; echo 12.0 >"${SIM}/ping-1.1.1.1"; echo 15.0 >"${SIM}/ping-8.8.8.8"
  printf 'MemTotal:       16000000 kB\nMemFree:         4000000 kB\nMemAvailable:    8000000 kB\n' >"${T}/proc/meminfo"
  echo "0.50 0.40 0.30 1/200 12345" >"${T}/proc/loadavg"
  ban_sao_luu 2
  rm -rf "${T}/secrets/ca"; "${T}/lib/onebee-ca.sh" "${T}/secrets/ca" kiem-thu 127.0.0.1 >/dev/null 2>&1
  rm -f "${T}/secrets/https-da-bat"
}
# Bản sao lưu Box mới nhất cách đây $1 giờ (rỗng = kho chưa có bản nào)
ban_sao_luu() {
  if [[ -z "${1:-}" ]]; then echo "[]" >"${SIM}/restic-snapshots"; return; fi
  python3 -c 'import datetime, json, sys
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=float(sys.argv[1]))
cu = t - datetime.timedelta(days=3)
print(json.dumps([{"time": cu.isoformat().replace("+00:00", "Z"), "tags": ["onebee-box", "chung"]},
                  {"time": t.strftime("%Y-%m-%dT%H:%M:%S.123456789+00:00"), "tags": ["onebee-box", "csdl"]}]))' "$1" >"${SIM}/restic-snapshots"
}

# Chạy lệnh, lưu stdout + mã thoát
chay() { OUT="$(bash "${T}/bin/onebee-box" chan-doan "$@" 2>"${T}/stderr")"; RC=$?; }
# trang_thai <hạng mục> <mã mục> → ok | canh_bao | loi | (không có)
trang_thai() {
  python3 -c 'import json, sys
d = json.loads(sys.argv[1])
for h in d["hang_muc"]:
    if h["ma"] == sys.argv[2]:
        for m in h["muc"]:
            if m["ma"] == sys.argv[3]:
                print(m["trang_thai"]); sys.exit()
print("khong-co")' "${OUT}" "$1" "$2" 2>/dev/null || echo "json-hong"
}
# Các mục KHÔNG ok, dạng "hạng_mục/mã=trạng_thái" cách nhau dấu cách
khong_ok() {
  python3 -c 'import json, sys
d = json.loads(sys.argv[1])
print(" ".join(h["ma"] + "/" + m["ma"] + "=" + m["trang_thai"] for h in d["hang_muc"] for m in h["muc"] if m["trang_thai"] != "ok"))' "${OUT}" 2>/dev/null || echo "json-hong"
}
# kich_ban <mô tả> <mã thoát mong đợi> <danh sách mục không ok mong đợi> — chạy --json sau khi đã đặt trạng thái giả
kich_ban() {
  local mo_ta="$1" rc_mong="$2" mong="$3" thuc
  chay --json
  thuc="$(khong_ok)"
  if [[ "${RC}" == "${rc_mong}" && "${thuc}" == "${mong}" ]]; then pass "${mo_ta}"
  else fail "${mo_ta} — mã thoát ${RC} (mong ${rc_mong}); mục không OK: '${thuc}' (mong '${mong}')"; sed 's/^/      /' "${T}/stderr" | head -5; fi
}

# ===== 1. Mọi dịch vụ sống =====
moi_thu_khoe
chay --json
if python3 -c 'import json, sys
d = json.loads(sys.argv[1])
assert [h["ma"] for h in d["hang_muc"]] == ["mang", "tai_nguyen", "docker", "ai", "samba", "sao_luu", "ssl"], d["hang_muc"]
assert d["ket_luan"] == "ok" and d["dem"]["loi"] == 0 and d["dem"]["canh_bao"] == 0 and d["dem"]["ok"] >= 15, d["dem"]
for h in d["hang_muc"]:
    assert h["ten"] and h["trang_thai"] == "ok" and h["muc"], h
    for m in h["muc"]:
        assert set(m) == {"ma", "ten", "trang_thai", "chi_tiet", "goi_y"} and m["ten"] and m["chi_tiet"], m
assert d["thoi_diem"][:2] == "20"' "${OUT}" 2>"${T}/py-loi"; then pass "Mọi dịch vụ sống: JSON đủ 7 hạng mục, toàn OK"
else fail "Mọi dịch vụ sống: JSON sai — $(tail -1 "${T}/py-loi")"; echo "${OUT}" | head -c 600; echo; fi
if [[ "${RC}" == 0 ]]; then pass "Mọi dịch vụ sống: mã thoát 0"; else fail "Mọi dịch vụ sống: mã thoát ${RC} (mong 0)"; fi
[[ "$(khong_ok)" == "" ]] || fail "Mọi dịch vụ sống: có mục không OK: $(khong_ok)"
for c in onebee-portal onebee-ollama onebee-open-webui onebee-n8n onebee-uptime-kuma onebee-rest-server; do
  [[ "$(trang_thai docker "${c}")" == ok ]] || fail "Thiếu mục container ${c} trong hạng mục Docker"
done
if grep -q 'gemma4:e2b-it-qat' "${SIM}/docker-exec.log" && grep -q 'http://ollama:11434/api/generate' "${SIM}/docker-exec.log"; then pass "Thử AI: gửi prompt tới Ollama cổng 11434 bằng đúng model trong group_vars"; else fail "Thử AI không gọi Ollama đúng model/cổng: $(cat "${SIM}/docker-exec.log" 2>/dev/null)"; fi

chay
if [[ "${RC}" == 0 ]] && grep -q '\[OK\]' <<<"${OUT}" && ! grep -q 'LỖI\|CẢNH BÁO' <<<"${OUT}" \
   && grep -q '^KẾT LUẬN' <<<"${OUT}" && [[ "$(grep -c '^[1-7]\. ' <<<"${OUT}")" == 7 ]]; then pass "Bảng chữ: 7 hạng mục, [OK], có kết luận"
else fail "Bảng chữ sai (mã ${RC}):"; echo "${OUT}"; fi
if grep -q $'\e\[' <<<"${OUT}"; then fail "Có mã màu khi không phải terminal / NO_COLOR"; else pass "Không in mã màu khi ra file / NO_COLOR"; fi

# ===== 2. Tắt đúng 1 dịch vụ → báo đúng chỗ =====
moi_thu_khoe; echo "exited" >"${SIM}/ct-onebee-n8n"
kich_ban "Tắt n8n → chỉ container n8n LỖI, mã thoát 2" 2 "docker/onebee-n8n=loi"
chay
if grep -q '\[LỖI\].*onebee-n8n' <<<"${OUT}" && grep -q 'docker compose' <<<"${OUT}" && grep -q '^KẾT LUẬN.*1 lỗi' <<<"${OUT}"; then pass "Bảng chữ: dòng [LỖI] n8n kèm gợi ý chạy lại, kết luận nêu 1 lỗi"; else fail "Bảng chữ khi tắt n8n thiếu [LỖI]/gợi ý/kết luận"; echo "${OUT}"; fi

moi_thu_khoe; echo "exited" >"${SIM}/ct-onebee-open-webui"
kich_ban "Tắt Open WebUI → container LỖI và không thử được AI (LỖI)" 2 "docker/onebee-open-webui=loi ai/ollama=loi"
moi_thu_khoe; echo "running unhealthy" >"${SIM}/ct-onebee-ollama"
kich_ban "Container Ollama unhealthy → LỖI" 2 "docker/onebee-ollama=loi"
moi_thu_khoe; echo "running starting" >"${SIM}/ct-onebee-rest-server"
kich_ban "Container đang khởi động (health starting) → CẢNH BÁO, mã thoát 1" 1 "docker/onebee-rest-server=canh_bao"
moi_thu_khoe; : >"${SIM}/ct-onebee-portal-mat"
kich_ban "Mất container portal → LỖI" 2 "docker/onebee-portal=loi"
moi_thu_khoe; : >"${SIM}/docker-tat"
chay --json
if [[ "${RC}" == 2 && "$(trang_thai docker docker)" == loi && "$(trang_thai ai ollama)" == loi ]]; then pass "Dịch vụ Docker ngừng → Docker LỖI, AI LỖI, lệnh vẫn chạy hết các hạng mục"; else fail "Docker ngừng: mã ${RC}, docker=$(trang_thai docker docker), ai=$(trang_thai ai ollama)"; fi
[[ "$(trang_thai samba smbd)" == ok && "$(trang_thai sao_luu ban_moi_nhat)" == ok ]] || fail "Docker ngừng làm hỏng kết quả các hạng mục khác"

# ===== Mạng =====
moi_thu_khoe; rm -f "${SIM}/ping-192.168.1.1"
kich_ban "Router không trả lời → mạng LỖI" 2 "mang/gateway=loi"
moi_thu_khoe; echo 9.5 >"${SIM}/ping-192.168.1.1"
kich_ban "Router trả lời chậm (≥ 5 ms) → CẢNH BÁO" 1 "mang/gateway=canh_bao"
moi_thu_khoe; : >"${SIM}/gateway"
kich_ban "Không có gateway (chưa có đường ra mạng) → LỖI" 2 "mang/gateway=loi"
moi_thu_khoe; rm -f "${SIM}/ping-1.1.1.1"
kich_ban "Chỉ 1 trong 2 DNS công cộng trả lời → Internet vẫn OK" 0 ""
rm -f "${SIM}/ping-8.8.8.8"
kich_ban "Không ping được 1.1.1.1 lẫn 8.8.8.8 → Internet CẢNH BÁO (Box vẫn phục vụ LAN)" 1 "mang/internet=canh_bao"
moi_thu_khoe; : >"${SIM}/tailscale-dung"
kich_ban "Đã cài Tailscale nhưng chưa nối → CẢNH BÁO" 1 "mang/tailscale=canh_bao"

# ===== Tài nguyên =====
moi_thu_khoe; echo 85 >"${SIM}/df_"
kich_ban "Ổ hệ thống 85% → CẢNH BÁO" 1 "tai_nguyen/o_dia_he_thong=canh_bao"
moi_thu_khoe; echo 95 >"${SIM}/df${T//\//_}_data"
kich_ban "Ổ dữ liệu 95% → LỖI" 2 "tai_nguyen/o_dia_du_lieu=loi"
moi_thu_khoe; echo 80 >"${SIM}/df_"
kich_ban "Ổ đúng 80% → vẫn OK (ngưỡng là > 80%)" 0 ""
moi_thu_khoe; printf 'MemTotal:        8000000 kB\nMemAvailable:    1200000 kB\n' >"${T}/proc/meminfo"
kich_ban "RAM trống 1,2 GB (< 1,5 GB) → CẢNH BÁO" 1 "tai_nguyen/ram=canh_bao"
moi_thu_khoe; echo "$(( $(nproc) * 3 )).00 1.0 1.0 1/200 1" >"${T}/proc/loadavg"
kich_ban "Tải CPU vượt số nhân → CẢNH BÁO" 1 "tai_nguyen/cpu=canh_bao"

# ===== Trợ lý AI =====
moi_thu_khoe; echo "200 8.4" >"${SIM}/ai"
kich_ban "AI trả lời sau 8,4 giây (> 5 giây) → CẢNH BÁO chậm" 1 "ai/ollama=canh_bao"
moi_thu_khoe; echo "404 0.1" >"${SIM}/ai"
kich_ban "Model chưa tải (Ollama 404) → LỖI" 2 "ai/ollama=loi"
chay; if grep -q 'ollama pull gemma4:e2b-it-qat' <<<"${OUT}"; then pass "Gợi ý tải lại đúng model"; else fail "Thiếu gợi ý 'ollama pull <model>'"; fi
moi_thu_khoe; echo "000 120" >"${SIM}/ai"
kich_ban "Ollama không trả lời (hết giờ) → LỖI" 2 "ai/ollama=loi"

# ===== Samba =====
moi_thu_khoe; : >"${SIM}/dung-smbd"
kich_ban "smbd ngừng → LỖI" 2 "samba/smbd=loi"
moi_thu_khoe; : >"${SIM}/chung-khong-ghi"
kich_ban "Tài khoản thư mục chung không ghi được → LỖI" 2 "samba/ghi_thu_muc_chung=loi"
moi_thu_khoe; chay --json
if [[ -z "$(find "${T}/data/chung" -mindepth 1 -print -quit)" ]]; then pass "Thử ghi thư mục chung không để lại file"; else fail "Thử ghi để lại file trong thư mục chung"; fi

# ===== Sao lưu =====
moi_thu_khoe; ban_sao_luu 30
kich_ban "Bản sao lưu mới nhất cách 30 giờ (> 26 giờ) → CẢNH BÁO" 1 "sao_luu/ban_moi_nhat=canh_bao"
moi_thu_khoe; ban_sao_luu ""
kich_ban "Kho chưa có bản sao lưu nào → LỖI" 2 "sao_luu/ban_moi_nhat=loi"
moi_thu_khoe; : >"${SIM}/restic-chua-tao"
kich_ban "Chưa tạo kho sao lưu → LỖI" 2 "sao_luu/ban_moi_nhat=loi"
chay; if grep -q 'onebee-box khoi-tao' <<<"${OUT}"; then pass "Gợi ý chạy khoi-tao khi chưa có kho"; else fail "Thiếu gợi ý khoi-tao"; fi
moi_thu_khoe; : >"${SIM}/o-sao-luu-chua-gan"
kich_ban "Chưa gắn ổ sao lưu → LỖI (không đọc kho)" 2 "sao_luu/o_sao_luu=loi sao_luu/ban_moi_nhat=loi"

# ===== Chứng chỉ =====
# CA trung gian còn 10 ngày (ký lại bằng khóa CA gốc thật, giữ nguyên khóa trung gian)
moi_thu_khoe
openssl x509 -in "${T}/secrets/ca/inter.crt" -x509toreq -signkey "${T}/secrets/ca/inter.key" -out "${T}/inter.csr" 2>/dev/null
printf 'basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\n' >"${T}/inter.ext"
openssl x509 -req -in "${T}/inter.csr" -CA "${T}/secrets/ca/root.crt" -CAkey "${T}/secrets/ca/root.key" -CAcreateserial \
  -days 10 -extfile "${T}/inter.ext" -out "${T}/secrets/ca/inter.crt" 2>/dev/null
kich_ban "CA trung gian còn 10 ngày (< 15) → CẢNH BÁO" 1 "ssl/ca_trung_gian=canh_bao"
chay; if grep -q 'onebee-box gia-han-ca' <<<"${OUT}"; then pass "Gợi ý gia hạn CA"; else fail "Thiếu gợi ý gia-han-ca"; fi
moi_thu_khoe; rm -f "${T}/secrets/ca/root.crt"
kich_ban "Mất chứng chỉ CA gốc → LỖI" 2 "ssl/ca_goc=loi"

# HTTPS đang bật: đọc chứng chỉ thật đang phục vụ ở cổng 443 (cần quyền root để mở cổng 443)
if [[ ${EUID} -eq 0 ]] && command -v openssl >/dev/null; then
  moi_thu_khoe; : >"${T}/secrets/https-da-bat"
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout "${T}/la.key" -out "${T}/la.crt" -days 7 -subj /CN=127.0.0.1 2>/dev/null
  openssl s_server -accept 443 -cert "${T}/la.crt" -key "${T}/la.key" -quiet -naccept 5 >/dev/null 2>&1 &
  srv=$!
  sleep 1
  kich_ban "HTTPS bật, chứng chỉ cổng 443 còn 7 ngày → CẢNH BÁO" 1 "ssl/https=canh_bao"
  kill "${srv}" 2>/dev/null; wait "${srv}" 2>/dev/null
  kich_ban "HTTPS bật nhưng cổng 443 không trả chứng chỉ → LỖI" 2 "ssl/https=loi"
else
  echo "BỎ QUA  Chứng chỉ HTTPS cổng 443 (cần chạy bằng root)"
fi

# ===== Cách gọi =====
moi_thu_khoe
OUT="$(bash "${T}/bin/onebee-box" chan-doan --sai 2>&1)"; RC=$?
if [[ "${RC}" != 0 ]] && grep -q 'chan-doan \[--json\]' <<<"${OUT}"; then pass "Tham số lạ → báo cách dùng"; else fail "Tham số lạ không báo cách dùng (mã ${RC})"; fi
OUT="$(bash "${T}/bin/onebee-box" 2>&1)"
if grep -q 'chan-doan' <<<"${OUT}"; then pass "Trợ giúp onebee-box có lệnh chan-doan"; else fail "Trợ giúp onebee-box thiếu chan-doan"; fi

echo "---"
echo "Kết quả: ${fails} mục không đạt"
exit $((fails > 0))
