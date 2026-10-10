#!/usr/bin/env python3
"""Kiểm chứng chỉ CA của OneBee Box trước khi cài lên máy trạm (rà soát bảo mật F3).
Cách dùng: onebee-kiem-ca.py <BOX_CA base64 DER> <BOX_CA_VAN_TAY sha256 hex> <BOX_IP>
Đạt → in chứng chỉ dạng PEM ra stdout, thoát 0. Không đạt → in lý do ra stderr, thoát 1.
Kiểm: (1) vân tay khớp (chỉ bắt lỗi chép — vân tay đi cùng kênh với chứng chỉ nên KHÔNG chứng minh nguồn);
(2) đây đúng là CA OneBee CÓ RÀNG BUỘC: CA:TRUE, nameConstraints critical, IP được phép duy nhất là <BOX_IP>/32,
DNS được phép chỉ dạng <nhãn>.onebee.internal, không loại tên nào khác (email, URI…); (3) chưa hết hạn.
Nhờ (2), kể cả Box bị chiếm cũng không đẩy xuống được CA "mọi tên" (google.com, ngân hàng…) qua đường này."""
import base64
import binascii
import hashlib
import re
import subprocess
import sys


def loi(thong_bao):
    print(f"LỖI: {thong_bao}", file=sys.stderr)
    sys.exit(1)


def openssl(args, du_lieu):
    r = subprocess.run(["openssl", *args], input=du_lieu, capture_output=True)
    if r.returncode != 0:
        loi("openssl không đọc được chứng chỉ: " + r.stderr.decode(errors="replace").strip()[:200])
    return r.stdout


def kiem(b64, van_tay, box_ip):
    try:
        der = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        loi("BOX_CA không phải base64")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", van_tay or ""):
        loi("BOX_CA_VAN_TAY không đúng dạng sha256 (64 ký tự hex)")
    if hashlib.sha256(der).hexdigest() != van_tay.lower():
        loi("vân tay không khớp chứng chỉ (chép sai?)")
    if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", box_ip or ""):
        loi("BOX_IP không hợp lệ")
    ext = openssl(["x509", "-inform", "DER", "-noout", "-ext", "basicConstraints,nameConstraints"], der).decode()
    if "CA:TRUE" not in ext:
        loi("không phải chứng chỉ CA")
    if not re.search(r"X509v3 Name Constraints: critical", ext):
        loi("CA không có ràng buộc tên (nameConstraints critical) — từ chối: CA như vậy giả được mọi trang web")
    permitted = []
    trong_permitted = False
    dong_ext = ext.splitlines()
    tu = next(i for i, d in enumerate(dong_ext) if "Name Constraints" in d)
    for dong in dong_ext[tu + 1:]:
        s = dong.strip()
        if s == "Permitted:":
            trong_permitted = True
        elif s == "Excluded:":
            trong_permitted = False   # loại bớt chỉ làm CA hẹp hơn
        elif trong_permitted and s:
            permitted.append(s)
    ips = [p for p in permitted if p.startswith("IP:")]
    dns = [p for p in permitted if p.startswith("DNS:")]
    khac = [p for p in permitted if not p.startswith(("IP:", "DNS:"))]
    if khac:
        loi(f"CA cho phép loại tên không thuộc OneBee: {khac}")
    if ips != [f"IP:{box_ip}/255.255.255.255"]:
        loi(f"CA phải chỉ cho phép đúng IP của Box ({box_ip}/32), đang là: {ips}")
    if not dns or not all(re.fullmatch(r"DNS:[a-z0-9]([a-z0-9-]*[a-z0-9])?\.onebee\.internal", d) for d in dns):
        loi(f"CA phải chỉ cho phép tên dạng <mã>.onebee.internal, đang là: {dns}")
    r = subprocess.run(["openssl", "x509", "-inform", "DER", "-noout", "-checkend", "0"], input=der, capture_output=True)
    if r.returncode != 0:
        loi("chứng chỉ CA đã hết hạn")
    sys.stdout.write(openssl(["x509", "-inform", "DER", "-outform", "PEM"], der).decode())


if __name__ == "__main__":
    if len(sys.argv) != 4:
        loi("cách dùng: onebee-kiem-ca.py <BOX_CA> <BOX_CA_VAN_TAY> <BOX_IP>")
    kiem(*sys.argv[1:])
