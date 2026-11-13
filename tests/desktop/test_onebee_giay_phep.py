#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử giấy phép nguồn mở (tiêu chí PoF): gốc repo có LICENSE (MIT License)
và mọi tệp mã được theo dõi có dòng SPDX-License-Identifier: MIT trong 5 dòng đầu.
Chạy: python3 -m unittest tests/desktop/test_onebee_giay_phep.py"""
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(HERE, "../.."))
SPDX_CHUAN = "SPDX-License-Identifier: MIT"

DUOI_MA = (".sh", ".py", ".yml", ".yaml", ".j2", ".js", ".html")

# Danh sách loại trừ kèm lý do rõ ràng
THU_MUC_LOAI_TRU = {
    "plans/": "Kế hoạch nội bộ, không thuộc gói phát hành",
    "reports/": "Báo cáo đo đạc và thử nghiệm",
    "box/ansible/roles/box-n8n/templates/workflows/": "Mẫu JSON quy trình n8n sẽ bị xóa ở giai đoạn 5",
}

DUOI_LOAI_TRU = {
    ".json": "Tệp JSON thuần không hỗ trợ cú pháp chú thích",
    ".png": "Tệp ảnh nhị phân",
    ".svg": "Tệp ảnh vector",
    ".pdf": "Tệp PDF nhị phân",
    ".docx": "Tệp văn bản Word mẫu kiểm thử",
    ".asc": "Khóa PGP công khai của bên thứ ba",
}

TEP_LOAI_TRU = {}


def la_tep_ma(duong_dan):
    if duong_dan in TEP_LOAI_TRU:
        return False
    if any(duong_dan.startswith(tien_to) for tien_to in THU_MUC_LOAI_TRU):
        return False
    ten = os.path.basename(duong_dan)
    _, duoi = os.path.splitext(ten)
    if duoi in DUOI_LOAI_TRU:
        return False
    if duoi in DUOI_MA:
        return True
    if duoi == "" and (ten == "hoi" or ten.startswith("onebee-")):
        return True
    return False


def danh_sach_tep_ma():
    kq = subprocess.run(
        ["git", "ls-files"],
        cwd=GOC,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return [d for d in kq.stdout.splitlines() if d and la_tep_ma(d)]


class GiayPhepTungTep(unittest.TestCase):
    def test_goc_repo_co_license_mit(self):
        duong_dan = os.path.join(GOC, "LICENSE")
        self.assertTrue(os.path.isfile(duong_dan), "Thiếu tệp LICENSE ở gốc repo")
        with open(duong_dan, encoding="utf-8") as f:
            noi_dung = f.read()
        self.assertIn("MIT License", noi_dung, "Tệp LICENSE không chứa chữ 'MIT License'")

    def test_moi_tep_ma_co_spdx_trong_5_dong_dau(self):
        cac_tep = danh_sach_tep_ma()
        self.assertGreater(len(cac_tep), 100, "Danh sách tệp mã quá ít bất thường")
        thieu = []
        for tep in cac_tep:
            duong_dan = os.path.join(GOC, tep)
            if not os.path.isfile(duong_dan):
                continue
            with open(duong_dan, encoding="utf-8") as f:
                nam_dong_dau = [f.readline() for _ in range(5)]
            if not any(SPDX_CHUAN in dong for dong in nam_dong_dau):
                thieu.append(tep)
        self.assertEqual(
            thieu,
            [],
            "Có %d/%d tệp mã thiếu '%s' trong 5 dòng đầu:\n%s"
            % (len(thieu), len(cac_tep), SPDX_CHUAN, "\n".join(thieu)),
        )


if __name__ == "__main__":
    unittest.main()
