#!/usr/bin/env python3
"""Kiểm thử docker-compose.yml.j2 ở hai chế độ HTTP / HTTPS (không cần Docker): chỉ Caddy công bố cổng khi HTTPS,
cấu hình ứng dụng đổi đúng (n8n sau proxy, cookie Secure, CORS), chế độ HTTP giữ nguyên như trước. Chạy: python3 -m unittest"""
import os
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
TEMPLATE = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/docker-compose.yml.j2")


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

    def test_ca_gui_den_cac_cong_cu_cung_mot_nguon(self):
        # image không đổi giữa hai chế độ → chuyển HTTP ↔ HTTPS không phải tải lại gì
        a, b = ve(False), ve(True)
        for ten in a:
            self.assertEqual(a[ten]["image"], b[ten]["image"], ten)


if __name__ == "__main__":
    unittest.main()
