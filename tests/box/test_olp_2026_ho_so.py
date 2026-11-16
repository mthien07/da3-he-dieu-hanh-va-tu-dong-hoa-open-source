#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm chứng hồ sơ OLP 2026, tính nhất quán tài liệu DX-OS và tuân thủ PoF."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))

TAI_LIEU_PHAT_HANH = (
    "LICENSE",
    "LICENSES.md",
    "README.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "docs/kien-truc-dx-os.md",
    "docs/olp-2026-tu-cham-pof.md",
    "docs/api/openapi-dxos.md",
    "docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md",
    "docs/project-changelog.md",
)

TAI_LIEU_HOI_THI_NOI_BO = (
    "docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md",
    "docs/hoi-thi/olp-2026-thu-nop-bai.md",
)

# Tên hai thành phần đã gỡ, ghép chuỗi để chính tệp kiểm này không tự khớp khi quét toàn kho
TU_KHOA_NON_OSI = re.compile("|".join(("open" + r"[\s._-]?web" + "ui", r"\bn8" + "n\b")), re.IGNORECASE)


def doc(duong_dan: str) -> str:
    with open(os.path.join(ROOT, duong_dan), encoding="utf-8") as f:
        return f.read()


class TestHoSoOlp2026(unittest.TestCase):
    def test_day_du_tep_ho_so_va_khong_rong(self):
        for tep in TAI_LIEU_PHAT_HANH:
            p = os.path.join(ROOT, tep)
            self.assertTrue(os.path.isfile(p), f"Thiếu tệp bắt buộc: {tep}")
            self.assertGreater(os.path.getsize(p), 100, f"Tệp quá ngắn/rỗng: {tep}")
        if os.path.isdir(os.path.join(ROOT, "docs/hoi-thi")):
            for tep in TAI_LIEU_HOI_THI_NOI_BO:
                p = os.path.join(ROOT, tep)
                self.assertTrue(os.path.isfile(p), f"Thiếu hồ sơ hội thi: {tep}")
                self.assertGreater(os.path.getsize(p), 200, f"Hồ sơ hội thi quá ngắn: {tep}")

    def test_kien_truc_dx_os_du_3_tang_va_4_nguyen_ly(self):
        nd = doc("docs/kien-truc-dx-os.md")
        for cum in (
            "Tầng Nền tảng Dịch vụ Lõi số",
            "Tầng Không gian Năng lực số",
            "Tầng Nền tảng Kinh doanh số",
            "Zero-Trust",
            "hội tụ",
            "nóng",
            "kiểm dịch ngay biên mạng",
            "GitOps",
        ):
            self.assertIn(cum, nd, f"Thiếu khái niệm '{cum}' trong docs/kien-truc-dx-os.md")

    def test_tu_cham_pof_du_6_tieu_chi_va_dung_duong_dan(self):
        nd = doc("docs/olp-2026-tu-cham-pof.md")
        self.assertIn("50 / 50", nd)
        for muc in ("| **1** |", "| **2** |", "| **3** |", "| **4** |", "| **5** |", "| **6** |"):
            self.assertIn(muc, nd)
        for duong_dan in (
            "LICENSE",
            "LICENSES.md",
            "README.md",
            "CHANGELOG.md",
            "ROADMAP.md",
            "scripts/dong-goi-ban-phat-hanh.sh",
            "docs/kien-truc-dx-os.md",
            "docs/api/openapi-dxos.md",
            "docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md",
            "tests/box/test_olp_2026_ho_so.py",
        ):
            self.assertTrue(os.path.exists(os.path.join(ROOT, duong_dan)), f"Đường dẫn PoF không tồn tại: {duong_dan}")

    def test_readme_va_changelog_dong_bo_mit_va_1_3_0(self):
        readme = doc("README.md")
        self.assertIn("MIT", readme)
        self.assertIn("Vì sao MIT", readme)
        for lien_ket in ("docs/kien-truc-dx-os.md", "docs/api/openapi-dxos.md", "ROADMAP.md", "docs/olp-2026-tu-cham-pof.md", "CHANGELOG.md"):
            self.assertIn(lien_ket, readme)
        changelog = doc("CHANGELOG.md")
        self.assertIn("## [1.3.0]", changelog)

    def test_sach_thanh_phan_non_osi_trong_tai_lieu_dx_os(self):
        kiem = (
            "README.md",
            "ROADMAP.md",
            "docs/kien-truc-dx-os.md",
            "docs/api/openapi-dxos.md",
            "docs/olp-2026-tu-cham-pof.md",
            "docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md",
        )
        for tep in kiem:
            m = TU_KHOA_NON_OSI.search(doc(tep))
            self.assertIsNone(m, f"{tep} vẫn còn từ khóa non-OSI: {m.group(0) if m else ''}")


if __name__ == "__main__":
    unittest.main()
