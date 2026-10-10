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


TEN_DNS = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?\.onebee\.internal")
DONG_IP = re.compile(r"      IP:((\d{1,3}\.){3}\d{1,3}/(\d{1,3}\.){3}\d{1,3})")
DONG_DNS = re.compile(r"      DNS:(.*)")


def rang_buoc_nghiem(ext):
    """Đọc phần nameConstraints trong đầu ra `openssl x509 -ext …` theo cách NGHIÊM: sau tiêu đề chỉ được có đúng dòng "    Permitted:" rồi các dòng
    "      IP:<ip>/<mask>" hoặc "      DNS:<nhãn>.onebee.internal" — mọi dòng khác (Excluded:, loại tên khác, ký tự lạ) đều bị từ chối.
    Lý do: openssl in tên DNS nguyên văn kể cả ký tự xuống dòng, nên chứng chỉ có thể GIẢ dòng "Excluded:" bên trong một tên để giấu ràng buộc rộng.
    Trả về (danh sách "ip/mask", danh sách tên DNS); thoát với lỗi nếu có gì lạ."""
    if not re.fullmatch(r"[\x20-\x7e\n]*", ext):
        loi("đầu ra chứng chỉ có ký tự lạ")
    dong = ext.rstrip("\n").split("\n")
    if "X509v3 Name Constraints: critical" not in dong:
        loi("CA không có ràng buộc tên (nameConstraints critical) — từ chối: CA như vậy giả được mọi trang web")
    phan = dong[dong.index("X509v3 Name Constraints: critical") + 1:]
    if not phan or phan[0] != "    Permitted:":
        loi("ràng buộc tên không đúng dạng (cần đúng một mục Permitted, không có Excluded)")
    ips, dns = [], []
    for d in phan[1:]:
        m_ip, m_dns = DONG_IP.fullmatch(d), DONG_DNS.fullmatch(d)
        if m_ip:
            ips.append(m_ip.group(1))
        elif m_dns and TEN_DNS.fullmatch(m_dns.group(1)):
            dns.append(m_dns.group(1))
        else:
            loi(f"ràng buộc tên có mục không thuộc OneBee: {d.strip()!r}")
    return ips, dns


def rang_buoc_tu_pem(file_pem):
    """Như trên, đọc từ file PEM (dùng cho chính sách trình duyệt — cùng một bộ đọc nghiêm)."""
    ext = subprocess.run(["openssl", "x509", "-in", file_pem, "-noout", "-ext", "nameConstraints"], capture_output=True, text=True, check=True).stdout
    return rang_buoc_nghiem(ext)


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
    ips, dns = rang_buoc_nghiem(ext)
    if ips != [f"{box_ip}/255.255.255.255"]:
        loi(f"CA phải chỉ cho phép đúng IP của Box ({box_ip}/32), đang là: {ips}")
    if not dns:
        loi("CA phải có ràng buộc tên DNS dạng <mã>.onebee.internal")
    r = subprocess.run(["openssl", "x509", "-inform", "DER", "-noout", "-checkend", "0"], input=der, capture_output=True)
    if r.returncode != 0:
        loi("chứng chỉ CA đã hết hạn")
    sys.stdout.write(openssl(["x509", "-inform", "DER", "-outform", "PEM"], der).decode())


if __name__ == "__main__":
    if len(sys.argv) != 4:
        loi("cách dùng: onebee-kiem-ca.py <BOX_CA> <BOX_CA_VAN_TAY> <BOX_IP>")
    kiem(*sys.argv[1:])
