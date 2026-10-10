#!/usr/bin/env python3
"""Kiểm thử Caddyfile HTTPS của Box (box-stack/templates/Caddyfile.j2) bằng Caddy THẬT chạy trên máy (không cần Docker).
Cần tệp chạy caddy: đặt biến ONEBEE_TEST_CADDY=/đường/dẫn/caddy (hoặc caddy có trong PATH), nếu không bài này bị bỏ qua.
Backend là máy chủ HTTP giả; CA là CA riêng do onebee-ca.sh sinh (gốc không kèm khóa gốc ở thư mục của Caddy).
Kiểm: Caddy nhận gốc không khóa + trung gian có khóa; nối bằng IP KHÔNG SNI (default_sni) và bằng tên; chuỗi đến CA riêng; http:// tới cổng TLS bị chuyển 308;
cổng 80 chỉ phục vụ CA/hướng dẫn; mỗi cổng tới đúng backend; Kuma chỉ có site khi đã sẵn sàng. Chạy: python3 -m unittest"""
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
            nd = f"backend-{ten} host={self.headers.get('Host')} xfp={self.headers.get('X-Forwarded-Proto')}".encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(nd)))
            self.end_headers()
            self.wfile.write(nd)
    sv = HTTPServer(("127.0.0.1", 0), H)
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
        cls.cong = {"portal": cong_trong(), "open_webui": cong_trong(), "n8n": cong_trong(), "rest_server": cong_trong(),
                    "uptime_kuma": cong_trong(), "http": cong_trong()}
        cls.bk = {n: backend(n) for n in ("open-webui", "n8n", "rest-server", "uptime-kuma")}
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
        v.update(onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_kuma_dia_chi=kuma,
                 onebee_box_ports={"portal": 80, "open_webui": c["open_webui"], "n8n": c["n8n"], "rest_server": c["rest_server"],
                                   "uptime_kuma": c["uptime_kuma"]})
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # Ansible mặc định trim_blocks=True
        env.filters["bool"] = bool
        nd = env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v)
        nd = nd.replace(":443", f":{c['portal']}").replace("\n:80 {", f"\n:{c['http']} {{")
        nd = nd.replace("/srv-http", f"{t}/srv-http").replace("root * /srv\n", f"root * {t}/srv\n").replace("/pki/", f"{t}/pki/")
        for ten, cong_goc in (("open-webui", 8080), ("n8n", 5678), ("rest-server", 8000), ("uptime-kuma", 3001)):
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
        for cong, ten in ((c["open_webui"], "open-webui"), (c["n8n"], "n8n"), (c["rest_server"], "rest-server"), (c["uptime_kuma"], "uptime-kuma")):
            r = curl("--cacert", self.goc(), f"https://127.0.0.1:{cong}/x")
            self.assertEqual(r.returncode, 0, (ten, r.stderr))
            self.assertIn(f"backend-{ten}", r.stdout)
            self.assertIn("xfp=https", r.stdout)                                      # backend biết mình đứng sau HTTPS

    def test_b_ten_phu_cho_ky_thuat_qua_tailscale(self):
        c = self.cong
        r = curl("--cacert", self.goc(), "--resolve", f"box.anphu.onebee.internal:{c['open_webui']}:127.0.0.1",
                 f"https://box.anphu.onebee.internal:{c['open_webui']}/x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("backend-open-webui", r.stdout)

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
        r = curl("-i", f"http://127.0.0.1:{c['open_webui']}/x?a=1")
        self.assertIn(" 308 ", r.stdout.splitlines()[0], r.stdout)
        self.assertIn(f"https://127.0.0.1:{c['open_webui']}/x?a=1", r.stdout)

    def test_e_cong_80_chi_phuc_vu_ca_va_huong_dan(self):
        c = self.cong
        self.assertEqual(curl(f"http://127.0.0.1:{c['http']}/onebee-ca.crt").stdout, open(self.goc()).read())
        self.assertEqual(curl(f"http://127.0.0.1:{c['http']}/").stdout, "huong dan cai CA")

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
        r = curl("--cacert", self.goc(), f"https://127.0.0.1:{self.cong['open_webui']}/x")
        self.assertEqual(r.returncode, 0, r.stderr)   # các cổng khác vẫn chạy


if __name__ == "__main__":
    unittest.main()
