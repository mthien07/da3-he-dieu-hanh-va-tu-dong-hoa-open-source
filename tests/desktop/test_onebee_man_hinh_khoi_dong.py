#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử chủ đề Plymouth của OneBee: tệp chủ đề khớp nhau, tác vụ Ansible đặt chủ đề mặc định đúng cách và chỉ dựng lại
initramfs khi có thay đổi (lần cài thứ hai không đổi gì). Không cần Plymouth thật. Chạy: python3 -m unittest"""
import configparser
import os
import re
import struct
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "../../desktop/ansible/roles/theme")
THU_MUC = os.path.join(THEME, "files/plymouth")
TASKS = os.path.join(THEME, "tasks/man-hinh-khoi-dong.yml")
MAIN = os.path.join(THEME, "tasks/main.yml")
DICH = "/usr/share/plymouth/themes/onebee"


def doc(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def kich_thuoc_png(p):
    d = open(p, "rb").read(32)
    assert d[:8] == b"\x89PNG\r\n\x1a\n", p
    return struct.unpack(">II", d[16:24])


class TepChuDe(unittest.TestCase):
    def test_tep_plymouth_dung_module_script_va_duong_dan_dich(self):
        cp = configparser.RawConfigParser()
        cp.read_string(doc(os.path.join(THU_MUC, "onebee.plymouth")))
        self.assertEqual(cp["Plymouth Theme"]["ModuleName"], "script")
        self.assertEqual(cp["script"]["ImageDir"], DICH)
        self.assertEqual(cp["script"]["ScriptFile"], f"{DICH}/onebee.script")

    def test_script_co_logo_thanh_tien_trinh_va_o_nhap_mat_khau(self):
        s = doc(os.path.join(THU_MUC, "onebee.script"))
        for thanh_phan in ("Image(\"logo.png\")", "Image(\"thanh-nen.png\")", "Image(\"thanh-tien-trinh.png\")",
                           "Plymouth.SetBootProgressFunction", "Plymouth.SetDisplayPasswordFunction",
                           "Plymouth.SetDisplayNormalFunction"):
            self.assertIn(thanh_phan, s)   # máy mã hóa ổ đĩa vẫn thấy ô nhập mật khẩu khi khởi động

    def test_moi_anh_script_goi_deu_co_trong_thu_muc(self):
        s = doc(os.path.join(THU_MUC, "onebee.script"))
        for ten in set(re.findall(r'Image\("([^"]+\.png)"\)', s)):
            self.assertTrue(os.path.isfile(os.path.join(THU_MUC, ten)), ten)

    def test_thanh_tien_trinh_cung_kich_thuoc_voi_thanh_nen(self):
        self.assertEqual(kich_thuoc_png(os.path.join(THU_MUC, "thanh-nen.png")),
                         kich_thuoc_png(os.path.join(THU_MUC, "thanh-tien-trinh.png")))


class TacVuAnsible(unittest.TestCase):
    def setUp(self):
        self.viec = yaml.safe_load(doc(TASKS))
        self.chuoi = str(self.viec)

    def test_chi_chay_khi_may_co_plymouth_va_initramfs(self):
        self.assertIn("/usr/share/plymouth/themes", doc(TASKS))
        self.assertIn("/usr/sbin/update-initramfs", doc(TASKS))
        for v in self.viec[3:]:   # hai việc stat và set_fact đầu là phần tính cờ
            self.assertIn("when", v, v.get("name"))

    def test_chep_chu_de_vao_thu_muc_plymouth(self):
        self.assertIn(DICH, self.chuoi)
        for ten in ("onebee.plymouth", "onebee.script", "logo.png", "thanh-nen.png", "thanh-tien-trinh.png"):
            self.assertIn(ten, self.chuoi)

    def test_dat_chu_de_mac_dinh_bang_update_alternatives_chi_khi_dang_khac(self):
        self.assertIn("update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth", self.chuoi)
        self.assertIn("update-alternatives --set default.plymouth", self.chuoi)
        self.assertIn("update-alternatives --query default.plymouth", self.chuoi)
        dat = next(v for v in self.viec if "--set default.plymouth" in str(v))
        self.assertIn("when", dat)   # đã đúng chủ đề thì không đặt lại → lần hai changed=0

    def test_dung_lai_initramfs_chi_khi_vua_doi_chu_de(self):
        v = next(x for x in self.viec if x.get("ansible.builtin.command") == "update-initramfs -u")
        self.assertIn("is changed", str(v["when"]))
        self.assertTrue(v.get("changed_when"))

    def test_main_goi_tac_vu_man_hinh_khoi_dong(self):
        self.assertIn("man-hinh-khoi-dong.yml", doc(MAIN))


if __name__ == "__main__":
    unittest.main()
