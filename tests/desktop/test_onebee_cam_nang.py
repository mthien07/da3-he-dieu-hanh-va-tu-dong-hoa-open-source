#!/usr/bin/env python3
"""Kiểm thử nguồn chung cẩm nang (onebee-cam-nang.json): phím tắt và tên gọi trên máy phải khớp nguồn,
và 5 tài liệu phát cho người dùng không được nêu tên sai hay phím sai.
Chạy: python3 -m unittest"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(HERE, "../.."))
ROLES = os.path.join(GOC, "desktop/ansible/roles")
CAM_NANG = os.path.join(ROLES, "theme/files/onebee-cam-nang.json")
OVERRIDE = os.path.join(ROLES, "theme/files/zz_onebee-windows-layout.gschema.override")
THEME_TASKS = os.path.join(ROLES, "theme/tasks/main.yml")

# Tên gọi nào nằm ở file nào của bộ cài máy trạm (dòng Name=<tên>)
NOI_DINH_NGHIA_TEN = {
    "tro_ly_ai": "theme/tasks/main.yml",
    "thu_muc_chung": "ket-noi-box/tasks/main.yml",
    "bao_ho_tro": "quan-ly-tap-trung/tasks/muc-menu.yml",
    "ho_tro_tu_xa": "ho-tro-tu-xa/tasks/main.yml",
}

BE_MAT = [
    "docs/huong-dan/to-phim-tat.md",
    "docs/thuong-mai/huong-dan-nhanh-a4-can-bo-htx.md",
    "docs/huong-dan/dao-tao-buoi-1-3.md",
    "docs/huong-dan/kich-ban-video-huong-dan.md",
    "box/ansible/roles/box-stack/templates/index.html.j2",
]


def doc_dong(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read().splitlines()


def chuan_hoa(dong):
    """Bỏ định dạng (<kbd>, **, dấu `) và gộp khoảng trắng để so chuỗi."""
    for chuoi in ("<kbd>", "</kbd>", "**", "`"):
        dong = dong.replace(chuoi, "")
    return re.sub(r"\s+", " ", dong).strip()


def nap_cam_nang():
    with open(CAM_NANG, encoding="utf-8") as f:
        return json.load(f)


class CamNangNhatQuan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nguon = nap_cam_nang()

    def test_cau_truc(self):
        self.assertEqual(self.nguon.get("phien_ban"), 1)
        da_thay = set()
        for muc in self.nguon["phim_tat"]:
            for truong in ("ma", "nhom", "viec", "phim"):
                self.assertTrue(muc.get(truong), "Mục phím tắt %r thiếu trường %r" % (muc.get("ma"), truong))
            self.assertNotIn(muc["ma"], da_thay, "Mã phím tắt trùng: %s" % muc["ma"])
            da_thay.add(muc["ma"])

    def test_phim_khop_cau_hinh_may(self):
        dong_override = doc_dong(OVERRIDE)
        dong_theme = doc_dong(THEME_TASKS)
        loi = []
        for muc in self.nguon["phim_tat"]:
            kiem = muc.get("kiem")
            if not kiem:
                continue
            khoa, chuoi = kiem["khoa"], kiem["chuoi"]
            if kiem["tep"] == "override":
                khop = [d for d in dong_override if d.startswith(khoa + "=") and chuoi in d]
                noi = "zz_onebee-windows-layout.gschema.override"
            elif kiem["tep"] == "dconf":
                khop = [d for d in dong_theme if (khoa + "=") in d and chuoi in d]
                noi = "theme/tasks/main.yml"
            else:
                self.fail("Mục %s có kiem.tep lạ: %r" % (muc["ma"], kiem["tep"]))
            if not khop:
                loi.append("%s: không thấy %s=%s trong %s" % (muc["ma"], khoa, chuoi, noi))
        self.assertEqual(loi, [], "Phím trong nguồn chung lệch cấu hình máy:\n" + "\n".join(loi))

    def test_ten_goi_trung_ten_tren_may(self):
        loi = []
        for khoa, ten in self.nguon["ten_goi"].items():
            self.assertIn(khoa, NOI_DINH_NGHIA_TEN, "Tên gọi %r chưa khai báo nơi định nghĩa trong test" % khoa)
            duong_dan = os.path.join(ROLES, NOI_DINH_NGHIA_TEN[khoa])
            dong = [d.strip() for d in doc_dong(duong_dan)]
            if ("Name=" + ten) not in dong:
                loi.append("%s: không có dòng Name=%s trong %s" % (khoa, ten, NOI_DINH_NGHIA_TEN[khoa]))
        self.assertEqual(loi, [], "Tên gọi lệch tên trên máy:\n" + "\n".join(loi))

    def test_be_mat_khong_dung_ten_sai(self):
        loi = []
        for be_mat in BE_MAT:
            for so_dong, dong in enumerate(doc_dong(os.path.join(GOC, be_mat)), 1):
                dong = chuan_hoa(dong)
                for ten_sai in self.nguon["ten_sai"]:
                    if ten_sai in dong:
                        loi.append("%s:%d: dùng tên sai %r" % (be_mat, so_dong, ten_sai))
        self.assertEqual(loi, [], "Tài liệu gọi sai tên:\n" + "\n".join(loi))

    def test_be_mat_ghi_dung_phim(self):
        loi = []
        for be_mat in BE_MAT:
            for so_dong, dong in enumerate(doc_dong(os.path.join(GOC, be_mat)), 1):
                dong = chuan_hoa(dong)
                dong_thuong = dong.lower()
                for muc in self.nguon["phim_tat"]:
                    if not any(tu.lower() in dong_thuong for tu in muc.get("tu_khoa", [])):
                        continue
                    if muc["phim"] not in dong:
                        loi.append("%s:%d [%s]: thiếu phím %r" % (be_mat, so_dong, muc["ma"], muc["phim"]))
                    for mau_cam in muc.get("cam", []):
                        if re.search(mau_cam, dong):
                            loi.append("%s:%d [%s]: ghi phím bị cấm (khớp %r)" % (be_mat, so_dong, muc["ma"], mau_cam))
        self.assertEqual(loi, [], "Tài liệu ghi sai phím:\n" + "\n".join(loi))


if __name__ == "__main__":
    unittest.main()
