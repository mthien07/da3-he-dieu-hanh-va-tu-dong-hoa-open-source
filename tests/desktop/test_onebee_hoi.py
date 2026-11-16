#!/usr/bin/env python3
"""Kiểm thử lệnh `hoi` gọi dịch vụ Trợ lý AI qua /ai/ (F10): dán khóa chỉ lưu khóa (0600), kiểm khóa trước khi lưu,
đăng xuất, hai tài khoản Linux dùng hai khóa khác nhau, khóa máy chỉ là chuyển tiếp, từ chối http:// và CA lạ.
Máy chủ giả chạy sau TLS thật (CA do onebee-ca.sh sinh). Chạy: python3 -m unittest"""
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


class TroLyGia(BaseHTTPRequestHandler):
    """Phần dịch vụ Trợ lý AI mà hoi gọi: POST /ai/hoi và POST /ai/tom-tat."""
    khoa_hop_le = {}         # khóa -> tên người dùng
    nhat_ky = []

    def log_message(self, *a):
        pass

    def _gui(self, ma, nd=None):
        raw = json.dumps(nd, ensure_ascii=False).encode() if nd is not None else b""
        self.send_response(ma)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        TroLyGia.nhat_ky.append(self.path)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        khoa = self.headers.get("X-OneBee-Khoa", "")
        if khoa not in TroLyGia.khoa_hop_le:
            return self._gui(401, {"loi": "Chưa đăng nhập hoặc khóa API không hợp lệ"})
        if self.path == "/ai/hoi":
            if not (body.get("cau_hoi") or "").strip():
                return self._gui(400, {"loi": "Thiếu câu hỏi"})
            return self._gui(200, {"tra_loi": f"trả lời cho {TroLyGia.khoa_hop_le[khoa]}",
                                   "nguon": [{"nguon": "tri-thuc/nd30.md", "tieu_de": "Thể thức văn bản"}]})
        if self.path == "/ai/tom-tat":
            if not (body.get("noi_dung") or "").strip():
                return self._gui(400, {"loi": "Thiếu nội dung cần tóm tắt"})
            return self._gui(200, {"tom_tat": f"tóm tắt cho {TroLyGia.khoa_hop_le[khoa]}"})
        self._gui(404, {"loi": "Không có đường dẫn này"})


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class HoiQuaDuongAi(unittest.TestCase):
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
        sv = HTTPServer(("127.0.0.1", 0), TroLyGia)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(f"{t}/chuoi.pem", f"{t}/l.key")
        sv.socket = ctx.wrap_socket(sv.socket, server_side=True)
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        cls.sv = sv
        cls.https = f"https://127.0.0.1:{sv.server_port}"
        sv2 = HTTPServer(("127.0.0.1", 0), TroLyGia)   # cùng API nhưng KHÔNG có TLS
        threading.Thread(target=sv2.serve_forever, daemon=True).start()
        cls.sv2 = sv2
        cls.http = f"http://127.0.0.1:{sv2.server_port}"
        subprocess.run([TAO_CA, f"{t}/ca-khac", "khac", "127.0.0.1"], check=True, capture_output=True)   # CA không phải của Box này

    @classmethod
    def tearDownClass(cls):
        for sv in (cls.sv, cls.sv2):
            sv.shutdown()
            sv.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        TroLyGia.khoa_hop_le, TroLyGia.nhat_ky = {}, []
        self.home = tempfile.mkdtemp(dir=self.t)
        self.conf = f"{self.t}/hoi.conf"
        self.dat_conf(self.https)

    def dat_conf(self, url, khoa_may=None):
        with open(self.conf, "w") as f:
            f.write(f"HOI_URL={url}\n" + (f"HOI_API_KEY={khoa_may}\n" if khoa_may else ""))

    def hoi(self, *args, dau_vao=(), home=None, ca=None, piped=""):
        """Chạy main() của hoi với CA/home giả; dau_vao: các chuỗi trả về cho getpass()."""
        m = nap_hoi()
        m.CONF, m.CA_ONEBEE = self.conf, ca or f"{self.t}/ca/root.crt"
        m.KHOA_NV = os.path.join(home or self.home, ".config/onebee/hoi-khoa")
        nhap = iter(dau_vao)
        out, err = io.StringIO(), io.StringIO()
        ma = 0
        with mock.patch("builtins.input", lambda *_: next(nhap)), mock.patch("getpass.getpass", lambda *_: next(nhap)), \
                mock.patch.object(m.sys, "argv", ["hoi", *args]), mock.patch.object(m, "read_piped_input", lambda: piped), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                ma = m.main()
            except SystemExit as e:
                ma = e.code if isinstance(e.code, int) else str(e.code)
                err.write(str(e.code))
        return ma, out.getvalue(), err.getvalue(), m.KHOA_NV

    def test_dan_khoa_chi_luu_khoa_quyen_0600_va_hoi_duoc(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        ma, out, err, f = self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        self.assertEqual(ma, 0, err)
        self.assertEqual(open(f).read().strip(), "obk-" + "a" * 48)
        self.assertEqual(stat.S_IMODE(os.stat(f).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(f)).st_mode), 0o700)
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual((ma, out.strip()), (0, "trả lời cho an"), err)
        self.assertIn("Thể thức văn bản", err)   # nguồn tham khảo in ở stderr
        self.assertEqual(TroLyGia.nhat_ky, ["/ai/hoi", "/ai/hoi"])

    def test_dan_khoa_sai_khong_luu(self):
        ma, _, err, f = self.hoi("--dan-khoa", dau_vao=("obk-" + "b" * 48,))
        self.assertNotEqual(ma, 0)
        self.assertIn("chưa lưu gì", err)
        self.assertFalse(os.path.exists(f))

    def test_tu_choi_khi_url_con_http(self):
        self.dat_conf(self.http)
        ma, _, err, f = self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        self.assertNotEqual(ma, 0)
        self.assertIn("https://", err)
        self.assertEqual(TroLyGia.nhat_ky, [])      # không gửi khóa qua mạng dạng rõ
        self.assertFalse(os.path.exists(f))

    def test_ca_la_khong_duoc_chap_nhan(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        with mock.patch.dict(os.environ, {"SSL_CERT_FILE": f"{self.t}/ca/root.crt"}):
            ma, _, err, f = self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,), ca=f"{self.t}/ca-khac/root.crt")
        self.assertNotEqual(ma, 0)
        self.assertIn("KHÔNG HỢP LỆ", err)
        self.assertEqual(TroLyGia.nhat_ky, [])
        self.assertFalse(os.path.exists(f))

    def test_hai_tai_khoan_linux_hai_khoa_khac_nhau(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        TroLyGia.khoa_hop_le["obk-" + "b" * 48] = "binh"
        home_b = tempfile.mkdtemp(dir=self.t)
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        self.hoi("--dan-khoa", dau_vao=("obk-" + "b" * 48,), home=home_b)
        self.assertEqual(self.hoi("câu hỏi")[1].strip(), "trả lời cho an")
        self.assertEqual(self.hoi("câu hỏi", home=home_b)[1].strip(), "trả lời cho binh")

    def test_dang_xuat_xoa_khoa(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        ma, out, _, f = self.hoi("--dang-xuat")
        self.assertEqual(ma, 0)
        self.assertFalse(os.path.exists(f))
        self.assertIn("chưa lưu khóa", self.hoi("--dang-xuat")[1])

    def test_chua_co_khoa_thi_huong_dan_cap_khoa(self):
        ma, _, err, _ = self.hoi("xin chào")
        self.assertNotEqual(ma, 0)
        self.assertIn("cap-khoa-hoi", err)

    def test_khoa_may_chi_la_chuyen_tiep_va_khoa_nhan_vien_duoc_uu_tien(self):
        TroLyGia.khoa_hop_le["obk-" + "b" * 48] = "may"
        self.dat_conf(self.https, khoa_may="obk-" + "b" * 48)
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual((ma, out.strip()), (0, "trả lời cho may"), err)
        self.assertIn("khóa chung của máy", err)
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        ma, out, err, _ = self.hoi("xin chào")
        self.assertEqual(out.strip(), "trả lời cho an")      # khóa nhân viên thắng khóa máy
        self.assertNotIn("khóa chung của máy", err)

    def test_khoa_bi_thu_hoi_bao_ro(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        TroLyGia.khoa_hop_le.clear()                                   # quản trị thu hồi khóa
        ma, _, err, _ = self.hoi("xin chào")
        self.assertNotEqual(ma, 0)
        self.assertIn("thu hồi", err)
        self.assertIn("--dan-khoa", err)

    def test_tom_tat_gui_dung_duong_tom_tat(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        ma, out, err, _ = self.hoi("--tom-tat", piped="Tuần này: 12 đơn, doanh thu 34 triệu.")
        self.assertEqual((ma, out.strip()), (0, "tóm tắt cho an"), err)
        self.assertEqual(TroLyGia.nhat_ky[-1], "/ai/tom-tat")

    def test_noi_dung_dan_qua_dau_vao_duoc_gui_kem_cau_hoi(self):
        TroLyGia.khoa_hop_le["obk-" + "a" * 48] = "an"
        self.hoi("--dan-khoa", dau_vao=("obk-" + "a" * 48,))
        ma, out, _, _ = self.hoi("tóm tắt đoạn này", piped="Nội dung cần tóm tắt.")
        self.assertEqual(ma, 0)
        self.assertEqual(TroLyGia.nhat_ky[-1], "/ai/hoi")


if __name__ == "__main__":
    unittest.main()
