#!/usr/bin/env python3
"""Kiểm thử đơn vị cho máy trạm báo tình trạng (quan-ly-tap-trung/files/onebee-bao-tinh-trang). Chạy: python3 -m unittest"""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DUONG_DAN = os.path.join(HERE, "../../desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-tinh-trang")
# File không có đuôi .py → chỉ rõ bộ nạp mã nguồn
SPEC = importlib.util.spec_from_loader("bao_tinh_trang", importlib.machinery.SourceFileLoader("bao_tinh_trang", DUONG_DAN))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)


class SoTaiKhoanSudo(unittest.TestCase):
    def dem(self, noi_dung):
        with tempfile.NamedTemporaryFile("w", suffix=".group", delete=False, encoding="utf-8") as f:
            f.write(noi_dung)
        try:
            return bt.so_tai_khoan_sudo(f.name)
        finally:
            os.unlink(f.name)

    def test_chi_tinh_nhom_sudo_va_admin_khong_tinh_root(self):
        nd = "root:x:0:\nsudo:x:27:quanly,root\nadmin:x:110:quanly,ketoan\nusers:x:100:a,b,c\n"
        self.assertEqual(self.dem(nd), 2)  # quanly (2 nhóm, đếm 1 lần) + ketoan

    def test_khong_co_ai(self):
        self.assertEqual(self.dem("root:x:0:\nsudo:x:27:\n"), 0)

    def test_dong_hong_va_file_khong_co(self):
        self.assertEqual(self.dem("sudo:x\n\n::\n"), 0)
        self.assertIsNone(bt.so_tai_khoan_sudo("/khong-co/group"))


if __name__ == "__main__":
    unittest.main()
