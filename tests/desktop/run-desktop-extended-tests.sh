#!/usr/bin/env bash
# Kiểm thử MỞ RỘNG cho OneBee OS Desktop (chạy trên máy có Docker). Mỗi kịch bản 1 container sạch.
#   1. guards    — chặn đúng: không phải root, có tham số, hệ điều hành không hỗ trợ (Debian 12)
#   2. mint      — Mint 22.3: chờ khóa dpkg, giữ LC_* sẵn có, cài 2 lần, tự sửa khi cấu hình bị lệch,
#                  verify + LibreOffice (UNO) + mở file Word tiếng Việt/xuất PDF + gõ Telex thật qua IBus
#   3. unikey    — biến thể bộ gõ Unikey: cài + verify + gõ Telex thật
#   4. systemd   — Mint chạy systemd thật (container --privileged): timer mintupdate chạy ngay sau khi cài
#   5. ubuntu    — nền Ubuntu 24.04 không phải Mint: cài + verify (nhánh unattended-upgrades)
# Cách dùng: tests/desktop/run-desktop-extended-tests.sh [tên kịch bản ...]   (mặc định: chạy tất cả)
# Mạng có proxy HTTPS tự ký: đặt ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MINT_IMAGE="${ONEBEE_TEST_IMAGE:-linuxmintd/mint22.3-amd64}"
docker_opts=(--rm -v "${REPO_ROOT}:/onebee:ro")
if [[ -n "${ONEBEE_TEST_EXTRA_CA:-}" ]]; then
  docker_opts+=(-v "${ONEBEE_TEST_EXTRA_CA}:/usr/local/share/ca-certificates/onebee-test-extra.crt:ro")
fi

# Đoạn lệnh dùng chung đầu mỗi container: tin CA phụ (nếu có), chép repo ra chỗ ghi được
PREP='set -euo pipefail; export DEBIAN_FRONTEND=noninteractive
if [ -f /usr/local/share/ca-certificates/onebee-test-extra.crt ]; then
  command -v update-ca-certificates >/dev/null || { apt-get update -q >/dev/null; apt-get install -y -q ca-certificates >/dev/null; }
  update-ca-certificates >/dev/null 2>&1
fi
rm -rf /tmp/onebee; cp -r /onebee /tmp/onebee; T=/tmp/onebee/tests/desktop'
# Thành phần có sẵn trên Mint Cinnamon cài thật (image container rút gọn không có)
MINT_DESKTOP_PARTS='apt-get update -q >/dev/null; apt-get install -y -q mintupdate mint-artwork cinnamon-desktop-data libglib2.0-bin >/dev/null'
# Công cụ chỉ dùng để kiểm thử (cài SAU OneBee để không che lỗi thiếu gói của bộ cài)
TEST_TOOLS='apt-get install -y -q python3-uno poppler-utils hunspell xvfb xdotool dbus-x11 python3-gi gir1.2-gtk-3.0 vncsnapshot >/dev/null
useradd -m -s /bin/bash nhanvien'

scenario_guards() {
  docker run "${docker_opts[@]}" "${MINT_IMAGE}" bash -c "${PREP}"'
    useradd -m tester
    if su tester -c "/tmp/onebee/desktop/onebee-install.sh" >/tmp/o1 2>&1; then echo "FAIL  Không phải root vẫn chạy"; exit 1; fi
    grep -q "quyền quản trị" /tmp/o1 || { echo "FAIL  Thông báo khi không phải root"; exit 1; }
    echo "PASS  Chặn người dùng không phải root"
    if /tmp/onebee/desktop/onebee-install.sh --check >/tmp/o2 2>&1; then echo "FAIL  Nhận tham số lạ"; exit 1; fi
    grep -q "không nhận tham số" /tmp/o2 || { echo "FAIL  Thông báo khi có tham số"; exit 1; }
    echo "PASS  Chặn tham số lạ"' || return 1
  docker run "${docker_opts[@]}" debian:12 bash -c "${PREP}"'
    if /tmp/onebee/desktop/onebee-install.sh >/tmp/o3 2>&1; then echo "FAIL  Debian 12 vẫn cài"; exit 1; fi
    grep -q "Chỉ hỗ trợ Linux Mint 22" /tmp/o3 || { echo "FAIL  Thông báo hệ điều hành"; exit 1; }
    echo "PASS  Chặn hệ điều hành không hỗ trợ (Debian 12)"' || return 1
}

scenario_mint() {
  docker run "${docker_opts[@]}" "${MINT_IMAGE}" bash -c "${PREP}; ${MINT_DESKTOP_PARTS}"'
    printf "LANG=en_US.UTF-8\nLC_TIME=en_GB.UTF-8\n" > /etc/default/locale
    # Máy trạm nâng cấp từ v0.1: file cấu hình sao lưu tên cũ, quyền lỏng
    mkdir -p /etc/onebee && chmod 755 /etc/onebee
    printf "RESTIC_REPOSITORY=rest:http://may:mk@127.0.0.1:1/may/\nRESTIC_PASSWORD=thu\n" > /etc/onebee/sao-luu.env
    # Giữ khóa dpkg 40 giây như lúc máy mới cài đang tự cập nhật ngầm (khóa fcntl giống apt)
    python3 -c "import fcntl,time; f=open(\"/var/lib/dpkg/lock-frontend\",\"w\"); fcntl.lockf(f,fcntl.LOCK_EX); time.sleep(40)" &
    sleep 1; start=$(date +%s)
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run1.log 2>&1 || { tail -30 /tmp/run1.log; exit 1; }
    echo "PASS  Chờ khóa dpkg rồi cài thành công ($(( $(date +%s) - start ))s)"
    grep -q "^LC_TIME=en_GB.UTF-8$" /etc/default/locale && grep -q "^LANG=vi_VN.UTF-8$" /etc/default/locale \
      && echo "PASS  Đổi LANG, giữ nguyên LC_TIME sẵn có" || { echo "FAIL  /etc/default/locale"; exit 1; }
    [ ! -e /etc/onebee/sao-luu.env ] && [ "$(stat -c %a /etc/onebee/may-tram.env)" = 600 ] \
      && [ "$(stat -c %a /etc/onebee)" = 700 ] && [ -e /etc/systemd/system/timers.target.wants/onebee-sao-luu.timer ] \
      && [ ! -e /etc/onebee-hoi.conf ] \
      && echo "PASS  Nâng cấp từ v0.1: sao-luu.env → may-tram.env (600), vẫn bật lịch sao lưu; chưa có khóa AI thì không tạo cấu hình hoi" \
      || { echo "FAIL  Chuyển cấu hình sao lưu v0.1"; ls -la /etc/onebee /etc/onebee-hoi.conf; exit 1; }
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run2.log 2>&1
    grep -Eq "changed=0 .*failed=0" /tmp/run2.log && echo "PASS  Chạy lần 2 không thay đổi gì" || { echo "FAIL  idempotent"; exit 1; }
    # Làm lệch cấu hình rồi chạy lại: bộ cài phải tự sửa
    rm -f /usr/share/backgrounds/onebee/onebee-wallpaper.png /etc/apt/preferences.d/onebee-ibus-bamboo
    sed -i "s/^IM_CONFIG_DEFAULT_MODE=.*/IM_CONFIG_DEFAULT_MODE=auto/" /etc/default/im-config
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run3.log 2>&1
    grep -Eq "changed=[1-9].*failed=0" /tmp/run3.log && echo "PASS  Tự sửa cấu hình bị lệch khi chạy lại" || { echo "FAIL  drift"; exit 1; }
    '"${TEST_TOOLS}"'
    $T/verify-desktop-install.sh
    python3 $T/check-libreoffice-default-formats.py
    su - nhanvien -c "$T/extended/check-office-documents-inside.sh"
    su - nhanvien -c "$T/extended/check-vietnamese-typing-inside.sh" 2>/dev/null | grep -E "^(PASS|FAIL|Gõ|preload|hình nền)"
    su - nhanvien -c "$T/extended/check-ho-tro-tu-xa-inside.sh"
    # Bộ đo trước/sau: chạy được trên máy đã cài, đo được thời gian mở LibreOffice, ghi đủ cột CSV
    su - nhanvien -c "Xvfb :78 >/dev/null 2>&1 & xp=\$!; sleep 2; DISPLAY=:78 python3 /tmp/onebee/tests/do-dac/do-may.py \
      --don-vi thu --may mint-thu --giai-doan sau -o /tmp/do-dac.csv >/dev/null; kill \$xp"
    python3 -c "import csv; r=list(csv.DictReader(open(\"/tmp/do-dac.csv\"))); assert len(r)==1 and float(r[0][\"mo_van_ban_giay\"])>0 and len(r[0])==15, r; print(\"PASS  Bộ đo trước/sau: ghi 1 dòng CSV đủ 15 cột, đo được mở LibreOffice Writer (\"+r[0][\"mo_van_ban_giay\"]+\" giây)\")"'
}

scenario_unikey() {
  docker run "${docker_opts[@]}" "${MINT_IMAGE}" bash -c "${PREP}; ${MINT_DESKTOP_PARTS}"'
    sed -i "s/^onebee_input_method: .*/onebee_input_method: unikey/" /tmp/onebee/desktop/ansible/group_vars/all.yml
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run1.log 2>&1 || { tail -30 /tmp/run1.log; exit 1; }
    '"${TEST_TOOLS}"'
    $T/verify-desktop-install.sh | grep -E "Unikey|unikey|KẾT"
    su - nhanvien -c "ONEBEE_TEST_ENGINE=Unikey $T/extended/check-vietnamese-typing-inside.sh" 2>/dev/null | grep -E "^(PASS|FAIL|Gõ)"'
}

scenario_systemd() {
  local name="onebee-systemd-test-$$"
  docker run -d --name "${name}" "${docker_opts[@]}" --privileged --cgroupns=host \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rw --tmpfs /run --tmpfs /run/lock "${MINT_IMAGE}" /lib/systemd/systemd >/dev/null
  trap 'docker rm -f "${name}" >/dev/null 2>&1 || true' RETURN
  sleep 8
  docker exec "${name}" bash -c "${PREP}; ${MINT_DESKTOP_PARTS}"'
    test -d /run/systemd/system || { echo "FAIL  systemd chưa chạy"; exit 1; }
    echo "PASS  Container chạy systemd thật"
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run1.log 2>&1 || { tail -30 /tmp/run1.log; exit 1; }
    for t in mintupdate-automation-upgrade.timer mintupdate-automation-autoremove.timer; do
      [ "$(systemctl is-active $t)" = active ] && echo "PASS  $t đang chạy ngay sau khi cài" || { echo "FAIL  $t"; exit 1; }
    done'
}

scenario_ubuntu() {
  docker run "${docker_opts[@]}" ubuntu:24.04 bash -c "${PREP}"'
    /tmp/onebee/desktop/onebee-install.sh >/tmp/run1.log 2>&1 || { tail -30 /tmp/run1.log; exit 1; }
    grep -q "không phải Linux Mint" /tmp/run1.log || { echo "FAIL  Thiếu cảnh báo không phải Mint"; exit 1; }
    echo "PASS  Cảnh báo đúng khi không phải Mint"
    apt-get install -y -q python3-uno >/dev/null
    $T/verify-desktop-install.sh | grep -E "FAIL|unattended|KẾT"
    python3 $T/check-libreoffice-default-formats.py >/tmp/lo.txt || { cat /tmp/lo.txt; exit 1; }
    echo "PASS  LibreOffice (UNO) đạt trên Ubuntu"'
}

scenarios=("$@")
[[ ${#scenarios[@]} -gt 0 ]] || scenarios=(guards mint unikey systemd ubuntu)
failed=()
for s in "${scenarios[@]}"; do
  echo "================ KỊCH BẢN: ${s} ================"
  if "scenario_${s}"; then echo "---- ${s}: ĐẠT"; else echo "---- ${s}: KHÔNG ĐẠT"; failed+=("${s}"); fi
done
echo "================================================"
if [[ ${#failed[@]} -eq 0 ]]; then echo "TẤT CẢ KỊCH BẢN ĐẠT"; else echo "KHÔNG ĐẠT: ${failed[*]}"; exit 1; fi
