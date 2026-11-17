#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử tĩnh cho kho và kế toán của OneBee Box (không cần Docker):
- tệp lược đồ mới đúng quy ước, có đủ bảng/khung nhìn/hàm và bật RLS, không chứa bí mật;
- vai trò thu_kho, ke_toan có mặt ở group_vars, cầu nối danh tính, chính sách Authelia;
- trang Sổ điều hành có khu Kho, khu Kế toán, gọi đúng API/RPC và có nút xuất CSV;
- dữ liệu mẫu có mặt hàng, tồn đầu kỳ và bút toán cân; bài kiểm Box có đủ bốn vai trò.
Chạy: python3 -m unittest"""
import os
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
LUOC_DO = os.path.join(ROOT, "box/ansible/roles/box-du-lieu/files/luoc-do")
STACK = os.path.join(ROOT, "box/ansible/roles/box-stack")
DINH_DANH = os.path.join(ROOT, "box/ansible/roles/box-dinh-danh")
DEMO = os.path.join(ROOT, "scripts/nap-du-lieu-demo.sql")
KIEM = os.path.join(HERE, "check-kho-ke-toan.sh")
SQL_SCHEMA = os.path.join(LUOC_DO, "006-kho-va-ke-toan.sql")
SQL_QUYEN = os.path.join(LUOC_DO, "007-phan-quyen-kho-ke-toan.sql")


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


def bien_trang(**them):
    with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
        bien = yaml.safe_load(f)
    with open(os.path.join(ROOT, "desktop/ansible/roles/theme/files/onebee-cam-nang.json"), encoding="utf-8") as f:
        bien["onebee_cam_nang"] = __import__("json").load(f)
    with open(os.path.join(STACK, "tasks/main.yml"), encoding="utf-8") as f:
        for t in yaml.safe_load(f):
            facts = t.get("ansible.builtin.set_fact") or {}
            if "onebee_cam_nang_nhom" in facts:
                bien["onebee_cam_nang_nhom"] = facts["onebee_cam_nang_nhom"]
    bien.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True,
                onebee_sso_hieu_luc=True, onebee_kuma_dia_chi="0.0.0.0", onebee_box_ten_don_vi="HTX An Phú")
    bien.update(them)
    return bien


def render(ten, **them):
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
    env.filters["bool"] = bool
    return env.from_string(doc(os.path.join(STACK, "templates", ten))).render(**bien_trang(**them))


class LuocDo(unittest.TestCase):
    def test_ten_tep_dung_quy_uoc_va_khong_co_bi_mat(self):
        ten = sorted(os.listdir(LUOC_DO))
        for f in ten:
            if f.endswith(".sql"):
                self.assertRegex(f, r"^[0-9]{3}-[a-z0-9-]+\.sql$", f)
        self.assertIn("006-kho-va-ke-toan.sql", ten)
        self.assertIn("007-phan-quyen-kho-ke-toan.sql", ten)
        for tep in (SQL_SCHEMA, SQL_QUYEN):
            noi = doc(tep)
            self.assertNotRegex(noi, r"(?i)(password|mat_khau)\s*=\s*'[^']+'", tep)

    def test_bang_va_khung_nhin_day_du_va_bat_rls(self):
        sql = doc(SQL_SCHEMA)
        for bang in ("mat_hang", "phieu_kho", "phieu_kho_dong", "tai_khoan", "but_toan", "but_toan_dong"):
            self.assertIn(f"CREATE TABLE onebee.{bang}", sql, bang)
            self.assertIn(f"ALTER TABLE onebee.{bang} ENABLE ROW LEVEL SECURITY", sql, bang)
            self.assertIn(f"ALTER TABLE onebee.{bang} FORCE ROW LEVEL SECURITY", sql, bang)
        for khung in ("ton_kho", "so_kho", "so_nhat_ky", "bang_can_doi"):
            self.assertIn(f"CREATE VIEW onebee.{khung}", sql, khung)
        for ham in ("ghi_but_toan(", "them_nhap_kho(", "don_hang_hoan_tat(", "kiem_ton_kho("):
            self.assertIn(ham, sql)
        # Bút toán mỗi dòng đúng một bên; hàm ghi bút toán bịt gọi từ ngoài
        self.assertIn("CONSTRAINT mot_ben CHECK ((no > 0) <> (co > 0))", sql)
        self.assertIn("REVOKE ALL ON FUNCTION onebee_noi_bo.ghi_but_toan(date, text, text, jsonb) FROM PUBLIC", doc(SQL_QUYEN))
        # Chặn xuất quá tồn: khoá thẻ kho rồi mới so tồn
        self.assertIn("FOR UPDATE", sql)
        self.assertIn("Không đủ tồn kho", sql)
        # Duyệt đơn sinh chứng từ trong cùng giao dịch
        self.assertIn("CREATE TRIGGER don_hang_hoan_tat AFTER UPDATE ON onebee.don_hang", sql)

    def test_quyen_vai_tro_moi(self):
        sql = doc(SQL_QUYEN)
        for vai in ("thu_kho", "ke_toan"):
            self.assertIn(f"'{vai}'", sql, vai)
        self.assertIn("GRANT SELECT ON onebee.ton_kho", sql)
        self.assertIn("GRANT EXECUTE ON FUNCTION onebee.them_nhap_kho(date, text, jsonb) TO thu_kho, quan_ly", sql)
        self.assertNotIn("GRANT INSERT ON onebee.phieu_kho", sql)
        self.assertNotIn("GRANT INSERT ON onebee.but_toan", sql)


class VaiTro(unittest.TestCase):
    def test_group_vars_va_cau_noi_danh_tinh(self):
        with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
            bien = yaml.safe_load(f)
        self.assertEqual(bien["onebee_box_nhom_nguoi_dung"], ["nhan_vien", "ky_thuat", "quan_ly", "thu_kho", "ke_toan"])
        cau_noi = doc(os.path.join(DINH_DANH, "files/onebee-cau-noi-danh-tinh.py"))
        self.assertIn('VAI_TRO = ("quan_ly", "ke_toan", "thu_kho", "ky_thuat", "nhan_vien")', cau_noi)
        noi = doc(os.path.join(DINH_DANH, "templates/configuration.yml.j2"))
        self.assertIn("group:thu_kho", noi)
        self.assertIn("group:ke_toan", noi)


class GiaoDien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = render("so-dieu-hanh.html.j2")
        cls.js = doc(os.path.join(STACK, "files/so-dieu-hanh.js"))
        cls.kho = doc(os.path.join(STACK, "files/so-dieu-hanh-kho.js"))

    def test_co_hai_khu_moi_va_nut_xuat_csv(self):
        for khu in ("khu-k", "khu-t"):
            self.assertIn(f'id="{khu}"', self.html, khu)
            self.assertIn(f'data-khu="{khu}"', self.html, khu)
        for nut in ("k-xuat-ton", "k-xuat-so", "t-xuat-nhat-ky", "t-xuat-can-doi"):
            self.assertIn(f'id="{nut}"', self.html, nut)
        self.assertIn("/so-dieu-hanh/so-dieu-hanh-kho.js", self.html)

    def test_goi_dung_api_va_rpc(self):
        for duong in ("/api/ton_kho", "/api/so_kho", "/api/so_nhat_ky", "/api/bang_can_doi", "/api/mat_hang",
                      "/api/rpc/them_nhap_kho"):
            self.assertIn(duong, self.js + self.kho, duong)
        self.assertIn("textContent", self.kho)
        for cam in ("innerHTML", "outerHTML", "eval(", "new Function"):
            self.assertNotIn(cam, self.kho, cam)
        # CSV cho LibreOffice Việt Nam: BOM UTF-8 và dấu chấm phẩy
        self.assertIn("\\uFEFF", self.kho)
        self.assertIn('.join(";")', self.kho)

    def test_bieu_mau_don_chon_mat_hang_tu_danh_muc(self):
        self.assertIn('<select id="don-mat-hang"', self.html)
        self.assertIn("mat_hang_id", self.js)


class DuLieuMau(unittest.TestCase):
    def test_co_mat_hang_ton_dau_va_but_toan_can(self):
        sql = doc(DEMO)
        self.assertIn("INSERT INTO onebee.mat_hang", sql)
        self.assertIn("PN-DEMO-0001", sql)
        self.assertIn("BT-DEMO-0001", sql)
        self.assertIn("DELETE FROM onebee.but_toan_dong", sql)   # xoá tường minh vì trigger tắt
        self.assertEqual(sql.count("'156'"), 1)
        self.assertEqual(sql.count("'111'"), 1)
        self.assertIn("session_replication_role = replica", sql)


class BaiKiemBox(unittest.TestCase):
    def test_du_bon_vai_tro_va_buoc_chinh(self):
        noi = doc(KIEM)
        for user in ("kkt-nv nhan_vien", "kkt-thu-kho thu_kho", "kkt-ke-toan ke_toan", "kkt-ql quan_ly"):
            self.assertIn(user, noi)
        for buoc in ("them_nhap_kho", "onebee-phe-duyet", "Không đủ tồn kho", "so_nhat_ky", "ton_kho"):
            self.assertIn(buoc, noi)
        self.assertIn("trap", noi)
        self.assertNotRegex(noi, r"(?i)(password|mat_khau)=\S+")


if __name__ == "__main__":
    unittest.main()
