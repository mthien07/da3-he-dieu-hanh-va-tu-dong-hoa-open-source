#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử Caddyfile HTTPS của Box (box-stack/templates/Caddyfile.j2) bằng Caddy THẬT chạy trên máy (không cần Docker).
Cần tệp chạy caddy: đặt biến ONEBEE_TEST_CADDY=/đường/dẫn/caddy (hoặc caddy có trong PATH), nếu không bài này bị bỏ qua.
Backend là máy chủ HTTP giả; CA là CA riêng do onebee-ca.sh sinh (gốc không kèm khóa gốc ở thư mục của Caddy).
Kiểm: Caddy nhận gốc không khóa + trung gian có khóa; nối bằng IP KHÔNG SNI (default_sni) và bằng tên; chuỗi đến CA riêng; http:// tới cổng TLS bị chuyển 308;
cổng 80 chỉ phục vụ CA/hướng dẫn + tuyến máy trạm xin vào (không đăng nhập, xóa Remote-*/Authorization, thân tối đa 64 KB; cả chế độ HTTP);
mỗi cổng tới đúng backend; Kuma chỉ có site khi đã sẵn sàng. Chạy: python3 -m unittest"""
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
TEMPLATE = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/Caddyfile.j2")
TAO_CA = os.path.join(ROOT, "box/ansible/roles/box-stack/files/onebee-ca.sh")
CADDY = os.environ.get("ONEBEE_TEST_CADDY") or shutil.which("caddy")


def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def backend(ten):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            nd = (f"backend-{ten} host={self.headers.get('Host')} xfp={self.headers.get('X-Forwarded-Proto')} "
                  f"ru={self.headers.get('Remote-User')} auth={self.headers.get('Authorization')} {self.command} {self.path}").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(nd)))
            self.end_headers()
            self.wfile.write(nd)

        do_POST = do_GET
    sv = HTTPServer(("127.0.0.1", 0), H)
    sv.handle_error = lambda *a: None   # Caddy ngắt giữa chừng khi thân vượt giới hạn
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    return sv


def curl(*a):
    return subprocess.run(["curl", "-sS", "--noproxy", "*", "-m", "15", *a], capture_output=True, text=True)


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddyHttps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name
        subprocess.run([TAO_CA, f"{t}/ca", "anphu", "127.0.0.1"], check=True, capture_output=True,
                       env={**os.environ, "ONEBEE_PKI_OUT": f"{t}/pki"})
        os.makedirs(f"{t}/srv"), os.makedirs(f"{t}/srv-http")
        open(f"{t}/srv/index.html", "w").write("OneBee Box trang chu")
        open(f"{t}/srv-http/index.html", "w").write("huong dan cai CA")
        shutil.copy(f"{t}/ca/root.crt", f"{t}/srv-http/onebee-ca.crt")
        cls.cong = {"portal": cong_trong(), "rest_server": cong_trong(),
                    "uptime_kuma": cong_trong(), "http": cong_trong()}
        cls.bk = {n: backend(n) for n in ("quy-trinh", "rest-server", "uptime-kuma")}
        cls.caddy = None

    @classmethod
    def tearDownClass(cls):
        if cls.caddy:
            cls.caddy.terminate()
            cls.caddy.wait(10)
        cls.tmp.cleanup()

    @classmethod
    def dung_caddy(cls, kuma="0.0.0.0"):
        """Render Caddyfile như Ansible rồi đổi cổng/đường dẫn/backend sang cổng thử trên máy này."""
        t = cls.t
        v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
        c = cls.cong
        # Đăng nhập một lần tắt: các cổng ứng dụng tới thẳng dịch vụ (tuyến SSO kiểm ở test_onebee_caddy_sso.py)
        v.update(onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_kuma_dia_chi=kuma,
                 onebee_sso_hieu_luc=False,
                 onebee_box_ports={"portal": 80, "rest_server": c["rest_server"],
                                   "uptime_kuma": c["uptime_kuma"]})
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # Ansible mặc định trim_blocks=True
        env.filters["bool"] = bool
        nd = env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v)
        nd = nd.replace(":443", f":{c['portal']}").replace("\n:80 {", f"\n:{c['http']} {{")
        nd = nd.replace("/srv-http", f"{t}/srv-http").replace("root * /srv\n", f"root * {t}/srv\n").replace("/pki/", f"{t}/pki/")
        for ten, cong_goc in (("quy-trinh", 1880), ("rest-server", 8000), ("uptime-kuma", 3001)):
            nd = nd.replace(f"{ten}:{cong_goc}", f"127.0.0.1:{cls.bk[ten].server_port}")
        open(f"{t}/Caddyfile", "w").write(nd)
        cls.nd = nd
        if cls.caddy:
            cls.caddy.terminate()
            cls.caddy.wait(10)
        env_c = {**os.environ, "XDG_DATA_HOME": f"{t}/data", "XDG_CONFIG_HOME": f"{t}/cfg"}
        r = subprocess.run([CADDY, "validate", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], capture_output=True, text=True, env=env_c)
        assert r.returncode == 0, r.stderr[-2000:]
        cls.caddy = subprocess.Popen([CADDY, "run", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], env=env_c,
                                     stdout=subprocess.DEVNULL, stderr=open(f"{t}/caddy.log", "w"))
        for _ in range(100):   # chờ Caddy nghe cổng và cấp xong chứng chỉ
            time.sleep(0.2)
            if curl("--cacert", f"{t}/ca/root.crt", f"https://127.0.0.1:{c['portal']}/").returncode == 0:
                return
        raise AssertionError("Caddy không lên: " + open(f"{t}/caddy.log").read()[-2000:])

    def goc(self):
        return f"{self.t}/ca/root.crt"

    def test_a_cac_cong_toi_dung_backend_qua_ip_khong_sni(self):
        self.dung_caddy()
        c = self.cong
        r = curl("--cacert", self.goc(), f"https://127.0.0.1:{c['portal']}/")        # nối bằng IP → không gửi SNI
        self.assertEqual((r.returncode, r.stdout), (0, "OneBee Box trang chu"), r.stderr)
        for cong, ten in ((c["rest_server"], "rest-server"), (c["uptime_kuma"], "uptime-kuma")):
            r = curl("--cacert", self.goc(), f"https://127.0.0.1:{cong}/x")
            self.assertEqual(r.returncode, 0, (ten, r.stderr))
            self.assertIn(f"backend-{ten}", r.stdout)
            self.assertIn("xfp=https", r.stdout)                                      # backend biết mình đứng sau HTTPS
        # Điểm nhận webhook của động cơ quy trình đi qua Caddy trên tên Box (không cổng riêng, không đăng nhập)
        r = curl("--cacert", self.goc(), "--resolve", f"box.anphu.onebee.internal:{c['portal']}:127.0.0.1",
                 f"https://box.anphu.onebee.internal:{c['portal']}/webhook/suc-khoe")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("backend-quy-trinh", r.stdout)

    def test_c_chuoi_chung_chi_la_gui_ra_tu_trung_gian_va_dung_rang_buoc(self):
        c = self.cong
        r = subprocess.run(["openssl", "s_client", "-connect", f"127.0.0.1:{c['portal']}", "-noservername", "-showcerts", "-CAfile", self.goc(),
                            "-verify_ip", "127.0.0.1", "-verify_return_error"], input="", capture_output=True, text=True)
        self.assertIn("Verification: OK", r.stdout + r.stderr)
        self.assertIn("Intermediate CA", r.stdout)
        # Mọi chứng chỉ khóa gốc không có trong tập tin của Caddy
        self.assertFalse(os.path.exists(f"{self.t}/pki/root.key"))

    def test_d_http_toi_cong_tls_bi_chuyen_308_sang_https(self):
        c = self.cong
        r = curl("-i", f"http://127.0.0.1:{c['rest_server']}/x?a=1")
        self.assertIn(" 308 ", r.stdout.splitlines()[0], r.stdout)
        self.assertIn(f"https://127.0.0.1:{c['rest_server']}/x?a=1", r.stdout)

    def test_e_cong_80_chi_phuc_vu_ca_va_huong_dan(self):
        c = self.cong
        self.assertEqual(curl(f"http://127.0.0.1:{c['http']}/onebee-ca.crt").stdout, open(self.goc()).read())
        self.assertEqual(curl(f"http://127.0.0.1:{c['http']}/").stdout, "huong dan cai CA")

    def test_e2_cong_80_chi_them_tuyen_xin_vao_toi_quy_trinh(self):
        if not self.caddy:
            self.dung_caddy()
        goc = f"http://127.0.0.1:{self.cong['http']}"
        gia = ("-H", "Remote-User: quanly", "-H", "Remote-Groups: quan_ly", "-H", "Authorization: Bearer x",
               "-H", "Content-Type: application/json")
        for duong in ("/webhook/onebee-xin-vao", "/webhook/onebee-xin-vao-mo", "/webhook/onebee-xin-vao-ket-qua"):
            r = curl("-X", "POST", *gia, "-d", "{}", goc + duong)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.split(" ", 1)[0], "backend-quy-trinh", r.stdout)
            self.assertIn(f"ru=None auth=None POST {duong}", r.stdout)      # danh tính máy khách tự gửi bị xóa
        # chỉ đúng tuyến đó: mọi webhook/đường dẫn khác vẫn chỉ là tệp tĩnh (404)
        for duong in ("/webhook/suc-khoe", "/webhook/onebee-duyet-may", "/webhook/onebee-may-xin-vao", "/webhook/onebee-canh-bao",
                      "/quy-trinh/", "/quy-trinh/webhook/onebee-duyet-may"):
            r = curl("-i", "-X", "POST", "-d", "{}", goc + duong)
            self.assertNotIn("backend-", r.stdout, duong)
            self.assertRegex(r.stdout.splitlines()[0], r" (404|405) ", duong)
        tep = f"{self.t}/lon64.bin"
        open(tep, "wb").write(b"x" * (64 * 1024 + 10))
        r = curl("-i", "-X", "POST", "--data-binary", f"@{tep}", "-H", "Content-Type: application/json", goc + "/webhook/onebee-xin-vao")
        self.assertIn(" 413 ", r.stdout.splitlines()[0], r.stdout)
        self.assertEqual(curl(f"{goc}/").stdout, "huong dan cai CA")        # phần cũ của cổng 80 giữ nguyên

    def test_f_ca_la_khong_tin_duoc(self):
        la = f"{self.t}/ca-la"
        subprocess.run([TAO_CA, la, "ke-la", "127.0.0.1"], check=True, capture_output=True)
        r = curl("--cacert", f"{la}/root.crt", f"https://127.0.0.1:{self.cong['portal']}/")
        self.assertNotEqual(r.returncode, 0)

    def test_g_khong_co_site_kuma_khi_chua_san_sang(self):
        self.dung_caddy(kuma="127.0.0.1")   # giám sát chưa có tài khoản quản trị → Caddy chưa công bố cổng 3001
        self.assertNotIn(f":{self.cong['uptime_kuma']}", self.nd.split("(onebee_tls)")[1])
        r = curl("--cacert", self.goc(), f"https://127.0.0.1:{self.cong['uptime_kuma']}/")
        self.assertNotEqual(r.returncode, 0)
        r = curl("--cacert", self.goc(), f"https://127.0.0.1:{self.cong['rest_server']}/x")
        self.assertEqual(r.returncode, 0, r.stderr)   # các cổng khác vẫn chạy


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddyHttpXinVao(unittest.TestCase):
    """Chế độ HTTP (HTTPS chưa bật): cổng 80 vẫn có tuyến xin vào với cùng giới hạn như chế độ HTTPS."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name
        os.makedirs(f"{t}/srv")
        open(f"{t}/srv/index.html", "w").write("OneBee Box trang chu")
        cls.http, cls.bk = cong_trong(), backend("quy-trinh")
        v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
        v.update(onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=False, onebee_sso_hieu_luc=False)
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
        env.filters["bool"] = bool
        nd = env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v)
        nd = nd.replace("\n:80 {", f"\n:{cls.http} {{").replace("root * /srv\n", f"root * {t}/srv\n")
        nd = nd.replace("quy-trinh:1880", f"127.0.0.1:{cls.bk.server_port}")
        open(f"{t}/Caddyfile", "w").write(nd)
        env_c = {**os.environ, "XDG_DATA_HOME": f"{t}/data", "XDG_CONFIG_HOME": f"{t}/cfg"}
        r = subprocess.run([CADDY, "validate", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], capture_output=True, text=True, env=env_c)
        assert r.returncode == 0, r.stderr[-2000:]
        cls.caddy = subprocess.Popen([CADDY, "run", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], env=env_c,
                                     stdout=subprocess.DEVNULL, stderr=open(f"{t}/caddy.log", "w"))
        for _ in range(100):
            time.sleep(0.2)
            if curl(f"http://127.0.0.1:{cls.http}/").stdout == "OneBee Box trang chu":
                return
        raise AssertionError("Caddy không lên: " + open(f"{t}/caddy.log").read()[-2000:])

    @classmethod
    def tearDownClass(cls):
        cls.caddy.terminate()
        cls.caddy.wait(10)
        cls.tmp.cleanup()

    def test_tuyen_xin_vao_xoa_danh_tinh_va_gioi_han_64kb(self):
        goc = f"http://127.0.0.1:{self.http}"
        for duong in ("/webhook/onebee-xin-vao", "/webhook/onebee-xin-vao-mo", "/webhook/onebee-xin-vao-ket-qua"):
            r = curl("-X", "POST", "-H", "Remote-User: quanly", "-H", "Authorization: Bearer x", "-d", "{}", goc + duong)
            self.assertIn(f"backend-quy-trinh", r.stdout)
            self.assertIn(f"ru=None auth=None POST {duong}", r.stdout)
        tep = f"{self.t}/lon64.bin"
        open(tep, "wb").write(b"x" * (64 * 1024 + 10))
        r = curl("-i", "-X", "POST", "--data-binary", f"@{tep}", goc + "/webhook/onebee-xin-vao-mo")
        self.assertIn(" 413 ", r.stdout.splitlines()[0], r.stdout)

    def test_webhook_cu_va_trang_chu_giu_nguyen(self):
        goc = f"http://127.0.0.1:{self.http}"
        self.assertIn("backend-quy-trinh", curl(f"{goc}/webhook/suc-khoe").stdout)
        self.assertIn(" 404 ", curl("-i", f"{goc}/so-dieu-hanh/").stdout.splitlines()[0])
        self.assertEqual(curl(f"{goc}/").stdout, "OneBee Box trang chu")


if __name__ == "__main__":
    unittest.main()
