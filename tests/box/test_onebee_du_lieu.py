#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử phần dữ liệu cấu trúc của OneBee Box (không cần Docker): dịch vụ PostgreSQL + PostgREST trong docker-compose.yml.j2
(không công bố cổng, no-new-privileges, ghim digest, chỉ cầu nối danh tính nối được tới API, dùng chung khóa ký JWT của cầu nối),
các tệp lược đồ (RLS trên mọi bảng, không tự duyệt đơn, danh mục khớp biểu mẫu, đúng giao kèo cột), role box-du-lieu trong site.yml,
không có mật khẩu dạng rõ trong mẫu. Phân quyền chạy thật trên PostgreSQL: tests/box/check-csdl-rls.sh. Chạy: python3 -m unittest"""
import glob
import os
import re
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ANSIBLE = os.path.join(ROOT, "box/ansible")
STACK = os.path.join(ANSIBLE, "roles/box-stack/templates")
DU_LIEU = os.path.join(ANSIBLE, "roles/box-du-lieu")
LUOC_DO = sorted(glob.glob(os.path.join(DU_LIEU, "files/luoc-do/*.sql")))
GROUP_VARS = yaml.safe_load(open(os.path.join(ANSIBLE, "group_vars/all.yml"), encoding="utf-8"))

# Giao kèo lược đồ: cột dữ liệu đúng thứ tự (= thứ tự cột sổ cũ và thứ tự xuất cho báo cáo tuần), rồi tới cột thêm
GIAO_KEO = {
    "don_hang": ["thoi_gian", "khach_hang", "mat_hang", "so_luong_kg", "don_gia", "thanh_tien", "ngay_giao", "ghi_chu",
                 "id", "nguoi_tao", "nguon", "dong", "trang_thai_duyet", "nguoi_duyet", "ly_do_duyet", "thoi_gian_duyet"],
    "yeu_cau_ho_tro": ["ma", "thoi_gian", "may", "loai", "muc_do", "nguoi_bao", "mo_ta", "id", "nguoi_tao", "nguon", "dong"],
    "xu_ly_ho_tro": ["ma", "thoi_gian", "cach_xu_ly", "so_phut", "ghi_chu", "id", "nguoi_tao", "nguon", "dong"],
    "khao_sat": ["thoi_gian", "diem_1", "diem_2", "diem_3", "diem_4", "diem_5", "gop_y", "id", "nguon", "dong"],
    "tinh_trang_may": ["ten", "bao_bi", "nhan_luc"],
}


def ve_compose(https):
    v = dict(GROUP_VARS, onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=https, onebee_kuma_dia_chi="0.0.0.0")
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # như Ansible
    env.filters["bool"] = bool
    return yaml.safe_load(env.from_string(open(os.path.join(STACK, "docker-compose.yml.j2"), encoding="utf-8").read()).render(**v))


def sql_tat_ca():
    return "\n".join(open(f, encoding="utf-8").read() for f in LUOC_DO)


def bo_chu_thich(sql):
    return re.sub(r"--[^\n]*", "", sql)


def cot_cua_bang(sql, bang):
    """Tên cột (theo thứ tự) trong CREATE TABLE onebee.<bang> (...): dòng bắt đầu bằng tên cột, bỏ các dòng ràng buộc."""
    m = re.search(r"CREATE TABLE onebee\.%s \((.*?)\n\);" % bang, bo_chu_thich(sql), re.S)
    assert m, bang
    cot = []
    for dong in m.group(1).splitlines():
        t = re.match(r"\s+([a-z_0-9]+)\s", dong)
        if t and t.group(1).upper() not in ("UNIQUE", "CHECK", "PRIMARY", "FOREIGN", "CONSTRAINT"):
            cot.append(t.group(1))
    return cot


class ComposeDuLieu(unittest.TestCase):
    def test_hai_dich_vu_khong_cong_bo_cong_co_no_new_privileges_va_ghim_digest(self):
        for https in (False, True):
            c = ve_compose(https)
            s = c["services"]
            for ten, anh in (("postgres", "postgres"), ("postgrest", "postgrest")):
                self.assertNotIn("ports", s[ten], ten)
                self.assertIn("no-new-privileges:true", s[ten]["security_opt"], ten)
                self.assertEqual(s[ten]["logging"], c["x-logging"], ten)          # logging: *logging
                self.assertEqual(s[ten]["image"], GROUP_VARS["onebee_box_images"][anh])
                self.assertRegex(s[ten]["image"], r":[^@]+@sha256:[0-9a-f]{64}$")
                self.assertEqual(s[ten]["cap_drop"], ["ALL"], ten)
            self.assertEqual(s["postgres"]["container_name"], "onebee-postgres")
            self.assertEqual(s["postgrest"]["container_name"], "onebee-postgrest")
            self.assertTrue(s["postgrest"]["read_only"])

    def test_chi_cau_noi_noi_duoc_toi_api_va_chi_api_noi_duoc_toi_csdl(self):
        c = ve_compose(True)
        s = c["services"]
        mang = {ten: set(d.get("networks", ["default"])) for ten, d in s.items()}
        self.assertEqual(mang["postgres"], {"csdl"})
        self.assertEqual(mang["postgrest"], {"api", "csdl"})
        self.assertEqual(mang["cau-noi"], {"sso", "api"})
        self.assertEqual({t for t, m in mang.items() if "api" in m}, {"postgrest", "cau-noi"})
        self.assertEqual({t for t, m in mang.items() if "csdl" in m}, {"postgres", "postgrest"})
        for m in ("api", "csdl"):
            self.assertTrue(c["networks"][m]["internal"], m)                      # không có đường ra ngoài
        self.assertEqual(s["cau-noi"]["environment"]["CAU_NOI_PHIA_SAU"], "http://postgrest:3000")

    def test_postgrest_dung_chung_khoa_ky_cua_cau_noi_va_khong_co_vai_tro_an_danh(self):
        s = ve_compose(False)["services"]
        env = s["postgrest"]["environment"]
        khoa_cau_noi = [v for v in s["cau-noi"]["volumes"] if "cau-noi-jwt-secret" in v][0].split(":")[0]
        self.assertTrue(khoa_cau_noi.endswith("/cau-noi-jwt-secret"))
        gan = [v for v in s["postgrest"]["volumes"] if v.split(":")[0] == khoa_cau_noi]
        self.assertEqual(len(gan), 1, s["postgrest"]["volumes"])                  # cùng một tệp khóa với cầu nối
        self.assertTrue(gan[0].endswith(":ro"))
        self.assertEqual(env["PGRST_JWT_SECRET"], "@" + gan[0].split(":")[1])
        self.assertEqual(env["PGRST_JWT_AUD"], "onebee-api")
        self.assertEqual(env["PGRST_DB_SCHEMAS"], "onebee")
        self.assertEqual(env["PGRST_DB_URI"], "${PGRST_DB_URI}")                  # mật khẩu nằm trong .env (chỉ root đọc)
        self.assertFalse([k for k in env if "ANON" in k])
        self.assertNotIn("PGRST_JWT_ROLE_CLAIM_KEY", env)                          # mặc định $.role
        self.assertEqual(s["postgres"]["environment"]["POSTGRES_DB"], "onebee")
        self.assertNotIn("POSTGRES_PASSWORD", s["postgres"]["environment"])         # chỉ đọc từ tệp bí mật
        self.assertTrue(s["postgres"]["environment"]["POSTGRES_PASSWORD_FILE"].startswith("/run/secrets/"))

    def test_khong_co_mat_khau_dang_ro_trong_mau(self):
        tep = [os.path.join(STACK, "docker-compose.yml.j2"), os.path.join(STACK, "env.j2")] + glob.glob(os.path.join(DU_LIEU, "**/*.y*ml"), recursive=True)
        mau = re.compile(r"(?i)(password|passwd|mat_khau|secret)[A-Z_]*\s*[:=]\s*['\"]?(?![$@{/]|\$\{|\{\{)[A-Za-z0-9+/]{8,}")
        for f in tep:
            for so, dong in enumerate(open(f, encoding="utf-8"), 1):
                self.assertIsNone(mau.search(dong), f"{f}:{so}: {dong.strip()}")
        env = open(os.path.join(STACK, "env.j2"), encoding="utf-8").read()
        self.assertRegex(env, r"(?m)^PGRST_DB_URI=postgres://xac_thuc:\{\{ lookup\('ansible.builtin.password', onebee_box_secrets ~ '/postgrest-password'")


class LuocDo(unittest.TestCase):
    def test_moi_bang_bat_va_ep_rls(self):
        sql = bo_chu_thich(sql_tat_ca())
        tao = re.findall(r"CREATE TABLE (onebee\.\w+)", sql)
        bat = re.findall(r"ALTER TABLE (onebee\.\w+) ENABLE ROW LEVEL SECURITY", sql)
        ep = re.findall(r"ALTER TABLE (onebee\.\w+) FORCE ROW LEVEL SECURITY", sql)
        self.assertGreaterEqual(len(tao), 8)
        self.assertEqual(len(re.findall(r"CREATE TABLE", sql)), len(re.findall(r"ENABLE ROW LEVEL SECURITY", sql)))
        self.assertEqual(sorted(tao), sorted(bat))
        self.assertEqual(sorted(tao), sorted(ep))
        for b in ("don_hang", "yeu_cau_ho_tro", "xu_ly_ho_tro", "khao_sat", "tinh_trang_may", "tep_dinh_kem", "tai_lieu_tri_thuc", "lich_su_hoi_ai"):
            self.assertIn("onebee." + b, tao)

    def test_khong_tu_duyet_va_khong_co_vai_tro_an_danh(self):
        sql = bo_chu_thich(sql_tat_ca())
        self.assertIn("CHECK (nguoi_duyet IS NULL OR nguoi_duyet <> nguoi_tao)", sql)
        self.assertIn("CHECK (so_luong_kg > 0 AND don_gia >= 0)", sql)
        self.assertNotRegex(sql, r"(?i)\banon|\bweb_anon|TO PUBLIC")
        self.assertIn("current_setting('request.jwt.claims', true)", sql)
        # Quản lý chỉ sửa được hai cột duyệt; không ai có UPDATE/DELETE khác
        self.assertEqual(re.findall(r"GRANT [^;]*\b(?:UPDATE|DELETE)\b[^;]*;", sql),
                         ["GRANT UPDATE (trang_thai_duyet, ly_do_duyet) ON onebee.don_hang TO quan_ly;"])

    def test_dung_giao_keo_cot(self):
        sql = sql_tat_ca()
        for bang, cot in GIAO_KEO.items():
            self.assertEqual(cot_cua_bang(sql, bang), cot, bang)
        self.assertNotIn("nguoi_tao", cot_cua_bang(sql, "khao_sat"))             # khảo sát ẩn danh
        for bang in ("don_hang", "yeu_cau_ho_tro", "xu_ly_ho_tro", "khao_sat"):
            than = re.search(r"CREATE TABLE onebee\.%s \((.*?)\n\);" % bang, bo_chu_thich(sql), re.S).group(1)
            self.assertIn("UNIQUE (nguon, dong)", than, bang)
        self.assertRegex(sql, r"timestamp without time zone")
        self.assertNotRegex(bo_chu_thich(sql), r"timestamptz|with time zone")

    def test_danh_muc_khop_bieu_mau(self):
        v = yaml.safe_load(open(os.path.join(ANSIBLE, "roles/box-quy-trinh/vars/main.yml"), encoding="utf-8"))
        sql = sql_tat_ca()

        def danh_muc(cot):
            m = re.search(r"CHECK \(nguon IS NOT NULL OR %s IN \(([^)]*(?:\([^)]*\)[^)]*)*)\)\)" % cot, sql)
            self.assertIsNotNone(m, cot)
            return re.findall(r"'([^']*)'", m.group(1))
        self.assertEqual(danh_muc("loai"), v["onebee_ho_tro_loai"])
        self.assertEqual(danh_muc("cach_xu_ly"), v["onebee_ho_tro_cach_xu_ly"])
        self.assertEqual(danh_muc("muc_do"), ["gap", "binh-thuong"])              # giá trị sổ cũ ghi; ứng dụng giai đoạn 4 dùng lại

    def test_ten_tep_luoc_do_dung_dang_va_khong_tu_mo_giao_dich(self):
        self.assertEqual([os.path.basename(f) for f in LUOC_DO],
                         ["001-khoi-tao.sql", "002-phan-quyen.sql", "003-khung-nhin-tong-hop.sql",
                          "004-kho-tep.sql", "005-tri-thuc-va-lich-su-hoi-ai.sql"])
        for f in LUOC_DO:
            noi_dung = bo_chu_thich(open(f, encoding="utf-8").read())
            self.assertNotRegex(noi_dung, r"(?im)^\s*(BEGIN|COMMIT|ROLLBACK)\s*;", f)   # công cụ áp dụng bọc mỗi tệp một giao dịch


class BoCaiDuLieu(unittest.TestCase):
    def test_site_yml_co_box_du_lieu_ngay_sau_box_dinh_danh(self):
        roles = [r if isinstance(r, str) else r["role"] for r in yaml.safe_load(open(os.path.join(ANSIBLE, "site.yml"), encoding="utf-8"))[0]["roles"]]
        self.assertEqual(roles[roles.index("box-dinh-danh") + 1], "box-du-lieu")

    def test_cai_lenh_chuyen_du_lieu_va_cong_cu_luoc_do(self):
        tasks = yaml.safe_load(open(os.path.join(DU_LIEU, "tasks/main.yml"), encoding="utf-8"))
        chep = {}
        for t in tasks:
            c = t.get("ansible.builtin.copy")
            for muc in (t.get("loop") or [c["src"]]) if c else []:
                chep[muc] = c["dest"].replace("{{ item }}", muc)
        for ten in ("onebee-chuyen-du-lieu.py", "onebee-luoc-do.sh"):
            self.assertEqual(chep.get(ten), "/usr/local/lib/onebee-box/" + ten)
            self.assertTrue(os.path.isfile(os.path.join(DU_LIEU, "files", ten)), ten)
        ap_dung = [t for t in tasks if "onebee-luoc-do.sh" in str(t.get("ansible.builtin.command", ""))]
        self.assertEqual(len(ap_dung), 1)
        self.assertIn("đã áp dụng", ap_dung[0]["changed_when"])
        self.assertIn("postgres-ket-xuat", ap_dung[0]["ansible.builtin.command"])

    def test_giay_phep_va_ci(self):
        lic = open(os.path.join(ROOT, "LICENSES.md"), encoding="utf-8").read()
        for ten in ("PostgreSQL", "pgvector", "PostgREST", "SeaweedFS", "ClamAV"):
            self.assertIn(ten, lic)
        ci = yaml.safe_load(open(os.path.join(ROOT, ".github/workflows/ci.yml"), encoding="utf-8"))
        buoc = "\n".join(b.get("run", "") for b in ci["jobs"]["lint"]["steps"])
        self.assertIn("tests/box/check-csdl-rls.sh", buoc)
        self.assertIn("tests/box/*.sh", buoc)                                      # shellcheck có cả check-csdl-rls.sh
        self.assertIn("box/ansible/roles/box-du-lieu/files/onebee-luoc-do.sh", buoc)


if __name__ == "__main__":
    unittest.main()
