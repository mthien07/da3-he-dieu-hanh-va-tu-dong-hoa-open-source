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
    may = {"may_tram": [{"ten": "kho-02", "canh_bao": ["ổ đĩa sắp đầy (còn 5%)"], "gio_tu_lan_cuoi": 80}, {"ten": "ketoan-01", "canh_bao": []}]}
    return bct.bao_cao(thu_muc, dt.date(2026, 10, 8), may, bay_gio=dt.datetime(2026, 10, 12, 8, 0))


class BaoCaoTuan(unittest.TestCase):
    def test_nhan_khop_voi_bieu_mau(self):
        import yaml
        v = yaml.safe_load(open(os.path.join(HERE, "../../box/ansible/roles/box-n8n/vars/main.yml"), encoding="utf-8"))
        self.assertEqual(v["onebee_ho_tro_loai"], bct.LOAI)
        self.assertEqual(v["onebee_ho_tro_cach_xu_ly"], bct.CACH_XU_LY)

    def test_chu_tu_do_ma_sai_va_nhieu_lan_xu_ly(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "yeu-cau.csv"), "w", encoding="utf-8") as f:
                f.write('"261005-080000-12","2026-10-05 08:00","m","Chị Lan 0909 | lương","gap","",""\n')
                f.write('"261005-090000-13","2026-10-05 09:00","m","Khác","binh-thuong","",""\n')
            with open(os.path.join(d, "xu-ly.csv"), "w", encoding="utf-8") as f:
                f.write('"261005-080000-12","2026-10-05 10:00","Chưa xử lý được","60",""\n')
                f.write('"261005-080000-12","2026-10-06 10:00","Sửa cấu hình","30",""\n')
                f.write('"999999-999999-99","2026-10-06 11:00","Sửa cấu hình","5",""\n')  # gõ nhầm mã
            md = bct.bao_cao(d, dt.date(2026, 10, 8), {})
        self.assertNotIn("Chị Lan", md)
        self.assertIn("| Khác | 2 |", md)
        self.assertIn("Xử lý xong trong tuần: **1**", md)        # mã gõ nhầm không tính
        self.assertIn("Còn mở đến cuối tuần: **1** (mã: 261005-090000-13)", md)
        self.assertIn("Công xử lý: tổng 90 phút", md)             # cộng cả lần chưa xong
        self.assertIn("trung vị 26 giờ, lâu nhất 26 giờ", md)     # tính đến lần xử lý xong

    def test_dem_dung_trong_tuan(self):
        with tempfile.TemporaryDirectory() as d:
            md = lam(d, KHAO_SAT_2)
        self.assertIn("Nhật ký tuần 05/10 – 11/10/2026", md)
        self.assertIn("Mới trong tuần: **3** (gấp: 1)", md)          # yêu cầu 28/9 thuộc tuần trước
        self.assertIn("Xử lý xong trong tuần: **2**", md)
        self.assertIn("Còn mở đến cuối tuần: **1** (mã: 261007-100000-14)", md)
        self.assertIn("| Máy in / máy quét | 2 |", md)
        self.assertIn("Công xử lý: tổng 130 phút, trung vị 65 phút/lần", md)
        self.assertIn("Phải quay về Windows trong tuần: **1** lần", md)
        self.assertIn("- kho-02: sao lưu 80 giờ trước — **cần xử lý:** ổ đĩa sắp đầy (còn 5%)", md)
        self.assertIn("- ketoan-01: chưa có bản sao lưu hợp lệ", md)
        self.assertIn("Gấp có phản hồi trong 4 giờ làm việc: **1/1**", md)  # 08:00 báo → 11:00 xử lý = 3 giờ
        self.assertIn("Đã phải quay về Windows (từ đầu sổ đến hết tuần): **1** máy — kho-02 (Phần mềm chỉ chạy trên Windows)",
                      md)

    def test_gio_lam_viec(self):
        g = bct.gio_lam_viec
        self.assertEqual(g(dt.datetime(2026, 10, 6, 8, 0), dt.datetime(2026, 10, 6, 14, 0)), 4.0)   # 3,5 sáng + 0,5 chiều
        self.assertEqual(g(dt.datetime(2026, 10, 10, 16, 0), dt.datetime(2026, 10, 12, 10, 0)), 3.5)  # T7 1 giờ, CN nghỉ, T2 2,5
        self.assertEqual(g(dt.datetime(2026, 10, 6, 12, 0), dt.datetime(2026, 10, 6, 13, 0)), 0.0)   # giờ nghỉ trưa

    def test_gap_dung_han_tre_dang_cho_va_may_la(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "yeu-cau.csv"), "w", encoding="utf-8") as f:
                f.write('"A","2026-10-06 08:00","ketoan-01","Khác","gap","",""\n')   # phản hồi đúng 4 giờ → đạt
                f.write('"B","2026-10-07 08:00","ketoan-01","Khác","gap","",""\n')   # phản hồi sau 7,5 giờ → trễ
                f.write('"C","2026-10-10 16:00","Chị Lan 0909","Khác","gap","",""\n')  # chưa phản hồi, mới 1 giờ → chờ
                f.write('"D","2026-10-09 08:00","ketoan-01","Khác","gap","",""\n')   # chưa phản hồi, quá hạn → trễ
            with open(os.path.join(d, "xu-ly.csv"), "w", encoding="utf-8") as f:
                f.write('"A","2026-10-06 14:00","Chưa xử lý được","10",""\n')
                f.write('"A","2026-10-07 09:00","Hướng dẫn người dùng","10",""\n')
                f.write('"B","2026-10-08 08:00","Sửa cấu hình","10",""\n')
                f.write('"C","2026-10-10 17:30","Quay về Windows (máy/phần mềm)","30",""\n')  # ngoài giờ, sau "bây giờ"
            md = bct.bao_cao(d, dt.date(2026, 10, 8), {"may_tram": [{"ten": "ketoan-01"}]},
                             bay_gio=dt.datetime(2026, 10, 10, 17, 0))
        self.assertIn("Gấp có phản hồi trong 4 giờ làm việc: **1/3** (trễ: B, D) · 1 đang chờ", md)
        self.assertNotIn("Chị Lan", md)
        self.assertIn("**1** máy — 1 máy ghi tên khác (Khác)", md)  # tên máy gõ tự do không in ra

    def test_khao_sat_dem_phieu_thap(self):
        with tempfile.TemporaryDirectory() as d:
            md = lam(d, KHAO_SAT_2 + '"2026-10-10 09:00","5","5","5","5","2",""\n')
        self.assertIn("| Muốn tiếp tục dùng | 3,67 | 1 |", md)  # 2 số lẻ: 3,95 không bị làm tròn thành "4"

    def test_ve_windows_dem_ca_da_sua_va_moi_ten_la(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "yeu-cau.csv"), "w", encoding="utf-8") as f:
                for ma, may in (("A", "kt-01"), ("B", "Phòng kho"), ("C", "máy chị Hoa"), ("D", "kt-01")):
                    f.write(f'"{ma}","2026-10-06 08:00","{may}","Máy in / máy quét","binh-thuong","",""\n')
            with open(os.path.join(d, "xu-ly.csv"), "w", encoding="utf-8") as f:
                f.write('"A","2026-10-06 09:00","Quay về Windows (máy/phần mềm)","30",""\n')
                f.write('"A","2026-10-07 09:00","Sửa cấu hình","30",""\n')  # sau đó sửa được — vẫn tính
                for ma in "BCD":
                    f.write(f'"{ma}","2026-10-06 09:00","Quay về Windows (máy/phần mềm)","30",""\n')
            md = bct.bao_cao(d, dt.date(2026, 10, 8), {"may_tram": [{"ten": "kt-01"}, "rác"]},
                             bay_gio=dt.datetime(2026, 10, 12, 8, 0))
        self.assertIn("**3** máy — kt-01 (Máy in / máy quét); 2 máy ghi tên khác (Máy in / máy quét)", md)
        self.assertNotIn("chị Hoa", md)
        self.assertNotIn("Phòng kho", md)

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
