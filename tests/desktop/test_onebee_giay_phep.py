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

DUOI_MA = (".sh", ".py", ".yml", ".yaml", ".j2", ".js", ".html", ".sql", ".css")

# Danh sách loại trừ kèm lý do rõ ràng
THU_MUC_LOAI_TRU = {
    "plans/": "Kế hoạch nội bộ, không thuộc gói phát hành",
    "reports/": "Báo cáo đo đạc và thử nghiệm",
    "box/ansible/roles/box-n8n/templates/workflows/": "Mẫu quy trình n8n cũ, đang được thay bằng quy trình mới",
}

THU_MUC_BO_QUA_WALK = {".git", "__pycache__", ".pytest_cache", "dist", "node_modules", ".venv"}

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
    try:
        kq = subprocess.run(
            ["git", "-c", f"safe.directory={GOC}", "ls-files"],
            cwd=GOC,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        kq = None
    if kq is not None and kq.returncode == 0 and kq.stdout.strip():
        return sorted(d for d in kq.stdout.splitlines() if d and la_tep_ma(d))

    # Fallback khi kiểm tra bên ngoài cây Git (ví dụ giải nén gói .tar.gz phát hành)
    cac_tep = []
    for thu_muc, ds_con, ds_tep in os.walk(GOC):
        ds_con[:] = [c for c in ds_con if c not in THU_MUC_BO_QUA_WALK]
        for ten_tep in ds_tep:
            tuong_doi = os.path.relpath(os.path.join(thu_muc, ten_tep), GOC).replace(os.sep, "/")
            if la_tep_ma(tuong_doi):
                cac_tep.append(tuong_doi)
    return sorted(cac_tep)


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

    def test_ci_chay_kiem_tra_giay_phep(self):
        ci_yml = os.path.join(GOC, ".github/workflows/ci.yml")
        if not os.path.isfile(ci_yml):
            self.skipTest("gói phát hành không kèm .github/workflows/ci.yml")
        with open(ci_yml, encoding="utf-8") as f:
            noi_dung = f.read()
        self.assertIn(
            "python3 scripts/chen-giay-phep.py --kiem",
            noi_dung,
            ".github/workflows/ci.yml chưa chạy python3 scripts/chen-giay-phep.py --kiem",
        )


if __name__ == "__main__":
    unittest.main()
