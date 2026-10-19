#!/usr/bin/env python3
"""Kiểm thử onebee-loi-tat-chia-se (role ket-noi-box): đặt lối tắt "Chia sẻ nội bộ (OneBee Box)" lên màn hình nền khi đăng nhập —
đặt 1 lần, người dùng xóa thì không đặt lại, Box đổi IP thì làm mới, bản người dùng tự sửa thì giữ; chưa nối Box thì không làm gì.
Lệnh giả: xdg-user-dir (thư mục màn hình nền tiếng Việt), gio. Chạy: python3 -m unittest"""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LENH = os.path.join(HERE, "../../desktop/ansible/roles/ket-noi-box/files/onebee-loi-tat-chia-se")


def loi_tat(ip):
    return ("[Desktop Entry]\nType=Application\nName=Chia sẻ nội bộ (OneBee Box)\n"
            f"Exec=nemo smb://{ip}/chung\nIcon=folder-remote\nX-OneBee=1\n")


class LoiTatChiaSe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.desk = os.path.join(self.home, "Màn hình nền")
        self.bin = os.path.join(self.tmp, "bin")
        self.goc = os.path.join(self.tmp, "onebee-chia-se-noi-bo.desktop")
        self.nhat_ky = os.path.join(self.tmp, "gio.log")
        os.makedirs(self.bin)
        os.makedirs(self.home)
        for ten, than in {"xdg-user-dir": f'echo "{self.desk}"', "gio": f'echo "$*" >> "{self.nhat_ky}"'}.items():
            p = os.path.join(self.bin, ten)
            with open(p, "w") as f:
                f.write(f"#!/bin/bash\n{than}\n")
            os.chmod(p, 0o755)
        self.dich = os.path.join(self.desk, "onebee-chia-se-noi-bo.desktop")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def dat_goc(self, ip):
        with open(self.goc, "w") as f:
            f.write(loi_tat(ip))

    def chay(self):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": self.home, "ONEBEE_LOI_TAT_GOC": self.goc}
        r = subprocess.run(["bash", LENH], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)

    def doc(self):
        with open(self.dich) as f:
            return f.read()

    def test_chua_noi_box_khong_lam_gi(self):
        self.chay()
        self.assertFalse(os.path.exists(self.desk))

    def test_lan_dau_dat_vao_man_hinh_nen_tieng_viet_va_tin_cay(self):
        self.dat_goc("192.168.1.10")
        self.chay()
        self.assertIn("smb://192.168.1.10/chung", self.doc())
        self.assertTrue(os.stat(self.dich).st_mode & stat.S_IXUSR)       # Nemo chỉ chạy lối tắt có quyền chạy
        with open(self.nhat_ky) as f:
            self.assertIn(f"set {self.dich} metadata::trusted true", f.read())

    def test_nguoi_dung_xoa_thi_khong_dat_lai(self):
        self.dat_goc("192.168.1.10")
        self.chay()
        os.remove(self.dich)
        self.chay()
        self.assertFalse(os.path.exists(self.dich))

    def test_box_doi_ip_thi_lam_moi(self):
        self.dat_goc("192.168.1.10")
        self.chay()
        self.dat_goc("192.168.1.20")
        self.chay()
        self.assertIn("smb://192.168.1.20/chung", self.doc())

    def test_ban_nguoi_dung_tu_sua_thi_giu(self):
        self.dat_goc("192.168.1.10")
        self.chay()
        with open(self.dich, "w") as f:
            f.write("[Desktop Entry]\nType=Application\nName=Ổ chung của tôi\nExec=nemo smb://nas/chung\n")
        self.dat_goc("192.168.1.20")
        self.chay()
        self.assertIn("Ổ chung của tôi", self.doc())


if __name__ == "__main__":
    unittest.main()
