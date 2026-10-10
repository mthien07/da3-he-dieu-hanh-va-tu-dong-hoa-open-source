#!/usr/bin/env python3
"""Kiểm thử CA riêng của Box (box-stack/files/onebee-ca.sh): ràng buộc tên thật sự chặn chứng chỉ giả, idempotent, xoay CA phải có chủ ý.
Chuỗi thật: gốc → trung gian → lá (lá do test ký bằng khóa trung gian — giả định kẻ tấn công lấy được khóa trung gian).
Kiểm bằng openssl, Python ssl và curl. Chạy: python3 -m unittest"""
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")
CO_CONG_CU = shutil.which("openssl") is not None


def chay(*a, **kw):
    return subprocess.run(list(a), capture_output=True, text=True, **kw)


@unittest.skipUnless(CO_CONG_CU, "cần openssl")
class CaRieng(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = self.tmp.name
        self.ca = f"{self.t}/ca"
        r = chay(SCRIPT, self.ca, "anphu", "127.0.0.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("đã đổi", r.stdout)

    def la(self, san, ten="la"):
        """Lá với SAN cho trước, ký bằng khóa trung gian."""
        t, ca = self.t, self.ca
        chay("openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", f"{t}/{ten}.key")
        chay("openssl", "req", "-new", "-key", f"{t}/{ten}.key", "-subj", "/CN=x", "-out", f"{t}/{ten}.csr")
        open(f"{t}/{ten}.ext", "w").write(f"subjectAltName={san}\nbasicConstraints=CA:FALSE\n")
        r = chay("openssl", "x509", "-req", "-in", f"{t}/{ten}.csr", "-CA", f"{ca}/inter.crt", "-CAkey", f"{ca}/inter.key",
                 "-CAcreateserial", "-days", "30", "-extfile", f"{t}/{ten}.ext", "-out", f"{t}/{ten}.crt")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(f"{t}/{ten}.pem", "w") as f:   # chuỗi gửi cho client: lá + trung gian
            f.write(open(f"{t}/{ten}.crt").read() + open(f"{ca}/inter.crt").read())
        return f"{t}/{ten}.pem", f"{t}/{ten}.key"

    def openssl_chap_nhan(self, san, host):
        pem, _ = self.la(san, "v")
        opt = ["-verify_ip", host] if host[0].isdigit() else ["-verify_hostname", host]
        r = chay("openssl", "verify", "-CAfile", f"{self.ca}/root.crt", "-untrusted", f"{self.ca}/inter.crt", *opt, f"{self.t}/v.crt")
        return r.returncode == 0

    def test_quyen_va_rang_buoc(self):
        self.assertEqual(oct(os.stat(self.ca).st_mode & 0o777), "0o700")
        for k in ("root.key", "inter.key"):
            self.assertEqual(oct(os.stat(f"{self.ca}/{k}").st_mode & 0o777), "0o600")
        for c in ("root.crt", "inter.crt"):
            txt = chay("openssl", "x509", "-in", f"{self.ca}/{c}", "-noout", "-text").stdout
            self.assertIn("Name Constraints: critical", txt)
            self.assertIn("IP:127.0.0.1/255.255.255.255", txt)
            self.assertIn("DNS:anphu.onebee.internal", txt)
        self.assertIn("pathlen:1", chay("openssl", "x509", "-in", f"{self.ca}/root.crt", "-noout", "-text").stdout)
        self.assertIn("pathlen:0", chay("openssl", "x509", "-in", f"{self.ca}/inter.crt", "-noout", "-text").stdout)

    def test_chuoi_that_chi_chap_nhan_ten_trong_rang_buoc(self):
        self.assertTrue(self.openssl_chap_nhan("IP:127.0.0.1", "127.0.0.1"))
        self.assertTrue(self.openssl_chap_nhan("DNS:box.anphu.onebee.internal", "box.anphu.onebee.internal"))
        self.assertFalse(self.openssl_chap_nhan("DNS:www.google.com", "www.google.com"))
        self.assertFalse(self.openssl_chap_nhan("IP:10.0.0.5", "10.0.0.5"))           # router/NAS khác trong LAN
        self.assertFalse(self.openssl_chap_nhan("DNS:box.khachkhac.onebee.internal", "box.khachkhac.onebee.internal"))  # CA khách A không giả được khách B

    def _may_chu_tls(self, san):
        pem, key = self.la(san, "srv")
        ngu_canh = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ngu_canh.load_cert_chain(pem, key)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(5)

        def phuc_vu():
            while True:
                try:
                    c, _ = sock.accept()
                    with ngu_canh.wrap_socket(c, server_side=True) as tls:
                        tls.recv(10)
                        tls.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nok")
                except (ssl.SSLError, OSError):
                    if sock.fileno() == -1:
                        return
        threading.Thread(target=phuc_vu, daemon=True).start()
        self.addCleanup(sock.close)
        return sock.getsockname()[1]

    def test_python_ssl_va_curl_chan_ten_ngoai_rang_buoc(self):
        cong = self._may_chu_tls("DNS:www.google.com")   # kẻ tấn công cầm khóa trung gian dựng máy chủ giả google.com
        ctx = ssl.create_default_context(cafile=f"{self.ca}/root.crt")
        with self.assertRaises(ssl.SSLCertVerificationError):
            with ctx.wrap_socket(socket.create_connection(("127.0.0.1", cong)), server_hostname="www.google.com"):
                pass
        r = chay("curl", "-sS", "--noproxy", "*", "--cacert", f"{self.ca}/root.crt", "--resolve", f"www.google.com:{cong}:127.0.0.1",
                 f"https://www.google.com:{cong}/")
        self.assertNotEqual(r.returncode, 0)
        # Đúng tên trong ràng buộc thì qua
        cong2 = self._may_chu_tls("IP:127.0.0.1")
        r = chay("curl", "-sS", "--noproxy", "*", "--cacert", f"{self.ca}/root.crt", f"https://127.0.0.1:{cong2}/")
        self.assertEqual((r.returncode, r.stdout), (0, "ok"), r.stderr)

    def test_chay_lai_khong_doi_gi(self):
        truoc = {f: open(f"{self.ca}/{f}", "rb").read() for f in os.listdir(self.ca)}
        r = chay(SCRIPT, self.ca, "anphu", "127.0.0.1")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(truoc, {f: open(f"{self.ca}/{f}", "rb").read() for f in os.listdir(self.ca)})

    def test_doi_ma_hoac_ip_phai_xoay_co_chu_y(self):
        r = chay(SCRIPT, self.ca, "anphu", "192.168.9.9")
        self.assertEqual(r.returncode, 4)
        self.assertIn("xoay CA", r.stderr)
        r = chay(SCRIPT, self.ca, "khac", "127.0.0.1")
        self.assertEqual(r.returncode, 4)
        van_tay_cu = open(f"{self.ca}/root.sha256").read()
        r = chay(SCRIPT, self.ca, "khac", "127.0.0.1", "--xoay")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(open(f"{self.ca}/root.sha256").read(), van_tay_cu)
        self.assertTrue([d for d in os.listdir(self.t) if d.startswith("ca.cu-")])   # CA cũ được cất lại, không mất

    def test_gia_han_trung_gian_khi_con_it_ngay_giu_nguyen_goc(self):
        goc = open(f"{self.ca}/root.crt", "rb").read()
        # Giả lập trung gian sắp hết hạn: ký lại với hạn 10 ngày
        chay("openssl", "req", "-new", "-key", f"{self.ca}/inter.key", "-subj", "/CN=cu", "-out", f"{self.t}/i.csr")
        open(f"{self.t}/i.ext", "w").write(
            "basicConstraints=critical,CA:TRUE,pathlen:0\nnameConstraints=critical,permitted;IP:127.0.0.1/255.255.255.255,permitted;DNS:anphu.onebee.internal\n")
        chay("openssl", "x509", "-req", "-in", f"{self.t}/i.csr", "-CA", f"{self.ca}/root.crt", "-CAkey", f"{self.ca}/root.key",
             "-CAcreateserial", "-days", "10", "-extfile", f"{self.t}/i.ext", "-out", f"{self.ca}/inter.crt")
        cu = open(f"{self.ca}/inter.crt", "rb").read()
        r = chay(SCRIPT, self.ca, "anphu", "127.0.0.1")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "đã đổi"))
        self.assertNotEqual(open(f"{self.ca}/inter.crt", "rb").read(), cu)
        self.assertEqual(open(f"{self.ca}/root.crt", "rb").read(), goc)   # gốc không đổi → máy trạm không phải nhận CA lại
        self.assertEqual(chay("openssl", "verify", "-CAfile", f"{self.ca}/root.crt", f"{self.ca}/inter.crt").returncode, 0)

    def test_thu_muc_cho_caddy_chi_co_goc_va_trung_gian_khong_co_khoa_goc(self):
        pki = f"{self.t}/pki"
        env = dict(os.environ, ONEBEE_PKI_OUT=pki)
        r = chay(SCRIPT, self.ca, "anphu", "127.0.0.1", env=env)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "đã đổi"))   # thư mục mới → đổi
        self.assertEqual(sorted(os.listdir(pki)), ["inter.crt", "inter.key", "root.crt"])
        self.assertEqual(oct(os.stat(f"{pki}/inter.key").st_mode & 0o777), "0o600")
        self.assertEqual(open(f"{pki}/root.crt").read(), open(f"{self.ca}/root.crt").read())
        r = chay(SCRIPT, self.ca, "anphu", "127.0.0.1", env=env)
        self.assertEqual((r.returncode, r.stdout), (0, ""))                 # chạy lại không đổi
        open(f"{pki}/root.key", "w").write("khoa goc chep nham")
        chay(SCRIPT, self.ca, "anphu", "127.0.0.1", env=env)
        self.assertFalse(os.path.exists(f"{pki}/root.key"))                 # khóa gốc không bao giờ nằm ở thư mục này

    def test_tu_choi_dau_vao_sai(self):
        for ma in ("Viet Hoa", "-abc", "a" * 40, "co.dau"):
            self.assertNotEqual(chay(SCRIPT, f"{self.t}/x", ma, "10.0.0.1").returncode, 0, ma)
        self.assertNotEqual(chay(SCRIPT, f"{self.t}/x", "abc", "10.0.0.999x").returncode, 0)


if __name__ == "__main__":
    unittest.main()
