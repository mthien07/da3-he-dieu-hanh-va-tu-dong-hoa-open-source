#!/usr/bin/env python3
"""Kiểm thử nhanh cho giao diện kiểu Windows (role theme + office): file override gsettings, ghim ứng dụng, Ribbon LibreOffice.
Không cần Cinnamon/LibreOffice thật. Chạy: python3 -m unittest"""
import configparser
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES = os.path.join(HERE, "../../desktop/ansible/roles")
OVERRIDE = os.path.join(ROLES, "theme/files/zz_onebee-windows-layout.gschema.override")
PIN_JSON = os.path.join(ROLES, "theme/files/grouped-window-list-settings-override.json")
LAUNCHER = os.path.join(ROLES, "theme/files/onebee-mo-tro-ly-ai")
THEME_TASKS = os.path.join(ROLES, "theme/tasks/main.yml")
RIBBON_XCD = os.path.join(ROLES, "office/files/onebee-office-ribbon.xcd")

# Chỉ những khóa này được phép có trong override: schema:khóa -> kiểu GVariant (đã đối chiếu với gói cinnamon-desktop-data,
# cinnamon, nemo trên Mint 22.x). Khóa sai tên/sai schema bị glib-compile-schemas bỏ qua lặng lẽ → phải bắt ở đây.
ALLOWLIST = {
    "org.cinnamon.desktop.wm.preferences": {"button-layout": "s"},
    "org.cinnamon.desktop.keybindings.wm": {"show-desktop": "as"},
    "org.cinnamon.desktop.keybindings.media-keys": {"home": "as", "screensaver": "as"},
    "org.cinnamon.desktop.keybindings": {"looking-glass-keybinding": "as"},
    "org.nemo.desktop": {"computer-icon-visible": "b", "trash-icon-visible": "b", "home-icon-visible": "b"},
    "org.cinnamon": {"app-menu-icon-name": "s", "favorite-apps": "as"},
}
APPS_VAN_PHONG = {"firefox.desktop", "libreoffice-writer.desktop", "libreoffice-calc.desktop",
                  "libreoffice-impress.desktop", "nemo.desktop", "onebee-tro-ly-ai.desktop"}


def doc_override():
    cp = configparser.RawConfigParser(strict=True)
    cp.optionxform = str  # giữ nguyên chữ hoa/thường của khóa
    with open(OVERRIDE, encoding="utf-8") as f:
        cp.read_file(f)
    return cp


class FileOverrideGsettings(unittest.TestCase):
    def test_chi_co_schema_va_khoa_trong_danh_sach_cho_phep(self):
        cp = doc_override()
        self.assertEqual(set(cp.sections()), set(ALLOWLIST))
        for schema in cp.sections():
            self.assertEqual(set(cp[schema]), set(ALLOWLIST[schema]), schema)

    def test_gia_tri_dung_nhu_thiet_ke(self):
        cp = doc_override()
        self.assertEqual(cp["org.cinnamon.desktop.wm.preferences"]["button-layout"], "':minimize,maximize,close'")
        self.assertEqual(cp["org.cinnamon.desktop.keybindings.wm"]["show-desktop"], "['<Super>d']")
        keys = cp["org.cinnamon.desktop.keybindings.media-keys"]
        self.assertIn("'<Super>e'", keys["home"])
        self.assertIn("'<Super>l'", keys["screensaver"])
        self.assertIn("'<Control><Alt>l'", keys["screensaver"])  # giữ phím khóa màn hình cũ của Mint
        for icon in ("computer", "trash", "home"):
            self.assertEqual(cp["org.nemo.desktop"][f"{icon}-icon-visible"], "true")

    def test_win_l_nhuong_tu_looking_glass(self):
        # Super+L mặc định của Cinnamon là Looking Glass: nếu không tháo, hai chức năng tranh cùng một phím
        self.assertEqual(doc_override()["org.cinnamon.desktop.keybindings"]["looking-glass-keybinding"], "@as []")

    def test_phim_tat_khong_trung_nhau(self):
        cp = doc_override()
        dung = {}
        for schema, khoa in (("org.cinnamon.desktop.keybindings.wm", "show-desktop"),
                             ("org.cinnamon.desktop.keybindings.media-keys", "home"),
                             ("org.cinnamon.desktop.keybindings.media-keys", "screensaver"),
                             ("org.cinnamon.desktop.keybindings", "looking-glass-keybinding")):
            for phim in re.findall(r"'([^']+)'", cp[schema][khoa]):
                self.assertNotIn(phim, dung, f"{phim} gán cho cả {dung.get(phim)} và {schema}.{khoa}")
                dung[phim] = f"{schema}.{khoa}"

    def test_ghim_menu_bat_dau_la_ung_dung_van_phong(self):
        ghim = set(re.findall(r"'([^']+\.desktop)'", doc_override()["org.cinnamon"]["favorite-apps"]))
        self.assertTrue(APPS_VAN_PHONG <= ghim, APPS_VAN_PHONG - ghim)

    @unittest.skipUnless(shutil.which("glib-compile-schemas"), "máy không có glib-compile-schemas")
    def test_bien_dich_nghiem_ngat_voi_schema_gia_lap(self):
        """Dựng schema giả đúng tên + kiểu khóa theo danh sách cho phép, biên dịch --strict: bắt sai kiểu/giá trị cú pháp."""
        with tempfile.TemporaryDirectory() as tmp:
            for i, (schema, khoa) in enumerate(ALLOWLIST.items()):
                keys = "".join(f'<key name="{k}" type="{t}"><default>{self.mac_dinh(t)}</default></key>' for k, t in khoa.items())
                with open(os.path.join(tmp, f"{i}.gschema.xml"), "w", encoding="utf-8") as f:
                    f.write(f'<schemalist><schema id="{schema}">{keys}</schema></schemalist>')
            shutil.copy(OVERRIDE, tmp)
            r = subprocess.run(["glib-compile-schemas", "--strict", "--dry-run", tmp], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    @staticmethod
    def mac_dinh(kieu):
        return {"s": "''", "as": "[]", "b": "false"}[kieu]


class GhimThanhTacVu(unittest.TestCase):
    def test_json_hop_le_va_ghi_de_chi_gia_tri_mac_dinh(self):
        with open(PIN_JSON, encoding="utf-8") as f:
            data = json.load(f)
        # override-props: chỉ thay thuộc tính nêu ra, giữ nguyên kiểu/mô tả của khóa gốc trong applet
        self.assertEqual(list(data), ["pinned-apps"])
        self.assertIs(data["pinned-apps"]["override-props"], True)
        self.assertEqual(set(data["pinned-apps"]["default"]), APPS_VAN_PHONG)

    def test_thu_tu_ghim_nemo_truoc_trinh_duyet_roi_van_phong(self):
        with open(PIN_JSON, encoding="utf-8") as f:
            ghim = json.load(f)["pinned-apps"]["default"]
        self.assertEqual(ghim[:2], ["nemo.desktop", "firefox.desktop"])
        self.assertEqual(ghim[-1], "onebee-tro-ly-ai.desktop")

    def test_role_dinh_nghia_muc_menu_tro_ly_ai_ma_thanh_tac_vu_ghim(self):
        with open(THEME_TASKS, encoding="utf-8") as f:
            tasks = f.read()
        self.assertIn("/usr/share/applications/onebee-tro-ly-ai.desktop", tasks)
        self.assertIn("Exec=onebee-mo-tro-ly-ai", tasks)


class LenhMoTroLyAi(unittest.TestCase):
    def test_cu_phap_bash(self):
        r = subprocess.run(["bash", "-n", LAUNCHER], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_chi_mo_dia_chi_http_https(self):
        with open(LAUNCHER, encoding="utf-8") as f:
            ma = f.read()
        self.assertIn("^https?://[^[:space:]]+$", ma)
        self.assertIn('exec xdg-open "${url}"', ma)


class RibbonLibreOffice(unittest.TestCase):
    def test_xcd_dat_tabbed_cho_writer_calc_impress(self):
        goc = ET.parse(RIBBON_XCD).getroot()
        oor = "{http://openoffice.org/2001/registry}"
        comp = goc.find(f"{oor}component-data")
        self.assertEqual(comp.get(f"{oor}name"), "ToolbarMode")
        self.assertEqual(comp.get(f"{oor}package"), "org.openoffice.Office.UI")
        ung_dung = {}
        for node in comp.find("node").findall("node"):
            prop = node.find("prop")
            ung_dung[node.get(f"{oor}name")] = (prop.get(f"{oor}name"), prop.find("value").text)
        self.assertEqual(ung_dung, {a: ("Active", "Tabbed") for a in ("Writer", "Calc", "Impress")})

    def test_nap_sau_cac_module_goc(self):
        goc = ET.parse(RIBBON_XCD).getroot()
        self.assertEqual({d.get("file") for d in goc.findall("dependency")}, {"main", "writer", "calc", "impress"})


if __name__ == "__main__":
    unittest.main()
