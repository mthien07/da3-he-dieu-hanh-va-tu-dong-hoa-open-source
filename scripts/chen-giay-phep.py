#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Chèn hoặc kiểm tra dòng giấy phép SPDX-License-Identifier: MIT trong các tệp mã của repo.
Cách dùng:
  python3 scripts/chen-giay-phep.py          # chèn vào các tệp còn thiếu (lũy đẳng)
  python3 scripts/chen-giay-phep.py --kiem   # chỉ kiểm tra, thoát khác 0 nếu còn tệp thiếu"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, GOC)

from tests.desktop.test_onebee_giay_phep import SPDX_CHUAN, danh_sach_tep_ma  # noqa: E402

BAN_QUYEN = "Copyright (c) 2026 Dương Minh Thiện, HTX OneBee"


def cap_dong_giay_phep(tep, cac_dong):
    dau_trang = cac_dong[0].lstrip().lower() if cac_dong else ""
    if tep.endswith(".json.j2"):
        return [
            f"{{# {SPDX_CHUAN} #}}\n",
            f"{{# {BAN_QUYEN} #}}\n",
        ]
    if tep.endswith((".html", ".html.j2")) or dau_trang.startswith("<?xml"):
        return [
            f"<!-- {SPDX_CHUAN} -->\n",
            f"<!-- {BAN_QUYEN} -->\n",
        ]
    if tep.endswith((".js", ".js.j2")):
        return [
            f"// {SPDX_CHUAN}\n",
            f"// {BAN_QUYEN}\n",
        ]
    return [
        f"# {SPDX_CHUAN}\n",
        f"# {BAN_QUYEN}\n",
    ]


def vi_tri_chen(tep, cac_dong):
    if not cac_dong:
        return 0
    dau_trang = cac_dong[0].lstrip().lower()
    if tep.endswith((".html", ".html.j2")) or dau_trang.startswith("<?xml"):
        vi_tri = 0
        for i, dong in enumerate(cac_dong[:3]):
            d = dong.lstrip().lower()
            if d.startswith(("<?xml", "<!doctype")):
                vi_tri = i + 1
        return vi_tri
    dong_dau = cac_dong[0].rstrip("\r\n")
    if dong_dau.startswith("#!") or dong_dau == "---":
        return 1
    return 0


def da_co_giay_phep(cac_dong):
    return any(SPDX_CHUAN in dong for dong in cac_dong[:5])


def main(argv):
    chi_kiem = "--kiem" in argv
    cac_tep = danh_sach_tep_ma()
    thieu = []
    da_chen = 0

    for tep in cac_tep:
        duong_dan = os.path.join(GOC, tep)
        if not os.path.isfile(duong_dan):
            continue
        with open(duong_dan, encoding="utf-8") as f:
            cac_dong = f.readlines()
        if da_co_giay_phep(cac_dong):
            continue
        if chi_kiem:
            thieu.append(tep)
            continue
        dong_moi = cap_dong_giay_phep(tep, cac_dong)
        vt = vi_tri_chen(tep, cac_dong)
        cac_dong_moi = cac_dong[:vt] + dong_moi + cac_dong[vt:]
        with open(duong_dan, "w", encoding="utf-8") as f:
            f.writelines(cac_dong_moi)
        da_chen += 1

    if chi_kiem:
        if thieu:
            for tep in thieu:
                print(f"Thiếu giấy phép: {tep}", file=sys.stderr)
            print(f"LỖI: {len(thieu)}/{len(cac_tep)} tệp mã thiếu {SPDX_CHUAN}", file=sys.stderr)
            return 1
        print(f"Đạt: {len(cac_tep)} tệp mã đều có {SPDX_CHUAN}")
        return 0

    print(f"Đã chèn giấy phép vào {da_chen} tệp (tổng {len(cac_tep)} tệp mã).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
