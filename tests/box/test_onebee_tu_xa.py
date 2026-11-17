#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm lệnh duyệt / thu hồi / hết hạn máy trạm đi công tác (ADR 0008) mà KHÔNG cần Box thật:
dựng onebee-box từ mẫu .j2 (như check-diagnosis.sh), thay tailscale/conntrack/smbcontrol/onebee-tuong-lua/logger/htpasswd
bằng lệnh GIẢ ghi lại lời gọi; openssl + CA riêng là THẬT. Chạy: python3 -m unittest tests.box.test_onebee_tu_xa"""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest

import jinja2
import yaml

# Windows: system32 có bash.exe của WSL, CreateProcess ưu tiên nó trước PATH → chọn bash đúng bằng đường đầy đủ
BASH = shutil.which("bash") or "bash"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

IP_BOX_TS = "100.64.0.1"
IP_MAY = "100.64.0.7"
HOSTS_ALLOW_GOC = "127. 10. 172.16.0.0/12 192.168."
IP_KY_THUAT = "100.64.9.9"

TS_STATUS = {
    "Self": {"TailscaleIPs": [IP_BOX_TS, "fd7a:115c:a1e0::1"]},
    "Peer": {"k1": {"HostName": "ketoan-01", "TailscaleIPs": [IP_MAY, "fd7a:115c:a1e0::7"],
                    "OS": "linux", "Online": True, "LastSeen": "2026-11-17T01:00:00Z"}},
}


class TuXa(unittest.TestCase):
    DUYET = ("duyet-tu-xa", "ketoan-01")

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.t = cls.tmp.name.replace("\\", "/")   # đường dẫn vào văn bản script — bash nuốt dấu \
        for d in ("lib", "bin", "secrets", "ssh", "box", "data", "log", "sim", "tu-xa", "mnt/onebee-sao-luu"):
            os.makedirs(f"{t}/{d}", exist_ok=True)
        cls.env = dict(os.environ, PATH=f"{t}/bin{os.pathsep}{os.environ['PATH']}", SIM=f"{t}/sim",
                       ONEBEE_AI_RAG_DB=f"{t}/data/ai-rag.sqlite3", PYTHONUTF8="1",
                       MSYS2_ARG_CONV_EXCL="*")   # Windows: Git-bash tự đổi "-subj /O=..." thành đường dẫn — tắt đi (Linux: vô hại)
        cls.dung_lenh()
        shutil.copy(f"{ROOT}/box/ansible/roles/box-stack/files/onebee-ca.sh", f"{t}/lib/onebee-ca.sh")
        shutil.copy(f"{ROOT}/box/ansible/roles/box-fleet/files/onebee-may-tram.py", f"{t}/lib/onebee-may-tram.py")
        shutil.copy(f"{ROOT}/box/ansible/roles/box-ai/files/onebee-ai-rag.py", f"{t}/lib/onebee-ai-rag.py")
        subprocess.run([BASH, f"{t}/lib/onebee-ca.sh", f"{t}/secrets/ca", "kiem-thu", "127.0.0.1"],
                       capture_output=True, env=cls.env, check=True)
        open(f"{t}/ssh/quan-tri.pub", "w").write("ssh-ed25519 AAAAtest-key quan-tri@box")
        # Lệnh giả ghi lại lời gọi vào ${SIM}/*.log
        gia = lambda ten, than: (open(f"{t}/bin/{ten}", "w", encoding="utf-8").write(f"#!/usr/bin/env bash\n{than}\n"),
                                 os.chmod(f"{t}/bin/{ten}", 0o755))
        gia("tailscale", 'case "$*" in\n'
                         '  "status --json") cat "${SIM}/ts-status.json" 2>/dev/null || echo "{}" ;;\n'
                         '  "debug prefs") cat "${SIM}/ts-prefs.json" 2>/dev/null || echo \'{"RunSSH": false}\' ;;\n'
                         '  "status") [[ -e "${SIM}/ts-dung" ]] && exit 1; exit 0 ;;\n'
                         '  *) exit 2 ;;\nesac')
        gia("conntrack", 'echo "$*" >> "${SIM}/conntrack.log"; echo "conntrack v1.4.7: 1 flow entries have been deleted."')
        gia("smbcontrol", 'exit 0')
        gia("logger", 'echo "$*" >> "${SIM}/logger.log"')
        gia("systemctl", 'u="${!#}"; [[ -e "${SIM}/dung-${u}" ]] && exit 3; exit 0')
        gia("onebee-tuong-lua", 'echo "$*" >> "${SIM}/tuong-lua.log"')
        gia("htpasswd", 'echo "$*" >> "${SIM}/htpasswd.log"')
        gia("flock", 'exit 0')
        gia("docker", 'exit 0')
        # install giả: msys từ chối chmod/chown trên thư mục (Linux thật dùng install gốc)
        gia("install", 'd=0; a=()\n'
                       'while [[ $# -gt 0 ]]; do case "$1" in\n'
                       '  -d) d=1 ;; -m) shift ;; -[ogp]) shift ;; -*) ;;\n'
                       '  *) a+=("$1") ;; esac; shift; done\n'
                       'if [[ $d == 1 ]]; then mkdir -p "${a[@]}"; else cp "${a[0]}" "${a[1]}"; fi')
        gia("chown", 'exit 0')   # msys không có nhóm 1000 (Linux thật vẫn dùng chown gốc)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def dung_lenh(cls):
        """Dựng lệnh onebee-box từ mẫu (như bộ cài Ansible), đường dẫn máy thật → thư mục tạm, bỏ kiểm quyền root."""
        tpl = f"{ROOT}/box/ansible/roles/box-stack/templates"
        v = yaml.safe_load(open(f"{ROOT}/box/ansible/group_vars/all.yml", encoding="utf-8"))
        v.update(onebee_box_secrets=f"{cls.t}/secrets", onebee_box_ssh_dir=f"{cls.t}/ssh", onebee_box_data=f"{cls.t}/data",
                 onebee_box_dir=f"{cls.t}/box", onebee_box_backup_repo=f"{cls.t}/mnt/onebee-sao-luu/restic-box",
                 onebee_box_ip="127.0.0.1", onebee_box_ma_don_vi="kiem-thu", onebee_box_tailscale_cho_phep=[IP_KY_THUAT])
        env = jinja2.Environment(keep_trailing_newline=True)
        env.filters.update(to_json=lambda x: json.dumps(x, ensure_ascii=False), quote=shlex_quote, bool=bool)
        t = cls.t

        def sua(s):
            return (s.replace("#!/usr/bin/env bash\n", f'#!/usr/bin/env bash\nexport PATH="{t}/bin:$PATH"\n', 1)
                     .replace("/usr/local/lib/onebee-box", f"{t}/lib")
                     .replace("/var/log/onebee-box", f"{t}/log")
                     .replace("/run/onebee-box-tu-xa.lock", f"{t}/lock-tu-xa")
                     .replace("/run/onebee-box.lock", f"{t}/lock")
                     .replace("/etc/onebee-box/tu-xa", f"{t}/tu-xa")
                     .replace("/etc/onebee-box/tuong-lua-tu-xa.conf", f"{t}/tuong-lua-tu-xa.conf")
                     .replace("/etc/onebee-box/samba-tu-xa.conf", f"{t}/samba-tu-xa.conf")
                     .replace("/usr/local/sbin/onebee-tuong-lua", f"{t}/bin/onebee-tuong-lua")
                     .replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||"))

        for src, dst in (("onebee-box-common.sh.j2", "lib/common.sh"), ("onebee-box-sao-luu.sh.j2", "lib/sao-luu.sh"),
                         ("onebee-box-tu-xa.sh.j2", "lib/tu-xa.sh"), ("onebee-box-chan-doan.sh.j2", "lib/chan-doan.sh"),
                         ("onebee-box.sh.j2", "bin/onebee-box")):
            duong = f"{tpl}/{src}"
            if not os.path.exists(duong):
                continue   # mẫu chưa viết (bài kiểm đang trượt) — onebee-box vẫn dựng được phần còn lại
            out = sua(env.from_string(open(duong, encoding="utf-8").read()).render(**v))
            open(f"{t}/{dst}", "w", encoding="utf-8").write(out)
        os.chmod(f"{t}/bin/onebee-box", 0o755)

    def setUp(self):
        # Xoá mọi trạng thái bài trước có thể làm bài sau thấy "không đổi": sim, lượt duyệt, hai tệp conf, dấu thu hồi, danh sách máy
        for d in ("sim", "tu-xa", "data/may-da-cap", "secrets/thu-hoi", "secrets/ca-da-dong-bo"):
            shutil.rmtree(f"{self.t}/{d}", ignore_errors=True)
        os.makedirs(f"{self.t}/sim", exist_ok=True)
        for f in ("tuong-lua-tu-xa.conf", "samba-tu-xa.conf"):
            duong = f"{self.t}/{f}"
            os.path.exists(duong) and os.remove(duong)
        for ten in os.listdir(f"{self.t}/secrets"):
            if ten.startswith("may-") or ten == "https-da-bat":
                os.remove(f"{self.t}/secrets/{ten}")

    def tep(self, *p):
        return os.path.join(self.t, *p)

    def chay(self, *args, stdin=None):
        stdin_tep = None
        if stdin is not None:
            stdin_tep = tempfile.TemporaryFile()
            stdin_tep.write(stdin.encode("utf-8"))   # ghi nhị phân: text mode của Windows dịch \n thành \r\n
            stdin_tep.seek(0)
        try:
            return subprocess.run([BASH, self.tep("bin/onebee-box"), *args], stdin=stdin_tep, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", env=self.env, cwd=self.t, timeout=180)
        finally:
            if stdin_tep is not None:
                stdin_tep.close()

    def tao_may(self, ten="ketoan-01", ts_status=None):
        open(self.tep("secrets", f"may-{ten}-http"), "w").write(f"pw-http-{ten}")
        open(self.tep("secrets", f"may-{ten}-repo"), "w").write(f"pw-repo-{ten}")
        open(self.tep("secrets", "https-da-bat"), "w").write("")
        json.dump(ts_status if ts_status is not None else TS_STATUS, open(self.tep("sim/ts-status.json"), "w"))

    def dat_luot(self, ten="ketoan-01", ip=IP_MAY, het_han=0, duyet_luc=None, nguoi="quantri"):
        os.makedirs(self.tep("tu-xa"), exist_ok=True)
        duyet_luc = int(time.time()) if duyet_luc is None else duyet_luc
        open(self.tep("tu-xa", ten), "w").write(f"IP={ip}\nHET_HAN={het_han}\nDUYET_LUC={duyet_luc}\nNGUOI_DUYET={nguoi}\n")

    def log(self, ten):
        duong = self.tep("sim", f"{ten}.log")
        return open(duong, encoding="utf-8").read().splitlines() if os.path.exists(duong) else []

    def test_duyet_ip_ghi_trang_thai_va_sinh_hai_tep(self):
        self.tao_may()
        r = self.chay(*self.DUYET, "--ip", IP_MAY, "--ngay", "1", "--dong-y")
        self.assertEqual(r.returncode, 0, r.stderr)
        dong = dict(x.split("=", 1) for x in open(self.tep("tu-xa/ketoan-01"), encoding="utf-8").read().splitlines())
        self.assertEqual(set(dong), {"IP", "HET_HAN", "DUYET_LUC", "NGUOI_DUYET"})
        self.assertEqual(dong["IP"], IP_MAY)
        self.assertAlmostEqual(int(dong["HET_HAN"]), time.time() + 86400, delta=120)
        self.assertAlmostEqual(int(dong["DUYET_LUC"]), time.time(), delta=120)
        self.assertEqual(dong["NGUOI_DUYET"], "onebee")
        self.assertEqual(open(self.tep("tuong-lua-tu-xa.conf"), encoding="utf-8").read(), f'TU_XA_CHO_PHEP="{IP_MAY}"\n')
        self.assertEqual(open(self.tep("samba-tu-xa.conf"), encoding="utf-8").read(),
                         f"hosts allow = {HOSTS_ALLOW_GOC} {IP_KY_THUAT} {IP_MAY}\n")
        self.assertIn(f"sudo onebee-cong-tac bat --box-tu-xa {IP_BOX_TS}", r.stdout)
        self.assertEqual(self.log("conntrack"), [])   # duyệt không đụng conntrack
        self.assertEqual(self.log("tuong-lua"), ["bat"])

    def test_duyet_theo_ten_may(self):
        self.tao_may()
        r = self.chay(*self.DUYET, "--dong-y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"IP={IP_MAY}", open(self.tep("tu-xa/ketoan-01"), encoding="utf-8").read())
        # không có thiết bị nào tên đúng → dừng, đòi --ip, không ghi gì
        self.tao_may("may-trong", ts_status={"Self": TS_STATUS["Self"], "Peer": {}})
        r = self.chay("duyet-tu-xa", "may-trong", "--dong-y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--ip", r.stderr)
        self.assertFalse(os.path.exists(self.tep("tu-xa/may-trong")))
        # hai thiết bị trùng tên → dừng (tránh duyệt nhầm)
        self.tao_may("ketoan-02", ts_status={"Self": TS_STATUS["Self"], "Peer": {
            "k1": TS_STATUS["Peer"]["k1"], "k2": dict(TS_STATUS["Peer"]["k1"], TailscaleIPs=["100.64.0.8"])}})
        r = self.chay("duyet-tu-xa", "ketoan-02", "--dong-y")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.tep("tu-xa/ketoan-02")))

    def test_tu_choi_cac_truong_hop(self):
        self.tao_may()
        khong_tep = lambda: self.assertFalse(os.path.exists(self.tep("tu-xa/ketoan-01")))
        # máy chưa cấp
        r = self.chay("duyet-tu-xa", "may-chua-cap", "--ip", IP_MAY, "--dong-y")
        self.assertNotEqual(r.returncode, 0)
        # HTTPS chưa bật
        os.remove(self.tep("secrets/https-da-bat"))
        r = self.chay(*self.DUYET, "--ip", IP_MAY, "--dong-y")
        self.assertNotEqual(r.returncode, 0)
        khong_tep()
        open(self.tep("secrets/https-da-bat"), "w").write("")
        # IP ngoài dải Tailscale, IP của chính Box, IP của máy kỹ thuật
        for ip_sai in ("192.168.1.55", IP_BOX_TS, IP_KY_THUAT, "100.64.0.999.1"):
            r = self.chay(*self.DUYET, "--ip", ip_sai, "--dong-y")
            self.assertNotEqual(r.returncode, 0, ip_sai)
            khong_tep()
        # IP đã duyệt cho máy khác
        self.dat_luot("may-02", "100.64.0.8")
        r = self.chay(*self.DUYET, "--ip", "100.64.0.8", "--dong-y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("may-02", r.stderr)
        khong_tep()
        # --ngay ngoài 1..365
        for ngay in ("0", "366", "abc"):
            r = self.chay(*self.DUYET, "--ip", IP_MAY, "--ngay", ngay, "--dong-y")
            self.assertNotEqual(r.returncode, 0, ngay)
            khong_tep()

    def test_hoi_xac_nhan(self):
        self.tao_may()
        r = self.chay(*self.DUYET, "--ip", IP_MAY, stdin="duyet\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(self.tep("tu-xa/ketoan-01")))
        r = self.chay(*self.DUYET, "--ip", IP_MAY, stdin="khong\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(self.tep("tu-xa/ketoan-01")))   # lượt trước vẫn nguyên

    def test_khong_ngay_la_khong_han(self):
        self.tao_may()
        r = self.chay(*self.DUYET, "--ip", IP_MAY, "--dong-y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HET_HAN=0", open(self.tep("tu-xa/ketoan-01"), encoding="utf-8").read())
        r = self.chay("tu-xa-ap-dung")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(self.tep("tu-xa/ketoan-01")))
        self.assertEqual(self.log("conntrack"), [])

    def test_thu_hoi(self):
        self.tao_may()
        self.dat_luot(het_han=int(time.time()) + 3600)
        r = self.chay("thu-hoi-tu-xa", "ketoan-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.tep("tu-xa/ketoan-01")))
        self.assertIn(f"-D -s {IP_MAY}", " ".join(self.log("conntrack")))
        self.assertEqual(self.log("tuong-lua"), ["bat"])
        self.assertIn("Đã thu hồi quyền từ xa", r.stdout)
        # thu hồi lần nữa: không có gì, thoát 0
        r = self.chay("thu-hoi-tu-xa", "ketoan-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("không có gì để thu hồi", r.stdout)

    def test_thu_hoi_may_thu_hoi_luon_tu_xa(self):
        self.tao_may()
        self.dat_luot(het_han=int(time.time()) + 3600)
        r = self.chay("thu-hoi-may", "ketoan-01", "--dong-y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.tep("tu-xa/ketoan-01")))
        self.assertIn(f"-D -s {IP_MAY}", " ".join(self.log("conntrack")))

    def test_het_han_tu_thu_hoi(self):
        self.tao_may()
        self.dat_luot(het_han=int(time.time()) - 100)
        r = self.chay("tu-xa-ap-dung")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("đã đổi", r.stdout)
        self.assertFalse(os.path.exists(self.tep("tu-xa/ketoan-01")))
        self.assertIn(f"-D -s {IP_MAY}", " ".join(self.log("conntrack")))

    def test_ap_dung_hai_lan_khong_doi(self):
        self.tao_may()
        self.dat_luot(het_han=int(time.time()) + 3600)
        r = self.chay("tu-xa-ap-dung")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("đã đổi", r.stdout)
        r = self.chay("tu-xa-ap-dung")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("đã đổi", r.stdout)
        self.assertEqual(self.log("tuong-lua"), ["bat"])

    def test_in_cau_hinh_may(self):
        self.tao_may()
        r = self.chay("them-may", "ketoan-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("BOX_IP_TU_XA", r.stdout)
        self.assertIn(f"@127.0.0.1:8000/ketoan-01/", r.stdout.replace("127.0.0.1", "127.0.0.1"))
        # máy có lượt duyệt còn hạn: in địa chỉ từ xa và kho theo TÊN Box
        self.dat_luot(het_han=int(time.time()) + 3600)
        r = self.chay("them-may", "ketoan-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"BOX_IP_TU_XA={IP_BOX_TS}", r.stdout)
        self.assertIn(f"@box.kiem-thu.onebee.internal:8000/ketoan-01/", r.stdout)
        # lượt hết hạn thì coi như không có
        self.dat_luot(het_han=int(time.time()) - 10)
        r = self.chay("them-may", "ketoan-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("BOX_IP_TU_XA", r.stdout)

    def test_bang_tu_xa(self):
        r = self.chay("tu-xa")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)
        self.tao_may()
        self.dat_luot(het_han=int(time.time()) + 3600)
        r = self.chay("tu-xa")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ketoan-01", r.stdout)
        self.assertIn(IP_MAY, r.stdout)


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


if __name__ == "__main__":
    unittest.main()
