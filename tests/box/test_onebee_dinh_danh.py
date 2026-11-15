#!/usr/bin/env python3
"""Kiểm thử dịch vụ định danh (Authelia) của Box mà không cần Docker:
- cấu hình Authelia sinh từ mẫu không chứa bí mật dạng rõ (mọi bí mật đọc từ tệp trong thư mục bí mật qua biến *_FILE),
  luật truy cập theo nhóm (đánh giá như Authelia: luật đầu tiên khớp thắng), cookie đặt cho tên box.<mã>.onebee.internal;
- dịch vụ authelia trong compose không công bố cổng, không tự nâng quyền, chỉ nằm trong mạng nội bộ với Caddy;
- bộ cài không ghi đè tệp người dùng, sinh đủ bí mật;
- lệnh onebee-box them-nguoi / xoa-nguoi / danh-sach-nguoi / ma-xac-nhan chạy bằng bash với docker GIẢ.
Chạy: python3 -m unittest"""
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ROLES = os.path.join(ROOT, "box/ansible/roles")
TEMPLATES = os.path.join(ROLES, "box-stack/templates")
DINH_DANH = os.path.join(ROLES, "box-dinh-danh")
CAU_HINH = os.path.join(DINH_DANH, "templates/configuration.yml.j2")
NHOM = ["nhan_vien", "ky_thuat", "quan_ly"]
TEN = "box.anphu.onebee.internal"


def bien(**them):
    v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_sso_hieu_luc=True)
    v.update(them)
    return v


def moi_truong():
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # như Ansible
    env.filters["bool"] = bool
    env.filters["to_json"] = lambda x: json.dumps(x, ensure_ascii=False)
    env.filters["quote"] = shlex.quote
    return env


def cau_hinh(**them):
    return yaml.safe_load(moi_truong().from_string(open(CAU_HINH, encoding="utf-8").read()).render(**bien(**them)))


def compose(https=True):
    nd = moi_truong().from_string(open(os.path.join(TEMPLATES, "docker-compose.yml.j2"), encoding="utf-8").read())
    return yaml.safe_load(nd.render(**bien(onebee_https_hieu_luc=https)))


def chinh_sach(cfg, nhom, duong_dan, ten_mien=TEN):
    """Chính sách Authelia áp cho người thuộc các nhóm `nhom` khi mở `duong_dan`: luật đầu tiên khớp (tên miền, đường dẫn, nhóm) thắng."""
    for luat in cfg["access_control"]["rules"]:
        mien = luat["domain"] if isinstance(luat["domain"], list) else [luat["domain"]]
        if ten_mien not in mien:
            continue
        if "resources" in luat and not any(re.search(r, duong_dan) for r in luat["resources"]):
            continue
        if "subject" in luat:
            chu_the = [s if isinstance(s, str) else s[0] for s in luat["subject"]]
            if not any(s == f"group:{n}" for s in chu_the for n in nhom):
                continue
        return luat["policy"]
    return cfg["access_control"]["default_policy"]


def tim_chuoi(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from tim_chuoi(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from tim_chuoi(v)
    else:
        yield str(obj)


def khoa(obj, tien_to=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{tien_to}{k}"
            yield from khoa(v, f"{tien_to}{k}.")
    elif isinstance(obj, list):
        for v in obj:
            yield from khoa(v, tien_to)


class CauHinhAuthelia(unittest.TestCase):
    def test_khong_co_bi_mat_dang_ro_trong_cau_hinh(self):
        cfg = cau_hinh()
        ten_khoa = list(khoa(cfg))
        for cam in ("session.secret", "storage.encryption_key", "identity_validation.reset_password.jwt_secret",
                    "identity_validation.elevated_session.jwt_secret"):
            self.assertNotIn(cam, ten_khoa)
        def gia_tri(duong):
            o = cfg
            for p in duong.split("."):
                o = o[p] if isinstance(o, dict) else None
            return o
        for k in ten_khoa:   # khóa mang tên bí mật chỉ được là nhóm cấu hình (vd file.password.algorithm), không phải một giá trị
            if re.search(r"secret|password$|encryption_key|key$", k.split(".")[-1]):
                self.assertIsInstance(gia_tri(k), dict, k)
        for s in tim_chuoi(cfg):
            self.assertNotRegex(s, r"^[A-Za-z0-9]{32,}$", "chuỗi giống khóa bí mật: " + s)
            self.assertNotIn("$argon2", s)

    def test_bi_mat_doc_tu_tep_trong_thu_muc_bi_mat_qua_bien_file(self):
        for https in (False, True):
            dv = compose(https)["services"]["authelia"]
            env = dv["environment"]
            cap = {
                "AUTHELIA_SESSION_SECRET_FILE": "authelia-session-secret",
                "AUTHELIA_STORAGE_ENCRYPTION_KEY_FILE": "authelia-storage-key",
                "AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET_FILE": "authelia-jwt-secret",
            }
            for bien_env, tep in cap.items():
                trong = env[bien_env]
                self.assertIn(f"/etc/onebee-box/secrets/{tep}:{trong}:ro", dv["volumes"])
            self.assertFalse([k for k in env if k.startswith("AUTHELIA_") and not k.endswith("_FILE")], env)
            self.assertFalse([v for v in env.values() if re.fullmatch(r"[A-Za-z0-9]{32,}", str(v))])

    def test_luat_truy_cap_theo_nhom(self):
        cfg = cau_hinh()
        self.assertEqual(cfg["access_control"]["default_policy"], "deny")
        for duong_dan in ("/api/toi", "/files/a.txt", "/ai/api/chat"):
            self.assertEqual(chinh_sach(cfg, ["nhan_vien"], duong_dan), "one_factor", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["ky_thuat"], duong_dan), "two_factor", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["quan_ly"], duong_dan), "two_factor", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["nhan_vien", "quan_ly"], duong_dan), "two_factor", duong_dan)
            self.assertEqual(chinh_sach(cfg, [], duong_dan), "deny", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["la"], duong_dan), "deny", duong_dan)
        # Trang giám sát (cổng 3001, Caddy gắn tiền tố /giam-sat): chỉ kỹ thuật, hai lớp
        for duong_dan in ("/giam-sat/dashboard", "/giam-sat/api/badge/1/status", "/giam-sat/socket.io/?EIO=4"):
            self.assertEqual(chinh_sach(cfg, ["ky_thuat"], duong_dan), "two_factor", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["nhan_vien"], duong_dan), "deny", duong_dan)
            self.assertEqual(chinh_sach(cfg, ["quan_ly"], duong_dan), "deny", duong_dan)
        # Luật Authelia không phân biệt cổng: đường dẫn lạ (vd /api/... của Kuma khi chưa gắn tiền tố) không mở cho ai ngoài tuyến lõi
        self.assertEqual(chinh_sach(cfg, ["nhan_vien"], "/dashboard"), "deny")
        # Tên miền khác (IP, tên lạ) không có luật nào → từ chối
        self.assertEqual(chinh_sach(cfg, ["quan_ly"], "/api/toi", ten_mien="192.168.1.10"), "deny")

    def test_phien_dang_nhap_tren_ten_box_va_duong_dan_dangnhap(self):
        cfg = cau_hinh()
        self.assertEqual(cfg["server"]["address"], "tcp://:9091/dangnhap")
        cookie = cfg["session"]["cookies"]
        self.assertEqual(len(cookie), 1)
        self.assertEqual(cookie[0]["domain"], TEN)
        self.assertEqual(cookie[0]["authelia_url"], f"https://{TEN}/dangnhap")
        self.assertEqual(cookie[0]["default_redirection_url"], f"https://{TEN}/")
        for luat in cfg["access_control"]["rules"]:
            self.assertEqual(luat["domain"], TEN)

    def test_xac_thuc_chi_bang_cookie_phien_va_tep_nguoi_dung(self):
        cfg = cau_hinh()
        fa = cfg["server"]["endpoints"]["authz"]["forward-auth"]
        self.assertEqual(fa["implementation"], "ForwardAuth")
        self.assertEqual(fa["authn_strategies"], [{"name": "CookieSession"}])   # không nhận Authorization/Proxy-Authorization
        ab = cfg["authentication_backend"]
        self.assertEqual(ab["file"]["path"], "/data/users_database.yml")
        self.assertTrue(ab["file"]["watch"])                 # them-nguoi/xoa-nguoi có hiệu lực không cần khởi động lại (không mất phiên)
        self.assertEqual(ab["refresh_interval"], "always")   # người bị xóa mất quyền ngay ở lần gọi kế tiếp
        self.assertTrue(ab["password_reset"]["disable"])
        self.assertEqual(cfg["storage"]["local"]["path"], "/data/db.sqlite3")
        self.assertEqual(cfg["notifier"]["filesystem"]["filename"], "/data/thong-bao.txt")
        self.assertTrue(cfg["webauthn"]["disable"])

    def test_dich_vu_authelia_khong_cong_bo_cong_va_chi_o_mang_noi_bo(self):
        for https in (False, True):
            c = compose(https)
            dv = c["services"]["authelia"]
            self.assertNotIn("ports", dv)
            self.assertIn("no-new-privileges:true", dv["security_opt"])
            self.assertEqual(dv["cap_drop"], ["ALL"])
            self.assertEqual(dv["container_name"], "onebee-authelia")
            self.assertEqual(dv["networks"], ["sso"])
            self.assertTrue(c["networks"]["sso"]["internal"])
            self.assertIn("sso", c["services"]["portal"]["networks"])
            self.assertEqual(dv["image"], bien()["onebee_box_images"]["authelia"])
            self.assertEqual(dv["command"], ["authelia", "--config", "/config/configuration.yml"])
            self.assertIn("./authelia:/config:ro", dv["volumes"])
            self.assertIn("/srv/onebee/authelia:/data", dv["volumes"])
            self.assertIn("logging", dv)

    def test_image_ghim_dung_adr_va_co_giay_phep(self):
        img = bien()["onebee_box_images"]
        self.assertEqual(img["authelia"], "docker.io/authelia/authelia:4.39.28@sha256:"
                                          "bd97cff4fcbf715b5ff1f9ae286afbe6033afce385302520b0368122d43a6f54")
        self.assertEqual(img["python"], "docker.io/library/python:3.14.10-slim-trixie@sha256:"
                                        "9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f")
        self.assertEqual(bien()["onebee_box_nhom_nguoi_dung"], NHOM)
        lic = open(os.path.join(ROOT, "LICENSES.md"), encoding="utf-8").read()
        self.assertRegex(lic, r"\| Authelia[^|]*\| Apache-2\.0")
        self.assertRegex(lic, r"\| Python[^|]*\| (PSF-2\.0|Python-2\.0)")

    def test_vai_tro_chay_sau_box_stack_va_khong_ghi_de_tep_nguoi_dung(self):
        site = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/site.yml"), encoding="utf-8"))[0]["roles"]
        self.assertEqual(site.index("box-dinh-danh"), site.index("box-stack") + 1)
        tasks = yaml.safe_load(open(os.path.join(DINH_DANH, "tasks/main.yml"), encoding="utf-8"))
        tep = [t for t in tasks if "users_database.yml" in json.dumps(t)]
        self.assertTrue(tep)
        for t in tep:
            hd = t.get("ansible.builtin.shell") or t.get("ansible.builtin.copy") or t.get("ansible.builtin.file") or {}
            tham = t.get("args", {})
            if "ansible.builtin.copy" in t:
                self.assertFalse(hd.get("force", True), t["name"])
            if "ansible.builtin.shell" in t:
                self.assertEqual(tham.get("creates"), "{{ onebee_box_data }}/authelia/users_database.yml", t["name"])
                self.assertIn("umask 077", hd)
        # Ba bí mật sinh một lần trong thư mục bí mật; task đọc bí mật không in ra nhật ký Ansible
        noi_dung = open(os.path.join(DINH_DANH, "tasks/main.yml"), encoding="utf-8").read()
        for ten in ("authelia-session-secret", "authelia-storage-key", "authelia-jwt-secret"):
            self.assertIn(f"onebee_box_secrets ~ '/{ten}'", noi_dung, ten)
        for t in tasks:
            if "lookup('ansible.builtin.password'" in json.dumps(t, ensure_ascii=False):
                self.assertTrue(t.get("no_log"), t["name"])

    def test_sao_luu_va_khoi_phuc_co_du_lieu_dinh_danh(self):
        nd = open(os.path.join(TEMPLATES, "onebee-box-sao-luu.sh.j2"), encoding="utf-8").read()
        self.assertIn("local svcs=(ai-rag n8n uptime-kuma authelia)", nd)          # tạm dừng khi chụp CSDL (nhất quán)
        csdl = next(d for d in nd.splitlines() if '"${DATA}/ai-rag" "${DATA}/n8n"' in d and "${SECRETS}" in d)
        self.assertIn('"${DATA}/authelia"', csdl)                                         # cùng bản chụp có nhãn csdl
        xoa = next(d for d in nd.splitlines() if d.strip().startswith('rm -rf "${DATA}/ai-rag"'))
        self.assertIn('"${DATA}/authelia"', xoa)                                          # khôi phục: xóa bản của lần cài mới trước


# docker GIẢ: chỉ trả lời các lệnh onebee-box gọi tới dịch vụ định danh; ghi lại tham số (không in bí mật)
DOCKER_GIA = r'''#!/usr/bin/env bash
printf '%s\n' "$*" >>"${ONEBEE_OUT}/docker.log"
if [[ "$*" == "exec onebee-authelia authelia crypto hash generate argon2 --random --random.length 16 --random.charset alphanumeric" ]]; then
  [[ ! -e "${ONEBEE_OUT}/authelia-tat" ]] || { echo "Error: No such container: onebee-authelia" >&2; exit 1; }
  printf 'Random Password: MkTam%05dx9Zq7W\n' "${RANDOM}"   # 16 ký tự chữ-số như Authelia sinh
  echo 'Digest: $argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0$aGFzaGhhc2hoYXNoaGFzaGhhc2hoYXNoaGFzaA'
  exit 0
fi
[[ "$1" == exec ]] && exit 0
exit 0
'''

THONG_BAO = """Date: 2026-11-15 03:09:44.433254839 +0000 UTC m=+16.108476361
Recipient: {binh binh@anphu.onebee.internal}
Subject: Confirm your identity
A ONE-TIME CODE HAS BEEN GENERATED TO COMPLETE A REQUESTED ACTION

Hi binh,

The following one-time code should only be used in the prompt displayed in your browser.

----------------------------------------

K7PX2M9Q

----------------------------------------

If you did not initiate the process your credentials may have been compromised and you should:
"""


@unittest.skipUnless(shutil.which("bash"), "cần bash")
class LenhNguoiDung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.t = self.tmp.name
        for d in ("lib", "bin", "secrets", "ssh", "data/authelia", "box", "out", "log"):
            os.makedirs(os.path.join(t, d))
        v = bien(onebee_box_secrets=f"{t}/secrets", onebee_box_ssh_dir=f"{t}/ssh", onebee_box_data=f"{t}/data",
                 onebee_box_dir=f"{t}/box")
        env = moi_truong()
        lib = f"{t}/lib"

        def sua(txt):
            return (txt.replace("/usr/local/lib/onebee-box", lib).replace("/var/log/onebee-box", f"{t}/log")
                    .replace("/run/onebee-box.lock", f"{t}/onebee-box.lock")
                    .replace("[[ ${EUID} -eq 0 ]] ||", "[[ 1 -eq 1 ]] ||"))
        for dst, src in (("lib/common.sh", "onebee-box-common.sh.j2"), ("lib/sao-luu.sh", "onebee-box-sao-luu.sh.j2"),
                         ("lib/chan-doan.sh", "onebee-box-chan-doan.sh.j2"), ("bin/onebee-box", "onebee-box.sh.j2")):
            nd = env.from_string(open(os.path.join(TEMPLATES, src), encoding="utf-8").read()).render(**v)
            open(f"{t}/{dst}", "w", encoding="utf-8").write(sua(nd))
        shutil.copy(os.path.join(DINH_DANH, "files/onebee-nguoi-dung.py"), f"{lib}/onebee-nguoi-dung.py")
        open(f"{t}/bin/docker", "w").write(DOCKER_GIA)
        os.chmod(f"{t}/bin/docker", 0o755)
        # Tệp người dùng như bộ cài tạo lần đầu: một tài khoản hệ thống đã khóa (Authelia không chạy với danh sách rỗng)
        self.tep = f"{t}/data/authelia/users_database.yml"
        with open(self.tep, "w") as f:
            f.write('users:\n  _onebee:\n    disabled: true\n    displayname: "OneBee"\n    password: "$argon2id$v=19$m=65536,t=3,p=4$eA$eA"\n    groups: []\n')
        os.chmod(self.tep, 0o600)
        self.env = dict(os.environ, PATH=f"{t}/bin:{os.environ['PATH']}", ONEBEE_OUT=f"{t}/out")

    def chay(self, *args, kiem=True):
        r = subprocess.run(["bash", f"{self.t}/bin/onebee-box", *args], env=self.env, capture_output=True, text=True, timeout=60)
        if kiem and r.returncode != 0:
            self.fail(f"onebee-box {' '.join(args)} lỗi ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r

    def nguoi(self):
        return yaml.safe_load(open(self.tep))["users"]

    def mat_khau_in_ra(self, r):
        m = re.findall(r"Mật khẩu tạm[^:]*: (\S+)", r.stdout)
        self.assertEqual(len(m), 1, r.stdout)
        return m[0]

    def test_them_nguoi_ghi_tep_in_mat_khau_mot_lan(self):
        r = self.chay("them-nguoi", "an", "nhan_vien")
        mk = self.mat_khau_in_ra(r)
        self.assertEqual((r.stdout + r.stderr).count(mk), 1)
        u = self.nguoi()["an"]
        self.assertEqual(u["groups"], ["nhan_vien"])
        self.assertTrue(u["password"].startswith("$argon2id$"))
        self.assertEqual(u["email"], "an@anphu.onebee.internal")
        self.assertIn("_onebee", self.nguoi())                                   # tài khoản hệ thống giữ nguyên
        self.assertEqual(stat.S_IMODE(os.stat(self.tep).st_mode), 0o600)
        self.assertNotIn(mk, open(self.tep).read())                            # tệp chỉ có bản băm
        for goc, _, tep in os.walk(f"{self.t}/log"):                            # không có gì ghi vào /var/log/onebee-box
            for f in tep:
                self.assertNotIn(mk, open(os.path.join(goc, f), errors="replace").read())
        self.assertNotIn(mk, open(f"{self.t}/out/docker.log").read())          # mật khẩu không nằm trên dòng lệnh nào
        self.assertNotIn(mk, self.chay("in-khoa").stdout)

    def test_them_nguoi_kiem_ten_va_nhom(self):
        truoc = open(self.tep).read()
        for ten, nhom in (("An", "nhan_vien"), ("-an", "nhan_vien"), ("a" * 33, "nhan_vien"), ("an;rm", "nhan_vien"),
                          ("_onebee", "nhan_vien"), ("an", "admin"), ("an", ""), ("", "")):
            r = self.chay("them-nguoi", ten, nhom, kiem=False)
            self.assertNotEqual(r.returncode, 0, (ten, nhom))
            self.assertNotIn("Mật khẩu tạm", r.stdout)
        self.assertEqual(open(self.tep).read(), truoc)
        self.chay("them-nguoi", "binh", "quan_ly")
        r = self.chay("them-nguoi", "binh", "ky_thuat", kiem=False)             # đã có thì không đổi mật khẩu/nhóm
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.nguoi()["binh"]["groups"], ["quan_ly"])

    def test_dich_vu_dinh_danh_chua_chay_thi_bao_loi_khong_ghi_gi(self):
        open(f"{self.t}/out/authelia-tat", "w").close()
        truoc = open(self.tep).read()
        r = self.chay("them-nguoi", "an", "nhan_vien", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dịch vụ định danh", r.stderr)
        self.assertEqual(open(self.tep).read(), truoc)

    def test_danh_sach_va_xoa_nguoi(self):
        self.chay("them-nguoi", "an", "nhan_vien")
        self.chay("them-nguoi", "kythuat", "ky_thuat")
        ds = self.chay("danh-sach-nguoi").stdout
        self.assertRegex(ds, r"(?m)^an\s+nhan_vien")
        self.assertRegex(ds, r"(?m)^kythuat\s+ky_thuat")
        self.assertNotIn("_onebee", ds)
        self.assertNotIn("argon2", ds)
        self.chay("xoa-nguoi", "an")
        self.assertNotIn("an", self.nguoi())
        self.assertIn("kythuat", self.nguoi())
        # Xóa luôn ghi danh hai lớp (người mới trùng tên không nhận lại TOTP của người cũ)
        self.assertIn("exec onebee-authelia authelia storage user totp delete an --config /config/configuration.yml",
                      open(f"{self.t}/out/docker.log").read())
        self.assertNotEqual(self.chay("xoa-nguoi", "an", kiem=False).returncode, 0)        # không còn ai tên đó
        self.assertNotEqual(self.chay("xoa-nguoi", "_onebee", kiem=False).returncode, 0)   # tài khoản hệ thống không xóa được

    def test_ma_xac_nhan_in_ma_moi_nhat(self):
        r = self.chay("ma-xac-nhan", kiem=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Chưa có mã", r.stderr)
        open(f"{self.t}/data/authelia/thong-bao.txt", "w").write(THONG_BAO)
        r = self.chay("ma-xac-nhan")
        self.assertIn("K7PX2M9Q", r.stdout)
        self.assertIn("binh", r.stdout)
        self.assertIn("2026-11-15 03:09:44", r.stdout)


if __name__ == "__main__":
    unittest.main()
