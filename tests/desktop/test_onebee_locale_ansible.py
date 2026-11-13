#!/usr/bin/env python3
"""Kiểm thử: mọi chỗ bộ cài gọi `ansible-playbook` chạy được bất kể locale của người chạy.

Mint cài bằng tiếng Việt ghi `LANG=vi_VN` (không có `.UTF-8`). Python chuẩn hóa tên này thành bảng mã TCVN, và ansible-core
dừng ngay với "ERROR: Ansible requires the locale encoding to be UTF-8; Detected TCVN." — dù glibc dùng UTF-8 cho vi_VN.
Trên Box, quản trị SSH từ máy trạm Mint mang theo LANG=vi_VN (SendEnv/AcceptEnv mặc định) mà Box chưa tạo locale đó
→ ansible-core báo "could not initialize the preferred locale".

Cách kiểm: lấy nguyên văn từng lệnh gọi `ansible-playbook` trong các script (gộp dòng nối bằng `\\`), chạy bằng bash với
`ansible-playbook` GIẢ làm đúng phép kiểm locale của ansible-core, dưới các locale "xấu" của người chạy.
Ansible giả ghi lại locale hiệu lực theo thứ tự POSIX (LC_ALL → LC_CTYPE → LANG); test chuẩn hóa nó như
`locale.getlocale()` của ansible-core (phải ra UTF-8) và đòi đúng `C.UTF-8` — locale có sẵn trong glibc của Ubuntu 24.04/Mint 22
nên không cần locale-gen. Không gọi setlocale thật vì kết quả phụ thuộc máy chạy test. Chạy: python3 -m unittest
"""
import locale
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.abspath(os.path.join(HERE, "../.."))
SCRIPT_GOI_ANSIBLE = [
    "desktop/onebee-install.sh",
    "box/onebee-box-install.sh",
    "box/ansible/roles/box-stack/templates/onebee-box.sh.j2",   # sudo onebee-box cap-nhat-may / dong-bo-may
]
LOCALE_XAU = [
    {"LANG": "vi_VN"},                                   # Mint cài bằng tiếng Việt
    {"LANG": "vi_VN", "LC_CTYPE": "vi_VN"},
    {"LANG": "vi_VN.UTF-8", "LC_ALL": "vi_VN"},
    {"LANG": "vi_VN.UTF-8", "LC_ALL": "vi_VN.UTF-8"},    # có thể chưa tạo locale này trên Box
    {"LANG": "C", "LC_ALL": "POSIX"},
]

# Viết bằng bash: python3 khởi động trong locale lạ tự ép LC_CTYPE=C.UTF-8 (PEP 538) nên không đọc được locale người chạy.
# Ghi locale hiệu lực theo thứ tự POSIX (biến rỗng coi như không đặt), phép kiểm bảng mã làm trong test.
ANSIBLE_GIA = r'''#!/usr/bin/env bash
printf '%s\n' "${LC_ALL:-${LC_CTYPE:-${LANG:-C}}}" >>"${ONEBEE_GHI}"
'''


def lenh_goi_ansible(duong_dan):
    """Các lệnh (đã gộp dòng nối `\\`) có gọi ansible-playbook, bỏ dòng chú thích."""
    with open(os.path.join(GOC, duong_dan), encoding="utf-8") as f:
        noi_dung = f.read()
    lenh = []
    for dong in re.sub(r"\\\n", " ", noi_dung).splitlines():
        if re.search(r"(^|\s)ansible-playbook\s", dong) and not dong.lstrip().startswith("#"):
            lenh.append(dong.strip())
    return lenh


class NguyenNhanLoi(unittest.TestCase):
    def test_vi_VN_khong_co_utf8_bi_hieu_la_tcvn(self):
        # Ghi lại đúng nguyên nhân thấy trên máy Mint: không phải lỗi của glibc mà do Python chuẩn hóa tên locale
        self.assertEqual(locale._parse_localename("vi_VN"), ("vi_VN", "TCVN"))
        self.assertEqual(locale._parse_localename("vi_VN.UTF-8")[1], "UTF-8")


@unittest.skipUnless(shutil.which("bash"), "cần bash")
class AnsibleKhongPhuThuocLocaleNguoiChay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_dir = os.path.join(self.tmp, "bin")
        os.mkdir(bin_dir)
        gia = os.path.join(bin_dir, "ansible-playbook")
        with open(gia, "w", encoding="utf-8") as f:
            f.write(ANSIBLE_GIA)
        os.chmod(gia, 0o755)
        self.ghi = os.path.join(self.tmp, "ghi")
        self.env = {"PATH": bin_dir + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
                    "ONEBEE_GHI": self.ghi, "HOME": self.tmp,
                    # biến mà các lệnh trong script dùng; giá trị không quan trọng với phép kiểm locale
                    "PLAYBOOK_DIR": self.tmp, "LOG_FILE": os.path.join(self.tmp, "log"),
                    "SSH_DIR": self.tmp, "LIB": self.tmp, "inv": os.path.join(self.tmp, "inv"),
                    "log": os.path.join(self.tmp, "log"), "playbook": "site.yml"}

    def chay(self, lenh, locale_nguoi_chay):
        if os.path.exists(self.ghi):
            os.remove(self.ghi)
        env = {**self.env, **locale_nguoi_chay}
        p = subprocess.run(["bash", "-c", "set -o pipefail; " + lenh], cwd=self.tmp, env=env,
                           capture_output=True, text=True, timeout=30)
        with open(self.ghi, encoding="utf-8") as f:
            da_goi = f.read().split()
        return p, da_goi

    def test_moi_lenh_goi_ansible_dat_locale_utf8(self):
        for duong_dan in SCRIPT_GOI_ANSIBLE:
            cac_lenh = lenh_goi_ansible(duong_dan)
            self.assertTrue(cac_lenh, "Không thấy lệnh ansible-playbook trong %s" % duong_dan)
            for lenh in cac_lenh:
                for loc in LOCALE_XAU:
                    with self.subTest(script=duong_dan, locale=loc):
                        p, da_goi = self.chay(lenh, loc)
                        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                        self.assertEqual(len(da_goi), 1, lenh)
                        bang_ma = locale._parse_localename(da_goi[0])[1]
                        self.assertIn((bang_ma or "").lower(), ("utf-8", "utf8"),
                                      "ansible-core sẽ báo: Ansible requires the locale encoding to be UTF-8; "
                                      "Detected %s.\n%s" % (bang_ma, lenh))
                        self.assertEqual(da_goi[0], "C.UTF-8", "locale %s có thể chưa được tạo trên máy\n%s"
                                         % (da_goi[0], lenh))


if __name__ == "__main__":
    unittest.main()
