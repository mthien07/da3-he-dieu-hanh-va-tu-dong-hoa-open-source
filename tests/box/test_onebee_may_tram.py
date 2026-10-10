#!/usr/bin/env python3
"""Kiểm thử đơn vị cho báo cáo tình trạng máy trạm (box-fleet/files/onebee-may-tram.py). Chạy: python3 -m unittest"""
import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "may_tram", os.path.join(HERE, "../../box/ansible/roles/box-fleet/files/onebee-may-tram.py"))
mt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mt)


class DanhGia(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.tot = {"ten": "a", "nhan_luc": self.now - 600, "o_trong_phan_tram": 60, "cap_nhat_cho": 0,
                    "bao_mat_cho": 0, "can_khoi_dong_lai": False}

    def test_may_on(self):
        cb, tom = mt.danh_gia("a", 5, self.tot, self.now)
        self.assertEqual(cb, [])
        self.assertIn("sao lưu 5 giờ trước", tom)
        self.assertIn("đã cập nhật", tom)

    def test_chua_sao_luu_chua_bao(self):
        cb, _ = mt.danh_gia("a", None, None, self.now)
        self.assertEqual(len(cb), 2)
        self.assertIn("chưa từng sao lưu", cb[0])

    def test_cac_nguong(self):
        tt = dict(self.tot, nhan_luc=self.now - 3 * 86400, o_trong_phan_tram=5, bao_mat_cho=4, can_khoi_dong_lai=True)
        cb, _ = mt.danh_gia("a", 100, tt, self.now)
        chu = " | ".join(cb)
        for y in ("quá 3 ngày chưa sao lưu", "3 ngày không liên lạc", "ổ đĩa sắp đầy (còn 5%)",
                  "4 bản vá bảo mật", "cần khởi động lại"):
            self.assertIn(y, chu)

    def test_canh_bao_nhieu_tai_khoan_sudo(self):
        # Chủ trương: nhân viên không có sudo → chỉ 1 tài khoản (quản trị máy) là bình thường
        cb, _ = mt.danh_gia("a", 5, dict(self.tot, sudo_so=1), self.now)
        self.assertEqual(cb, [])
        cb, _ = mt.danh_gia("a", 5, dict(self.tot, sudo_so=3), self.now)
        self.assertEqual(len(cb), 1)
        self.assertIn("3 tài khoản có quyền sudo", cb[0])
        # máy chạy mã cũ (không có trường) hoặc dữ liệu sai kiểu: không báo nhầm
        for v in ({}, {"sudo_so": "abc"}, {"sudo_so": True}, {"sudo_so": None}):
            cb, _ = mt.danh_gia("a", 5, dict(self.tot, **v), self.now)
            self.assertEqual(cb, [], v)

    def test_du_lieu_la_khong_lam_hong(self):
        tt = dict(self.tot, o_trong_phan_tram="abc", cap_nhat_cho=True, can_khoi_dong_lai="true")
        cb, _ = mt.danh_gia("a", 1, tt, self.now)
        self.assertEqual(cb, [])  # chuỗi/boolean sai kiểu bị bỏ qua, không báo nhầm


def bao_cao_ky(bi_mat, ten, tt, nhan_luc=None, mat_khau="mat-khau-kho-ketoan-01", gui_luc=None):
    """Tạo file <ten>.json như n8n ghi cho báo cáo có chữ ký, và file bí mật may-<ten>-repo như Box lưu."""
    now = time.time()
    du_lieu = json.dumps(dict(tt, ten=ten, gui_luc=now if gui_luc is None else gui_luc))
    return {"ten": ten, "dinh_dang": 2, "du_lieu": du_lieu, "ky": mt.ky_bao_cao(mat_khau, du_lieu),
            "nhan_luc": now if nhan_luc is None else nhan_luc}


class ChuKy(unittest.TestCase):
    """Rà soát bảo mật F2: báo cáo có chữ ký suy từ mật khẩu kho sao lưu; n8n không giữ khóa → không giả được."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = self._tmp.name
        self.bi_mat = os.path.join(self.d, "bi-mat")
        self.tt_dir = os.path.join(self.d, "tt")
        os.makedirs(self.bi_mat)
        os.makedirs(self.tt_dir)
        with open(os.path.join(self.bi_mat, "may-ketoan-01-repo"), "w") as f:
            f.write("mat-khau-kho-ketoan-01\n")
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("ONEBEE_BI_MAT", "ONEBEE_DA_GHIM")])

    def ghi(self, ten, noi_dung):
        with open(os.path.join(self.tt_dir, f"{ten}.json"), "w") as f:
            json.dump(noi_dung, f)

    def doc(self, ten="ketoan-01"):
        return mt.doc_tinh_trang(self.tt_dir, ten, self.bi_mat)

    def kho(self, *ten, da_ghim=None):
        os.environ["ONEBEE_BI_MAT"] = self.bi_mat
        if da_ghim is not None:
            os.environ["ONEBEE_DA_GHIM"] = da_ghim
        buf = io.StringIO()
        with redirect_stdout(buf):
            mt.main(["x", "kho", self.tt_dir, *ten])
        return buf.getvalue()

    def test_vector_chu_ky_co_dinh(self):
        # Giá trị cố định, đã đối chiếu độc lập bằng openssl: K = HMAC-SHA256(khóa=mật khẩu, "onebee-tinh-trang-v1"), chữ ký = HMAC-SHA256(K, dữ liệu).
        # Đổi cách ký là phá tương thích với mọi máy trạm đã cài → test này phải đỏ. Mã máy trạm có cùng vector (tests/desktop).
        self.assertEqual(mt.ky_bao_cao("mat-khau", '{"a": 1}'), "74a539bdbbb008e1811d060d2cce3a6685b0673d55d18df3cfe18fb1eca665b5")
        self.assertEqual(mt.ky_bao_cao("Mật khẩu có dấu 123", '{"ten": "a"}'),
                         "f58ed6c936281dcd7a5152a1cd38c078dcbbcc69de140788f8c4ba3f9181c569")
        self.assertNotEqual(mt.ky_bao_cao("mat-khau", "x"), mt.ky_bao_cao("mat-khau-khac", "x"))

    def test_hop_le(self):
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "192.168.1.9", "cap_nhat_cho": 3}))
        tt = self.doc()
        self.assertEqual(tt["_ky"], "hop-le")
        self.assertEqual((tt["ip"], tt["cap_nhat_cho"]), ("192.168.1.9", 3))

    def test_sai_mat_khau_sua_noi_dung_ten_lech_dong_ho(self):
        now = time.time()
        # 1) ký bằng mật khẩu khác (máy giả / n8n bị chiếm không biết mật khẩu kho)
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {}, mat_khau="doan-mo"))
        self.assertEqual(self.doc()["_ky"], "sai")
        # 2) sửa nội dung sau khi ký (đổi IP)
        bc = bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "192.168.1.9"})
        bc["du_lieu"] = bc["du_lieu"].replace("192.168.1.9", "10.0.0.66")
        self.ghi("ketoan-01", bc)
        self.assertEqual(self.doc()["_ky"], "sai")
        # 3) báo cáo của máy khác đặt vào file ketoan-01 (khóa đúng của máy khác, tên trong dữ liệu khác)
        bc = bao_cao_ky(self.bi_mat, "kho-02", {}, mat_khau="mat-khau-kho-ketoan-01")
        bc["ten"] = "ketoan-01"
        self.ghi("ketoan-01", bc)
        self.assertEqual(self.doc()["_ky"], "sai")
        # 4) phát lại báo cáo cũ (hoặc đồng hồ máy sai): chữ ký đúng nhưng giờ ký cách giờ Box nhận quá 10 phút → nhãn riêng,
        #    giờ báo cáo = giờ KÝ (không trông như vừa gửi) và không đủ tin để chọn IP máy chưa ghim
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {}, gui_luc=now - 3600, nhan_luc=now))
        tt = self.doc()
        self.assertEqual(tt["_ky"], "lech-gio")
        self.assertAlmostEqual(tt["nhan_luc"], now - 3600, delta=5)
        cb, _ = mt.danh_gia("ketoan-01", 5, dict(tt, o_trong_phan_tram=50, cap_nhat_cho=0), now)
        self.assertTrue(any("lệch giờ" in c for c in cb))
        # 5) máy chưa cấp (không có file mật khẩu) → không kiểm được → sai
        self.ghi("la-hoac", bao_cao_ky(self.bi_mat, "la-hoac", {}))
        self.assertEqual(self.doc("la-hoac")["_ky"], "sai")

    def test_bao_cao_cu_khong_chu_ky(self):
        self.ghi("ketoan-01", {"ten": "ketoan-01", "ip": "192.168.1.9", "nhan_luc": time.time()})
        self.assertEqual(self.doc()["_ky"], "chua-ky")

    def test_canh_bao_sai_va_chua_ky(self):
        cb, _ = mt.danh_gia("a", 5, {"ten": "a", "_ky": "sai"}, time.time())
        self.assertTrue(any("sai chữ ký" in c for c in cb))
        cb, _ = mt.danh_gia("a", 5, {"ten": "a", "nhan_luc": time.time(), "o_trong_phan_tram": 50, "cap_nhat_cho": 0,
                                       "_ky": "chua-ky"}, time.time())
        self.assertTrue(any("chưa có chữ ký" in c for c in cb))
        cb, _ = mt.danh_gia("a", 5, {"ten": "a", "nhan_luc": time.time(), "o_trong_phan_tram": 50, "cap_nhat_cho": 0,
                                       "_ky": "hop-le"}, time.time())
        self.assertEqual(cb, [])

    def test_kho_may_chua_ghim_chi_tin_bao_cao_co_chu_ky(self):
        self.ghi("ketoan-01", {"ten": "ketoan-01", "ip": "192.168.1.9", "nhan_luc": time.time()})  # báo cáo cũ, không ký
        self.assertEqual(self.kho("ketoan-01", da_ghim=""), "")
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "192.168.1.9"}))
        self.assertEqual(self.kho("ketoan-01", da_ghim=""), "ketoan-01 192.168.1.9 chua-ghim\n")
        # có chữ ký nhưng đã cũ hơn 2 giờ: IP có thể đã sang máy khác
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "192.168.1.9"},
                                         gui_luc=time.time() - 3 * 3600, nhan_luc=time.time() - 3 * 3600))
        self.assertEqual(self.kho("ketoan-01", da_ghim=""), "")

    def test_kho_may_da_ghim_tin_ip_30_ngay_tru_bao_cao_sai_chu_ky(self):
        cu = time.time() - 10 * 86400
        self.ghi("ketoan-01", {"ten": "ketoan-01", "ip": "192.168.1.9", "nhan_luc": cu})  # báo cáo cũ không ký, 10 ngày trước
        self.assertEqual(self.kho("ketoan-01", da_ghim="ketoan-01"), "ketoan-01 192.168.1.9 ghim\n")
        self.ghi("ketoan-01", {"ten": "ketoan-01", "ip": "192.168.1.9", "nhan_luc": time.time() - 40 * 86400})
        self.assertEqual(self.kho("ketoan-01", da_ghim="ketoan-01"), "")  # quá 30 ngày
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "10.0.0.66"}, mat_khau="doan-mo"))
        self.assertEqual(self.kho("ketoan-01", da_ghim="ketoan-01"), "")  # sai chữ ký → bỏ

    def test_kho_tu_choi_khi_thieu_moi_truong(self):
        # Mặc định ĐÓNG: thiếu ONEBEE_BI_MAT/ONEBEE_DA_GHIM thì không bao giờ tin IP chưa kiểm
        self.ghi("a", {"ten": "a", "ip": "192.168.1.9", "nhan_luc": time.time() - 600})
        for k in ("ONEBEE_BI_MAT", "ONEBEE_DA_GHIM"):
            os.environ.pop(k, None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(mt.main(["x", "kho", self.tt_dir, "a"]), 2)
        self.assertEqual(buf.getvalue(), "")
        os.environ["ONEBEE_BI_MAT"] = self.bi_mat       # có một biến thôi cũng chưa đủ
        self.assertEqual(mt.main(["x", "kho", self.tt_dir, "a"]), 2)

    def test_kho_may_chua_ghim_voi_chu_ky_lech_gio_khong_dung_duoc(self):
        now = time.time()
        self.ghi("ketoan-01", bao_cao_ky(self.bi_mat, "ketoan-01", {"ip": "192.168.1.9"}, gui_luc=now - 3600, nhan_luc=now))
        self.assertEqual(self.kho("ketoan-01", da_ghim=""), "")


class DocFile(unittest.TestCase):
    def setUp(self):
        self._bm = tempfile.TemporaryDirectory()
        self.addCleanup(self._bm.cleanup)
        os.environ["ONEBEE_BI_MAT"], os.environ["ONEBEE_DA_GHIM"] = self._bm.name, "a,c,cu,moi"   # đã ghim: báo cáo cũ không ký được dùng IP
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("ONEBEE_BI_MAT", "ONEBEE_DA_GHIM")])

    def test_bo_qua_file_sai_ten_va_ten_khong_hop_le(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.json"), "w") as f:
                json.dump({"ten": "b", "ip": "10.0.0.5"}, f)  # file a.json nhưng ghi tên b → bỏ
            with open(os.path.join(d, "c.json"), "w") as f:
                json.dump({"ten": "c", "ip": "10.0.0.7; rm -rf /"}, f)
            self.assertIsNone(mt.doc_tinh_trang(d, "a"))
            buf = io.StringIO()
            with redirect_stdout(buf):
                mt.main(["x", "kho", d, "a", "c", "../c"])
            self.assertEqual(buf.getvalue(), "")  # IP bậy không lọt vào danh sách máy để SSH

    def test_kho_may_da_ghim_bo_bao_cao_qua_30_ngay(self):
        with tempfile.TemporaryDirectory() as d:
            for ten, tuoi in (("moi", 600), ("cu", 40 * 86400)):
                with open(os.path.join(d, f"{ten}.json"), "w") as f:
                    json.dump({"ten": ten, "ip": "192.168.1.9", "nhan_luc": time.time() - tuoi}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                mt.main(["x", "kho", d, "moi", "cu"])
            self.assertEqual(buf.getvalue(), "moi 192.168.1.9 ghim\n")

    def test_loi_doc_kho_khac_chua_sao_luu(self):
        rows = mt.tong_hop("/khong-co", ["a=loi", "b=null", "c=-5000"])
        self.assertIn("không đọc được kho", rows[0]["canh_bao"][0])
        self.assertIn("chưa từng sao lưu", rows[1]["canh_bao"][0])
        self.assertIn("ngày tương lai", rows[2]["canh_bao"][0])  # bản giả mạo không được coi là "vừa sao lưu"

    def test_payload_thu_khong_doc_may(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            mt.main(["x", "payload", "/khong-co", "THU", "nd", "a=5"])
        self.assertEqual(json.loads(buf.getvalue())["may_tram"], [])


if __name__ == "__main__":
    unittest.main()
