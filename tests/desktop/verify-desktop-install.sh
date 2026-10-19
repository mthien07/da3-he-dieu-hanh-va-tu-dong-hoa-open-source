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
# Giá trị MẶC ĐỊNH đã biên dịch của khóa gsettings (bộ nhớ tạm, không phụ thuộc phiên người dùng) có chứa chuỗi
gs_has() { GSETTINGS_BACKEND=memory gsettings get "$1" "$2" | grep -qF -- "$3"; }
has_schema() { gsettings list-schemas | grep -qx "$1"; }

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

# Bố cục kiểu Windows (role theme) — chỉ kiểm khi máy có Cinnamon; Nemo/Cinnamon đầy đủ có thể chưa cài trong container rút gọn
if [[ -f /usr/share/glib-2.0/schemas/org.cinnamon.desktop.background.gschema.xml ]]; then
  check "Có file schema bố cục Windows (zz_onebee-windows-layout)" test -s /usr/share/glib-2.0/schemas/zz_onebee-windows-layout.gschema.override
  check "Nút cửa sổ: thu nhỏ, phóng to, đóng ở góc phải" gs_has org.cinnamon.desktop.wm.preferences button-layout "':minimize,maximize,close'"
  check "Win+D hiện màn hình nền" gs_has org.cinnamon.desktop.keybindings.wm show-desktop "'<Super>d'"
  check "Win+E mở thư mục cá nhân (Nemo)" gs_has org.cinnamon.desktop.keybindings.media-keys home "'<Super>e'"
  check "Win+L khóa màn hình (vẫn giữ Ctrl+Alt+L)" bash -c \
    "export GSETTINGS_BACKEND=memory; v=\$(gsettings get org.cinnamon.desktop.keybindings.media-keys screensaver); \
     [[ \$v == *'<Super>l'* && \$v == *'<Control><Alt>l'* ]]"
  check "Win+R mở hộp thoại Chạy lệnh (vẫn giữ Alt+F2)" bash -c \
    "export GSETTINGS_BACKEND=memory; v=\$(gsettings get org.cinnamon.desktop.keybindings.wm panel-run-dialog); \
     [[ \$v == *\"'<Super>r'\"* && \$v == *\"'<Alt>F2'\"* ]]"
  check "Win+Shift+S chụp màn hình chọn vùng (vẫn giữ Shift+Print)" bash -c \
    "export GSETTINGS_BACKEND=memory; v=\$(gsettings get org.cinnamon.desktop.keybindings.media-keys area-screenshot); \
     [[ \$v == *\"'<Super><Shift>s'\"* && \$v == *\"'<Shift>Print'\"* ]]"
  check "Bộ biểu tượng thư mục vàng Mint-Y-Sand (có cài + đặt mặc định)" bash -c \
    "test -d /usr/share/icons/Mint-Y-Sand && GSETTINGS_BACKEND=memory gsettings get org.cinnamon.desktop.interface icon-theme | grep -qx \"'Mint-Y-Sand'\""
  check "Ctrl+Shift+Esc mở Quản lý tác vụ (phím tùy chỉnh mặc định trong dconf hệ thống)" bash -c \
    "command -v gnome-system-monitor && dconf read /org/cinnamon/desktop/keybindings/custom-list | grep -qF "'custom0'" \
     && dconf read /org/cinnamon/desktop/keybindings/custom-keybindings/custom0/command | grep -qF gnome-system-monitor \
     && dconf read /org/cinnamon/desktop/keybindings/custom-keybindings/custom0/binding | grep -qF '<Primary><Shift>Escape'"
  if has_schema org.nemo.preferences; then
    check "Nemo: ẩn file ẩn, nhấp đúp để mở" bash -c \
      "export GSETTINGS_BACKEND=memory; [ \"\$(gsettings get org.nemo.preferences show-hidden-files)\" = false ] \
       && [ \"\$(gsettings get org.nemo.preferences click-policy)\" = \"'double'\" ]"
  fi
  check "Win+L không còn là phím bảng gỡ lỗi Looking Glass" bash -c \
    "[ \"\$(GSETTINGS_BACKEND=memory gsettings get org.cinnamon.desktop.keybindings looking-glass-keybinding)\" = '@as []' ]"
  if has_schema org.nemo.desktop; then
    for icon in computer trash home; do
      check "Màn hình nền hiện biểu tượng ${icon}" gs_has org.nemo.desktop "${icon}-icon-visible" true
    done
  fi
  if has_schema org.cinnamon; then
    check "Bảng điều khiển ở đáy màn hình, cao 40px" bash -c \
      "export GSETTINGS_BACKEND=memory; gsettings get org.cinnamon panels-enabled | grep -qF ':bottom' \
       && gsettings get org.cinnamon panels-height | grep -qF '1:40'"
    check "Nút menu Bắt đầu dùng logo OneBee" gs_has org.cinnamon app-menu-icon-name "'onebee-logo'"
    check "Nút menu có chữ \"Bắt đầu\"" gs_has org.cinnamon app-menu-label "'Bắt đầu'"
    for app in firefox libreoffice-writer libreoffice-calc libreoffice-impress nemo onebee-tro-ly-ai cinnamon-settings; do
      check "Menu bắt đầu ghim sẵn ${app}" gs_has org.cinnamon favorite-apps "'${app}.desktop'"
    done
  fi
fi
check "Có lệnh mở Trợ lý AI + mục menu Trợ lý AI OneBee" bash -c \
  "test -x /usr/local/bin/onebee-mo-tro-ly-ai && grep -q '^Exec=onebee-mo-tro-ly-ai$' /usr/share/applications/onebee-tro-ly-ai.desktop"
check "Logo OneBee là biểu tượng hệ thống onebee-logo (SVG + PNG 48px, đã làm mới bộ đệm)" bash -c \
  "test -s /usr/share/icons/hicolor/scalable/apps/onebee-logo.svg && test -s /usr/share/icons/hicolor/48x48/apps/onebee-logo.png \
   && test /usr/share/icons/hicolor/icon-theme.cache -nt /usr/share/icons/hicolor/48x48/apps/onebee-logo.png"
check "Trợ lý AI dùng biểu tượng logo OneBee" grep -qx 'Icon=onebee-logo' /usr/share/applications/onebee-tro-ly-ai.desktop
check "Có lệnh đặt lối tắt Chia sẻ nội bộ (OneBee Box) khi đăng nhập" bash -c \
  "test -x /usr/local/lib/onebee/onebee-loi-tat-chia-se && grep -qx 'Exec=/usr/local/lib/onebee/onebee-loi-tat-chia-se' /etc/xdg/autostart/onebee-loi-tat-chia-se.desktop"
if [[ -d /usr/share/cinnamon/applets/grouped-window-list@cinnamon.org ]]; then
  override=/usr/share/cinnamon/applets/grouped-window-list@cinnamon.org/settings-override.json
  check "Thanh tác vụ có file ghim sẵn ứng dụng (JSON hợp lệ)" python3 -m json.tool "${override}"
  for app in nemo firefox libreoffice-writer libreoffice-calc libreoffice-impress onebee-tro-ly-ai; do
    check "Thanh tác vụ ghim sẵn ${app}" grep -qF "\"${app}.desktop\"" "${override}"
  done
  check "Thanh tác vụ: xem trước cửa sổ thu nhỏ khi rê chuột" python3 -c \
    "import json,sys; d=json.load(open(sys.argv[1])); assert d['show-thumbnails']['default'] is True and d['enable-hover-peek']['default'] is True" "${override}"
fi
if [[ -f /usr/share/cinnamon/applets/menu@cinnamon.org/settings-schema.json ]]; then
  check "Phím Super mở menu bắt đầu (applet menu mặc định)" \
    grep -qF 'Super_L::Super_R' /usr/share/cinnamon/applets/menu@cinnamon.org/settings-schema.json
fi

check "LibreOffice mở mặc định giao diện Ribbon (tab) cho Writer, Calc, Impress" bash -c \
  "[ \$(grep -c '<value>Tabbed</value>' /usr/lib/libreoffice/share/registry/onebee-office-ribbon.xcd) -eq 3 ]"

if [[ -x /usr/bin/mintupdate-automation ]]; then
  check "Bật tự động nâng cấp mintupdate" test -e /etc/systemd/system/timers.target.wants/mintupdate-automation-upgrade.timer
  check "Bật tự động dọn gói thừa mintupdate" test -e /etc/systemd/system/timers.target.wants/mintupdate-automation-autoremove.timer
else
  check "Bật unattended-upgrades" grep -q 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades
fi

check "Có lệnh sao lưu onebee-sao-luu + restic" bash -c "test -x /usr/local/sbin/onebee-sao-luu && command -v restic"
check "Thư mục cấu hình /etc/onebee chỉ root vào (700)" bash -c "[ \"\$(stat -c %a /etc/onebee)\" = 700 ]"
check "Có lệnh hỏi Trợ lý AI (hoi)" test -x /usr/local/bin/hoi
check "Có lệnh báo tình trạng về Box" test -x /usr/local/sbin/onebee-bao-tinh-trang
check "Có hỗ trợ từ xa (onebee-ho-tro + x11vnc + mục menu)" bash -c \
  "test -x /usr/local/bin/onebee-ho-tro && command -v x11vnc && test -f /usr/share/applications/onebee-ho-tro.desktop"

echo "----"
if [[ ${fails} -eq 0 ]]; then echo "KẾT QUẢ: tất cả mục đạt"; else echo "KẾT QUẢ: ${fails} mục KHÔNG đạt"; exit 1; fi
