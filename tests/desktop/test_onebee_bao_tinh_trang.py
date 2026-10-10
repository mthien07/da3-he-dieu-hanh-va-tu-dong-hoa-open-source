#!/usr/bin/env python3
"""Kiểm thử đơn vị cho máy trạm báo tình trạng (quan-ly-tap-trung/files/onebee-bao-tinh-trang). Chạy: python3 -m unittest"""
import importlib.machinery
import importlib.util
import json
import os
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DUONG_DAN = os.path.join(HERE, "../../desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-tinh-trang")
# File không có đuôi .py → chỉ rõ bộ nạp mã nguồn
SPEC = importlib.util.spec_from_loader("bao_tinh_trang", importlib.machinery.SourceFileLoader("bao_tinh_trang", DUONG_DAN))
bt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bt)
# Mã phía Box kiểm chữ ký — hai bên phải ra cùng một kết quả
SPEC_BOX = importlib.util.spec_from_file_location(
    "may_tram", os.path.join(HERE, "../../box/ansible/roles/box-fleet/files/onebee-may-tram.py"))
box = importlib.util.module_from_spec(SPEC_BOX)
SPEC_BOX.loader.exec_module(box)


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


class ChuKy(unittest.TestCase):
    def test_vector_co_dinh_trung_voi_phia_box(self):
        # Cùng vector với tests/box/test_onebee_may_tram.py (đã đối chiếu bằng openssl): hai phía ký/kiểm phải khớp từng bit
        self.assertEqual(bt.ky_bao_cao("mat-khau", '{"a": 1}'), "74a539bdbbb008e1811d060d2cce3a6685b0673d55d18df3cfe18fb1eca665b5")
        self.assertEqual(bt.ky_bao_cao("Mật khẩu có dấu 123", '{"ten": "a"}'),
                         "f58ed6c936281dcd7a5152a1cd38c078dcbbcc69de140788f8c4ba3f9181c569")

    def test_khop_voi_ma_phia_box(self):
        for mk, dl in (("mat-khau", "{}"), ("Mật khẩu có dấu 123", '{"ten": "a", "ghi_chú": "đ"}')):
            self.assertEqual(bt.ky_bao_cao(mk, dl), box.ky_bao_cao(mk, dl))

    def test_dong_goi_co_ky_box_kiem_duoc(self):
        goi = bt.dong_goi({"ten": "ketoan-01", "ip": "192.168.1.9", "cap_nhat_cho": 2}, "mat-khau-kho")
        self.assertEqual(set(goi), {"ten", "du_lieu", "ky"})
        self.assertEqual(goi["ky"], box.ky_bao_cao("mat-khau-kho", goi["du_lieu"]))
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "may-ketoan-01-repo"), "w") as f:
                f.write("mat-khau-kho\n")
            env = dict(goi, nhan_luc=time.time(), dinh_dang=2)
            tt, trang_thai = box.kiem_chu_ky(env, "ketoan-01", d)
            self.assertEqual((trang_thai, tt["ip"], tt["cap_nhat_cho"]), ("hop-le", "192.168.1.9", 2))
            self.assertAlmostEqual(json.loads(goi["du_lieu"])["gui_luc"], time.time(), delta=5)

    def test_thieu_mat_khau_gui_dang_cu(self):
        tt = {"ten": "a", "ip": "10.0.0.5"}
        self.assertEqual(bt.dong_goi(tt, None), tt)
        self.assertEqual(bt.dong_goi(tt, ""), tt)


if __name__ == "__main__":
    unittest.main()
