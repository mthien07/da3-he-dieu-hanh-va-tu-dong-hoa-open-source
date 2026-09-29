#!/usr/bin/env bash
# Kiểm tra kết quả cài OneBee OS Desktop trên máy (hoặc container) vừa chạy onebee-install.sh.
# In PASS/FAIL từng mục, thoát mã 1 nếu có mục FAIL.
set -uo pipefail

fails=0
check() { # check "mô tả" lệnh...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS  %s\n' "$desc"; else printf 'FAIL  %s\n' "$desc"; fails=$((fails + 1)); fi
}
pkg() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'install ok installed'; }
font_is() { fc-match "$1" | grep -q "$2"; }

check "Có file phiên bản /etc/onebee-release" grep -q '^ONEBEE_VERSION=' /etc/onebee-release
check "Locale vi_VN.UTF-8 đã tạo" bash -c "locale -a | grep -qi '^vi_VN.utf8$'"
check "Ngôn ngữ mặc định là vi_VN.UTF-8" grep -q '^LANG=vi_VN.UTF-8$' /etc/default/locale
check "Múi giờ Asia/Ho_Chi_Minh" bash -c "readlink /etc/localtime | grep -q 'Asia/Ho_Chi_Minh'"

# Bộ gõ đang dùng: ibus-bamboo (mặc định) hoặc ibus-unikey (tùy chọn onebee_input_method: unikey)
if pkg ibus-bamboo; then ime_pkg=ibus-bamboo; ime_engine=Bamboo; else ime_pkg=ibus-unikey; ime_engine=Unikey; fi

for p in language-pack-vi language-pack-gnome-vi firefox-locale-vi ibus "${ime_pkg}" \
         fonts-liberation2 fonts-crosextra-carlito fonts-crosextra-caladea fonts-noto-core \
         libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-l10n-vi hunspell-vi; do
  check "Đã cài gói ${p}" pkg "$p"
done

check "IBus là bộ gõ mặc định (im-config)" grep -q '^IM_CONFIG_DEFAULT_MODE=ibus$' /etc/default/im-config
check "Bộ gõ ${ime_engine} được nạp sẵn trong IBus (gsettings org.freedesktop.ibus.general)" \
  bash -c "GSETTINGS_BACKEND=memory gsettings get org.freedesktop.ibus.general preload-engines | grep -q \"'${ime_engine}'\""
if [[ ${ime_pkg} == ibus-bamboo ]]; then
  check "PPA ibus-bamboo chỉ cấp được gói ibus-bamboo (gói khác bị chặn)" \
    bash -c "apt-cache policy | grep -Eq -- '^ +-1 https://ppa.launchpadcontent.net/bamboo-engine/' \
             && apt-cache policy | grep -Eq 'ibus-bamboo -> .* with priority 500'"
fi

check "Arial → Liberation Sans" font_is Arial "Liberation Sans"
check "Times New Roman → Liberation Serif" font_is "Times New Roman" "Liberation Serif"
check "Calibri → Carlito" font_is Calibri Carlito
check "Cambria → Noto Serif (Caladea thiếu chữ tiếng Việt)" font_is Cambria "Noto Serif"
check "Font Noto có đủ dấu tiếng Việt (ạ ử ỗ)" bash -c "fc-list ':charset=1ea1 1eed 1ed7' family | grep -qi noto"

check "Có file cấu hình định dạng mặc định LibreOffice" \
  grep -q 'MS Word 2007 XML' /usr/lib/libreoffice/share/registry/onebee-office-defaults.xcd

check "Có hình nền OneBee" test -s /usr/share/backgrounds/onebee/onebee-wallpaper.png
if [[ -f /usr/share/glib-2.0/schemas/org.cinnamon.desktop.background.gschema.xml ]]; then
  check "Cinnamon dùng hình nền OneBee mặc định" bash -c \
    "GSETTINGS_BACKEND=memory gsettings get org.cinnamon.desktop.background picture-uri | grep -q onebee-wallpaper.png"
fi

if [[ -x /usr/bin/mintupdate-automation ]]; then
  check "Bật tự động nâng cấp mintupdate" test -e /etc/systemd/system/timers.target.wants/mintupdate-automation-upgrade.timer
  check "Bật tự động dọn gói thừa mintupdate" test -e /etc/systemd/system/timers.target.wants/mintupdate-automation-autoremove.timer
else
  check "Bật unattended-upgrades" grep -q 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades
fi

check "Có lệnh sao lưu onebee-sao-luu + restic" bash -c "test -x /usr/local/sbin/onebee-sao-luu && command -v restic"
check "Thư mục cấu hình /etc/onebee chỉ root vào (700)" bash -c "[ \"\$(stat -c %a /etc/onebee)\" = 700 ]"
check "Có lệnh hỏi Trợ lý AI (hoi)" test -x /usr/local/bin/hoi

echo "----"
if [[ ${fails} -eq 0 ]]; then echo "KẾT QUẢ: tất cả mục đạt"; else echo "KẾT QUẢ: ${fails} mục KHÔNG đạt"; exit 1; fi
