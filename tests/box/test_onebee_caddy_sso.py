#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử tuyến đăng nhập một lần + cổng API trong Caddyfile HTTPS của Box bằng Caddy THẬT (ONEBEE_TEST_CADDY hoặc caddy trong PATH;
không có thì bỏ qua). Phía sau là máy chủ HTTP giả: Authelia giả (forward-auth theo cookie + luật nhóm như cấu hình thật),
Ollama, Uptime Kuma, PostgREST giả; cầu nối danh tính là mã THẬT (box-dinh-danh/files/onebee-cau-noi-danh-tinh.py).
Kiểm: chưa phiên → 401; có phiên → 200; tiêu đề Remote-*/Authorization do máy khách gửi không có tác dụng; /ai/ chỉ mở 2 đường dẫn POST;
/files/ → 503; trang chủ công khai; vào bằng IP chỉ có trang chủ; giám sát chỉ cho kỹ thuật hai lớp; SSO tạm tắt thì tuyến lõi 503.
Chạy: python3 -m unittest"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
TEMPLATE = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/Caddyfile.j2")
TAO_CA = os.path.join(ROOT, "box/ansible/roles/box-stack/files/onebee-ca.sh")
CAU_NOI = os.path.join(ROOT, "box/ansible/roles/box-dinh-danh/files/onebee-cau-noi-danh-tinh.py")
CADDY = os.environ.get("ONEBEE_TEST_CADDY") or shutil.which("caddy")
TEN = "box.anphu.onebee.internal"
# Phiên giả: cookie → (tên, nhóm, số lớp đã qua)
PHIEN = {"phien-an": ("an", "nhan_vien", 1), "phien-ql": ("binh", "quan_ly", 2), "phien-kt1": ("kythuat", "ky_thuat", 1),
         "phien-kt2": ("kythuat", "ky_thuat", 2)}


def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def may_chu(xu_ly):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def tra(self, ma, than=b"", tieu_de=()):
            self.send_response(ma)
            for k, v in tieu_de:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(than)))
            self.end_headers()
            self.wfile.write(than)

        def xong(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            xu_ly(self)
        do_GET = do_POST = do_DELETE = do_PUT = xong
    sv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    sv.daemon_threads = True
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    return sv


class Ghi:
    def __init__(self):
        self.ds = []


AUTHELIA_THAY, PHIA_SAU_THAY, OLLAMA_THAY, KUMA_THAY = Ghi(), Ghi(), Ghi(), Ghi()


def authelia(h):
    if h.path.startswith("/dangnhap"):
        return h.tra(200, b"trang-dang-nhap")
    if h.path.split("?")[0] != "/api/authz/forward-auth":   # Caddy giữ chuỗi truy vấn gốc khi đổi uri
        return h.tra(404)
    uri = h.headers.get("X-Forwarded-Uri", "")
    AUTHELIA_THAY.ds.append({"uri": uri, "method": h.headers.get("X-Forwarded-Method"), "host": h.headers.get("X-Forwarded-Host"),
                             "authorization": h.headers.get("Authorization"), "remote_user": h.headers.get("Remote-User")})
    cookie = dict(c.strip().split("=", 1) for c in (h.headers.get("Cookie") or "").split(";") if "=" in c)
    phien = PHIEN.get(cookie.get("authelia_session"))
    if (h.headers.get("X-Forwarded-Host") or "").rsplit(":", 1)[0] != TEN or not phien:   # máy thử dùng cổng khác 443
        return h.tra(401)
    ten, nhom, lop = phien
    if uri.startswith("/giam-sat"):
        ok = nhom == "ky_thuat" and lop == 2
    elif uri.startswith(("/api/", "/files/", "/ai/")):
        ok = nhom == "nhan_vien" or lop == 2
        if not ok:
            return h.tra(401)
    else:
        ok = False
    if not ok:
        return h.tra(403)
    h.tra(200, tieu_de=(("Remote-User", ten), ("Remote-Groups", nhom), ("Remote-Email", f"{ten}@anphu.onebee.internal"),
                        ("Remote-Name", ten)))


def ghi_va_tra(noi, ten):
    def f(h):
        noi.ds.append({"method": h.command, "path": h.path, "headers": dict(h.headers)})
        h.tra(200, json.dumps({"dich_vu": ten, "path": h.path}).encode(), (("Content-Type", "application/json"),))
    return f


def curl(*a):
    r = subprocess.run(["curl", "-sS", "--noproxy", "*", "-m", "15", "-o", "-", "-w", "\n%{http_code} %{redirect_url}", *a],
                       capture_output=True, text=True)
    than, _, cuoi = r.stdout.rpartition("\n")
    ma, _, chuyen = cuoi.partition(" ")
    return ma, than, chuyen, r


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddySso(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name
        subprocess.run([TAO_CA, f"{t}/ca", "anphu", "127.0.0.1"], check=True, capture_output=True,
                       env={**os.environ, "ONEBEE_PKI_OUT": f"{t}/pki"})
        os.makedirs(f"{t}/srv"), os.makedirs(f"{t}/srv-http")
        open(f"{t}/srv/index.html", "w").write("OneBee Box trang chu")
        open(f"{t}/srv/trang-thai.json", "w").write("{}")
        open(f"{t}/srv-http/index.html", "w").write("huong dan cai CA")
        cls.cong = {k: cong_trong() for k in ("portal", "open_webui", "n8n", "rest_server", "uptime_kuma", "http")}
        cls.sv = {"authelia": may_chu(authelia), "postgrest": may_chu(ghi_va_tra(PHIA_SAU_THAY, "postgrest")),
                  "ollama": may_chu(ghi_va_tra(OLLAMA_THAY, "ollama")), "uptime-kuma": may_chu(ghi_va_tra(KUMA_THAY, "kuma")),
                  "khac": may_chu(ghi_va_tra(Ghi(), "khac"))}
        with open(f"{t}/khoa", "w") as f:
            f.write("ab" * 32 + "\n")
        cls.cong_cau_noi = cong_trong()
        cls.cau_noi = subprocess.Popen([sys.executable, "-I", CAU_NOI], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       env={"PATH": os.environ.get("PATH", ""), "CAU_NOI_CONG": str(cls.cong_cau_noi),
                                            "CAU_NOI_DIA_CHI": "127.0.0.1", "CAU_NOI_JWT_SECRET_FILE": f"{t}/khoa",
                                            "CAU_NOI_PHIA_SAU": f"http://127.0.0.1:{cls.sv['postgrest'].server_port}"})
        cls.caddy = None

    @classmethod
    def tearDownClass(cls):
        if cls.caddy:
            cls.caddy.terminate()
            cls.caddy.wait(10)
        cls.cau_noi.terminate()
        cls.cau_noi.wait(10)
        cls.tmp.cleanup()

    @classmethod
    def dung_caddy(cls, sso=True, authelia_chet=False):
        """Render Caddyfile như Ansible (HTTPS bật) rồi đổi cổng/đường dẫn/dịch vụ phía sau sang cổng thử trên máy này."""
        t, c = cls.t, cls.cong
        v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
        v.update(onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_kuma_dia_chi="0.0.0.0",
                 onebee_sso_hieu_luc=sso,
                 onebee_box_ports={"portal": 80, "open_webui": c["open_webui"], "n8n": c["n8n"], "rest_server": c["rest_server"],
                                   "uptime_kuma": c["uptime_kuma"]})
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
        env.filters["bool"] = bool
        nd = env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v)
        cls.nd_goc = nd
        nd = nd.replace(":443", f":{c['portal']}").replace("\n:80 {", f"\n:{c['http']} {{")
        nd = nd.replace("/srv-http", f"{t}/srv-http").replace("root * /srv\n", f"root * {t}/srv\n").replace("/pki/", f"{t}/pki/")
        p = {k: s.server_port for k, s in cls.sv.items()}
        for goc, moi in (("authelia:9091", cong_trong() if authelia_chet else p["authelia"]), ("cau-noi:8080", cls.cong_cau_noi), ("ollama:11434", p["ollama"]),
                         ("uptime-kuma:3001", p["uptime-kuma"]), ("open-webui:8080", p["khac"]), ("n8n:5678", p["khac"]),
                         ("rest-server:8000", p["khac"])):
            nd = nd.replace(goc, f"127.0.0.1:{moi}")
        open(f"{t}/Caddyfile", "w").write(nd)
        if cls.caddy:
            cls.caddy.terminate()
            cls.caddy.wait(10)
        env_c = {**os.environ, "XDG_DATA_HOME": f"{t}/data", "XDG_CONFIG_HOME": f"{t}/cfg"}
        r = subprocess.run([CADDY, "validate", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], capture_output=True, text=True,
                           env=env_c)
        assert r.returncode == 0, r.stderr[-3000:]
        cls.caddy = subprocess.Popen([CADDY, "run", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], env=env_c,
                                     stdout=subprocess.DEVNULL, stderr=open(f"{t}/caddy.log", "w"))
        for _ in range(100):
            time.sleep(0.2)
            if cls.ten("/")[0] == "200" and curl("--cacert", f"{t}/ca/root.crt", f"https://127.0.0.1:{c['portal']}/")[0] == "200":
                return
        raise AssertionError("Caddy không lên: " + open(f"{t}/caddy.log").read()[-3000:])

    @classmethod
    def ten(cls, duong_dan, *a, cong=None):
        cong = cong or cls.cong["portal"]
        return curl("--cacert", f"{cls.t}/ca/root.crt", "--resolve", f"{TEN}:{cong}:127.0.0.1", *a, f"https://{TEN}:{cong}{duong_dan}")

    def setUp(self):
        if not self.caddy or getattr(self, "_sso", True) is not True:
            type(self).dung_caddy(sso=True)
            type(self)._sso = True
        for g in (AUTHELIA_THAY, PHIA_SAU_THAY, OLLAMA_THAY, KUMA_THAY):
            g.ds.clear()

    def test_a_chua_co_phien_goi_api_toi_nhan_401(self):
        ma, _, _, r = self.ten("/api/toi", "-H", "Accept: application/json")
        self.assertEqual(ma, "401", r.stderr)
        self.assertEqual(AUTHELIA_THAY.ds[0]["uri"], "/api/toi")   # Authelia thấy đường dẫn gốc (không bị bỏ tiền tố trước forward_auth)

    def test_b_phien_hop_le_nhan_200_tu_cau_noi(self):
        ma, than, _, _ = self.ten("/api/toi", "-b", "authelia_session=phien-an")
        self.assertEqual(ma, "200", than)
        self.assertEqual(json.loads(than), {"ten": "an", "vai_tro": "nhan_vien"})
        ma, than, _, _ = self.ten("/api/toi", "-b", "authelia_session=phien-ql")
        self.assertEqual(json.loads(than), {"ten": "binh", "vai_tro": "quan_ly"})

    def test_c_may_khach_tu_gui_remote_user_khong_co_tac_dung(self):
        gia = ("-H", "Remote-User: quanly", "-H", "Remote-Groups: quan_ly", "-H", "Accept: application/json")
        self.assertEqual(self.ten("/api/toi", *gia)[0], "401")
        self.assertIsNone(AUTHELIA_THAY.ds[0]["remote_user"])         # bị xóa trước cả forward_auth
        ma, than, _, _ = self.ten("/api/toi", "-b", "authelia_session=phien-an", *gia)
        self.assertEqual((ma, json.loads(than)), ("200", {"ten": "an", "vai_tro": "nhan_vien"}))

    def test_d_authorization_cua_may_khach_khong_toi_phia_sau(self):
        gia = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJiaW5oIn0.khoa-sai"
        self.assertEqual(self.ten("/api/ghi_chu", "-H", f"Authorization: {gia}", "-H", "Accept: application/json")[0], "401")
        self.assertIsNone(AUTHELIA_THAY.ds[0]["authorization"])
        ma, _, _, _ = self.ten("/api/ghi_chu?select=noi_dung", "-H", f"Authorization: {gia}", "-b", "authelia_session=phien-an")
        self.assertEqual(ma, "200")
        yc = PHIA_SAU_THAY.ds[0]
        self.assertEqual(yc["path"], "/ghi_chu?select=noi_dung")
        self.assertTrue(yc["headers"]["Authorization"].startswith("Bearer "))
        self.assertNotEqual(yc["headers"]["Authorization"], gia)
        self.assertNotIn("Cookie", yc["headers"])

    def test_e_ai_chi_mo_hai_duong_dan_post(self):
        for phien in ((), ("-b", "authelia_session=phien-an")):
            self.assertEqual(self.ten("/ai/api/tags", *phien)[0], "404", phien)
            self.assertEqual(self.ten("/ai/api/delete", "-X", "DELETE", *phien)[0], "404", phien)
            self.assertEqual(self.ten("/ai/api/pull", "-X", "POST", "-d", "{}", *phien)[0], "404", phien)
            self.assertEqual(self.ten("/ai/api/chat", *phien)[0], "404", phien)                # GET hỏi đáp cũng không
        self.assertEqual(OLLAMA_THAY.ds, [])
        self.assertEqual(self.ten("/ai/api/chat", "-X", "POST", "-d", "{}", "-H", "Accept: application/json")[0], "401")
        for duong in ("/ai/api/chat", "/ai/api/generate"):
            ma, than, _, _ = self.ten(duong, "-X", "POST", "-d", "{}", "-b", "authelia_session=phien-an")
            self.assertEqual(ma, "200", duong)
        self.assertEqual([y["path"] for y in OLLAMA_THAY.ds], ["/api/chat", "/api/generate"])
        self.assertNotIn("Cookie", OLLAMA_THAY.ds[0]["headers"])                                 # cookie phiên không tới Ollama

    def test_f_files_co_phien_nhan_503(self):
        self.assertEqual(self.ten("/files/x", "-b", "authelia_session=phien-an")[0], "503")
        self.assertEqual(self.ten("/files/x", "-H", "Accept: application/json")[0], "401")

    def test_g_trang_chu_khong_can_phien(self):
        ma, than, _, _ = self.ten("/")
        self.assertEqual((ma, than), ("200", "OneBee Box trang chu"))
        r = subprocess.run(["curl", "-sSI", "--noproxy", "*", "--cacert", f"{self.t}/ca/root.crt", "--resolve",
                            f"{TEN}:{self.cong['portal']}:127.0.0.1", f"https://{TEN}:{self.cong['portal']}/trang-thai.json"],
                           capture_output=True, text=True)
        self.assertIn("cache-control: no-store", r.stdout.lower())
        self.assertEqual(AUTHELIA_THAY.ds, [])

    def test_h_vao_bang_ip_chi_co_trang_chu(self):
        goc = f"https://127.0.0.1:{self.cong['portal']}"
        ma, than, _, _ = curl("--cacert", f"{self.t}/ca/root.crt", goc + "/")
        self.assertEqual((ma, than), ("200", "OneBee Box trang chu"))
        for duong in ("/api/toi", "/dangnhap/", "/files/x", "/ai/api/chat"):
            ma, _, chuyen, _ = curl("--cacert", f"{self.t}/ca/root.crt", "-b", "authelia_session=phien-an", goc + duong)
            self.assertEqual((ma, chuyen), ("308", f"https://{TEN}{duong}"), duong)
        self.assertEqual((AUTHELIA_THAY.ds, PHIA_SAU_THAY.ds), ([], []))

    def test_i_trang_dang_nhap_toi_authelia(self):
        self.assertEqual(self.ten("/dangnhap/")[:2], ("200", "trang-dang-nhap"))

    def test_j_than_qua_1mb_bi_chan(self):
        tep = f"{self.t}/lon.bin"
        with open(tep, "wb") as f:
            f.write(b"x" * (1024 * 1024 + 10))
        ma, _, _, _ = self.ten("/api/ghi_chu", "-b", "authelia_session=phien-an", "--data-binary", f"@{tep}",
                               "-H", "Content-Type: application/json")
        self.assertEqual(ma, "413")
        self.assertEqual(PHIA_SAU_THAY.ds, [])

    def test_k_giam_sat_chi_ky_thuat_hai_lop(self):
        k = self.cong["uptime_kuma"]
        self.assertEqual(self.ten("/dashboard", "-H", "Accept: application/json", cong=k)[0], "401")
        self.assertEqual(self.ten("/dashboard", "-b", "authelia_session=phien-an", cong=k)[0], "403")
        self.assertEqual(self.ten("/dashboard", "-b", "authelia_session=phien-ql", cong=k)[0], "403")
        self.assertEqual(self.ten("/dashboard", "-b", "authelia_session=phien-kt1", cong=k)[0], "403")
        self.assertEqual(KUMA_THAY.ds, [])
        for duong in ("/dashboard", "/giam-sat/dashboard"):     # Authelia trả người dùng về /giam-sat/... → bỏ tiền tố
            ma, than, _, _ = self.ten(duong, "-b", "authelia_session=phien-kt2", "-H", "Remote-User: quanly", cong=k)
            self.assertEqual(ma, "200", duong)
        self.assertEqual([y["path"] for y in KUMA_THAY.ds], ["/dashboard", "/dashboard"])
        self.assertTrue(all(a["uri"] == "/giam-sat/dashboard" for a in AUTHELIA_THAY.ds), AUTHELIA_THAY.ds)
        self.assertNotIn("quanly", json.dumps(KUMA_THAY.ds))
        ma, _, chuyen, _ = curl("--cacert", f"{self.t}/ca/root.crt", f"https://127.0.0.1:{k}/dashboard")
        self.assertEqual((ma, chuyen), ("308", f"https://{TEN}:{k}/dashboard"))

    def test_l_cac_cong_khac_giu_nguyen(self):
        for cong in (self.cong["open_webui"], self.cong["n8n"], self.cong["rest_server"]):
            ma, than, _, _ = curl("--cacert", f"{self.t}/ca/root.crt", f"https://127.0.0.1:{cong}/x")
            self.assertEqual(ma, "200", cong)
        self.assertEqual(AUTHELIA_THAY.ds, [])


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddySsoTamTat(CaddySso):
    """onebee-box tat-sso-tam: tuyến lõi trả 503 (không mở toang dữ liệu), giám sát về đăng nhập riêng của Uptime Kuma."""

    def setUp(self):
        if not self.caddy or getattr(self, "_sso", True) is not False:
            type(self).dung_caddy(sso=False)
            type(self)._sso = False
        for g in (AUTHELIA_THAY, PHIA_SAU_THAY, OLLAMA_THAY, KUMA_THAY):
            g.ds.clear()

    def test_tuyen_loi_tra_503_ca_khi_co_phien(self):
        for duong, them in (("/api/toi", ()), ("/files/x", ()), ("/ai/api/chat", ("-X", "POST", "-d", "{}"))):
            for phien in ((), ("-b", "authelia_session=phien-an"), ("-H", "Remote-User: an", "-H", "Remote-Groups: quan_ly")):
                self.assertEqual(self.ten(duong, *them, *phien)[0], "503", (duong, phien))
        self.assertEqual((PHIA_SAU_THAY.ds, OLLAMA_THAY.ds, AUTHELIA_THAY.ds), ([], [], []))
        self.assertEqual(self.ten("/")[:2], ("200", "OneBee Box trang chu"))
        self.assertNotIn("forward_auth", self.nd_goc)

    def test_giam_sat_ve_dang_nhap_rieng_cua_uptime_kuma(self):
        k = self.cong["uptime_kuma"]
        self.assertEqual(self.ten("/dashboard", cong=k)[0], "200")
        self.assertEqual(curl("--cacert", f"{self.t}/ca/root.crt", f"https://127.0.0.1:{k}/dashboard")[0], "200")
        self.assertEqual(AUTHELIA_THAY.ds, [])

    # Các bài của lớp cha chỉ đúng khi đăng nhập một lần bật
    test_a_chua_co_phien_goi_api_toi_nhan_401 = test_b_phien_hop_le_nhan_200_tu_cau_noi = None
    test_c_may_khach_tu_gui_remote_user_khong_co_tac_dung = test_d_authorization_cua_may_khach_khong_toi_phia_sau = None
    test_e_ai_chi_mo_hai_duong_dan_post = test_f_files_co_phien_nhan_503 = test_j_than_qua_1mb_bi_chan = None
    test_k_giam_sat_chi_ky_thuat_hai_lop = None


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddyDinhDanhChet(unittest.TestCase):
    """Dịch vụ định danh không trả lời: tuyến lõi và giám sát đóng (lỗi), không bao giờ cho qua; trang chủ vẫn mở."""

    @classmethod
    def setUpClass(cls):
        CaddySso.setUpClass()
        CaddySso.dung_caddy(sso=True, authelia_chet=True)

    @classmethod
    def tearDownClass(cls):
        CaddySso.tearDownClass()
        CaddySso.caddy = None

    def test_khong_cho_qua_khi_dinh_danh_chet(self):
        for g in (PHIA_SAU_THAY, OLLAMA_THAY, KUMA_THAY):
            g.ds.clear()
        gia = ("-b", "authelia_session=phien-ql", "-H", "Remote-User: binh", "-H", "Remote-Groups: quan_ly")
        for duong, them in (("/api/toi", ()), ("/files/x", ()), ("/ai/api/chat", ("-X", "POST", "-d", "{}"))):
            ma = CaddySso.ten(duong, *them, *gia)[0]
            self.assertRegex(ma, r"^50[024]$", duong)          # Caddy không gọi được forward_auth → lỗi cổng, không chuyển tiếp
        self.assertRegex(CaddySso.ten("/dashboard", *gia, cong=CaddySso.cong["uptime_kuma"])[0], r"^50[024]$")
        self.assertEqual((PHIA_SAU_THAY.ds, OLLAMA_THAY.ds, KUMA_THAY.ds), ([], [], []))
        self.assertEqual(CaddySso.ten("/")[:2], ("200", "OneBee Box trang chu"))


if __name__ == "__main__":
    unittest.main()
