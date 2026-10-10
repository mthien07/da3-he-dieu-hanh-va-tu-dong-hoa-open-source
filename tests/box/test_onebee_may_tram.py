#!/usr/bin/env python3
"""Kiểm thử đơn vị cho báo cáo tình trạng máy trạm (box-fleet/files/onebee-may-tram.py). Chạy: python3 -m unittest"""
import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "may_tram", os.path.join(HERE, "../../box/ansible/roles/box-fleet/files/onebee-may-tram.py"))
mt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mt)


class DanhGia(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.tot = {"ten": "a", "nhan_luc": self.now - 600, "o_trong_phan_tram": 60, "cap_nhat_cho": 0,
                    "bao_mat_cho": 0, "can_khoi_dong_lai": False}

    def test_may_on(self):
        cb, tom = mt.danh_gia("a", 5, self.tot, self.now)
        self.assertEqual(cb, [])
        self.assertIn("sao lưu 5 giờ trước", tom)
        self.assertIn("đã cập nhật", tom)

    def test_chua_sao_luu_chua_bao(self):
        cb, _ = mt.danh_gia("a", None, None, self.now)
        self.assertEqual(len(cb), 2)
        self.assertIn("chưa từng sao lưu", cb[0])

    def test_cac_nguong(self):
        tt = dict(self.tot, nhan_luc=self.now - 3 * 86400, o_trong_phan_tram=5, bao_mat_cho=4, can_khoi_dong_lai=True)
        cb, _ = mt.danh_gia("a", 100, tt, self.now)
        chu = " | ".join(cb)
        for y in ("quá 3 ngày chưa sao lưu", "3 ngày không liên lạc", "ổ đĩa sắp đầy (còn 5%)",
                  "4 bản vá bảo mật", "cần khởi động lại"):
            self.assertIn(y, chu)

    def test_canh_bao_nhieu_tai_khoan_sudo(self):
        # Chủ trương: nhân viên không có sudo → chỉ 1 tài khoản (quản trị máy) là bình thường
        cb, _ = mt.danh_gia("a", 5, dict(self.tot, sudo_so=1), self.now)
        self.assertEqual(cb, [])
        cb, _ = mt.danh_gia("a", 5, dict(self.tot, sudo_so=3), self.now)
        self.assertEqual(len(cb), 1)
        self.assertIn("3 tài khoản có quyền sudo", cb[0])
        # máy chạy mã cũ (không có trường) hoặc dữ liệu sai kiểu: không báo nhầm
        for v in ({}, {"sudo_so": "abc"}, {"sudo_so": True}, {"sudo_so": None}):
            cb, _ = mt.danh_gia("a", 5, dict(self.tot, **v), self.now)
            self.assertEqual(cb, [], v)

    def test_du_lieu_la_khong_lam_hong(self):
        tt = dict(self.tot, o_trong_phan_tram="abc", cap_nhat_cho=True, can_khoi_dong_lai="true")
        cb, _ = mt.danh_gia("a", 1, tt, self.now)
        self.assertEqual(cb, [])  # chuỗi/boolean sai kiểu bị bỏ qua, không báo nhầm


class DocFile(unittest.TestCase):
    def test_bo_qua_file_sai_ten_va_ten_khong_hop_le(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.json"), "w") as f:
                json.dump({"ten": "b", "ip": "10.0.0.5"}, f)  # file a.json nhưng ghi tên b → bỏ
            with open(os.path.join(d, "c.json"), "w") as f:
                json.dump({"ten": "c", "ip": "10.0.0.7; rm -rf /"}, f)
            self.assertIsNone(mt.doc_tinh_trang(d, "a"))
            buf = io.StringIO()
            with redirect_stdout(buf):
                mt.main(["x", "kho", d, "a", "c", "../c"])
            self.assertEqual(buf.getvalue(), "")  # IP bậy không lọt vào danh sách máy để SSH

    def test_kho_bo_bao_cao_cu_hon_2_gio(self):
        with tempfile.TemporaryDirectory() as d:
            for ten, tuoi in (("moi", 600), ("cu", 3 * 3600)):
                with open(os.path.join(d, f"{ten}.json"), "w") as f:
                    json.dump({"ten": ten, "ip": "192.168.1.9", "nhan_luc": time.time() - tuoi}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                mt.main(["x", "kho", d, "moi", "cu"])
            self.assertEqual(buf.getvalue(), "moi 192.168.1.9\n")  # IP cũ có thể đã sang máy khác

    def test_loi_doc_kho_khac_chua_sao_luu(self):
        rows = mt.tong_hop("/khong-co", ["a=loi", "b=null", "c=-5000"])
        self.assertIn("không đọc được kho", rows[0]["canh_bao"][0])
        self.assertIn("chưa từng sao lưu", rows[1]["canh_bao"][0])
        self.assertIn("ngày tương lai", rows[2]["canh_bao"][0])  # bản giả mạo không được coi là "vừa sao lưu"

    def test_payload_thu_khong_doc_may(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            mt.main(["x", "payload", "/khong-co", "THU", "nd", "a=5"])
        self.assertEqual(json.loads(buf.getvalue())["may_tram"], [])


if __name__ == "__main__":
    unittest.main()
