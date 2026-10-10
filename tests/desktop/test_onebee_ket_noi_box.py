#!/usr/bin/env python3
"""Kiểm thử role ket-noi-box: kiểm CA (vân tay + ràng buộc tên) và chính sách trình duyệt (Firefox/Chromium) cài, gỡ, trộn với file của gói.
Dùng CA thật do box-stack/files/onebee-ca.sh sinh. Chạy: python3 -m unittest"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(HERE, "../../desktop/ansible/roles/ket-noi-box/files")
KIEM_CA = os.path.join(FILES, "onebee-kiem-ca.py")
TRINH_DUYET = os.path.join(FILES, "onebee-chinh-sach-trinh-duyet.py")
TAO_CA = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")


def chay(*a, **kw):
    return subprocess.run(list(a), capture_output=True, text=True, **kw)


def der_b64(pem):
    r = subprocess.run(["openssl", "x509", "-in", pem, "-outform", "DER"], capture_output=True, check=True)
    return base64.b64encode(r.stdout).decode(), hashlib.sha256(r.stdout).hexdigest()


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class KiemCa(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = self.tmp.name
        r = chay(TAO_CA, f"{self.t}/ca", "anphu", "192.168.1.10")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.b64, self.vt = der_b64(f"{self.t}/ca/root.crt")

    def ca_khac(self, ext_nc):
        """CA tự ký với ràng buộc tên tùy ý (ext_nc rỗng = không ràng buộc)."""
        chay("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-keyout", f"{self.t}/x.key",
             "-subj", "/CN=x", "-days", "30", "-addext", "basicConstraints=critical,CA:TRUE",
             *(["-addext", f"nameConstraints={ext_nc}"] if ext_nc else []), "-out", f"{self.t}/x.crt")
        return der_b64(f"{self.t}/x.crt")

    def test_ca_dung_duoc_cai_va_in_pem(self):
        r = chay(KIEM_CA, self.b64, self.vt, "192.168.1.10")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("-----BEGIN CERTIFICATE-----"))

    def test_sai_van_tay_hoac_sai_ip_bi_tu_choi(self):
        self.assertEqual(chay(KIEM_CA, self.b64, "0" * 64, "192.168.1.10").returncode, 1)
        r = chay(KIEM_CA, self.b64, self.vt, "192.168.1.11")
        self.assertEqual(r.returncode, 1)
        self.assertIn("đúng IP của Box", r.stderr)
        self.assertEqual(chay(KIEM_CA, "không-phải-base64", self.vt, "192.168.1.10").returncode, 1)
        self.assertEqual(chay(KIEM_CA, self.b64, "abc", "192.168.1.10").returncode, 1)

    def test_ca_khong_rang_buoc_bi_tu_choi_du_van_tay_khop(self):
        b64, vt = self.ca_khac("")
        r = chay(KIEM_CA, b64, vt, "192.168.1.10")
        self.assertEqual(r.returncode, 1)
        self.assertIn("không có ràng buộc tên", r.stderr)

    def test_rang_buoc_lech_bi_tu_choi(self):
        for nc in ("critical,permitted;IP:192.168.1.10/255.255.255.0,permitted;DNS:anphu.onebee.internal",    # cả dải /24
                   "critical,permitted;IP:192.168.1.10/255.255.255.255,permitted;DNS:onebee.example.com",       # tên miền khác
                   "critical,permitted;IP:192.168.1.10/255.255.255.255,permitted;DNS:onebee.internal",          # không có nhãn mã đơn vị
                   "critical,permitted;IP:192.168.1.10/255.255.255.255,permitted;email:example.com",            # thêm loại tên khác
                   "critical,permitted;IP:192.168.1.10/255.255.255.255"):                                        # thiếu ràng buộc DNS
            b64, vt = self.ca_khac(nc)
            self.assertEqual(chay(KIEM_CA, b64, vt, "192.168.1.10").returncode, 1, nc)

    def test_ca_la_khong_phai_ca_bi_tu_choi(self):
        chay("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-keyout", f"{self.t}/l.key",
             "-subj", "/CN=la", "-days", "30", "-out", f"{self.t}/l.crt")
        b64, vt = der_b64(f"{self.t}/l.crt")
        self.assertEqual(chay(KIEM_CA, b64, vt, "192.168.1.10").returncode, 1)


class DocRangBuocNghiem(unittest.TestCase):
    """openssl in tên DNS nguyên văn kể cả xuống dòng → chứng chỉ có thể GIẢ dòng "Excluded:" trong một tên để giấu "DNS:com" rộng (PoC của rà soát Opus)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("kiem_ca", KIEM_CA)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)

    TIEU_DE = "X509v3 Basic Constraints: critical\n    CA:TRUE, pathlen:1\nX509v3 Name Constraints: critical\n"

    def doc(self, *dong):
        return self.m.rang_buoc_nghiem(self.TIEU_DE + "\n".join(dong) + "\n")

    def test_dung_dang(self):
        self.assertEqual(self.doc("    Permitted:", "      IP:10.0.0.1/255.255.255.255", "      DNS:anphu.onebee.internal"),
                         (["10.0.0.1/255.255.255.255"], ["anphu.onebee.internal"]))

    def test_gia_dong_excluded_de_giau_dns_com_bi_tu_choi(self):
        for dong in (("    Permitted:", "      IP:10.0.0.1/255.255.255.255", "      DNS:a.onebee.internal", " Excluded:", "      DNS:com"),
                     ("    Permitted:", "      DNS:a.onebee.internal", "    Excluded:", "      DNS:com"),     # mục Excluded thật cũng không nhận
                     ("    Permitted:", "      DNS:com"),
                     ("    Permitted:", "      DNS:a.onebee.internal", "      email:x@y"),
                     ("    Permitted:", "      DNS:onebee.internal"),
                     ("      DNS:a.onebee.internal",)):
            with self.assertRaises(SystemExit, msg=str(dong)):
                self.doc(*dong)

    def test_ky_tu_la_bi_tu_choi(self):
        with self.assertRaises(SystemExit):
            self.m.rang_buoc_nghiem(self.TIEU_DE + "    Permitted:\r\n      DNS:a.onebee.internal\x00\n")


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class ChinhSachTrinhDuyet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.g = self.tmp.name
        chay(TAO_CA, f"{self.g}/ca", "anphu", "192.168.1.10")
        self.pem = f"{self.g}/ca/root.crt"
        self.env = dict(os.environ, ONEBEE_GOC=f"{self.g}/goc")
        self.ff = f"{self.g}/goc/etc/firefox/policies/policies.json"
        self.goi = f"{self.g}/goc/usr/lib/firefox/distribution/policies.json"
        self.chrome = f"{self.g}/goc/etc/chromium/policies/managed/onebee-box.json"
        self.chrome2 = f"{self.g}/goc/etc/opt/chrome/policies/managed/onebee-box.json"

    def td(self, *a):
        r = subprocess.run([TRINH_DUYET, *a], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def dat_goi(self, nd):
        os.makedirs(os.path.dirname(self.goi))
        json.dump(nd, open(self.goi, "w"))

    def test_cai_khong_co_file_goi_roi_go_xoa_sach(self):
        self.assertEqual(self.td("cai", self.pem), "đã đổi")
        self.assertEqual(json.load(open(self.ff))["policies"]["Certificates"]["Install"], ["/usr/local/share/ca-certificates/onebee-box-ca.crt"])
        c = json.load(open(self.chrome))["CACertificatesWithConstraints"][0]
        self.assertEqual(c["constraints"], {"permitted_cidrs": ["192.168.1.10/32"], "permitted_dns_names": ["anphu.onebee.internal"]})
        self.assertTrue(os.path.exists(self.chrome2))
        self.assertEqual(self.td("cai", self.pem), "không đổi")   # chạy lại không đổi (changed=0)
        self.assertEqual(self.td("go"), "đã đổi")
        for p in (self.ff, self.chrome, self.chrome2):
            self.assertFalse(os.path.exists(p), p)
        self.assertEqual(self.td("go"), "không đổi")

    def test_https_dat_trang_chu_va_dau_trang_roi_go_tra_lai(self):
        goi = {"policies": {"DisableAppUpdate": True}}
        self.dat_goi(goi)
        self.assertEqual(self.td("cai", self.pem, "--https", "192.168.1.10"), "đã đổi")
        nd = json.load(open(self.ff))["policies"]
        self.assertEqual(nd["Homepage"]["URL"], "https://192.168.1.10/")
        urls = [b["url"] for b in nd["ManagedBookmarks"] if "url" in b]
        self.assertIn("https://192.168.1.10:3000/", urls)
        self.assertTrue(all(u.startswith("https://") for u in urls))
        self.assertNotIn("DisableSecurityBypass", nd)          # QĐ8: máy in/thiết bị LAN tự ký vẫn phải mở được
        self.assertNotIn("HttpsOnlyMode", nd)
        ch = json.load(open(self.chrome))
        self.assertEqual(ch["HomepageLocation"], "https://192.168.1.10/")
        self.assertEqual(ch["ManagedBookmarks"], nd["ManagedBookmarks"])
        self.assertEqual(self.td("cai", self.pem, "--https", "192.168.1.10"), "không đổi")
        self.td("go")
        self.assertEqual(json.load(open(self.ff)), goi)

    def test_tron_voi_file_cua_goi_firefox_va_tra_ve_nguyen_ven(self):
        goi = {"policies": {"DisableAppUpdate": True, "Certificates": {"ImportEnterpriseRoots": True, "Install": ["/etc/khac.crt"]}}}
        self.dat_goi(goi)
        self.td("cai", self.pem)
        nd = json.load(open(self.ff))["policies"]
        self.assertTrue(nd["DisableAppUpdate"])                                       # file /etc THAY file gói → phải giữ mục của gói
        self.assertTrue(nd["Certificates"]["ImportEnterpriseRoots"])
        self.assertEqual(nd["Certificates"]["Install"], ["/etc/khac.crt", "/usr/local/share/ca-certificates/onebee-box-ca.crt"])
        self.td("go")
        self.assertEqual(json.load(open(self.ff)), goi)                               # trả đúng nội dung gói, không còn mục OneBee

    def test_go_khi_chua_cai_gi_khong_loi_va_khong_dung_file_la(self):
        self.dat_goi({"policies": {"X": 1}})
        self.assertEqual(self.td("go"), "không đổi")
        self.assertFalse(os.path.exists(self.ff))


if __name__ == "__main__":
    unittest.main()
