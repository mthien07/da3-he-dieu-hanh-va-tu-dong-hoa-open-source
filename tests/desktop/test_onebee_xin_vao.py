#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử `onebee-xin-vao` (máy trạm xin vào OneBee Box). Box giả là máy chủ http.server trong Python làm đúng giao thức:
CA thật do box-stack/files/onebee-ca.sh sinh (Box giả KÝ cấu hình bằng khóa trung gian của CA đó rồi mới mã hóa), cam kết + mã đối chiếu tính độc lập bằng hashlib (không dùng lại hàm của script),
cấu hình gửi về mã hóa bằng `openssl cms -encrypt` thật. Mọi đường dẫn hệ thống đặt dưới ONEBEE_XIN_VAO_GOC.
Chạy: python3 -m unittest tests/desktop/test_onebee_xin_vao.py"""
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "../../desktop/onebee-xin-vao")
TAO_CA = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")
TIEN_TO = "onebee-xin-vao-v1"


def bam(s):
    return hashlib.sha256(s.encode()).hexdigest()


def chay_openssl(*a, du_lieu=None):
    return subprocess.run(["openssl", *a], input=du_lieu, capture_output=True, check=True).stdout


def van_tay_der(pem_path):
    return hashlib.sha256(chay_openssl("x509", "-in", pem_path, "-outform", "DER")).hexdigest()


def khoa_bam_cua(cert_pem_bytes):
    pub = chay_openssl("x509", "-noout", "-pubkey", du_lieu=cert_pem_bytes)
    return hashlib.sha256(chay_openssl("pkey", "-pubin", "-outform", "DER", du_lieu=pub)).hexdigest()


def ma_doi_chieu(b, kieu="6"):
    """Mã đối chiếu theo công thức của hợp đồng, tính độc lập từ dữ liệu Box giả đã thấy."""
    h = bam("|".join([TIEN_TO, "ma-so", b.id, b.khoa_bam, b.ca_van_tay, b.n_w, b.n_b]))
    return "%06d" % (int(h[:8], 16) % 1000000)


def nap_script():
    spec = importlib.util.spec_from_loader("onebee_xin_vao", importlib.machinery.SourceFileLoader("onebee_xin_vao", SCRIPT))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class BoxGia:
    """Box giả. `dong` = danh sách trạng thái trả lần lượt cho /ket-qua (dòng cuối lặp lại mãi). Các cờ ghi đè hành vi để thử tấn công."""

    def __init__(self, thu_muc, ca_pem, noi_dung_env=None, dong=("CHO_DUYET", "DA_CAP"), cam_ket_sai=False, ca_van_tay_tra_ve=None,
                 mo_409=False, loi_tu_choi="Quản trị từ chối", ma_hoa_cho_khoa_khac=False, khong_ky=False, ky_bang_ca=None,
                 dau_cau_hinh=None):
        self.thu_muc, self.ca_pem = thu_muc, ca_pem
        self.ca_van_tay = van_tay_der(ca_pem) if ca_pem else None
        self.noi_dung_env = noi_dung_env
        self.dong = list(dong)
        self.cam_ket_sai, self.ca_van_tay_tra_ve, self.mo_409 = cam_ket_sai, ca_van_tay_tra_ve, mo_409
        self.loi_tu_choi, self.ma_hoa_cho_khoa_khac = loi_tu_choi, ma_hoa_cho_khoa_khac
        self.khong_ky, self.ky_bang_ca = khong_ky, ky_bang_ca     # ky_bang_ca: thư mục CA khác dùng để ký (thử giả mạo)
        self.dau_cau_hinh = dau_cau_hinh                            # thay hai dòng XIN_VAO_ID / XIN_VAO_N_W (thử phát lại / sai yêu cầu)
        self.yeu_cau = []        # (đường dẫn, nội dung JSON) đã nhận
        self.id = secrets.token_hex(16)
        self.n_b = secrets.token_hex(16)
        self.n_w = self.khoa_bam = self.cert = None
        self.so_lan_ket_qua = 0
        self.da_mo = False
        box = self

        class XuLy(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def gui(self, ma, doi_tuong=None, du_lieu=None):
                nd = du_lieu if du_lieu is not None else json.dumps(doi_tuong).encode()
                self.send_response(ma)
                self.send_header("Content-Length", str(len(nd)))
                self.end_headers()
                self.wfile.write(nd)

            def do_GET(self):   # noqa: N802
                if self.path == "/onebee-ca.crt":
                    with open(box.ca_pem, "rb") as f:
                        return self.gui(200, du_lieu=f.read())
                return self.gui(404, {})

            def do_POST(self):   # noqa: N802
                nd = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                box.yeu_cau.append((self.path, nd))
                return getattr(box, "xu_ly_" + self.path.rsplit("/", 1)[1].replace("-", "_"), lambda h, n: h.gui(404, {}))(self, nd)

        self.may_chu = ThreadingHTTPServer(("127.0.0.1", 0), XuLy)
        self.cong = self.may_chu.server_address[1]
        threading.Thread(target=self.may_chu.serve_forever, daemon=True).start()

    def dong_lai(self):
        self.may_chu.shutdown()
        self.may_chu.server_close()

    # --- các điểm nhận ---
    def xu_ly_onebee_xin_vao(self, h, nd):
        self.cert = nd["cert"].encode()
        self.khoa_bam = khoa_bam_cua(self.cert)
        ck = bam("|".join([TIEN_TO, "cam-ket", self.id, self.khoa_bam, self.ca_van_tay, self.n_b]))
        if self.cam_ket_sai:
            ck = bam("khac")
        h.gui(200, {"id": self.id, "cam_ket": ck, "ca_van_tay": self.ca_van_tay_tra_ve or self.ca_van_tay})

    def xu_ly_onebee_xin_vao_mo(self, h, nd):
        if self.da_mo or self.mo_409:
            return h.gui(409, {"loi": "đã mở rồi"})
        self.da_mo, self.n_w = True, nd["n_w"]
        h.gui(200, {"n_b": self.n_b})

    def xu_ly_onebee_xin_vao_ket_qua(self, h, nd):
        tt = self.dong[min(self.so_lan_ket_qua, len(self.dong) - 1)]
        self.so_lan_ket_qua += 1
        if tt == "DA_CAP":
            return h.gui(200, {"trang_thai": "DA_CAP", "cms": self.ma_hoa()})
        if tt in ("TU_CHOI", "LOI"):
            return h.gui(200, {"trang_thai": tt, "loi": self.loi_tu_choi})
        h.gui(200, {"trang_thai": tt})

    def ma_hoa(self):
        cert = os.path.join(self.thu_muc, "nguoi-nhan.pem")
        if self.ma_hoa_cho_khoa_khac:   # mã hóa cho một chứng chỉ khác chứ không phải của máy trạm
            chay_openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=khac",
                         "-keyout", os.path.join(self.thu_muc, "khac.key"), "-out", cert)
        else:
            with open(cert, "wb") as f:
                f.write(self.cert)
        dau = self.dau_cau_hinh if self.dau_cau_hinh is not None else f"XIN_VAO_ID={self.id}\nXIN_VAO_N_W={self.n_w}\n"
        nd = (dau + (self.noi_dung_env if self.noi_dung_env is not None else self.env_dung())).encode()
        if not self.khong_ky:   # ký trước (không kèm chuỗi chứng chỉ), rồi mới mã hóa bản đã ký
            thu_muc_ca = self.ky_bang_ca or os.path.dirname(self.ca_pem)
            nd = chay_openssl("cms", "-sign", "-binary", "-nodetach", "-md", "sha256", "-signer", os.path.join(thu_muc_ca, "inter.crt"),
                              "-inkey", os.path.join(thu_muc_ca, "inter.key"), "-outform", "DER", du_lieu=nd)
        der = chay_openssl("cms", "-encrypt", "-binary", "-aes-256-gcm", "-outform", "DER", "-recip", cert,
                           "-keyopt", "rsa_padding_mode:oaep", "-keyopt", "rsa_oaep_md:sha256", du_lieu=nd)
        return base64.b64encode(der).decode()

    def env_dung(self, ten="kt-01", van_tay=None, them=""):
        return (f"MAY_TRAM={ten}\nBOX_IP=127.0.0.1\nRESTIC_PASSWORD=mat=khau=\nPHONG_BAN=ke-toan\nPHONG_BAN_TEN=\"Phòng Kế toán\"\n"
                f"BOX_CA_VAN_TAY={van_tay or self.ca_van_tay}\n{them}")


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class XinVao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goc_ca = tempfile.mkdtemp(prefix="xin-vao-ca-")
        r = subprocess.run([TAO_CA, f"{cls.goc_ca}/ca", "anphu", "127.0.0.1"], capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stderr
        cls.ca_pem = f"{cls.goc_ca}/ca/root.crt"
        r = subprocess.run([TAO_CA, f"{cls.goc_ca}/ca-la", "ketgia", "127.0.0.1"], capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.goc_ca, ignore_errors=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.goc = os.path.join(self.tmp.name, "goc")
        self.tam = os.path.join(self.tmp.name, "tam")   # TMPDIR của script: phải sạch sau khi chạy
        os.makedirs(self.goc)
        os.makedirs(self.tam)
        self.hop = []

    def box(self, **kw):
        b = BoxGia(self.tmp.name, kw.pop("ca_pem", self.ca_pem), **kw)
        self.addCleanup(b.dong_lai)
        return b

    def chay(self, b, *tham_so, dau_vao="", ma="tu-dong", script=SCRIPT, khong_cai=True):
        """Chạy onebee-xin-vao. `dau_vao`: các dòng gõ trước (vd tên máy). `ma`: "tu-dong" = gõ lại đúng mã đối chiếu (tính độc lập
        từ dữ liệu Box giả đã thấy, ngay khi Box mở xong bước 3); chuỗi khác = gõ chuỗi đó; None = không gõ gì (hết dữ liệu nhập)."""
        env = {**os.environ, "ONEBEE_XIN_VAO_GOC": self.goc, "TMPDIR": self.tam, "ONEBEE_XIN_VAO_CHU_KY": "0.05", "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("http_proxy", None)
        cmd = [sys.executable, script, "--box", f"127.0.0.1:{b.cong}", *(["--khong-cai"] if khong_cai else []), *tham_so]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)   # noqa: S603
        try:
            p.stdin.write(dau_vao)
            p.stdin.flush()
            cach = ma == "tu-dong-cach"
            if ma in ("tu-dong", "tu-dong-cach"):
                han = time.monotonic() + 60
                while b.n_w is None and p.poll() is None and time.monotonic() < han:
                    time.sleep(0.02)
                if b.n_w is not None:
                    ma = ma_doi_chieu(b)
                    ma = f"{ma[:3]} {ma[3:]}" if cach else ma
            if ma not in (None, "tu-dong", "tu-dong-cach"):
                p.stdin.write(ma + "\n")
                p.stdin.flush()
        except OSError:   # script đã thoát trước khi nhận mã (các ca dừng sớm)
            pass
        finally:
            try:
                p.stdin.close()
            except OSError:
                pass
            p.stdin = None   # để communicate() không flush lại ống đã đóng
        try:
            out, err = p.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
            raise
        return subprocess.CompletedProcess(cmd, p.returncode, out, err)

    def env_path(self):
        return os.path.join(self.goc, "etc/onebee/may-tram.env")

    def khong_ghi_gi(self, r):
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.env_path()))
        self.assertEqual(os.listdir(self.tam), [], "thư mục tạm chứa khóa riêng phải được xóa")

    # ---- luồng thành công ----
    def test_thanh_cong_ghi_env_dung_quyen_va_hien_ma_doi_chieu(self):
        b = self.box(dong=("CHO_DUYET", "DANG_CAP", "DA_CAP"), noi_dung_env=None)
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01", "--phong", "ke-toan")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Đã kết nối OneBee Box 127.0.0.1", r.stdout)
        self.assertIn("so đúng mã này rồi bấm Duyệt", r.stdout)
        # mã đối chiếu tính độc lập đúng công thức của hợp đồng
        ma = ma_doi_chieu(b)
        self.assertIn(f"{ma[:3]} {ma[3:]}", r.stdout)
        self.assertIn("gõ lại mã đó vào đây", r.stdout)
        # đã gửi đúng nội dung xin vào
        gui = dict(b.yeu_cau)["/webhook/onebee-xin-vao"]
        self.assertEqual((gui["ten"], gui["phong"]), ("kt-01", "ke-toan"))
        self.assertTrue(gui["cert"].startswith("-----BEGIN CERTIFICATE-----"))
        self.assertEqual(len(b.n_w), 32)
        # cấu hình
        with open(self.env_path(), encoding="utf-8") as f:
            nd = f.read()
        self.assertIn("MAY_TRAM=kt-01\n", nd)
        self.assertIn("RESTIC_PASSWORD=mat=khau=\n", nd)
        self.assertIn('PHONG_BAN_TEN="Phòng Kế toán"\n', nd)
        self.assertNotIn("XIN_VAO", nd, "hai dòng kiểm XIN_VAO_* không được ghi vào cấu hình")
        self.assertEqual(stat.S_IMODE(os.stat(self.env_path()).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(self.env_path())).st_mode), 0o700)
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.env_path()))), ["may-tram.env"])
        self.assertEqual(os.listdir(self.tam), [], "thư mục tạm chứa khóa riêng phải được xóa")

    def test_khong_co_phong_gui_null(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        self.assertEqual(self.chay(b, "--ten", "kt-01").returncode, 0)
        self.assertIsNone(dict(b.yeu_cau)["/webhook/onebee-xin-vao"]["phong"])

    def test_tep_cu_duoc_giu_sang_dau_ngoc(self):
        os.makedirs(os.path.dirname(self.env_path()))
        with open(self.env_path(), "w", encoding="utf-8") as f:
            f.write("MAY_TRAM=cu\nRESTIC_PASSWORD=cu\n")
        os.chmod(self.env_path(), 0o644)
        b = self.box()
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.env_path() + ".~", encoding="utf-8") as f:
            self.assertEqual(f.read(), "MAY_TRAM=cu\nRESTIC_PASSWORD=cu\n")
        self.assertEqual(stat.S_IMODE(os.stat(self.env_path() + ".~").st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.env_path()).st_mode), 0o600)
        with open(self.env_path(), encoding="utf-8") as f:
            self.assertIn("MAY_TRAM=kt-01\n", f.read())

    def test_dong_rac_bi_bo_dong_hop_le_duoc_giu(self):
        b = self.box()
        b.noi_dung_env = b.env_dung(them="rm -rf /\n$(touch /tmp/bi-chay)\n`id`\nchu_thuong=1\n KHOA_CO_DAU_CACH=1\nXAU=a\x01b\nKHOA9=1\n"
                                         "QUAN_TRI_SSH_KEY=\"ssh-ed25519 AAAA x\"\r\nHOI_URL=https://box/\n")
        r = self.chay(b, "--ten", "kt-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.env_path(), encoding="utf-8") as f:
            dong = f.read().splitlines()
        for rac in ("rm -rf /", "$(touch /tmp/bi-chay)", "`id`", "chu_thuong=1", " KHOA_CO_DAU_CACH=1", "XAU=a\x01b", "KHOA9=1"):
            self.assertNotIn(rac, dong)
        self.assertIn('QUAN_TRI_SSH_KEY="ssh-ed25519 AAAA x"', dong)   # \r cuối dòng được bỏ
        self.assertIn("HOI_URL=https://box/", dong)
        self.assertTrue(all(d.split("=")[0].replace("_", "").isalpha() and d.split("=")[0].isupper() for d in dong), dong)

    # ---- tấn công / sai lệch: phải dừng, không ghi gì ----
    def test_cam_ket_sai_thi_dung(self):
        r = self.chay(self.box(cam_ket_sai=True), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("máy giả mạo Box", r.stderr)
        self.assertNotIn("MÃ ĐỐI CHIẾU", r.stdout)

    def test_ca_van_tay_box_tra_ve_khac_thi_dung(self):
        r = self.chay(self.box(ca_van_tay_tra_ve="0" * 64), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("máy giả mạo Box", r.stderr)

    def test_van_tay_ca_trong_cau_hinh_lech_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung(van_tay="a" * 64)
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("Vân tay", r.stderr)

    def test_thieu_van_tay_ca_trong_cau_hinh_thi_dung(self):
        b = self.box()
        b.noi_dung_env = "MAY_TRAM=kt-01\nRESTIC_PASSWORD=x\n"
        self.khong_ghi_gi(self.chay(b, "--ten", "kt-01"))

    def test_may_tram_lech_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung(ten="may-khac")
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không dành cho máy 'kt-01'", r.stderr)

    def test_may_tram_hai_gia_tri_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung(them="MAY_TRAM=may-khac\n")
        self.khong_ghi_gi(self.chay(b, "--ten", "kt-01"))

    def test_ma_hoa_cho_khoa_khac_khong_giai_ma_duoc(self):
        r = self.chay(self.box(ma_hoa_cho_khoa_khac=True), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("Không giải mã được", r.stderr)

    def test_bi_tu_choi_in_ly_do_va_thoat_1(self):
        r = self.chay(self.box(dong=("CHO_DUYET", "TU_CHOI"), loi_tu_choi="Máy lạ, không biết"), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("Máy lạ, không biết", r.stderr)

    def test_loi_tu_box_in_ly_do_va_thoat_1(self):
        r = self.chay(self.box(dong=("LOI",), loi_tu_choi="Không cấp được khóa"), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("Không cấp được khóa", r.stderr)

    def test_yeu_cau_het_han_khong_co(self):
        r = self.chay(self.box(dong=("KHONG_CO",)), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không còn yêu cầu", r.stderr)

    def test_mo_lan_hai_409_thi_dung(self):
        r = self.chay(self.box(mo_409=True), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("409", r.stderr)

    def test_ca_khong_rang_buoc_ten_bi_tu_choi(self):
        khac = os.path.join(self.tmp.name, "ca-rong.crt")
        chay_openssl("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-keyout",
                     os.path.join(self.tmp.name, "ca-rong.key"), "-subj", "/CN=ca", "-days", "30",
                     "-addext", "basicConstraints=critical,CA:TRUE", "-out", khac)
        r = self.chay(self.box(ca_pem=khac), "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không phải CA OneBee", r.stderr)

    # ---- chữ ký của Box và kiểm đúng yêu cầu ----
    def test_cau_hinh_khong_ky_bi_tu_choi(self):
        b = self.box(khong_ky=True)
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không có chữ ký hợp lệ của Box", r.stderr)

    def test_cau_hinh_ky_bang_ca_khac_bi_tu_choi(self):
        b = self.box(ky_bang_ca=f"{self.goc_ca}/ca-la")
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không có chữ ký hợp lệ của Box", r.stderr)

    def test_xin_vao_id_lech_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        self.dat_dau_theo_yeu_cau(b, id_="0" * 32)
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không thuộc yêu cầu xin vào này", r.stderr)

    def test_xin_vao_n_w_lech_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        self.dat_dau_theo_yeu_cau(b, n_w="1" * 32)
        r = self.chay(b, "--ten", "kt-01")
        self.khong_ghi_gi(r)
        self.assertIn("không thuộc yêu cầu xin vào này", r.stderr)

    def test_thieu_hoac_trung_dong_xin_vao_thi_dung(self):
        for dau in ("", "XIN_VAO_ID={id}\n", "XIN_VAO_N_W={n_w}\n", "XIN_VAO_ID={id}\nXIN_VAO_ID={id}\nXIN_VAO_N_W={n_w}\n",
                    "XIN_VAO_ID={id}\nXIN_VAO_N_W={n_w}\nXIN_VAO_N_W={n_w}\n"):
            with self.subTest(dau=dau):
                b = self.box()
                b.noi_dung_env = b.env_dung()
                self.dat_dau_theo_yeu_cau(b, mau=dau)
                self.khong_ghi_gi(self.chay(b, "--ten", "kt-01"))

    def dat_dau_theo_yeu_cau(self, b, id_=None, n_w=None, mau=None):
        """Box giả ký hai dòng XIN_VAO_* theo ý muốn; n_w thật của máy chỉ biết lúc xử lý bước 3 nên dựng dòng khi ký."""
        goc_ma_hoa = b.ma_hoa

        def ma_hoa():
            b.dau_cau_hinh = (mau.format(id=b.id, n_w=b.n_w) if mau is not None
                              else f"XIN_VAO_ID={id_ or b.id}\nXIN_VAO_N_W={n_w or b.n_w}\n")
            return goc_ma_hoa()
        b.ma_hoa = ma_hoa

    # ---- bắt người dùng gõ lại mã ----
    def test_go_sai_ma_thi_dung_khong_cho_duyet(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01", ma="000000")
        self.khong_ghi_gi(r)
        self.assertIn("Mã gõ vào không khớp", r.stderr)
        self.assertEqual(b.so_lan_ket_qua, 0, "chưa gõ đúng mã thì không được hỏi kết quả")

    def test_go_ma_co_dau_cach_van_nhan(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        # gõ "123 456" như trên màn hình: bài tính mã rồi chèn dấu cách
        r = self.chay(b, "--ten", "kt-01", ma="tu-dong-cach")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_khong_nhap_gi_o_cau_hoi_ma_thi_dung(self):
        b = self.box()
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01", ma=None)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(b.so_lan_ket_qua, 0)
        self.assertFalse(os.path.exists(self.env_path()))

    # ---- tham số ----
    def test_ten_va_phong_sai_thoat_2(self):
        b = self.box()
        for tham_so in (["--ten", "KT-01"], ["--ten", "-kt"], ["--ten", "a" * 33], ["--ten", "kt_01"],
                        ["--ten", "kt-01", "--phong", "Ke-Toan"], ["--ten", "kt-01", "--phong", "k"], ["--ten", "kt-01", "--phong", "1ke"]):
            self.assertEqual(self.chay(b, *tham_so).returncode, 2, tham_so)
        self.assertEqual(b.yeu_cau, [], "tham số sai thì chưa được gọi Box")

    def test_box_dia_chi_la_thoat_2(self):
        b = self.box()
        r = subprocess.run([sys.executable, SCRIPT, "--box", "a b;rm", "--ten", "kt-01"], capture_output=True, text=True,
                           env={**os.environ, "ONEBEE_XIN_VAO_GOC": self.goc}, check=False)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(b.yeu_cau, [])

    def test_hoi_ten_may_khi_thieu_va_hoi_lai_khi_sai(self):
        b = self.box()
        b.noi_dung_env = b.env_dung(ten="kt-02")
        r = self.chay(b, dau_vao="Sai Ten\nkt-02\n")   # sau hai dòng tên, bài tự gõ thêm mã đối chiếu
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Tên chưa đúng", r.stdout)
        self.assertEqual(dict(b.yeu_cau)["/webhook/onebee-xin-vao"]["ten"], "kt-02")

    def test_thieu_ten_va_khong_hoi_duoc_thoat_2(self):
        r = self.chay(self.box(), dau_vao="", ma=None)
        self.assertEqual(r.returncode, 2)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "đang chạy bằng root")
    def test_khong_phai_root_thi_tu_choi(self):
        env = {k: v for k, v in os.environ.items() if k != "ONEBEE_XIN_VAO_GOC"}
        r = subprocess.run([sys.executable, SCRIPT, "--box", "127.0.0.1:1", "--ten", "kt-01"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("sudo", r.stderr)

    def test_box_khong_tra_loi_bao_loi_de_hieu(self):
        b = self.box()
        b.dong_lai()
        r = self.chay(b, "--ten", "kt-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Không nối được tới OneBee Box", r.stderr)

    # ---- bước cài ----
    def test_chay_onebee_install_canh_script_tru_khi_khong_cai(self):
        thu_muc = os.path.join(self.tmp.name, "bo-cai")
        os.makedirs(thu_muc)
        shutil.copy(SCRIPT, thu_muc + "/onebee-xin-vao")
        dau = os.path.join(self.tmp.name, "da-chay-cai")
        with open(thu_muc + "/onebee-install.sh", "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\ncp {self.goc}/etc/onebee/may-tram.env {dau}\nexit 7\n")
        os.chmod(thu_muc + "/onebee-install.sh", 0o755)
        b = self.box()
        b.noi_dung_env = b.env_dung()
        r = self.chay(b, "--ten", "kt-01", script=thu_muc + "/onebee-xin-vao", khong_cai=False)
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)    # mã thoát của bộ cài được chuyển tiếp
        self.assertTrue(os.path.exists(dau), "bộ cài phải thấy cấu hình đã ghi")

    def test_khong_cai_thi_khong_chay_bo_cai(self):
        thu_muc = os.path.join(self.tmp.name, "bo-cai2")
        os.makedirs(thu_muc)
        shutil.copy(SCRIPT, thu_muc + "/onebee-xin-vao")
        dau = os.path.join(self.tmp.name, "da-chay-cai2")
        with open(thu_muc + "/onebee-install.sh", "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\ntouch {dau}\n")
        os.chmod(thu_muc + "/onebee-install.sh", 0o755)
        b = self.box()
        b.noi_dung_env = b.env_dung()
        self.assertEqual(self.chay(b, "--ten", "kt-01", script=thu_muc + "/onebee-xin-vao").returncode, 0)
        self.assertFalse(os.path.exists(dau))


class HamThuanTuy(unittest.TestCase):
    def setUp(self):
        self.m = nap_script()

    def test_ma_so_dung_cong_thuc_va_dem_so_0(self):
        da_thay_so_0 = False
        for i in range(2000):
            n_b = "%032x" % i
            tham = ("a" * 32, "b" * 64, "c" * 64, "d" * 32, n_b)
            h = bam("|".join([TIEN_TO, "ma-so", *tham]))
            mong_doi = "%06d" % (int(h[:8], 16) % 1000000)
            self.assertEqual(self.m.ma_so(*tham), mong_doi)
            self.assertEqual(len(mong_doi), 6)
            da_thay_so_0 = da_thay_so_0 or mong_doi.startswith("0")
        self.assertTrue(da_thay_so_0, "phải có ca mã bắt đầu bằng 0 để kiểm việc đệm")

    def test_cam_ket_dung_cong_thuc(self):
        self.assertEqual(self.m.cam_ket_dung("i" * 32, "k" * 64, "c" * 64, "n" * 32), bam("onebee-xin-vao-v1|cam-ket|" + "i" * 32 + "|" + "k" * 64 + "|" + "c" * 64 + "|" + "n" * 32))

    def test_het_gio_cho_thi_bao_loi(self):
        b = BoxGia(tempfile.gettempdir(), None, dong=("CHO_DUYET",))
        self.addCleanup(b.dong_lai)
        with self.assertRaises(self.m.Loi) as ctx:
            self.m.cho_ket_qua(f"http://127.0.0.1:{b.cong}", "a" * 32, 0.0005, chu_ky=0.01)
        self.assertIn("Hết", str(ctx.exception))
        self.assertGreaterEqual(b.so_lan_ket_qua, 1)


if __name__ == "__main__":
    unittest.main()
