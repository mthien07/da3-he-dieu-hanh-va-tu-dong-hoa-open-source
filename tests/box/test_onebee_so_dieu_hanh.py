#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Kiểm thử Ứng dụng Sổ điều hành H-P-D-I (box-stack: so-dieu-hanh.html.j2, so-dieu-hanh.css, so-dieu-hanh.js), không cần Box thật.
Trang: tĩnh, không nguồn ngoài, không innerHTML, dưới 40 KB, đủ bốn khu H, P, D, I, chỉ gọi /api/, /files/, /ai/, /quy-trinh/webhook/onebee-phe-duyet;
mã JavaScript chạy THẬT bằng node (nếu có): kiểm dữ liệu nhập, đọc số dòng, thông báo lỗi tiếng Việt, tóm tắt tuần chỉ có số liệu tổng hợp.
Bộ cài tạo thư mục portal/site/so-dieu-hanh trước khi sinh trang; Caddyfile có tuyến sau đăng nhập; Authelia có luật theo nhóm; trang chủ và
menu máy trạm trỏ tới ứng dụng. Chạy: python3 -m unittest"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
ROLES = os.path.join(ROOT, "box/ansible/roles")
STACK = os.path.join(ROLES, "box-stack")
TRANG = os.path.join(STACK, "templates/so-dieu-hanh.html.j2")
CSS = os.path.join(STACK, "files/so-dieu-hanh.css")
JS = os.path.join(STACK, "files/so-dieu-hanh.js")
MUC_MENU = os.path.join(ROOT, "desktop/ansible/roles/quan-ly-tap-trung/tasks/muc-menu.yml")
NODE = shutil.which("node")


def nhom_cam_nang():
    with open(os.path.join(STACK, "tasks/main.yml"), encoding="utf-8") as f:
        for t in yaml.safe_load(f):
            facts = t.get("ansible.builtin.set_fact") or {}
            if "onebee_cam_nang_nhom" in facts:
                return facts["onebee_cam_nang_nhom"]
    raise AssertionError("tasks box-stack thiếu onebee_cam_nang_nhom")


def bien(**them):
    with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
        v = yaml.safe_load(f)
    # Nguồn dữ liệu dùng chung mà bộ cài nạp bằng lookup khi sinh trang chủ
    with open(os.path.join(ROOT, "desktop/ansible/roles/theme/files/onebee-cam-nang.json"), encoding="utf-8") as f:
        v["onebee_cam_nang"] = json.load(f)
    v["onebee_cam_nang_nhom"] = nhom_cam_nang()
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_sso_hieu_luc=True,
             onebee_kuma_dia_chi="0.0.0.0", onebee_box_ten_don_vi="HTX An Phú")
    v.update(them)
    return v


def render(duong_dan, **them):
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True, undefined=jinja2.StrictUndefined)
    env.filters["bool"] = bool
    with open(duong_dan, encoding="utf-8") as f:
        return env.from_string(f.read()).render(**bien(**them))


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


class TrangTinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html, cls.css, cls.js = render(TRANG), doc(CSS), doc(JS)
        cls.tat_ca = {"so-dieu-hanh.html": cls.html, "so-dieu-hanh.css": cls.css, "so-dieu-hanh.js": cls.js}

    def test_nhe_duoi_40kb(self):
        tong = sum(len(t.encode("utf-8")) for t in self.tat_ca.values())
        self.assertLess(tong, 40 * 1024, f"cả trang (HTML + CSS + JS) {tong} byte")

    def test_khong_innerhtml_khong_ma_dong(self):
        for ten, noi_dung in self.tat_ca.items():
            for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "srcdoc"):
                self.assertNotIn(cam, noi_dung, f"{ten} dùng {cam}")

    def test_khong_tai_gi_tu_internet(self):
        for ten, noi_dung in self.tat_ca.items():
            self.assertNotRegex(noi_dung, r"https?://", f"{ten} có địa chỉ http(s)")
            self.assertIsNone(re.search(r"""(src|href|action|poster|data)\s*=\s*["']?\s*(https?:)?//""", noi_dung), ten)
            self.assertNotIn("@import", noi_dung, ten)
            self.assertNotRegex(noi_dung, r"url\(\s*[\"']?(https?:)?//", ten)

    def test_tai_nguyen_cung_goc_va_khong_ma_nhung(self):
        # CSP của Caddy chỉ cho script/style từ chính Box ('self'): trang không được có script/style nhúng, thuộc tính style, trình xử lý on…=
        h = self.html
        self.assertIn('<script src="/so-dieu-hanh/so-dieu-hanh.js"></script>', h)
        self.assertIn('<link rel="stylesheet" href="/so-dieu-hanh/so-dieu-hanh.css">', h)
        self.assertEqual(len(re.findall(r"<script\b", h)), 1)
        self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)[^>]*>", h), "script nhúng")
        self.assertNotRegex(h, r"<style\b")
        self.assertNotRegex(h, r"""\sstyle\s*=""")
        self.assertNotRegex(h, r"""\son[a-z]+\s*=""")
        self.assertNotRegex(h, r"<(iframe|object|embed|form[^>]*\saction=)")

    def test_du_bon_khu_h_p_d_i(self):
        h = self.html
        for khu in "hpdi":
            self.assertIn(f'id="khu-{khu}"', h)
            self.assertIn(f'data-khu="khu-{khu}"', h)
        for the in ("[H]", "[P]", "[D]", "[I]"):
            self.assertIn(the, h)
        self.assertIn("luu-y-ai", h)     # dòng nhắc "AI có thể sai" luôn hiện cạnh kết quả
        self.assertIn("AI có thể sai", h)

    def test_tieu_de_ten_don_vi_thoat_html_va_mo_hinh_ai(self):
        h = render(TRANG, onebee_box_ten_don_vi='<script>alert("x")</script>')
        self.assertNotIn('<script>alert("x")', h)
        self.assertIn("&lt;script&gt;", h)
        self.assertIn(f'data-mo-hinh-ai="{bien()["onebee_box_ai_model"]}"', self.html)
        self.assertIn("HTX An Phú", self.html)
        self.assertIn("<title>Sổ điều hành", render(TRANG, onebee_box_ten_don_vi=""))

    def test_chi_goi_dung_cac_duong_dan_da_giao_kem(self):
        js = self.js
        duong = set(re.findall(r"""["'](/(?:api|files|ai|quy-trinh)/[A-Za-z0-9_/.\-]*)""", js))
        da_giao = {"/api/toi", "/api/don_hang", "/api/yeu_cau_ho_tro", "/api/khao_sat", "/api/khao_sat_tong_hop", "/api/tinh_trang_may",
                   "/api/tep_dinh_kem", "/files/", "/ai/hoi", "/ai/tom-tat", "/quy-trinh/webhook/onebee-phe-duyet"}
        self.assertEqual(duong, da_giao)
        self.assertNotIn("/ai/api/chat", js)   # dịch vụ Trợ lý chỉ mở /ai/hoi và /ai/tom-tat (Giai đoạn 3)
        self.assertNotIn("/webhook/", re.sub(r"/quy-trinh/webhook/", "", js))   # không gọi webhook không qua /quy-trinh/
        self.assertNotIn(":5678", js)
        self.assertNotIn(":3000", js)

    def test_du_lieu_nguoi_dung_chi_hien_bang_textcontent(self):
        js = self.js
        self.assertIn("textContent", js)
        self.assertNotRegex(js, r"\.(innerText|outerText)\s*=")
        # mọi lần gọi fetch đều xin JSON để phiên hết hạn trả 401 chứ không đổi sang HTML trang đăng nhập
        self.assertIn("application/json", js)
        self.assertIn("no-store", js)

    def test_html_la_html_hop_le_co_lang_vi(self):
        self.assertTrue(self.html.lstrip().lower().startswith("<!doctype html>"))
        self.assertIn('<html lang="vi">', self.html)
        self.assertIn('name="viewport"', self.html)


@unittest.skipUnless(NODE, "cần node")
class MaJavaScript(unittest.TestCase):
    """Chạy so-dieu-hanh.js THẬT trong node (không có `document`, nên chỉ nạp các hàm thuần)."""

    def chay(self, bieu_thuc):
        ma = (
            "const vm = require('vm'); const fs = require('fs');\n"
            "const ctx = vm.createContext({});\n"
            "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx, {filename: 'so-dieu-hanh.js'});\n"
            f"console.log(JSON.stringify(vm.runInContext({json.dumps(bieu_thuc)}, ctx)));\n"
        )
        r = subprocess.run([NODE, "-e", ma, JS], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_doc_so_dong_tu_content_range(self):
        for gia_tri, mong_doi in (("0-4/5", 5), ("*/0", 0), ("*/137", 137), ("0-0/*", None), ("", None), ("sai", None)):
            self.assertEqual(self.chay(f"docSoDong({json.dumps(gia_tri)})"), mong_doi, gia_tri)
        self.assertIsNone(self.chay("docSoDong(null)"))

    def test_don_hang_hop_le(self):
        kq = self.chay("""dungDonHang({khach_hang: '  HTX An Phú ', mat_hang: 'Mật ong', so_luong_kg: '3', don_gia: '100000',
                           ngay_giao: '2026-12-01', ghi_chu: ''})""")
        self.assertEqual(kq["than"], {"khach_hang": "HTX An Phú", "mat_hang": "Mật ong", "so_luong_kg": 3, "don_gia": 100000,
                                      "thanh_tien": 300000, "ngay_giao": "2026-12-01"})
        self.assertNotIn("loi", kq)

    def test_don_hang_sai_bi_chan_o_trinh_duyet_kem_loi_giai_thich(self):
        co_ban = {"khach_hang": "A", "mat_hang": "B", "so_luong_kg": "2", "don_gia": "10", "ngay_giao": "", "ghi_chu": ""}
        for sua, tu_khoa in (({"khach_hang": "   "}, "khách hàng"), ({"mat_hang": ""}, "mặt hàng"), ({"so_luong_kg": "0"}, "số lượng"),
                             ({"so_luong_kg": "-3"}, "số lượng"), ({"so_luong_kg": "abc"}, "số lượng"), ({"don_gia": "-1"}, "đơn giá"),
                             ({"don_gia": ""}, "đơn giá"), ({"ngay_giao": "mai"}, "ngày giao"),
                             ({"khach_hang": "x" * 201}, "khách hàng")):
            kq = self.chay(f"dungDonHang({json.dumps({**co_ban, **sua})})")
            self.assertIn("loi", kq, sua)
            self.assertIn(tu_khoa, kq["loi"].lower(), sua)
            self.assertNotIn("than", kq, sua)

    def test_thong_bao_loi_tieng_viet(self):
        def tb(ma, than):
            return self.chay(f"thongBaoLoi({ma}, {json.dumps(than)})")
        self.assertIn("hết hạn", tb(401, None))
        self.assertIn("không có quyền", tb(403, {"code": "42501", "message": "permission denied for view khao_sat_tong_hop"}))
        self.assertIn("quá lớn", tb(413, None))
        self.assertIn("không được nhận", tb(415, {"loi": ""}))
        self.assertIn("chưa sẵn sàng", tb(503, None))
        self.assertIn("chưa sẵn sàng", tb(502, {"loi": ""}))
        self.assertIn("Mức độ", tb(400, {"code": "23514", "message": 'new row violates check constraint "muc_do_trong_danh_muc"'}))
        self.assertIn("Loại sự cố", tb(400, {"message": 'violates check constraint "loai_trong_danh_muc"'}))
        self.assertIn("tự duyệt", tb(400, {"message": 'violates check constraint "khong_tu_duyet"'}))
        self.assertIn("Số lượng", tb(400, {"message": 'violates check constraint "so_luong_duong_don_gia_khong_am"'}))
        self.assertIn("chưa hợp lệ", tb(400, {"message": "gì đó không rõ"}))
        # Dịch vụ của Box trả lời tiếng Việt thì dùng nguyên văn
        self.assertEqual(tb(409, {"loi": "Chốt chặn: không tự phê duyệt đơn của chính mình"}), "Chốt chặn: không tự phê duyệt đơn của chính mình")
        self.assertIn("mã 418", tb(418, None))

    SO_LIEU = {
        "don_hang": {"tong": 12, "cho_duyet": 3, "da_duyet": 7, "tu_choi": 2},
        "ho_tro": {"tong": 5, "gap": 1},
        "may_tram": 4,
        "tep": {"tong": 9, "sach": 8, "nhiem": 1},
        "khao_sat": [{"tuan": "2026-11-09", "so_phieu": 6, "diem_tb": 4.2}],
    }

    def test_tom_tat_tuan_chi_gui_so_lieu_tong_hop(self):
        # Dữ liệu "bẩn": có tên người, số điện thoại, tên khách ở mọi chỗ — chỉ con số được phép đi qua
        ban = json.loads(json.dumps(self.SO_LIEU))
        ban["don_hang"].update(nguoi_tao="Nguyễn Văn An", khach_hang="HTX Bình Minh", ghi_chu="gọi 0912345678")
        ban["ho_tro"]["nguoi_bao"] = "Trần Thị Bình"
        ban["khao_sat"][0].update(gop_y="Anh Cường chậm quá", ten="Lê Hoa")
        ban["nguoi_dung"] = "binh"
        ban["may_tram"] = 4
        ban["tep"]["ten_tep"] = "bao-gia-nguyen-van-an.pdf"
        ban["khao_sat"].append({"tuan": "Nguyễn Văn An", "so_phieu": "0912345678", "diem_tb": "x"})
        loi_nhac = self.chay(f"taoLoiNhacTomTat({json.dumps(ban)})")
        for ten in ("Nguyễn", "Văn An", "Bình Minh", "0912345678", "Trần", "Cường", "Lê Hoa", "binh", "bao-gia", "nguoi_tao", "khach_hang",
                    "ghi_chu", "gop_y", "ten_tep", "nguoi_bao"):
            self.assertNotIn(ten, loi_nhac, ten)
        phan_json = loi_nhac[loi_nhac.index("{"):]
        so_lieu = json.loads(phan_json)
        self.assertEqual(so_lieu["don_hang"], self.SO_LIEU["don_hang"])
        self.assertEqual(so_lieu["ho_tro"], self.SO_LIEU["ho_tro"])
        self.assertEqual(so_lieu["may_tram"], 4)
        self.assertEqual(so_lieu["tep"], self.SO_LIEU["tep"])
        self.assertEqual(so_lieu["khao_sat"], self.SO_LIEU["khao_sat"])   # dòng có tuần/số phiếu không hợp lệ bị bỏ
        self.assertIn("tiếng Việt", loi_nhac)
        self.assertIn("không bịa", loi_nhac)

    def test_mau_tom_tat_la_chuoi_json_mot_dong_de_bai_kiem_tren_box_doc_duoc(self):
        dong = [d for d in doc(JS).splitlines() if d.startswith("var MAU_TOM_TAT = ")]
        self.assertEqual(len(dong), 1)
        mau = json.loads(dong[0][len("var MAU_TOM_TAT = "):].rstrip().rstrip(";"))
        self.assertEqual(self.chay("MAU_TOM_TAT"), mau)
        self.assertEqual(self.chay("taoLoiNhacTomTat({})").startswith(mau), True)

    def test_so_lieu_thieu_van_tao_duoc_loi_nhac(self):
        loi_nhac = self.chay("taoLoiNhacTomTat({don_hang: {tong: 'abc', cho_duyet: -1}})")
        so_lieu = json.loads(loi_nhac[loi_nhac.index("{"):])
        self.assertEqual(so_lieu, {})

    def test_khong_co_ten_tuy_y_di_vao_so_lieu_gui_ai(self):
        loi_nhac = self.chay("taoLoiNhacTomTat({__proto__: {x: 1}, constructor: 'a', don_hang: {tong: 2, toString: 'b'}})")
        self.assertEqual(json.loads(loi_nhac[loi_nhac.index("{"):]), {"don_hang": {"tong": 2}})


class BoCaiVaNoiTrang(unittest.TestCase):
    def test_thu_muc_trang_duoc_tao_truoc_khi_sinh_trang(self):
        with open(os.path.join(STACK, "tasks/main.yml"), encoding="utf-8") as f:
            viec = yaml.safe_load(f)
        vi_tri_thu_muc = vi_tri_trang = None
        for i, t in enumerate(viec):
            noi_dung = json.dumps(t, ensure_ascii=False)
            if "portal/site/so-dieu-hanh" in noi_dung and "ansible.builtin.file" in t and vi_tri_thu_muc is None:
                vi_tri_thu_muc = i
            if "so-dieu-hanh.html.j2" in noi_dung and vi_tri_trang is None:
                vi_tri_trang = i
        self.assertIsNotNone(vi_tri_thu_muc, "chưa có việc tạo thư mục portal/site/so-dieu-hanh")
        self.assertIsNotNone(vi_tri_trang, "chưa có việc sinh trang so-dieu-hanh")
        self.assertLessEqual(vi_tri_thu_muc, vi_tri_trang)
        noi_dung = json.dumps(viec, ensure_ascii=False)
        for tep in ("so-dieu-hanh.css", "so-dieu-hanh.js", "portal/site/so-dieu-hanh/index.html"):
            self.assertIn(tep, noi_dung)

    def test_trang_chu_tro_toi_ung_dung_thay_bieu_mau_cu(self):
        h = render(os.path.join(STACK, "templates/index.html.j2"), onebee_box_ten_mdns="onebee", onebee_https_hieu_luc=True)
        self.assertIn('href="/so-dieu-hanh/"', h)
        self.assertIn("Sổ điều hành", h)
        self.assertNotIn("form/onebee-ho-tro", h)
        self.assertNotIn("form/onebee-don-hang", h)

    def test_trang_chu_o_che_do_http_khong_dan_toi_tuyen_khong_co(self):
        h = render(os.path.join(STACK, "templates/index.html.j2"), onebee_box_ten_mdns="onebee", onebee_https_hieu_luc=False)
        self.assertNotIn('href="/so-dieu-hanh/"', h)
        self.assertIn("HTTPS", h)

    def test_menu_bao_can_ho_tro_mo_ung_dung_tren_ten_box(self):
        with open(MUC_MENU, encoding="utf-8") as f:
            viec = yaml.safe_load(f)
        conf = next(t for t in viec if t.get("name", "").startswith("Ghi địa chỉ"))
        noi_dung = conf["ansible.builtin.copy"]["content"]
        self.assertIn("HO_TRO_URL=https://{{ onebee_may_tram.BOX_TEN }}/so-dieu-hanh/", noi_dung)
        self.assertNotIn("5678", noi_dung)
        self.assertNotIn("form/", noi_dung)
        dieu_kien = json.dumps(conf["when"])
        self.assertIn("BOX_TEN", dieu_kien)
        self.assertIn("BOX_HTTPS", dieu_kien)


class TuyenCaddy(unittest.TestCase):
    """Không cần Caddy thật (bài có Caddy thật ở test_onebee_caddy_sso.py): kiểm văn bản Caddyfile sinh ra."""

    def caddyfile(self, **them):
        return render(os.path.join(STACK, "templates/Caddyfile.j2"), onebee_box_ports={"portal": 80,
                                                                                         "rest_server": 8000, "uptime_kuma": 3001}, **them)

    def khoi(self, nd, mo_dau):
        i = nd.index(mo_dau)
        sau = nd[i:]
        return sau[:sau.index("\n\t}\n") + 4] if "\n\t}\n" in sau else sau

    def test_co_sso_trang_nam_sau_forward_auth(self):
        nd = self.caddyfile()
        k = self.khoi(nd, "@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\thandle @so_dieu_hanh {")
        self.assertIn("import onebee_sso", k)
        self.assertLess(k.index("import onebee_sso"), k.index("file_server"))
        self.assertIn("root * /srv\n", k)
        for tieu_de in ("Content-Security-Policy", "default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'self'",
                        "form-action 'none'", "frame-ancestors 'none'", "base-uri 'none'", "Cache-Control", "X-Content-Type-Options nosniff"):
            self.assertIn(tieu_de, k, tieu_de)
        self.assertNotIn("unsafe-inline", k)
        self.assertNotIn("unsafe-eval", k)

    def test_vao_bang_ip_chuyen_sang_ten_box(self):
        nd = self.caddyfile()
        khoi_ip = nd[nd.index("https://192.168.1.10:443 {"):nd.index("https://box.anphu.onebee.internal:443 {")]
        self.assertIn("@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*", khoi_ip)
        self.assertIn("redir https://box.anphu.onebee.internal{uri} 308", khoi_ip)

    def test_sso_tam_tat_tra_503(self):
        nd = self.caddyfile(onebee_sso_hieu_luc=False)
        k = self.khoi(nd, "@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\thandle @so_dieu_hanh {")
        self.assertIn("respond", k)
        self.assertIn("503", k)
        self.assertNotIn("file_server", k)

    def test_che_do_http_khong_co_ung_dung(self):
        nd = self.caddyfile(onebee_https_hieu_luc=False)
        self.assertIn("@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\trespond @so_dieu_hanh 404", nd)
        self.assertLess(nd.index("respond @so_dieu_hanh 404"), nd.index("file_server"))


class LuatAuthelia(unittest.TestCase):
    def test_luat_cho_trang(self):
        with tempfile.TemporaryDirectory():
            cfg = yaml.safe_load(render(os.path.join(ROLES, "box-dinh-danh/templates/configuration.yml.j2")))
        luat = [r for r in cfg["access_control"]["rules"] if any("so-dieu-hanh" in x for x in r.get("resources", []))]
        self.assertEqual(len(luat), 2)
        theo_nhom = {tuple(r["subject"]): r["policy"] for r in luat}
        self.assertEqual(theo_nhom, {("group:ky_thuat", "group:quan_ly"): "two_factor", ("group:nhan_vien",): "one_factor"})
        for r in luat:
            self.assertEqual(r["domain"], "box.anphu.onebee.internal")
            for duong in ("/so-dieu-hanh/", "/so-dieu-hanh", "/so-dieu-hanh/so-dieu-hanh.js", "/so-dieu-hanh/?may=ketoan-01"):
                self.assertTrue(any(re.search(x, duong) for x in r["resources"]), duong)
            for duong in ("/so-dieu-hanh-gia/", "/x/so-dieu-hanh/", "/so-dieu-hanhx"):
                self.assertFalse(any(re.search(x, duong) for x in r["resources"]), duong)


if __name__ == "__main__":
    unittest.main()
