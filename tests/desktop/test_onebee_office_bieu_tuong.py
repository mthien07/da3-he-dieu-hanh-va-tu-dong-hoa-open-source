#!/usr/bin/env python3
"""Kiểm thử nhanh bộ biểu tượng LibreOffice mặc định (role office): Colibre, kiểu biểu tượng giống Microsoft Office.
Không cần LibreOffice thật (giá trị thực tế do check-libreoffice-default-formats.py đọc qua UNO). Chạy: python3 -m unittest"""
import os
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OFFICE = os.path.join(HERE, "../../desktop/ansible/roles/office")
RIBBON_XCD = os.path.join(OFFICE, "files/onebee-office-ribbon.xcd")
OFFICE_TASKS = os.path.join(OFFICE, "tasks/main.yml")
OOR = "{http://openoffice.org/2001/registry}"


def _tim_symbol_style():
    """Trả về (node Common, prop SymbolStyle) theo đường dẫn org.openoffice.Office.Common / Misc / SymbolStyle."""
    goc = ET.parse(RIBBON_XCD).getroot()
    for comp in goc.findall(f"{OOR}component-data"):
        if comp.get(f"{OOR}name") == "Common" and comp.get(f"{OOR}package") == "org.openoffice.Office":
            for node in comp.findall("node"):
                if node.get(f"{OOR}name") == "Misc":
                    for prop in node.findall("prop"):
                        if prop.get(f"{OOR}name") == "SymbolStyle":
                            return comp, prop
    return None, None


class BieuTuongColibre(unittest.TestCase):
    def test_xcd_dat_symbolstyle_colibre(self):
        _, prop = _tim_symbol_style()
        self.assertIsNotNone(prop, "Thiếu org.openoffice.Office.Common/Misc/SymbolStyle trong onebee-office-ribbon.xcd")
        self.assertEqual(prop.find("value").text, "colibre")

    def test_symbolstyle_dung_fuse_de_khong_mat_cac_gia_tri_khac(self):
        _, prop = _tim_symbol_style()
        self.assertIsNotNone(prop)
        self.assertEqual(prop.get(f"{OOR}op"), "fuse")

    def test_nap_sau_main_vi_symbolstyle_khai_bao_trong_main_xcd(self):
        goc = ET.parse(RIBBON_XCD).getroot()
        self.assertIn("main", {d.get("file") for d in goc.findall("dependency")})

    def test_van_con_ribbon_tabbed(self):
        goc = ET.parse(RIBBON_XCD).getroot()
        comps = {c.get(f"{OOR}name") for c in goc.findall(f"{OOR}component-data")}
        self.assertEqual(comps, {"ToolbarMode", "Common"})

    def test_task_apt_cai_goi_colibre(self):
        with open(OFFICE_TASKS, encoding="utf-8") as f:
            dong = [d.strip() for d in f]
        self.assertIn("- libreoffice-style-colibre", dong)
        # Gói phải nằm trong khối apt cài LibreOffice (cùng task với libreoffice-writer), state: present
        vi_tri_goi = dong.index("- libreoffice-style-colibre")
        self.assertIn("- libreoffice-writer", dong[:vi_tri_goi][-6:])
        self.assertIn("state: present", dong[vi_tri_goi:vi_tri_goi + 10])


if __name__ == "__main__":
    unittest.main()
