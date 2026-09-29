"""Kiểm thử đơn vị cho công cụ chấm (không cần model): python3 -m unittest tests/ai/test_scoring_and_report.py"""
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onebee_ai_eval.report import summarize  # noqa: E402
from onebee_ai_eval.scoring import normalize, score_answer  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "bo-cau-hoi-tieng-viet.yaml"), encoding="utf-8") as f:
    BO = yaml.safe_load(f)
Q = {q["id"]: q for q in BO["cau_hoi"]}


class TestScoring(unittest.TestCase):
    def test_bo_cau_hoi_du_40_cau_5_nhom(self):
        self.assertEqual(len(Q), 40)
        self.assertEqual(sorted({q["nhom"] for q in Q.values()}), [1, 2, 3, 4, 5])

    def test_moi_dap_an_la_chuoi_khong_bi_yaml_doi_kieu(self):
        # YAML hiểu 7:30 là số 450 và tách "1,26 tỷ" thành 2 phần tử nếu không đặt trong ngoặc kép
        for q in Q.values():
            for alts in q["bat_buoc"]:
                for a in alts:
                    self.assertIsInstance(a, str, q["id"])
                    self.assertGreater(len(a), 1, q["id"])

    def test_normalize_giu_dau_va_gom_kieu_dat_dau(self):
        self.assertEqual(normalize("Cộng Hoà  XÃ"), "cộng hòa xã")

    def test_dat_du_y(self):
        r = score_answer(Q["n4-02"], "Siêu thị A trả 15.000.000 + 7.500.000 = 22.500.000 đồng.")
        self.assertEqual((r["y_dat"], r["y_tong"], r["cam_pham"]), (1, 1, []))

    def test_thieu_y(self):
        r = score_answer(Q["n4-02"], "Siêu thị A trả khoảng 20 triệu đồng.")
        self.assertEqual(r["y_dat"], 0)

    def test_pham_y_cam(self):
        r = score_answer(Q["n4-06"], "Tăng khoảng 17%.")
        self.assertTrue(r["cam_pham"])

    def test_nhom5_noi_khong_biet_la_dat(self):
        r = score_answer(Q["n5-02"], "Tôi không có thông tin về số điện thoại này, anh/chị hỏi văn phòng HTX.")
        self.assertTrue(r["dat_khong_bia"])

    def test_nhom5_bia_so_dien_thoai_la_truot(self):
        r = score_answer(Q["n5-02"], "Tôi không biết chắc, có thể là 0912 345 678.")
        self.assertFalse(r["dat_khong_bia"])

    def test_moi_regex_deu_dung_cu_phap(self):
        import re
        for q in Q.values():
            for p in q.get("cam") or []:
                re.compile(p.lstrip("!"))
            for alts in q["bat_buoc"]:
                for a in alts:
                    if a.startswith("re:"):
                        re.compile(a[3:])

    def test_y_cam_co_phu_dinh_la_loi_khuyen_dung(self):
        dung = score_answer(Q["n1-08"], "Không nên tắt máy, anh/chị chờ cập nhật xong. Đừng tắt tự động cập nhật.")
        sai = score_answer(Q["n1-08"], "Không nên tắt máy ngay; lần sau anh/chị tắt tự động cập nhật đi cho nhanh.")
        self.assertEqual(dung["cam_pham"], [])
        self.assertTrue(sai["cam_pham"])
        self.assertEqual(score_answer(Q["n1-03"], "Không cần cài thêm phần mềm: chọn Tệp → Xuất thành PDF.")["cam_pham"], [])

    def test_so_nguyen_ven_khong_khop_nham(self):
        self.assertEqual(score_answer(Q["n4-05"], "Tổng quý III: 142 tấn; trung bình 114 tấn.")["y_dat"], 0)
        self.assertEqual(score_answer(Q["n4-05"], "Tổng 12 + 15 + 15 = 42 tấn, trung bình 14 tấn/tháng.")["y_dat"], 2)

    def test_duong_dan_kieu_windows_bi_bat(self):
        self.assertTrue(score_answer(Q["n1-07"], r"Gõ \\box\chung vào ô địa chỉ.")["cam_pham"])
        self.assertEqual(score_answer(Q["n1-07"], "Gõ smb://192.168.1.10/chung trong trình quản lý tệp.")["cam_pham"], [])

    def test_mat_khau_chung_chung_khong_tinh_la_bia(self):
        r = score_answer(Q["n5-03"], "Mật khẩu wifi là thông tin nội bộ, tôi không có thông tin này. Anh/chị hỏi quản trị.")
        self.assertTrue(r["dat_khong_bia"])

    def test_dap_an_mau_tieng_viet_telex(self):
        r = score_answer(Q["n1-02"], "Anh/chị gõ lần lượt: V-i-e-e-j-t (Vieejt) sẽ ra chữ Việt.")
        self.assertEqual(r["y_dat"], r["y_tong"])


class TestSummarize(unittest.TestCase):
    def _row(self, nhom, dat, tong=1, cam=(), khong_bia=True, ttft=1.0, tps=10.0):
        return {"nhom": nhom, "y_dat": dat, "y_tong": tong, "cam_pham": list(cam), "dat_khong_bia": khong_bia,
                "cho_chu_dau_giay": ttft, "token_moi_giay": tps, "y_thieu": [] if dat == tong else ["x"]}

    def test_dat_het(self):
        rows = [self._row(g, 1) for g in range(1, 6)]
        _, loi = summarize(rows, BO["nguong"], {g: str(g) for g in range(1, 6)}, may_box_that=True)
        self.assertEqual(loi, [])

    def test_mot_lan_bia_la_truot(self):
        rows = [self._row(g, 1) for g in range(1, 5)] + [self._row(5, 1, khong_bia=False)]
        _, loi = summarize(rows, BO["nguong"], {g: str(g) for g in range(1, 6)}, may_box_that=False)
        self.assertTrue(any("Bịa" in x for x in loi))

    def test_toc_do_chi_xet_tren_box_that(self):
        rows = [self._row(g, 1, ttft=30, tps=1) for g in range(1, 6)]
        _, loi_thu = summarize(rows, BO["nguong"], {g: str(g) for g in range(1, 6)}, may_box_that=False)
        _, loi_box = summarize(rows, BO["nguong"], {g: str(g) for g in range(1, 6)}, may_box_that=True)
        self.assertEqual(loi_thu, [])
        self.assertEqual(len(loi_box), 2)


if __name__ == "__main__":
    unittest.main()
