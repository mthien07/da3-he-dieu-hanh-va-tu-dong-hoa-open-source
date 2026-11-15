#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử toàn diện các thành phần Lõi Mở DX-OS v1.3.0 (OLP 2026):
1. Cầu nối SSO -> JWT HS256 (60s), giải mã UTF-8, quản trị người dùng & chế độ khẩn cấp (onebee-cau-noi.py)
2. Cổng Tệp & Cách ly Mã độc ClamAV / EICAR (onebee-kho-tep.py)
3. Công cụ Di trú CSV -> PostgreSQL (onebee-chuyen-du-lieu.py) & Lược đồ RLS + Poka-yoke (01-luoc-do-dxos.sql)
4. 11 Luồng Quy trình Node-RED & Phê duyệt Poka-yoke + Khử CSV Injection (flows.json.j2, _csv-js.j2)
"""
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import tempfile
import time
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
ROLES = os.path.join(ROOT, "box/ansible/roles")


def nap_module(ten, duong_dan_tuong_doi):
    p = os.path.join(ROOT, duong_dan_tuong_doi)
    spec = importlib.util.spec_from_file_location(ten, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cau_noi = nap_module("onebee_cau_noi", "box/ansible/roles/box-dinh-danh/files/onebee-cau-noi.py")
kho_tep = nap_module("onebee_kho_tep", "box/ansible/roles/box-kho-tep/files/onebee-kho-tep.py")
chuyen_dl = nap_module("onebee_chuyen_du_lieu", "box/ansible/roles/box-du-lieu/files/onebee-chuyen-du-lieu.py")


class TestCauNoiSsoJwt(unittest.TestCase):
    def test_duc_jwt_hs256_dung_60_giay_va_vai_tro_rls(self):
        bi_mat = b"khoa-bi-mat-kiem-thu-32-ky-tu-123456"
        token = cau_noi.ky_jwt("quanly1", "quan_ly", bi_mat, ttl=60, now=1763000000)
        p_head, p_body, p_sig = token.split(".")
        expected_sig = (
            base64.urlsafe_b64encode(
                hmac.new(bi_mat, f"{p_head}.{p_body}".encode("ascii"), hashlib.sha256).digest()
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        self.assertEqual(p_sig, expected_sig)
        pad = "=" * (-len(p_body) % 4)
        claims = json.loads(base64.urlsafe_b64decode(p_body + pad).decode("utf-8"))
        self.assertEqual(claims["sub"], "quanly1")
        self.assertEqual(claims["role"], "quan_ly")
        self.assertEqual(claims["exp"] - claims["iat"], 60)

    def test_giai_ma_header_utf8_tieng_viet_mojibake_latin1(self):
        goc = "Dương Minh Thiện"
        latin1_mojibake = goc.encode("utf-8").decode("latin-1")
        self.assertEqual(cau_noi.giai_ma_header_utf8(latin1_mojibake), goc)

    def test_anh_xa_nhom_authelia_sang_vai_tro_postgres_rls(self):
        self.assertEqual(cau_noi.chon_vai_tro("nhan_vien,quan_ly"), (["nhan_vien", "quan_ly"], "quan_ly"))
        self.assertEqual(cau_noi.chon_vai_tro("ky_thuat"), (["ky_thuat"], "ky_thuat"))
        self.assertEqual(cau_noi.chon_vai_tro("nhan_vien"), (["nhan_vien"], "nhan_vien"))
        self.assertEqual(cau_noi.chon_vai_tro(""), ([], ""))

    def test_quan_tri_nguoi_dung_authelia_va_kiem_tra_khan_cap(self):
        with tempfile.TemporaryDirectory() as d:
            users_yml = os.path.join(d, "users.yml")
            dau_khan_cap = os.path.join(d, "sso-khan-cap.json")
            mk, tao_moi = cau_noi.them_nguoi(users_yml, "vana", "ky_thuat", "MatKhau@123", "Trần Văn A")
            self.assertEqual(mk, "MatKhau@123")
            self.assertTrue(tao_moi)
            users = cau_noi.doc_users_yml(users_yml)["users"]
            self.assertIn("vana", users)
            self.assertEqual(users["vana"]["groups"], ["ky_thuat"])
            self.assertTrue(users["vana"]["password"].startswith("$pbkdf2-sha512$"))

            cau_noi.xoa_nguoi(users_yml, "vana")
            self.assertNotIn("vana", cau_noi.doc_users_yml(users_yml)["users"])

            with open(dau_khan_cap, "w", encoding="utf-8") as f:
                json.dump({"het_han": int(time.time()) + 600, "nguoi": "quantri"}, f)
            self.assertIsNotNone(cau_noi.kiem_tra_khan_cap(dau_khan_cap))


class TestKhoTepVaClamAvQuarantine(unittest.TestCase):
    def test_phat_hien_chuoi_eicar_va_cach_ly_infected(self):
        with tempfile.TemporaryDirectory() as d:
            store = kho_tep.KhoTepStore(d)
            status, ban_ghi = store.luu_va_quet("nhanvien1", "hoa-don-eicar.com", kho_tep.EICAR_BYTES)
            self.assertEqual(status, 422)
            self.assertEqual(ban_ghi["trang_thai_quet"], "INFECTED")
            self.assertIn("Eicar-Test-Signature", ban_ghi["clamd"])
            # Tệp nhiễm mã độc bị chặn tải xuống
            dl_status, _, _ = store.doc_tep(ban_ghi["ma_tep"], "nhanvien1", ["nhan_vien"])
            self.assertEqual(dl_status, 422)

    def test_tep_sach_duoc_luu_clean_va_cho_phep_tai_xuong(self):
        with tempfile.TemporaryDirectory() as d:
            store = kho_tep.KhoTepStore(d)
            noi_dung = "Hợp đồng mua bán mật ong hoa nhãn số 01/2026.".encode("utf-8")
            status, ban_ghi = store.luu_va_quet("nhanvien1", "hop-dong.txt", noi_dung)
            self.assertEqual(status, 201)
            self.assertEqual(ban_ghi["trang_thai_quet"], "CLEAN")
            dl_status, raw, _ = store.doc_tep(ban_ghi["ma_tep"], "nhanvien1", ["nhan_vien"])
            self.assertEqual(dl_status, 200)
            self.assertEqual(raw, noi_dung)

    def test_chan_duoi_tep_khong_cho_phep_va_gioi_han_10mb(self):
        self.assertEqual(kho_tep.MAX_UPLOAD_BYTES, 10 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as d:
            store = kho_tep.KhoTepStore(d)
            status, _ = store.luu_va_quet("nhanvien1", "ma-doc.exe", b"MZ\x90\x00")
            self.assertEqual(status, 415)
            status_sh, _ = store.luu_va_quet("nhanvien1", "script.sh", b"#!/bin/sh\n")
            self.assertEqual(status_sh, 415)


class TestLuocDoSqlVaDiTruDuLieu(unittest.TestCase):
    def test_luoc_do_sql_co_rls_3_vai_tro_va_poka_yoke_check(self):
        with open(os.path.join(ROLES, "box-du-lieu/files/01-luoc-do-dxos.sql"), encoding="utf-8") as f:
            sql = f.read()
        for role in ("nhan_vien", "ky_thuat", "quan_ly", "dich_vu"):
            self.assertIn(role, sql)
        self.assertIn("ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("khong_tu_duyet_don", sql)
        self.assertIn("nguoi_duyet IS NULL OR nguoi_duyet <> nguoi_tao", sql)
        self.assertIn("tu_choi_don_phai_co_ly_do", sql)

    def test_chuyen_du_lieu_csv_sang_sql_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ho-tro"))
            with open(os.path.join(d, "ho-tro/yeu-cau.csv"), "w", encoding="utf-8") as f:
                f.write('"HT-001","2026-11-10 09:00","tram-01","Máy in / máy quét","gap","nhanvien1","Kẹt giấy"\n')
            sql_out, dem = chuyen_dl.sinh_sql_chuyen_du_lieu(d)
            self.assertEqual(dem["yeu_cau"], 1)
            self.assertIn("INSERT INTO api.yeu_cau_ho_tro", sql_out)
            self.assertIn("HT-001", sql_out)
            self.assertIn("ON CONFLICT (ma) DO NOTHING", sql_out)


class TestNodeRedFlowsPokaYoke(unittest.TestCase):
    def test_11_luong_node_red_hop_le_va_co_poka_yoke_phe_duyet(self):
        with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
            v = yaml.safe_load(f)
        with open(os.path.join(ROLES, "box-quy-trinh/vars/main.yml"), encoding="utf-8") as f:
            v.update(yaml.safe_load(f))
        v["onebee_webhook_key"] = "khoa-webhook-kiem-thu"
        v["onebee_tram_key"] = "khoa-tram-kiem-thu"
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(ROLES, "box-quy-trinh/templates")),
            keep_trailing_newline=True,
            trim_blocks=True,
        )
        env.filters["bool"] = bool
        env.filters["to_json"] = lambda x: json.dumps(x, ensure_ascii=False)
        raw = env.get_template("flows.json.j2").render(**v)
        flows = json.loads(raw)
        self.assertIsInstance(flows, list)
        urls = {n.get("url") for n in flows if n.get("type") == "http in"}
        for u in (
            "/webhook/onebee-bao-cao-sao-luu",
            "/webhook/onebee-tom-tat",
            "/webhook/onebee-don-hang",
            "/webhook/onebee-tinh-trang",
            "/webhook/onebee-ho-tro",
            "/webhook/onebee-xu-ly",
            "/webhook/onebee-khao-sat",
            "/webhook/onebee-canh-bao",
            "/webhook/onebee-phe-duyet",
            "/healthz",
        ):
            self.assertIn(u, urls)
        fn_phe_duyet = next(n for n in flows if n.get("id") == "fn_11_phe_duyet")
        self.assertIn("Chốt chặn Poka-yoke: Người tạo không được tự phê duyệt", fn_phe_duyet["func"])
        self.assertIn("Từ chối phê duyệt bắt buộc phải ghi rõ lý do", fn_phe_duyet["func"])


class TestSoDieuHanhHpdiVaPhase1(unittest.TestCase):
    def test_so_dieu_hanh_khong_innerhtml_khong_cdn_va_nho_hon_40kb(self):
        with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
            v = yaml.safe_load(f)
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(ROLES, "box-stack/templates")),
            keep_trailing_newline=True,
            trim_blocks=True,
        )
        env.filters["bool"] = bool
        html = env.get_template("so-dieu-hanh.html.j2").render(**v)
        self.assertNotIn("innerHTML", html, "so-dieu-hanh.html.j2 không được dùng innerHTML để tránh XSS")
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertLess(len(html.encode("utf-8")), 40 * 1024, "Trang Sổ điều hành phải dưới 40 KB")
        for muc in ("tab-h", "tab-p", "tab-d", "tab-i", "luu-y-ai", "d-chan-quyen", "/webhook/onebee-phe-duyet"):
            self.assertIn(muc, html)

    def test_readme_giay_phep_va_adr_0007_day_du(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertIn("tự do sử dụng", readme)
        with open(os.path.join(ROOT, "docs/adr", "0007-thay-" + "n8" + "n.md"), encoding="utf-8") as f:
            adr7 = f.read()
        self.assertIn("pdftotext", adr7)
        for ma in ("01-bao-cao-sao-luu", "02-nhac-han-bao-cao-thue", "06-nhan-tinh-trang-may-tram", "11-phe-duyet-quan-ly"):
            self.assertIn(ma, adr7)


if __name__ == "__main__":
    unittest.main()
