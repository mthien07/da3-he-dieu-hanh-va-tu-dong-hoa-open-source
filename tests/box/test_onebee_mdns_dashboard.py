#!/usr/bin/env python3
"""Kiểm thử Task 01 — tên onebee.local (avahi mDNS) và trang chủ Dashboard cổng 80 của Box (không cần Box thật).
Kiểm: box-base cài + bật avahi-daemon, cấu hình chỉ quảng bá IPv4 trên cổng mạng chính, không lộ thông tin máy, tệp dịch vụ http cổng 80;
trang chủ có tên đơn vị (thoát HTML), lối tắt, cẩm nang, ô tình trạng, không tải gì từ Internet;
onebee-trang-thai-web.py tính CPU/RAM/ổ, trạng thái dịch vụ, ghi JSON nguyên tử;
Caddy THẬT (nếu có ONEBEE_TEST_CADDY) trả trang chủ cho Host onebee.local và số liệu không bị lưu đệm; Open WebUI nhận Origin onebee.local.
Chạy: python3 -m unittest"""
import configparser
import importlib.util
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
ROLES = os.path.join(ROOT, "box/ansible/roles")
TRANG_THAI_PY = os.path.join(ROLES, "box-stack/files/onebee-trang-thai-web.py")
CADDY = os.environ.get("ONEBEE_TEST_CADDY") or shutil.which("caddy")


def bien(**them):
    v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=False,
             onebee_kuma_dia_chi="0.0.0.0", onebee_mdns_cong_mang="eth0")
    v.update(them)
    return v


def ve(duong_dan, **them):
    """Render mẫu Jinja như Ansible (trim_blocks, không tự thoát HTML)."""
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
    env.filters["bool"] = bool
    return env.from_string(open(os.path.join(ROLES, duong_dan), encoding="utf-8").read()).render(**bien(**them))


def tasks(role, tep="main.yml"):
    return yaml.safe_load(open(os.path.join(ROLES, role, "tasks", tep), encoding="utf-8"))


def tim(ds, module, dieu_kien=lambda a: True):
    return [t for t in ds if isinstance(t.get(module), dict) and dieu_kien(t[module])]


def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class AvahiMdns(unittest.TestCase):
    def test_box_base_cai_bat_avahi_va_sinh_cau_hinh(self):
        ds = tasks("box-base")
        apt = tim(ds, "ansible.builtin.apt", lambda a: "avahi-daemon" in (a.get("name") or []))
        self.assertTrue(apt, "chưa cài avahi-daemon")
        self.assertIn("avahi-utils", apt[0]["ansible.builtin.apt"]["name"])   # avahi-resolve-host-name để kiểm/chẩn đoán
        dich = {it["dest"]: it["src"] for t in tim(ds, "ansible.builtin.template") for it in t.get("loop") or [t["ansible.builtin.template"]]}
        self.assertEqual(dich.get("/etc/avahi/avahi-daemon.conf"), "avahi-daemon.conf.j2")
        self.assertEqual(dich.get("/etc/avahi/services/http.service"), "avahi-http.service.j2")
        sv = tim(ds, "ansible.builtin.systemd_service", lambda a: a.get("name") == "avahi-daemon.service")
        self.assertTrue(sv, "chưa bật avahi-daemon")
        self.assertIs(sv[0]["ansible.builtin.systemd_service"]["enabled"], True)
        # Tên quảng bá sai dạng thì dừng sớm, không sinh cấu hình avahi hỏng
        self.assertTrue(tim(ds, "ansible.builtin.assert", lambda a: "onebee_box_ten_mdns" in str(a.get("that"))))

    def test_ten_mdns_mac_dinh_la_onebee(self):
        self.assertEqual(bien()["onebee_box_ten_mdns"], "onebee")

    def test_cau_hinh_avahi_chi_ipv4_tren_cong_mang_chinh_khong_lo_thong_tin_may(self):
        cp = configparser.ConfigParser()
        cp.read_string(ve("box-base/templates/avahi-daemon.conf.j2"))
        self.assertEqual(cp["server"]["host-name"], "onebee")
        self.assertEqual(cp["server"]["domain-name"], "local")
        # Chỉ cổng mạng chính: không quảng bá IP mạng Docker (docker0, br-*) cho tên onebee.local
        self.assertEqual(cp["server"]["allow-interfaces"], "eth0")
        # Docker chỉ mở cổng IPv4 → tên chỉ trỏ IPv4, kẻo máy Windows thử IPv6 trước rồi treo
        self.assertEqual(cp["server"]["use-ipv6"], "no")
        self.assertEqual(cp["publish"]["publish-aaaa-on-ipv4"], "no")
        self.assertEqual(cp["publish"]["publish-workstation"], "no")   # không lộ địa chỉ MAC
        self.assertEqual(cp["publish"]["publish-hinfo"], "no")         # không lộ hệ điều hành/CPU

    def test_khong_biet_cong_mang_chinh_thi_bo_allow_interfaces(self):
        cp = configparser.ConfigParser()
        cp.read_string(ve("box-base/templates/avahi-daemon.conf.j2", onebee_mdns_cong_mang=""))
        self.assertNotIn("allow-interfaces", cp["server"])

    def test_tep_dich_vu_http_cong_80(self):
        goc = ET.fromstring(ve("box-base/templates/avahi-http.service.j2"))
        sv = goc.find("service")
        self.assertEqual(sv.findtext("type"), "_http._tcp")
        self.assertEqual(sv.findtext("port"), "80")
        self.assertIn("OneBee Box", goc.findtext("name"))
        self.assertIn("path=/", [t.text for t in sv.findall("txt-record")])


class TrangChu(unittest.TestCase):
    TEN = "HTX Nông nghiệp An Phú"

    def setUp(self):
        self.html = ve("box-stack/templates/index.html.j2", onebee_box_ten_don_vi=self.TEN)

    def test_tieu_de_va_ten_don_vi(self):
        self.assertIn("<title>OneBee Box", self.html)
        self.assertIn(self.TEN, self.html)

    def test_ten_don_vi_duoc_thoat_html(self):
        html = ve("box-stack/templates/index.html.j2", onebee_box_ten_don_vi='<script>alert("x")</script>')
        self.assertNotIn('<script>alert("x")', html)
        self.assertIn("&lt;script&gt;", html)

    def test_loi_tat_tro_ly_ai_thu_muc_chung_ho_tro_cam_nang(self):
        h = self.html
        self.assertIn('data-port="3000"', h)                                          # Trợ lý AI
        self.assertIn('data-port="5678" data-path="form/onebee-ho-tro"', h)          # Yêu cầu hỗ trợ (biểu mẫu n8n)
        self.assertIn('id="smb-win"', h)                                              # \\onebee.local\chung (Windows)
        self.assertIn('id="smb"', h)                                                  # smb://onebee.local/chung
        self.assertIn('href="#cam-nang"', h)
        self.assertRegex(h, r'id="cam-nang"')
        for y in ("Ctrl + P", "Super + Space", "Ctrl + S"):
            self.assertIn(y, h)

    def test_o_tinh_trang_doc_so_lieu_va_khong_dung_innerhtml(self):
        h = self.html
        self.assertIn('fetch("/trang-thai.json"', h)
        for i in ("tt-cpu", "tt-ram", "tt-o-dia", "dv-tro_ly_ai", "dv-thu_muc_chung", "dv-sao_luu"):
            self.assertIn(f'id="{i}"', h)
        self.assertNotIn("innerHTML", h)   # số liệu chỉ gán bằng textContent

    def test_khong_tai_gi_tu_internet_va_nhe(self):
        h = self.html
        self.assertIsNone(re.search(r'<(script|link|img|iframe)[^>]+(src|href)="(https?:)?//', h), "trang chủ tải tài nguyên ngoài")
        self.assertNotIn("<script src", h)
        self.assertLess(len(h.encode()), 24 * 1024)   # 1 tệp, không thư viện ngoài → mở ngay trong LAN


class TrangThaiWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("trang_thai", TRANG_THAI_PY)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)

    def test_cpu_theo_hai_lan_doc(self):
        self.assertEqual(self.m.phan_tram_cpu("cpu  100 0 100 800 0 0 0 0 0 0", "cpu  150 0 150 900 0 0 0 0 0 0"), 50)
        self.assertEqual(self.m.phan_tram_cpu("cpu  1 0 0 9 0 0 0 0 0 0", "cpu  1 0 0 9 0 0 0 0 0 0"), 0)   # không đổi: không chia 0

    def test_ram_theo_memavailable(self):
        self.assertEqual(self.m.phan_tram_ram("MemTotal:        8000000 kB\nMemFree: 100 kB\nMemAvailable:    2000000 kB\n"), 75)

    def test_sao_luu_lan_cuoi(self):
        bay_gio = 1_800_000_000
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "sao-luu-lan-cuoi")
            self.assertEqual(self.m.sao_luu(f, bay_gio), "chua_co")
            for nd, mong in ((f"DAT {bay_gio - 3600}", "tot"), (f"DAT {bay_gio - 3 * 86400}", "qua_han"),
                             (f"LOI {bay_gio - 60}", "loi"), ("rac", "loi")):
                open(f, "w").write(nd + "\n")
                self.assertEqual(self.m.sao_luu(f, bay_gio), mong, nd)

    def chay(self, docker_ra, smbd_ma):
        t = self.t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, t)
        bin_ = os.path.join(t, "bin")
        os.makedirs(bin_)
        for ten, nd in (("docker", f'#!/bin/sh\n{docker_ra}\n'), ("systemctl", f'#!/bin/sh\n[ "$3" = smbd ] && exit {smbd_ma}\nexit 9\n')):
            p = os.path.join(bin_, ten)
            open(p, "w").write(nd)
            os.chmod(p, 0o755)
        proc = os.path.join(t, "proc")
        os.makedirs(proc)
        open(os.path.join(proc, "stat"), "w").write("cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 1 0 0 0 0 0 0 0 0 0\n")
        open(os.path.join(proc, "meminfo"), "w").write("MemTotal: 4000000 kB\nMemAvailable: 3000000 kB\n")
        open(os.path.join(t, "sao-luu-lan-cuoi"), "w").write(f"DAT {int(time.time())}\n")
        ra = os.path.join(t, "site", "trang-thai.json")
        os.makedirs(os.path.dirname(ra))
        r = subprocess.run([sys.executable, TRANG_THAI_PY, ra, t, os.path.join(t, "sao-luu-lan-cuoi")], capture_output=True, text=True,
                           env={**os.environ, "PATH": bin_ + ":/usr/bin:/bin", "ONEBEE_PROC": proc, "ONEBEE_CPU_CHO": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return ra

    def test_ghi_json_day_du_nguyen_tu_va_khong_lo_thong_tin_mang(self):
        ra = self.chay('echo true; echo true', 0)
        d = json.load(open(ra))
        self.assertEqual(set(d), {"cap_nhat", "cpu_phan_tram", "ram_phan_tram", "o_dia", "dich_vu"})
        self.assertEqual(d["ram_phan_tram"], 25)
        self.assertEqual(set(d["o_dia"]), {"con_trong_gb", "da_dung_phan_tram"})
        self.assertGreater(d["o_dia"]["con_trong_gb"], 0)
        self.assertEqual(d["dich_vu"], {"tro_ly_ai": "chay", "thu_muc_chung": "chay", "sao_luu": "tot"})
        self.assertEqual(stat.S_IMODE(os.stat(ra).st_mode), 0o644)            # Caddy (không phải root) đọc được
        self.assertEqual(os.listdir(os.path.dirname(ra)), ["trang-thai.json"])  # không sót tệp tạm

    def test_dich_vu_ngung_hoac_khong_co_docker(self):
        d = json.load(open(self.chay('echo true; echo false', 3)))
        self.assertEqual(d["dich_vu"]["tro_ly_ai"], "dung")       # Ollama hoặc Open WebUI ngừng là Trợ lý không dùng được
        self.assertEqual(d["dich_vu"]["thu_muc_chung"], "dung")
        d = json.load(open(self.chay('echo "Error: No such object" >&2; exit 1', 0)))
        self.assertEqual(d["dich_vu"]["tro_ly_ai"], "dung")


class TrienKhai(unittest.TestCase):
    def test_box_stack_cai_va_hen_gio_cap_nhat_so_lieu(self):
        ds = tasks("box-stack")
        tep = [t["ansible.builtin.copy"] for t in tim(ds, "ansible.builtin.copy", lambda a: a.get("src") == "onebee-trang-thai-web.py")]
        self.assertEqual(tep[0]["dest"], "/usr/local/lib/onebee-box/onebee-trang-thai-web.py")
        sv = tim(ds, "ansible.builtin.systemd_service", lambda a: a.get("name") == "onebee-trang-thai-web.timer")
        self.assertIs(sv[0]["ansible.builtin.systemd_service"]["enabled"], True)
        unit = ve("box-stack/templates/onebee-trang-thai-web.service.j2")
        self.assertIn("/usr/local/lib/onebee-box/onebee-trang-thai-web.py /opt/onebee-box/portal/site/trang-thai.json /srv/onebee "
                      "/var/lib/onebee-box/sao-luu-lan-cuoi", unit)
        self.assertIn("ReadWritePaths=/opt/onebee-box/portal/site", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertRegex(ve("box-stack/templates/onebee-trang-thai-web.timer.j2"), r"OnUnitActiveSec=1min")

    def test_sao_luu_ghi_ket_qua_lan_cuoi(self):
        sh = ve("box-stack/templates/onebee-box-sao-luu.sh.j2")
        than = sh.split("cmd_sao_luu_co_bao_cao() {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("/var/lib/onebee-box/sao-luu-lan-cuoi", than)
        self.assertIn("DAT", than)

    def test_open_webui_nhan_origin_onebee_local_o_che_do_http(self):
        s = yaml.safe_load(ve("box-stack/templates/docker-compose.yml.j2"))["services"]
        nguon = s["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"].split(";")
        self.assertIn("http://onebee.local:3000", nguon)   # mở Trợ lý từ trang chủ onebee.local: lệch thì WebSocket chat hỏng
        self.assertIn("http://192.168.1.10:3000", nguon)
        s = yaml.safe_load(ve("box-stack/templates/docker-compose.yml.j2", onebee_https_hieu_luc=True))["services"]
        self.assertNotIn("onebee.local", s["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"])   # chứng chỉ không cấp cho .local

    def test_caddy_https_cung_khong_luu_dem_so_lieu(self):
        nd = ve("box-stack/templates/Caddyfile.j2", onebee_https_hieu_luc=True)
        site443 = nd.split("onebee.internal:443 {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("/trang-thai.json", site443)
        self.assertIn("no-store", site443)


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class CaddyCong80(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        os.makedirs(f"{t}/srv")
        open(f"{t}/srv/index.html", "w").write(ve("box-stack/templates/index.html.j2", onebee_box_ten_don_vi="HTX An Phú"))
        open(f"{t}/srv/trang-thai.json", "w").write('{"cpu_phan_tram": 3}')
        cls.cong = cong_trong()
        nd = ve("box-stack/templates/Caddyfile.j2").replace(":80 {", f":{cls.cong} {{").replace("root * /srv\n", f"root * {t}/srv\n")
        open(f"{t}/Caddyfile", "w").write(nd)
        env = {**os.environ, "XDG_DATA_HOME": f"{t}/data", "XDG_CONFIG_HOME": f"{t}/cfg"}
        r = subprocess.run([CADDY, "validate", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr[-2000:]
        cls.caddy = subprocess.Popen([CADDY, "run", "--config", f"{t}/Caddyfile", "--adapter", "caddyfile"], env=env,
                                     stdout=subprocess.DEVNULL, stderr=open(f"{t}/caddy.log", "w"))
        for _ in range(100):
            time.sleep(0.1)
            if cls.curl("-o", "/dev/null", "/").returncode == 0:
                return
        raise AssertionError("Caddy không lên: " + open(f"{t}/caddy.log").read()[-2000:])

    @classmethod
    def tearDownClass(cls):
        cls.caddy.terminate()
        cls.caddy.wait(10)
        cls.tmp.cleanup()

    @classmethod
    def curl(cls, *a):
        *tuy_chon, duong = a
        return subprocess.run(["curl", "-sS", "--noproxy", "*", "-m", "10", "--resolve", f"onebee.local:{cls.cong}:127.0.0.1", *tuy_chon,
                               f"http://onebee.local:{cls.cong}{duong}"], capture_output=True, text=True)

    def test_onebee_local_tra_trang_chu(self):
        r = self.curl("-i", "/")
        self.assertRegex(r.stdout, r"^HTTP/1.1 200")
        self.assertIn("OneBee Box", r.stdout)
        self.assertIn("HTX An Phú", r.stdout)
        self.assertRegex(r.stdout, r"(?i)x-frame-options: DENY")
        self.assertNotRegex(r.stdout, r"(?im)^server:")

    def test_so_lieu_khong_bi_luu_dem(self):
        r = self.curl("-i", "/trang-thai.json")
        self.assertRegex(r.stdout, r"^HTTP/1.1 200")
        self.assertRegex(r.stdout, r"(?i)cache-control: no-store")
        self.assertRegex(r.stdout, r"(?i)content-type: application/json")


if __name__ == "__main__":
    unittest.main()
