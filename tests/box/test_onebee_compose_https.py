#!/usr/bin/env python3
"""Kiểm thử docker-compose.yml.j2 ở hai chế độ HTTP / HTTPS (không cần Docker): chỉ Caddy công bố cổng khi HTTPS,
cấu hình ứng dụng đổi đúng (n8n sau proxy, cookie Secure, CORS), chế độ HTTP giữ nguyên cổng như trước và vẫn giới hạn CORS.
Chạy: python3 -m unittest"""
import os
import re
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
TEMPLATE = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/docker-compose.yml.j2")
TASKS_MAIN = os.path.join(ROOT, "box/ansible/roles/box-stack/tasks/main.yml")


def ve(https, kuma="0.0.0.0", cors_them=None):
    v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=https, onebee_kuma_dia_chi=kuma)
    if cors_them is not None:
        v["onebee_box_cors_them"] = cors_them
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # như Ansible
    env.filters["bool"] = bool
    return yaml.safe_load(env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v))["services"]


def cors_hop_le(cors_them):
    """Chạy các điều kiện `that` của task kiểm onebee_box_cors_them trong tasks/main.yml (test `match` của Ansible = re.match)."""
    task = next(t for t in yaml.safe_load(open(TASKS_MAIN, encoding="utf-8")) if "cors_them" in t.get("name", ""))
    env = jinja2.Environment()
    env.tests["match"] = lambda gia_tri, mau: re.match(mau, gia_tri) is not None
    return all(env.compile_expression(dk)(onebee_box_cors_them=cors_them) for dk in task["ansible.builtin.assert"]["that"])


class ComposeHaiCheDo(unittest.TestCase):
    def test_http_giu_nguyen_cong_backend(self):
        s = ve(False)
        self.assertEqual(s["portal"]["ports"], ["0.0.0.0:80:80"])
        self.assertEqual(s["open-webui"]["ports"], ["0.0.0.0:3000:8080"])
        self.assertEqual(s["n8n"]["ports"], ["0.0.0.0:5678:5678"])
        self.assertEqual(s["rest-server"]["ports"], ["0.0.0.0:8000:8000"])
        self.assertEqual(s["uptime-kuma"]["ports"], ["0.0.0.0:3001:3001"])
        env = s["n8n"]["environment"]
        self.assertEqual(env["N8N_SECURE_COOKIE"], "false")
        self.assertEqual(env["N8N_WEBHOOK_URL"], "http://192.168.1.10:5678/")
        self.assertNotIn("N8N_PROXY_HOPS", env)
        self.assertNotIn("WEBUI_SESSION_COOKIE_SECURE", s["open-webui"]["environment"])

    def test_https_chi_caddy_cong_bo_cong_va_backend_khong_co_ports(self):
        s = ve(True)
        for ten in ("open-webui", "n8n", "uptime-kuma", "rest-server", "ollama"):
            self.assertNotIn("ports", s[ten], ten)
        cong = sorted(s["portal"]["ports"])
        self.assertEqual(cong, sorted(["0.0.0.0:80:80"] + [f"0.0.0.0:{p}:{p}" for p in (443, 3000, 5678, 8000, 3001)]))
        self.assertIn("./portal/pki:/pki:ro", s["portal"]["volumes"])
        self.assertFalse([v for v in s["portal"]["volumes"] if "secrets" in v or "root.key" in v])   # khóa gốc không gắn vào container
        self.assertEqual(s["portal"]["cap_drop"], ["ALL"])
        self.assertEqual(s["portal"]["cap_add"], ["NET_BIND_SERVICE"])
        self.assertIn("no-new-privileges:true", s["portal"]["security_opt"])

    def test_https_kuma_chua_co_quan_tri_thi_chua_cong_bo_3001(self):
        s = ve(True, kuma="127.0.0.1")
        self.assertNotIn("0.0.0.0:3001:3001", s["portal"]["ports"])
        self.assertIn("0.0.0.0:3000:3000", s["portal"]["ports"])

    def test_moi_container_khong_duoc_tu_nang_quyen_va_rest_server_khoa_chat(self):
        for che_do in (False, True):
            s = ve(che_do)
            for ten, dv in s.items():
                self.assertIn("no-new-privileges:true", dv["security_opt"], ten)
            rs = s["rest-server"]
            self.assertEqual((rs["cap_drop"], rs["read_only"]), (["ALL"], True))
            self.assertEqual(rs["tmpfs"], ["/tmp"])

    def test_https_cau_hinh_ung_dung(self):
        s = ve(True)
        n = s["n8n"]["environment"]
        self.assertNotIn("N8N_SECURE_COOKIE", n)
        self.assertEqual((n["N8N_PROTOCOL"], n["N8N_HOST"], n["N8N_PROXY_HOPS"]), ("https", "192.168.1.10", "1"))
        self.assertEqual(n["N8N_EDITOR_BASE_URL"], "https://192.168.1.10:5678/")
        self.assertEqual(n["N8N_WEBHOOK_URL"], "https://192.168.1.10:5678/")
        w = s["open-webui"]["environment"]
        self.assertEqual((w["WEBUI_SESSION_COOKIE_SECURE"], w["WEBUI_AUTH_COOKIE_SECURE"]), ("true", "true"))
        self.assertEqual(w["CORS_ALLOW_ORIGIN"], "https://192.168.1.10:3000;https://box.anphu.onebee.internal:3000")

    def test_cors_o_che_do_http_duoc_gioi_han(self):
        # Thiếu biến này thì Open WebUI phản chiếu mọi Origin kèm allow-credentials → trang web lạ đọc được API bằng phiên đăng nhập
        # Kỹ thuật vào qua Tailscale bằng tên box.<mã>.onebee.internal, người dùng trong LAN bằng onebee.local (mDNS)
        # → các tên này cũng phải có, lệch thì WebSocket chat hỏng
        w = ve(False)["open-webui"]["environment"]
        self.assertIn("CORS_ALLOW_ORIGIN", w)
        for nguon in w["CORS_ALLOW_ORIGIN"].split(";"):
            self.assertRegex(nguon, r"^http://[a-z0-9.-]+:3000$")
        self.assertEqual(w["CORS_ALLOW_ORIGIN"],
                         "http://192.168.1.10:3000;http://onebee.local:3000;http://box.anphu.onebee.internal:3000")

    def test_cors_o_che_do_https_van_dung_nhu_cu(self):
        cors = ve(True)["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"]
        for nguon in cors.split(";"):
            self.assertTrue(nguon.startswith("https://"), nguon)
        self.assertIn(".onebee.internal:3000", cors)
        self.assertNotIn("http://", cors)

    def test_cors_them_ghep_vao_sau_hai_nguon_mac_dinh_o_ca_hai_che_do(self):
        # Mở WebUI bằng tên/IP khác (DNS router, IP Tailscale, đường hầm SSH) thì Origin lệch → WebSocket chat bị chặn 403; quản trị khai thêm Origin ở đây
        them = ["http://onebee-box.lan:3000", "http://100.64.1.2:3000"]
        mac_dinh_http = "http://192.168.1.10:3000;http://onebee.local:3000;http://box.anphu.onebee.internal:3000"
        mac_dinh_https = "https://192.168.1.10:3000;https://box.anphu.onebee.internal:3000"
        self.assertEqual(ve(False, cors_them=them)["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"], mac_dinh_http + ";" + ";".join(them))
        self.assertEqual(ve(True, cors_them=them)["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"], mac_dinh_https + ";" + ";".join(them))

    def test_cors_them_rong_giu_nguyen_gia_tri_cu(self):
        # Box đã cài không khai biến mới → cấu hình sinh ra phải y hệt trước đây, không thêm dấu ";" thừa
        self.assertEqual(ve(False, cors_them=[]), ve(False))
        self.assertEqual(ve(True, cors_them=[]), ve(True))
        self.assertEqual(ve(False)["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"], "http://192.168.1.10:3000;http://onebee.local:3000;http://box.anphu.onebee.internal:3000")
        self.assertEqual(ve(True)["open-webui"]["environment"]["CORS_ALLOW_ORIGIN"], "https://192.168.1.10:3000;https://box.anphu.onebee.internal:3000")

    def test_cors_them_mac_dinh_trong_group_vars_la_danh_sach_rong(self):
        v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
        self.assertEqual(v["onebee_box_cors_them"], [])

    def test_cors_them_kiem_tra_dinh_dang_origin(self):
        for tot in ([], ["http://onebee-box.lan:3000"], ["https://192.168.1.50:3000", "http://localhost:3000", "http://may-chu"]):
            self.assertTrue(cors_hop_le(tot), tot)
        for xau in (["*"], ["onebee-box.lan:3000"], ["http://onebee-box.lan:3000/"], ["http://onebee-box.lan:3000/duong-dan"],
                    ["ftp://onebee-box.lan"], ["http://a.lan;http://b.lan"], ["http://a.lan:3000 http://b.lan"], [""], ["http://"],
                    "http://onebee-box.lan:3000", [3000]):
            self.assertFalse(cors_hop_le(xau), xau)

    def test_ca_gui_den_cac_cong_cu_cung_mot_nguon(self):
        # image không đổi giữa hai chế độ → chuyển HTTP ↔ HTTPS không phải tải lại gì
        a, b = ve(False), ve(True)
        for ten in a:
            self.assertEqual(a[ten]["image"], b[ten]["image"], ten)


def bieu_thuc_task(tep, ten_bien):
    """Biểu thức Jinja của set_fact gán `ten_bien` trong tệp task (tìm cả trong block)."""
    def duyet(ds):
        for t in ds:
            yield t
            for k in ("block", "rescue", "always"):
                yield from duyet(t.get(k, []))
    for t in duyet(yaml.safe_load(open(tep, encoding="utf-8"))):
        sf = t.get("ansible.builtin.set_fact") or {}
        if ten_bien in sf:
            return sf[ten_bien].strip()
    raise AssertionError(f"không thấy set_fact {ten_bien} trong {tep}")


def tinh(bieu_thuc, **bien):
    env = jinja2.Environment()
    env.filters["bool"] = bool
    return env.from_string(bieu_thuc).render(**bien).strip()


class GiamSatSauDangNhapMotLan(unittest.TestCase):
    """Uptime Kuma tắt đăng nhập riêng khi đứng sau đăng nhập một lần; KHÔNG được mở ra LAN khi còn tắt đăng nhập riêng mà SSO không che."""

    def stat(self, co):
        return {"stat": {"exists": co}}

    def test_sso_hieu_luc_khi_https_va_khong_co_dau_tam_tat(self):
        bt = bieu_thuc_task(os.path.join(ROOT, "box/ansible/roles/box-stack/tasks/https.yml"), "onebee_sso_hieu_luc")
        for https, dau, mong in ((True, False, "True"), (True, True, "False"), (False, False, "False"), (False, True, "False")):
            self.assertEqual(tinh(bt, onebee_https_hieu_luc=https, onebee_sso_dau=self.stat(dau)), mong, (https, dau))

    def test_cong_giam_sat_chi_mo_ra_lan_khi_an_toan(self):
        bt = bieu_thuc_task(TASKS_MAIN, "onebee_kuma_dia_chi")
        for quan_tri, tat_rieng, sso, mong in (
                (False, False, False, "127.0.0.1"),   # chưa có tài khoản quản trị: trang "tạo tài khoản đầu tiên"
                (True, False, False, "0.0.0.0"),
                (True, False, True, "0.0.0.0"),
                (True, True, True, "0.0.0.0"),        # đăng nhập riêng tắt nhưng Caddy đòi đăng nhập một lần
                (True, True, False, "127.0.0.1"),     # tắt HTTPS / tạm tắt SSO: đóng lại tới khi bật lại đăng nhập riêng
                (False, True, True, "127.0.0.1")):
            self.assertEqual(tinh(bt, onebee_kuma_xong=self.stat(quan_tri), onebee_kuma_dau_tat_rieng=self.stat(tat_rieng),
                                  onebee_sso_hieu_luc=sso), mong, (quan_tri, tat_rieng, sso))

    def test_dieu_kien_block_khong_doi_giua_chung(self):
        """Ansible đánh giá lại `when` của block ở TỪNG task: task trong block đổi biến mà điều kiện dùng thì các task sau bị bỏ qua
        (đã gặp: lần cài đầu không sinh lại docker-compose.yml với cổng giám sát mở ra LAN → lần cài hai còn changed)."""
        import re as _re
        for t in yaml.safe_load(open(TASKS_MAIN, encoding="utf-8")):
            if "block" not in t or "when" not in t:
                continue
            dk = " ".join(t["when"] if isinstance(t["when"], list) else [str(t["when"])])
            for con in t["block"]:
                for bien in (con.get("ansible.builtin.set_fact") or {}):
                    self.assertIsNone(_re.search(rf"\b{bien}\b", dk), f"block '{t['name']}': điều kiện dùng {bien} mà task '{con['name']}' đổi")

    def test_cau_hinh_kuma_tat_dang_nhap_rieng_theo_sso(self):
        task = next(t for t in yaml.safe_load(open(TASKS_MAIN, encoding="utf-8")) if t.get("name") == "Cấu hình Uptime Kuma (tài khoản, theo dõi dịch vụ, email báo)")
        self.assertIn("-e KUMA_TAT_DANG_NHAP", task["ansible.builtin.shell"])
        bt = task["environment"]["KUMA_TAT_DANG_NHAP"]
        self.assertEqual(tinh(bt, onebee_sso_hieu_luc=True), "1")
        self.assertEqual(tinh(bt, onebee_sso_hieu_luc=False), "0")
        js = open(os.path.join(ROOT, "box/ansible/roles/box-stack/files/onebee-kuma.js"), encoding="utf-8").read()
        self.assertIn("process.env.KUMA_TAT_DANG_NHAP", js)
        self.assertIn("disableAuth", js)


if __name__ == "__main__":
    unittest.main()
