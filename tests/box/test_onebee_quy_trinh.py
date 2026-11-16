#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Động cơ quy trình Node-RED của Box (role box-quy-trinh), không cần Docker:
- compose: dịch vụ quy-trinh không công bố cổng, ghim tag + digest, không tự nâng quyền, không vào mạng sso/api/csdl,
  danh sách máy đã cấp (may-da-cap) và cấu hình gắn CHỈ ĐỌC; Caddy có tên Box trong mạng default (Node-RED gọi lại /api/ qua Caddy);
- settings.js: adminAuth bật, trình soạn (httpAdminRoot) tách khỏi điểm nhận (httpNodeRoot), không mật khẩu/khóa dạng rõ, không cài gói;
- cau-hinh.json: chỉ SHA-256 của khóa, bản băm bcrypt của mật khẩu trình soạn; khóa gửi tình trạng chung theo đúng cờ;
- flows.json: JSON hợp lệ, chỉ nút lõi, đủ điểm nhận và lịch 7:30;
- role: đặt sau box-du-lieu, tự tạo thư mục và tệp TRƯỚC khi chạy container;
- mô-đun onebee-quy-trinh.js chạy bằng node thật: tình trạng máy trạm, thư SMTP (máy chủ thư giả), phê duyệt (API giả).
Chạy: python3 -m unittest"""
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ANSIBLE = os.path.join(ROOT, "box/ansible")
ROLE = os.path.join(ANSIBLE, "roles/box-quy-trinh")
STACK = os.path.join(ANSIBLE, "roles/box-stack/templates")
MAT_KHAU_SOAN = "MatKhauSoanLuongRo123"
KHOA_BOX = "KhoaWebhookBoxRo0123456789abcdef"
KHOA_TRAM = "KhoaTramChungRo0123456789abcdef"
BAM = "$2b$10$abcdefghijklmnopqrstuuJ1sQ9Jb3lG4fGQ7xXqv0Zz8Yh2K6m3e"
TEN_CU = "n" + "8n"   # tên công cụ quy trình cũ, dựng chuỗi để không còn nguyên văn trong kho mã


def bien(**them):
    v = yaml.safe_load(open(os.path.join(ANSIBLE, "group_vars/all.yml"), encoding="utf-8"))
    v.update(yaml.safe_load(open(os.path.join(ROLE, "vars/main.yml"), encoding="utf-8")) or {})
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_sso_hieu_luc=True,
             onebee_webhook_key=KHOA_BOX, onebee_tram_key=KHOA_TRAM, onebee_quy_trinh_soan_hash=BAM, onebee_smtp_password="mk-smtp",
             onebee_smtp_co_mat_khau=True)
    v.update(them)
    return v


def moi_truong(thu_muc=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(thu_muc) if thu_muc else None, keep_trailing_newline=True, trim_blocks=True)
    env.filters["bool"] = bool
    env.filters["to_json"] = lambda x: json.dumps(x, ensure_ascii=False)
    env.filters["to_nice_json"] = lambda x: json.dumps(x, ensure_ascii=False, indent=4, sort_keys=True)
    env.filters["hash"] = lambda x, kieu: hashlib.new(kieu, str(x).encode()).hexdigest()
    env.filters["int"] = int
    env.filters["quote"] = shlex.quote
    return env


def ve(ten, **them):
    return moi_truong(os.path.join(ROLE, "templates")).get_template(ten).render(**bien(**them))


def compose(https=True):
    nd = moi_truong().from_string(open(os.path.join(STACK, "docker-compose.yml.j2"), encoding="utf-8").read())
    return yaml.safe_load(nd.render(**bien(onebee_https_hieu_luc=https)))


class ComposeQuyTrinh(unittest.TestCase):
    def test_khong_cong_ghim_digest_khong_nang_quyen_hai_che_do(self):
        anh = bien()["onebee_box_images"]["node_red"]
        self.assertRegex(anh, r"^docker\.io/nodered/node-red:5\.0\.9@sha256:[0-9a-f]{64}$")
        for https in (True, False):
            dv = compose(https)["services"]["quy-trinh"]
            self.assertNotIn("ports", dv, https)
            self.assertEqual(dv["image"], anh)
            self.assertEqual(dv["container_name"], "onebee-quy-trinh")
            self.assertIn("no-new-privileges:true", dv["security_opt"])
            self.assertEqual(dv["cap_drop"], ["ALL"])
            self.assertEqual(dv["logging"]["driver"], "json-file")
            mang = dv.get("networks", ["default"])
            self.assertEqual(set(mang), {"default"})                 # không tới được cầu nối, định danh, PostgREST, PostgreSQL
            self.assertEqual(dv["command"], ["--settings", "/cau-hinh/settings.js"])

    def test_gan_chi_doc_danh_sach_may_da_cap_va_cau_hinh(self):
        v = compose()["services"]["quy-trinh"]["volumes"]
        self.assertIn("/srv/onebee/may-da-cap:/may-da-cap:ro", v)
        self.assertIn("./quy-trinh:/cau-hinh:ro", v)
        self.assertIn("/srv/onebee/tinh-trang-may:/tinh-trang-may", v)
        self.assertFalse([x for x in v if "secrets" in x or "pki" in x])   # không gắn thư mục bí mật / khóa CA trung gian

    def test_caddy_mang_ten_box_trong_mang_default(self):
        p = compose()["services"]["portal"]["networks"]
        self.assertIn("box.anphu.onebee.internal", p["default"]["aliases"])
        self.assertIn("sso", p)

    def test_khong_con_dich_vu_hay_cong_cu(self):
        c = compose(True)
        self.assertNotIn(TEN_CU, c["services"])
        self.assertFalse([x for x in c["services"]["portal"]["ports"] if "5678" in x])
        self.assertNotIn(TEN_CU, bien()["onebee_box_ports"])
        self.assertNotIn(TEN_CU, bien()["onebee_box_images"])


class SettingsJs(unittest.TestCase):
    def setUp(self):
        self.nd = ve("settings.js.j2")

    def test_adminauth_va_hai_goc_tach_nhau(self):
        self.assertRegex(self.nd, r"adminAuth:\s*\{\s*type: 'credentials'")
        quan_tri = re.search(r"httpAdminRoot: '([^']+)'", self.nd).group(1)
        diem_nhan = re.search(r"httpNodeRoot: '([^']+)'", self.nd).group(1)
        self.assertEqual(quan_tri, "/quy-trinh")
        self.assertEqual(diem_nhan, "/webhook")
        self.assertNotEqual(quan_tri, diem_nhan)
        self.assertFalse(quan_tri.startswith(diem_nhan) or diem_nhan.startswith(quan_tri))

    def test_khong_mat_khau_dang_ro_khong_cai_goi(self):
        for bi_mat in (MAT_KHAU_SOAN, KHOA_BOX, KHOA_TRAM, "mk-smtp", BAM):
            self.assertNotIn(bi_mat, self.nd)
        self.assertNotRegex(self.nd, r"\$2[aby]\$")
        self.assertIn("functionExternalModules: false", self.nd)
        self.assertIn("allowInstall: false", self.nd)
        self.assertIn("autoInstall: false", self.nd)


class CauHinhJson(unittest.TestCase):
    def test_chi_ban_bam_cua_khoa_va_mat_khau_soan(self):
        nd = ve("cau-hinh.json.j2")
        ch = json.loads(nd)
        for bi_mat in (KHOA_BOX, KHOA_TRAM, MAT_KHAU_SOAN):
            self.assertNotIn(bi_mat, nd)
        self.assertEqual(ch["khoa_box_sha256"], hashlib.sha256(KHOA_BOX.encode()).hexdigest())
        self.assertEqual(ch["khoa_tram_sha256"], hashlib.sha256(KHOA_TRAM.encode()).hexdigest())
        self.assertTrue(ch["khoa_chung"])
        self.assertTrue(ch["soan_luong_hash"].startswith("$2b$"))
        self.assertEqual(ch["api_goc"], "https://box.anphu.onebee.internal")
        self.assertEqual((ch["may_da_cap"], ch["tinh_trang"]), ("/may-da-cap", "/tinh-trang-may"))

    def test_bo_khoa_chung(self):
        ch = json.loads(ve("cau-hinh.json.j2", onebee_box_khoa_tinh_trang_chung=False, onebee_tram_key=""))
        self.assertFalse(ch["khoa_chung"])
        self.assertEqual(ch["khoa_tram_sha256"], "")


class FlowsJson(unittest.TestCase):
    def test_luong_hop_le_chi_nut_loi_du_diem_nhan(self):
        for chung in (True, False):
            luong = json.loads(ve("flows.json.j2", onebee_box_khoa_tinh_trang_chung=chung))
            self.assertTrue({n["type"] for n in luong} <= {"tab", "http in", "function", "http response", "inject", "comment"})
            ids = [n["id"] for n in luong]
            self.assertEqual(len(ids), len(set(ids)))
            noi = {w for n in luong for ra in n.get("wires", []) for w in ra}
            self.assertTrue(noi <= set(ids))
            vao = {n["url"]: n["method"] for n in luong if n["type"] == "http in"}
            for url in ("/onebee-bao-cao-sao-luu", "/onebee-nhac-han", "/onebee-tong-hop-don-hang", "/onebee-tinh-trang",
                        "/onebee-canh-bao", "/onebee-phe-duyet"):
                self.assertEqual(vao.get(url), "post", url)
            self.assertEqual(vao.get("/suc-khoe"), "get")
            self.assertIn("30 07 * * *", [n.get("crontab") for n in luong if n["type"] == "inject"])
            for n in luong:
                if n["type"] == "function":
                    self.assertIn("global.get('onebee').xuLy(", n["func"])
                    self.assertFalse(n.get("libs"))


class RoleQuyTrinh(unittest.TestCase):
    def test_sau_box_du_lieu_trong_site(self):
        vai = yaml.safe_load(open(os.path.join(ANSIBLE, "site.yml"), encoding="utf-8"))[0]["roles"]
        self.assertIn("box-quy-trinh", vai)
        self.assertNotIn("box-" + TEN_CU, vai)
        self.assertGreater(vai.index("box-quy-trinh"), vai.index("box-du-lieu"))
        self.assertFalse(os.path.exists(os.path.join(ANSIBLE, "roles/box-" + TEN_CU)))

    def test_tao_thu_muc_va_tep_truoc_khi_chay_container(self):
        tasks = yaml.safe_load(open(os.path.join(ROLE, "tasks/main.yml"), encoding="utf-8"))
        chu = [json.dumps(t, ensure_ascii=False) for t in tasks]
        chay = next(i for i, t in enumerate(chu) if "docker compose up" in t and "quy-trinh" in t)
        for can in ("state\": \"directory", "settings.js", "cau-hinh.json", "flows.json", "onebee-quy-trinh.js", "ca.crt"):
            truoc = [i for i, t in enumerate(chu) if can in t]
            self.assertTrue(truoc and min(truoc) < chay, can)
        self.assertFalse([t for t in tasks if "ignore_errors" in t])


# ---------- Mô-đun chạy bằng node thật ----------
class MayChuThuGia(threading.Thread):
    """Máy chủ SMTP giả (không TLS, không đăng nhập): ghi lại lệnh và thư nhận được."""

    def __init__(self):
        super().__init__(daemon=True)
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        self.s.listen(5)
        self.cong = self.s.getsockname()[1]
        self.lenh, self.thu = [], []

    def run(self):
        while True:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            f = c.makefile("rb")
            c.sendall(b"220 gia ESMTP\r\n")
            while True:
                d = f.readline().decode().rstrip("\r\n")
                if not d:
                    break
                self.lenh.append(d)
                if d.startswith("EHLO"):
                    c.sendall(b"250-gia\r\n250 8BITMIME\r\n")
                elif d == "DATA":
                    c.sendall(b"354 go\r\n")
                    than = []
                    while (x := f.readline().decode()) != ".\r\n":
                        than.append(x)
                    self.thu.append("".join(than))
                    c.sendall(b"250 ok\r\n")
                elif d == "QUIT":
                    c.sendall(b"221 bye\r\n")
                    break
                else:
                    c.sendall(b"250 ok\r\n")
            c.close()


class ApiGia(BaseHTTPRequestHandler):
    """Giả Caddy /api/don_hang: phiên 'phien-binh' là quản lý binh; đơn 1 của an chờ duyệt, đơn 2 của binh, đơn 3 đã duyệt."""
    don = {}
    ghi = []

    def log_message(self, *a):
        pass

    def tra(self, ma, than):
        b = json.dumps(than).encode()
        self.send_response(ma)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def phien(self):
        return "authelia_session=phien-binh" in (self.headers.get("Cookie") or "")

    def do_GET(self):
        if not self.phien():
            return self.tra(401, {})
        m = re.search(r"id=eq\.(\d+)", self.path)
        d = self.don.get(int(m.group(1))) if m else None
        self.tra(200, [d] if d else [])

    def do_PATCH(self):
        than = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).ghi.append((self.path, self.headers.get("Cookie"), than))
        if not self.phien():
            return self.tra(401, {})
        d = self.don[int(re.search(r"id=eq\.(\d+)", self.path).group(1))]
        if d["nguoi_tao"] == "binh":
            return self.tra(400, {"code": "23514", "message": 'new row violates check constraint "khong_tu_duyet"'})
        d.update(than, nguoi_duyet="binh", thoi_gian_duyet="2026-11-16T09:00:00")
        self.tra(200, [d])


@unittest.skipUnless(shutil.which("node"), "cần node")
class MoDunNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.mkdtemp()
        cls.smtp = MayChuThuGia()
        cls.smtp.start()
        cls.api = ThreadingHTTPServer(("127.0.0.1", 0), ApiGia)
        threading.Thread(target=cls.api.serve_forever, daemon=True).start()
        for d in ("cau-hinh", "may-da-cap", "tinh-trang-may"):
            os.makedirs(f"{cls.t}/{d}")
        open(f"{cls.t}/may-da-cap/ketoan-01", "w").write("1\n")
        ch = json.loads(ve("cau-hinh.json.j2"))
        ch.update(may_da_cap=f"{cls.t}/may-da-cap", tinh_trang=f"{cls.t}/tinh-trang-may", api_goc=f"http://127.0.0.1:{cls.api.server_port}")
        ch["thu"].update(host="127.0.0.1", port=cls.smtp.cong, starttls=False, ssl=False, user="")
        json.dump(ch, open(f"{cls.t}/cau-hinh/cau-hinh.json", "w"))
        shutil.copy(os.path.join(ROLE, "files/onebee-quy-trinh.js"), f"{cls.t}/cau-hinh/")
        open(f"{cls.t}/cau-hinh/settings.js", "w").write(ve("settings.js.j2"))

    @classmethod
    def tearDownClass(cls):
        cls.api.shutdown()
        cls.smtp.s.close()
        shutil.rmtree(cls.t)

    def goi(self, diem, than=None, tieu_de=None):
        msg = {"payload": than if than is not None else {}, "req": {"headers": {k.lower(): v for k, v in (tieu_de or {}).items()}}}
        ma = ("const q = require(process.argv[1]);"
              "q.xuLy(process.argv[2], JSON.parse(process.argv[3])).then(m => console.log(JSON.stringify({ma: m.statusCode, than: m.payload})));")
        r = subprocess.run(["node", "-e", ma, f"{self.t}/cau-hinh/onebee-quy-trinh.js", diem, json.dumps(msg)],
                           capture_output=True, text=True, timeout=60, env=dict(os.environ, ONEBEE_CAU_HINH=f"{self.t}/cau-hinh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout.strip().splitlines()[-1])
        return kq["ma"], kq["than"]

    def test_settings_nap_duoc_va_dung_gia_tri(self):
        ma = ("const s = require(process.argv[1]); console.log(JSON.stringify({a: s.httpAdminRoot, n: s.httpNodeRoot, u: s.adminAuth.users,"
              " f: typeof s.functionGlobalContext.onebee.xuLy}));")
        r = subprocess.run(["node", "-e", ma, f"{self.t}/cau-hinh/settings.js"], capture_output=True, text=True,
                           env=dict(os.environ, ONEBEE_CAU_HINH=f"{self.t}/cau-hinh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        s = json.loads(r.stdout)
        self.assertEqual((s["a"], s["n"], s["f"]), ("/quy-trinh", "/webhook", "function"))
        self.assertEqual(s["u"], [{"username": "kythuat", "password": BAM, "permissions": "*"}])

    def test_tinh_trang_chi_may_da_cap_dung_khoa(self):
        k = {"X-OneBee-Key": KHOA_TRAM}
        self.assertEqual(self.goi("tinh-trang", {"ten": "ketoan-01"}, {"X-OneBee-Key": "sai"})[0], 403)
        self.assertEqual(self.goi("tinh-trang", {"ten": "ketoan-01"})[0], 403)
        self.assertEqual(self.goi("tinh-trang", {"ten": "../etc"}, k)[0], 400)
        self.assertEqual(self.goi("tinh-trang", {"ten": "chua-cap"}, k)[0], 403)
        self.assertFalse(os.path.exists(f"{self.t}/tinh-trang-may/chua-cap.json"))
        self.assertEqual(self.goi("tinh-trang", {"ten": "ketoan-01", "du_lieu": "{}", "ky": "x"}, k)[0], 400)
        ma, _ = self.goi("tinh-trang", {"ten": "ketoan-01", "du_lieu": '{"a":1}', "ky": "a" * 64}, k)
        self.assertEqual(ma, 200)
        tt = json.load(open(f"{self.t}/tinh-trang-may/ketoan-01.json"))
        self.assertEqual((tt["dinh_dang"], tt["du_lieu"], tt["ky"]), (2, '{"a":1}', "a" * 64))   # lưu nguyên bao bì có chữ ký
        ma, _ = self.goi("tinh-trang", {"ten": "ketoan-01", "ip": "1.2.3.4", "o_trong_phan_tram": 150, "hostname": "a\nb"}, k)
        tt = json.load(open(f"{self.t}/tinh-trang-may/ketoan-01.json"))
        self.assertEqual((ma, tt["ip"], tt["o_trong_phan_tram"], tt["hostname"]), (200, "1.2.3.4", None, "a b"))
        self.assertFalse([f for f in os.listdir(f"{self.t}/tinh-trang-may") if f.endswith(".tam")])

    def test_thu_bao_cao_sao_luu_va_nhac_han_qua_smtp(self):
        self.assertEqual(self.goi("bao-cao-sao-luu", {"trang_thai": "DAT"}, {"X-OneBee-Key": "sai"})[0], 403)
        n = len(self.smtp.thu)
        ma, than = self.goi("bao-cao-sao-luu", {"trang_thai": "DAT", "noi_dung": "xong", "may_tram": [
            {"ten": "ketoan-01", "canh_bao": []}, {"ten": "kho-02", "canh_bao": ["mất liên lạc"]}]}, {"X-OneBee-Key": KHOA_BOX})
        self.assertEqual((ma, than["tieu_de"]), (200, "[OneBee Box] Sao lưu ĐẠT — 1 máy trạm cần xử lý"))
        thu = self.smtp.thu[n]
        self.assertIn("Subject: =?UTF-8?B?", thu)
        self.assertIn("Content-Transfer-Encoding: base64", thu)
        self.assertIn("MAIL FROM:<box@onebee.lan>", self.smtp.lenh)
        self.assertIn("RCPT TO:<quantri@onebee.lan>", self.smtp.lenh)
        ma, than = self.goi("nhac-han", {"hom_nay": "2026-10-17"}, {"X-OneBee-Key": KHOA_BOX})
        self.assertEqual((ma, than["tieu_de"]), (200, "[OneBee] Nhắc hạn nộp: 1 việc — gần nhất còn 3 ngày"))
        self.assertEqual(self.goi("nhac-han", {"hom_nay": "17/10"}, {"X-OneBee-Key": KHOA_BOX})[0], 400)

    def test_tong_hop_don_hang_va_canh_bao(self):
        k = {"X-OneBee-Key": KHOA_BOX}
        don = [{"khach_hang": "Siêu thị A", "mat_hang": "Xoài", "so_luong_kg": 500, "don_gia": 30000, "thanh_tien": 15000000,
                "ngay_giao": "2026-10-05", "trang_thai_duyet": "CHO_DUYET"},
               {"khach_hang": "Quán C", "mat_hang": "Bưởi", "so_luong_kg": 100, "don_gia": 25000, "thanh_tien": 2500000,
                "ngay_giao": "2026-10-06", "trang_thai_duyet": "DA_DUYET"}]
        ma, than = self.goi("tong-hop-don-hang", {"ngay": "2026-10-05", "don": don}, k)
        self.assertEqual((ma, than["tieu_de"]), (200, "[OneBee] Đơn hàng hôm nay: 2 đơn — 17.500.000 đồng"))
        ma, than = self.goi("canh-bao", {"muc_do": "warn", "tieu_de": "Ổ đầy\r\nBcc: x@y", "don_vi": "HTX An Phú"}, k)
        self.assertEqual((ma, than["tieu_de"]), (200, "[CẢNH BÁO] HTX An Phú: Ổ đầy Bcc: x@y"))   # không chèn được tiêu đề thư

    def test_may_chu_thu_hong_bao_loi_khong_treo(self):
        ch = json.load(open(f"{self.t}/cau-hinh/cau-hinh.json"))
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cong = s.getsockname()[1]
        s.close()
        ch["thu"]["port"] = cong
        t2 = tempfile.mkdtemp()
        try:
            shutil.copytree(f"{self.t}/cau-hinh", f"{t2}/cau-hinh")
            json.dump(ch, open(f"{t2}/cau-hinh/cau-hinh.json", "w"))
            ma = ("require(process.argv[1]).xuLy('canh-bao', {payload: {tieu_de: 'x'}, req: {headers: {'x-onebee-key': process.argv[2]}}})"
                  ".then(m => console.log(m.statusCode))")
            r = subprocess.run(["node", "-e", ma, f"{t2}/cau-hinh/onebee-quy-trinh.js", KHOA_BOX], capture_output=True, text=True,
                               timeout=40, env=dict(os.environ, ONEBEE_CAU_HINH=f"{t2}/cau-hinh"))
            self.assertEqual(r.stdout.strip(), "502", r.stderr)
        finally:
            shutil.rmtree(t2)

    def test_phe_duyet(self):
        ApiGia.don = {1: {"id": 1, "nguoi_tao": "an", "trang_thai_duyet": "CHO_DUYET"},
                      2: {"id": 2, "nguoi_tao": "binh", "trang_thai_duyet": "CHO_DUYET"},
                      3: {"id": 3, "nguoi_tao": "an", "trang_thai_duyet": "DA_DUYET"},
                      4: {"id": 4, "nguoi_tao": "an", "trang_thai_duyet": "CHO_DUYET"}}
        ApiGia.ghi = []
        ql = {"Remote-User": "binh", "Cookie": "khac=1; authelia_session=phien-binh"}
        self.assertEqual(self.goi("phe-duyet", {"id": 1, "trang_thai_duyet": "DA_DUYET"}, {"Remote-User": "binh"})[0], 401)
        self.assertEqual(self.goi("phe-duyet", {"id": 1, "trang_thai_duyet": "TU_CHOI", "ly_do_duyet": "  "}, ql)[0], 400)
        self.assertEqual(self.goi("phe-duyet", {"id": 1, "trang_thai_duyet": "XOA"}, ql)[0], 400)
        self.assertEqual(self.goi("phe-duyet", {"id": "1; drop", "trang_thai_duyet": "DA_DUYET"}, ql)[0], 400)
        self.assertEqual(self.goi("phe-duyet", {"id": 2, "trang_thai_duyet": "DA_DUYET"}, ql)[0], 403)        # tự duyệt
        self.assertEqual(self.goi("phe-duyet", {"id": 3, "trang_thai_duyet": "DA_DUYET"}, ql)[0], 409)        # đã xử lý
        self.assertEqual(self.goi("phe-duyet", {"id": 9, "trang_thai_duyet": "DA_DUYET"}, ql)[0], 404)
        self.assertEqual(ApiGia.ghi, [])                                                                          # chưa ghi gì
        # Người duyệt lấy từ Remote-User, không từ thân yêu cầu; chỉ cookie phiên được chuyển tiếp
        ma, than = self.goi("phe-duyet", {"id": 1, "trang_thai_duyet": "DA_DUYET", "ly_do_duyet": "Đủ hàng", "nguoi_duyet": "gia"}, ql)
        self.assertEqual((ma, than["trang_thai_duyet"], than["nguoi_duyet"]), (200, "DA_DUYET", "binh"))
        duong, cookie, gui = ApiGia.ghi[-1]
        self.assertEqual(cookie, "authelia_session=phien-binh")
        self.assertEqual(gui, {"trang_thai_duyet": "DA_DUYET", "ly_do_duyet": "Đủ hàng"})
        self.assertIn("trang_thai_duyet=eq.CHO_DUYET", duong)
        ma, than = self.goi("phe-duyet", {"id": 4, "trang_thai_duyet": "TU_CHOI", "ly_do_duyet": "Hết hàng"}, ql)
        self.assertEqual((ma, than["trang_thai_duyet"]), (200, "TU_CHOI"))
        # Cookie khác (không phải phiên quản lý): API trả 401 → 401
        self.assertEqual(self.goi("phe-duyet", {"id": 1, "trang_thai_duyet": "DA_DUYET"},
                                  {"Remote-User": "binh", "Cookie": "authelia_session=gia"})[0], 401)


if __name__ == "__main__":
    unittest.main()
