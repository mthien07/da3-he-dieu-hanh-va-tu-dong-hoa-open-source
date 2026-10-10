#!/usr/bin/env python3
"""Cài / gỡ CA của OneBee Box vào trình duyệt (Firefox, Chromium, Chrome) bằng chính sách doanh nghiệp (rà soát bảo mật F3).
Cách dùng: onebee-chinh-sach-trinh-duyet.py cai <file-pem-CA> | go
 - Firefox: chính sách Certificates.Install ghi vào /etc/firefox/policies/policies.json. File ở /etc THAY THẾ file
   /usr/lib/firefox/distribution/policies.json của gói → trộn nội dung gói vào rồi mới thêm mục OneBee; khi gỡ, trả về đúng nội dung gói
   (hoặc xóa file nếu gói không có). Firefox KHÔNG tự gỡ chứng chỉ đã nạp khi bỏ chính sách → 'go' gỡ thêm khỏi từng hồ sơ bằng certutil (cố gắng hết sức).
 - Chromium/Chrome: CACertificatesWithConstraints — trình duyệt tự áp ràng buộc tên của CA; gỡ = xóa file chính sách.
Biến ONEBEE_GOC: tiền tố thư mục gốc (để kiểm thử); mặc định rỗng."""
import base64
import glob
import json
import os
import re
import subprocess
import sys

GOC = os.environ.get("ONEBEE_GOC", "")
DICH_CA = "/usr/local/share/ca-certificates/onebee-box-ca.crt"
FIREFOX_ETC = GOC + "/etc/firefox/policies/policies.json"
FIREFOX_GOI = GOC + "/usr/lib/firefox/distribution/policies.json"
CHROME_FILES = [GOC + "/etc/chromium/policies/managed/onebee-box.json", GOC + "/etc/opt/chrome/policies/managed/onebee-box.json"]
TEN_CHUNG_CHI = re.compile(r"^(OneBee Box .+? Root CA)\s+[A-Za-z,]*$")


def doc_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def ghi_neu_doi(p, du_lieu):
    """Ghi JSON nếu nội dung khác; trả True khi có đổi."""
    moi = json.dumps(du_lieu, indent=2, ensure_ascii=False) + "\n"
    try:
        if open(p, encoding="utf-8").read() == moi:
            return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(moi)
    os.chmod(p, 0o644)
    return True


def pem_sang_der_b64(p):
    pem = open(p, encoding="ascii").read()
    return base64.b64encode(base64.b64decode("".join(l for l in pem.splitlines() if not l.startswith("-----")))).decode()


def rang_buoc(file_pem):
    """(danh sách CIDR, danh sách tên DNS) mà CA cho phép — đọc từ chính chứng chỉ, để trình duyệt tự áp."""
    ext = subprocess.run(["openssl", "x509", "-in", file_pem, "-noout", "-ext", "nameConstraints"], capture_output=True, text=True, check=True).stdout
    cidr, dns = [], []
    for dong in ext.splitlines():
        s = dong.strip()
        if s.startswith("IP:"):
            ip, mask = s[3:].split("/")
            cidr.append(f"{ip}/{sum(bin(int(o)).count('1') for o in mask.split('.'))}")
        elif s.startswith("DNS:"):
            dns.append(s[4:])
    return cidr, dns


def cai(file_pem):
    doi = False
    goi = doc_json(FIREFOX_GOI) or {}
    cs = goi.get("policies", {}) if isinstance(goi.get("policies", {}), dict) else {}
    goi = {"policies": dict(cs)}
    chung_chi = dict(goi["policies"].get("Certificates", {}))
    chung_chi["Install"] = [x for x in chung_chi.get("Install", []) if x != DICH_CA] + [DICH_CA]
    goi["policies"]["Certificates"] = chung_chi
    doi |= ghi_neu_doi(FIREFOX_ETC, goi)
    b64 = pem_sang_der_b64(file_pem)
    cidr, dns = rang_buoc(file_pem)
    for p in CHROME_FILES:
        doi |= ghi_neu_doi(p, {"CACertificatesWithConstraints": [
            {"certificate": b64, "constraints": {"permitted_cidrs": cidr, "permitted_dns_names": dns}}]})
    return doi


def go_khoi_ho_so_firefox():
    """Xóa chứng chỉ 'OneBee Box … Root CA' khỏi cert9.db của mọi hồ sơ (cố gắng hết sức: cần certutil)."""
    dem = 0
    mau = [GOC + "/home/*/.mozilla/firefox/*/cert9.db", GOC + "/root/.mozilla/firefox/*/cert9.db",
           GOC + "/home/*/snap/firefox/common/.mozilla/firefox/*/cert9.db"]
    for pattern in mau:
        for db in glob.glob(pattern):
            thu_muc = "sql:" + os.path.dirname(db)
            r = subprocess.run(["certutil", "-L", "-d", thu_muc], capture_output=True, text=True)
            for dong in r.stdout.splitlines():
                m = TEN_CHUNG_CHI.match(dong.strip())
                if m and subprocess.run(["certutil", "-D", "-n", m.group(1), "-d", thu_muc], capture_output=True).returncode == 0:
                    dem += 1
    return dem


def go():
    doi = False
    goi = doc_json(FIREFOX_GOI)
    if os.path.exists(FIREFOX_ETC):
        if goi is None:
            os.remove(FIREFOX_ETC)
        else:
            ghi_neu_doi(FIREFOX_ETC, goi)
        doi = True
    for p in CHROME_FILES:
        if os.path.exists(p):
            os.remove(p)
            doi = True
    n = 0
    try:
        n = go_khoi_ho_so_firefox()
    except FileNotFoundError:
        print("CẢNH BÁO: chưa có certutil (gói libnss3-tools) — không gỡ được CA khỏi hồ sơ Firefox đã nạp trước đó", file=sys.stderr)
    if n:
        doi = True
        print(f"Đã gỡ {n} chứng chỉ OneBee khỏi hồ sơ Firefox")
    return doi


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "cai":
        thay_doi = cai(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "go":
        thay_doi = go()
    else:
        sys.exit("Cách dùng: onebee-chinh-sach-trinh-duyet.py cai <file-pem-CA> | go")
    print("đã đổi" if thay_doi else "không đổi")
