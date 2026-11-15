# SPDX-License-Identifier: MIT
"""Kiểm thử kho tệp nội bộ SeaweedFS + kiểm dịch ClamAV (Giai đoạn 7)."""
import importlib.util
import os
import tempfile
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
KHO_TEP_PY = os.path.join(ROOT, "box/ansible/roles/box-kho-tep/files/onebee-kho-tep.py")
GROUP_VARS = os.path.join(ROOT, "box/ansible/group_vars/all.yml")
TEMPLATES = os.path.join(ROOT, "box/ansible/roles/box-stack/templates")


def _load_kho_tep():
    spec = importlib.util.spec_from_file_location("onebee_kho_tep", KHO_TEP_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestKhoTepVaClamAvQuarantine(unittest.TestCase):
    def setUp(self):
        self.mod = _load_kho_tep()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = self.mod.KhoTepStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_eicar_bi_cach_ly_422(self):
        status, ban_ghi = self.store.luu_va_quet("nhanvien1", "hoa-don-eicar.com", self.mod.EICAR_BYTES)
        self.assertEqual(status, 422)
        self.assertEqual(ban_ghi["trang_thai_quet"], "INFECTED")
        self.assertIn("Eicar-Test-Signature", ban_ghi["clamd"])
        dl_status, _, _ = self.store.doc_tep(ban_ghi["ma_tep"], "nhanvien1", ["nhan_vien"])
        self.assertEqual(dl_status, 422)
        self.assertEqual(len(os.listdir(os.path.join(self.tmp.name, "cach-ly"))), 1)

    def test_tep_sach_luu_va_tai_duoc(self):
        noi_dung = "Hợp đồng mua bán mật ong hoa nhãn số 01/2026.".encode("utf-8")
        status, ban_ghi = self.store.luu_va_quet("nhanvien1", "hop-dong.txt", noi_dung)
        self.assertEqual(status, 201)
        self.assertEqual(ban_ghi["trang_thai_quet"], "CLEAN")
        dl_status, raw, _ = self.store.doc_tep(ban_ghi["ma_tep"], "nhanvien1", ["nhan_vien"])
        self.assertEqual(dl_status, 200)
        self.assertEqual(raw, noi_dung)

    def test_duoi_tep_nguy_hiem_bi_tu_choi_415(self):
        for ten, data in (("ma-doc.exe", b"MZ\x90\x00"), ("script.sh", b"#!/bin/sh\n")):
            status, _ = self.store.luu_va_quet("nhanvien1", ten, data)
            self.assertEqual(status, 415)

    def test_gioi_han_kich_thuoc_10mb(self):
        self.assertEqual(self.mod.MAX_UPLOAD_BYTES, 10 * 1024 * 1024)

    def test_cap_nhat_chu_ky_clamav_ngoai_tuyen(self):
        nguon = os.path.join(self.tmp.name, "usb")
        dich = os.path.join(self.tmp.name, "clamav")
        os.makedirs(nguon)
        with open(os.path.join(nguon, "daily.cvd"), "wb") as f:
            f.write(b"ClamAV-VDB:" + b"x" * 100)
        ds = self.mod.cap_nhat_chu_ky_clamav(nguon, dich)
        self.assertEqual(ds, ["daily.cvd"])
        self.assertTrue(os.path.exists(os.path.join(dich, "daily.cvd")))
        rong = os.path.join(self.tmp.name, "usb-rong")
        os.makedirs(rong)
        with self.assertRaises(ValueError):
            self.mod.cap_nhat_chu_ky_clamav(rong, dich)

    def test_render_compose_caddy_va_cli_co_kho_tep(self):
        with open(GROUP_VARS, encoding="utf-8") as f:
            v = yaml.safe_load(f)
        self.assertIn("seaweedfs", v["onebee_box_images"])
        self.assertIn("clamav", v["onebee_box_images"])
        v.update(
            onebee_box_ip="192.168.1.50",
            onebee_box_ma_don_vi="anphu",
            onebee_box_https=False,
            onebee_https_hieu_luc=False,
            onebee_kuma_dia_chi="0.0.0.0",
        )
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
        env.filters["bool"] = bool
        with open(os.path.join(TEMPLATES, "docker-compose.yml.j2"), encoding="utf-8") as f:
            compose_yaml = yaml.safe_load(env.from_string(f.read()).render(**v))
        self.assertIn("seaweedfs", compose_yaml["services"])
        self.assertIn("kho-tep", compose_yaml["services"])
        with open(os.path.join(TEMPLATES, "Caddyfile.j2"), encoding="utf-8") as f:
            caddy = env.from_string(f.read()).render(**v)
        self.assertIn("handle /files/*", caddy)
        self.assertIn("reverse_proxy kho-tep:8080", caddy)


if __name__ == "__main__":
    unittest.main()
