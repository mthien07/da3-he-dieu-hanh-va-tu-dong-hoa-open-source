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


def ve(https, kuma="0.0.0.0"):
    v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=https, onebee_kuma_dia_chi=kuma)
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # như Ansible
    env.filters["bool"] = bool
    return yaml.safe_load(env.from_string(open(TEMPLATE, encoding="utf-8").read()).render(**v))["services"]


class ComposeHaiCheDo(unittest.TestCase):
    def test_http_giu_nguyen_cong_backend(self):
        s = ve(False)
        self.assertEqual(s["portal"]["ports"], ["0.0.0.0:80:80"])
        self.assertEqual(s["n8n"]["ports"], ["0.0.0.0:5678:5678"])
        self.assertEqual(s["rest-server"]["ports"], ["0.0.0.0:8000:8000"])
        self.assertEqual(s["uptime-kuma"]["ports"], ["0.0.0.0:3001:3001"])
        self.assertNotIn("ports", s["ai-rag"])          # Trợ lý AI chỉ vào qua Caddy, không công bố cổng
        env = s["n8n"]["environment"]
        self.assertEqual(env["N8N_SECURE_COOKIE"], "false")
        self.assertEqual(env["N8N_WEBHOOK_URL"], "http://192.168.1.10:5678/")
        self.assertNotIn("N8N_PROXY_HOPS", env)

    def test_https_chi_caddy_cong_bo_cong_va_backend_khong_co_ports(self):
        s = ve(True)
        for ten in ("ai-rag", "n8n", "uptime-kuma", "rest-server", "ollama"):
            self.assertNotIn("ports", s[ten], ten)
        cong = sorted(s["portal"]["ports"])
        self.assertEqual(cong, sorted(["0.0.0.0:80:80"] + [f"0.0.0.0:{p}:{p}" for p in (443, 5678, 8000, 3001)]))
        self.assertIn("./portal/pki:/pki:ro", s["portal"]["volumes"])
        self.assertFalse([v for v in s["portal"]["volumes"] if "secrets" in v or "root.key" in v])   # khóa gốc không gắn vào container
        self.assertEqual(s["portal"]["cap_drop"], ["ALL"])
        self.assertEqual(s["portal"]["cap_add"], ["NET_BIND_SERVICE"])
        self.assertIn("no-new-privileges:true", s["portal"]["security_opt"])

    def test_https_kuma_chua_co_quan_tri_thi_chua_cong_bo_3001(self):
        s = ve(True, kuma="127.0.0.1")
        self.assertNotIn("0.0.0.0:3001:3001", s["portal"]["ports"])
        self.assertIn("0.0.0.0:5678:5678", s["portal"]["ports"])

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
        a = s["ai-rag"]["environment"]
        self.assertEqual(a["AI_MO_HINH"], "gemma4:e2b-it-qat")
        self.assertEqual(a["AI_MO_HINH_NHUNG"], "nomic-embed-text:v1.5")
        self.assertEqual((a["AI_OLLAMA_URL"], a["AI_CAU_NOI_URL"]), ("http://ollama:11434", "http://cau-noi:8080"))
        self.assertEqual((a["AI_TRI_THUC"], a["AI_MAU"], a["AI_TRI_THUC_DON_VI"]),
                         ("/app/knowledge", "/app/prompts", "/du-lieu-tri-thuc"))
        self.assertEqual(s["ai-rag"]["networks"], ["sso", "ai"])
        self.assertEqual(s["ollama"]["networks"], ["default", "ai"])
        self.assertEqual(s["ai-rag"]["healthcheck"]["test"][0], "CMD")
        self.assertIn("./ai-rag:/app:ro", s["ai-rag"]["volumes"])

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
