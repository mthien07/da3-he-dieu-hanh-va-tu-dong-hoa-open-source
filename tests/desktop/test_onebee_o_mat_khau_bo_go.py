#!/usr/bin/env python3
"""Kiểm thử: bộ gõ tiếng Việt (Telex) không được thêm dấu vào ô mật khẩu của Firefox.
ibus-bamboo không phân biệt ô mật khẩu, nên role vietnamese đặt chính sách Firefox intl.ime.use_simple_context_on_password_field
(ô mật khẩu dùng ngữ cảnh nhập đơn giản, phím không qua IBus) vào file chính sách dùng chung của máy, và chính sách đó phải
còn nguyên khi role ket-noi-box ghi /etc/firefox/policies/policies.json. Chạy: python3 -m unittest"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES = os.path.join(HERE, "../../desktop/ansible/roles")
VI_DEFAULTS = os.path.join(ROLES, "vietnamese/defaults/main.yml")
VI_TASKS = os.path.join(ROLES, "vietnamese/tasks/main.yml")
SITE = os.path.join(HERE, "../../desktop/ansible/site.yml")
TRINH_DUYET = os.path.join(ROLES, "ket-noi-box/files/onebee-chinh-sach-trinh-duyet.py")
TAO_CA = os.path.join(HERE, "../../box/ansible/roles/box-stack/files/onebee-ca.sh")
FILE_DUNG_CHUNG = "/usr/lib/firefox/distribution/policies.json"
KHOA = "intl.ime.use_simple_context_on_password_field"


def doc_yaml(p):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


class ChinhSachFirefoxOMatKhau(unittest.TestCase):
    def test_khoa_bat_va_khoa_cung(self):
        cs = doc_yaml(VI_DEFAULTS)["onebee_firefox_chinh_sach_o_mat_khau"]
        self.assertEqual(cs, {"policies": {"Preferences": {KHOA: {"Value": True, "Status": "locked"}}}})

    def test_ghi_vao_file_chinh_sach_dung_chung_bang_cach_tron(self):
        tac_vu = [t for t in doc_yaml(VI_TASKS) if "ansible.builtin.copy" in t
                  and t["ansible.builtin.copy"].get("dest") == FILE_DUNG_CHUNG]
        self.assertEqual(len(tac_vu), 1)
        t = tac_vu[0]
        nd = t["ansible.builtin.copy"]["content"]
        # Trộn vào nội dung đang có (không xóa chính sách khác), xuất JSON
        self.assertIn("combine(onebee_firefox_chinh_sach_o_mat_khau, recursive=True)", nd)
        self.assertIn("to_nice_json", nd)
        self.assertIn("from_json", t["vars"]["onebee_ff_cu"])
        # Máy không có Firefox bản .deb thì bỏ qua, không tạo thư mục lạ
        self.assertIn("onebee_ff_phan_phoi.stat.isdir", str(t["when"]))

    def test_khong_dat_bang_file_pref_vi_firefox_khong_nap(self):
        with open(VI_TASKS, encoding="utf-8") as f:
            self.assertNotIn("defaults/pref", "\n".join(d for d in f if not d.lstrip().startswith("#")))

    def test_role_vietnamese_chay_truoc_ket_noi_box(self):
        # ket-noi-box trộn file dùng chung vào /etc/firefox/policies/policies.json → file dùng chung phải có khóa trước
        roles = doc_yaml(SITE)[0]["roles"]
        self.assertLess(roles.index("vietnamese"), roles.index("ket-noi-box"))


@unittest.skipUnless(shutil.which("openssl"), "cần openssl")
class KhoaConKhiNoiBox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        g = self.tmp.name
        subprocess.run([TAO_CA, f"{g}/ca", "anphu", "192.168.1.10"], capture_output=True, check=True)
        self.pem = f"{g}/ca/root.crt"
        self.env = dict(os.environ, ONEBEE_GOC=f"{g}/goc")
        self.etc = f"{g}/goc/etc/firefox/policies/policies.json"
        dung_chung = f"{g}/goc{FILE_DUNG_CHUNG}"
        os.makedirs(os.path.dirname(dung_chung))
        self.cs = doc_yaml(VI_DEFAULTS)["onebee_firefox_chinh_sach_o_mat_khau"]
        with open(dung_chung, "w", encoding="utf-8") as f:
            json.dump(self.cs, f)

    def td(self, *a):
        r = subprocess.run([TRINH_DUYET, *a], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_cai_ca_va_bat_https_van_giu_khoa_roi_go_tra_lai(self):
        self.td("cai", self.pem, "--https", "192.168.1.10")
        with open(self.etc, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["policies"]["Preferences"], self.cs["policies"]["Preferences"])
        self.td("go")
        with open(self.etc, encoding="utf-8") as f:
            self.assertEqual(json.load(f), self.cs)


if __name__ == "__main__":
    unittest.main()
