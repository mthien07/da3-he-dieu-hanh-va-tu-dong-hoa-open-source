#!/usr/bin/env python3
"""Kiểm thử các lệnh shell quản lý máy trạm của `onebee-box` (them-may, thu-hoi-may, cap-nhat-may, dong-bo-may, ghim-lai-may)
mà không cần Box thật: render các mẫu .j2, chạy bằng bash trong thư mục tạm, với `ssh`, `ansible-playbook`, Open WebUI GIẢ.
Dùng ssh-keygen và htpasswd thật (apt: openssh-client, apache2-utils) — thiếu thì bỏ qua. Chạy: python3 -m unittest

Kiểm các tính chất của rà soát bảo mật F2: máy chỉ được ghim khóa SSH / nhận cấu hình sau khi CHỨNG MINH biết mật khẩu kho sao lưu,
báo cáo chưa ký không đủ để Box đem khóa quản trị tới một địa chỉ lạ, máy đã thu hồi không được "hồi sinh", dong-bo-may không đẩy file thiếu.
"""
import base64
import hashlib
import json
import os
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

WEBUI_GIA = r'''#!/usr/bin/env python3
import os, sys
open(os.environ["ONEBEE_OUT"] + "/webui.log", "a").write(" ".join(sys.argv[1:]) + "\n")
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "xoay-khoa":
    print("sk-moi-" + sys.argv[2])
if cmd == "doi-mat-khau-quan-tri":
    open(os.environ["ONEBEE_OUT"] + "/mk-quan-tri-moi", "w").write(os.environ["ONEBEE_MAT_KHAU_MOI"])
if cmd in ("cap-khoa", "lay-khoa"):
    if cmd == "lay-khoa" and os.environ.get("ONEBEE_WEBUI_LAY_KHOA_LOI"):
        sys.exit("Open WebUI chưa chạy")
    if cmd == "cap-khoa":   # như onebee-webui.py thật: lưu mật khẩu tài khoản may-<tên> vào thư mục bí mật
        open(os.path.join(os.environ["ONEBEE_SECRETS"], "may-%s-webui" % sys.argv[2]), "w").write("mk\n")
    print("sk-khoa-" + sys.argv[2])
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
        for d in ("lib", "bin", "secrets", "ssh", "data/restic", "data/tinh-trang-may", "box", "out", "tmp"):
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
                    .replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||"))
        files = {"common.sh": "onebee-box-common.sh.j2", "sao-luu.sh": "onebee-box-sao-luu.sh.j2", "chan-doan.sh": "onebee-box-chan-doan.sh.j2"}
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
        for ten, nd in (("onebee-webui.py", WEBUI_GIA),):
            open(f"{lib}/{ten}", "w").write(nd)
        docker_gia = '#!/bin/sh\necho "docker $*" >> "$ONEBEE_OUT/docker.log"\n'
        for ten, nd in (("ssh", SSH_GIA), ("ansible-playbook", ANSIBLE_GIA), ("install", INSTALL_GIA), ("chown", "#!/bin/sh\nexit 0\n"), ("docker", docker_gia)):
            open(f"{t}/bin/{ten}", "w").write(nd)
        for f in os.listdir(f"{t}/bin") + [os.path.join("..", "lib", "onebee-webui.py")]:
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
        r = subprocess.run(["bash", self.cmd, *args], env=self.env, capture_output=True, text=True, timeout=120)
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
        for f in ("lib/common.sh", "lib/sao-luu.sh", "bin/onebee-box"):
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
        self.assertEqual(kv["HOI_API_KEY"], "sk-khoa-ketoan-01")
        self.assertTrue(os.path.exists(f"{self.t}/data/may-da-cap/ketoan-01"))      # động cơ quy trình sẽ nhận báo cáo của máy này
        self.assertIn("ketoan-01:", open(f"{self.t}/data/restic/.htpasswd").read())
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-hoi").read(), "sk-khoa-ketoan-01")  # lưu để in lại không cần gọi Open WebUI
        # in lại cấu hình (dong-bo-may) không gọi cap-khoa nữa, không tạo gì mới
        webui_truoc = open(f"{self.t}/out/webui.log").read()
        self.assertEqual(webui_truoc.strip().splitlines(), ["cap-khoa ketoan-01"])

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
        self.assertNotIn("PRIVATE KEY", r)

    def test_in_khoa_khong_in_khoa_rieng_cua_ca_nhung_co_van_tay(self):
        r = self.chay("in-khoa").stdout
        self.assertNotIn("PRIVATE KEY", r)
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
        self.assertTrue(kv["HOI_URL"].startswith("http://") and kv["TINH_TRANG_URL"].startswith("http://"))
        open(f"{self.t}/secrets/https-da-bat", "w").write("1\n")
        kv = self.kv()
        self.assertEqual(kv["BOX_HTTPS"], "1")
        self.assertTrue(kv["RESTIC_REPOSITORY"].startswith("rest:https://ketoan-01:"))
        self.assertEqual(kv["HOI_URL"], "https://192.168.1.10:3000")
        self.assertEqual(kv["TINH_TRANG_URL"], "https://box.anphu.onebee.internal/webhook/onebee-tinh-trang")

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
        self.assertEqual(kv["HOI_URL"], "http://192.168.1.10:3000")                       # hoi --dang-nhap cần địa chỉ
        log = f"{self.t}/out/webui.log"
        self.assertNotIn("cap-khoa", open(log).read() if os.path.exists(log) else "")      # không tạo tài khoản may-<tên>
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-hoi"))

    def test_go_khoa_hoi_may_chi_khi_da_tat_va_xoa_dung(self):
        self.kv("ketoan-01")
        r = self.chay("go-khoa-hoi-may", kiem=False)
        self.assertNotEqual(r.returncode, 0)                                                # còn bật khóa theo máy → từ chối
        self.thay_khoa_may("false")
        r = self.chay("go-khoa-hoi-may")
        self.assertIn("ketoan-01", r.stdout)
        self.assertIn("xoa-tai-khoan ketoan-01", open(f"{self.t}/out/webui.log").read())
        self.assertFalse(os.path.exists(f"{self.t}/secrets/may-ketoan-01-hoi"))
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
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-hoi").read(), "sk-moi-ketoan-01")
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-repo").read(), repo_cu)       # RESTIC_PASSWORD KHÔNG xoay
        self.assertIn("xoay-khoa ketoan-01", open(f"{self.t}/out/webui.log").read())
        goi = self.ansible_goi()
        self.assertEqual(len(goi), 1)
        self.assertIn("dong-bo-may-tram.yml", open(f"{self.t}/out/{goi[0]}/args").read())     # đã đẩy xuống máy
        self.assertIn("RESTIC_REPOSITORY", "".join(open(f"{self.t}/out/{goi[0]}/cau-hinh/{f}").read() for f in os.listdir(f"{self.t}/out/{goi[0]}/cau-hinh")))
        self.assertNotIn(open(f"{self.t}/secrets/may-ketoan-01-http").read(), r.stdout + r.stderr)   # không in mật khẩu ra màn hình

    def test_xoay_khoa_can_xac_nhan_va_dung_may(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        self.assertNotEqual(self.chay("xoay-khoa", "--may", "khong-co", "--dong-y", kiem=False).returncode, 0)
        self.assertNotEqual(self.chay("xoay-khoa", kiem=False).returncode, 0)
        r = subprocess.run([self.cmd, "xoay-khoa", "--may", "ketoan-01"], capture_output=True, text=True, env=self.env, input="khong\n")
        self.assertNotEqual(r.returncode, 0)                                                   # không gõ đúng câu xác nhận → hủy
        self.assertFalse(os.path.exists(f"{self.t}/out/webui.log") and "xoay-khoa" in open(f"{self.t}/out/webui.log").read())

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
        moi = open(f"{self.t}/out/mk-quan-tri-moi").read()
        self.assertEqual(open(f"{self.t}/secrets/webui-admin-password").read(), moi)           # đổi trong dịch vụ rồi mới ghi file
        self.assertRegex(moi, r"^[A-Za-z0-9]{24}$")
        soan = open(f"{self.t}/secrets/quy-trinh-soan-luong").read()
        self.assertNotEqual(soan, "soan-cu")
        self.assertTrue(open(f"{self.t}/secrets/quy-trinh-soan-hash").read().startswith("$2"))      # bcrypt
        for f in ("webui-secret-key", "bieu-mau-nhanvien", "bieu-mau-kythuat", "authelia-session-secret", "cau-noi-jwt-secret"):
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
                        ("restic", '#!/bin/sh\necho "restic $*" >> "$ONEBEE_OUT/restic.log"\n[ "$1" != snapshots ] || echo "[]"\n'),
                        ("curl", "#!/bin/sh\nexit 7\n")):
            open(f"{self.t}/bin/{ten}", "w").write(nd)
            os.chmod(f"{self.t}/bin/{ten}", 0o755)
        open(f"{self.t}/secrets/restic-box", "w").write("mk-kho-box")

    def test_sao_luu_ket_xuat_csdl_truoc_khi_tam_dung_va_dua_vao_ban_csdl(self):
        self.chuan_bi_sao_luu()
        self.docker_csdl_gia()
        self.chay("sao-luu", kiem=False)
        kx = f"{self.t}/data/postgres-ket-xuat"
        self.assertEqual(open(f"{kx}/onebee.dump").read(), "BAN-KET-XUAT")
        self.assertEqual(sorted(os.listdir(kx)), ["onebee.dump"])                              # không còn tệp tạm
        log = self.docker_log().splitlines()
        dump = [i for i, d in enumerate(log) if "exec onebee-postgres pg_dump -U postgres -d onebee -Fc" in d]
        pause = [i for i, d in enumerate(log) if d.endswith(" pause open-webui quy-trinh uptime-kuma authelia")]
        self.assertTrue(dump and pause, log)
        self.assertLess(dump[0], pause[0])                                                       # không exec được trong container đang dừng
        ban_csdl = [d for d in open(f"{self.t}/out/restic.log").read().splitlines() if d.startswith("restic backup") and "--tag csdl" in d][0]
        self.assertIn(f" {kx} ", ban_csdl + " ")
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
        """Chưa gắn ổ sao lưu thì sao lưu dừng — nhưng gia hạn CA trung gian phải chạy trước đó, kẻo hết hạn là HTTPS sập."""
        self.chay("gia-han-ca")
        self.lam_trung_gian_sap_het_han()
        cu = open(f"{self.t}/secrets/ca/inter.crt").read()
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
        self.assertIn("xoa-tai-khoan ketoan-01", open(f"{self.t}/out/webui.log").read())
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
                     "HOI_API_KEY=sk-khoa-ketoan-01"):
            self.assertIn(dong, env_dich)
        self.assertNotIn("kho-02", env_dich)
        # mọi file/thư mục tạm (chứa mật khẩu, inventory) đã được xóa
        self.assertEqual(os.listdir(f"{self.t}/tmp"), [])

    def test_dong_bo_may_thieu_khoa_hoi_thi_bo_qua_may_do_khong_day_file_thieu(self):
        self.cap_may("ketoan-01", "10.1.1.5")
        os.remove(f"{self.t}/secrets/may-ketoan-01-hoi")       # máy cấp từ bản cũ chưa lưu khóa
        self.env["ONEBEE_WEBUI_LAY_KHOA_LOI"] = "1"            # và Open WebUI đang trục trặc
        r = self.chay("dong-bo-may", "ketoan-01", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.ansible_goi(), [])               # không đẩy cấu hình thiếu dòng hoi (sẽ làm hỏng hoi trên máy)
        # Open WebUI chạy lại → lấy lại khóa đã cấp (không tạo mới) và đẩy bình thường
        del self.env["ONEBEE_WEBUI_LAY_KHOA_LOI"]
        self.chay("dong-bo-may", "ketoan-01")
        self.assertEqual(len(self.ansible_goi()), 1)
        self.assertEqual(open(f"{self.t}/secrets/may-ketoan-01-hoi").read(), "sk-khoa-ketoan-01")
        self.assertNotIn("cap-khoa ketoan-01", open(f"{self.t}/out/webui.log").read().splitlines()[1:])

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


if __name__ == "__main__":
    unittest.main()
