#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Kiểm thử chế độ bản chạy thử công khai (không cần Docker): biến mặc định tắt, dữ liệu mẫu đúng lược đồ
onebee.* và nạp idempotent, bộ hẹn giờ 03:00, thanh thông báo demo trên Sổ điều hành, inventory mẫu không chứa
bí mật, vai trò box-demo chạy sau CSDL và định danh. Chạy: python3 -m unittest"""
import os
import re
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ANSIBLE = os.path.join(ROOT, "box/ansible")
ROLE = os.path.join(ANSIBLE, "roles/box-demo")
ROLE_TEMPLATES = os.path.join(ROLE, "templates")
STACK_TEMPLATES = os.path.join(ANSIBLE, "roles/box-stack/templates")
SQL_FILE = os.path.join(ROOT, "scripts/nap-du-lieu-demo.sql")
INVENTORY = os.path.join(ANSIBLE, "inventory.demo.ini.example")
GROUP_VARS_FILE = os.path.join(ANSIBLE, "group_vars/all.yml")
SITE_FILE = os.path.join(ANSIBLE, "site.yml")
CHECK_FILE = os.path.join(ROOT, "tests/box/check-ban-demo.sh")

with open(GROUP_VARS_FILE, encoding="utf-8") as f:
    GROUP_VARS = yaml.safe_load(f)


def nap_bien(**them):
    v = dict(GROUP_VARS)
    v.update(
        onebee_box_dir="/opt/onebee-box",
        onebee_box_secrets="/etc/onebee-box/secrets",
        onebee_box_che_do_demo=False,
    )
    v.update(them)
    return v


def render(ten, thu_muc, **bien):
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
    env.filters["bool"] = bool
    with open(os.path.join(thu_muc, ten), encoding="utf-8") as f:
        return env.from_string(f.read()).render(**bien)


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


class CheDoDemoMacDinh(unittest.TestCase):
    def test_mac_dinh_tat(self):
        self.assertIs(GROUP_VARS.get("onebee_box_che_do_demo"), False)


class BoHenGioDatLai(unittest.TestCase):
    def test_hen_gio_03_00_moi_ngay_va_ben(self):
        nd = render("onebee-demo-reset.timer.j2", ROLE_TEMPLATES, **nap_bien())
        self.assertIn("OnCalendar=*-*-* 03:00:00", nd)
        self.assertIn("Persistent=true", nd)
        self.assertIn("WantedBy=timers.target", nd)

    def test_dich_vu_nap_bang_tai_khoan_chu_csdl_trong_container(self):
        nd = render("onebee-demo-reset.service.j2", ROLE_TEMPLATES, **nap_bien())
        self.assertIn("docker exec -i onebee-postgres", nd)
        self.assertIn("-U postgres", nd)
        self.assertIn("-d onebee", nd)
        self.assertIn("ON_ERROR_STOP=1", nd)
        self.assertIn("/usr/local/lib/onebee-box/nap-du-lieu-demo.sql", nd)
        self.assertIn("Requires=docker.service", nd)


class DuLieuDemo(unittest.TestCase):
    def setUp(self):
        self.sql = doc(SQL_FILE)

    def test_dung_luoc_do_onebee_cua_nen_csdl(self):
        self.assertTrue(self.sql.startswith("-- SPDX-License-Identifier: MIT"))
        self.assertIn("\nBEGIN;\n", self.sql)
        self.assertIn("\nCOMMIT;\n", self.sql)
        for bang in ("don_hang", "yeu_cau_ho_tro", "xu_ly_ho_tro", "khao_sat", "tinh_trang_may"):
            self.assertIn("onebee." + bang, self.sql, bang)
        self.assertNotRegex(self.sql, r"CREATE TABLE\s+don_hang")
        self.assertNotIn("onebee_dxos", self.sql)
        self.assertNotIn("CREATE TABLE", self.sql)          # dữ liệu mẫu không tự tạo bảng

    def test_nap_lai_idempotent(self):
        self.assertGreaterEqual(len(re.findall(r"ON CONFLICT \(nguon, dong\) DO UPDATE", self.sql)), 4)
        self.assertIn("ON CONFLICT (ten) DO UPDATE", self.sql)
        self.assertEqual(len(re.findall(r"DELETE FROM onebee\.", self.sql)), 5)   # xóa dòng phát sinh + dòng thừa trước khi nạp
        self.assertIn("nguon = 'nap-du-lieu-demo'", self.sql)
        self.assertIn("nguon IS NULL", self.sql)             # dòng người dùng tạo qua API trở về trạng thái mẫu
        self.assertIn("SET LOCAL session_replication_role = replica", self.sql)   # trigger duyệt không ghi đè dữ liệu mẫu

    def test_trang_thai_va_danh_muc_dung_giao_keo(self):
        self.assertNotIn("'NHAP'", self.sql)
        self.assertNotIn("'KHAN'", self.sql)
        self.assertNotIn("'BINH_THUONG'", self.sql)
        self.assertIn("'CHO_DUYET'", self.sql)
        self.assertIn("'DA_DUYET'", self.sql)
        self.assertIn("'TU_CHOI'", self.sql)
        self.assertIn("'gap'", self.sql)
        self.assertIn("'binh-thuong'", self.sql)
        self.assertIn("'quanly1'", self.sql)                 # người duyệt khác người tạo (không tự duyệt)
        for loai in ("Máy in / máy quét", "Gõ tiếng Việt", "Mạng / Internet"):
            self.assertIn("'" + loai + "'", self.sql)


class ThanhThongBaoDemo(unittest.TestCase):
    def test_bat_thi_hien_tat_thi_an(self):
        bat = render("so-dieu-hanh-demo.html.j2", STACK_TEMPLATES, **nap_bien(onebee_box_che_do_demo=True))
        tat = render("so-dieu-hanh-demo.html.j2", STACK_TEMPLATES, **nap_bien(onebee_box_che_do_demo=False))
        self.assertIn("Dữ liệu giả lập", bat)
        self.assertIn("03:00", bat)
        self.assertIn("Bản chạy thử công khai", bat)
        self.assertNotIn("Dữ liệu giả lập", tat)
        self.assertNotIn("<style", bat)                      # CSP style-src 'self' chặn style nhúng
        self.assertNotRegex(bat, r"(?i)innerHTML|\bsrc=\"https?://|\bhref=\"https?://")   # không nguồn ngoài

    def test_khoi_chen_nam_trong_mot_dieu_kien_demo(self):
        nd = doc(os.path.join(STACK_TEMPLATES, "so-dieu-hanh-demo.html.j2"))
        self.assertIn("{% if onebee_box_che_do_demo | default(false) | bool %}", nd)
        self.assertIn('class="thong-bao thanh-demo"', nd)
        self.assertIn("so-dieu-hanh.html.j2", nd)             # chỉ rõ nơi dán khi gộp


class InventoryMau(unittest.TestCase):
    def test_dung_nhom_box_bat_demo_va_https(self):
        nd = doc(INVENTORY)
        self.assertIn("[box]", nd)
        self.assertIn("onebee_box_che_do_demo=true", nd)
        self.assertIn("onebee_box_https=true", nd)
        self.assertIn("203.0.113.10", nd)                    # dải tài liệu RFC 5737, không phải IP thật
        self.assertIn("onebee_box_ma_don_vi=demo", nd)

    def test_khong_co_bi_mat(self):
        nd = doc(INVENTORY)
        self.assertIsNone(re.search("PRIVATE" + r"\s+KEY", nd))
        self.assertIsNone(re.search("ansible_ssh_" + "pass", nd))
        self.assertNotRegex(nd, r"(?i)mật\s*khẩu\s*[:=]\s*\S+")


class BoCaiDemo(unittest.TestCase):
    def test_vai_tro_box_demo_chay_sau_csdl_va_dinh_danh(self):
        roles = [r if isinstance(r, str) else r["role"] for r in yaml.safe_load(doc(SITE_FILE))[0]["roles"]]
        self.assertIn("box-demo", roles)
        self.assertGreater(roles.index("box-demo"), roles.index("box-du-lieu"))
        self.assertGreater(roles.index("box-demo"), roles.index("box-dinh-danh"))

    def test_tat_demo_thi_go_bo_hen_gio(self):
        nd = doc(os.path.join(ROLE, "tasks/main.yml"))
        self.assertIn("onebee-demo-reset.timer", nd)
        self.assertIn("onebee-demo-reset.service", nd)
        self.assertIn("when: not (onebee_box_che_do_demo | default(false) | bool)", nd)
        self.assertRegex(nd, r"state: absent")
        self.assertIn("tai-khoan-demo.txt", nd)              # mật khẩu tạm chỉ lưu trên Box
        self.assertNotRegex(nd, r"(?i)mật\s*khẩu\s*(tạm)?\s*[:=]\s*[A-Za-z0-9]{8,}")

    def test_bai_kiem_du_bon_dong_pass(self):
        nd = doc(CHECK_FILE)
        self.assertGreaterEqual(len(re.findall(r"echo ['\"]PASS", nd)), 4)
        self.assertIn("onebee_box_che_do_demo: true", nd)
        self.assertIn("onebee_box_che_do_demo: false", nd)
        self.assertIn("KẾT QUẢ", nd)


if __name__ == "__main__":
    unittest.main()
