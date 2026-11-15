#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sửa tệp người dùng của dịch vụ định danh (Authelia, users_database.yml) cho lệnh onebee-box (quản lý bởi OneBee OS).
Cách dùng:
  onebee-nguoi-dung.py co   <tệp> <tên>                 mã thoát 0 nếu đã có người dùng này
  onebee-nguoi-dung.py them <tệp> <tên> <nhóm> <email>  bản băm mật khẩu đọc từ biến ONEBEE_BAM (không nhận qua tham số)
  onebee-nguoi-dung.py xoa  <tệp> <tên>                 mã thoát 1 nếu không có người dùng này
  onebee-nguoi-dung.py ds   <tệp>                       in "tên nhóm,nhóm [đã khóa]"; không in bản băm, không in tài khoản hệ thống (tên bắt đầu bằng "_")
Ghi tệp mới cạnh tệp cũ (0600) rồi đổi tên: Authelia (watch: true) đọc lại khi tệp được thay, không bao giờ đọc tệp ghi dở."""
import os
import sys
import tempfile

import yaml


def doc(tep):
    with open(tep, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    if not isinstance(d.get("users"), dict):
        sys.exit(f"Tệp người dùng {tep} sai cấu trúc (thiếu khóa users)")
    return d


def ghi(tep, d):
    fd, tam = tempfile.mkstemp(dir=os.path.dirname(tep), prefix=".users_database.", suffix=".moi")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(d, f, allow_unicode=True, sort_keys=True, default_flow_style=False)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tam, 0o600)
        os.replace(tam, tep)
    except BaseException:
        os.unlink(tam)
        raise


def main(a):
    if len(a) < 2:
        sys.exit(__doc__)
    lenh, tep = a[0], a[1]
    d = doc(tep)
    nguoi = d["users"]
    if lenh == "co" and len(a) == 3:
        return 0 if a[2] in nguoi else 1
    if lenh == "them" and len(a) == 5:
        ten, nhom, email = a[2], a[3], a[4]
        bam = os.environ.get("ONEBEE_BAM", "")
        if not bam.startswith("$argon2id$"):
            sys.exit("Thiếu bản băm mật khẩu (ONEBEE_BAM)")
        if ten in nguoi:
            sys.exit(f"Đã có người dùng {ten}")
        nguoi[ten] = {"displayname": ten, "password": bam, "email": email, "groups": [nhom], "disabled": False}
        ghi(tep, d)
        return 0
    if lenh == "xoa" and len(a) == 3:
        if a[2] not in nguoi:
            return 1
        del nguoi[a[2]]
        ghi(tep, d)
        return 0
    if lenh == "ds" and len(a) == 2:
        for ten in sorted(nguoi):
            if ten.startswith("_"):
                continue
            u = nguoi[ten] or {}
            dong = f"{ten:<34}{','.join(u.get('groups') or []) or '(không nhóm)'}"
            print(dong + ("  [đã khóa]" if u.get("disabled") else ""))
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
