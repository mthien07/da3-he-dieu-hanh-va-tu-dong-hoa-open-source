#!/usr/bin/env python3
"""Kiểm thử lệnh `onebee-nhac-sao-luu`: người đang đăng nhập nhận một thông báo (tối đa một lần mỗi ngày) khi máy đã nối Box
mà quá 72 giờ chưa sao lưu. Đường dẫn được thay bằng biến môi trường, `notify-send` là lệnh giả ghi tham số ra file.
Chạy: python3 -m unittest tests/desktop/test_onebee_nhac_sao_luu.py"""
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LENH = os.path.join(HERE, "../../desktop/ansible/roles/backup-client/files/onebee-nhac-sao-luu")
GIO = 3600


class NhacSaoLuu(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.bin_gia = os.path.join(self.tam.name, "bin")
        os.mkdir(self.bin_gia)
        self.nhat_ky = os.path.join(self.tam.name, "notify-send.log")
        gia = os.path.join(self.bin_gia, "notify-send")
        with open(gia, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\nprintf "%s\\n" "$*" >>"{self.nhat_ky}"\n')
        os.chmod(gia, os.stat(gia).st_mode | stat.S_IXUSR)
        self.cuoi = os.path.join(self.tam.name, "sao-luu-cuoi")
        self.hoi_conf = os.path.join(self.tam.name, "onebee-hoi.conf")
        self.da_nhac = os.path.join(self.tam.name, "cache", "nhac-sao-luu")

    def noi_box(self, cach_day_gio=1000):
        """Tạo file dấu hiệu máy đã nối Box, thời điểm sửa cách đây `cach_day_gio` giờ."""
        with open(self.hoi_conf, "w", encoding="utf-8") as f:
            f.write("HOI_URL=http://192.168.1.10:3000\n")
        t = time.time() - cach_day_gio * GIO
        os.utime(self.hoi_conf, (t, t))

    def ghi_lan_cuoi(self, noi_dung):
        with open(self.cuoi, "w", encoding="utf-8") as f:
            f.write(noi_dung)

    def chay(self, path=None):
        env = dict(os.environ)
        env.update({"ONEBEE_SAO_LUU_CUOI": self.cuoi, "ONEBEE_HOI_CONF": self.hoi_conf, "ONEBEE_NHAC_DAU": self.da_nhac})
        env["PATH"] = self.bin_gia if path is None else path
        r = subprocess.run([sys.executable, LENH], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def so_lan_nhac(self):
        if not os.path.exists(self.nhat_ky):
            return 0
        with open(self.nhat_ky, encoding="utf-8") as f:
            return len([d for d in f.read().splitlines() if d.strip()])

    def noi_dung_nhac(self):
        with open(self.nhat_ky, encoding="utf-8") as f:
            return f.read()

    def test_chua_noi_box_thi_im_lang(self):
        self.ghi_lan_cuoi(str(int(time.time()) - 500 * GIO))   # rất lâu chưa sao lưu, nhưng máy chưa nối Box
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 0)

    def test_sao_luu_moi_thi_im_lang(self):
        self.noi_box()
        self.ghi_lan_cuoi(str(int(time.time()) - 10 * GIO))
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 0)

    def test_qua_72_gio_thi_nhac_mot_lan_moi_ngay(self):
        self.noi_box()
        self.ghi_lan_cuoi(str(int(time.time()) - 80 * GIO))
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 1)
        nhac = self.noi_dung_nhac()
        self.assertIn("chưa sao lưu", nhac)
        self.assertIn("3 ngày", nhac)
        self.assertIn("Báo cần hỗ trợ", nhac)
        self.chay()   # cùng ngày: không nhắc thêm
        self.assertEqual(self.so_lan_nhac(), 1)
        # Sang ngày khác (dấu ghi ngày hôm qua) thì nhắc lại
        with open(self.da_nhac, "w", encoding="utf-8") as f:
            f.write("2000-01-01\n")
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 2)

    def test_chua_tung_sao_luu(self):
        # Chưa có file lần cuối: tính từ lúc máy nối Box (thời điểm sửa file cấu hình)
        self.noi_box(cach_day_gio=80)
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 1)
        self.assertIn("chưa sao lưu", self.noi_dung_nhac())
        os.remove(self.da_nhac)
        os.remove(self.nhat_ky)
        self.noi_box(cach_day_gio=5)
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 0)

    def test_tep_hong_khong_lam_vo_lenh(self):
        self.noi_box(cach_day_gio=80)
        self.ghi_lan_cuoi("abc")
        self.chay()   # coi như chưa từng sao lưu → tính từ lúc nối Box (80 giờ) → nhắc
        self.assertEqual(self.so_lan_nhac(), 1)

    def test_dong_ho_lech_ve_tuong_lai_thi_im_lang(self):
        self.noi_box()
        self.ghi_lan_cuoi(str(int(time.time()) + 10 * GIO))
        self.chay()
        self.assertEqual(self.so_lan_nhac(), 0)

    def test_khong_co_notify_send_thi_thoat_im_lang(self):
        self.noi_box()
        self.ghi_lan_cuoi(str(int(time.time()) - 80 * GIO))
        thu_muc_trong = os.path.join(self.tam.name, "trong")
        os.mkdir(thu_muc_trong)
        r = self.chay(path=thu_muc_trong)
        self.assertEqual(r.stderr, "")
        self.assertFalse(os.path.exists(self.da_nhac), "chưa nhắc được thì không được ghi dấu đã nhắc")


if __name__ == "__main__":
    unittest.main()
