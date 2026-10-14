#!/usr/bin/env python3
"""Cài / gỡ CA của OneBee Box vào trình duyệt (Firefox, Chromium, Chrome) bằng chính sách doanh nghiệp (rà soát bảo mật F3).
Cách dùng: onebee-chinh-sach-trinh-duyet.py cai <file-pem-CA> [--https <IP-Box>] | go
 - Firefox: chính sách Certificates.Install ghi vào /etc/firefox/policies/policies.json. File ở /etc THAY THẾ file
   /usr/lib/firefox/distribution/policies.json của gói → trộn nội dung gói vào rồi mới thêm mục OneBee; khi gỡ, trả về đúng nội dung gói
   (hoặc xóa file nếu gói không có). Firefox KHÔNG tự gỡ chứng chỉ đã nạp khi bỏ chính sách → 'go' gỡ thêm khỏi từng hồ sơ bằng certutil (cố gắng hết sức).
   Xoay CA: mỗi lần 'cai' dọn khỏi từng hồ sơ mọi chứng chỉ cùng tên CA hiện tại nhưng KHÁC vân tay CA hiện tại (CA mới cùng mã đơn vị trùng
   tên CA cũ) — không dựa vào dấu "lần cài trước", nên lần gỡ sót vì lỗi tạm (thiếu certutil, đĩa chưa gắn…) tự lành ở lần sau, và xoay nhiều lần liên tiếp không để sót CA nào.
 - Có --https <IP>: Firefox và Chromium/Chrome mở sẵn Box bằng https:// (trang chủ + dấu trang do quản trị đặt), để người dùng không gõ tay
   http:// (HSTS vô tác dụng với địa chỉ IP). KHÔNG bật DisableSecurityBypass / HTTPS-Only: máy in, thiết bị LAN dùng chứng chỉ tự ký vẫn phải
   mở được. Tập huấn: cảnh báo chứng chỉ ở địa chỉ Box = dấu hiệu bị tấn công, không bấm qua.
 - Chromium/Chrome: CACertificatesWithConstraints — trình duyệt tự áp ràng buộc tên của CA; gỡ = xóa file chính sách.
Biến ONEBEE_GOC: tiền tố thư mục gốc (để kiểm thử); mặc định rỗng."""
import base64
import glob
import hashlib
import importlib.util
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
HO_SO_FIREFOX = [GOC + "/home/*/.mozilla/firefox/*/cert9.db", GOC + "/root/.mozilla/firefox/*/cert9.db",
                 GOC + "/home/*/snap/firefox/common/.mozilla/firefox/*/cert9.db"]


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
    """(danh sách CIDR, danh sách tên DNS) mà CA cho phép — đọc bằng bộ đọc NGHIÊM của onebee-kiem-ca.py (cùng thư mục), để trình duyệt tự áp."""
    spec = importlib.util.spec_from_file_location("onebee_kiem_ca", os.path.join(os.path.dirname(os.path.abspath(__file__)), "onebee-kiem-ca.py"))
    kiem = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kiem)
    ips, dns = kiem.rang_buoc_tu_pem(file_pem)
    cidr = []
    for x in ips:
        ip, mask = x.split("/")
        cidr.append(f"{ip}/{sum(bin(int(o)).count('1') for o in mask.split('.'))}")
    return cidr, dns


DICH_VU = [("Trợ lý AI", 3000, ""), ("Tự động hóa (n8n)", 5678, ""), ("Giám sát", 3001, ""),
           ("Báo cần hỗ trợ", 5678, "form/onebee-ho-tro"), ("Nhập đơn hàng", 5678, "form/onebee-don-hang")]


def dau_trang(ip):
    """Danh sách dấu trang do quản trị đặt (định dạng ManagedBookmarks dùng chung cho Firefox và Chrome)."""
    return [{"toplevel_name": "OneBee Box"}, {"name": "Trang giới thiệu OneBee Box", "url": f"https://{ip}/"}] + \
        [{"name": ten, "url": f"https://{ip}:{cong}/{duong}"} for ten, cong, duong in DICH_VU]


def cai(file_pem, ip_https=None):
    doi = False
    goi = doc_json(FIREFOX_GOI) or {}
    cs = goi.get("policies", {}) if isinstance(goi.get("policies", {}), dict) else {}
    goi = {"policies": dict(cs)}
    chung_chi = dict(goi["policies"].get("Certificates", {}))
    chung_chi["Install"] = [x for x in chung_chi.get("Install", []) if x != DICH_CA] + [DICH_CA]
    goi["policies"]["Certificates"] = chung_chi
    if ip_https:
        goi["policies"]["Homepage"] = {"URL": f"https://{ip_https}/", "StartPage": "homepage"}
        goi["policies"]["ManagedBookmarks"] = dau_trang(ip_https)
    doi |= ghi_neu_doi(FIREFOX_ETC, goi)
    b64 = pem_sang_der_b64(file_pem)
    cidr, dns = rang_buoc(file_pem)
    for p in CHROME_FILES:
        chinh_sach = {"CACertificatesWithConstraints": [
            {"certificate": b64, "constraints": {"permitted_cidrs": cidr, "permitted_dns_names": dns}}]}
        if ip_https:
            chinh_sach.update(HomepageLocation=f"https://{ip_https}/", ManagedBookmarks=dau_trang(ip_https))
        doi |= ghi_neu_doi(p, chinh_sach)
    ten, vt = ten_ca(file_pem), van_tay(open(file_pem, encoding="ascii").read())
    n = 0
    try:
        n = go_ca_khac_khoi_ho_so_firefox(ten, vt)
    except FileNotFoundError:
        print("CẢNH BÁO: chưa có certutil (gói libnss3-tools) — không gỡ được CA cũ khỏi hồ sơ Firefox", file=sys.stderr)
    if n:
        doi = True
        print(f"Đã gỡ {n} chứng chỉ OneBee mang vân tay CA cũ khỏi hồ sơ Firefox")
    return doi


def van_tay(pem):
    """Vân tay SHA-256 (hex thường) của từng chứng chỉ trong chuỗi PEM."""
    return [hashlib.sha256(base64.b64decode(k)).hexdigest()
            for k in re.findall(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem, re.S)]


def ho_so_firefox():
    """(thư mục certutil, các tên 'OneBee Box … Root CA' trong đó) của mọi hồ sơ Firefox; thiếu certutil → FileNotFoundError."""
    for db in sorted(set(sum((glob.glob(m) for m in HO_SO_FIREFOX), []))):
        thu_muc = "sql:" + os.path.dirname(db)
        r = subprocess.run(["certutil", "-L", "-d", thu_muc], capture_output=True, text=True)
        ten = [m.group(1) for m in (TEN_CHUNG_CHI.match(d.strip()) for d in r.stdout.splitlines()) if m]
        yield thu_muc, list(dict.fromkeys(ten))   # nhiều chứng chỉ cùng tên thì certutil -L in tên nhiều lần


def go_khoi_ho_so_firefox():
    """Xóa chứng chỉ 'OneBee Box … Root CA' khỏi cert9.db của mọi hồ sơ (cố gắng hết sức: cần certutil)."""
    dem = 0
    for thu_muc, ds_ten in ho_so_firefox():
        for ten in ds_ten:
            for _ in range(20):   # mọi bản cùng tên; có giới hạn để không lặp vô hạn
                if subprocess.run(["certutil", "-D", "-n", ten, "-d", thu_muc], capture_output=True).returncode != 0:
                    break
                dem += 1
    return dem


def van_tay_theo_ten(thu_muc, ten):
    """Vân tay của mọi chứng chỉ mang tên `ten` trong hồ sơ (certutil -L -n ... -a in hết các bản cùng tên)."""
    pem = subprocess.run(["certutil", "-L", "-d", thu_muc, "-n", ten, "-a"], capture_output=True, text=True).stdout
    return van_tay(pem)


def ten_ca(file_pem):
    """Tên chứng chỉ trong cert9.db = CN của CA ('OneBee Box <mã> Root CA'); không đọc được CN đúng dạng → None (không gỡ gì, tránh xóa nhầm)."""
    r = subprocess.run(["openssl", "x509", "-in", file_pem, "-noout", "-subject", "-nameopt", "RFC2253"], capture_output=True, text=True, check=True)
    m = re.search(r"(?:^subject=|,)CN=([^,]+)", r.stdout.strip())
    return m.group(1) if m and re.fullmatch(r"OneBee Box .+? Root CA", m.group(1)) else None


def go_ca_khac_khoi_ho_so_firefox(ten_hien_tai, van_tay_hien_tai):
    """Gỡ khỏi mọi hồ sơ các chứng chỉ mang tên CA hiện tại nhưng vân tay KHÁC CA hiện tại; tên khác (CA của đơn vị khác trong hồ sơ kỹ thuật viên)
    giữ nguyên. certutil chỉ xóa theo TÊN và có thể xóa bản mới trước → xóa lặp, liệt kê lại sau mỗi lần, tới khi tên đó hết bản lạ. CA hiện tại
    lỡ bị xóa theo thì chính sách Certificates.Install nạp lại khi Firefox mở. Trả số chứng chỉ KHÁC CA hiện tại đã gỡ (không đếm CA hiện tại)."""
    if not ten_hien_tai:
        return 0
    dem = 0
    for thu_muc, ds_ten in ho_so_firefox():
        if ten_hien_tai not in ds_ten:
            continue
        la = [v for v in van_tay_theo_ten(thu_muc, ten_hien_tai) if v not in van_tay_hien_tai]
        dau = len(la)
        for _ in range(20):   # chặn vòng lặp vô hạn nếu certutil báo xóa được mà không xóa
            if not la or subprocess.run(["certutil", "-D", "-n", ten_hien_tai, "-d", thu_muc], capture_output=True).returncode != 0:
                break
            la = [v for v in van_tay_theo_ten(thu_muc, ten_hien_tai) if v not in van_tay_hien_tai]
        dem += dau - len(la)
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
    if len(sys.argv) in (3, 5) and sys.argv[1] == "cai" and (len(sys.argv) == 3 or sys.argv[3] == "--https"):
        thay_doi = cai(sys.argv[2], sys.argv[4] if len(sys.argv) == 5 else None)
    elif len(sys.argv) == 2 and sys.argv[1] == "go":
        thay_doi = go()
    else:
        sys.exit("Cách dùng: onebee-chinh-sach-trinh-duyet.py cai <file-pem-CA> [--https <IP-Box>] | go")
    print("đã đổi" if thay_doi else "không đổi")
