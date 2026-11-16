#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Kiểm thử đơn vị cho công cụ chuyển dữ liệu sổ cũ sang PostgreSQL."""
import csv
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(HERE, "../../box/ansible/roles/box-du-lieu/files/onebee-chuyen-du-lieu.py")
FIXTURES = os.path.join(HERE, "fixtures/so-cu")


def tai_mo_dun():
    spec = importlib.util.spec_from_file_location("onebee_chuyen_du_lieu", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tach_khoi_copy(sql):
    """Tách văn bản SQL thành (danh sách câu lệnh ngoài COPY, dict {tên_bảng_đích: danh sách dòng CSV đã đọc})."""
    ngoai_copy = []
    du_lieu_copy = []
    dang_copy = False
    dong_tam = []
    for dong in sql.splitlines():
        if not dang_copy:
            ngoai_copy.append(dong)
            if dong.startswith("COPY ") and "FROM STDIN" in dong:
                dang_copy = True
                dong_tam = []
        else:
            if dong == r"\.":
                dang_copy = False
                ngoai_copy.append(dong)
                van_ban_csv = "\n".join(dong_tam) + ("\n" if dong_tam else "")
                du_lieu_copy.append(list(csv.reader(io.StringIO(van_ban_csv))))
            else:
                dong_tam.append(dong)
    return "\n".join(ngoai_copy), du_lieu_copy


class ChuyenDuLieuTest(unittest.TestCase):
    def setUp(self):
        self.cdl = tai_mo_dun()

    def chay_in_sql(self, thu_muc):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            ma = self.cdl.main([SCRIPT_PATH, thu_muc, "--in-sql"])
        return ma, out.getvalue(), err.getvalue()

    def test_bo_mau_so_cu_dung_so_dong_va_on_conflict(self):
        ma, sql, err = self.chay_in_sql(FIXTURES)
        self.assertEqual(ma, 0, msg=err)
        ngoai_copy, cac_khoi = tach_khoi_copy(sql)
        # 5 khối: don_hang (3), yeu_cau_ho_tro (3), xu_ly_ho_tro (2), khao_sat (3), tinh_trang_may (2 tệp = 2 dòng)
        tong_theo_bang = {}
        for dong in ngoai_copy.splitlines():
            if dong.startswith("INSERT INTO onebee."):
                ten_bang = dong.split("INSERT INTO onebee.", 1)[1].split()[0]
                tong_theo_bang[ten_bang] = tong_theo_bang.get(ten_bang, 0) + 1
        for bang in ("don_hang", "yeu_cau_ho_tro", "xu_ly_ho_tro", "khao_sat", "tinh_trang_may"):
            self.assertIn(bang, tong_theo_bang)
        # Đếm tổng số dòng dữ liệu COPY
        so_dong_copy = sum(len(k) for k in cac_khoi)
        self.assertEqual(so_dong_copy, 3 + 3 + 2 + 3 + 2)
        # Kiểm tra đúng số dòng từng bảng trong các khối COPY
        self.assertEqual(len(cac_khoi[0]), 3)  # don_hang
        self.assertEqual(cac_khoi[0][0][0], "don-hang/don-hang-2026-10.csv")
        self.assertEqual(cac_khoi[0][0][1], "1")
        self.assertEqual(len(cac_khoi[1]), 3)  # yeu_cau_ho_tro
        self.assertEqual(cac_khoi[1][0][0], "ho-tro/yeu-cau.csv")
        self.assertEqual(len(cac_khoi[2]), 2)  # xu_ly_ho_tro
        self.assertEqual(cac_khoi[2][0][0], "ho-tro/xu-ly.csv")
        self.assertEqual(len(cac_khoi[3]), 3)  # khao_sat
        self.assertEqual(cac_khoi[3][0][0], "ho-tro/khao-sat.csv")
        # 4 bảng CSV đều có ON CONFLICT (nguon, dong) DO NOTHING
        self.assertEqual(ngoai_copy.count("ON CONFLICT (nguon, dong) DO NOTHING"), 4)
        # Tình trạng máy có ON CONFLICT (ten) DO UPDATE SET bao_bi = EXCLUDED.bao_bi, nhan_luc = EXCLUDED.nhan_luc
        self.assertIn(
            "ON CONFLICT (ten) DO UPDATE SET bao_bi = EXCLUDED.bao_bi, nhan_luc = EXCLUDED.nhan_luc",
            ngoai_copy,
        )

    def test_ky_tu_dac_biet_va_sql_injection_nam_trong_copy(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "chung/don-hang"))
            chuoi_nguy_hiem = "Khách 'A', B\nDòng 2 '); DROP TABLE onebee.don_hang; --"
            with open(os.path.join(d, "chung/don-hang/don-hang-2026-10.csv"), "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["2026-10-05 08:30", chuoi_nguy_hiem, "Mật ong, sáp", "2", "100000", "200000", "2026-10-10", "Ghi chú 'thử'"])
            ma, sql, err = self.chay_in_sql(d)
            self.assertEqual(ma, 0, msg=err)
            ngoai_copy, cac_khoi = tach_khoi_copy(sql)
            self.assertNotIn("DROP TABLE onebee.don_hang", ngoai_copy)
            self.assertNotIn("Khách 'A'", ngoai_copy)
            self.assertEqual(len(cac_khoi), 1)
            self.assertEqual(len(cac_khoi[0]), 1)
            self.assertEqual(cac_khoi[0][0][3], chuoi_nguy_hiem)
            self.assertEqual(cac_khoi[0][0][4], "Mật ong, sáp")
            self.assertEqual(cac_khoi[0][0][9], "Ghi chú 'thử'")

    def test_dong_sai_dung_ca_tep_do_nhung_tep_khac_van_chay(self):
        # 1) Thiếu cột ở yeu-cau.csv, nhưng xu-ly.csv hợp lệ
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ho-tro"))
            with open(os.path.join(d, "ho-tro/yeu-cau.csv"), "w", encoding="utf-8") as f:
                f.write('"261005-080000-11","2026-10-05 08:00","ketoan-01","Gõ tiếng Việt","binh-thuong","","ok"\n')
                f.write('"261006-091500-22","2026-10-06 09:15"\n')  # dòng 2 thiếu cột
            with open(os.path.join(d, "ho-tro/xu-ly.csv"), "w", encoding="utf-8") as f:
                f.write('"261005-080000-11","2026-10-05 08:45","Hướng dẫn người dùng","15","ok"\n')
            ma, sql, err = self.chay_in_sql(d)
            self.assertNotEqual(ma, 0)
            self.assertIn("yeu-cau.csv", err)
            self.assertIn("2", err)
            self.assertNotIn("onebee.yeu_cau_ho_tro", sql)
            self.assertIn("onebee.xu_ly_ho_tro", sql)

        # 2) Số lượng không phải số ở don-hang, nhưng khao-sat.csv hợp lệ
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "chung/don-hang"))
            os.makedirs(os.path.join(d, "ho-tro"))
            with open(os.path.join(d, "chung/don-hang/don-hang-2026-10.csv"), "w", encoding="utf-8") as f:
                f.write('"2026-10-05 08:30","Khách mẫu","Mật ong","khong-phai-so","100000","200000","2026-10-10",""\n')
            with open(os.path.join(d, "ho-tro/khao-sat.csv"), "w", encoding="utf-8") as f:
                f.write('"2026-10-09 16:00","4","5","5","4","5",""\n')
            ma, sql, err = self.chay_in_sql(d)
            self.assertNotEqual(ma, 0)
            self.assertIn("don-hang-2026-10.csv", err)
            self.assertIn("1", err)
            self.assertNotIn("onebee.don_hang", sql)
            self.assertIn("onebee.khao_sat", sql)

        # 3) Điểm khảo sát = 7 ở dòng 3 (sau dòng trống ở dòng 2)
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ho-tro"))
            with open(os.path.join(d, "ho-tro/khao-sat.csv"), "w", encoding="utf-8") as f:
                f.write('"2026-10-09 16:00","4","5","5","4","5",""\n')
                f.write("\n")
                f.write('"2026-10-09 16:05","4","7","5","4","5",""\n')
            ma, sql, err = self.chay_in_sql(d)
            self.assertNotEqual(ma, 0)
            self.assertIn("khao-sat.csv", err)
            self.assertIn("3", err)
            self.assertNotIn("onebee.khao_sat", sql)

        # 4) Tệp JSON hỏng trong tinh-trang-may, nhưng tệp JSON khác hợp lệ
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tinh-trang-may"))
            with open(os.path.join(d, "tinh-trang-may/ketoan-01.json"), "w", encoding="utf-8") as f:
                f.write("{json-hong")
            shutil.copyfile(
                os.path.join(FIXTURES, "tinh-trang-may/kho-02.json"),
                os.path.join(d, "tinh-trang-may/kho-02.json"),
            )
            ma, sql, err = self.chay_in_sql(d)
            self.assertNotEqual(ma, 0)
            self.assertIn("ketoan-01.json", err)
            self.assertIn("onebee.tinh_trang_may", sql)
            self.assertIn("kho-02", sql)

    def test_dong_trong_bo_qua_nhung_van_tinh_so_thu_tu_dong(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ho-tro"))
            with open(os.path.join(d, "ho-tro/xu-ly.csv"), "w", encoding="utf-8") as f:
                f.write('"261005-080000-11","2026-10-05 08:45","Hướng dẫn người dùng","15","dòng 1"\n')
                f.write("\n")
                f.write('"261006-091500-22","2026-10-06 10:00","Sửa cấu hình","30","dòng 3"\n')
            ma, sql, err = self.chay_in_sql(d)
            self.assertEqual(ma, 0, msg=err)
            _, cac_khoi = tach_khoi_copy(sql)
            self.assertEqual(len(cac_khoi[0]), 2)
            self.assertEqual(cac_khoi[0][0][1], "1")
            self.assertEqual(cac_khoi[0][1][1], "3")

    def test_tep_khong_ton_tai_khong_gay_loi(self):
        with tempfile.TemporaryDirectory() as d:
            ma, sql, err = self.chay_in_sql(d)
            self.assertEqual(ma, 0, msg=err)
            self.assertEqual(sql.strip(), "")

    def test_in_sql_hai_lan_giong_het_va_khong_tao_truoc_chuyen(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ho-tro"))
            tep_csv = os.path.join(d, "ho-tro/yeu-cau.csv")
            shutil.copyfile(os.path.join(FIXTURES, "ho-tro/yeu-cau.csv"), tep_csv)
            ma1, sql1, _ = self.chay_in_sql(d)
            ma2, sql2, _ = self.chay_in_sql(d)
            self.assertEqual(ma1, 0)
            self.assertEqual(ma2, 0)
            self.assertEqual(sql1, sql2)
            self.assertFalse(os.path.exists(tep_csv + ".truoc-chuyen"))

    def test_che_do_mac_dinh_tao_sao_luu_truoc_chuyen_va_in_tong_ket(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(FIXTURES, d, dirs_exist_ok=True)
            lenh_da_goi = []

            def gia_psql(lenh, input_sql=None):
                lenh_da_goi.append((lenh, input_sql))
                if input_sql and "SELECT" in input_sql and "UNION ALL" in input_sql:
                    return subprocess.CompletedProcess(
                        lenh, 0, stdout="don_hang|3\nyeu_cau_ho_tro|3\nxu_ly_ho_tro|2\nkhao_sat|3\ntinh_trang_may|2\n", stderr=""
                    )
                return subprocess.CompletedProcess(lenh, 0, stdout="BEGIN\nCREATE TABLE\nCOPY 2\nINSERT 0 2\nCOMMIT\n", stderr="")

            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                ma = self.cdl.chay(d, in_sql=False, chay_psql=gia_psql)
            self.assertEqual(ma, 0, msg=err.getvalue())
            self.assertTrue(os.path.exists(os.path.join(d, "chung/don-hang/don-hang-2026-10.csv.truoc-chuyen")))
            self.assertTrue(os.path.exists(os.path.join(d, "ho-tro/yeu-cau.csv.truoc-chuyen")))
            self.assertIn("don_hang", out.getvalue())
            self.assertIn("tinh_trang_may", out.getvalue())


if __name__ == "__main__":
    unittest.main()
