#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Bổ sung nút OneBee còn thiếu vào flows.json đang chạy của Node-RED.

Bộ cài chỉ chép flows.json khi Box chưa có, để giữ luồng người dùng đã sửa trong trình soạn. Box nâng cấp từ bản cũ
vì thế không nhận điểm nhận mới (vd xin vào máy trạm). Tệp này so theo id nút: nút nào có trong bản bộ cài sinh mà chưa
có trong bản đang chạy thì thêm vào; nút đang có (kể cả nút OneBee người dùng đã sửa) giữ nguyên.

Dùng: onebee-bo-sung-luong.py <flows-bo-cai-sinh.json> <flows-dang-chay.json>
In "DA_BO_SUNG <id>..." khi có thay đổi; không in gì khi đủ.
"""
import json
import os
import sys
import tempfile


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        luong = json.load(f)
    if not isinstance(luong, list) or not all(isinstance(n, dict) and "id" in n for n in luong):
        raise ValueError(f"{duong_dan}: không phải danh sách nút Node-RED")
    return luong


def bo_sung(mau, dang_chay):
    co = {n["id"] for n in dang_chay}
    thieu = [n for n in mau if n["id"] not in co]
    return dang_chay + thieu, [n["id"] for n in thieu]


def main():
    if len(sys.argv) != 3:
        sys.exit("Dùng: onebee-bo-sung-luong.py <flows-bo-cai-sinh.json> <flows-dang-chay.json>")
    mau_tep, dich = sys.argv[1], sys.argv[2]
    try:
        mau = doc(mau_tep)
        dang_chay = doc(dich)
    except (OSError, ValueError) as loi:
        sys.exit(f"LỖI: {loi}. Sửa tệp trong trình soạn luồng, hoặc dời tệp đi để bộ cài chép lại bản gốc.")
    moi, them = bo_sung(mau, dang_chay)
    if not them:
        return
    tt = os.stat(dich)
    fd, tam = tempfile.mkstemp(dir=os.path.dirname(dich), prefix=".flows-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(moi, f, ensure_ascii=False, indent=4)
            f.write("\n")
        os.chown(tam, tt.st_uid, tt.st_gid)
        os.chmod(tam, tt.st_mode & 0o7777)
        os.replace(tam, dich)
    except BaseException:
        os.unlink(tam)
        raise
    print("DA_BO_SUNG " + " ".join(them))


if __name__ == "__main__":
    main()
