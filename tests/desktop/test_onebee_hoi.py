#!/usr/bin/env python3
"""Kiểm thử lệnh `hoi` theo từng nhân viên (rà soát bảo mật F10, Pha 4c): đăng nhập → chỉ lưu khóa (0600), dán khóa, đăng xuất, hai tài khoản
Linux dùng hai khóa khác nhau, khóa máy chỉ là chuyển tiếp, từ chối đăng nhập qua http://. Open WebUI giả chạy sau TLS thật (CA do onebee-ca.sh sinh).
Chạy: python3 -m unittest"""
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import ssl
import stat
import subprocess
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HOI_PATH = os.path.join(HERE, "../../desktop/ansible/roles/ai-cli/files/hoi")
TAO_CA = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")


def nap_hoi():
    spec = importlib.util.spec_from_loader("hoi_ca_nhan", importlib.machinery.SourceFileLoader("hoi_ca_nhan", HOI_PATH))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class OpenWebuiGia(BaseHTTPRequestHandler):
    """Phần API Open WebUI mà hoi gọi: signin, api_key (GET/POST), models, chat/completions."""
    mat_khau = {"an@onebee.lan": "mk-an", "binh@onebee.lan": "mk-binh"}
    khoa_cua = {}            # email -> khóa API đã có
    khoa_hop_le = {}         # khóa -> email
    cho_phep_tao_khoa = True
    nhat_ky = []

    def log_message(self, *a):
        pass

    def _gui(self, ma, nd=None):
        raw = json.dumps(nd).encode() if nd is not None else b""
        self.send_response(ma)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _email_phien(self):
        t = self.headers.get("Authorization", "").replace("Bearer ", "")
        return t[len("tok-"):] if t.startswith("tok-") else None

    def do_GET(self):
        OpenWebuiGia.nhat_ky.append(f"GET {self.path}")
        if self.path == "/api/v1/auths/api_key":
            e = self._email_phien()
            k = OpenWebuiGia.khoa_cua.get(e)
            return self._gui(200, {"api_key": k}) if k else self._gui(404, {"detail": "none"})
        if self.path == "/api/models":
            k = self.headers.get("Authorization", "").replace("Bearer ", "")
            return self._gui(200, {"data": []}) if k in OpenWebuiGia.khoa_hop_le else self._gui(401)
        self._gui(404)

    def do_POST(self):
        OpenWebuiGia.nhat_ky.append(f"POST {self.path}")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/api/v1/auths/signin":
            if OpenWebuiGia.mat_khau.get(body.get("email")) == body.get("password"):
                return self._gui(200, {"token": "tok-" + body["email"]})
            return self._gui(400, {"detail": "sai"})
        if self.path == "/api/v1/auths/api_key":
            e = self._email_phien()
            if not e or not OpenWebuiGia.cho_phep_tao_khoa:
                return self._gui(403)
            k = "sk-" + e.split("@")[0] + "-moi"
            OpenWebuiGia.khoa_cua[e] = k
            OpenWebuiGia.khoa_hop_le[k] = e
            return self._gui(200, {"api_key": k})
        if self.path == "/api/chat/completions":
            k = self.headers.get("Authorization", "").replace("Bearer ", "")
            if k not in OpenWebuiGia.khoa_hop_le:
                return self._gui(401)
            return self._gui(200, {"choices": [{"message": {"content": f"trả lời cho {OpenWebuiGia.khoa_hop_le[k]}"}}]})
        self._gui(404)


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class HoiTungNhanVien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name
        subprocess.run([TAO_CA, f"{t}/ca", "kiem-thu", "127.0.0.1"], check=True, capture_output=True)
        subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", f"{t}/l.key"], check=True, capture_output=True)
        subprocess.run(["openssl", "req", "-new", "-key", f"{t}/l.key", "-subj", "/CN=x", "-out", f"{t}/l.csr"], check=True, capture_output=True)
        open(f"{t}/l.ext", "w").write("subjectAltName=IP:127.0.0.1\nbasicConstraints=CA:FALSE\n")
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca/inter.crt", "-CAkey", f"{t}/ca/inter.key",
                        "-CAcreateserial", "-days", "30", "-extfile", f"{t}/l.ext", "-out", f"{t}/l.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi.pem", "w") as f:
            f.write(open(f"{t}/l.crt").read() + open(f"{t}/ca/inter.crt").read())
        sv = HTTPServer(("127.0.0.1", 0), OpenWebuiGia)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(f"{t}/chuoi.pem", f"{t}/l.key")
        sv.socket = ctx.wrap_socket(sv.socket, server_side=True)
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        cls.sv = sv
        cls.https = f"https://127.0.0.1:{sv.server_port}"
        sv2 = HTTPServer(("127.0.0.1", 0), OpenWebuiGia)   # cùng API nhưng KHÔNG có TLS
        threading.Thread(target=sv2.serve_forever, daemon=True).start()
        cls.sv2 = sv2
        cls.http = f"http://127.0.0.1:{sv2.server_port}"

    @classmethod
    def tearDownClass(cls):
        for sv in (cls.sv, cls.sv2):
            sv.shutdown()
            sv.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        OpenWebuiGia.khoa_cua, OpenWebuiGia.khoa_hop_le, OpenWebuiGia.cho_phep_tao_khoa, OpenWebuiGia.nhat_ky = {}, {}, True, []
        self.home = tempfile.mkdtemp(dir=self.t)
        self.conf = f"{self.t}/hoi.conf"
        self.dat_conf(self.https)

    def dat_conf(self, url, khoa_may=None):
        with open(self.conf, "w") as f:
            f.write(f"HOI_URL={url}\n" + (f"HOI_API_KEY={khoa_may}\n" if khoa_may else "") + "HOI_MODEL=onebee-tro-ly\n")

    def hoi(self, *args, dau_vao=(), home=None, https_bat=False):
        """Chạy main() của hoi với CA/dấu/home giả; dau_vao: các chuỗi trả về cho input()/getpass()."""
        m = nap_hoi()
        m.CONF, m.CA_ONEBEE = self.conf, f"{self.t}/ca/root.crt"
        dau = f"{self.t}/https-bat"
        if https_bat:
            open(dau, "w").write("1\n")
        elif os.path.exists(dau):
            os.unlink(dau)
        m.HTTPS_BAT = dau
        m.KHOA_NV = os.path.join(home or self.home, ".config/onebee/hoi-khoa")
        nhap = iter(dau_vao)
        out, err = io.StringIO(), io.StringIO()
        ma = 0
        with mock.patch("builtins.input", lambda *_: next(nhap)), mock.patch("getpass.getpass", lambda *_: next(nhap)), \
                mock.patch.object(m.sys, "argv", ["hoi", *args]), mock.patch.object(m, "read_piped_input", lambda: ""), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                ma = m.main()
            except SystemExit as e:
                ma = e.code if isinstance(e.code, int) else str(e.code)
                err.write(str(e.code))
        return ma, out.getvalue(), err.getvalue(), m.KHOA_NV

    def test_dang_nhap_chi_luu_khoa_quyen_0600_khong_luu_mat_khau(self):
        ma, out, err, f = self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        self.assertEqual(ma, 0, err)
        self.assertEqual(open(f).read().strip(), "sk-an-moi")
        self.assertEqual(stat.S_IMODE(os.stat(f).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(f)).st_mode), 0o700)
        for dirpath, _, files in os.walk(self.home):
            for fn in files:
                self.assertNotIn("mk-an", open(os.path.join(dirpath, fn)).read())
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual((ma, out.strip()), (0, "trả lời cho an@onebee.lan"), err)

    def test_dang_nhap_lai_khong_tao_khoa_moi_lam_hong_khoa_cu(self):
        self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        OpenWebuiGia.nhat_ky.clear()
        ma, *_ = self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        self.assertEqual(ma, 0)
        self.assertNotIn("POST /api/v1/auths/api_key", OpenWebuiGia.nhat_ky)   # đã có khóa thì dùng lại

    def test_sai_mat_khau_hoac_khong_duoc_tao_khoa_thi_khong_luu(self):
        ma, _, err, f = self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "sai"))
        self.assertNotEqual(ma, 0)
        self.assertIn("Sai email hoặc mật khẩu", err)
        self.assertFalse(os.path.exists(f))
        OpenWebuiGia.cho_phep_tao_khoa = False
        ma, _, err, f = self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        self.assertNotEqual(ma, 0)
        self.assertIn("Báo người quản trị", err)
        self.assertFalse(os.path.exists(f))

    def test_tu_choi_dang_nhap_khi_url_con_http(self):
        self.dat_conf(self.http)
        ma, _, err, f = self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        self.assertNotEqual(ma, 0)
        self.assertIn("http://", err)
        self.assertEqual(OpenWebuiGia.nhat_ky, [])      # không gửi gì tới Box (mật khẩu không đi qua mạng dạng rõ)
        self.assertFalse(os.path.exists(f))

    def test_dan_khoa_kiem_truoc_khi_luu(self):
        ma, _, err, f = self.hoi("--dan-khoa", dau_vao=("sk-khong-co",))
        self.assertNotEqual(ma, 0)
        self.assertIn("chưa lưu gì", err)
        self.assertFalse(os.path.exists(f))
        OpenWebuiGia.khoa_hop_le["sk-tu-tao"] = "binh@onebee.lan"
        ma, *_ = self.hoi("--dan-khoa", dau_vao=("  sk-tu-tao  ",))
        self.assertEqual(ma, 0)
        self.assertEqual(open(f).read().strip(), "sk-tu-tao")
        self.assertEqual(stat.S_IMODE(os.stat(f).st_mode), 0o600)

    def test_hai_tai_khoan_linux_hai_khoa_khac_nhau(self):
        home_b = tempfile.mkdtemp(dir=self.t)
        self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        self.hoi("--dang-nhap", dau_vao=("binh@onebee.lan", "mk-binh"), home=home_b)
        self.assertEqual(self.hoi("câu hỏi")[1].strip(), "trả lời cho an@onebee.lan")
        self.assertEqual(self.hoi("câu hỏi", home=home_b)[1].strip(), "trả lời cho binh@onebee.lan")

    def test_dang_xuat_xoa_khoa(self):
        self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        ma, out, _, f = self.hoi("--dang-xuat")
        self.assertEqual(ma, 0)
        self.assertFalse(os.path.exists(f))
        self.assertIn("chưa lưu khóa", self.hoi("--dang-xuat")[1])     # chạy lại không lỗi

    def test_chua_dang_nhap_va_khong_co_khoa_may_thi_huong_dan_ca_hai_cach(self):
        ma, _, err, _ = self.hoi("xin chào")
        self.assertNotEqual(ma, 0)
        self.assertIn("hoi --dang-nhap", err)
        self.assertIn("hoi --dan-khoa", err)

    def test_chuyen_tiep_khoa_may_van_dung_duoc_kem_nhac_va_khoa_nhan_vien_duoc_uu_tien(self):
        OpenWebuiGia.khoa_hop_le["sk-may"] = "may-ketoan@onebee.lan"
        self.dat_conf(self.https, khoa_may="sk-may")
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual((ma, out.strip()), (0, "trả lời cho may-ketoan@onebee.lan"), err)
        self.assertIn("hoi --dang-nhap", err)
        self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual(out.strip(), "trả lời cho an@onebee.lan")      # khóa nhân viên thắng khóa máy
        self.assertNotIn("khóa chung của máy", err)

    def test_khoa_bi_thu_hoi_bao_ro(self):
        self.hoi("--dang-nhap", dau_vao=("an@onebee.lan", "mk-an"))
        OpenWebuiGia.khoa_hop_le.clear()                                   # quản trị xóa tài khoản → khóa mất hiệu lực
        ma, _, err, _ = self.hoi("xin chào")
        self.assertNotEqual(ma, 0)
        self.assertIn("thu hồi", err)
        self.assertIn("hoi --dang-nhap", err)


if __name__ == "__main__":
    unittest.main()
