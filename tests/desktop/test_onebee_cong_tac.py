#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử đơn vị cho lệnh `onebee-cong-tac` trên máy trạm (ket-noi-box/files/onebee-cong-tac):
cờ của `tailscale up` đúng và đủ; `--khoa` không lọt vào tệp hay nhật ký nào; `--box-tu-xa` ghi đúng dòng
và từ chối IP ngoài dải 100.64.0.0/10; `tat` không xoá BOX_IP_TU_XA; `xem` chạy được không cần root."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "../../desktop/ansible/roles/ket-noi-box/files/onebee-cong-tac"))
BASH = shutil.which("bash") or "bash"


class CongTac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.t = self.tmp.name.replace("\\", "/")
        for d in ("bin", "etc/onebee", "sim"):
            os.makedirs(f"{t}/{d}", exist_ok=True)
        self.conf = f"{t}/etc/onebee/may-tram.env"
        self.hosts = f"{t}/etc/hosts"
        self.os_rel = f"{t}/etc/os-release"
        with open(self.conf, "w", encoding="utf-8") as f:
            f.write("MAY_TRAM=ketoan-01\nBOX_IP=192.168.1.10\nBOX_TEN=box.kiem-thu.onebee.internal\n")
        os.chmod(self.conf, 0o600)
        with open(self.hosts, "w", encoding="utf-8") as f:
            f.write("127.0.0.1 localhost\n192.168.1.10 box.kiem-thu.onebee.internal # onebee-box\n")
        with open(self.os_rel, "w", encoding="utf-8") as f:
            f.write('ID=linuxmint\nID_LIKE="ubuntu debian"\nUBUNTU_CODENAME=noble\nPRETTY_NAME="Linux Mint 22.3"\n')

        def gia(ten, than):
            p = f"{t}/bin/{ten}"
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"#!/usr/bin/env bash\n{than}\n")
            os.chmod(p, 0o755)

        gia("tailscale", 'echo "tailscale $*" >> "${SIM}/calls.log"\n'
                         'case "$1" in\n'
                         '  ip) echo "100.64.0.7" ;;\n'
                         '  status) echo "100.64.0.7 ketoan-01 linux -" ;;\n'
                         '  up|logout) exit 0 ;;\n'
                         '  *) exit 0 ;;\n'
                         'esac')
        gia("onebee-chon-duong-box", 'echo "chon-duong $*" >> "${SIM}/calls.log"\n'
                                     'if [[ "${1:-}" == "--xem" ]]; then echo "từ xa qua VPN"; fi')
        gia("systemctl", 'echo "systemctl $*" >> "${SIM}/calls.log"')
        gia("apt-get", 'echo "apt-get $*" >> "${SIM}/calls.log"')
        gia("curl", 'echo "curl $*" >> "${SIM}/calls.log"')
        gia("dpkg", 'echo "amd64"')

    def chay(self, *args, gia_root=True):
        env = dict(
            os.environ,
            PATH=f"{self.t}/bin" + os.pathsep + os.environ.get("PATH", ""),
            SIM=f"{self.t}/sim",
            ONEBEE_CONF=self.conf,
            ONEBEE_HOSTS=self.hosts,
            ONEBEE_TEST_OS_RELEASE=self.os_rel,
            ONEBEE_TEST_ROOT="1" if gia_root else "0",
        )
        return subprocess.run([BASH, SCRIPT, *args], env=env, capture_output=True, text=True, timeout=15)

    def calls(self):
        p = f"{self.t}/sim/calls.log"
        return open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []

    def test_bat_goi_tailscale_up_du_co_va_khong_lo_khoa(self):
        khoa = "tskey-auth-kBiMat123456"
        r = self.chay("bat", "--khoa", khoa)
        self.assertEqual(r.returncode, 0, r.stderr)
        ts_up = [c for c in self.calls() if c.startswith("tailscale up ")]
        self.assertEqual(len(ts_up), 1, self.calls())
        for co in ("--reset", "--hostname=ketoan-01", "--accept-dns=false",
                   "--accept-routes=false", "--shields-up", "--ssh=false", f"--authkey={khoa}"):
            self.assertIn(co, ts_up[0])
        # Khóa không được ghi vào may-tram.env hay xuất hiện trên stdout/stderr
        self.assertNotIn(khoa, open(self.conf, encoding="utf-8").read())
        self.assertNotIn(khoa, r.stdout + r.stderr)
        self.assertIn("chon-duong ", " ".join(self.calls()))

    def test_box_tu_xa_ghi_dung_dong_va_tu_choi_ngoai_dai(self):
        r = self.chay("bat", "--box-tu-xa", "100.64.0.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        nd = open(self.conf, encoding="utf-8").read().splitlines()
        self.assertEqual(nd.count("BOX_IP_TU_XA=100.64.0.1"), 1)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(os.stat(self.conf).st_mode), 0o600)
        # Chạy lại đổi IP khác: thay dòng cũ, không nhân đôi
        r2 = self.chay("bat", "--box-tu-xa", "100.100.5.9")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        nd2 = open(self.conf, encoding="utf-8").read().splitlines()
        self.assertEqual([d for d in nd2 if d.startswith("BOX_IP_TU_XA=")], ["BOX_IP_TU_XA=100.100.5.9"])
        # Từ chối IP ngoài 100.64.0.0/10
        for ip_sai in ("192.168.1.10", "1.2.3.4", "100.63.255.1", "100.128.0.1", "khong-phai-ip"):
            r_sai = self.chay("bat", "--box-tu-xa", ip_sai)
            self.assertNotEqual(r_sai.returncode, 0, ip_sai)
        # File cấu hình vẫn giữ giá trị hợp lệ trước đó
        self.assertIn("BOX_IP_TU_XA=100.100.5.9", open(self.conf, encoding="utf-8").read())

    def test_box_tu_xa_doi_kho_sao_luu_sang_ten_box(self):
        """Máy đã đi mà chưa chuẩn bị (Box không SSH tới để đẩy cấu hình): URL kho sao lưu đang theo IP LAN thì qua VPN
        không tới được. Ghi --box-tu-xa phải đổi luôn máy chủ trong RESTIC_REPOSITORY sang tên Box, đúng dạng Box đẩy khi duyệt."""
        with open(self.conf, "a", encoding="utf-8") as f:
            f.write("RESTIC_REPOSITORY=rest:https://ketoan-01:mk.Ab-9@192.168.1.10:8000/ketoan-01/\nRESTIC_PASSWORD=bi-mat\n")
        r = self.chay("bat", "--box-tu-xa", "100.64.0.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        nd = open(self.conf, encoding="utf-8").read().splitlines()
        self.assertIn("RESTIC_REPOSITORY=rest:https://ketoan-01:mk.Ab-9@box.kiem-thu.onebee.internal:8000/ketoan-01/", nd)
        self.assertIn("RESTIC_PASSWORD=bi-mat", nd)
        # Chạy lại: không đổi gì thêm
        self.chay("bat", "--box-tu-xa", "100.64.0.1")
        self.assertEqual(nd, open(self.conf, encoding="utf-8").read().splitlines())

    def test_box_tu_xa_khong_dung_kho_http_hoac_ip_khac(self):
        """Kho http:// (Box chưa bật HTTPS) hoặc máy chủ không phải BOX_IP thì giữ nguyên: tên Box chỉ có chứng chỉ khi HTTPS bật."""
        for dong in ("RESTIC_REPOSITORY=rest:http://ketoan-01:mk@192.168.1.10:8000/ketoan-01/",
                     "RESTIC_REPOSITORY=rest:https://ketoan-01:mk@10.9.9.9:8000/ketoan-01/"):
            with open(self.conf, "w", encoding="utf-8") as f:
                f.write("MAY_TRAM=ketoan-01\nBOX_IP=192.168.1.10\nBOX_TEN=box.kiem-thu.onebee.internal\n" + dong + "\n")
            r = self.chay("bat", "--box-tu-xa", "100.64.0.1")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(dong, open(self.conf, encoding="utf-8").read().splitlines())

    def test_tat_goi_logout_va_giu_nguyen_box_ip_tu_xa(self):
        self.chay("bat", "--box-tu-xa", "100.64.0.1")
        r = self.chay("tat")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("tailscale logout", self.calls())
        self.assertIn("BOX_IP_TU_XA=100.64.0.1", open(self.conf, encoding="utf-8").read())

    def test_xem_chay_duoc_khong_can_root(self):
        r = self.chay("xem", gia_root=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("từ xa qua VPN", r.stdout)
        # bat và tat không có root thì bị từ chối
        self.assertNotEqual(self.chay("bat", gia_root=False).returncode, 0)
        self.assertNotEqual(self.chay("tat", gia_root=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
