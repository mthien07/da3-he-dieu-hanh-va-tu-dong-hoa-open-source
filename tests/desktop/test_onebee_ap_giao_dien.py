#!/usr/bin/env python3
"""Kiểm thử việc áp hình nền OneBee cho người dùng: script chạy một lần theo phiên bản giao diện, đăng nhập tự áp,
bộ cài áp ngay cho phiên đồ họa đang mở. Không cần Cinnamon thật (gsettings giả). Chạy: python3 -m unittest"""
import os
import struct
import subprocess
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
THEME = os.path.join(ROOT, "desktop/ansible/roles/theme")
SCRIPT = os.path.join(THEME, "files/onebee-ap-giao-dien")
TASKS = os.path.join(THEME, "tasks/main.yml")
INSTALL = os.path.join(ROOT, "desktop/onebee-install.sh")
PNG = os.path.join(THEME, "files/onebee-wallpaper.png")
SVG = os.path.join(THEME, "files/onebee-wallpaper.svg")


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


class ChayScript(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        t = self.t.name
        os.makedirs(f"{t}/bin")
        os.makedirs(f"{t}/home")
        self.nhat_ky = f"{t}/gsettings.log"
        self.hinh = f"{t}/onebee-wallpaper.png"
        open(self.hinh, "wb").write(b"png")
        self.dat_gsettings(0)

    def dat_gsettings(self, ma):
        p = f"{self.t.name}/bin/gsettings"
        with open(p, "w") as f:
            f.write(f'#!/bin/sh\necho "$@" >> "{self.nhat_ky}"\nexit {ma}\n')
        os.chmod(p, 0o755)

    def chay(self, hinh=None):
        env = {"PATH": f"{self.t.name}/bin:/usr/bin:/bin", "HOME": f"{self.t.name}/home",
               "ONEBEE_HINH_NEN": hinh or self.hinh}
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True)

    def goi(self):
        return open(self.nhat_ky).read().splitlines() if os.path.exists(self.nhat_ky) else []

    def danh_dau(self):
        return f"{self.t.name}/home/.local/state/onebee/giao-dien"

    def test_lan_dau_dat_hinh_nen_va_ghi_danh_dau(self):
        r = self.chay()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.goi(), [
            f"set org.cinnamon.desktop.background picture-uri file://{self.hinh}",
            "set org.cinnamon.desktop.background picture-options zoom",
        ])
        self.assertTrue(os.path.exists(self.danh_dau()))

    def test_lan_hai_khong_dat_lai_de_giu_lua_chon_cua_nguoi_dung(self):
        self.chay()
        self.assertEqual(len(self.goi()), 2)
        self.chay()
        self.assertEqual(len(self.goi()), 2)   # không thêm lệnh nào

    def test_danh_dau_phien_ban_cu_thi_ap_lai(self):
        os.makedirs(os.path.dirname(self.danh_dau()))
        open(self.danh_dau(), "w").write("0\n")
        self.chay()
        self.assertEqual(len(self.goi()), 2)

    def test_thieu_hinh_nen_thi_bo_qua_khong_loi(self):
        r = self.chay(hinh=f"{self.t.name}/khong-co.png")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.goi(), [])
        self.assertFalse(os.path.exists(self.danh_dau()))

    def test_gsettings_loi_thi_khong_ghi_danh_dau_de_lan_sau_thu_lai(self):
        self.dat_gsettings(1)
        r = self.chay()
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.danh_dau()))


class TrienKhai(unittest.TestCase):
    def test_role_cai_script_va_tu_chay_khi_dang_nhap(self):
        viec = yaml.safe_load(doc(TASKS))
        noi_dung = str(viec)
        self.assertIn("/usr/local/bin/onebee-ap-giao-dien", noi_dung)
        self.assertIn("/etc/xdg/autostart/onebee-ap-giao-dien.desktop", noi_dung)
        self.assertIn("Exec=/usr/local/bin/onebee-ap-giao-dien", noi_dung)
        self.assertIn("OnlyShowIn=X-Cinnamon;", noi_dung)

    def test_bo_cai_ap_ngay_cho_phien_dang_mo_theo_loginctl(self):
        sh = doc(INSTALL)
        self.assertIn("loginctl list-sessions", sh)
        self.assertIn("runuser -u", sh)
        self.assertIn("/usr/local/bin/onebee-ap-giao-dien", sh)
        self.assertNotIn("SUDO_USER", sh)   # chỉ lấy người dùng từ chính phiên đồ họa, không đoán

    def test_loi_nhan_cuoi_khong_bao_phai_khoi_dong_lai_de_thay_giao_dien(self):
        sh = doc(INSTALL)
        self.assertNotIn("để áp dụng ngôn ngữ, bộ gõ tiếng Việt và giao diện", sh)
        self.assertIn("Khởi động lại máy để áp dụng ngôn ngữ và bộ gõ tiếng Việt", sh)


class HinhNen(unittest.TestCase):
    def test_png_ti_le_16_9_va_du_net(self):
        d = open(PNG, "rb").read(32)
        self.assertEqual(d[:8], b"\x89PNG\r\n\x1a\n")
        rong, cao = struct.unpack(">II", d[16:24])
        self.assertGreaterEqual(rong, 1920)
        self.assertEqual(rong * 9, cao * 16)

    def test_svg_chi_con_logo_khong_khau_hieu_khong_ho_so_ngoai(self):
        s = doc(SVG)
        for cam in ("Máy cũ chạy mới", "Dữ liệu ở nhà", "<text", "c2pa", "http://www.w3.org/1999/xlink", "<image"):
            self.assertNotIn(cam, s)
        self.assertIn("#F5A524", s)


if __name__ == "__main__":
    unittest.main()
