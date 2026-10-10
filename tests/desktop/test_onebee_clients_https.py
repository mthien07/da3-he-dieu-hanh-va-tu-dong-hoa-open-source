#!/usr/bin/env python3
"""Kiểm thử phía máy trạm khi Box bật HTTPS (rà soát bảo mật F3, Pha 4): hoi / onebee-bao-tinh-trang ghim CA riêng của OneBee,
từ chối http:// khi máy đã có dấu bật HTTPS, báo lỗi dễ hiểu (chứng chỉ lạ, 502/503/504, 301/308); onebee-sao-luu đọc cấu hình không chạy như mã shell.
Máy chủ TLS thật dùng CA do box-stack/files/onebee-ca.sh sinh. Chạy: python3 -m unittest"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES = os.path.join(HERE, "../../desktop/ansible/roles")
TAO_CA = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")


def nap(ten, duong_dan):
    spec = importlib.util.spec_from_loader(ten, importlib.machinery.SourceFileLoader(ten, duong_dan))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HOI = nap("hoi", os.path.join(ROLES, "ai-cli/files/hoi"))
BAO = nap("bao_tinh_trang_https", os.path.join(ROLES, "quan-ly-tap-trung/files/onebee-bao-tinh-trang"))


class May(BaseHTTPRequestHandler):
    ma = 200
    dich = "https://khac.example/"   # nơi 301/308 chỉ tới

    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(May.ma)
        if May.ma in (301, 308):
            self.send_header("Location", May.dich)
        self.send_header("Content-Type", "application/json")
        nd = json.dumps({"choices": [{"message": {"content": "xin chào"}}]}).encode()
        self.send_header("Content-Length", str(len(nd)))
        self.end_headers()
        self.wfile.write(nd)


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class KhachHttps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        subprocess.run([TAO_CA, f"{t}/ca", "kiem-thu", "127.0.0.1"], check=True, capture_output=True)
        subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", f"{t}/l.key"], check=True, capture_output=True)
        subprocess.run(["openssl", "req", "-new", "-key", f"{t}/l.key", "-subj", "/CN=x", "-out", f"{t}/l.csr"], check=True, capture_output=True)
        open(f"{t}/l.ext", "w").write("subjectAltName=IP:127.0.0.1\nbasicConstraints=CA:FALSE\n")
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca/inter.crt", "-CAkey", f"{t}/ca/inter.key",
                        "-CAcreateserial", "-days", "30", "-extfile", f"{t}/l.ext", "-out", f"{t}/l.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi.pem", "w") as f:
            f.write(open(f"{t}/l.crt").read() + open(f"{t}/ca/inter.crt").read())
        # Chuỗi của một CA LẠ (kẻ giả danh Box): cùng IP nhưng CA khác
        subprocess.run([TAO_CA, f"{t}/ca-la", "ke-la", "127.0.0.1"], check=True, capture_output=True)
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca-la/inter.crt", "-CAkey", f"{t}/ca-la/inter.key",
                        "-CAcreateserial", "-days", "30", "-extfile", f"{t}/l.ext", "-out", f"{t}/l-la.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi-la.pem", "w") as f:
            f.write(open(f"{t}/l-la.crt").read() + open(f"{t}/ca-la/inter.crt").read())
        cls.cong_that = cls.chay_may_chu(f"{t}/chuoi.pem", f"{t}/l.key")
        cls.cong_la = cls.chay_may_chu(f"{t}/chuoi-la.pem", f"{t}/l.key")
        cls.cong_http = cls.chay_may_chu(None, None)
        cls.ca = f"{t}/ca/root.crt"

    @classmethod
    def chay_may_chu(cls, chuoi, khoa):
        sv = HTTPServer(("127.0.0.1", 0), May)
        if chuoi:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(chuoi, khoa)
            sv.socket = ctx.wrap_socket(sv.socket, server_side=True)
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        return sv.server_port

    def setUp(self):
        May.ma = 200
        self.dau = tempfile.NamedTemporaryFile(delete=False)
        self.dau.close()
        os.unlink(self.dau.name)   # chưa có dấu bật HTTPS
        self.addCleanup(lambda: os.path.exists(self.dau.name) and os.unlink(self.dau.name))
        for m in (HOI, BAO):
            m.CA_ONEBEE, m.HTTPS_BAT = self.ca, self.dau.name

    def req(self, cong, giao="https"):
        return urllib.request.Request(f"{giao}://127.0.0.1:{cong}/x", data=b"{}", method="POST")

    def test_hai_ban_mo_va_loi_mang_giong_het_nhau(self):
        import inspect
        for ten in ("mo", "loi_mang"):
            self.assertEqual(inspect.getsource(getattr(HOI, ten)), inspect.getsource(getattr(BAO, ten)), ten)

    def test_ca_that_nối_duoc_ca_la_bi_chan_voi_thong_bao_ro(self):
        for m in (HOI, BAO):
            with m.mo(self.req(self.cong_that), 10) as r:
                self.assertEqual(r.status, 200)
            with self.assertRaises(urllib.error.URLError) as cx:
                m.mo(self.req(self.cong_la), 10)
            self.assertIn("KHÔNG HỢP LỆ", m.loi_mang(cx.exception))

    def test_khong_tin_ca_cong_cong_chi_tin_ca_onebee(self):
        # Máy chủ dùng CA riêng nhưng client trỏ cafile khác (CA của kẻ lạ) → bị chặn dù chuỗi hợp lệ với kho hệ thống nào đó
        HOI.CA_ONEBEE = self.ca.replace("/ca/", "/ca-la/")
        with self.assertRaises(urllib.error.URLError):
            HOI.mo(self.req(self.cong_that), 10)

    def test_co_dau_https_thi_tu_choi_http(self):
        open(self.dau.name, "w").write("1\n")
        for m in (HOI, BAO):
            with self.assertRaises(SystemExit) as cx:
                m.mo(self.req(self.cong_http, "http"), 10)
            self.assertIn("đã bật HTTPS", str(cx.exception))
        os.unlink(self.dau.name)
        with HOI.mo(self.req(self.cong_http, "http"), 10) as r:   # chưa bật HTTPS (chuyển tiếp) → http vẫn chạy như cũ
            self.assertEqual(r.status, 200)

    def test_thieu_file_ca_thi_bao_chay_dong_bo(self):
        HOI.CA_ONEBEE = "/khong/co/ca.crt"
        with self.assertRaises(SystemExit) as cx:
            HOI.mo(self.req(self.cong_that), 10)
        self.assertIn("dong-bo-may", str(cx.exception))

    def test_cau_hinh_cu_http_tren_box_da_chuyen_https_thi_theo_308_mot_lan_cung_may_chu(self):
        for m in (HOI, BAO):
            May.ma, May.dich = 308, f"https://127.0.0.1:{self.cong_that}/x"
            try:
                May.ma = 308
                # máy chủ http trả 308 → https cùng host; máy chủ https đích trả 200 (đổi mã lại ngay sau lần đầu)
                kq = []
                orig = May.do_POST

                def post(self_, orig=orig):
                    if self_.server.server_port == self.cong_http:
                        return orig(self_)
                    May.ma = 200
                    return orig(self_)
                May.do_POST = post
                with m.mo(self.req(self.cong_http, "http"), 10) as r:
                    kq.append(r.status)
                self.assertEqual(kq, [200])
            finally:
                May.do_POST, May.ma, May.dich = orig, 200, "https://khac.example/"
            # Location tới máy chủ KHÁC: không theo
            May.ma = 308
            with self.assertRaises(urllib.error.HTTPError):
                m.mo(self.req(self.cong_http, "http"), 10)
            May.ma = 200

    def test_loi_502_503_504_va_chuyen_huong_cu(self):
        for ma, mong in ((502, "chưa chạy"), (503, "chưa chạy"), (504, "chưa chạy"), (308, "dong-bo-may")):
            May.ma = ma
            for m in (HOI, BAO):
                with self.assertRaises(urllib.error.HTTPError) as cx:
                    m.mo(self.req(self.cong_that), 10)
                self.assertIn(mong, m.loi_mang(cx.exception), (ma, m))
        May.ma = 401
        with self.assertRaises(urllib.error.HTTPError) as cx:
            HOI.mo(self.req(self.cong_that), 10)
        self.assertIsNone(HOI.loi_mang(cx.exception))   # mã khác giữ thông báo cũ


class SaoLuuDocCauHinh(unittest.TestCase):
    """onebee-sao-luu: đọc cấu hình bằng vòng lặp KHÓA=giá trị. restic giả ghi lại biến môi trường nhận được."""

    def chay(self, env_nd, dau_https=False):
        with tempfile.TemporaryDirectory() as t:
            nd = open(os.path.join(ROLES, "backup-client/files/onebee-sao-luu"), encoding="utf-8").read()
            nd = nd.replace("CONF=/etc/onebee/may-tram.env", f"CONF={t}/may-tram.env").replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||")
            nd = nd.replace("/usr/local/share/ca-certificates/onebee-box-ca.crt", f"{t}/ca.crt").replace("/var/lib/onebee", f"{t}/var")
            nd = nd.replace("restic ", "restic_gia ")
            open(f"{t}/sao-luu", "w").write(nd)
            open(f"{t}/may-tram.env", "w").write(env_nd)
            open(f"{t}/ca.crt", "w").write("ca\n")
            os.makedirs(f"{t}/var")
            if dau_https:
                open(f"{t}/var/https-bat", "w").write("1\n")
            open(f"{t}/restic_gia", "w").write(f'#!/bin/bash\necho "$@" >> {t}/lenh\n'
                                               f'echo "REPO=$RESTIC_REPOSITORY PW=$RESTIC_PASSWORD CACERT=${{RESTIC_CACERT:-}}" >> {t}/env\n')
            os.chmod(f"{t}/restic_gia", 0o755)
            r = subprocess.run(["bash", f"{t}/sao-luu"], capture_output=True, text=True, env={**os.environ, "PATH": f"{t}:{os.environ['PATH']}"})
            env = open(f"{t}/env").read() if os.path.exists(f"{t}/env") else ""
            return r, env

    def test_chi_nap_hai_dong_restic_va_khong_chay_dong_la_nhu_lenh(self):
        r, env = self.chay("RESTIC_REPOSITORY=rest:http://a:b@1.2.3.4:8000/a/\r\nQUAN_TRI_SSH_KEY=\"x\"\n$(touch /tmp/bi-chay-lenh)\n"
                           "`touch /tmp/bi-chay-lenh2`\nRESTIC_PASSWORD=mk=co=dau-bang=")        # dòng cuối KHÔNG có xuống dòng; giá trị kết thúc bằng =
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("REPO=rest:http://a:b@1.2.3.4:8000/a/ PW=mk=co=dau-bang= CACERT=", env)
        self.assertFalse(os.path.exists("/tmp/bi-chay-lenh") or os.path.exists("/tmp/bi-chay-lenh2"))

    def test_kho_https_dat_cacert_va_kho_http_bi_chan_khi_co_dau(self):
        r, env = self.chay("RESTIC_REPOSITORY=rest:https://a:b@1.2.3.4:8000/a/\nRESTIC_PASSWORD=x\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(env, r"CACERT=\S+/ca\.crt")
        r, env = self.chay("RESTIC_REPOSITORY=rest:http://a:b@1.2.3.4:8000/a/\nRESTIC_PASSWORD=x\n", dau_https=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dong-bo-may", r.stderr)
        self.assertEqual(env, "")   # restic không được chạy

    def test_thieu_mat_khau_thi_dung(self):
        r, _ = self.chay("RESTIC_REPOSITORY=rest:http://a:b@1.2.3.4:8000/a/\n")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
