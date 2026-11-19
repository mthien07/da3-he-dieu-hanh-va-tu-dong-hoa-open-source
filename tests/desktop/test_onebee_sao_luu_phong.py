#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử thẻ sao lưu theo phòng của `onebee-sao-luu`: máy có PHONG_BAN hợp lệ trong /etc/onebee/may-tram.env thì bản chụp restic
mang thêm thẻ `phong-<mã>` (Box khôi phục riêng từng phòng theo thẻ này); máy không có phòng, hoặc mã phòng sai dạng, thì giữ nguyên
như trước (chỉ thẻ onebee-may-tram). restic là lệnh giả ghi lại tham số. Chạy: python3 -m unittest tests/desktop/test_onebee_sao_luu_phong.py"""
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SAO_LUU = os.path.join(HERE, "../../desktop/ansible/roles/backup-client/files/onebee-sao-luu")
CO_BAN = "RESTIC_REPOSITORY=rest:http://a:b@1.2.3.4:8000/a/\nRESTIC_PASSWORD=x\n"


class SaoLuuTheoPhong(unittest.TestCase):
    def chay(self, env_nd):
        """Trả (kết quả, dòng tham số của lệnh `restic backup`)."""
        with tempfile.TemporaryDirectory() as t:
            with open(SAO_LUU, encoding="utf-8") as f:
                nd = f.read()
            nd = nd.replace("CONF=/etc/onebee/may-tram.env", f"CONF={t}/may-tram.env").replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||")
            nd = nd.replace("/usr/local/share/ca-certificates/onebee-box-ca.crt", f"{t}/ca.crt").replace("/var/lib/onebee", f"{t}/var")
            nd = nd.replace("restic ", "restic_gia ")
            with open(f"{t}/sao-luu", "w", encoding="utf-8") as f:
                f.write(nd)
            with open(f"{t}/may-tram.env", "w", encoding="utf-8") as f:
                f.write(env_nd)
            with open(f"{t}/restic_gia", "w", encoding="utf-8") as f:
                f.write(f'#!/bin/bash\necho "$@" >> {t}/lenh\n')
            os.chmod(f"{t}/restic_gia", 0o755)
            r = subprocess.run(["bash", f"{t}/sao-luu"], capture_output=True, text=True, env={**os.environ, "PATH": f"{t}:{os.environ['PATH']}"}, check=False)
            with open(f"{t}/lenh", encoding="utf-8") as f:
                backup = [d for d in f.read().splitlines() if d.startswith("backup")]
            return r, (backup[0].split() if backup else [])

    def the(self, tham_so):
        return [tham_so[i + 1] for i, v in enumerate(tham_so) if v == "--tag"]

    def test_co_phong_them_the_phong(self):
        r, backup = self.chay(CO_BAN + "PHONG_BAN=ke-toan\nPHONG_BAN_TEN=\"Phòng Kế toán\"\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.the(backup), ["onebee-may-tram", "phong-ke-toan"])
        self.assertIn("/home", backup)

    def test_phong_trong_ngoac_kep_va_dong_cuoi_khong_xuong_dong(self):
        _, backup = self.chay(CO_BAN + 'PHONG_BAN="hanh-chinh"')
        self.assertEqual(self.the(backup), ["onebee-may-tram", "phong-hanh-chinh"])

    def test_khong_co_phong_giu_nguyen_nhu_cu(self):
        r, backup = self.chay(CO_BAN)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.the(backup), ["onebee-may-tram"])

    def test_ma_phong_sai_dang_bi_bo_qua_khong_thanh_lenh(self):
        for sai in ("Ke Toan", "$(touch /tmp/bi-chay-phong)", "k", "1ke", "ke_toan", "a" * 21, "ke-toan;rm", ""):
            r, backup = self.chay(CO_BAN + f"PHONG_BAN={sai}\n")
            self.assertEqual(r.returncode, 0, (sai, r.stderr))
            self.assertEqual(self.the(backup), ["onebee-may-tram"], sai)
        self.assertFalse(os.path.exists("/tmp/bi-chay-phong"))

    def test_dong_phong_ban_khac_khong_bi_nham(self):
        _, backup = self.chay(CO_BAN + 'PHONG_BAN_TEN="Phòng Kế toán"\nPHONG_BAN_PHAN_MEM="gnucash"\n')
        self.assertEqual(self.the(backup), ["onebee-may-tram"])


if __name__ == "__main__":
    unittest.main()
