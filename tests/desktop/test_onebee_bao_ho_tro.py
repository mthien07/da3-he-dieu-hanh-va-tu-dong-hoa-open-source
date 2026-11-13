#!/usr/bin/env python3
"""Kiểm thử lệnh `onebee-bao-ho-tro`: mở biểu mẫu "Báo cần hỗ trợ" của Box với tên máy (và loại sự cố, mô tả) đã điền sẵn.
Địa chỉ biểu mẫu chỉ lấy từ file cấu hình do root ghi; tham số của người dùng được mã hóa phần trăm. Chạy: python3 -m unittest"""
import importlib.machinery
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
LENH = os.path.join(HERE, "../../desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-ho-tro")
BIEU_MAU = "http://192.168.1.10:5678/form/onebee-ho-tro"


def nap_lenh():
    spec = importlib.util.spec_from_loader("onebee_bao_ho_tro", importlib.machinery.SourceFileLoader("onebee_bao_ho_tro", LENH))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DungDiaChi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = nap_lenh()

    def test_dia_chi_co_ten_may_va_ma_hoa_tieng_viet(self):
        url = self.m.dung_dia_chi(BIEU_MAU, may="ketoan-01", loai="Máy in / máy quét", mo_ta="Đang in thì báo lỗi mực")
        self.assertTrue(url.startswith(BIEU_MAU + "?"), url)
        self.assertIn("may=ketoan-01", url)
        self.assertIn("loai=M%C3%A1y%20in%20%2F%20m%C3%A1y%20qu%C3%A9t", url)
        self.assertIn("mo_ta=%C4%90ang%20in%20th%C3%AC%20b%C3%A1o%20l%E1%BB%97i%20m%E1%BB%B1c", url)
        self.assertNotIn("+", url)

    def test_bo_tham_so_rong(self):
        url = self.m.dung_dia_chi(BIEU_MAU, may="ketoan-01", loai="", mo_ta="")
        self.assertEqual(url, BIEU_MAU + "?may=ketoan-01")
        self.assertEqual(self.m.dung_dia_chi(BIEU_MAU, may="ketoan-01"), BIEU_MAU + "?may=ketoan-01")

    def test_mo_ta_dai_bi_cat(self):
        url = self.m.dung_dia_chi(BIEU_MAU, may="ketoan-01", mo_ta="a" * 5000)
        mo_ta = parse_qs(urlsplit(url).query)["mo_ta"][0]
        self.assertEqual(mo_ta, "a" * 1200 + "…")

    def test_mo_ta_vua_du_khong_bi_cat(self):
        url = self.m.dung_dia_chi(BIEU_MAU, may="ketoan-01", mo_ta="b" * 1200)
        self.assertEqual(parse_qs(urlsplit(url).query)["mo_ta"][0], "b" * 1200)

    def test_ky_tu_dac_biet_khong_thoat_khoi_gia_tri(self):
        url = self.m.dung_dia_chi(BIEU_MAU, may="a&b=c", mo_ta="x&muc_do=Khẩn#y")
        q = parse_qs(urlsplit(url).query)
        self.assertEqual(q["may"], ["a&b=c"])
        self.assertEqual(q["mo_ta"], ["x&muc_do=Khẩn#y"])
        self.assertNotIn("muc_do", q)


class DocDiaChi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = nap_lenh()

    def doc(self, noi_dung):
        with tempfile.TemporaryDirectory() as t:
            tep = os.path.join(t, "ho-tro.conf")
            with open(tep, "w", encoding="utf-8") as f:
                f.write(noi_dung)
            return self.m.doc_dia_chi(tep)

    def test_doc_dia_chi_hop_le(self):
        self.assertEqual(self.doc(f"# Quản lý bởi OneBee OS\nHO_TRO_URL={BIEU_MAU}\n"), BIEU_MAU)
        self.assertEqual(self.doc(f"HO_TRO_URL={BIEU_MAU}\r\n"), BIEU_MAU)
        self.assertEqual(self.doc("HO_TRO_URL=https://box.onebee.lan/form/onebee-ho-tro\n"), "https://box.onebee.lan/form/onebee-ho-tro")

    def test_tu_choi_dia_chi_la(self):
        for xau in ("file:///etc/passwd", "javascript:alert(1)", "ftp://192.168.1.10/x", "192.168.1.10:5678/form",
                    "http://192.168.1.10:5678/a b", "http://192.168.1.10/x\tevil", "http://", ""):
            with self.subTest(xau=xau):
                self.assertIsNone(self.doc(f"HO_TRO_URL={xau}\n"))

    def test_file_khong_ton_tai_hoac_thieu_khoa(self):
        self.assertIsNone(self.m.doc_dia_chi("/khong/co/file/nay"))
        self.assertIsNone(self.doc("# chỉ có chú thích\nKHAC=1\n"))


class ChayLenh(unittest.TestCase):
    def chay(self, tham_so, env_them, path=None):
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "ONEBEE_HO_TRO_CONF")}
        env["DISPLAY"] = ""
        if path:
            env["PATH"] = path + os.pathsep + env.get("PATH", "")
        env.update(env_them)
        return subprocess.run([sys.executable, LENH, *tham_so], env=env, capture_output=True, text=True, timeout=30)

    def test_chua_noi_box_thi_bao_ro(self):
        r = self.chay([], {"ONEBEE_HO_TRO_CONF": "/khong/co/file/nay"})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("chưa nối OneBee Box", r.stderr)

    def test_tro_giup(self):
        r = self.chay(["--help"], {"ONEBEE_HO_TRO_CONF": "/khong/co/file/nay"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--mo-ta", r.stdout)
        self.assertIn("--loai", r.stdout)

    def test_mo_trinh_duyet_voi_dia_chi_da_dien(self):
        with tempfile.TemporaryDirectory() as t:
            bin_gia = os.path.join(t, "bin")
            os.mkdir(bin_gia)
            ghi = os.path.join(t, "xdg-open.log")
            gia = os.path.join(bin_gia, "xdg-open")
            with open(gia, "w", encoding="utf-8") as f:
                f.write(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{ghi}.tmp" && mv "{ghi}.tmp" "{ghi}"\n')
            os.chmod(gia, os.stat(gia).st_mode | stat.S_IXUSR)
            conf = os.path.join(t, "ho-tro.conf")
            with open(conf, "w", encoding="utf-8") as f:
                f.write(f"# Quản lý bởi OneBee OS\nHO_TRO_URL={BIEU_MAU}\n")
            r = self.chay(["--mo-ta", "thử"], {"ONEBEE_HO_TRO_CONF": conf}, path=bin_gia)
            self.assertEqual(r.returncode, 0, r.stderr)
            han = time.time() + 10
            while not os.path.exists(ghi) and time.time() < han:   # xdg-open giả được chạy nền, đợi nó ghi xong
                time.sleep(0.05)
            with open(ghi, encoding="utf-8") as f:
                url = f.read().strip()
            self.assertTrue(url.startswith(BIEU_MAU + "?"), url)
            self.assertIn("may=", url)
            self.assertIn("mo_ta=th%E1%BB%AD", url)
            self.assertNotIn("loai=", url)


if __name__ == "__main__":
    unittest.main()
