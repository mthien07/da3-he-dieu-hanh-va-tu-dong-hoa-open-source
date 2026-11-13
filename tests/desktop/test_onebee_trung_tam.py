#!/usr/bin/env python3
"""Kiểm thử phần logic của Trung tâm OneBee (onebee-trung-tam): đọc cẩm nang phím tắt, đọc thông tin đơn vị, dấu "đã xem"
của lần đăng nhập đầu, 6 ô của trang Bắt đầu, tham số dòng lệnh. Phần logic không cần GTK nên test chạy được cả trên máy
không có màn hình (macOS, CI lint); giao diện thật được kiểm trong container Linux Mint.
Chạy: python3 -m unittest tests/desktop/test_onebee_trung_tam.py"""
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TRUNG_TAM = os.path.join(HERE, "../../desktop/ansible/roles/trung-tam/files/onebee-trung-tam")
CAM_NANG = os.path.join(HERE, "../../desktop/ansible/roles/theme/files/onebee-cam-nang.json")
TEP_CHIA_SE = "/usr/share/applications/onebee-chia-se-noi-bo.desktop"


def nap_trung_tam():
    spec = importlib.util.spec_from_loader("onebee_trung_tam", importlib.machinery.SourceFileLoader("onebee_trung_tam", TRUNG_TAM))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TrungTamOneBee(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tt = nap_trung_tam()

    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)

    def ghi(self, ten, noi_dung):
        duong_dan = os.path.join(self.tam.name, ten)
        with open(duong_dan, "w", encoding="utf-8") as f:
            f.write(noi_dung)
        return duong_dan

    def test_nap_duoc_khong_can_gtk(self):
        # sys.modules["gi"] = None: mọi lệnh `import gi` sẽ lỗi ImportError
        with mock.patch.dict(sys.modules, {"gi": None}):
            m = nap_trung_tam()
            self.assertIsNone(sys.modules["gi"], "nạp module không được import gi")
        self.assertTrue(callable(m.chay_giao_dien))
        self.assertEqual([ma for ma, _ in m.TRANG], ["bat-dau", "phim-tat", "tro-giup"])

    def test_nhom_phim_tat_dung_thu_tu_va_du_muc(self):
        cam_nang = self.tt.doc_cam_nang(CAM_NANG)
        self.assertIsNotNone(cam_nang, "phải đọc được cẩm nang thật")
        nhom = self.tt.nhom_phim_tat(cam_nang)
        self.assertEqual([(n["ma"], n["ten"]) for n in nhom], [
            ("go-tieng-viet", "Gõ tiếng Việt"),
            ("man-hinh", "Màn hình và cửa sổ"),
            ("chup", "Chụp màn hình"),
            ("soan-thao", "Soạn thảo"),
        ])
        with open(CAM_NANG, encoding="utf-8") as f:
            so_muc = len(json.load(f)["phim_tat"])
        self.assertEqual(sum(len(n["muc"]) for n in nhom), so_muc)
        for n in nhom:
            for muc in n["muc"]:
                self.assertEqual(muc["nhom"], n["ma"], f"{muc['ma']} nằm sai nhóm")

    def test_cam_nang_thieu_hoac_hong_thi_rong(self):
        self.assertIsNone(self.tt.doc_cam_nang(os.path.join(self.tam.name, "khong-co.json")))
        self.assertIsNone(self.tt.doc_cam_nang(self.ghi("hong.json", "abc")))
        self.assertEqual(self.tt.nhom_phim_tat(None), [])

    def test_lan_dau_chi_hien_mot_lan(self):
        thu_muc = os.path.join(self.tam.name, "cau-hinh")
        self.assertTrue(self.tt.can_hien_lan_dau(thu_muc))
        self.tt.danh_dau_da_xem(thu_muc)
        self.assertFalse(self.tt.can_hien_lan_dau(thu_muc))
        self.assertTrue(os.path.isfile(os.path.join(thu_muc, "onebee", "trung-tam-da-xem")))
        # Đánh dấu lần hai không lỗi, vẫn là đã xem
        self.tt.danh_dau_da_xem(thu_muc)
        self.assertFalse(self.tt.can_hien_lan_dau(thu_muc))

    def test_sau_o_bat_dau(self):
        tep_da_hoi = []

        def co_tep(duong_dan):
            tep_da_hoi.append(duong_dan)
            return duong_dan != TEP_CHIA_SE

        o = self.tt.cac_o_bat_dau(lambda lenh: True, co_tep)
        self.assertEqual([x["ma"] for x in o],
                         ["soan-van-ban", "bang-tinh", "thu-muc-cua-toi", "thu-muc-chung", "tro-ly-ai", "can-giup-do"])
        self.assertIn(TEP_CHIA_SE, tep_da_hoi)
        theo_ma = {x["ma"]: x for x in o}
        self.assertFalse(theo_ma["thu-muc-chung"]["co_san"])
        self.assertIn("chưa nối OneBee Box", theo_ma["thu-muc-chung"]["ly_do"])
        for ma, x in theo_ma.items():
            self.assertTrue(x["ten"] and x["mo_ta"] and x["bieu_tuong"], f"{ma} thiếu tên, mô tả hoặc biểu tượng")
            if ma != "thu-muc-chung":
                self.assertTrue(x["co_san"], f"{ma} phải có sẵn khi đủ lệnh")
        self.assertEqual(theo_ma["soan-van-ban"]["lenh"], ["libreoffice", "--writer"])
        self.assertEqual(theo_ma["bang-tinh"]["lenh"], ["libreoffice", "--calc"])
        self.assertEqual(theo_ma["thu-muc-chung"]["lenh"], ["gtk-launch", "onebee-chia-se-noi-bo"])
        self.assertEqual(theo_ma["tro-ly-ai"]["lenh"], ["onebee-mo-tro-ly-ai"])
        self.assertEqual(theo_ma["thu-muc-cua-toi"]["lenh"][0], "xdg-open")
        self.assertEqual(theo_ma["can-giup-do"]["trang"], "tro-giup")

        # Thiếu lệnh: ô cần lệnh đó không có sẵn và nêu lý do; ô "luôn có" vẫn có sẵn
        thieu = {x["ma"]: x for x in self.tt.cac_o_bat_dau(lambda lenh: False, lambda duong_dan: True)}
        for ma in ("soan-van-ban", "bang-tinh", "tro-ly-ai"):
            self.assertFalse(thieu[ma]["co_san"], ma)
            self.assertTrue(thieu[ma]["ly_do"], ma)
        for ma in ("thu-muc-cua-toi", "thu-muc-chung", "can-giup-do"):
            self.assertTrue(thieu[ma]["co_san"], ma)

    def test_doc_don_vi(self):
        so = "0777 794 089"
        self.assertEqual(self.tt.doc_don_vi(self.ghi("don-vi.json", json.dumps({"dien_thoai_ho_tro": so}))), so)
        self.assertEqual(self.tt.doc_don_vi(os.path.join(self.tam.name, "khong-co.json")), "")
        self.assertEqual(self.tt.doc_don_vi(self.ghi("hong.json", "abc")), "")
        self.assertEqual(self.tt.doc_don_vi(self.ghi("so.json", json.dumps({"dien_thoai_ho_tro": 777794089}))), "")
        self.assertEqual(self.tt.doc_don_vi(self.ghi("mang.json", json.dumps(["0777 794 089"]))), "")

    def test_tham_so(self):
        lan_dau = self.tt.doc_tham_so(["--lan-dau"])
        self.assertEqual(lan_dau.che_do, "lan-dau")
        trang = self.tt.doc_tham_so(["--trang", "phim-tat"])
        self.assertEqual((trang.che_do, trang.trang), ("binh-thuong", "phim-tat"))
        self.assertEqual(self.tt.doc_tham_so(["--tu-kiem"]).che_do, "tu-kiem")
        mac_dinh = self.tt.doc_tham_so([])
        self.assertEqual((mac_dinh.che_do, mac_dinh.trang), ("binh-thuong", "bat-dau"))
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as loi:
                self.tt.doc_tham_so(["--trang", "khong-co-trang-nay"])
        self.assertEqual(loi.exception.code, 64)


if __name__ == "__main__":
    unittest.main()
