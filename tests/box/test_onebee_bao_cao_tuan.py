#!/usr/bin/env python3
"""Kiểm thử đơn vị cho nhật ký tuần (box-fleet/files/onebee-bao-cao-tuan.py). Chạy: python3 -m unittest"""
import datetime as dt
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "bao_cao_tuan", os.path.join(HERE, "../../box/ansible/roles/box-fleet/files/onebee-bao-cao-tuan.py"))
bct = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bct)

YEU_CAU = '''"260928-090000-11","2026-09-28 09:00","ketoan-01","Gõ tiếng Việt","binh-thuong","Chị Lan","mật khẩu email là abc123"
"261005-080000-12","2026-10-05 08:00","kho-02","Máy in / máy quét","gap","Anh Tư","máy in HP không in"
"261006-100000-13","2026-10-06 10:00","kho-02","Phần mềm chỉ chạy trên Windows","binh-thuong","","phần mềm kế toán X"
"261007-100000-14","2026-10-07 10:00","ketoan-01","Máy in / máy quét","binh-thuong","","kẹt giấy"
'''
XU_LY = '''"260928-090000-11","2026-09-28 10:00","Hướng dẫn người dùng","15","đã chỉ Ctrl+Space"
"261005-080000-12","2026-10-05 11:00","Sửa cấu hình","40","cài driver"
"261006-100000-13","2026-10-07 10:00","Quay về Windows (máy/phần mềm)","90",""
'''
KHAO_SAT_2 = '''"2026-10-09 16:00","4","5","5","4","5","rất tốt, chị Lan phòng kế toán"
"2026-10-09 16:05","3","4","5","5","4",""
'''


def lam(thu_muc, khao_sat):
    for ten, nd in (("yeu-cau.csv", YEU_CAU), ("xu-ly.csv", XU_LY), ("khao-sat.csv", khao_sat)):
        with open(os.path.join(thu_muc, ten), "w", encoding="utf-8") as f:
            f.write(nd)
    may = {"may_tram": [{"ten": "kho-02", "canh_bao": ["ổ đĩa sắp đầy (còn 5%)"]}, {"ten": "ketoan-01", "canh_bao": []}]}
    return bct.bao_cao(thu_muc, dt.date(2026, 10, 8), may)


class BaoCaoTuan(unittest.TestCase):
    def test_dem_dung_trong_tuan(self):
        with tempfile.TemporaryDirectory() as d:
            md = lam(d, KHAO_SAT_2)
        self.assertIn("Nhật ký tuần 05/10 – 11/10/2026", md)
        self.assertIn("Mới trong tuần: **3** (gấp: 1)", md)          # yêu cầu 28/9 thuộc tuần trước
        self.assertIn("Xử lý xong trong tuần: **2**", md)
        self.assertIn("Còn mở đến cuối tuần: **1** (mã: 261007-100000-14)", md)
        self.assertIn("| Máy in / máy quét | 2 |", md)
        self.assertIn("Công xử lý: tổng 130 phút, trung vị 65 phút", md)
        self.assertIn("Phải quay về Windows trong tuần: **1** lần", md)
        self.assertIn("- kho-02: ổ đĩa sắp đầy (còn 5%)", md)

    def test_khong_lo_thong_tin_ca_nhan(self):
        with tempfile.TemporaryDirectory() as d:
            md = lam(d, KHAO_SAT_2 + '"2026-10-10 09:00","5","5","5","5","5",""\n')
        for bi_mat in ("Chị Lan", "Anh Tư", "abc123", "kẹt giấy", "cài driver", "rất tốt", "phần mềm kế toán X"):
            self.assertNotIn(bi_mat, md)
        self.assertIn("| Gõ tiếng Việt | 5 |", md)  # 3 phiếu → hiện điểm

    def test_duoi_3_phieu_khong_hien_diem(self):
        with tempfile.TemporaryDirectory() as d:
            md = lam(d, KHAO_SAT_2)
        self.assertIn("2 phiếu — chưa đủ 3 phiếu", md)
        self.assertNotIn("| Gõ tiếng Việt |", md)

    def test_chua_co_du_lieu(self):
        with tempfile.TemporaryDirectory() as d:
            md = bct.bao_cao(d, dt.date(2026, 10, 8), {})
        self.assertIn("Mới trong tuần: **0**", md)
        self.assertIn("Không có phiếu trong tuần.", md)


if __name__ == "__main__":
    unittest.main()
