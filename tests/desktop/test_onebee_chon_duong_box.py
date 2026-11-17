#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử đơn vị cho công cụ tự chọn đường tới Box trên máy trạm (ket-noi-box/files/onebee-chon-duong-box):
bắt tay TLS với CA đã ghim tới BOX_IP:443 (server_hostname=BOX_TEN) để phân biệt Box thật trong LAN với mạng ngoài;
chỉ ghi /etc/hosts khi dòng # onebee-box thay đổi. Chạy: python3 -m unittest tests/desktop/test_onebee_chon_duong_box.py"""
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "../../desktop/ansible/roles/ket-noi-box/files/onebee-chon-duong-box"))
TAO_CA = os.path.abspath(os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh"))

BOX_IP = "127.0.0.1"
BOX_TEN = "box.kiem-thu.onebee.internal"
BOX_IP_TU_XA = "100.64.0.1"


class HandlerGia(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class ChonDuongBox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name
        subprocess.run(["bash", TAO_CA, f"{t}/ca", "kiem-thu", BOX_IP], check=True, capture_output=True)
        subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", f"{t}/l.key"],
                       check=True, capture_output=True)
        subprocess.run(["openssl", "req", "-new", "-key", f"{t}/l.key", "-subj", f"/CN={BOX_TEN}", "-out", f"{t}/l.csr"],
                       check=True, capture_output=True)
        # Chứng chỉ đúng: do CA của Box cấp cho đúng tên BOX_TEN
        with open(f"{t}/l-dung.ext", "w", encoding="utf-8") as f:
            f.write(f"subjectAltName=DNS:{BOX_TEN},IP:{BOX_IP}\nbasicConstraints=CA:FALSE\n")
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca/inter.crt",
                        "-CAkey", f"{t}/ca/inter.key", "-CAcreateserial", "-days", "30",
                        "-extfile", f"{t}/l-dung.ext", "-out", f"{t}/l-dung.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi-dung.pem", "w", encoding="utf-8") as f:
            f.write(open(f"{t}/l-dung.crt", encoding="utf-8").read() + open(f"{t}/ca/inter.crt", encoding="utf-8").read())

        # Chứng chỉ đúng CA của Box nhưng cấp cho tên khác (DNS:khac.kiem-thu.onebee.internal, khác BOX_TEN)
        with open(f"{t}/l-sai-ten.ext", "w", encoding="utf-8") as f:
            f.write("subjectAltName=DNS:khac.kiem-thu.onebee.internal\nbasicConstraints=CA:FALSE\n")
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca/inter.crt",
                        "-CAkey", f"{t}/ca/inter.key", "-CAcreateserial", "-days", "30",
                        "-extfile", f"{t}/l-sai-ten.ext", "-out", f"{t}/l-sai-ten.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi-sai-ten.pem", "w", encoding="utf-8") as f:
            f.write(open(f"{t}/l-sai-ten.crt", encoding="utf-8").read() + open(f"{t}/ca/inter.crt", encoding="utf-8").read())

        # Chứng chỉ của một CA LẠ (thiết bị giả danh Box ở mạng khách sạn)
        subprocess.run(["bash", TAO_CA, f"{t}/ca-la", "kiem-thu", BOX_IP], check=True, capture_output=True)
        subprocess.run(["openssl", "x509", "-req", "-in", f"{t}/l.csr", "-CA", f"{t}/ca-la/inter.crt",
                        "-CAkey", f"{t}/ca-la/inter.key", "-CAcreateserial", "-days", "30",
                        "-extfile", f"{t}/l-dung.ext", "-out", f"{t}/l-la.crt"], check=True, capture_output=True)
        with open(f"{t}/chuoi-la.pem", "w", encoding="utf-8") as f:
            f.write(open(f"{t}/l-la.crt", encoding="utf-8").read() + open(f"{t}/ca-la/inter.crt", encoding="utf-8").read())

        cls.ca = f"{t}/ca/root.crt"
        cls.cong_dung = cls.chay_tls(f"{t}/chuoi-dung.pem", f"{t}/l.key")
        cls.cong_sai_ten = cls.chay_tls(f"{t}/chuoi-sai-ten.pem", f"{t}/l.key")
        cls.cong_ca_la = cls.chay_tls(f"{t}/chuoi-la.pem", f"{t}/l.key")
        # Cổng đóng: mở rồi đóng ngay để lấy số cổng trống
        s = HTTPServer((BOX_IP, 0), HandlerGia)
        cls.cong_dong = s.server_port
        s.server_close()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def chay_tls(cls, chuoi_pem, khoa_pem):
        sv = HTTPServer((BOX_IP, 0), HandlerGia)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(chuoi_pem, khoa_pem)
        sv.socket = ctx.wrap_socket(sv.socket, server_side=True)
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        return sv.server_port

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.conf = os.path.join(self.d.name, "may-tram.env")
        self.hosts = os.path.join(self.d.name, "hosts")
        with open(self.hosts, "w", encoding="utf-8") as f:
            f.write("127.0.0.1 localhost\n10.0.0.5 may-in.lan # may-in\n")

    def ghi_conf(self, box_ip=BOX_IP, box_ten=BOX_TEN, box_ip_tu_xa=None):
        dong = ["MAY_TRAM=ketoan-01"]
        if box_ip is not None:
            dong.append(f"BOX_IP={box_ip}")
        if box_ten is not None:
            dong.append(f"BOX_TEN={box_ten}")
        if box_ip_tu_xa is not None:
            dong.append(f"BOX_IP_TU_XA={box_ip_tu_xa}")
        with open(self.conf, "w", encoding="utf-8") as f:
            f.write("\n".join(dong) + "\n")

    def chay(self, *args, cong=None, ca=None):
        env = dict(
            os.environ,
            ONEBEE_CONF=self.conf,
            ONEBEE_HOSTS=self.hosts,
            ONEBEE_CA=self.ca if ca is None else ca,
            ONEBEE_PORT=str(self.cong_dung if cong is None else cong),
        )
        return subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True, timeout=15)

    def doc_hosts(self):
        with open(self.hosts, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_khong_co_ip_tu_xa_ghi_dong_lan(self):
        self.ghi_conf(box_ip_tu_xa=None)
        r = self.chay(cong=self.cong_dong)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("đã đổi", r.stdout)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP} {BOX_TEN} # onebee-box")
        self.assertEqual(self.chay("--xem").stdout.strip(), "mạng văn phòng")

    def test_co_ip_tu_xa_va_tls_lan_dat_thi_dung_lan(self):
        self.ghi_conf(box_ip_tu_xa=BOX_IP_TU_XA)
        r = self.chay(cong=self.cong_dung)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP} {BOX_TEN} # onebee-box")
        self.assertEqual(self.chay("--xem").stdout.strip(), "mạng văn phòng")

    def test_co_ip_tu_xa_khong_ai_nghe_lan_thi_dung_vpn(self):
        self.ghi_conf(box_ip_tu_xa=BOX_IP_TU_XA)
        r = self.chay(cong=self.cong_dong)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP_TU_XA} {BOX_TEN} # onebee-box")
        self.assertEqual(self.chay("--xem").stdout.strip(), "từ xa qua VPN")

    def test_co_ip_tu_xa_chung_chi_ca_khac_thi_dung_vpn(self):
        self.ghi_conf(box_ip_tu_xa=BOX_IP_TU_XA)
        r = self.chay(cong=self.cong_ca_la)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP_TU_XA} {BOX_TEN} # onebee-box")

    def test_co_ip_tu_xa_chung_chi_dung_ca_nhung_sai_ten_thi_dung_vpn(self):
        self.ghi_conf(box_ip_tu_xa=BOX_IP_TU_XA)
        r = self.chay(cong=self.cong_sai_ten)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP_TU_XA} {BOX_TEN} # onebee-box")

    def test_chay_hai_lan_khong_doi_mtime(self):
        self.ghi_conf(box_ip_tu_xa=BOX_IP_TU_XA)
        r1 = self.chay(cong=self.cong_dung)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("đã đổi", r1.stdout)
        t_cu = os.path.getmtime(self.hosts) - 10
        os.utime(self.hosts, (t_cu, t_cu))
        r2 = self.chay(cong=self.cong_dung)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout.strip(), "")
        self.assertEqual(os.path.getmtime(self.hosts), t_cu)

    def test_box_ten_sai_dang_go_dong_va_giu_dong_khac(self):
        self.ghi_conf(box_ip_tu_xa=None)
        self.chay(cong=self.cong_dong)
        self.assertEqual(len(self.doc_hosts()), 3)
        for ten_sai in ("evil.com", "Box.UPPER.onebee.internal", "box..onebee.internal", ""):
            self.ghi_conf(box_ten=ten_sai)
            r = self.chay(cong=self.cong_dong)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self.doc_hosts(), ["127.0.0.1 localhost", "10.0.0.5 may-in.lan # may-in"])
        self.assertEqual(self.chay("--xem").stdout.strip(), "chưa nối Box")

    def test_ip_tu_xa_ngoai_dai_tailscale_bi_coi_nhu_khong_co(self):
        self.ghi_conf(box_ip_tu_xa="1.2.3.4")
        r = self.chay(cong=self.cong_dong)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.doc_hosts()[-1], f"{BOX_IP} {BOX_TEN} # onebee-box")


if __name__ == "__main__":
    unittest.main()
