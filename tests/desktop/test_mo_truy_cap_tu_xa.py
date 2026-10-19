#!/usr/bin/env python3
"""Kiểm thử script mo-truy-cap-tu-xa.sh — cầu nối TẠM để kỹ thuật vào máy Ubuntu 24.04 mới cài.
Kiểm thử bằng lệnh giả: chặn đầu vào sai; bật trên GNOME (RDP, mật khẩu chỉ ở file 0600); không phải GNOME chỉ bật SSH;
chạy qua SSH bằng root; --tat gỡ hết. Chưa chạy trên máy thật.
Chạy: python3 -m unittest
"""
import os
import shutil
import stat
import subprocess
import socket
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(HERE, "../..")
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts/mo-truy-cap-tu-xa.sh")


class MockEnvironment:
    """Tạo môi trường kiểm thử với lệnh giả."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_bin = os.path.join(self.temp_dir, "bin")
        self.log_file = os.path.join(self.temp_dir, "calls.log")
        self.os_release = os.path.join(self.temp_dir, "os-release")
        self.password_file = os.path.join(self.temp_dir, "password.txt")
        self.dbus_socket_path = None
        os.makedirs(self.mock_bin)

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if getattr(self, "sock_dir", None):
            shutil.rmtree(self.sock_dir, ignore_errors=True)

    def _create_mock(self, name, script_body=""):
        """Tạo lệnh giả ghi lại lời gọi vào nhật ký."""
        cmd_path = os.path.join(self.mock_bin, name)
        default_body = f'echo "{name} $*" >> "{self.log_file}"\n'
        with open(cmd_path, "w") as f:
            f.write(f"#!/bin/bash\n{default_body}{script_body}exit 0\n")
        os.chmod(cmd_path, 0o755)

    def setup_basic_mocks(self):
        """Tạo tất cả lệnh giả cơ bản."""
        for cmd in ["apt-get", "curl", "systemctl", "hostname"]:
            self._create_mock(cmd)
        # runuser thật chạy lệnh sau "--" bằng quyền người dùng → giả lập: bỏ phần đầu rồi chạy lệnh
        self._create_mock("runuser", 'while [[ $# -gt 0 && "$1" != -- ]]; do shift; done; shift; "$@" || exit $?\n')
        self.tailscale_dang_nhap(False)
        self._create_mock("timeout", 'shift; "$@" || exit $?\n')  # macOS không có timeout; chỉ chạy lệnh phía sau

        self._create_mock("dpkg", 'if [[ "$1" == "--print-architecture" ]]; then echo "amd64"; fi\n')
        self._create_mock("id", 'if [[ "$1" == "-u" ]] && [[ -n "${2:-}" ]]; then echo "1000"; fi\n')
        self._create_mock("getent",
            f'if [[ "$1" == "passwd" ]]; then echo "testuser:x:1000:1000:Test:{self.temp_dir}:/bin/bash"; fi\n')
        self._create_mock("loginctl",
            'if [[ "$1" == "show-seat" ]]; then echo "1"; elif [[ "$1" == "show-session" ]]; then echo "testuser"; fi\n')
        self._create_mock("gnome-shell")
        self._create_mock("gsettings", 'if [[ "$1" == "list-schemas" ]]; then echo "org.gnome.desktop.screensaver"; fi\n')
        self._create_mock("grdctl")
        self._create_mock("openssl", """
if [[ "$1" == "rand" ]]; then
  echo "ABCD1234EFGH5678IJKL9012"
elif [[ "$1" == "req" ]]; then
  for ((i=1; i<$#; i++)); do
    if [[ "${!i}" == "-keyout" ]] || [[ "${!i}" == "-out" ]]; then
      ((j=i+1))
      mkdir -p "$(dirname "${!j}")"
      touch "${!j}"
    fi
  done
fi
""")
        self._create_mock("install",
            'mkdir -p "$(dirname "${!#}")" 2>/dev/null; touch "${!#}" 2>/dev/null\n')

    def tailscale_dang_nhap(self, da_vao):
        """tailscale giả: đã vào tailnet thì `ip -4` in IP, chưa vào thì lỗi như bản thật (NeedsLogin)."""
        if da_vao:
            body = 'if [[ "$1" == ip ]]; then echo 100.64.0.9; fi\n'
        else:
            # như bản thật: sau `up` (kỹ thuật đã mở link) thì có IP
            co = os.path.join(self.temp_dir, "ts-da-vao")
            body = (f'if [[ "$1" == up ]]; then touch "{co}"; fi\n'
                    f'if [[ "$1" == ip ]]; then [[ -e "{co}" ]] && {{ echo 100.64.0.7; exit 0; }}; echo NeedsLogin >&2; exit 1; fi\n')
        self._create_mock("tailscale", body)

    def create_dbus_socket(self):
        """Tạo Unix domain socket để GNOME được phát hiện."""
        self.sock_dir = tempfile.mkdtemp(dir="/tmp")
        dbus_path = os.path.join(self.sock_dir, "bus")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(dbus_path)
        sock.close()
        self.dbus_socket_path = dbus_path

    def set_os_release(self, id_="ubuntu", codename="noble"):
        """Đặt nội dung /etc/os-release."""
        with open(self.os_release, "w") as f:
            f.write(f"""ID={id_}
VERSION_CODENAME={codename}
PRETTY_NAME="Ubuntu 24.04 LTS"
UBUNTU_CODENAME={codename}
ID_LIKE=debian
""")

    def run_script(self, args=None, euid=None, sudo_user=None, env_extra=None):
        """Chạy script với môi trường kiểm thử."""
        env = os.environ.copy()
        env["PATH"] = self.mock_bin + ":" + env.get("PATH", "")
        env["ONEBEE_TEST_OS_RELEASE"] = self.os_release
        env["ONEBEE_TRUY_CAP_FILE"] = self.password_file
        env["HOME"] = self.temp_dir

        if euid is not None:
            env["ONEBEE_TEST_EUID"] = str(euid)

        if sudo_user is not None:
            env["SUDO_USER"] = sudo_user
        else:
            env.pop("SUDO_USER", None)

        if self.dbus_socket_path:
            env["ONEBEE_TEST_BUS_SOCKET"] = self.dbus_socket_path

        if env_extra:
            env.update(env_extra)

        cmd = ["bash", SCRIPT_PATH]
        if args:
            cmd.extend(args)

        return subprocess.run(
            cmd,
            cwd=self.temp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def get_call_log(self):
        """Lấy danh sách lời gọi lệnh từ nhật ký."""
        if not os.path.exists(self.log_file):
            return []
        with open(self.log_file) as f:
            return [line.strip() for line in f if line.strip()]

    def password_file_readable_0600(self):
        """Kiểm file mật khẩu tồn tại với quyền 0600."""
        if not os.path.exists(self.password_file):
            return False
        st = os.stat(self.password_file)
        return stat.S_IMODE(st.st_mode) == 0o600


class TestMoTruyCapTuXa(unittest.TestCase):
    """Kiểm thử script mo-truy-cap-tu-xa.sh."""

    def setUp(self):
        self.env = MockEnvironment()

    def tearDown(self):
        self.env.cleanup()

    def test_a_tham_so_sai_thoat_khac_zero(self):
        """(a) Tham số không hợp lệ → thoát với mã khác 0."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        result = self.env.run_script(["--khong-hop-le"], euid=0, sudo_user="testuser")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cách dùng", result.stderr)

    def test_b_khong_root_thoat(self):
        """(b) Không phải root (EUID != 0) → từ chối."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        result = self.env.run_script(euid=1000, sudo_user="testuser")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quyền quản trị", result.stderr)

    def test_c_os_khong_noble_thoat(self):
        """(c) OS không phải noble → từ chối."""
        self.env.setup_basic_mocks()
        self.env.set_os_release(codename="jammy")
        result = self.env.run_script(euid=0, sudo_user="testuser")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Ubuntu 24.04", result.stderr)

    def chay_bat(self, gnome=True, da_vao=False, sudo_user="testuser"):
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        self.env.tailscale_dang_nhap(da_vao)
        if gnome:
            self.env.create_dbus_socket()
        r = self.env.run_script(euid=0, sudo_user=sudo_user)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r, self.env.get_call_log()

    def test_d_gnome_bat_rdp_va_ghi_mat_khau_0600(self):
        """(d) GNOME: chưa vào tailnet → tailscale up --ssh; bật RDP đủ bước; không khóa màn hình; mật khẩu chỉ ở file 0600."""
        r, calls = self.chay_bat(gnome=True, da_vao=False)
        self.assertIn("tailscale up --ssh", calls)
        for buoc in ("rdp set-tls-key", "rdp set-tls-cert", "rdp set-credentials onebee ", "rdp disable-view-only",
                     "rdp enable"):
            self.assertTrue(any(c.startswith("grdctl " + buoc) for c in calls), f"thiếu grdctl {buoc}: {calls}")
        self.assertIn("gsettings set org.gnome.desktop.screensaver lock-enabled false", calls)
        self.assertIn("gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing", calls)
        self.assertTrue(self.env.password_file_readable_0600())
        mat_khau = open(self.env.password_file).read().split("Mật khẩu: ")[1].strip()
        self.assertEqual(len(mat_khau), 16)
        self.assertIn(f"grdctl rdp set-credentials onebee {mat_khau}", calls)
        self.assertNotIn(mat_khau, r.stdout + r.stderr)

    def test_e_khong_gnome_chi_bat_ssh(self):
        """(e) Không phải GNOME (không có D-Bus phiên) → không đụng grdctl, không ghi mật khẩu, vẫn bật Tailscale SSH."""
        r, calls = self.chay_bat(gnome=False, da_vao=False)
        self.assertIn("tailscale up --ssh", calls)
        self.assertFalse(any(c.startswith("grdctl") for c in calls), calls)
        self.assertFalse(os.path.exists(self.env.password_file))
        self.assertIn("chưa bật", r.stdout)

    def test_f_ssh_khong_sudo_user_dung_loginctl(self):
        """(f) Chạy qua SSH bằng root (không SUDO_USER) → lấy người dùng phiên đồ họa từ loginctl; đã vào tailnet → set --ssh, không up."""
        r, calls = self.chay_bat(gnome=True, da_vao=True, sudo_user=None)
        self.assertTrue(any(c.startswith("loginctl show-seat seat0") for c in calls), calls)
        self.assertIn("tailscale set --ssh", calls)
        self.assertNotIn("tailscale up --ssh", calls)
        self.assertIn("100.64.0.9:3389", open(self.env.password_file).read())

    def test_k_vua_vao_tailnet_chua_co_ip_van_in_huong_dan(self):
        """(k) Sau `tailscale up` mà IP chưa có ngay → không dừng im lặng, vẫn in hướng dẫn cho kỹ thuật."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        self.env._create_mock("tailscale", 'if [[ "$1" == ip ]]; then exit 1; fi\n')
        r = self.env.run_script(euid=0, sudo_user="testuser")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ĐÃ MỞ TRUY CẬP TỪ XA", r.stdout)
        self.assertIn("IP Tailscale: chưa có", r.stdout)

    def test_g_tat_go_het(self):
        """(g) --tat: gỡ RDP + mật khẩu, trả khóa màn hình, tắt Tailscale SSH và rời tailnet, xóa file mật khẩu."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        self.env.create_dbus_socket()
        with open(self.env.password_file, "w") as f:
            f.write("Mật khẩu: cu\n")
        r = self.env.run_script(["--tat"], euid=0, sudo_user="testuser")
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.env.get_call_log()
        for c in ("grdctl rdp disable", "grdctl rdp clear-credentials",
                  "gsettings reset org.gnome.desktop.screensaver lock-enabled",
                  "gsettings reset org.gnome.desktop.remote-desktop.rdp tls-cert",
                  "tailscale set --ssh=false", "tailscale logout"):
            self.assertIn(c, calls)
        self.assertLess(calls.index("grdctl rdp disable"), calls.index("tailscale logout"))  # rời tailnet sau cùng
        self.assertFalse(os.path.exists(self.env.password_file))

    def test_l_keyring_khoa_bo_qua_rdp_giu_ssh(self):
        """(l) Keyring GNOME khóa → grdctl set-credentials lỗi: không dừng giữa chừng, không tắt khóa màn hình,
        không ghi file mật khẩu, báo rõ cách sửa; Tailscale SSH vẫn bật."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        self.env.create_dbus_socket()
        self.env._create_mock("grdctl", 'if [[ "$2" == set-credentials ]]; then echo "collection/login" >&2; exit 1; fi\n')
        r = self.env.run_script(euid=0, sudo_user="testuser")
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.env.get_call_log()
        self.assertIn("tailscale up --ssh", calls)
        self.assertFalse(any(c.startswith("gsettings set") for c in calls), calls)
        self.assertFalse(any(c.startswith("grdctl rdp enable") for c in calls), calls)
        self.assertFalse(os.path.exists(self.env.password_file))
        self.assertIn("keyring GNOME đang khóa", r.stdout)
        self.assertIn("ĐÃ MỞ TRUY CẬP TỪ XA", r.stdout)

    def test_i_os_khong_ubuntu_thoat(self):
        """(i) OS không phải Ubuntu → từ chối."""
        self.env.setup_basic_mocks()
        self.env.set_os_release(id_="debian")
        result = self.env.run_script(euid=0, sudo_user="testuser")
        self.assertNotEqual(result.returncode, 0)

    def test_j_architecture_khong_amd64_thoat(self):
        """(j) Architecture không phải amd64 → từ chối."""
        self.env.setup_basic_mocks()
        self.env.set_os_release()
        # Mock dpkg để trả arm64
        self.env._create_mock("dpkg", 'if [[ "$1" == "--print-architecture" ]]; then echo "arm64"; fi\n')
        result = self.env.run_script(euid=0, sudo_user="testuser")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("64-bit", result.stderr)


if __name__ == "__main__":
    unittest.main()
