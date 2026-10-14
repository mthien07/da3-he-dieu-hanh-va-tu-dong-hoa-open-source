#!/usr/bin/env python3
"""Kiểm thử role ket-noi-box: kiểm CA (vân tay + ràng buộc tên) và chính sách trình duyệt (Firefox/Chromium) cài, gỡ, trộn với file của gói.
Dùng CA thật do box-stack/files/onebee-ca.sh sinh. Chạy: python3 -m unittest"""
import base64
import hashlib
import json
import os
import re
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

    def ho_so_firefox(self, duong_dan, *chung_chi):
        """Hồ sơ Firefox giả (cert9.db thật, tạo bằng certutil) đã nạp sẵn các chứng chỉ (tên, file PEM)."""
        hs = f"{self.g}/goc/{duong_dan}"
        os.makedirs(hs)
        self.assertEqual(chay("certutil", "-N", "-d", f"sql:{hs}", "--empty-password").returncode, 0)
        for ten, pem in chung_chi:
            r = chay("certutil", "-A", "-n", ten, "-t", "C,,", "-i", pem, "-d", f"sql:{hs}")
            self.assertEqual(r.returncode, 0, r.stderr)
        return hs

    def van_tay_trong_ho_so(self, hs):
        """{tên: [vân tay SHA-256 của từng chứng chỉ mang tên đó]}"""
        kq = {}
        for dong in chay("certutil", "-L", "-d", f"sql:{hs}").stdout.splitlines()[4:]:
            ten = re.sub(r"\s+[A-Za-z]*,[A-Za-z]*,[A-Za-z]*\s*$", "", dong)
            if ten and ten not in kq:
                pem = chay("certutil", "-L", "-d", f"sql:{hs}", "-n", ten, "-a").stdout
                kq[ten] = sorted(hashlib.sha256(base64.b64decode(k)).hexdigest()
                                 for k in re.findall(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem, re.S))
        return kq

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_xoay_ca_go_ca_cu_khoi_ho_so_firefox_theo_van_tay(self):
        """Xoay CA (nghi lộ khóa) mà mã đơn vị giữ nguyên: CA mới trùng tên CA cũ; Firefox không tự gỡ CA đã nạp vào cert9.db → vẫn tin CA cũ."""
        chay(TAO_CA, f"{self.g}/ca-cu", "anphu", "192.168.1.10")
        _, vt_cu = der_b64(f"{self.g}/ca-cu/root.crt")
        _, vt_moi = der_b64(self.pem)
        ten = "OneBee Box anphu Root CA"
        chay("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-keyout", f"{self.g}/in.key",
             "-subj", "/CN=May in van phong", "-days", "30", "-out", f"{self.g}/may-in.crt")
        hs1 = self.ho_so_firefox("home/nv/.mozilla/firefox/abc.default-release", (ten, f"{self.g}/ca-cu/root.crt"),
                                 ("May in van phong", f"{self.g}/may-in.crt"))
        hs2 = self.ho_so_firefox("root/.mozilla/firefox/xyz.default", (ten, f"{self.g}/ca-cu/root.crt"))
        dau = f"{self.g}/goc/var/lib/onebee/ket-noi-box"           # vân tay CA đã cài lần trước (role ghi sau mỗi lần cài)
        os.makedirs(os.path.dirname(dau))
        open(dau, "w").write(vt_cu + "\n")
        ra = self.td("cai", self.pem)
        self.assertTrue(ra.endswith("đã đổi"), ra)
        for hs in (hs1, hs2):
            self.assertNotIn(vt_cu, sum(self.van_tay_trong_ho_so(hs).values(), []), hs)
        self.assertIn("May in van phong", self.van_tay_trong_ho_so(hs1))                    # chứng chỉ khác giữ nguyên
        # Firefox mở lại: chính sách nạp CA mới (cùng tên) → hồ sơ chỉ còn CA mới; chạy lại không gỡ nhầm nó
        self.assertEqual(chay("certutil", "-A", "-n", ten, "-t", "C,,", "-i", self.pem, "-d", f"sql:{hs1}").returncode, 0)
        self.assertEqual(self.td("cai", self.pem), "không đổi")
        self.assertEqual(self.van_tay_trong_ho_so(hs1)[ten], [vt_moi])
        self.assertTrue(self.td("go").endswith("đã đổi"))                                     # bỏ CA: gỡ mọi bản OneBee, giữ chứng chỉ khác
        self.assertEqual(list(self.van_tay_trong_ho_so(hs1)), ["May in van phong"])

    def tao_ca_cung_ma(self, ten_thu_muc, ma="anphu"):
        """CA thật khác (khóa khác) nhưng cùng mã đơn vị → cùng tên 'OneBee Box <mã> Root CA'; trả (file PEM, vân tay)."""
        chay(TAO_CA, f"{self.g}/{ten_thu_muc}", ma, "192.168.1.10")
        pem = f"{self.g}/{ten_thu_muc}/root.crt"
        return pem, der_b64(pem)[1]

    def them_vao_ho_so(self, hs, ten, pem):
        r = chay("certutil", "-A", "-n", ten, "-t", "C,,", "-i", pem, "-d", f"sql:{hs}")
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_ca_cu_con_sot_du_dau_van_tay_da_la_ca_moi_van_bi_go(self):
        """Lần xoay trước gỡ sót (thiếu certutil, đĩa chưa gắn…) nhưng role đã ghi vân tay CA mới → CA cũ không được ở lại mãi."""
        ten = "OneBee Box anphu Root CA"
        cu, vt_cu = self.tao_ca_cung_ma("ca-cu")
        _, vt_moi = der_b64(self.pem)
        hs = self.ho_so_firefox("home/nv/.mozilla/firefox/abc.default-release", (ten, cu), (ten, self.pem))
        self.assertEqual(sorted(self.van_tay_trong_ho_so(hs)[ten]), sorted([vt_cu, vt_moi]))   # tiền đề: hai bản cùng tên cùng tồn tại
        dau = f"{self.g}/goc/var/lib/onebee/ket-noi-box"
        os.makedirs(os.path.dirname(dau))
        open(dau, "w").write(vt_moi + "\n")                                                    # dấu đã là CA mới
        ra = self.td("cai", self.pem)
        self.assertIn("Đã gỡ 1 chứng chỉ", ra)                                                 # chỉ đếm bản CA cũ, không đếm CA mới
        self.assertTrue(ra.endswith("đã đổi"), ra)
        self.assertNotIn(vt_cu, sum(self.van_tay_trong_ho_so(hs).values(), []))
        self.assertEqual(self.td("cai", self.pem), "không đổi")                                # chạy lại không đổi (changed=0)

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_xoay_lien_tiep_ca1_ca2_deu_bi_go_khi_cai_ca3_khong_can_dau(self):
        """CA1 → CA2 → CA3: dấu chỉ nhớ một vân tay, nên việc gỡ phải theo vân tay CA hiện tại, không theo dấu."""
        ten = "OneBee Box anphu Root CA"
        ca1, vt1 = self.tao_ca_cung_ma("ca1")
        ca2, vt2 = self.tao_ca_cung_ma("ca2")
        hs = self.ho_so_firefox("home/nv/.mozilla/firefox/abc.default-release", (ten, ca1), (ten, ca2), ("May in van phong", self.pem))
        self.assertEqual(self.td("cai", self.pem).splitlines()[0], "Đã gỡ 2 chứng chỉ OneBee mang vân tay CA cũ khỏi hồ sơ Firefox")
        con_lai = sum(self.van_tay_trong_ho_so(hs).values(), [])
        self.assertNotIn(vt1, con_lai)
        self.assertNotIn(vt2, con_lai)
        self.assertIn("May in van phong", self.van_tay_trong_ho_so(hs))
        self.assertEqual(self.td("cai", self.pem), "không đổi")

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_dem_chi_tinh_chung_chi_khong_phai_ca_hien_tai(self):
        ten = "OneBee Box anphu Root CA"
        cu, vt_cu = self.tao_ca_cung_ma("ca-cu")
        hs1 = self.ho_so_firefox("home/nv/.mozilla/firefox/a.default", (ten, cu), (ten, self.pem))
        hs2 = self.ho_so_firefox("home/nv2/.mozilla/firefox/b.default", (ten, cu))
        hs3 = self.ho_so_firefox("root/.mozilla/firefox/c.default", (ten, self.pem))   # chỉ có CA hiện tại: không gỡ gì
        ra = self.td("cai", self.pem)
        self.assertIn("Đã gỡ 2 chứng chỉ", ra)                                          # đúng 2 bản CA cũ (hs1, hs2), không cộng CA mới lỡ bị xóa theo
        for hs in (hs1, hs2, hs3):
            self.assertNotIn(vt_cu, sum(self.van_tay_trong_ho_so(hs).values(), []), hs)
        self.assertEqual(self.van_tay_trong_ho_so(hs3)[ten], [der_b64(self.pem)[1]])

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_ca_cua_don_vi_khac_trong_ho_so_khong_bi_dong_den(self):
        """Hồ sơ của kỹ thuật viên có thể nạp CA của đơn vị khác (tên khác) — chỉ dọn CA cũ cùng tên CA hiện tại."""
        ten, ten_khac = "OneBee Box anphu Root CA", "OneBee Box khac Root CA"
        cu, vt_cu = self.tao_ca_cung_ma("ca-cu")
        khac, vt_khac = self.tao_ca_cung_ma("ca-khac", "khac")
        hs = self.ho_so_firefox("home/nv/.mozilla/firefox/abc.default-release", (ten, cu), (ten_khac, khac))
        self.td("cai", self.pem)
        con_lai = self.van_tay_trong_ho_so(hs)
        self.assertEqual(con_lai.get(ten_khac), [vt_khac])
        self.assertNotIn(vt_cu, con_lai.get(ten, []))

    @unittest.skipUnless(shutil.which("certutil"), "cần certutil (libnss3-tools)")
    def test_lan_dau_cai_khong_dung_ho_so_firefox(self):
        hs = self.ho_so_firefox("home/nv/.mozilla/firefox/abc.default-release", ("OneBee Box anphu Root CA", self.pem))
        self.assertEqual(self.td("cai", self.pem), "đã đổi")                               # chưa có dấu vân tay cũ → không gỡ gì
        self.assertIn("OneBee Box anphu Root CA", self.van_tay_trong_ho_so(hs))

    def test_go_khi_chua_cai_gi_khong_loi_va_khong_dung_file_la(self):
        self.dat_goi({"policies": {"X": 1}})
        self.assertEqual(self.td("go"), "không đổi")
        self.assertFalse(os.path.exists(self.ff))


if __name__ == "__main__":
    unittest.main()
