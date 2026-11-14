#!/usr/bin/env python3
"""Kiểm thử: Firefox chạy tiếng Việt ngay sau khi cài.
Gói firefox-locale-vi chỉ nạp được vào đúng phiên bản Firefox của nó và kho chỉ giữ bản mới nhất; máy cài từ ISO còn Firefox cũ thì
Firefox chạy tiếng Anh, Trợ lý AI chọn tiếng Anh theo trình duyệt ở lần mở đầu rồi ghi nhớ. Role vietnamese phải nâng Firefox cùng
gói tiếng Việt lên bản mới nhất (chỉ khi máy có Firefox bản .deb). Chạy: python3 -m unittest"""
import os
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
VI_TASKS = os.path.join(HERE, "../../desktop/ansible/roles/vietnamese/tasks/main.yml")


def tac_vu():
    with open(VI_TASKS, encoding="utf-8") as f:
        return yaml.safe_load(f)


class FirefoxKhopGoiTiengViet(unittest.TestCase):
    def test_nang_firefox_cung_goi_tieng_viet(self):
        ds = [t for t in tac_vu() if "ansible.builtin.apt" in t and "firefox" in (t["ansible.builtin.apt"].get("name") or [])]
        self.assertEqual(len(ds), 1)
        apt = ds[0]["ansible.builtin.apt"]
        self.assertEqual(set(apt["name"]), {"firefox", "firefox-locale-vi"})   # cùng một lệnh apt → cùng phiên bản
        self.assertEqual(apt["state"], "latest")
        self.assertTrue(apt["only_upgrade"])                                     # không tự cài Firefox lên máy không có
        self.assertIn("onebee_ff_phan_phoi.stat.isdir", str(ds[0]["when"]))     # chỉ máy có Firefox bản .deb (không đụng bản snap)

    def test_kiem_firefox_truoc_khi_nang(self):
        ten = [t.get("name") for t in tac_vu()]
        self.assertLess(ten.index("Kiểm tra Firefox (bản .deb) có trên máy"), ten.index("Nâng Firefox cùng gói tiếng Việt cho khớp phiên bản"))

    def test_van_cai_goi_tieng_viet(self):
        goi = [n for t in tac_vu() if "ansible.builtin.apt" in t and t["ansible.builtin.apt"].get("state") == "present"
               for n in (t["ansible.builtin.apt"].get("name") or [])]
        self.assertIn("firefox-locale-vi", goi)


if __name__ == "__main__":
    unittest.main()
