#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử phiên bản nhất quán: bộ cài Desktop, bộ cài Box và mục đầu nhật ký thay đổi phải trùng nhau,
và không thấp hơn tag phát hành mới nhất (nếu không thì workflow phát hành không đính kèm file tải).
Chạy: python3 -m unittest"""
import os
import re
import shutil
import subprocess
import tempfile
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
        # Mục [Unreleased] gom thay đổi chưa phát hành, không phải một phiên bản
        m = re.search(r"^## \[(?!Unreleased\])([^\]]+)\]", doc(CHANGELOG), re.M)
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


class GoiThu(unittest.TestCase):
    """Chạy script đóng gói thật trên một repo git tạm có đủ tệp mà script đòi."""

    def setUp(self):
        for lenh in ("git", "sha256sum", "tar", "awk"):
            if shutil.which(lenh) is None:
                self.skipTest("thiếu lệnh %s" % lenh)
        self.tmp = tempfile.mkdtemp(prefix="onebee-goi-thu-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.sao_chep(DONG_GOI, "scripts/dong-goi-ban-phat-hanh.sh")
        self.viet("desktop/ansible/group_vars/all.yml", 'onebee_version: "1.2.0"\n')
        self.viet("box/ansible/group_vars/all.yml", 'onebee_box_version: "1.2.0"\n')
        self.viet("CHANGELOG.md", "# Nhật ký thay đổi\n\n## [1.3.0] — 17/11/2026\n- Thay đổi chưa phát hành\n\n## [1.2.0] — 14/11/2026\n- Bản cũ\n")
        for tep in ("tests/a.txt", "docs/huong-dan/a.md", "docs/adr/a.md", "docs/kinh-doanh/a.md",
                    "docs/api/a.md", "docs/kien-truc-dx-os.md", "docs/olp-2026-tu-cham-pof.md", "ROADMAP.md",
                    "LICENSE", "LICENSES.md", "CONTRIBUTING.md", "SECURITY.md", "README.md"):
            self.viet(tep, "x\n")
        for lenh in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "ban dau"]):
            subprocess.run(["git", *lenh], cwd=self.tmp, check=True, capture_output=True)

    def viet(self, tuong_doi, noi_dung):
        duong_dan = os.path.join(self.tmp, tuong_doi)
        os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
        with open(duong_dan, "w", encoding="utf-8") as f:
            f.write(noi_dung)

    def sao_chep(self, nguon, tuong_doi):
        dich = os.path.join(self.tmp, tuong_doi)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.copy(nguon, dich)

    def chay(self, phien_ban, **moi_truong):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
        env.update(moi_truong)
        return subprocess.run(["bash", "scripts/dong-goi-ban-phat-hanh.sh", phien_ban], cwd=self.tmp,
                              capture_output=True, text=True, env=env, timeout=120)

    def test_goi_thu_dev_co_license_va_ghi_chu_theo_phien_ban(self):
        kq = self.chay("1.3.0-dev")
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("Đã tạo:", kq.stdout)
        ds = subprocess.run(["tar", "tzf", os.path.join(self.tmp, "dist/onebee-os-1.3.0-dev.tar.gz")],
                            capture_output=True, text=True, check=True).stdout.splitlines()
        for tep in ("LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"):
            self.assertEqual(sum(1 for d in ds if d.endswith("/" + tep)), 1, "gói thiếu %s" % tep)
        with open(os.path.join(self.tmp, "dist/ghi-chu-phat-hanh.md"), encoding="utf-8") as f:
            ghi_chu = f.read()
        self.assertIn("Thay đổi chưa phát hành", ghi_chu)
        self.assertNotIn("Bản cũ", ghi_chu)

    def test_goi_thu_dev_khong_dung_de_phat_hanh_tren_ci(self):
        kq = self.chay("1.3.0-dev", GITHUB_ACTIONS="true")
        self.assertNotEqual(kq.returncode, 0, "gói thử -dev không được phát hành qua workflow")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "dist/onebee-os-1.3.0-dev.tar.gz")))

    def test_phien_ban_that_van_phai_khop_group_vars(self):
        kq = self.chay("1.3.0")
        self.assertNotEqual(kq.returncode, 0)
        self.assertIn("chưa ghi phiên bản 1.3.0", kq.stderr)

    def test_phien_ban_that_dung_van_dong_goi_duoc(self):
        kq = self.chay("1.2.0")
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        with open(os.path.join(self.tmp, "dist/ghi-chu-phat-hanh.md"), encoding="utf-8") as f:
            self.assertIn("Bản cũ", f.read())

    def test_ghi_chu_ban_that_co_lenh_cai_nhanh_ghim_dung_phien_ban(self):
        kq = self.chay("1.2.0")
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        with open(os.path.join(self.tmp, "dist/ghi-chu-phat-hanh.md"), encoding="utf-8") as f:
            ghi_chu = f.read()
        self.assertIn("### Cài nhanh", ghi_chu)
        self.assertIn("/releases/download/v1.2.0", ghi_chu)
        self.assertIn("onebee-os-1.2.0.tar.gz", ghi_chu)
        self.assertIn("sha256sum -c SHA256SUMS", ghi_chu)
        self.assertIn("sudo ./desktop/onebee-install.sh", ghi_chu)
        # Biến shell phải còn nguyên để người dùng dán chạy được, không bị script đóng gói thay mất
        self.assertIn('cd "$(mktemp -d)"', ghi_chu)
        self.assertIn('"$B/onebee-os-1.2.0.tar.gz"', ghi_chu)

    def test_ghi_chu_ban_dev_khong_co_lenh_cai_nhanh(self):
        kq = self.chay("1.3.0-dev")
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        with open(os.path.join(self.tmp, "dist/ghi-chu-phat-hanh.md"), encoding="utf-8") as f:
            self.assertNotIn("Cài nhanh", f.read())


if __name__ == "__main__":
    unittest.main()
