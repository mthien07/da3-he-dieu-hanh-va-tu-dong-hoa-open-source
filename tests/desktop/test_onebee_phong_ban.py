#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử role phong-ban (gắn thư mục phòng từ OneBee Box, cài phần mềm phòng, gỡ khi máy không còn phòng).
Container kiểm thử không gắn được CIFS thật nên chỉ kiểm: các biểu thức Jinja (đọc cấu hình, kiểm hợp lệ), nội dung đơn vị systemd,
tệp mật khẩu (no_log, 0600), lối tắt, nhánh gỡ, thứ tự role. Gắn thật kiểm trên máy Mint thật. Chạy: python3 -m unittest"""
import base64
import os
import re
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES = os.path.join(HERE, "../../desktop/ansible/roles")
TASKS = os.path.join(ROLES, "phong-ban/tasks/main.yml")
DOC_CAU_HINH = os.path.join(ROLES, "backup-client/tasks/doc-cau-hinh.yml")
SITE = os.path.join(HERE, "../../desktop/ansible/site.yml")
DONG_BO = os.path.join(HERE, "../../box/ansible/roles/box-fleet/files/dong-bo-may-tram.yml")


def nap_yaml(duong):
    with open(duong, encoding="utf-8") as f:
        return yaml.safe_load(f)


def lam_phang(ds):
    """Duỗi các khối block/rescue thành danh sách phẳng các task."""
    kq = []
    for t in ds:
        kq.append(t)
        for khoa in ("block", "rescue", "always"):
            kq += lam_phang(t.get(khoa, []))
    return kq


def tim(ds, ten_chua):
    r = [t for t in ds if ten_chua in t.get("name", "")]
    assert len(r) == 1, (ten_chua, [t.get("name") for t in r])
    return r[0]


class PhongBan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goc = nap_yaml(TASKS)
        cls.ds = lam_phang(cls.goc)
        env = jinja2.Environment(keep_trailing_newline=True)   # như Ansible
        env.tests["match"] = lambda v, p: bool(re.match(p, str(v)))
        env.tests["search"] = lambda v, p: bool(re.search(p, str(v)))
        env.filters["b64decode"] = lambda v: base64.b64decode(v).decode("utf-8")
        env.filters["regex_findall"] = lambda v, p: re.findall(p, str(v))
        cls.env = env
        cls.doc = nap_yaml(DOC_CAU_HINH)

    # --- tiện ích dựng ngữ cảnh như Ansible ---
    def may_tram(self, env_text):
        """Chạy đúng biểu thức của backup-client/doc-cau-hinh để có onebee_may_tram."""
        sf = tim(self.doc, "Tách các dòng cấu hình")["ansible.builtin.set_fact"]["onebee_may_tram"]
        stat = type("S", (), {"stat": type("E", (), {"exists": True})()})()
        raw = {"content": base64.b64encode(env_text.encode("utf-8")).decode("ascii")}
        return yaml.safe_load(self.env.from_string(sf).render(onebee_backup_conf=stat, onebee_may_tram_raw=raw))

    def doc_phong(self, env_text, **them):
        ctx = {"onebee_may_tram": self.may_tram(env_text), **them}
        sf = tim(self.ds, "Đọc phòng ban từ cấu hình")["ansible.builtin.set_fact"]
        ctx.update({k: self.render(v, ctx) for k, v in sf.items()})
        sf2 = tim(self.ds, "Chuẩn hóa thông tin phòng")["ansible.builtin.set_fact"]
        ctx.update({k: self.render(v, ctx) for k, v in sf2.items()})
        return ctx

    def render(self, mau, ctx):
        kq = self.env.from_string(mau).render(**ctx).strip()
        return yaml.safe_load(kq) if kq in ("True", "False") or kq.startswith("[") else kq

    CO_BAN = ('MAY_TRAM=kt-01\nBOX_IP=192.168.1.10\nPHONG_BAN=ke-toan\nPHONG_BAN_TEN="Phòng Kế toán"\nPHONG_BAN_PHAN_MEM="gnucash libreoffice-calc"\n'
              "SAMBA_PHONG_USER=pb-ke-toan\nSAMBA_PHONG_PASS=Abc123Xyz456Qwe789ab\n")

    # --- đọc cấu hình & kiểm hợp lệ ---
    def test_doc_cau_hinh_phong_day_du(self):
        c = self.doc_phong(self.CO_BAN, onebee_kn_dia_chi_smb="192.168.1.10")
        self.assertEqual((c["onebee_pb_ma"], c["onebee_pb_ten"], c["onebee_pb_user"]), ("ke-toan", "Phòng Kế toán", "pb-ke-toan"))
        self.assertEqual(c["onebee_pb_goi"], ["gnucash", "libreoffice-calc"])
        self.assertEqual(c["onebee_pb_pass"], "Abc123Xyz456Qwe789ab")
        self.assertEqual(c["onebee_pb_dia_chi"], "192.168.1.10")
        for khoa in ("ma_dung", "mat_khau_dung", "dia_chi_dung", "ten_dung"):
            self.assertIs(c["onebee_pb_" + khoa], True, khoa)
        self.assertEqual(c["onebee_pb_goi_sai"], [])

    def test_dia_chi_lay_tu_box_ip_khi_khong_co_fact_cua_ket_noi_box(self):
        c = self.doc_phong(self.CO_BAN)
        self.assertEqual(c["onebee_pb_dia_chi"], "192.168.1.10")

    def test_dia_chi_ten_box_khi_di_cong_tac(self):
        c = self.doc_phong(self.CO_BAN, onebee_kn_dia_chi_smb="box.anphu.onebee.internal")
        self.assertEqual(c["onebee_pb_dia_chi"], "box.anphu.onebee.internal")
        self.assertIs(c["onebee_pb_dia_chi_dung"], True)

    def test_may_khong_co_phong_thi_ma_rong(self):
        c = self.doc_phong("MAY_TRAM=kt-01\nBOX_IP=192.168.1.10\n")
        self.assertEqual(c["onebee_pb_ma"], "")
        self.assertEqual(c["onebee_pb_goi"], [])

    def test_khong_co_cau_hinh_may_tram_van_khong_loi(self):
        c = self.doc_phong("")
        self.assertEqual(c["onebee_pb_ma"], "")

    def test_gia_tri_sai_bi_danh_dau_khong_dung(self):
        sai = self.CO_BAN.replace("PHONG_BAN=ke-toan", "PHONG_BAN=Ke Toan").replace("SAMBA_PHONG_PASS=Abc123Xyz456Qwe789ab", "SAMBA_PHONG_PASS=a,b\\n")
        c = self.doc_phong(sai, onebee_kn_dia_chi_smb="evil.example.com")
        self.assertIs(c["onebee_pb_ma_dung"], False)
        self.assertIs(c["onebee_pb_mat_khau_dung"], False)
        self.assertIs(c["onebee_pb_dia_chi_dung"], False)

    def test_ten_hien_thi_nguy_hiem_bi_loai(self):
        for ten in ('Phòng "A"', "Phòng {{ x }}", "Phòng 100%", "Phòng $HOME", "Phòng \\ A", "x" * 61, "Phòng\tA"):
            env_text = self.CO_BAN.replace('PHONG_BAN_TEN="Phòng Kế toán"', f'PHONG_BAN_TEN="{ten}"')
            self.assertIs(self.doc_phong(env_text)["onebee_pb_ten_dung"], False, ten)
        self.assertIs(self.doc_phong(self.CO_BAN.replace("Phòng Kế toán", "Phòng Tổ chức - Hành chính"))["onebee_pb_ten_dung"], True)

    def test_ten_goi_sai_duoc_liet_ke(self):
        env_text = self.CO_BAN.replace('"gnucash libreoffice-calc"', '"gnucash -oEvil Bad_Name a;rm x"')
        self.assertEqual(self.doc_phong(env_text)["onebee_pb_goi_sai"], ["-oEvil", "Bad_Name", "a;rm", "x"])

    def test_goi_sai_thi_dung_voi_ten_goi_sai_truoc_khi_cai(self):
        ds_khoi = tim(self.goc, "Gắn thư mục phòng ban")["block"]
        ten = [t["name"] for t in ds_khoi]
        kiem, cai = tim(ds_khoi, "Kiểm tên các gói"), tim(ds_khoi, "Cài cifs-utils")
        self.assertLess(ten.index(kiem["name"]), ten.index(cai["name"]))
        self.assertIn("onebee_pb_goi_sai", kiem["ansible.builtin.assert"]["that"])
        self.assertIn("onebee_pb_goi_sai | join", kiem["ansible.builtin.assert"]["fail_msg"])

    # --- nhánh có phòng ---
    def test_apt_cai_cifs_utils_va_phan_mem_phong(self):
        apt = tim(self.ds, "Cài cifs-utils")["ansible.builtin.apt"]
        self.assertEqual(apt["state"], "present")
        self.assertEqual(self.env.from_string(apt["name"]).render(onebee_pb_goi=["gnucash"]), "['cifs-utils', 'gnucash']")

    def test_tep_mat_khau_no_log_va_0600(self):
        t = tim(self.ds, "Ghi tài khoản Samba")
        cp = t["ansible.builtin.copy"]
        self.assertIs(t["no_log"], True)
        self.assertEqual((cp["dest"], cp["mode"], cp["owner"], cp["group"]), ("/etc/onebee/phong-ban.cred", "0600", "root", "root"))
        nd = self.env.from_string(cp["content"]).render(onebee_pb_ma="ke-toan", onebee_pb_pass="MatKhau123")
        self.assertEqual(nd, "username=pb-ke-toan\npassword=MatKhau123\n")

    def test_moi_task_cham_mat_khau_deu_no_log(self):
        for t in lam_phang(self.goc):
            if "onebee_pb_pass" in str(t.get("ansible.builtin.set_fact", "")) or "phong-ban.cred" in str(t.get("ansible.builtin.copy", "")):
                self.assertIs(t.get("no_log"), True, t["name"])
        self.assertIs(tim(self.ds, "Chuẩn hóa thông tin phòng")["no_log"], True)

    def don_vi(self, **ctx):
        loop = tim(self.ds, "Cài đơn vị gắn thư mục phòng")["ansible.builtin.copy"]
        return loop, {i["name"]: self.env.from_string(i["content"]).render(**ctx) for i in tim(self.ds, "Cài đơn vị gắn thư mục phòng")["loop"]}

    def test_don_vi_mount_dung_noi_dung(self):
        cp, dv = self.don_vi(onebee_pb_ma="ke-toan", onebee_pb_dia_chi="192.168.1.10")
        self.assertEqual(set(dv), {"mnt-phongban.mount", "mnt-phongban.automount"})   # tên đơn vị phải khớp Where=/mnt/phongban
        m = dv["mnt-phongban.mount"]
        self.assertIn("What=//192.168.1.10/pb-ke-toan\n", m)
        self.assertIn("Where=/mnt/phongban\n", m)
        self.assertIn("Type=cifs\n", m)
        self.assertIn("Options=credentials=/etc/onebee/phong-ban.cred,vers=3.1.1,seal,uid=0,gid=0,file_mode=0666,dir_mode=0777,"
                      "iocharset=utf8,_netdev,nofail\n", m)
        a = dv["mnt-phongban.automount"]
        self.assertIn("Where=/mnt/phongban\n", a)
        self.assertIn("TimeoutIdleSec=600\n", a)
        self.assertIn("[Install]", a)
        self.assertEqual((cp["dest"], cp["mode"]), ("/etc/systemd/system/{{ item.name }}", "0644"))

    def test_don_vi_dung_ten_box_khi_di_cong_tac(self):
        _, dv = self.don_vi(onebee_pb_ma="hc", onebee_pb_dia_chi="box.anphu.onebee.internal")
        self.assertIn("What=//box.anphu.onebee.internal/pb-hc\n", dv["mnt-phongban.mount"])

    def test_bat_automount_co_creates_va_chi_start_khi_co_systemd(self):
        bat = tim(self.ds, "Bật gắn thư mục phòng khi mở")
        self.assertEqual(bat["ansible.builtin.command"], "systemctl enable mnt-phongban.automount")
        self.assertEqual(bat["args"]["creates"], "/etc/systemd/system/remote-fs.target.wants/mnt-phongban.automount")
        chay = tim(self.ds, "Chạy ngay gắn thư mục phòng")
        self.assertEqual(chay["when"], "onebee_pb_systemd.stat.exists")
        self.assertEqual(chay["ansible.builtin.systemd_service"]["name"], "mnt-phongban.automount")
        self.assertEqual(tim(self.ds, "Kiểm tra máy đang chạy systemd (không phải")["ansible.builtin.stat"]["path"], "/run/systemd/system")

    def test_loi_tat_menu(self):
        t = tim(self.ds, "Lối tắt thư mục phòng")
        cp = t["ansible.builtin.copy"]
        self.assertEqual((cp["dest"], cp["mode"]), ("/usr/share/applications/onebee-thu-muc-phong.desktop", "0644"))
        nd = self.env.from_string(cp["content"]).render(onebee_pb_ten="Phòng Kế toán", onebee_pb_ten_dung=True, onebee_pb_ma="ke-toan")
        self.assertIn("Name=Thư mục phòng: Phòng Kế toán\n", nd)
        self.assertIn("Exec=nemo /mnt/phongban\n", nd)
        self.assertIn("X-OneBee=1\n", nd)
        # tên hiển thị không hợp lệ → dùng mã phòng
        nd2 = self.env.from_string(cp["content"]).render(onebee_pb_ten='bad"{{', onebee_pb_ten_dung=False, onebee_pb_ma="ke-toan")
        self.assertIn("Name=Thư mục phòng: ke-toan\n", nd2)

    def test_nhanh_co_phong_chi_chay_khi_moi_thu_hop_le(self):
        w = tim(self.goc, "Gắn thư mục phòng ban")["when"]
        self.assertEqual(sorted(w), ["onebee_pb_dia_chi_dung", "onebee_pb_ma_dung", "onebee_pb_mat_khau_dung"])

    # --- nhánh gỡ ---
    def test_nhanh_go_chay_khi_khong_co_phong_va_khong_go_phan_mem(self):
        go = tim(self.goc, "Gỡ thư mục phòng ban")
        self.assertEqual(go["when"], "onebee_pb_ma | length == 0")
        for t in lam_phang(go["block"]):
            apt = t.get("ansible.builtin.apt") or {}
            self.assertNotEqual(apt.get("state"), "absent", "không được gỡ phần mềm đã cài")
        tep_xoa = tim(go["block"], "Xóa đơn vị gắn")
        self.assertEqual(tep_xoa["ansible.builtin.file"]["state"], "absent")
        self.assertEqual(sorted(tep_xoa["loop"]), sorted([
            "/etc/systemd/system/mnt-phongban.automount", "/etc/systemd/system/mnt-phongban.mount",
            "/etc/onebee/phong-ban.cred", "/usr/share/applications/onebee-thu-muc-phong.desktop"]))

    def test_tat_truoc_roi_moi_xoa_va_khong_xoa_thu_muc_gan(self):
        go = tim(self.goc, "Gỡ thư mục phòng ban")["block"]
        ten = [t["name"] for t in go]
        self.assertLess(ten.index(tim(go, "Tắt gắn thư mục phòng")["name"]), ten.index(tim(go, "Xóa đơn vị gắn")["name"]))
        self.assertLess(ten.index(tim(go, "Bỏ bật gắn thư mục phòng")["name"]), ten.index(tim(go, "Xóa đơn vị gắn")["name"]))
        tat = tim(go, "Tắt gắn thư mục phòng")
        self.assertEqual(tat["ansible.builtin.command"], "systemctl stop {{ item.item }}")
        self.assertIs(tat["failed_when"], False)   # thư mục đang mở: chỉ báo, không làm hỏng cả lần đồng bộ
        self.assertIn("onebee_pb_systemd_go.stat.exists", tat["when"])
        self.assertEqual(tim(go, "Bỏ bật gắn thư mục phòng")["args"]["removes"], "/etc/systemd/system/remote-fs.target.wants/mnt-phongban.automount")
        # xóa nhầm thư mục /mnt/phongban đang gắn sẽ xóa dữ liệu thật trên Box
        for t in self.ds:
            f = t.get("ansible.builtin.file") or {}
            self.assertNotEqual(f.get("path"), "/mnt/phongban")
            self.assertNotIn("/mnt/phongban", t.get("loop", []) if isinstance(t.get("loop"), list) else [])

    # --- bố trí role ---
    def test_site_chay_phong_ban_sau_ket_noi_box(self):
        roles = nap_yaml(SITE)[0]["roles"]
        self.assertEqual(roles.count("phong-ban"), 1)
        self.assertGreater(roles.index("phong-ban"), roles.index("ket-noi-box"))
        self.assertGreater(roles.index("phong-ban"), roles.index("backup-client"))   # onebee_may_tram do backup-client đặt

    def test_dong_bo_may_tram_goi_phong_ban_sau_menu_va_truoc_bao_tinh_trang(self):
        ds = nap_yaml(DONG_BO)[0]["tasks"]
        ten_role = [t.get("ansible.builtin.include_role", {}).get("name") for t in ds]
        self.assertEqual(ten_role.count("phong-ban"), 1)
        i = ten_role.index("phong-ban")
        self.assertEqual(ds[i - 1]["ansible.builtin.include_role"]["tasks_from"], "muc-menu")
        self.assertEqual(ds[i + 1]["ansible.builtin.command"], "/usr/local/sbin/onebee-bao-tinh-trang")


if __name__ == "__main__":
    unittest.main()
