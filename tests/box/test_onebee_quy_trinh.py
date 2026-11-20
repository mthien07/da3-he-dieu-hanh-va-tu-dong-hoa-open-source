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
- mô-đun onebee-quy-trinh.js chạy bằng node thật: tình trạng máy trạm, thư SMTP (máy chủ thư giả), phê duyệt (API giả),
  máy trạm xin vào Box (giao thức cam kết + mã đối chiếu 3 bước, hai điểm duyệt chỉ tin /api/toi).
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
        self.assertIn("/srv/onebee/xin-vao:/xin-vao", v)            # yêu cầu xin vào: Node-RED ghi được
        self.assertIn("/srv/onebee/phong-ban-so:/phong-ban:ro", v)  # sổ phòng ban chỉ đọc (do onebee-box ghi)
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
        self.assertEqual((ch["xin_vao"], ch["phong_ban"]), ("/xin-vao", "/phong-ban"))

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
            for url in ("/onebee-xin-vao", "/onebee-xin-vao-mo", "/onebee-xin-vao-ket-qua", "/onebee-duyet-may"):
                self.assertEqual(vao.get(url), "post", url)
            self.assertEqual(vao.get("/onebee-may-xin-vao"), "get")
            self.assertEqual(vao.get("/suc-khoe"), "get")
            self.assertIn("30 07 * * *", [n.get("crontab") for n in luong if n["type"] == "inject"])
            for n in luong:
                if n["type"] == "function":
                    self.assertIn("global.get('onebee').xuLy(", n["func"])
                    self.assertFalse(n.get("libs"))


class BoSungLuongKhiNangCap(unittest.TestCase):
    """Box nâng cấp từ bản cũ đã có flows.json (bộ cài không ghi đè) vẫn phải nhận điểm nhận mới."""
    SCRIPT = os.path.join(ROLE, "files/onebee-bo-sung-luong.py")
    MOI = ("http_xin_vao", "fn_xin_vao", "http_xin_vao_mo", "http_xin_vao_ket_qua", "http_may_xin_vao", "http_duyet_may")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.mau = os.path.join(self.tmp, "mau.json")
        self.dich = os.path.join(self.tmp, "dang-chay.json")
        with open(self.mau, "w", encoding="utf-8") as f:
            f.write(ve("flows.json.j2"))

    def chay(self):
        return subprocess.run(["python3", self.SCRIPT, self.mau, self.dich], capture_output=True, text=True)

    def ghi_dich(self, luong):
        with open(self.dich, "w", encoding="utf-8") as f:
            json.dump(luong, f, ensure_ascii=False, indent=4)
        os.chmod(self.dich, 0o600)

    def test_box_cu_nhan_diem_nhan_moi_giu_nut_nguoi_dung_sua(self):
        cu = [n for n in json.load(open(self.mau, encoding="utf-8")) if "xin_vao" not in n["id"] and "duyet_may" not in n["id"]]
        next(n for n in cu if n["id"] == "fn_phe_duyet")["func"] = "return msg; // người dùng sửa"
        cu.append({"id": "nut_rieng", "type": "comment", "z": "tab_onebee_quy_trinh", "name": "của người dùng"})
        self.ghi_dich(cu)
        kq = self.chay()
        self.assertEqual(kq.returncode, 0, kq.stderr)
        self.assertTrue(kq.stdout.startswith("DA_BO_SUNG "), kq.stdout)
        sau = json.load(open(self.dich, encoding="utf-8"))
        theo_id = {n["id"]: n for n in sau}
        for i in self.MOI:
            self.assertIn(i, theo_id)
        self.assertEqual(theo_id["fn_phe_duyet"]["func"], "return msg; // người dùng sửa")
        self.assertIn("nut_rieng", theo_id)
        self.assertEqual(len(sau), len({n["id"] for n in sau}))
        self.assertEqual(os.stat(self.dich).st_mode & 0o777, 0o600)
        self.assertEqual(self.chay().stdout, "")   # chạy lại: đủ rồi, không đổi (bộ cài changed=0)

    def test_tep_hong_bao_loi_khong_ghi_de(self):
        with open(self.dich, "w", encoding="utf-8") as f:
            f.write("{hỏng")
        kq = self.chay()
        self.assertNotEqual(kq.returncode, 0)
        self.assertIn("LỖI", kq.stderr)
        self.assertEqual(open(self.dich, encoding="utf-8").read(), "{hỏng")

    def test_role_bo_sung_sau_khi_chep_va_khoi_dong_lai_node_red(self):
        tasks = yaml.safe_load(open(os.path.join(ROLE, "tasks/main.yml"), encoding="utf-8"))
        chu = [json.dumps(t, ensure_ascii=False) for t in tasks]
        chep = next(i for i, t in enumerate(chu) if "force\": false" in t and "node-red/flows.json" in t)
        bo_sung = next(i for i, t in enumerate(chu) if "onebee-bo-sung-luong.py" in t)
        chay = next(i for i, t in enumerate(chu) if "docker compose up" in t and "quy-trinh" in t)
        self.assertLess(chep, bo_sung)
        self.assertLess(bo_sung, chay)
        self.assertIn("onebee_qt_luong_bo_sung is changed", chu[chay])


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

    def test_thu_muc_xin_vao_va_so_phong_ban(self):
        tasks = yaml.safe_load(open(os.path.join(ROLE, "tasks/main.yml"), encoding="utf-8"))
        vong = next(t for t in tasks if "state" in json.dumps(t) and "xin-vao" in json.dumps(t))["loop"]
        theo = {i["path"].replace("{{ onebee_box_data }}/", ""): (i["owner"], i["group"], i["mode"]) for i in vong}
        self.assertEqual(theo["xin-vao"], ("1000", "1000", "0700"))
        self.assertEqual(theo["phong-ban-so"], ("root", "1000", "0750"))
        self.assertEqual(theo["phong-ban-so/may"], ("root", "1000", "0750"))


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

    NGUOI = {"phien-binh": {"ten": "binh", "vai_tro": "quan_ly"}, "phien-thuy": {"ten": "thuy", "vai_tro": "ky_thuat"},
             "phien-an": {"ten": "an", "vai_tro": "nhan_vien"}}

    def do_GET(self):
        if self.path.split("?")[0] == "/api/toi":   # cầu nối: danh tính theo cookie phiên; không phiên hợp lệ → 401
            cookie = dict(c.strip().split("=", 1) for c in (self.headers.get("Cookie") or "").split(";") if "=" in c)
            nguoi = self.NGUOI.get(cookie.get("authelia_session"))
            return self.tra(200, nguoi) if nguoi else self.tra(401, {})
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


class GoiNode:
    """Gọi một điểm nhận của onebee-quy-trinh.js bằng node thật (thư mục thử là self.t)."""

    def goi(self, diem, than=None, tieu_de=None):
        msg = {"payload": than if than is not None else {}, "req": {"headers": {k.lower(): v for k, v in (tieu_de or {}).items()}}}
        ma = ("const q = require(process.argv[1]);"
              "q.xuLy(process.argv[2], JSON.parse(process.argv[3])).then(m => console.log(JSON.stringify({ma: m.statusCode, than: m.payload})));")
        r = subprocess.run(["node", "-e", ma, f"{self.t}/cau-hinh/onebee-quy-trinh.js", diem, json.dumps(msg)],
                           capture_output=True, text=True, timeout=60, env=dict(os.environ, ONEBEE_CAU_HINH=f"{self.t}/cau-hinh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout.strip().splitlines()[-1])
        return kq["ma"], kq["than"]


@unittest.skipUnless(shutil.which("node"), "cần node")
class MoDunNode(GoiNode, unittest.TestCase):
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


def bam(chu):
    return hashlib.sha256(chu.encode()).hexdigest()


def tao_cert(thu_muc, ten, bit):
    """Chứng chỉ tự ký RSA `bit` bit bằng openssl; trả (PEM, sha256 hex của SPKI DER, sha256 hex của cert DER)."""
    khoa, cert = f"{thu_muc}/{ten}.key", f"{thu_muc}/{ten}.crt"
    subprocess.run(["openssl", "req", "-x509", "-newkey", f"rsa:{bit}", "-nodes", "-keyout", khoa, "-out", cert, "-subj", f"/CN={ten}",
                    "-days", "2"], check=True, capture_output=True)
    pub = subprocess.run(["openssl", "pkey", "-in", khoa, "-pubout", "-outform", "DER"], check=True, capture_output=True).stdout
    der = subprocess.run(["openssl", "x509", "-in", cert, "-outform", "DER"], check=True, capture_output=True).stdout
    return open(cert).read(), hashlib.sha256(pub).hexdigest(), hashlib.sha256(der).hexdigest()


@unittest.skipUnless(shutil.which("node") and shutil.which("openssl"), "cần node và openssl")
class MayXinVao(GoiNode, unittest.TestCase):
    """Giao thức xin vào 3 bước + hai điểm duyệt; tính lại cam_ket và ma_so trong Python đúng công thức của hợp đồng."""
    # Yêu cầu hợp lệ từ trang Sổ điều hành: JSON + cùng gốc (hai điểm duyệt từ chối mọi yêu cầu không có hai dấu hiệu này)
    AN_TOAN = {"Content-Type": "application/json", "Sec-Fetch-Site": "same-origin"}
    PHIEN_QL = {"Cookie": "khac=1; authelia_session=phien-binh", **AN_TOAN}

    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.mkdtemp()
        cls.api = ThreadingHTTPServer(("127.0.0.1", 0), ApiGia)
        threading.Thread(target=cls.api.serve_forever, daemon=True).start()
        for d in ("cau-hinh", "may-da-cap", "tinh-trang-may", "xin-vao", "phong-ban"):
            os.makedirs(f"{cls.t}/{d}")
        open(f"{cls.t}/may-da-cap/ketoan-01", "w").write("ke-toan\n")
        cls.cert, cls.khoa_bam, _ = tao_cert(cls.t, "may", 3072)
        cls.cert2048 = tao_cert(cls.t, "yeu", 2048)[0]
        ca_pem, _, cls.ca_van_tay = tao_cert(cls.t, "ca", 2048)
        open(f"{cls.t}/cau-hinh/ca.crt", "w").write(ca_pem)
        ch = json.loads(ve("cau-hinh.json.j2"))
        ch.update(may_da_cap=f"{cls.t}/may-da-cap", tinh_trang=f"{cls.t}/tinh-trang-may", xin_vao=f"{cls.t}/xin-vao",
                  phong_ban=f"{cls.t}/phong-ban", ca=f"{cls.t}/cau-hinh/ca.crt", api_goc=f"http://127.0.0.1:{cls.api.server_port}")
        json.dump(ch, open(f"{cls.t}/cau-hinh/cau-hinh.json", "w"))
        shutil.copy(os.path.join(ROLE, "files/onebee-quy-trinh.js"), f"{cls.t}/cau-hinh/")

    @classmethod
    def tearDownClass(cls):
        cls.api.shutdown()
        shutil.rmtree(cls.t)

    def setUp(self):
        for thu_muc in ("xin-vao", "phong-ban"):
            for f in os.listdir(f"{self.t}/{thu_muc}"):
                os.remove(f"{self.t}/{thu_muc}/{f}")
        self.phong("ke-toan", "Phòng Kế toán", ["gnucash"])
        self.phong("kho", "Phòng Kho", [])

    def phong(self, ma, ten, phan_mem):
        json.dump({"ma": ma, "ten": ten, "phan_mem": phan_mem}, open(f"{self.t}/phong-ban/{ma}.json", "w"), ensure_ascii=False)

    def doc(self, id_, duoi="json"):
        return json.load(open(f"{self.t}/xin-vao/{id_}.{duoi}"))

    def tep(self, id_):
        return sorted(f for f in os.listdir(f"{self.t}/xin-vao") if f.startswith(id_ + "."))

    def xin(self, ten="kt-01", phong="ke-toan", cert=None, **them):
        ma, kq = self.goi("xin-vao", {"ten": ten, "phong": phong, "hostname": "kt01-pc", "cert": cert or self.cert, **them},
                          {"X-Forwarded-For": "192.168.1.55"})
        return ma, kq

    def mo(self, id_, nw="ab" * 16):
        return self.goi("xin-vao-mo", {"id": id_, "n_w": nw})

    def ds(self, cookie=None):
        return self.goi("may-xin-vao", None, cookie or self.PHIEN_QL)

    def ma_cua(self, id_):
        try:
            return self.doc(id_).get("ma_so") or ""
        except FileNotFoundError:
            return ""

    def duyet(self, id_, cookie=None, **than):
        than.setdefault("ma_so", self.ma_cua(id_))   # người duyệt gõ đúng mã đang hiện trên máy trạm
        return self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "ke-toan", **than}, cookie or self.PHIEN_QL)

    def test_luong_ba_buoc_cam_ket_va_ma_so_khop_cong_thuc(self):
        ma, kq = self.xin()
        self.assertEqual(ma, 200, kq)
        id_ = kq["id"]
        self.assertRegex(id_, r"^[0-9a-f]{32}$")
        self.assertEqual(kq["ca_van_tay"], self.ca_van_tay)
        yc = self.doc(id_)
        self.assertEqual((yc["ten"], yc["phong_xin"], yc["hostname"], yc["ip"], yc["n_w"], yc["ma_so"]),
                         ("kt-01", "ke-toan", "kt01-pc", "192.168.1.55", None, None))
        self.assertEqual((yc["khoa_bam"], yc["ca_van_tay"]), (self.khoa_bam, self.ca_van_tay))
        self.assertTrue(yc["cert"].startswith("-----BEGIN CERTIFICATE-----"))
        self.assertIsInstance(yc["luc"], int)
        self.assertEqual(os.stat(f"{self.t}/xin-vao/{id_}.json").st_mode & 0o777, 0o600)
        # cam kết: công thức của hợp đồng, tính lại độc lập
        self.assertRegex(yc["n_b"], r"^[0-9a-f]{32}$")
        cam_ket = bam(f"onebee-xin-vao-v1|cam-ket|{id_}|{self.khoa_bam}|{self.ca_van_tay}|{yc['n_b']}")
        self.assertEqual(kq["cam_ket"], cam_ket)
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": id_}), (200, {"trang_thai": "CHO_DUYET"}))
        ma, kq = self.ds()
        self.assertEqual(ma, 200, kq)
        self.assertEqual([(y["ten"], y["trang_thai"], y["ma_so"], y["ip"], y["phong_xin"], y["hostname"]) for y in kq["yeu_cau"]],
                         [("kt-01", "CHO_MA", None, "192.168.1.55", "ke-toan", "kt01-pc")])
        self.assertEqual(kq["phong_ban"], [{"ma": "ke-toan", "ten": "Phòng Kế toán"}, {"ma": "kho", "ten": "Phòng Kho"}])
        self.assertNotIn("n_b", json.dumps(kq))   # bí mật cam kết và chứng chỉ không ra giao diện
        self.assertEqual(self.duyet(id_)[0], 409)  # chưa có mã đối chiếu thì chưa duyệt được
        # bước 3
        nw = "0123456789abcdef" * 2
        ma, kq = self.mo(id_, nw)
        self.assertEqual((ma, kq), (200, {"n_b": yc["n_b"]}))
        h = bam(f"onebee-xin-vao-v1|ma-so|{id_}|{self.khoa_bam}|{self.ca_van_tay}|{nw}|{yc['n_b']}")
        ma_so = "%06d" % (int(h[:8], 16) % 1000000)
        yc2 = self.doc(id_)
        self.assertEqual((yc2["n_w"], yc2["ma_so"]), (nw, ma_so))
        self.assertEqual(self.mo(id_, "cd" * 16)[0], 409)   # chỉ mở được một lần
        self.assertEqual(self.doc(id_)["n_w"], nw)
        ma, kq = self.ds()
        self.assertEqual((kq["yeu_cau"][0]["trang_thai"], kq["yeu_cau"][0]["ma_so"]), ("CHO_DUYET", ma_so))
        # duyệt: người duyệt lấy từ /api/toi, không từ thân yêu cầu
        ma, kq = self.duyet(id_, nguoi_duyet="gia")
        self.assertEqual((ma, kq["trang_thai"]), (200, "DANG_CAP"), kq)
        d = self.doc(id_, "duyet.json")
        self.assertEqual((d["id"], d["phong"], d["nguoi_duyet"]), (id_, "ke-toan", "binh"))
        self.assertIsInstance(d["luc"], int)
        self.assertEqual(self.ds()[1]["yeu_cau"][0]["trang_thai"], "DANG_CAP")
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": id_}), (200, {"trang_thai": "DANG_CAP"}))
        self.assertEqual(self.duyet(id_)[0], 409)          # đã quyết rồi
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "TU_CHOI", "ly_do": "x"}, self.PHIEN_QL)[0], 409)
        # root cấp xong: ghi ket-qua; Node-RED trả DA_CAP được nhiều lần (máy mất kết nối giữa chừng vẫn hỏi lại được), tệp giữ tới khi root dọn
        open(f"{self.t}/xin-vao/{id_}.ket-qua", "w").write(json.dumps({"trang_thai": "DA_CAP", "cms": "QUJD"}))
        self.assertEqual(self.ds()[1]["yeu_cau"][0]["trang_thai"], "DA_CAP")
        for _ in range(3):
            self.assertEqual(self.goi("xin-vao-ket-qua", {"id": id_}), (200, {"trang_thai": "DA_CAP", "cms": "QUJD"}))
        self.assertEqual(self.tep(id_), sorted(f"{id_}.{d}" for d in ("json", "duyet.json", "ket-qua")))

    def test_ket_qua_loi_giu_tep_va_bao_ly_do(self):
        id_ = self.xin()[1]["id"]
        open(f"{self.t}/xin-vao/{id_}.ket-qua", "w").write(json.dumps({"trang_thai": "LOI", "loi": "không mã hóa được"}))
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": id_}), (200, {"trang_thai": "LOI", "loi": "không mã hóa được"}))
        y = self.ds()[1]["yeu_cau"][0]
        self.assertEqual((y["trang_thai"], y["loi"]), ("LOI", "không mã hóa được"))
        self.assertIn(f"{id_}.json", self.tep(id_))        # root dọn sau 24 giờ; LOI không bị xóa ngay
        ma, _ = self.xin()                                # LOI không còn là "đang chờ": máy xin lại được
        self.assertEqual(ma, 200)

    def test_tu_choi_tra_ly_do_roi_xoa_tep(self):
        id_ = self.xin()[1]["id"]
        self.mo(id_)
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "TU_CHOI", "ly_do": "  "}, self.PHIEN_QL)[0], 400)
        ma, kq = self.goi("duyet-may", {"id": id_, "quyet_dinh": "TU_CHOI", "ly_do": "Mã\nkhông khớp"}, self.PHIEN_QL)
        self.assertEqual((ma, kq["trang_thai"]), (200, "TU_CHOI"))
        tc = self.doc(id_, "tu-choi.json")
        self.assertEqual((tc["id"], tc["nguoi_duyet"], tc["ly_do"]), (id_, "binh", "Mã không khớp"))
        self.assertEqual(self.ds()[1]["yeu_cau"][0]["trang_thai"], "TU_CHOI")
        self.assertEqual(self.xin()[0], 200)               # bị từ chối không chặn máy xin lại
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": id_}), (200, {"trang_thai": "TU_CHOI", "ly_do": "Mã không khớp"}))
        self.assertEqual(self.tep(id_), [])

    def test_xin_vao_bi_tu_choi(self):
        def loi(ma_mong, **kw):
            ma, kq = self.xin(**kw)
            self.assertEqual(ma, ma_mong, kq)
            self.assertFalse(kq["ok"])
            return kq["loi"]
        for ten in ("", "../etc", "A_B", "-x", "x" * 33, None):
            loi(400, ten=ten)
        loi(409, ten="ketoan-01")                         # máy đã cấp
        loi(400, cert=self.cert2048)                      # RSA 2048
        loi(400, cert="không phải PEM")                   # cert rác
        loi(400, cert="-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n")
        loi(400, cert=" ")
        self.assertEqual(self.goi("xin-vao", {"ten": "kt-01"})[0], 400)   # thiếu cert
        loi(413, cert=self.cert + "x" * 9000)             # quá 8 KB
        loi(400, phong="khong-co")                        # phòng không có trên Box
        loi(400, phong="Ke Toan")                         # sai dạng mã phòng
        self.assertEqual(self.goi("xin-vao", None)[0], 400)
        self.assertEqual(os.listdir(f"{self.t}/xin-vao"), [])   # bị từ chối thì không để lại tệp nào
        self.assertEqual(self.xin(ten="kt-01")[0], 200)
        ma, kq = self.goi("xin-vao", {"ten": "kt-01", "cert": self.cert}, {"X-Forwarded-For": "192.168.1.99"})
        self.assertEqual(ma, 409, kq)                     # cùng tên từ máy khác: không được giành chỗ
        self.assertEqual(self.xin(ten="may-khong-phong", phong="")[0], 200)   # phòng là tùy chọn

    def test_may_bo_do_xin_lai_cung_ten_cung_dia_chi_thay_yeu_cau_cu(self):
        _, cu = self.xin()
        self.mo(cu["id"])                                 # đã hiện mã rồi bấm Ctrl+C
        ma, moi = self.xin()
        self.assertEqual(ma, 200, moi)
        self.assertEqual(self.tep(cu["id"]), [])          # yêu cầu cũ (và mã cũ) bỏ hẳn
        self.assertEqual([y["id"] for y in self.ds()[1]["yeu_cau"]], [moi["id"]])
        self.mo(moi["id"])
        self.assertEqual(self.duyet(moi["id"])[0], 200)   # đang cấp thì không thay được nữa
        self.assertEqual(self.xin()[0], 409)

    def test_phong_null_rong_hoac_thieu_deu_luu_thanh_chuoi_rong(self):
        ma, kq = self.xin(ten="np-null", phong=None)                 # máy trạm gửi "phong": null khi không chọn phòng
        self.assertEqual(ma, 200, kq)
        ma2, kq2 = self.xin(ten="np-rong", phong="")
        ma3, kq3 = self.goi("xin-vao", {"ten": "np-thieu", "cert": self.cert})   # không có trường phong
        self.assertEqual((ma2, ma3), (200, 200), (kq2, kq3))
        for k in (kq, kq2, kq3):
            self.assertEqual(self.doc(k["id"])["phong_xin"], "")
        self.assertEqual({y["phong_xin"] for y in self.ds()[1]["yeu_cau"]}, {""})
        # máy không xin phòng vẫn được duyệt vào phòng người duyệt chọn
        self.mo(kq["id"])
        self.assertEqual(self.duyet(kq["id"], phong="kho")[0], 200)

    def test_duyet_phai_nhap_dung_ma_6_so(self):
        id_ = self.xin()[1]["id"]
        self.mo(id_)
        ma = self.ma_cua(id_)
        sai = "%06d" % ((int(ma) + 1) % 1000000)
        for v in (sai, "", None, "12345", ma + "0", "abcdef", " ".join(ma)):
            ma_loi, kq = self.duyet(id_, ma_so=v)
            self.assertEqual((ma_loi, kq["loi"]), (409, "Mã không khớp — KHÔNG duyệt"), v)
        ma_loi, kq = self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho"}, self.PHIEN_QL)   # thiếu hẳn trường ma_so
        self.assertEqual((ma_loi, kq["loi"]), (409, "Mã không khớp — KHÔNG duyệt"))
        self.assertEqual(self.tep(id_), [f"{id_}.json"])             # mã sai thì không ghi gì, yêu cầu vẫn chờ duyệt
        self.assertEqual(self.ds()[1]["yeu_cau"][0]["trang_thai"], "CHO_DUYET")
        self.assertEqual(self.duyet(id_, ma_so=f" {ma} ")[0], 200)   # mã đúng (thừa dấu cách hai đầu) thì duyệt
        # từ chối không cần mã
        id2 = self.xin(ten="kt-02")[1]["id"]
        self.mo(id2)
        self.assertEqual(self.goi("duyet-may", {"id": id2, "quyet_dinh": "TU_CHOI", "ly_do": "lạ"}, self.PHIEN_QL)[0], 200)

    def test_chong_csrf_hai_diem_duyet(self):
        ids = [self.xin(ten=f"cs-{i}")[1]["id"] for i in range(3)]
        for i in ids:
            self.mo(i)
        goc = f"http://127.0.0.1:{self.api.server_port}"
        cookie = {"Cookie": "authelia_session=phien-binh"}
        json_ct = {"Content-Type": "application/json"}

        def ghi(id_, tieu_de, **them):
            return self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho", "ma_so": self.ma_cua(id_), **them}, tieu_de)
        # GHI bị từ chối: sai kiểu nội dung, hoặc không chứng minh được cùng gốc
        for tieu_de in ({**cookie, "Sec-Fetch-Site": "same-origin"},                                   # không Content-Type
                        {**cookie, "Content-Type": "text/plain", "Sec-Fetch-Site": "same-origin"},
                        {**cookie, "Content-Type": "application/x-www-form-urlencoded", "Sec-Fetch-Site": "same-origin"},
                        {**cookie, "Content-Type": "application/jsonx", "Sec-Fetch-Site": "same-origin"},
                        {**cookie, **json_ct},                                                         # không Origin, không Sec-Fetch-Site
                        {**cookie, **json_ct, "Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
                        {**cookie, **json_ct, "Origin": "https://evil.example"},
                        {**cookie, **json_ct, "Origin": "null"},
                        {**cookie, **json_ct, "Sec-Fetch-Site": "same-site"},
                        {**cookie, **json_ct, "Sec-Fetch-Site": "cross-site"}):
            ma, kq = ghi(ids[0], tieu_de)
            self.assertEqual(ma, 403, tieu_de)
            self.assertFalse(kq["ok"])
        self.assertEqual(self.goi("duyet-may", {"id": ids[0], "quyet_dinh": "TU_CHOI", "ly_do": "x"}, {**cookie, "Content-Type": "text/plain"})[0], 403)
        self.assertEqual(self.tep(ids[0]), [f"{ids[0]}.json"])      # bị chặn thì không ghi quyết định nào
        # GHI hợp lệ: Origin đúng gốc Box, hoặc Sec-Fetch-Site same-origin (có tham số charset)
        self.assertEqual(ghi(ids[0], {**cookie, **json_ct, "Origin": goc})[0], 200)
        self.assertEqual(ghi(ids[1], {**cookie, "Content-Type": "Application/JSON; charset=utf-8", "Sec-Fetch-Site": "same-origin"})[0], 200)
        # ĐỌC: cross-site, same-site, none bị từ chối; same-origin hoặc vắng (trình duyệt cũ) thì được
        for site in ("cross-site", "same-site", "none", "bậy"):
            self.assertEqual(self.goi("may-xin-vao", None, {**cookie, "Sec-Fetch-Site": site})[0], 403, site)
        self.assertEqual(self.goi("may-xin-vao", None, {**cookie, "Sec-Fetch-Site": "same-origin"})[0], 200)
        self.assertEqual(self.goi("may-xin-vao", None, cookie)[0], 200)

    def _sua_luc(self, id_, giay_truoc):
        yc = self.doc(id_)
        yc["luc"] -= giay_truoc
        json.dump(yc, open(f"{self.t}/xin-vao/{id_}.json", "w"))

    def test_cho_ma_qua_10_phut_het_han(self):
        a, b, c, d, e, f = (self.xin(ten=f"hh-{x}")[1]["id"] for x in "abcdef")
        self.mo(c)                                    # c đã gửi n_w: không hết hạn dù cũ
        for id_, giay in ((a, 700), (b, 700), (c, 3000), (d, 700), (e, 500), (f, 700)):
            self._sua_luc(id_, giay)
        # b: xin-vao-mo trả 410 và xóa
        ma, kq = self.mo(b)
        self.assertEqual(ma, 410, kq)
        self.assertEqual(self.tep(b), [])
        # d: duyệt hay từ chối đều 410
        self.assertEqual(self.duyet(d)[0], 410)
        self.assertEqual(self.tep(d), [])
        self.assertEqual(self.goi("duyet-may", {"id": f, "quyet_dinh": "TU_CHOI", "ly_do": "x"}, self.PHIEN_QL)[0], 410)
        self.assertEqual(self.tep(f), [])
        # a: máy hỏi kết quả của yêu cầu hết hạn → KHONG_CO và dọn
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": a}), (200, {"trang_thai": "KHONG_CO"}))
        self.assertEqual(self.tep(a), [])
        # còn lại: c (đã mở) và e (CHO_MA nhưng mới 500 giây)
        self.assertEqual(sorted((y["ten"], y["trang_thai"]) for y in self.ds()[1]["yeu_cau"]), [("hh-c", "CHO_DUYET"), ("hh-e", "CHO_MA")])

    def test_yeu_cau_het_han_duoc_don_khi_quet_va_khong_tinh_gioi_han(self):
        for i in range(20):
            self.assertEqual(self.xin(ten=f"hq-{i:02d}")[0], 200)
        cu = next(f[:-5] for f in sorted(os.listdir(f"{self.t}/xin-vao")) if f.endswith(".json"))
        self._sua_luc(cu, 601)
        self.assertEqual(self.xin(ten="hq-moi")[0], 200)              # chỗ trống nhờ yêu cầu hết hạn
        self.assertEqual(self.tep(cu), [])                            # xin-vao quét thì dọn luôn
        self.assertEqual(self.xin(ten="hq-hon")[0], 429)              # đủ 20 trở lại
        # hết hạn cũng không chặn đặt lại cùng tên
        cu2 = next(f[:-5] for f in sorted(os.listdir(f"{self.t}/xin-vao")) if f.endswith(".json"))
        ten2 = self.doc(cu2)["ten"]
        self._sua_luc(cu2, 601)
        self.assertEqual(self.xin(ten=ten2)[0], 200)

    def test_toi_da_20_yeu_cau_cho(self):
        for i in range(20):
            self.assertEqual(self.xin(ten=f"may-{i:02d}")[0], 200, i)
        ma, kq = self.xin(ten="may-20")
        self.assertEqual(ma, 429, kq)
        # Chỉ tệp yêu cầu <id>.json (id 32 hex) — không lẫn <id>.tu-choi.json / <id>.duyet.json (id ngẫu nhiên, lẫn là lỗi lúc có lúc không)
        yeu_cau = lambda: sorted(f[:-5] for f in os.listdir(f"{self.t}/xin-vao") if re.fullmatch(r"[0-9a-f]{32}\.json", f))
        self.assertEqual(len(yeu_cau()), 20)
        # một yêu cầu được xử lý xong thì còn chỗ
        id_ = yeu_cau()[0]
        open(f"{self.t}/xin-vao/{id_}.tu-choi.json", "w").write("{}")
        self.assertEqual(self.xin(ten="may-20")[0], 200)
        # đã cấp xong (DA_CAP) cũng không còn tính vào số yêu cầu chờ, dù tệp được giữ để máy hỏi lại
        id2 = next(i for i in yeu_cau() if i != id_ and not os.path.exists(f"{self.t}/xin-vao/{i}.tu-choi.json"))
        open(f"{self.t}/xin-vao/{id2}.ket-qua", "w").write(json.dumps({"trang_thai": "DA_CAP", "cms": "QUJD"}))
        self.assertEqual(self.xin(ten="may-21")[0], 200)

    def test_khong_co_ca_tra_503_va_ip_xau_de_trong(self):
        ma, kq = self.xin()
        self.assertEqual(ma, 200)
        for i, (xff, mong) in enumerate((("192.168.1.55", "192.168.1.55"), ("1.2.3.4, 10.0.0.9", "10.0.0.9"), ("::ffff:10.1.1.1", "10.1.1.1"),
                          ("999.1.1.1", ""), ("<script>", ""), ("fe80::1", ""))):
            ma, kq = self.goi("xin-vao", {"ten": f"ip-{i}", "cert": self.cert}, {"X-Forwarded-For": xff})
            self.assertEqual(ma, 200, kq)
            self.assertEqual(self.doc(kq["id"])["ip"], mong, xff)
        t2 = tempfile.mkdtemp()
        try:
            shutil.copytree(f"{self.t}/cau-hinh", f"{t2}/cau-hinh")
            ch = json.load(open(f"{t2}/cau-hinh/cau-hinh.json"))
            ch["ca"] = f"{t2}/khong-co.crt"
            json.dump(ch, open(f"{t2}/cau-hinh/cau-hinh.json", "w"))
            saved, self.t = self.t, t2
            try:
                ma, kq = self.goi("xin-vao", {"ten": "kt-99", "cert": self.cert})
            finally:
                self.t = saved
            self.assertEqual(ma, 503)
            self.assertIn("CA", kq["loi"])
        finally:
            shutil.rmtree(t2)

    def test_xin_vao_mo_va_ket_qua_kiem_dau_vao(self):
        id_ = self.xin()[1]["id"]
        for than in ({"id": "x"}, {"id": id_}, {"id": id_, "n_w": "zz"}, {"id": id_, "n_w": "ab" * 8}, {"id": "../" + id_, "n_w": "ab" * 16}):
            self.assertEqual(self.goi("xin-vao-mo", than)[0], 400, than)
        self.assertEqual(self.goi("xin-vao-mo", {"id": "0" * 32, "n_w": "ab" * 16})[0], 404)
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": "../../etc/passwd"})[0], 400)
        self.assertEqual(self.goi("xin-vao-ket-qua", {"id": "0" * 32}), (200, {"trang_thai": "KHONG_CO"}))
        self.assertIsNone(self.doc(id_)["n_w"])

    def test_hai_diem_duyet_chi_tin_api_toi(self):
        id_ = self.xin()[1]["id"]
        self.mo(id_)
        gia = {"Remote-User": "binh", "Remote-Groups": "quan_ly", **self.AN_TOAN}
        # không cookie: Remote-* không có tác dụng
        self.assertEqual(self.goi("may-xin-vao", None, gia)[0], 401)
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho"}, gia)[0], 401)
        # cookie không phải phiên hợp lệ: cầu nối trả 401 → 401, dù giả Remote-*
        la = {**gia, "Cookie": "authelia_session=phien-la"}
        self.assertEqual(self.goi("may-xin-vao", None, la)[0], 401)
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho"}, la)[0], 401)
        # phiên của nhân viên thường: sai vai trò → 403 dù giả Remote-Groups quan_ly
        nv = {**gia, "Cookie": "authelia_session=phien-an"}
        self.assertEqual(self.goi("may-xin-vao", None, nv)[0], 403)
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho"}, nv)[0], 403)
        self.assertEqual(self.goi("duyet-may", {"id": id_, "quyet_dinh": "TU_CHOI", "ly_do": "x"}, nv)[0], 403)
        self.assertEqual(self.tep(id_), [f"{id_}.json"])   # chưa ghi quyết định nào
        # kỹ thuật cũng được duyệt, tên người duyệt là tên /api/toi trả về
        ma, kq = self.goi("duyet-may", {"id": id_, "quyet_dinh": "DUYET", "phong": "kho", "ma_so": self.ma_cua(id_)}, {"Cookie": "authelia_session=phien-thuy", **self.AN_TOAN})
        self.assertEqual((ma, kq["trang_thai"]), (200, "DANG_CAP"), kq)
        d = self.doc(id_, "duyet.json")
        self.assertEqual((d["phong"], d["nguoi_duyet"]), ("kho", "thuy"))

    def test_duyet_may_kiem_dau_vao(self):
        id_ = self.xin()[1]["id"]
        self.assertEqual(self.duyet(id_)[0], 409)                          # chưa có mã
        self.mo(id_)
        for than in ({"id": id_}, {"id": id_, "quyet_dinh": "XOA"}, {"id": id_, "quyet_dinh": "DUYET"},
                     {"id": id_, "quyet_dinh": "DUYET", "phong": "khong-co"}, {"id": id_, "quyet_dinh": "DUYET", "phong": "../x"},
                     {"id": id_, "quyet_dinh": "TU_CHOI"}, {"id": "bậy", "quyet_dinh": "DUYET", "phong": "kho"}):
            self.assertEqual(self.goi("duyet-may", than, self.PHIEN_QL)[0], 400, than)
        self.assertEqual(self.goi("duyet-may", {"id": "1" * 32, "quyet_dinh": "DUYET", "phong": "kho"}, self.PHIEN_QL)[0], 404)
        self.assertEqual(self.tep(id_), [f"{id_}.json"])
        self.assertEqual(self.duyet(id_)[0], 200)

    def test_phong_ban_hong_bi_bo_qua(self):
        open(f"{self.t}/phong-ban/hong.json", "w").write("{khong phai json")
        self.phong("sai-ma", "Tên", [])                                       # ma trong tệp khác tên tệp
        os.rename(f"{self.t}/phong-ban/sai-ma.json", f"{self.t}/phong-ban/khac.json")
        self.phong("tendai", "x" * 61, [])
        self.phong("co-nhay", 'Có "nháy"', [])
        os.makedirs(f"{self.t}/phong-ban/may", exist_ok=True)
        try:
            self.assertEqual([p["ma"] for p in self.ds()[1]["phong_ban"]], ["ke-toan", "kho"])
        finally:
            os.rmdir(f"{self.t}/phong-ban/may")


if __name__ == "__main__":
    unittest.main()
