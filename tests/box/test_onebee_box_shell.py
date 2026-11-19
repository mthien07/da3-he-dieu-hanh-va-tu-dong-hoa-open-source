#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử các lệnh shell quản lý máy trạm của `onebee-box` (them-may, thu-hoi-may, cap-nhat-may, dong-bo-may, ghim-lai-may)
mà không cần Box thật: render các mẫu .j2, chạy bằng bash trong thư mục tạm, với `ssh`, `ansible-playbook`, dịch vụ Trợ lý AI GIẢ.
Dùng ssh-keygen và htpasswd thật (apt: openssh-client, apache2-utils) — thiếu thì bỏ qua. Chạy: python3 -m unittest

Kiểm các tính chất của rà soát bảo mật F2: máy chỉ được ghim khóa SSH / nhận cấu hình sau khi CHỨNG MINH biết mật khẩu kho sao lưu,
báo cáo chưa ký không đủ để Box đem khóa quản trị tới một địa chỉ lạ, máy đã thu hồi không được "hồi sinh", dong-bo-may không đẩy file thiếu.
"""
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ROLES = os.path.join(ROOT, "box/ansible/roles")
TEMPLATES = os.path.join(ROLES, "box-stack/templates")
HAVE_TOOLS = all(shutil.which(t) for t in ("ssh-keygen", "htpasswd", "bash", "python3"))

# ssh giả: mô phỏng máy trạm. Bảng máy (ONEBEE_SIM) = {"ip": {"hostkey": "ssh-ed25519 ...", "password": "..."}}.
# Giống ssh thật ở chỗ cần kiểm: StrictHostKeyChecking=yes mà chưa ghim / khóa lệch thì thất bại; accept-new thì ghim lần đầu vào
# UserKnownHostsFile (theo HostKeyAlias). Chỉ trả mật khẩu khi vào được.
SSH_GIA = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if "-n" not in a:   # ssh thật không có -n sẽ đọc hết stdin → nuốt các dòng còn lại của vòng lặp "while read" gọi nó
    sys.stdin.read()
opts = {}
i = 0
while i < len(a):
    if a[i] == "-o":
        k, _, v = a[i + 1].partition("=")
        opts[k] = v
        i += 2
    elif a[i] == "-i":
        i += 2
    else:
        i += 1
target = [x for x in a if x.startswith("onebee-quantri@")][0].split("@", 1)[1]
open(os.environ["ONEBEE_SSH_LOG"], "a").write(target + " " + opts.get("StrictHostKeyChecking", "") + "\n")
may = json.load(open(os.environ["ONEBEE_SIM"])).get(target)
if not may:
    print("ssh: connect to host %s port 22: Connection timed out" % target, file=sys.stderr); sys.exit(255)
kh, alias, mode = opts["UserKnownHostsFile"], opts["HostKeyAlias"], opts["StrictHostKeyChecking"]
da_ghim = None
if os.path.exists(kh):
    for dong in open(kh):
        p = dong.split()
        if len(p) >= 3 and p[0] == alias:
            da_ghim = p[1] + " " + p[2]
if da_ghim and da_ghim != may["hostkey"]:
    print("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!\nHost key verification failed.", file=sys.stderr); sys.exit(255)
if not da_ghim:
    if mode == "yes":
        print("Host key verification failed.", file=sys.stderr); sys.exit(255)
    open(kh, "a").write(alias + " " + may["hostkey"] + "\n")
print("RESTIC_PASSWORD=" + may["password"])
'''

ANSIBLE_GIA = r'''#!/usr/bin/env bash
# ghi lại cách gọi và (với dong-bo-may) nội dung các file cấu hình định đẩy đi
d="${ONEBEE_OUT}/ansible-$(date +%s%N)"; mkdir -p "$d"
printf '%s\n' "$@" >"$d/args"; env | grep '^ANSIBLE_SSH_ARGS=' >"$d/env"
for ((i=1; i<=$#; i++)); do
  [[ "${!i}" == -i ]] && { j=$((i+1)); cp "${!j}" "$d/inventory"; }
  [[ "${!i}" == -e ]] && { j=$((i+1)); v="${!j}"; [[ "$v" == onebee_cau_hinh_dir=* ]] && cp -r "${v#onebee_cau_hinh_dir=}" "$d/cau-hinh"; }
done
exit "${ONEBEE_ANSIBLE_RC:-0}"
'''

AI_RAG_GIA = r'''#!/usr/bin/env python3
import hashlib
import os, sys
open(os.environ["ONEBEE_OUT"] + "/ai-rag.log", "a").write(" ".join(sys.argv[1:]) + "\n")
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "khoa":
    viec = sys.argv[2] if len(sys.argv) > 2 else ""
    if viec == "cap":
        dem = os.environ["ONEBEE_OUT"] + "/ai-rag-dem"
        n = (int(open(dem).read()) if os.path.exists(dem) else 0) + 1
        open(dem, "w").write(str(n))
        print("obk-" + hashlib.sha256((" ".join(sys.argv[3:]) + " " + str(n)).encode()).hexdigest()[:48])
    elif viec == "go":
        # giống dịch vụ thật: chỉ thu hồi được khi có khóa đã cấp
        sys.exit(0 if os.environ.get("ONEBEE_AI_RAG_CO_KHOA") == "1" else 1)
    elif viec == "ds":
        pass
elif cmd == "kiem-ollama":
    print("200 0.1")
'''

# Tài khoản hệ thống + Samba GIẢ (phòng ban): ghi vào tệp trong ONEBEE_OUT thay cho /etc/group, /etc/passwd, passdb của Samba
HE_THONG_GIA = r'''#!/usr/bin/env python3
import os, sys
lenh, a = os.path.basename(sys.argv[0]), sys.argv[1:]
out = os.environ["ONEBEE_OUT"]
db = out + "/he-thong"
dong = open(db).read().splitlines() if os.path.exists(db) else []
sam = out + "/samba-db"
s = open(sam).read().splitlines() if os.path.exists(sam) else []
open(out + "/he-thong.log", "a").write(lenh + " " + " ".join(a) + "\n")
if lenh == "getent":
    sys.exit(0 if a[0] + " " + a[1] in dong else 2)
elif lenh in ("groupadd", "useradd"):
    open(db, "a").write(("group " if lenh == "groupadd" else "passwd ") + a[-1] + "\n")
elif lenh == "pdbedit":
    for x in s:
        print(x.split(" ")[0] + ":1001:")
elif lenh == "smbpasswd":
    if "-a" in a:
        mk = sys.stdin.read().splitlines()
        assert len(mk) == 2 and mk[0] == mk[1], mk
        open(sam, "a").write(a[-1] + " " + mk[0] + "\n")
    elif "-x" in a:
        open(sam, "w").write("".join(x + "\n" for x in s if x.split(" ")[0] != a[-1]))
    else:   # đổi mật khẩu tài khoản đã có (smbpasswd -s <tên>)
        mk = sys.stdin.read().splitlines()
        assert len(mk) == 2 and mk[0] == mk[1], mk
        if not any(x.split(" ")[0] == a[-1] for x in s):
            print("Failed to find entry for user " + a[-1], file=sys.stderr); sys.exit(1)
        open(sam, "w").write("".join((a[-1] + " " + mk[0] if x.split(" ")[0] == a[-1] else x) + "\n" for x in s))
'''

INSTALL_GIA = r'''#!/usr/bin/env python3
import os, sys
a, kq, i = sys.argv[1:], [], 0
while i < len(a):
    if a[i] in ("-o", "-g", "-m"):
        if a[i] == "-m": kq += a[i:i + 2]
        i += 2
    else:
        kq.append(a[i]); i += 1
os.execv("/usr/bin/install", ["install"] + kq)
'''


def render(env, ten, **v):
    return env.from_string(open(os.path.join(TEMPLATES, ten), encoding="utf-8").read()).render(**v)


@unittest.skipUnless(HAVE_TOOLS, "cần openssh-client + apache2-utils")
class OnebeeBoxShell(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.t = self.tmp.name
        for d in ("lib", "bin", "secrets", "ssh", "data/restic", "data/tinh-trang-may", "box", "out", "tmp", "etc"):
            os.makedirs(os.path.join(t, d))
        v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
        v.update(onebee_box_secrets=f"{t}/secrets", onebee_box_ssh_dir=f"{t}/ssh", onebee_box_data=f"{t}/data",
                 onebee_box_dir=f"{t}/box", onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="kiem-thu")
        env = jinja2.Environment(keep_trailing_newline=True)
        env.filters["to_json"] = lambda x: json.dumps(x, ensure_ascii=False)
        env.filters["quote"] = shlex.quote
        env.filters["bool"] = bool
        lib = f"{t}/lib"

        def sua(txt):  # đường dẫn cố định của máy thật → thư mục tạm; bỏ kiểm quyền root
            # /var/log/onebee-box: nhật ký dong-bo-may/cap-nhat-may — không có quyền ghi khi CI chạy không phải root (và không nên ghi bừa vào máy chạy test)
            # /run/onebee-box.lock: khóa chống chạy chồng (with_lock) — CI không phải root nên không ghi được /run
            return (txt.replace("/usr/local/lib/onebee-box", lib).replace("/var/log/onebee-box", f"{t}/log")
                    .replace("/run/onebee-box.lock", f"{t}/onebee-box.lock")
                    .replace("/etc/onebee-box/samba-phong-ban.conf", f"{t}/etc/samba-phong-ban.conf")
                    .replace("/var/lib/onebee-box/xin-vao-da-cap.log", f"{t}/out/xin-vao-da-cap.log")
                    .replace("/usr/local/bin/onebee-canh-bao", f"{t}/bin/onebee-canh-bao")
                    .replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||"))
        files = {"common.sh": "onebee-box-common.sh.j2", "sao-luu.sh": "onebee-box-sao-luu.sh.j2", "chan-doan.sh": "onebee-box-chan-doan.sh.j2",
                 "phong-ban.sh": "onebee-box-phong-ban.sh.j2"}
        for dst, src in files.items():
            open(f"{lib}/{dst}", "w", encoding="utf-8").write(sua(render(env, src, **v)))
        self.cmd = f"{t}/bin/onebee-box"
        open(self.cmd, "w", encoding="utf-8").write(sua(render(env, "onebee-box.sh.j2", **v)))
        shutil.copy(os.path.join(ROLES, "box-fleet/files/onebee-may-tram.py"), f"{lib}/onebee-may-tram.py")
        shutil.copy(os.path.join(ROLES, "box-fleet/files/onebee-bao-cao-tuan.py"), f"{lib}/onebee-bao-cao-tuan.py")
        shutil.copy(os.path.join(ROLES, "box-du-lieu/files/onebee-chuyen-du-lieu.py"), f"{lib}/onebee-chuyen-du-lieu.py")
        shutil.copy(os.path.join(ROLES, "box-stack/files/onebee-ca.sh"), f"{lib}/onebee-ca.sh")
        # CA riêng của Box (bộ cài sinh bước này trước khi sinh các lệnh)
        subprocess.run([f"{lib}/onebee-ca.sh", f"{t}/secrets/ca", "kiem-thu", "192.168.1.10"], check=True, capture_output=True)
        for ten, nd in (("onebee-ai-rag.py", AI_RAG_GIA),):
            open(f"{lib}/{ten}", "w").write(nd)
        docker_gia = '#!/bin/sh\necho "docker $*" >> "$ONEBEE_OUT/docker.log"\n'
        for ten, nd in (("ssh", SSH_GIA), ("ansible-playbook", ANSIBLE_GIA), ("install", INSTALL_GIA), ("chown", "#!/bin/sh\nexit 0\n"), ("docker", docker_gia),
                        ("chgrp", '#!/bin/sh\necho "chgrp $*" >> "$ONEBEE_OUT/chgrp.log"\n'),
                        ("smbcontrol", '#!/bin/sh\necho "smbcontrol $*" >> "$ONEBEE_OUT/samba.log"\n'),
                        ("onebee-canh-bao", '#!/bin/sh\nprintf "%s|%s|%s\\n" "$1" "$2" "$3" >> "$ONEBEE_OUT/canh-bao.log"\nexit "${ONEBEE_CANH_BAO_RC:-0}"\n'),
                        *((x, HE_THONG_GIA) for x in ("getent", "groupadd", "useradd", "pdbedit", "smbpasswd"))):
            open(f"{t}/bin/{ten}", "w").write(nd)
        for f in os.listdir(f"{t}/bin") + [os.path.join("..", "lib", "onebee-ai-rag.py")]:
            os.chmod(os.path.join(t, "bin", f), 0o755)
        # khóa quản trị của Box (chỉ để tên file tồn tại; ssh giả không đọc)
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", f"{t}/ssh/quan-tri"], check=True)
        open(f"{t}/data/restic/.htpasswd", "w").close()    # Ansible tạo file rỗng này trên Box thật
        open(f"{t}/secrets/tinh-trang-key", "w").write("khoa-chung-0123456789abcdef0123456789\n")
        self.env = dict(os.environ, PATH=f"{t}/bin:{os.environ['PATH']}", ONEBEE_OUT=f"{t}/out", ONEBEE_SIM=f"{t}/sim.json",
                        ONEBEE_SSH_LOG=f"{t}/out/ssh.log", TMPDIR=f"{t}/tmp")
        self.sim = {}
        self.dat_sim()
        spec = __import__("importlib.util").util.spec_from_file_location("mt", f"{lib}/onebee-may-tram.py")
        self.mt = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(self.mt)

    # ---- tiện ích ----
    def dat_sim(self):
        json.dump(self.sim, open(f"{self.t}/sim.json", "w"))

    def chay(self, *args, kiem=True):
        # stdin rỗng (không phải cửa sổ dòng lệnh): như khi chạy từ tập lệnh / dịch vụ, không có dấu nhắc nào chờ
        r = subprocess.run(["bash", self.cmd, *args], env=self.env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if kiem and r.returncode != 0:
            self.fail(f"onebee-box {' '.join(args)} lỗi ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def ssh_goi(self):
        p = f"{self.t}/out/ssh.log"
        return open(p).read().splitlines() if os.path.exists(p) else []

    def ansible_goi(self):
        return sorted(d for d in os.listdir(f"{self.t}/out") if d.startswith("ansible-"))

    def bao_cao(self, ten, ip, ky=True, mat_khau=None, tuoi=0):
        """Ghi file tình trạng như động cơ quy trình ghi: có chữ ký (đúng mật khẩu kho của máy) hoặc dạng cũ."""
        now = time.time() - tuoi
        mk = mat_khau or open(f"{self.t}/secrets/may-{ten}-repo").read().strip()
        if ky:
            dl = json.dumps({"ten": ten, "ip": ip, "gui_luc": now})
            nd = {"ten": ten, "dinh_dang": 2, "du_lieu": dl, "ky": self.mt.ky_bao_cao(mk, dl), "nhan_luc": now}
        else:
            nd = {"ten": ten, "ip": ip, "nhan_luc": now}
        json.dump(nd, open(f"{self.t}/data/tinh-trang-may/{ten}.json", "w"))

    def mat_khau(self, ten):
        return open(f"{self.t}/secrets/may-{ten}-repo").read().strip()

    def khoa_host(self, ten="may"):
        p = f"{self.t}/hk-{ten}"
        if not os.path.exists(p):
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", p], check=True)
        return " ".join(open(p + ".pub").read().split()[:2])

    def da_ghim(self, ten):
        return subprocess.run(["ssh-keygen", "-F", ten, "-f", f"{self.t}/ssh/known_hosts"], capture_output=True).returncode == 0

    def cap_may(self, ten, ip, khoa=None):
        self.chay("them-may", ten)
        self.sim[ip] = {"hostkey": khoa or self.khoa_host(ten), "password": self.mat_khau(ten)}
        self.dat_sim()
        self.bao_cao(ten, ip)

    # ---- kiểm thử ----
    def docker_log(self):
        """Các lệnh docker (giả) đã gọi tới giờ, để so trước/sau một lệnh onebee-box."""
        f = f"{self.t}/out/docker.log"
        return open(f).read() if os.path.exists(f) else ""

    def test_ma_nguon_shell_hop_le(self):
        for f in ("lib/common.sh", "lib/sao-luu.sh", "lib/phong-ban.sh", "bin/onebee-box"):
            r = subprocess.run(["bash", "-n", f"{self.t}/{f}"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        if shutil.which("shellcheck"):
            r = subprocess.run(["shellcheck", "-e", "SC2016,SC1091,SC2034", "-s", "bash", f"{self.t}/bin/onebee-box"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_them_may_in_9_dong_ghi_danh_sach_va_hoi(self):
        r = self.chay("them-may", "ketoan-01")
        kv = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l and not l.startswith("#"))
        for k in ("MAY_TRAM", "BOX_IP", "RESTIC_REPOSITORY", "RESTIC_PASSWORD", "HOI_URL", "HOI_API_KEY", "TINH_TRANG_URL",
                  "TINH_TRANG_KEY", "QUAN_TRI_SSH_KEY", "BOX_CA", "BOX_CA_VAN_TAY"):
            self.assertTrue(kv.get(k), k)
        # BOX_CA = chứng chỉ gốc (DER base64 một dòng) và vân tay khớp chính chứng chỉ đó
        der = base64.b64decode(kv["BOX_CA"])
        self.assertEqual(hashlib.sha256(der).hexdigest(), kv["BOX_CA_VAN_TAY"])
        self.assertRegex(kv["HOI_API_KEY"], r"^obk-[0-9a-f]{48}$")
        self.assertTrue(os.path.exists(f"{self.t}/data/may-da-cap/ketoan-01"))      # động cơ quy trình sẽ nhận báo cáo của máy này
        self.assertIn("ketoan-01:", open(f"{self.t}/data/restic/.htpasswd").read())
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-khoa").read(), kv["HOI_API_KEY"])  # lưu để in lại không gọi dịch vụ
        # in lại cấu hình (dong-bo-may) không cấp khóa mới
        log = f"{self.t}/out/ai-rag.log"
        self.assertEqual(open(log).read().strip().splitlines(), ["khoa cap may ketoan-01"])

    def test_cau_hinh_may_co_ten_box_ngay_sau_ip(self):
        """Máy trạm (role ket-noi-box) ghi dòng /etc/hosts <IP Box> box.<mã>.onebee.internal từ hai dòng này (đăng nhập một lần chỉ mở bằng tên)."""
        for https in (False, True):
            if https:
                open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
            dong = [l for l in self.chay("them-may", "ketoan-01").stdout.splitlines() if "=" in l and not l.startswith("#")]
            khoa = [l.split("=", 1)[0] for l in dong]
            i = khoa.index("BOX_IP")
            self.assertEqual(dong[i], "BOX_IP=192.168.1.10")
            self.assertEqual(dong[i + 1], "BOX_TEN=box.kiem-thu.onebee.internal")
            self.assertEqual(khoa.count("BOX_TEN"), 1)

    def test_in_ca_in_van_tay_va_rang_buoc(self):
        r = self.chay("in-ca").stdout
        vt = open(f"{self.t}/secrets/ca/root.sha256").read().strip().upper()
        self.assertIn(":".join(vt[i:i + 2] for i in range(0, 64, 2)), r)
        self.assertIn("IP:192.168.1.10/255.255.255.255", r)
        self.assertIn("DNS:kiem-thu.onebee.internal", r)
        # Ghép chuỗi để từ khóa không nằm nguyên văn trong kho mã; bài kiểm vẫn kiểm đúng nội dung
        self.assertNotIn("PRIVATE" + " KEY", r)

    def test_in_khoa_khong_in_khoa_rieng_cua_ca_nhung_co_van_tay(self):
        r = self.chay("in-khoa").stdout
        # Ghép chuỗi để từ khóa không nằm nguyên văn trong kho mã; bài kiểm vẫn kiểm đúng nội dung
        self.assertNotIn("PRIVATE" + " KEY", r)
        self.assertIn("van-tay-ca-onebee-box=" + open(f"{self.t}/secrets/ca/root.sha256").read().strip(), r)

    def test_khong_in_cau_hinh_khi_thieu_ca(self):
        self.chay("them-may", "ketoan-01")
        shutil.rmtree(f"{self.t}/secrets/ca")
        r = self.chay("dong-bo-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)   # thiếu CA → không dựng được cấu hình → không đẩy gì
        self.assertNotIn("BOX_CA", r.stdout)

    def kv(self, ten="ketoan-01"):
        r = self.chay("them-may", ten)
        return dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l and not l.startswith("#"))

    def test_http_hay_https_theo_dau_https_da_bat(self):
        kv = self.kv()
        self.assertEqual(kv["BOX_HTTPS"], "0")
        self.assertTrue(kv["RESTIC_REPOSITORY"].startswith("rest:http://"))
        # Trợ lý AI chỉ chạy qua HTTPS trên tên Box (tuyến lõi), không phụ thuộc chế độ cổng Caddy
        self.assertEqual(kv["HOI_URL"], "https://box.kiem-thu.onebee.internal")
        self.assertTrue(kv["TINH_TRANG_URL"].startswith("http://"))
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        kv = self.kv()
        self.assertEqual(kv["BOX_HTTPS"], "1")
        self.assertTrue(kv["RESTIC_REPOSITORY"].startswith("rest:https://ketoan-01:"))
        self.assertEqual(kv["HOI_URL"], "https://box.kiem-thu.onebee.internal")
        self.assertEqual(kv["TINH_TRANG_URL"], "https://box.kiem-thu.onebee.internal/webhook/onebee-tinh-trang")

    def thay_khoa_may(self, gia_tri):
        """Dựng lại lệnh với onebee_box_hoi_khoa_may khác (giá trị lưu trong common.sh)."""
        p = f"{self.t}/lib/common.sh"
        s = open(p, encoding="utf-8").read()
        s2 = s.replace('HOI_KHOA_MAY="true"', f'HOI_KHOA_MAY="{gia_tri}"')
        self.assertNotEqual(s, s2)
        open(p, "w", encoding="utf-8").write(s2)

    def test_tat_khoa_tinh_trang_chung_thi_khong_in_khoa_nay(self):
        kv = self.kv("ketoan-01")
        self.assertTrue(kv["TINH_TRANG_KEY"])                                                 # chuyển tiếp: còn khóa
        p = f"{self.t}/lib/common.sh"
        s = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(s.replace('TINH_TRANG_KHOA_CHUNG="true"', 'TINH_TRANG_KHOA_CHUNG="false"'))
        os.unlink(f"{self.t}/secrets/tinh-trang-key")                                         # thiếu file khóa cũng không còn là lỗi
        kv = self.kv("kho-02")
        self.assertNotIn("TINH_TRANG_KEY", kv)
        self.assertTrue(kv["RESTIC_PASSWORD"] and kv["BOX_CA"])
        self.assertFalse(os.path.exists(f"{self.t}/secrets/tinh-trang-key"))                  # them-may không tạo lại

    def test_tat_khoa_hoi_theo_may_thi_khong_cap_khoa_nhung_van_in_dia_chi(self):
        self.thay_khoa_may("false")
        kv = self.kv("ketoan-01")
        self.assertNotIn("HOI_API_KEY", kv)
        self.assertEqual(kv["HOI_URL"], "https://box.kiem-thu.onebee.internal")          # hoi --dan-khoa cần địa chỉ
        log = f"{self.t}/out/ai-rag.log"
        self.assertNotIn("khoa cap", open(log).read() if os.path.exists(log) else "")     # không cấp khóa theo máy
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-khoa"))

    def test_go_khoa_hoi_may_chi_khi_da_tat_va_xoa_dung(self):
        self.kv("ketoan-01")
        r = self.chay("go-khoa-hoi-may", kiem=False)
        self.assertNotEqual(r.returncode, 0)                                                # còn bật khóa theo máy → từ chối
        self.thay_khoa_may("false")
        r = self.chay("go-khoa-hoi-may")
        self.assertIn("ketoan-01", r.stdout)
        self.assertIn("khoa go may ketoan-01", open(f"{self.t}/out/ai-rag.log").read())
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-khoa"))
        self.assertTrue(os.path.exists(f"{self.t}/secrets/may-ketoan-01-repo"))            # chỉ bỏ khóa hoi, máy vẫn được cấp

    def test_xoay_khoa_may_doi_mat_khau_kho_va_khoa_hoi_roi_day_xuong_may(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        http_cu = open(f"{self.t}/secrets/may-ketoan-01-http").read()
        htp_cu = open(f"{self.t}/data/restic/.htpasswd").read()
        repo_cu = open(f"{self.t}/secrets/may-ketoan-01-repo").read()
        docker_truoc = self.docker_log()
        r = self.chay("xoay-khoa", "--may", "ketoan-01", "--dong-y")
        self.assertNotEqual(open(f"{self.t}/secrets/may-ketoan-01-http").read(), http_cu)
        self.assertNotEqual(open(f"{self.t}/data/restic/.htpasswd").read(), htp_cu)           # htpasswd cập nhật theo mật khẩu mới
        # rest-server chỉ tự đọc lại .htpasswd ≤30 giây/lần → phải SIGHUP để mật khẩu cũ hết hiệu lực NGAY (lỗi bắt được khi chạy A4 trên Docker thật);
        # gửi qua docker exec, không 'docker kill' (Docker coi là dừng tay → Box khởi động lại thì kho sao lưu không tự chạy)
        self.assertNotIn("docker kill", self.docker_log())
        self.assertIn("docker exec onebee-rest-server kill -HUP 1", self.docker_log()[len(docker_truoc):])
        khoa_moi = open(f"{self.t}/secrets/may-ketoan-01-khoa").read()
        self.assertRegex(khoa_moi, r"^obk-[0-9a-f]{48}$")
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-repo").read(), repo_cu)       # RESTIC_PASSWORD KHÔNG xoay
        self.assertIn("khoa cap may ketoan-01", open(f"{self.t}/out/ai-rag.log").read())
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1)
        self.assertIn("dong-bo-may-tram.yml", open(f"{self.t}/out/{goi[0]}/args").read())     # đã đẩy xuống máy
        self.assertIn("RESTIC_REPOSITORY", "".join(open(f"{self.t}/out/{goi[0]}/cau-hinh/{f}").read() for f in os.listdir(f"{self.t}/out/{goi[0]}/cau-hinh")))
        self.assertNotIn(open(f"{self.t}/secrets/may-ketoan-01-http").read(), r.stdout + r.stderr)   # không in mật khẩu ra màn hình

    def test_xoay_khoa_can_xac_nhan_va_dung_may(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        log = f"{self.t}/out/ai-rag.log"
        truoc = open(log).read() if os.path.exists(log) else ""
        self.assertNotEqual(self.chay("xoay-khoa", "--may", "khong-co", "--dong-y", kiem=False).returncode, 0)
        self.assertNotEqual(self.chay("xoay-khoa", kiem=False).returncode, 0)
        r = subprocess.run([self.cmd, "xoay-khoa", "--may", "ketoan-01"], capture_output=True, text=True, env=self.env, input="khong\n")
        self.assertNotEqual(r.returncode, 0)                                                   # không gõ đúng câu xác nhận → hủy
        self.assertEqual(open(log).read() if os.path.exists(log) else "", truoc)               # hủy thì không cấp khóa mới

    def test_xoay_khoa_box_doi_bi_mat_va_chay_bo_cai(self):
        for f, nd in (("webui-admin-password", "admin-cu"), ("quy-trinh-soan-luong", "soan-cu"), ("quy-trinh-soan-hash", "h-cu"), ("webui-secret-key", "sk-cu"),
                      ("bieu-mau-nhanvien", "nv-cu"), ("bieu-mau-kythuat", "kt-cu"), ("quy-trinh-webhook-key", "wh-cu"),
                      ("authelia-session-secret", "ss-cu"), ("cau-noi-jwt-secret", "jwt-cu"), ("authelia-storage-key", "sk-cu"),
                      ("authelia-jwt-secret", "aj-cu")):
            open(f"{self.t}/secrets/{f}", "w").write(nd)
        bo_cai = f"{self.t}/bo-cai.sh"
        open(bo_cai, "w").write(f"#!/bin/sh\necho chay > {self.t}/out/bo-cai.log\n")
        os.chmod(bo_cai, 0o755)
        open(f"{self.t}/lib/duong-dan-bo-cai", "w").write(bo_cai + "\n")
        self.chay("xoay-khoa", "--box", "--dong-y")
        soan = open(f"{self.t}/secrets/quy-trinh-soan-luong").read()
        self.assertNotEqual(soan, "soan-cu")
        self.assertTrue(open(f"{self.t}/secrets/quy-trinh-soan-hash").read().startswith("$2"))      # bcrypt
        for f in ("webui-secret-key", "webui-admin-password", "bieu-mau-nhanvien", "bieu-mau-kythuat",
                  "authelia-session-secret", "cau-noi-jwt-secret"):
            self.assertFalse(os.path.exists(f"{self.t}/secrets/{f}"), f)                      # để bộ cài (Ansible) sinh lại
        # Khóa mã hóa CSDL định danh giữ nguyên (xóa là mất mọi ghi danh hai lớp); khóa JWT đặt lại mật khẩu không xoay
        self.assertEqual(open(f"{self.t}/secrets/authelia-storage-key").read(), "sk-cu")
        self.assertEqual(open(f"{self.t}/secrets/authelia-jwt-secret").read(), "aj-cu")
        self.assertNotEqual(open(f"{self.t}/secrets/quy-trinh-webhook-key").read(), "wh-cu")
        self.assertTrue(os.path.exists(f"{self.t}/out/bo-cai.log"))                            # đã chạy bộ cài để áp dụng

    def docker_csdl_gia(self, loi_exec=False, ket_xuat="BAN-KET-XUAT"):
        """docker giả ghi lại cả stdin và mật khẩu đang nằm trong tệp bí mật lúc gọi (để kiểm ALTER ROLE chạy TRƯỚC khi ghi tệp mới)."""
        nd = (f'#!/bin/bash\necho "docker $*" >> "$ONEBEE_OUT/docker.log"\n'
              f'if [[ "$1" == exec && " $* " == *" -i "* ]]; then {{ echo "--- $*"; cat; '
              f'echo "tep: $(cat {self.t}/secrets/postgres-password 2>/dev/null) $(cat {self.t}/secrets/postgrest-password 2>/dev/null)"; }} >> "$ONEBEE_OUT/docker-stdin.log"; fi\n'
              + ('[[ "$1" != exec ]] || exit 1\n' if loi_exec else "")
              + f'[[ "$1 $2 $3" != "exec onebee-postgres pg_dump" ]] || printf %s {ket_xuat}\n')
        open(f"{self.t}/bin/docker", "w").write(nd)

    def test_xoay_khoa_box_doi_mat_khau_csdl_trong_csdl_truoc_roi_moi_ghi_tep(self):
        for f, nd in (("postgres-password", "pgcu0123456789abcdef"), ("postgrest-password", "apicu0123456789abcdef")):
            open(f"{self.t}/secrets/{f}", "w").write(nd)
        self.bo_cai_gia()
        self.docker_csdl_gia()
        self.chay("xoay-khoa", "--box", "--dong-y")
        pg, api = (open(f"{self.t}/secrets/{f}").read() for f in ("postgres-password", "postgrest-password"))
        self.assertRegex(pg, r"^[A-Za-z0-9]{32}$")
        self.assertRegex(api, r"^[A-Za-z0-9]{32}$")
        vao = open(f"{self.t}/out/docker-stdin.log").read()
        # postgres đổi khi cả hai tệp còn cũ; xac_thuc đổi khi tệp postgres đã mới, tệp postgrest còn cũ
        self.assertIn(f"ALTER ROLE postgres PASSWORD '{pg}';\ntep: pgcu0123456789abcdef apicu0123456789abcdef", vao)
        self.assertIn(f"ALTER ROLE xac_thuc PASSWORD '{api}';\ntep: {pg} apicu0123456789abcdef", vao)
        self.assertNotIn(pg, self.docker_log())                                                  # mật khẩu không nằm trên dòng lệnh
        self.assertNotIn(api, self.docker_log())
        self.assertTrue(os.path.exists(f"{self.t}/out/bo-cai.log"))                            # bộ cài dựng lại PostgREST (.env mới)

    def test_xoay_khoa_box_csdl_loi_thi_giu_mat_khau_cu_va_dung(self):
        for f, nd in (("postgres-password", "pgcu0123456789abcdef"), ("postgrest-password", "apicu0123456789abcdef")):
            open(f"{self.t}/secrets/{f}", "w").write(nd)
        self.bo_cai_gia()
        self.docker_csdl_gia(loi_exec=True)
        r = self.chay("xoay-khoa", "--box", "--dong-y", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Không đổi được mật khẩu CSDL", r.stderr)
        self.assertEqual(open(f"{self.t}/secrets/postgres-password").read(), "pgcu0123456789abcdef")
        self.assertEqual(open(f"{self.t}/secrets/postgrest-password").read(), "apicu0123456789abcdef")
        self.assertFalse(os.path.exists(f"{self.t}/out/bo-cai.log"))

    def chuan_bi_sao_luu(self):
        """Ổ sao lưu đã gắn, kho Box đã tạo (restic giả ghi lại tham số)."""
        for ten, nd in (("mountpoint", "#!/bin/sh\nexit 0\n"),
                        ("restic", '#!/bin/sh\necho "restic $*" >> "$ONEBEE_OUT/restic.log"\necho "$RESTIC_REPOSITORY" >> "$ONEBEE_OUT/restic-kho.log"\n'
                                   '[ "$1" != snapshots ] || echo "[]"\n'),
                        ("curl", "#!/bin/sh\nexit 7\n")):
            open(f"{self.t}/bin/{ten}", "w").write(nd)
            os.chmod(f"{self.t}/bin/{ten}", 0o755)
        open(f"{self.t}/secrets/restic-box", "w").write("mk-kho-box")

    def bat_o_ngoai(self):
        """Phương án phụ (onebee_box_backup_o_ngoai: true): sửa lệnh đã dựng sang kho trên ổ ngoài."""
        p = f"{self.t}/lib/common.sh"
        nd = re.sub(r'(?m)^BACKUP_O_NGOAI=.*$', 'BACKUP_O_NGOAI="true"', open(p, encoding="utf-8").read())
        nd = re.sub(r'(?m)^BACKUP_REPO=.*$', f'BACKUP_REPO="{self.t}/mnt/onebee-sao-luu/restic-box"', nd)
        open(p, "w", encoding="utf-8").write(nd)

    def df_gia(self, phan_tram):
        open(f"{self.t}/bin/df", "w").write(
            f'#!/bin/sh\necho "Filesystem 1024-blocks Used Available Capacity Mounted on"\necho "/dev/sda1 100 {phan_tram} {100 - phan_tram} {phan_tram}% /srv"\n')
        os.chmod(f"{self.t}/bin/df", 0o755)

    def test_sao_luu_mac_dinh_ghi_vao_o_du_lieu_box_khong_can_gan_o(self):
        self.chuan_bi_sao_luu()
        open(f"{self.t}/bin/mountpoint", "w").write("#!/bin/sh\nexit 1\n")                     # không có ổ ngoài nào
        self.df_gia(60)
        self.docker_csdl_gia()
        self.chay("sao-luu", kiem=False)
        kho = f"{self.t}/data/sao-luu/restic-box"
        self.assertIn("--tag csdl", open(f"{self.t}/out/restic.log").read())
        self.assertEqual(set(open(f"{self.t}/out/restic-kho.log").read().split()) - {""}, {kho})   # mọi lệnh restic của Box đều vào kho trong ổ Box
        self.assertEqual(os.stat(f"{self.t}/data/sao-luu").st_mode & 0o777, 0o700)

    def test_khoi_tao_mac_dinh_tao_kho_trong_o_box(self):
        self.chuan_bi_sao_luu()
        open(f"{self.t}/bin/restic", "w").write('#!/bin/sh\necho "restic $*" >> "$ONEBEE_OUT/restic.log"\necho "$RESTIC_REPOSITORY" >> "$ONEBEE_OUT/restic-kho.log"\n'
                                                 '[ "$1 $2" != "cat config" ] || exit 1\n')                # chưa có kho
        r = self.chay("khoi-tao")
        self.assertIn("restic init", open(f"{self.t}/out/restic.log").read())
        self.assertIn(f"{self.t}/data/sao-luu/restic-box", open(f"{self.t}/out/restic-kho.log").read())
        self.assertNotIn("Chưa gắn ổ", r.stdout + r.stderr)

    def test_sao_luu_vao_o_box_dung_khi_o_du_lieu_gan_day(self):
        self.chuan_bi_sao_luu()
        self.df_gia(95)
        self.docker_csdl_gia()
        r = self.chay("sao-luu", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Ổ dữ liệu Box đã dùng 95%", r.stdout + r.stderr)
        self.assertNotIn("restic backup", open(f"{self.t}/out/restic.log").read() if os.path.exists(f"{self.t}/out/restic.log") else "")
        self.assertNotIn(" pause ", self.docker_log())                                           # dừng trước khi tạm dừng dịch vụ

    def test_sao_luu_ket_xuat_csdl_truoc_khi_tam_dung_va_dua_vao_ban_csdl(self):
        self.chuan_bi_sao_luu()
        self.docker_csdl_gia()
        self.chay("sao-luu", kiem=False)
        kx = f"{self.t}/data/postgres-ket-xuat"
        self.assertEqual(open(f"{kx}/onebee.dump").read(), "BAN-KET-XUAT")
        self.assertEqual(sorted(os.listdir(kx)), ["onebee.dump"])                              # không còn tệp tạm
        log = self.docker_log().splitlines()
        dump = [i for i, d in enumerate(log) if "exec onebee-postgres pg_dump -U postgres -d onebee -Fc" in d]
        pause = [i for i, d in enumerate(log) if d.endswith(" pause quy-trinh uptime-kuma authelia seaweedfs kho-tep")]
        self.assertTrue(dump and pause, log)
        self.assertLess(dump[0], pause[0])                                                       # không exec được trong container đang dừng
        ban_csdl = [d for d in open(f"{self.t}/out/restic.log").read().splitlines() if d.startswith("restic backup") and "--tag csdl" in d][0]
        self.assertIn(f" {kx} ", ban_csdl + " ")
        self.assertIn(f" {self.t}/data/seaweedfs ", ban_csdl + " ")                              # dữ liệu kho tệp trong bản chụp CSDL
        self.assertNotIn(f"{self.t}/data/postgres ", ban_csdl + " ")                             # không chụp thư mục sống

    def test_sao_luu_dung_khi_ket_xuat_csdl_loi(self):
        self.chuan_bi_sao_luu()
        self.docker_csdl_gia(ket_xuat="")                                                        # pg_dump không ra gì
        r = self.chay("sao-luu", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Không kết xuất được CSDL", r.stdout + r.stderr)
        self.assertNotIn(" pause ", self.docker_log())
        self.assertNotIn("restic backup", open(f"{self.t}/out/restic.log").read())
        self.assertFalse(os.path.exists(f"{self.t}/data/postgres-ket-xuat/onebee.dump"))

    def test_xoay_khoa_box_thu_lai_kuma_khi_chua_san_sang_va_dung_khi_sai_mat_khau(self):
        self.bo_cai_gia()
        open(f"{self.t}/lib/onebee-kuma.js", "w").write("// gia\n")
        open(f"{self.t}/secrets/uptime-kuma-da-co-quan-tri", "w").write("1\n")
        open(f"{self.t}/secrets/uptime-kuma-password", "w").write("kuma-cu")
        open(f"{self.t}/bin/sleep", "w").write('#!/bin/sh\necho "sleep $*" >> "$ONEBEE_OUT/sleep.log"\n')
        os.chmod(f"{self.t}/bin/sleep", 0o755)
        docker_gia = (
            '#!/bin/bash\necho "docker $*" >> "$ONEBEE_OUT/docker.log"\n'
            'if [[ " $* " == *" onebee-uptime-kuma "* ]]; then\n'
            '  n=$(( $(cat "$ONEBEE_OUT/kuma-n" 2>/dev/null || echo 0) + 1 ))\n'
            '  echo "$n" > "$ONEBEE_OUT/kuma-n"\n'
            '  [[ -z "${ONEBEE_KUMA_RC:-}" ]] || exit "${ONEBEE_KUMA_RC}"\n'
            '  [[ "$n" -ge 2 ]] && exit 0 || exit 1\n'
            'fi\n'
        )
        open(f"{self.t}/bin/docker", "w").write(docker_gia)
        os.chmod(f"{self.t}/bin/docker", 0o755)
        self.chay("xoay-khoa", "--box", "--dong-y")
        self.assertEqual(open(f"{self.t}/out/kuma-n").read().strip(), "2")
        self.assertIn("sleep 5", open(f"{self.t}/out/sleep.log").read())
        self.assertNotEqual(open(f"{self.t}/secrets/uptime-kuma-password").read(), "kuma-cu")
        # Mã 3 = sai mật khẩu quản trị → dừng ngay, không thử lại và giữ mật khẩu cũ
        open(f"{self.t}/secrets/uptime-kuma-password", "w").write("kuma-cu")
        os.remove(f"{self.t}/out/kuma-n")
        os.remove(f"{self.t}/out/bo-cai.log")
        env = dict(self.env, ONEBEE_KUMA_RC="3")
        r = subprocess.run([self.cmd, "xoay-khoa", "--box", "--dong-y"], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(f"{self.t}/out/kuma-n").read().strip(), "1")
        self.assertEqual(open(f"{self.t}/secrets/uptime-kuma-password").read(), "kuma-cu")
        self.assertFalse(os.path.exists(f"{self.t}/out/bo-cai.log"))

    def bo_cai_gia(self):
        """Bộ cài giả: như Ansible thật, sinh lại khóa gửi tình trạng dùng chung mà xoay-khoa --box vừa xóa."""
        bo_cai = f"{self.t}/bo-cai.sh"
        open(bo_cai, "w").write(f"#!/bin/sh\necho chay > {self.t}/out/bo-cai.log\n"
                                f"[ -s {self.t}/secrets/tinh-trang-key ] || echo khoa-tinh-trang-moi > {self.t}/secrets/tinh-trang-key\n")
        os.chmod(bo_cai, 0o755)
        open(f"{self.t}/lib/duong-dan-bo-cai", "w").write(bo_cai + "\n")

    def test_xoay_khoa_box_tu_day_khoa_tinh_trang_moi_xuong_moi_may(self):
        """Khóa gửi tình trạng dùng chung đổi mà máy trạm không nhận → máy báo tình trạng bị 403 tới khi quản trị nhớ chạy dong-bo-may."""
        self.cap_may("ketoan-01", "10.1.1.5")
        self.cap_may("kho-02", "10.1.1.6")
        self.bo_cai_gia()
        r = self.chay("xoay-khoa", "--box", "--dong-y")
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1, r.stdout + r.stderr)                                      # một lần đẩy cho mọi máy
        d = f"{self.t}/out/{goi[0]}"
        self.assertIn("dong-bo-may-tram.yml", open(f"{d}/args").read())
        self.assertEqual(sorted(os.listdir(f"{d}/cau-hinh")), ["ketoan-01.env", "kho-02.env"])
        for f in os.listdir(f"{d}/cau-hinh"):
            self.assertIn("TINH_TRANG_KEY=khoa-tinh-trang-moi", open(f"{d}/cau-hinh/{f}").read())
        self.assertNotIn("LƯU Ý: sau bộ cài", r.stdout)                                       # đã tự làm, không bắt quản trị nhớ

    def test_xoay_khoa_box_khi_tat_khoa_tinh_trang_chung_thi_khong_day_xuong_may(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        p = f"{self.t}/lib/common.sh"
        s = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(s.replace('TINH_TRANG_KHOA_CHUNG="true"', 'TINH_TRANG_KHOA_CHUNG="false"'))
        self.bo_cai_gia()
        self.chay("xoay-khoa", "--box", "--dong-y")
        self.assertEqual(self.ansible_goi(), [])

    def test_xoay_khoa_may_dang_tat_chi_canh_bao_khong_vo_lenh(self):
        """Máy tắt: mật khẩu kho đã đổi trên Box nhưng chưa đẩy được → trước đây die "Không có máy nào để làm", mất lời nhắc dong-bo-may."""
        self.cap_may("ketoan-01", "10.1.1.5")
        http_cu = open(f"{self.t}/secrets/may-ketoan-01-http").read()
        del self.sim["10.1.1.5"]                                                                # máy tắt: SSH timeout
        self.dat_sim()
        r = self.chay("xoay-khoa", "--may", "ketoan-01", "--dong-y", kiem=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotEqual(open(f"{self.t}/secrets/may-ketoan-01-http").read(), http_cu)
        self.assertIn("Máy trạm ketoan-01 hiện đang tắt", r.stderr)
        self.assertIn("sudo onebee-box dong-bo-may ketoan-01", r.stderr)
        self.assertIn("Xong.", r.stdout)
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])

    def test_xoay_khoa_day_loi_tren_may_dang_bat_van_nhac_dong_bo(self):
        """Máy vào được SSH nhưng playbook hỏng giữa chừng: máy chưa nhận mật khẩu kho mới (sao lưu sẽ 401) → phải nhắc riêng máy đó."""
        self.cap_may("ketoan-01", "10.1.1.5")
        self.env["ONEBEE_ANSIBLE_RC"] = "2"
        r = self.chay("xoay-khoa", "--may", "ketoan-01", "--dong-y", kiem=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Máy trạm ketoan-01 có thể chưa nhận cấu hình mới", r.stderr)
        self.assertIn("sudo onebee-box dong-bo-may ketoan-01", r.stderr)
        self.assertIn("Xong.", r.stdout)

    def test_xoay_khoa_khong_dung_duoc_cau_hinh_van_nhac_khong_vo_lenh(self):
        """Thiếu bí mật của máy (cấp dở): mật khẩu đã đổi trên Box → không được dừng giữa chừng, nhắc đúng nguyên nhân (không phải "đang tắt")."""
        self.cap_may("ketoan-01", "10.1.1.5")
        os.unlink(f"{self.t}/secrets/tinh-trang-key")
        r = self.chay("xoay-khoa", "--may", "ketoan-01", "--dong-y", kiem=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Máy trạm ketoan-01 chưa nhận cấu hình mới — không dựng được cấu hình", r.stderr)
        self.assertNotIn("đang tắt", r.stderr)
        self.assertIn("Xong.", r.stdout)

    def test_xoay_khoa_chi_giu_khoa_sau_khi_xac_nhan(self):
        """Dấu nhắc xác nhận để treo không được giữ khóa (sao lưu đêm 23:00 sẽ bị bỏ): hỏi trước, lấy khóa sau."""
        import fcntl
        self.cap_may("ketoan-01", "10.1.1.5")
        with open(f"{self.t}/onebee-box.lock", "w") as khoa:
            fcntl.flock(khoa, fcntl.LOCK_EX)
            r = subprocess.run([self.cmd, "xoay-khoa", "--may", "ketoan-01"], capture_output=True, text=True, env=self.env, input="khong\n")
        self.assertIn("Đã hủy", r.stderr)                                                       # tới được dấu nhắc dù khóa đang bị giữ
        self.assertNotIn("Đang có lệnh", r.stderr)

    def test_xoay_khoa_khong_chay_chong_voi_sao_luu(self):
        import fcntl
        self.cap_may("ketoan-01", "10.1.1.5")
        http_cu = open(f"{self.t}/secrets/may-ketoan-01-http").read()
        with open(f"{self.t}/onebee-box.lock", "w") as khoa:                                    # sao lưu đêm đang giữ khóa
            fcntl.flock(khoa, fcntl.LOCK_EX)
            r = self.chay("xoay-khoa", "--may", "ketoan-01", "--dong-y", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Đang có lệnh", r.stderr)
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-http").read(), http_cu)          # chưa đổi gì

    def lam_trung_gian_sap_het_han(self):
        ca = f"{self.t}/secrets/ca"
        subprocess.run(["openssl", "req", "-new", "-key", f"{ca}/inter.key", "-subj", "/CN=cu", "-out", f"{self.t}/i.csr"], check=True, capture_output=True)
        open(f"{self.t}/i.ext", "w").write("basicConstraints=critical,CA:TRUE,pathlen:0\nnameConstraints=critical,permitted;IP:192.168.1.10/255.255.255.255,"
                                           "permitted;DNS:kiem-thu.onebee.internal\n")
        subprocess.run(["openssl", "x509", "-req", "-in", f"{self.t}/i.csr", "-CA", f"{ca}/root.crt", "-CAkey", f"{ca}/root.key", "-CAcreateserial",
                        "-days", "10", "-extfile", f"{self.t}/i.ext", "-out", f"{ca}/inter.crt"], check=True, capture_output=True)

    def test_gia_han_ca_chep_trung_gian_moi_den_caddy_va_khoi_dong_lai_khi_https(self):
        pki = f"{self.t}/box/portal/pki"
        self.chay("gia-han-ca")                                         # lần đầu: thư mục pki mới → chép
        self.assertEqual(sorted(os.listdir(pki)), ["inter.crt", "inter.key", "root.crt"])
        self.lam_trung_gian_sap_het_han()
        cu = open(f"{pki}/inter.crt").read()
        os.makedirs(f"{self.t}/data/caddy/data/caddy/certificates")
        open(f"{self.t}/data/caddy/data/caddy/certificates/la.crt", "w").write("la cu")
        r = self.chay("gia-han-ca")                                     # HTTP: chỉ chép, không đụng Caddy
        self.assertIn("đã đổi", r.stdout)
        self.assertNotEqual(open(f"{pki}/inter.crt").read(), cu)
        self.assertEqual(open(f"{pki}/inter.crt").read(), open(f"{self.t}/secrets/ca/inter.crt").read())   # Caddy thấy bản mới
        self.assertFalse(os.path.exists(f"{self.t}/out/docker.log"))
        self.lam_trung_gian_sap_het_han()
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        self.chay("gia-han-ca")                                         # HTTPS: xóa chứng chỉ lá cũ + khởi động lại cổng
        self.assertIn("docker restart onebee-portal", open(f"{self.t}/out/docker.log").read())
        self.assertFalse(os.path.exists(f"{self.t}/data/caddy/data/caddy/certificates"))
        r = self.chay("gia-han-ca")                                     # còn hạn → không làm gì
        self.assertEqual(r.stdout.strip(), "")

    def test_sao_luu_chua_gan_o_van_gia_han_ca(self):
        """Phương án ổ ngoài: chưa gắn ổ sao lưu thì sao lưu dừng — nhưng gia hạn CA trung gian phải chạy trước đó, kẻo hết hạn là HTTPS sập."""
        self.chay("gia-han-ca")
        self.lam_trung_gian_sap_het_han()
        cu = open(f"{self.t}/secrets/ca/inter.crt").read()
        self.bat_o_ngoai()
        open(f"{self.t}/bin/mountpoint", "w").write("#!/bin/sh\nexit 1\n")                     # ổ sao lưu chưa gắn
        os.chmod(f"{self.t}/bin/mountpoint", 0o755)
        r = self.chay("sao-luu", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Chưa gắn ổ sao lưu", r.stdout + r.stderr)
        moi = open(f"{self.t}/secrets/ca/inter.crt").read()
        self.assertNotEqual(moi, cu)
        self.assertEqual(open(f"{self.t}/box/portal/pki/inter.crt").read(), moi)                # Caddy thấy bản mới

    def test_may_chua_nhan_ca_cho_den_khi_dong_bo_ghi_dau(self):
        self.kv("ketoan-01")
        self.kv("kho-02")
        self.assertEqual(sorted(self.chay("may-chua-nhan-ca").stdout.split()), ["ketoan-01", "kho-02"])
        os.makedirs(f"{self.t}/secrets/ca-da-dong-bo")
        vt = open(f"{self.t}/secrets/ca/root.sha256").read().strip()
        open(f"{self.t}/secrets/ca-da-dong-bo/ketoan-01", "w").write(vt + "\n")
        self.assertEqual(self.chay("may-chua-nhan-ca").stdout.split(), ["kho-02"])
        open(f"{self.t}/secrets/ca-da-dong-bo/kho-02", "w").write("0" * 64 + "\n")   # dấu của CA cũ (đã xoay CA) không tính
        self.assertEqual(self.chay("may-chua-nhan-ca").stdout.split(), ["kho-02"])

    def test_dong_bo_tat_ca_khi_chua_cap_may_nao_khong_loi(self):
        r = self.chay("dong-bo-may", "--tat-ca")
        self.assertIn("Chưa cấp máy trạm nào", r.stdout)

    def test_chua_cap_thi_khong_vao_danh_sach(self):
        self.assertEqual(self.chay("cap-nhat-may", "la-hoac", kiem=False).returncode, 1)
        self.assertEqual(self.chay("cap-nhat-may", "../etc", kiem=False).returncode, 1)
        self.assertEqual(self.ssh_goi(), [])

    def test_lan_dau_chi_ghim_sau_khi_may_chung_minh(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        r = self.chay("cap-nhat-may", "ketoan-01")
        self.assertIn("Đã ghim khóa SSH của ketoan-01", r.stdout)
        self.assertTrue(self.da_ghim("ketoan-01"))
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1)
        d = f"{self.t}/out/{goi[0]}"
        self.assertIn("ketoan-01 ansible_host=10.1.1.5", open(f"{d}/inventory").read())
        self.assertIn("StrictHostKeyChecking=yes", open(f"{d}/env").read())  # từ giờ khóa lệch là dừng
        self.assertNotIn("accept-new", open(f"{d}/env").read())

    def test_may_gia_khong_biet_mat_khau_khong_duoc_ghim_va_khong_nhan_gi(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.sim["10.1.1.5"]["password"] = "mat-khau-doan-sai"   # kẻ giả mạo đứng ở IP đã báo
        self.dat_sim()
        r = self.chay("cap-nhat-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("KHÔNG chứng minh được", r.stderr)
        self.assertFalse(self.da_ghim("ketoan-01"))
        self.assertEqual(self.ansible_goi(), [])

    def test_bao_cao_chua_ky_khong_du_tin_de_chon_dia_chi(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.bao_cao("ketoan-01", "10.1.1.5", ky=False)   # báo cáo cũ qua HTTP: ai có khóa chung cũng viết được
        r = self.chay("cap-nhat-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("chưa báo tình trạng hợp lệ", r.stderr)
        self.assertEqual(self.ssh_goi(), [])               # thậm chí không SSH tới địa chỉ đó
        # báo cáo ký bằng mật khẩu khác (khóa chung bị lộ + kẻ chiếm động cơ quy trình cũng không ký được)
        self.bao_cao("ketoan-01", "10.1.1.5", mat_khau="doan-mo")
        self.assertNotEqual(self.chay("cap-nhat-may", "ketoan-01", kiem=False).returncode, 0)
        self.assertEqual(self.ssh_goi(), [])

    def test_khoa_ssh_doi_thi_dung_va_ghim_lai_co_chung_minh(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.chay("cap-nhat-may", "ketoan-01")
        truoc = open(f"{self.t}/ssh/known_hosts").read()
        # máy bị đứng ra thay (khóa host khác) dù biết mật khẩu cũng bị chặn bởi khóa đã ghim
        self.sim["10.1.1.5"]["hostkey"] = self.khoa_host("khac")
        self.dat_sim()
        n = len(self.ansible_goi())
        r = self.chay("cap-nhat-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ghim-lai-may", r.stderr)
        self.assertEqual(len(self.ansible_goi()), n)
        self.assertEqual(open(f"{self.t}/ssh/known_hosts").read(), truoc)
        # máy cài lại hệ điều hành thật: bỏ ghim, báo cáo ký mới, chứng minh lại rồi ghim khóa mới
        self.chay("ghim-lai-may", "ketoan-01")
        self.assertFalse(self.da_ghim("ketoan-01"))
        self.bao_cao("ketoan-01", "10.1.1.5")
        self.chay("cap-nhat-may", "ketoan-01")
        self.assertTrue(self.da_ghim("ketoan-01"))
        self.assertEqual(len(self.ansible_goi()), n + 1)

    def test_ghim_cu_do_ban_truoc_tao_van_phai_chung_minh(self):
        """Khóa ghim bởi accept-new của bản cũ có thể đã bị đầu độc (F2): máy giả ghim sẵn vẫn không biết mật khẩu → bị chặn."""
        self.cap_may("ketoan-01", "10.1.1.5")
        ke_gia = self.khoa_host("ke-gia")
        open(f"{self.t}/ssh/known_hosts", "w").write(f"ketoan-01 {ke_gia}\n")     # ghim sẵn khóa của kẻ giả mạo
        self.sim["10.1.1.5"] = {"hostkey": ke_gia, "password": "khong-biet"}
        self.dat_sim()
        r = self.chay("cap-nhat-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.ansible_goi(), [])

    def test_thu_hoi_roi_cap_lai(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.chay("cap-nhat-may", "ketoan-01")
        http_cu = open(f"{self.t}/secrets/may-ketoan-01-http").read()
        docker_truoc = self.docker_log()
        r = self.chay("thu-hoi-may", "ketoan-01", "--dong-y")
        self.assertIn("Đã thu hồi", r.stdout)
        self.assertNotIn("ketoan-01:", open(f"{self.t}/data/restic/.htpasswd").read())    # hết quyền vào kho HTTP
        self.assertIn("docker exec onebee-rest-server kill -HUP 1", self.docker_log()[len(docker_truoc):])   # … ngay, không chờ ≤30 giây
        self.assertFalse(os.path.exists(f"{self.t}/data/may-da-cap/ketoan-01"))            # động cơ quy trình ngừng nhận báo cáo
        self.assertFalse(os.path.exists(f"{self.t}/data/tinh-trang-may/ketoan-01.json"))
        self.assertFalse(self.da_ghim("ketoan-01"))
        self.assertIn("khoa go may ketoan-01", open(f"{self.t}/out/ai-rag.log").read())
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-khoa"))
        self.assertTrue(os.path.exists(f"{self.t}/secrets/may-ketoan-01-repo"))            # giữ mật khẩu kho để khôi phục dữ liệu
        # không "hồi sinh": mọi lệnh dùng danh sách chung đều bỏ qua; in cấu hình thiếu bí mật thì dừng, không tự sinh mới
        self.assertEqual(self.chay("cap-nhat-may", "ketoan-01", kiem=False).returncode, 1)
        self.assertEqual(self.chay("cap-nhat-may", "--tat-ca", kiem=False).returncode, 1)
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-http"))
        self.assertTrue(os.path.exists(f"{self.t}/secrets/thu-hoi/ketoan-01"))
        # chạy lại thu hồi: an toàn
        self.chay("thu-hoi-may", "ketoan-01", "--dong-y")
        # cấp lại: mật khẩu kho HTTP, tài khoản Trợ lý AI VÀ mật khẩu kho sao lưu (khóa ký + bằng chứng danh tính) đều mới
        repo_cu = self.mat_khau("ketoan-01")
        os.makedirs(f"{self.t}/data/restic/ketoan-01")
        open(f"{self.t}/data/restic/ketoan-01/config", "w").write("kho cu")
        self.chay("them-may", "ketoan-01")
        self.assertNotEqual(open(f"{self.t}/secrets/may-ketoan-01-http").read(), http_cu)
        self.assertNotEqual(self.mat_khau("ketoan-01"), repo_cu)
        self.assertFalse(os.path.exists(f"{self.t}/secrets/thu-hoi/ketoan-01"))
        cu = [f for f in os.listdir(f"{self.t}/secrets") if f.startswith("cu-ketoan-01-repo-")]
        self.assertEqual(len(cu), 1)                                                  # mật khẩu kho cũ cất lại để mở dữ liệu cũ
        self.assertEqual(open(f"{self.t}/secrets/{cu[0]}").read().strip(), repo_cu)
        self.assertFalse(os.path.exists(f"{self.t}/data/restic/ketoan-01"))            # kho mới bắt đầu trống, kho cũ cất sang tên khác
        self.assertTrue(any(d.startswith("ketoan-01.cu-") for d in os.listdir(f"{self.t}/data/restic")))
        self.assertTrue(os.path.exists(f"{self.t}/data/may-da-cap/ketoan-01"))
        # MÁY CŨ (bị mất cắp) vẫn biết mật khẩu kho cũ, vẫn có khóa chung và khóa quản trị: không còn chứng minh được là máy ketoan-01
        self.sim["10.1.1.5"] = {"hostkey": self.khoa_host("cu"), "password": repo_cu}
        self.dat_sim()
        self.bao_cao("ketoan-01", "10.1.1.5", mat_khau=repo_cu)       # báo cáo ký bằng mật khẩu cũ → sai chữ ký, không được chọn IP
        so_lan_truoc = len(self.ansible_goi())
        r = self.chay("cap-nhat-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.da_ghim("ketoan-01"))
        self.assertEqual(len(self.ansible_goi()), so_lan_truoc)

    def test_dong_bo_may_day_dung_cau_hinh_chi_toi_may_da_chung_minh(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.cap_may("kho-02", "10.1.1.6")
        self.sim["10.1.1.6"]["password"] = "mat-khau-sai"      # kho-02 là máy giả
        self.dat_sim()
        r = self.chay("dong-bo-may", "--tat-ca", kiem=False)
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1, r.stderr)
        d = f"{self.t}/out/{goi[0]}"
        inv = open(f"{d}/inventory").read()
        self.assertIn("ketoan-01 ansible_host=10.1.1.5", inv)
        self.assertNotIn("kho-02", inv)
        env_dich = open(f"{d}/cau-hinh/ketoan-01.env").read()
        for dong in ("MAY_TRAM=ketoan-01", "BOX_IP=192.168.1.10", f"RESTIC_PASSWORD={self.mat_khau('ketoan-01')}",
                     "HOI_URL=https://box.kiem-thu.onebee.internal",
                     f"HOI_API_KEY={open(f'{self.t}/secrets/may-ketoan-01-khoa').read()}"):
            self.assertIn(dong, env_dich)
        self.assertNotIn("kho-02", env_dich)
        # mọi file/thư mục tạm (chứa mật khẩu, inventory) đã được xóa
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])

    def test_dong_bo_may_khong_co_khoa_may_van_day_cau_hinh_cho_khoa_rieng(self):
        """Khóa theo máy chỉ là chuyển tiếp: thiếu nó thì vẫn đẩy cấu hình (địa chỉ /ai/), chỉ không có dòng HOI_API_KEY."""
        self.cap_may("ketoan-01", "10.1.1.5")
        os.remove(f"{self.t}/secrets/may-ketoan-01-khoa")
        self.chay("dong-bo-may", "ketoan-01")
        self.assertEqual(len(self.ansible_goi()), 1)
        d = f"{self.t}/out/{self.ansible_goi()[0]}/cau-hinh/ketoan-01.env"
        env_dich = open(d).read()
        self.assertIn("HOI_URL=https://box.kiem-thu.onebee.internal", env_dich)
        self.assertNotIn("HOI_API_KEY", env_dich)
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-khoa"))   # không tự cấp khóa mới

    def test_dong_bo_ten_may_dung_va_idempotent(self):
        self.cap_may("a", "10.1.1.5")
        self.cap_may("b", "10.1.1.6")
        os.makedirs(f"{self.t}/data/may-da-cap", exist_ok=True)
        open(f"{self.t}/data/may-da-cap/mo-coi", "w").write("1")
        r = self.chay("dong-bo-ten-may")
        self.assertIn("đã đổi", r.stdout)                                  # gỡ file của máy không còn cấp
        self.assertEqual(sorted(os.listdir(f"{self.t}/data/may-da-cap")), ["a", "b"])
        self.assertEqual(self.chay("dong-bo-ten-may").stdout.strip(), "")  # lần 2 không đổi → Ansible changed=0
        mode = stat.S_IMODE(os.stat(f"{self.t}/data/may-da-cap/a").st_mode)
        self.assertEqual(mode, 0o640)

    def test_tat_ca_xu_ly_du_moi_may_ssh_khong_nuot_danh_sach(self):
        """Hồi quy: ssh không có -n đọc hết stdin của vòng lặp danh sách máy → --tat-ca chỉ làm máy đầu."""
        for i, ten in enumerate(("a1", "b2", "c3")):
            self.cap_may(ten, f"10.1.1.{10 + i}")
        self.chay("cap-nhat-may", "--tat-ca")
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1)
        inv = open(f"{self.t}/out/{goi[0]}/inventory").read()
        for ten in ("a1", "b2", "c3"):
            self.assertIn(f"{ten} ansible_host=", inv)
            self.assertTrue(self.da_ghim(ten))
        self.assertEqual(len(self.ssh_goi()), 3)

    def test_dong_bo_may_thieu_bi_mat_nao_cung_khong_day_file_thieu(self):
        """Hồi quy: die trong command substitution không dừng hàm → file cấu hình thiếu mật khẩu HTTP vẫn được đẩy đi."""
        self.cap_may("ketoan-01", "10.1.1.5")
        for thieu in ("may-ketoan-01-http", "tinh-trang-key"):
            bak = open(f"{self.t}/secrets/{thieu}").read()
            os.remove(f"{self.t}/secrets/{thieu}")
            r = self.chay("dong-bo-may", "ketoan-01", kiem=False)
            self.assertNotEqual(r.returncode, 0, thieu)
            self.assertEqual(self.ansible_goi(), [], thieu)
            open(f"{self.t}/secrets/{thieu}", "w").write(bak)
        os.remove(f"{self.t}/ssh/quan-tri.pub")
        self.assertNotEqual(self.chay("dong-bo-may", "ketoan-01", kiem=False).returncode, 0)
        self.assertEqual(self.ansible_goi(), [])

    def test_ten_gan_giong_khong_lam_song_lai_may_da_thu_hoi(self):
        """Hồi quy: dấu thu hồi từng là file may-<tên>-thu-hoi, trùng tên khóa hoi của máy "<tên>-thu" → máy đã thu hồi "sống lại"."""
        self.chay("them-may", "kho")
        self.chay("them-may", "kho-thu")
        self.chay("thu-hoi-may", "kho", "--dong-y")
        self.assertEqual(sorted(os.listdir(f"{self.t}/data/may-da-cap")), ["kho-thu"])
        self.chay("thu-hoi-may", "kho-thu", "--dong-y")
        self.chay("them-may", "kho-thu")
        self.assertEqual(sorted(os.listdir(f"{self.t}/data/may-da-cap")), ["kho-thu"])   # "kho" vẫn bị thu hồi

    def test_thoat_loi_van_don_file_tam_chua_bi_mat(self):
        """Hồi quy: trap RETURN không chạy khi die → inventory và thư mục cấu hình (mật khẩu) còn lại trong /tmp."""
        self.cap_may("ketoan-01", "10.1.1.5")
        self.bao_cao("ketoan-01", "10.1.1.5", ky=False)      # không máy nào vào được → die "Không có máy nào để làm"
        self.assertNotEqual(self.chay("dong-bo-may", "ketoan-01", kiem=False).returncode, 0)
        self.assertNotEqual(self.chay("cap-nhat-may", "ketoan-01", kiem=False).returncode, 0)
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])

    # ---- Lối thoát khi đăng nhập một lần hỏng: tat-sso-tam / bat-sso-lai ----
    def bo_cai_ghi_dau(self, rc=0):
        """Bộ cài giả: ghi lại dấu SSO lúc nó chạy (bộ cài thật dựng lại Caddyfile theo dấu này)."""
        bo_cai = f"{self.t}/bo-cai.sh"
        open(bo_cai, "w").write(f"#!/bin/sh\n[ -e {self.t}/secrets/sso-tam-tat ] && echo tat >> {self.t}/out/bo-cai.log"
                                f" || echo bat >> {self.t}/out/bo-cai.log\nexit {rc}\n")
        os.chmod(bo_cai, 0o755)
        open(f"{self.t}/lib/duong-dan-bo-cai", "w").write(bo_cai + "\n")

    def bo_cai_log(self):
        p = f"{self.t}/out/bo-cai.log"
        return open(p).read().split() if os.path.exists(p) else []

    def test_chuyen_du_lieu_nap_so_cu_cua_thu_muc_du_lieu_vao_csdl(self):
        os.makedirs(f"{self.t}/data/ho-tro")
        open(f"{self.t}/data/ho-tro/khao-sat.csv", "w").write("2026-10-09 16:00,4,5,5,4,5,mẫu\n")
        r = self.chay("chuyen-du-lieu")
        self.assertIn("khao_sat", r.stdout)                                                      # bảng tổng kết
        self.assertIn("docker exec -i onebee-postgres psql -U postgres -d onebee", self.docker_log())
        self.assertTrue(os.path.exists(f"{self.t}/data/ho-tro/khao-sat.csv.truoc-chuyen"))

    def test_bao_cao_tuan_chuyen_so_cu_truoc_roi_doc_tu_csdl(self):
        r = self.chay("bao-cao-tuan", "2026-10-12")
        log = self.docker_log().splitlines()
        nap = [i for i, d in enumerate(log) if d.startswith("docker exec -i onebee-postgres psql")]
        doc = [i for i, d in enumerate(log) if d.startswith("docker exec onebee-postgres psql") and "COPY (SELECT" in d]
        self.assertTrue(nap and doc, log)
        self.assertLess(max(nap), min(doc))                                                      # chuyển dữ liệu xong mới đọc
        self.assertNotIn("Số dòng mới nạp", r.stdout)                                            # bảng tổng kết không lẫn vào báo cáo
        self.assertIn("2026", r.stdout)

    def test_bao_cao_tuan_van_chay_khi_chuyen_du_lieu_loi_nhung_canh_bao(self):
        os.makedirs(f"{self.t}/data/ho-tro")
        open(f"{self.t}/data/ho-tro/xu-ly.csv", "w").write("261005-080000-11,2026-10-05 08:45,Sửa cấu hình,không-phải-số,\n")
        r = self.chay("bao-cao-tuan", "2026-10-12")
        self.assertIn("xu-ly.csv", r.stderr)
        self.assertIn("CẢNH BÁO", r.stderr)
        self.assertIn("onebee-box chuyen-du-lieu", r.stderr)

    def test_tat_sso_tam_ghi_dau_canh_bao_va_chay_bo_cai(self):
        self.bo_cai_ghi_dau()
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        r = self.chay("tat-sso-tam")
        dau = f"{self.t}/secrets/sso-tam-tat"
        self.assertTrue(os.path.exists(dau))
        self.assertEqual(stat.S_IMODE(os.stat(dau).st_mode), 0o600)
        self.assertEqual(self.bo_cai_log(), ["tat"])            # dấu ghi TRƯỚC khi bộ cài dựng lại Caddyfile
        ra = r.stdout + r.stderr
        self.assertIn("CẢNH BÁO", ra)
        self.assertIn("503", ra)                                 # nói rõ dữ liệu bị khóa, không mở toang
        self.assertIn("bat-sso-lai", ra)
        r = self.chay("bat-sso-lai")
        self.assertFalse(os.path.exists(dau))
        self.assertEqual(self.bo_cai_log(), ["tat", "bat"])
        self.assertIn("Đã bật lại", r.stdout)
        r = self.chay("bat-sso-lai")                             # đang bật sẵn: không chạy bộ cài nữa
        self.assertEqual(self.bo_cai_log(), ["tat", "bat"])
        self.assertIn("đang bật", r.stdout)

    def test_tat_sso_tam_khi_chua_bat_https_thi_tu_choi(self):
        self.bo_cai_ghi_dau()
        r = self.chay("tat-sso-tam", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("HTTPS", r.stderr)
        self.assertFalse(os.path.exists(f"{self.t}/secrets/sso-tam-tat"))
        self.assertEqual(self.bo_cai_log(), [])

    def test_tat_sso_tam_bo_cai_loi_thi_bao_loi_giu_dau(self):
        self.bo_cai_ghi_dau(rc=2)
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        r = self.chay("tat-sso-tam", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bộ cài", r.stderr.lower())
        self.assertTrue(os.path.exists(f"{self.t}/secrets/sso-tam-tat"))   # chạy lại bộ cài là áp dụng tiếp

    def test_tat_sso_tam_khong_chay_chong_voi_sao_luu(self):
        self.bo_cai_ghi_dau()
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        import fcntl
        with open(f"{self.t}/onebee-box.lock", "w") as khoa:                                    # sao lưu đêm đang giữ khóa
            fcntl.flock(khoa, fcntl.LOCK_EX)
            r = self.chay("tat-sso-tam", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Đang có lệnh", r.stderr)
        self.assertEqual(self.bo_cai_log(), [])
        self.assertFalse(os.path.exists(f"{self.t}/secrets/sso-tam-tat"))


    # ---- Phòng ban ----
    def phong_conf(self):
        p = f"{self.t}/etc/samba-phong-ban.conf"
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    def samba_db(self):
        p = f"{self.t}/out/samba-db"
        return dict(l.split(" ", 1) for l in open(p).read().splitlines()) if os.path.exists(p) else {}

    def test_them_phong_dung_nhom_thu_muc_samba_va_lan_hai_khong_doi(self):
        r = self.chay("them-phong", "ke-toan", "Phòng Kế toán", "gnucash", "libreoffice-calc", "gnucash")
        self.assertIn("Đã tạo phòng ke-toan", r.stdout)
        so = json.load(open(f"{self.t}/data/phong-ban-so/ke-toan.json", encoding="utf-8"))
        self.assertEqual(so, {"ma": "ke-toan", "ten": "Phòng Kế toán", "phan_mem": ["gnucash", "libreoffice-calc"]})   # bỏ gói trùng
        self.assertEqual(stat.S_IMODE(os.stat(f"{self.t}/data/phong-ban-so/ke-toan.json").st_mode), 0o644)
        ht = open(f"{self.t}/out/he-thong").read().split("\n")
        self.assertIn("group pb-ke-toan", ht)
        self.assertIn("passwd pb-ke-toan", ht)
        self.assertIn("useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --gid pb-ke-toan pb-ke-toan",
                      open(f"{self.t}/out/he-thong.log").read())
        d = f"{self.t}/data/phong-ban/ke-toan"
        self.assertEqual(stat.S_IMODE(os.stat(d).st_mode), 0o2770)
        mk = open(f"{self.t}/secrets/phong-ke-toan-samba").read()
        self.assertRegex(mk, r"^[A-Za-z0-9]{20}$")
        self.assertEqual(self.samba_db(), {"pb-ke-toan": mk})                      # mật khẩu Samba = bí mật của phòng (qua stdin)
        self.assertNotIn(mk, open(f"{self.t}/out/he-thong.log").read())            # không nằm trên dòng lệnh
        conf = self.phong_conf()
        khoi = conf[conf.index("[pb-ke-toan]"):]
        for dong in ("comment = Phòng Kế toán", f"path = {d}", "valid users = pb-ke-toan", "hosts allow = 127. 10. 172.16.0.0/12 192.168.",
                     "guest ok = no", "read only = no", "force group = pb-ke-toan", "create mask = 0660", "directory mask = 2770",
                     "access based share enum = yes", "include = /etc/onebee-box/samba-tu-xa.conf"):
            self.assertIn("\n   " + dong + "\n", khoi)
        self.assertIn("smbcontrol smbd reload-config", open(f"{self.t}/out/samba.log").read())
        # Bộ cài chạy lại: không đổi gì → không DA_DOI (Ansible changed=0), không nạp lại Samba
        os.remove(f"{self.t}/out/samba.log")
        self.assertEqual(self.chay("dong-bo-phong").stdout.strip(), "")
        self.assertFalse(os.path.exists(f"{self.t}/out/samba.log"))
        # Phòng thứ hai: thêm khối riêng, mật khẩu riêng; sửa phòng giữ mật khẩu cũ
        self.chay("them-phong", "kho", "Phòng Kho")
        self.assertIn("[pb-kho]", self.phong_conf())
        self.assertNotEqual(open(f"{self.t}/secrets/phong-kho-samba").read(), mk)
        r = self.chay("them-phong", "ke-toan", "Phòng Kế toán – Tài vụ", "gnucash")
        self.assertIn("Đã cập nhật phòng ke-toan", r.stdout)
        self.assertIn("comment = Phòng Kế toán – Tài vụ", self.phong_conf())
        self.assertEqual(open(f"{self.t}/secrets/phong-ke-toan-samba").read(), mk)
        # Tài khoản Samba mất (cài lại hệ điều hành): dong-bo-phong đặt lại bằng đúng mật khẩu cũ
        os.remove(f"{self.t}/out/samba-db")
        self.assertIn("DA_DOI", self.chay("dong-bo-phong").stdout)
        self.assertEqual(self.samba_db()["pb-ke-toan"], mk)

    def test_them_phong_tu_choi_ma_ten_goi_sai(self):
        for args in (("Ke-toan", "Kế toán"), ("k", "Kế toán"), ("ke_toan", "Kế toán"), ("ke-toan", ""),
                     ("ke-toan", 'Kế "toán"'), ("ke-toan", "Kế $(id)"), ("ke-toan", "Kế\ttoán"), ("ke-toan", "x" * 61),
                     ("ke-toan", "Kế toán", "GnuCash"), ("ke-toan", "Kế toán", "a;rm")):
            r = self.chay("them-phong", *args, kiem=False)
            self.assertNotEqual(r.returncode, 0, args)
        self.assertFalse(os.path.exists(f"{self.t}/data/phong-ban-so/ke-toan.json"))
        self.assertEqual(self.phong_conf(), "")

    def test_them_may_co_phong_in_5_dong_khong_phong_khong_in(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán", "gnucash", "homebank")
        kv = self.kv("kt-01")
        self.assertFalse(any(k.startswith(("PHONG_BAN", "SAMBA_PHONG")) for k in kv))     # không có phòng: như cũ
        r = self.chay("them-may", "kt-02", "ke-toan")
        dong = [l for l in r.stdout.splitlines() if "=" in l and not l.startswith("#")]
        phong = [l for l in dong if l.startswith(("PHONG_BAN", "SAMBA_PHONG"))]
        self.assertEqual(phong, ["PHONG_BAN=ke-toan", 'PHONG_BAN_TEN="Phòng Kế toán"', 'PHONG_BAN_PHAN_MEM="gnucash homebank"',
                                 "SAMBA_PHONG_USER=pb-ke-toan", "SAMBA_PHONG_PASS=" + open(f"{self.t}/secrets/phong-ke-toan-samba").read()])
        self.assertEqual(dong[-5:], phong)                                                  # cuối cấu hình, sau các dòng cũ
        self.assertEqual(open(f"{self.t}/data/phong-ban-so/may/kt-02").read(), "ke-toan\n")
        # Phòng không có trong sổ: không cấp gì
        r = self.chay("them-may", "kt-03", "khong-co", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-kt-03-repo"))
        # Thiếu mật khẩu phòng: không in cấu hình thiếu (dong-bo-may bỏ qua máy)
        os.rename(f"{self.t}/secrets/phong-ke-toan-samba", f"{self.t}/mk-phong")
        r = self.chay("dong-bo-may", "kt-02", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.ansible_goi(), [])

    def test_chuyen_phong_xoa_phong_danh_sach_va_thu_hoi(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán", "gnucash")
        self.chay("them-phong", "kho", "Phòng Kho")
        self.chay("them-may", "kt-01", "ke-toan")
        self.chay("them-may", "kho-01")
        self.assertNotEqual(self.chay("chuyen-phong", "chua-cap", "kho", kiem=False).returncode, 0)
        self.assertNotEqual(self.chay("chuyen-phong", "kho-01", "khong-co", kiem=False).returncode, 0)
        r = self.chay("chuyen-phong", "kho-01", "kho")
        self.assertIn("dong-bo-may kho-01", r.stdout)
        self.assertNotIn("LƯU Ý", r.stdout)                                                 # chưa thuộc phòng nào: không có mật khẩu cũ
        ds = self.chay("danh-sach-phong").stdout
        self.assertRegex(ds, r"ke-toan\s+Phòng Kế toán\s+gnucash\s+kt-01")
        self.assertRegex(ds, r"kho\s+Phòng Kho\s+-\s+kho-01")
        r = self.chay("xoa-phong", "kho", kiem=False)                                       # còn máy → từ chối
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("kho-01", r.stderr)
        self.chay("thu-hoi-may", "kho-01", "--dong-y")
        self.assertFalse(os.path.exists(f"{self.t}/data/phong-ban-so/may/kho-01"))           # thu hồi gỡ luôn tệp gán phòng
        open(f"{self.t}/data/phong-ban/kho/so-kho.ods", "w").write("du lieu")
        r = self.chay("xoa-phong", "kho")
        self.assertNotIn("[pb-kho]", self.phong_conf())
        self.assertIn("[pb-ke-toan]", self.phong_conf())
        giu = [d for d in os.listdir(f"{self.t}/data/phong-ban") if d.startswith(".da-xoa-kho-")]
        self.assertEqual(len(giu), 1)                                                       # dữ liệu giữ lại, chỉ đổi tên
        self.assertEqual(open(f"{self.t}/data/phong-ban/{giu[0]}/so-kho.ods").read(), "du lieu")
        self.assertNotIn("pb-kho", self.samba_db())                                         # mật khẩu Samba cũ hết hiệu lực
        self.assertFalse(os.path.exists(f"{self.t}/secrets/phong-kho-samba"))
        self.assertFalse(os.path.exists(f"{self.t}/data/phong-ban-so/kho.json"))
        # Chuyển máy sang phòng khác: máy vẫn biết mật khẩu phòng cũ → nhắc đổi
        self.chay("them-phong", "kd", "Phòng Kinh doanh")
        r = self.chay("chuyen-phong", "kt-01", "kd")
        self.assertIn("LƯU Ý: máy kt-01 vẫn biết mật khẩu thư mục phòng cũ ke-toan", r.stdout)
        self.assertIn("sudo onebee-box doi-mat-khau-phong ke-toan", r.stdout)
        self.assertNotIn("LƯU Ý", self.chay("chuyen-phong", "kt-01", "kd").stdout)          # cùng phòng: không nhắc

    def test_doi_mat_khau_phong_cat_tep_cu_dat_samba_va_day_xuong_may_cua_phong(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        self.chay("them-phong", "kho", "Phòng Kho")
        for ten, ip, phong in (("kt-01", "10.1.1.5", "ke-toan"), ("kt-02", "10.1.1.6", "ke-toan"), ("mat", "10.1.1.8", "ke-toan"),
                               ("le", "10.1.1.9", None)):
            self.cap_may(ten, ip)
            if phong:
                self.chay("chuyen-phong", ten, phong)
        # Thu hồi máy mất: nhắc đổi mật khẩu phòng (đọc phòng trước khi gỡ tệp gán phòng); máy không thuộc phòng thì không nhắc
        r = self.chay("thu-hoi-may", "mat", "--dong-y")
        self.assertIn("LƯU Ý: máy mat thuộc phòng ke-toan", r.stdout)
        self.assertIn("sudo onebee-box doi-mat-khau-phong ke-toan", r.stdout)
        self.assertNotIn("doi-mat-khau-phong", self.chay("thu-hoi-may", "le", "--dong-y").stdout)
        cu = open(f"{self.t}/secrets/phong-ke-toan-samba").read()
        mk_kho = open(f"{self.t}/secrets/phong-kho-samba").read()
        del self.sim["10.1.1.6"]                                                                # kt-02 đang tắt
        self.dat_sim()
        r = self.chay("doi-mat-khau-phong", "ke-toan")
        moi = open(f"{self.t}/secrets/phong-ke-toan-samba").read()
        self.assertRegex(moi, r"^[A-Za-z0-9]{20}$")
        self.assertNotEqual(moi, cu)
        cat = [f for f in os.listdir(f"{self.t}/secrets") if f.startswith("cu-phong-ke-toan-samba-")]
        self.assertEqual(len(cat), 1)
        self.assertRegex(cat[0], r"^cu-phong-ke-toan-samba-\d{8}-\d{6}$")
        self.assertEqual(open(f"{self.t}/secrets/{cat[0]}").read(), cu)                       # mật khẩu cũ cất lại
        self.assertEqual(self.samba_db()["pb-ke-toan"], moi)                                   # Samba nhận mật khẩu mới qua stdin
        self.assertEqual(self.samba_db()["pb-kho"], mk_kho)                                    # phòng khác không đổi
        self.assertIn("smbpasswd -s pb-ke-toan", open(f"{self.t}/out/he-thong.log").read())
        self.assertNotIn(moi, open(f"{self.t}/out/he-thong.log").read() + r.stdout + r.stderr)
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1, r.stdout + r.stderr)
        d = f"{self.t}/out/{goi[0]}"
        self.assertEqual(sorted(os.listdir(f"{d}/cau-hinh")), ["kt-01.env", "kt-02.env"])  # chỉ máy còn trong phòng (không máy đã thu hồi)
        self.assertIn(f"SAMBA_PHONG_PASS={moi}", open(f"{d}/cau-hinh/kt-01.env").read())
        self.assertIn("kt-01 ansible_host=10.1.1.5", open(f"{d}/inventory").read())
        self.assertIn("sudo onebee-box dong-bo-may kt-02", r.stderr)                          # máy tắt: nhắc đồng bộ sau
        self.assertNotIn("dong-bo-may kt-01", r.stderr)
        # Phòng không có máy: chỉ đổi mật khẩu
        r = self.chay("doi-mat-khau-phong", "kho")
        self.assertIn("không có máy để đồng bộ", r.stdout)
        self.assertNotEqual(open(f"{self.t}/secrets/phong-kho-samba").read(), mk_kho)
        self.assertEqual(len(self.ansible_goi()), 1)
        # Samba từ chối (tài khoản chưa có): giữ nguyên mật khẩu cũ, không cất thêm gì
        os.remove(f"{self.t}/out/samba-db")
        truoc = open(f"{self.t}/secrets/phong-kho-samba").read()
        r = self.chay("doi-mat-khau-phong", "kho", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(f"{self.t}/secrets/phong-kho-samba").read(), truoc)
        self.assertEqual(len([f for f in os.listdir(f"{self.t}/secrets") if f.startswith("cu-phong-kho-samba-")]), 1)
        self.assertNotEqual(self.chay("doi-mat-khau-phong", "khong-co", kiem=False).returncode, 0)

    # ---- Máy trạm xin vào ----
    def tao_yeu_cau(self, ten="kt-01", bit=3072, khoa_bam=None, id_=None, cn=None, **sua):
        """Ghi <id>.json như động cơ quy trình ghi sau bước 3 (mã đối chiếu đã tính); khóa + chứng chỉ thật của máy trạm."""
        id_ = id_ or os.urandom(16).hex()
        k = f"{self.t}/may-{id_}"
        subprocess.run(["openssl", "req", "-x509", "-newkey", f"rsa:{bit}", "-nodes", "-keyout", k + ".key", "-out", k + ".crt",
                        "-subj", f"/CN={cn or ten}", "-days", "2"], check=True, capture_output=True)
        pub = subprocess.run(["openssl", "x509", "-in", k + ".crt", "-noout", "-pubkey"], check=True, capture_output=True).stdout
        der = subprocess.run(["openssl", "pkey", "-pubin", "-outform", "DER"], input=pub, check=True, capture_output=True).stdout
        kb = khoa_bam or hashlib.sha256(der).hexdigest()
        vt = open(f"{self.t}/secrets/ca/root.sha256").read().strip()
        nb, nw = os.urandom(16).hex(), os.urandom(16).hex()
        h = lambda x: hashlib.sha256(x.encode()).hexdigest()
        ms = "%06d" % (int(h(f"onebee-xin-vao-v1|ma-so|{id_}|{kb}|{vt}|{nw}|{nb}")[:8], 16) % 1000000)
        yc = {"id": id_, "ten": ten, "phong_xin": "ke-toan", "hostname": ten + "-pc", "ip": "192.168.1.50", "cert": open(k + ".crt").read(),
              "khoa_bam": kb, "ca_van_tay": vt, "n_b": nb, "cam_ket": h(f"onebee-xin-vao-v1|cam-ket|{id_}|{kb}|{vt}|{nb}"),
              "n_w": nw, "ma_so": ms, "luc": int(time.time())}
        yc.update(sua)
        os.makedirs(f"{self.t}/data/xin-vao", exist_ok=True)
        json.dump(yc, open(f"{self.t}/data/xin-vao/{id_}.json", "w"))
        return id_, k, ms

    def duyet_nhu_web(self, id_, phong="ke-toan", noi_dung_id=None):
        json.dump({"id": noi_dung_id or id_, "phong": phong, "nguoi_duyet": "an", "luc": int(time.time())},
                  open(f"{self.t}/data/xin-vao/{id_}.duyet.json", "w"))

    def ket_qua(self, id_):
        return json.load(open(f"{self.t}/data/xin-vao/{id_}.ket-qua", encoding="utf-8"))

    def giai_ma(self, kq, k):
        """Như máy trạm: giải mã bằng khóa của máy, rồi kiểm chữ ký bằng CA gốc của Box (chỉ CA gốc, không tin chứng chỉ trong bản ký)."""
        open(f"{k}.cms", "wb").write(base64.b64decode(kq["cms"]))
        subprocess.run(["openssl", "cms", "-decrypt", "-binary", "-inform", "DER", "-inkey", k + ".key", "-recip", k + ".crt",
                        "-in", k + ".cms", "-out", k + ".da-ky"], check=True, capture_output=True)
        r = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER", "-CAfile", f"{self.t}/secrets/ca/root.crt",
                            "-purpose", "any", "-in", k + ".da-ky"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        # CA lạ (kẻ đứng giữa tự ký) không qua được bước kiểm này
        subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
                        "-keyout", k + ".la.key", "-out", k + ".la.crt", "-subj", "/CN=CA la", "-days", "2"], check=True, capture_output=True)
        la = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER", "-CAfile", k + ".la.crt", "-purpose", "any",
                             "-in", k + ".da-ky"], capture_output=True)
        self.assertNotEqual(la.returncode, 0)
        return dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)

    def test_xin_vao_duyet_dong_lenh_dau_cuoi_bang_openssl_that(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán", "gnucash")
        id_, k, ms = self.tao_yeu_cau("kt-01")
        bang = self.chay("xin-vao").stdout
        self.assertIn(id_, bang)
        self.assertIn(ms, bang)
        self.assertIn("chờ duyệt", bang)
        r = self.chay("duyet-may", id_, "ke-toan")
        self.assertIn(f"Mã đối chiếu: {ms}", r.stdout)
        self.assertIn("Đã cấp máy kt-01 (phòng ke-toan)", r.stdout)
        dy = json.load(open(f"{self.t}/data/xin-vao/{id_}.duyet.json", encoding="utf-8"))
        self.assertEqual((dy["id"], dy["phong"], dy["nguoi_duyet"]), (id_, "ke-toan", "quản trị (dòng lệnh)"))
        kq = self.ket_qua(id_)
        self.assertEqual(kq["trang_thai"], "DA_CAP")
        self.assertRegex(kq["cms"], r"^[A-Za-z0-9+/=]+$")                                     # base64 một dòng
        self.assertEqual(stat.S_IMODE(os.stat(f"{self.t}/data/xin-vao/{id_}.ket-qua").st_mode), 0o640)
        env_may = self.giai_ma(kq, k)
        self.assertEqual(env_may["MAY_TRAM"], "kt-01")
        self.assertEqual(env_may["BOX_CA_VAN_TAY"], open(f"{self.t}/secrets/ca/root.sha256").read().strip())
        self.assertEqual(env_may["PHONG_BAN"], "ke-toan")
        self.assertEqual(env_may["SAMBA_PHONG_USER"], "pb-ke-toan")
        self.assertEqual(env_may["SAMBA_PHONG_PASS"], open(f"{self.t}/secrets/phong-ke-toan-samba").read())
        self.assertEqual(env_may["RESTIC_PASSWORD"], self.mat_khau("kt-01"))
        yc = json.load(open(f"{self.t}/data/xin-vao/{id_}.json"))
        self.assertEqual((env_may["XIN_VAO_ID"], env_may["XIN_VAO_N_W"]), (id_, yc["n_w"]))   # gắn với đúng lượt xin vào này
        canh_bao = open(f"{self.t}/out/canh-bao.log").read()
        self.assertIn("INFO|Máy trạm mới vào Box|Đã cấp máy kt-01 vào phòng ke-toan, người duyệt quản trị (dòng lệnh), IP 192.168.1.50", canh_bao)
        nk = open(f"{self.t}/out/xin-vao-da-cap.log").read().split()
        self.assertEqual(nk[1:], ["kt-01", id_])
        self.assertEqual(stat.S_IMODE(os.stat(f"{self.t}/out/xin-vao-da-cap.log").st_mode), 0o600)
        self.assertTrue(os.path.exists(f"{self.t}/data/may-da-cap/kt-01"))                    # cấp như them-may
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])                                     # cấu hình rõ không còn trên đĩa
        self.assertNotIn(env_may["RESTIC_PASSWORD"], r.stdout + r.stderr)
        # Đã quyết rồi: không duyệt / từ chối lại được; xử lý lại không cấp lần hai
        self.assertNotEqual(self.chay("duyet-may", id_, "ke-toan", kiem=False).returncode, 0)
        self.assertNotEqual(self.chay("tu-choi-may", id_, kiem=False).returncode, 0)
        truoc = open(f"{self.t}/data/xin-vao/{id_}.ket-qua").read()
        self.chay("xu-ly-xin-vao")
        self.assertEqual(open(f"{self.t}/data/xin-vao/{id_}.ket-qua").read(), truoc)

    def test_duyet_may_tren_cua_so_dong_lenh_phai_go_dung_ma(self):
        import pty
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        id_, k, ms = self.tao_yeu_cau("kt-01")
        sai = "%06d" % ((int(ms) + 1) % 1000000)
        chu, to = pty.openpty()
        os.write(chu, (sai + "\n").encode())
        r = subprocess.run(["bash", self.cmd, "duyet-may", id_, "ke-toan"], env=self.env, stdin=to, capture_output=True, text=True, timeout=60)
        os.close(to)
        os.close(chu)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Mã không khớp", r.stderr)
        self.assertFalse(os.path.exists(f"{self.t}/data/xin-vao/{id_}.duyet.json"))
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-kt-01-repo"))

    def test_xin_vao_tu_choi_yeu_cau_xau(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        self.chay("them-may", "da-co")
        ca = {}
        id_, _, _ = self.tao_yeu_cau("rsa-2048", bit=2048);              ca[id_] = "RSA từ 3072 bit"
        # Subject giả chuỗi độ dài khóa: độ dài phải đọc từ khóa công khai, không từ văn bản của cả chứng chỉ
        id_, _, _ = self.tao_yeu_cau("rsa-gia", bit=2048, cn="Public-Key: (4096 bit) Public Key Algorithm: rsaEncryption")
        ca[id_] = "RSA từ 3072 bit"
        # khoa_bam lệch chứng chỉ, dù cam kết + mã số vẫn tính khớp với khoa_bam đó (kẻ đứng giữa tráo chứng chỉ)
        id_, _, _ = self.tao_yeu_cau("lech", khoa_bam="ab" * 32);        ca[id_] = "Khóa băm không khớp chứng chỉ"
        id_, _, _ = self.tao_yeu_cau("cam-ket", cam_ket="00" * 32);      ca[id_] = "Cam kết không khớp"
        id_, _, _ = self.tao_yeu_cau("da-co");                           ca[id_] = "Tên máy đã cấp — thu hồi trước"
        id_, _, _ = self.tao_yeu_cau("chua-mo", ma_so=None);             ca[id_] = "Chưa có mã đối chiếu"
        id_, _, _ = self.tao_yeu_cau("ca-khac", ca_van_tay="cd" * 32);   ca[id_] = "Vân tay CA"
        id_, _, _ = self.tao_yeu_cau("Ten-Hoa");                         ca[id_] = "Tên máy không hợp lệ"
        id_, _, _ = self.tao_yeu_cau("id-lech");                         ca[id_] = "Quyết định duyệt không khớp"
        for i in ca:
            self.duyet_nhu_web(i, noi_dung_id=("0" * 32 if ca[i].startswith("Quyết định") else None))
        # Phòng không có trong sổ
        id_, _, _ = self.tao_yeu_cau("sai-phong")
        self.duyet_nhu_web(id_, phong="khong-co")
        ca[id_] = "Phòng ban không có trong sổ"
        # Liên kết mềm tới tệp bí mật: không đọc theo
        id_ = os.urandom(16).hex()
        os.symlink(f"{self.t}/secrets/tinh-trang-key", f"{self.t}/data/xin-vao/{id_}.json")
        self.duyet_nhu_web(id_)
        ca[id_] = "Không có yêu cầu này"
        # Tên tệp không phải id 32 hex: bỏ qua, không ghi gì
        open(f"{self.t}/data/xin-vao/XYZ.duyet.json", "w").write("{}")
        r = self.chay("xu-ly-xin-vao")
        for i, ly_do in ca.items():
            kq = self.ket_qua(i)
            self.assertEqual(kq["trang_thai"], "LOI", i)
            self.assertIn(ly_do, kq["loi"], i)
            self.assertNotIn(self.t, kq["loi"])                                           # không lộ đường dẫn cho máy chưa xác thực
        self.assertNotIn("khoa-chung", json.dumps(self.ket_qua(id_)))                       # không đọc theo liên kết mềm
        self.assertFalse(os.path.exists(f"{self.t}/data/xin-vao/XYZ.ket-qua"))
        for ten in ("rsa-2048", "rsa-gia", "lech", "cam-ket", "chua-mo", "ca-khac", "sai-phong"):
            self.assertFalse(os.path.exists(f"{self.t}/secrets/may-{ten}-repo"), ten)      # không cấp máy nào
        self.assertIn("KHÔNG cấp", r.stderr)
        self.assertNotEqual(self.chay("duyet-may", "khong-phai-hex", "ke-toan", kiem=False).returncode, 0)
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])

    def test_xin_vao_gioi_han_10_may_24_gio_va_canh_bao_loi_khong_hong_viec_cap(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        bay_gio = int(time.time())
        nk = f"{self.t}/out/xin-vao-da-cap.log"
        open(nk, "w").write("".join(f"{bay_gio - 3600} cu-{i} {'a' * 32}\n" for i in range(9))
                            + "".join(f"{bay_gio - 90000} rat-cu-{i} {'b' * 32}\n" for i in range(5)))  # quá 24 giờ: không tính
        self.env["ONEBEE_CANH_BAO_RC"] = "1"                                                      # Telegram / động cơ quy trình hỏng
        id1, k1, _ = self.tao_yeu_cau("thu-10")
        self.duyet_nhu_web(id1)
        r = self.chay("xu-ly-xin-vao")
        self.assertEqual(self.ket_qua(id1)["trang_thai"], "DA_CAP")                              # máy thứ 10: vẫn cấp, cảnh báo lỗi không hỏng việc cấp
        self.assertIn("Chưa gửi được cảnh báo cấp máy thu-10", r.stderr)
        self.assertEqual(len(open(nk).read().splitlines()), 10)                                  # bỏ dòng quá 24 giờ
        id2, _, _ = self.tao_yeu_cau("thu-11")
        self.duyet_nhu_web(id2)
        self.chay("xu-ly-xin-vao")
        kq = self.ket_qua(id2)
        self.assertEqual(kq, {"trang_thai": "LOI", "loi": "Đã cấp quá 10 máy trong 24 giờ — duyệt tiếp bằng them-may trên Box"})
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-thu-11-repo"))

    def test_tu_choi_may_va_bang_loc_ky_tu_dieu_khien(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        id_, _, _ = self.tao_yeu_cau("kt-01", hostname="may\x1b]0;gia\x07\x1b[2J")
        bang = self.chay("xin-vao").stdout
        self.assertNotIn("\x1b", bang)                                                         # không chèn mã điều khiển vào cửa sổ quản trị
        self.chay("tu-choi-may", id_, "Không", "rõ\x1b[2J", "máy")
        tc = json.load(open(f"{self.t}/data/xin-vao/{id_}.tu-choi.json", encoding="utf-8"))
        self.assertEqual((tc["id"], tc["nguoi_duyet"], tc["ly_do"]), (id_, "quản trị (dòng lệnh)", "Không rõ[2J máy"))
        self.assertIn("từ chối", self.chay("xin-vao").stdout)
        self.chay("xu-ly-xin-vao")
        self.assertFalse(os.path.exists(f"{self.t}/data/xin-vao/{id_}.ket-qua"))              # từ chối: không cấp, không ghi kết quả
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-kt-01-repo"))

    def test_xu_ly_xin_vao_don_tep_qua_24_gio(self):
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        cu, _, _ = self.tao_yeu_cau("cu-01")
        moi, _, _ = self.tao_yeu_cau("moi-01")
        d = f"{self.t}/data/xin-vao"
        open(f"{d}/{cu}.tu-choi.json", "w").write("{}")
        open(f"{d}/{cu}.ket-qua.tam", "w").write("")
        os.symlink("/etc/passwd", f"{d}/{cu}.lien-ket")
        open(f"{d}/ghi-chu.txt", "w").write("khong phai yeu cau")
        xua = time.time() - 25 * 3600
        os.utime(f"{d}/{cu}.json", (xua, xua))
        r = self.chay("xu-ly-xin-vao")
        self.assertIn("Đã dọn 1 yêu cầu", r.stdout)
        self.assertEqual(sorted(os.listdir(d)), sorted([f"{moi}.json", "ghi-chu.txt"]))
        self.assertTrue(os.path.exists("/etc/passwd"))                                         # chỉ xóa liên kết, không theo

    # ---- Sao lưu theo phòng ----
    def test_sao_luu_tao_ban_chup_rieng_tung_phong(self):
        self.chuan_bi_sao_luu()
        self.docker_csdl_gia()
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        self.chay("them-phong", "kho", "Phòng Kho")
        self.chay("sao-luu", kiem=False)
        log = open(f"{self.t}/out/restic.log").read().splitlines()
        csdl = [d for d in log if d.startswith("restic backup") and "--tag csdl" in d][0]
        self.assertIn(f" {self.t}/data/phong-ban-so ", csdl + " ")                            # sổ phòng ban cùng bản chụp với bí mật
        for ma in ("ke-toan", "kho"):
            self.assertIn(f"restic backup --retry-lock 5m --tag onebee-box --tag phong-{ma} {self.t}/data/phong-ban/{ma}", log)
        chung = log.index(next(d for d in log if "--tag chung" in d))
        forget = log.index(next(d for d in log if d.startswith("restic forget --retry-lock 5m --tag onebee-box")))
        phong = [i for i, d in enumerate(log) if "--tag phong-" in d]
        self.assertTrue(chung < min(phong) and max(phong) < forget, log)

    def test_khoi_phuc_phong_lay_ban_moi_nhat_vao_thu_muc_rieng(self):
        self.chuan_bi_sao_luu()
        self.chay("them-phong", "ke-toan", "Phòng Kế toán")
        open(f"{self.t}/bin/restic", "w").write(r"""#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
open(os.environ["ONEBEE_OUT"] + "/restic.log", "a").write("restic " + " ".join(a) + "\n")
if a[0] == "snapshots":
    print(json.dumps([{"time": "2026-11-18T16:00:05.123456789Z"}] if "onebee-box,phong-ke-toan" in a else []))
elif a[0] == "restore":
    d = a[a.index("--target") + 1] + os.environ["ONEBEE_PHONG_GOC"] + "/ke-toan"
    os.makedirs(d + "/2026")
    open(d + "/2026/bao-cao.ods", "w").write("ban cu")
""")
        self.env["ONEBEE_PHONG_GOC"] = f"{self.t}/data/phong-ban"
        open(f"{self.t}/data/phong-ban/ke-toan/bao-cao-dang-dung.ods", "w").write("ban moi")
        r = self.chay("khoi-phuc-phong", "ke-toan")
        self.assertIn("restic restore latest --tag onebee-box,phong-ke-toan --target", open(f"{self.t}/out/restic.log").read())
        goc = f"{self.t}/data/phong-ban/ke-toan"
        kp = [d for d in os.listdir(goc) if d.startswith("khoi-phuc-")]
        self.assertEqual(len(kp), 1)
        self.assertRegex(kp[0], r"^khoi-phuc-\d{8}-\d{4}$")
        self.assertEqual(open(f"{goc}/{kp[0]}/2026/bao-cao.ods").read(), "ban cu")
        self.assertEqual(open(f"{goc}/bao-cao-dang-dung.ods").read(), "ban moi")              # không đụng tệp đang dùng
        self.assertIn(f"{goc}/{kp[0]}", r.stdout)
        self.assertIn(f"chgrp -R -h pb-ke-toan {goc}/{kp[0]}", open(f"{self.t}/out/chgrp.log").read())
        self.assertEqual([d for d in os.listdir(f"{self.t}/data/phong-ban") if d.startswith(".")], [])   # thư mục tạm đã dọn
        r = self.chay("khoi-phuc-phong", "khong-co", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.chay("them-phong", "kho", "Phòng Kho")
        r = self.chay("khoi-phuc-phong", "kho", kiem=False)                                     # chưa có bản nào của phòng
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Chưa có bản sao lưu nào của phòng kho", r.stderr)


if __name__ == "__main__":
    unittest.main()
