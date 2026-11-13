#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử phiên bản nhất quán: bộ cài Desktop, bộ cài Box và mục đầu nhật ký thay đổi phải trùng nhau,
và không thấp hơn tag phát hành mới nhất (nếu không thì workflow phát hành không đính kèm file tải).
Chạy: python3 -m unittest"""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(HERE, "../.."))
DESKTOP_VARS = os.path.join(GOC, "desktop/ansible/group_vars/all.yml")
BOX_VARS = os.path.join(GOC, "box/ansible/group_vars/all.yml")
CHANGELOG = os.path.join(GOC, "CHANGELOG.md")
DONG_GOI = os.path.join(GOC, "scripts/dong-goi-ban-phat-hanh.sh")


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


def lay_gia_tri(duong_dan, khoa):
    m = re.search(r'^%s:\s*"([^"]+)"' % re.escape(khoa), doc(duong_dan), re.M)
    if not m:
        raise AssertionError("Không thấy %s trong %s" % (khoa, duong_dan))
    return m.group(1)


def bo_ba(phien_ban):
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", phien_ban)
    return tuple(int(x) for x in m.groups()) if m else None


class PhienBanNhatQuan(unittest.TestCase):
    def test_desktop_box_va_nhat_ky_trung_phien_ban(self):
        desktop = lay_gia_tri(DESKTOP_VARS, "onebee_version")
        box = lay_gia_tri(BOX_VARS, "onebee_box_version")
        m = re.search(r"^## \[([^\]]+)\]", doc(CHANGELOG), re.M)
        self.assertIsNotNone(m, "Nhật ký thay đổi không có tiêu đề '## [phiên bản]'")
        nhat_ky = m.group(1)
        self.assertEqual(desktop, box, "onebee_version (Desktop) lệch onebee_box_version (Box)")
        self.assertEqual(desktop, nhat_ky, "Phiên bản trong bộ cài lệch mục đầu nhật ký thay đổi")

    def test_phien_ban_khong_thap_hon_tag_moi_nhat(self):
        try:
            kq = subprocess.run(["git", "tag", "-l", "v*"], cwd=GOC, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as loi:
            self.skipTest("Không chạy được git: %s" % loi)
        if kq.returncode != 0:
            self.skipTest("git tag lỗi: %s" % kq.stderr.strip())
        cac_tag = [t for t in kq.stdout.split() if "-rc" not in t and bo_ba(t)]
        if not cac_tag:
            self.skipTest("Chưa có tag phát hành nào")
        moi_nhat = max(cac_tag, key=bo_ba)
        hien_tai = lay_gia_tri(DESKTOP_VARS, "onebee_version")
        self.assertIsNotNone(bo_ba(hien_tai), "onebee_version không phải dạng X.Y.Z: %s" % hien_tai)
        self.assertGreaterEqual(
            bo_ba(hien_tai), bo_ba(moi_nhat),
            "Phiên bản trong mã (%s) thấp hơn tag %s: bản phát hành sẽ không có file tải" % (hien_tai, moi_nhat))

    def test_goi_phat_hanh_co_license_va_changelog_goc(self):
        self.assertTrue(os.path.isfile(CHANGELOG), "Thiếu CHANGELOG.md ở gốc repo")
        nd_dong_goi = doc(DONG_GOI)
        for tep in ("LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"):
            self.assertIn(tep, nd_dong_goi, "scripts/dong-goi-ban-phat-hanh.sh chưa đóng gói %s" % tep)


if __name__ == "__main__":
    unittest.main()
