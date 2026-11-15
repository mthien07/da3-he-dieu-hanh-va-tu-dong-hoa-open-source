# SPDX-License-Identifier: MIT
"""Kiểm thử Ứng dụng Sổ điều hành HTX theo mô hình H-P-D-I (Giai đoạn 6)."""
import os
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
GROUP_VARS = os.path.join(ROOT, "box/ansible/group_vars/all.yml")
TEMPLATES = os.path.join(ROOT, "box/ansible/roles/box-stack/templates")


class TestSoDieuHanhHpdi(unittest.TestCase):
    def test_so_dieu_hanh_nhe_duoi_40kb_khong_innerhtml_khong_cdn(self):
        with open(GROUP_VARS, encoding="utf-8") as f:
            v = yaml.safe_load(f)
        v.update(onebee_box_ten_don_vi="HTX An Phú")
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
        env.filters["bool"] = bool
        with open(os.path.join(TEMPLATES, "so-dieu-hanh.html.j2"), encoding="utf-8") as f:
            html = env.from_string(f.read()).render(**v)
        self.assertLess(len(html.encode("utf-8")), 40 * 1024)
        self.assertNotIn("innerHTML", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        for token in ("tab-h", "tab-p", "tab-d", "tab-i", "luu-y-ai", "d-chan-quyen", "/webhook/onebee-phe-duyet"):
            self.assertIn(token, html)

    def test_trang_chu_co_the_so_dieu_hanh(self):
        with open(GROUP_VARS, encoding="utf-8") as f:
            v = yaml.safe_load(f)
        v.update(
            onebee_box_ten_don_vi="HTX An Phú",
            onebee_box_ten_mdns="onebee",
            onebee_https_hieu_luc=False,
        )
        env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
        env.filters["bool"] = bool
        with open(os.path.join(TEMPLATES, "index.html.j2"), encoding="utf-8") as f:
            idx = env.from_string(f.read()).render(**v)
        self.assertIn('href="/so-dieu-hanh/"', idx)
        self.assertIn("Sổ điều hành HTX (H-P-D-I)", idx)


if __name__ == "__main__":
    unittest.main()
