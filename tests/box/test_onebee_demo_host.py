#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử chế độ bản chạy thử công khai OLP 2026 (Caddy demo host, biểu ngữ index.html, SQL idempotent, timer 03:00)."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
TEMPLATES = os.path.join(ROOT, "box/ansible/roles/box-stack/templates")
VARS_FILE = os.path.join(ROOT, "box/ansible/group_vars/all.yml")
GOI_Y_FILE = os.path.join(ROOT, "box/ansible/roles/box-ai/files/prompts/goi-y.json")
TAO_CA = os.path.join(ROOT, "box/ansible/roles/box-stack/files/onebee-ca.sh")
CADDY = os.environ.get("ONEBEE_TEST_CADDY") or shutil.which("caddy")


def nap_bien(**them):
    with open(VARS_FILE, encoding="utf-8") as f:
        v = yaml.safe_load(f)
    v.update(
        onebee_box_ip="127.0.0.1",
        onebee_box_ma_don_vi="anphu",
        onebee_box_ten_don_vi="HTX OneBee Demo",
        onebee_box_ten_mdns="onebee",
        onebee_box_samba_share="chung",
        onebee_https_hieu_luc=False,
        onebee_sso_hieu_luc=True,
        onebee_kuma_dia_chi="0.0.0.0",
        onebee_box_ports={"portal": 80, "tro_ly_ai": 3000, "n8n": 5678, "rest_server": 8000, "uptime_kuma": 3001},
        onebee_goi_y=[],
    )
    v.update(them)
    return v


def render_mau(ten, **bien):
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)
    env.filters["bool"] = bool
    with open(os.path.join(TEMPLATES, ten), encoding="utf-8") as f:
        return env.from_string(f.read()).render(**bien)


class TestDemoHostTemplatesVaSql(unittest.TestCase):
    def test_mac_dinh_tat_demo_va_khong_hien_khung_demo(self):
        with open(VARS_FILE, encoding="utf-8") as f:
            v_goc = yaml.safe_load(f)
        self.assertIs(v_goc.get("onebee_box_che_do_demo"), False)
        self.assertEqual(v_goc.get("onebee_box_domain"), "")

        html = render_mau("index.html.j2", **nap_bien(onebee_box_che_do_demo=False))
        self.assertNotIn("khung-demo-olp", html)
        self.assertNotIn("Bản chạy thử công khai OLP 2026", html)

        caddy_lan = render_mau("Caddyfile.j2", **nap_bien(onebee_box_che_do_demo=False, onebee_box_domain=""))
        self.assertNotIn("X-OneBee-Demo-Mode", caddy_lan)
        self.assertIn(":80 {", caddy_lan)

    def test_index_html_che_do_demo_du_3_tai_khoan_va_gioi_han_5mb(self):
        html = render_mau("index.html.j2", **nap_bien(onebee_box_che_do_demo=True, onebee_box_domain="demo.onebee.vn"))
        self.assertIn("Bản chạy thử công khai OLP 2026 — Dữ liệu giả lập, tự đặt lại lúc 03:00 mỗi ngày", html)
        for tk in ("nhanvien1", "kythuat1", "quanly1", "≤ 5 MB", "demo.onebee.vn"):
            self.assertIn(tk, html)

    def test_systemd_timer_va_service_dat_lai_03h_hang_ngay(self):
        timer = render_mau("onebee-demo-reset.timer.j2", **nap_bien())
        service = render_mau("onebee-demo-reset.service.j2", **nap_bien())
        self.assertIn("OnCalendar=*-*-* 03:00:00", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("nap-du-lieu-demo.sql", service)
        self.assertIn("ON_ERROR_STOP=1", service)

    def test_sql_nap_du_lieu_demo_idempotent_va_du_bang_mau(self):
        sql_path = os.path.join(ROOT, "scripts/nap-du-lieu-demo.sql")
        with open(sql_path, encoding="utf-8") as f:
            sql = f.read()
        self.assertIn("SPDX-License-Identifier: MIT", sql)
        self.assertIn("BEGIN;", sql)
        self.assertIn("COMMIT;", sql)
        self.assertGreaterEqual(sql.count("ON CONFLICT"), 5)
        for i in range(1, 6):
            self.assertIn(f"DEMO-DH-00{i}", sql)
        for i in range(1, 4):
            self.assertIn(f"DEMO-HT-00{i}", sql)
        self.assertIn("DEMO-KS-001", sql)
        self.assertIn("DEMO-KS-002", sql)
        self.assertEqual(len(re.findall(r"'DEMO-TEP-00[12]'", sql)), 2)
        self.assertIn("'CLEAN'", sql)

    def test_inventory_demo_example_day_du_bien(self):
        inv_path = os.path.join(ROOT, "box/ansible/inventory.demo.ini.example")
        with open(inv_path, encoding="utf-8") as f:
            inv = f.read()
        self.assertIn("SPDX-License-Identifier: MIT", inv)
        self.assertIn("onebee_box_che_do_demo=true", inv)
        self.assertIn("onebee_box_domain=", inv)


@unittest.skipUnless(CADDY, "cần caddy (ONEBEE_TEST_CADDY)")
class TestDemoHostCaddyValidate(unittest.TestCase):
    def _validate(self, caddyfile_txt):
        with tempfile.TemporaryDirectory() as tmp:
            if "/pki/" in caddyfile_txt:
                subprocess.run([TAO_CA, f"{tmp}/ca", "anphu", "127.0.0.1"], check=True, capture_output=True,
                               env={**os.environ, "ONEBEE_PKI_OUT": f"{tmp}/pki"})
                caddyfile_txt = caddyfile_txt.replace("/pki/", f"{tmp}/pki/")
            p = os.path.join(tmp, "Caddyfile")
            with open(p, "w", encoding="utf-8") as f:
                f.write(caddyfile_txt)
            env = {**os.environ, "XDG_DATA_HOME": f"{tmp}/data", "XDG_CONFIG_HOME": f"{tmp}/cfg"}
            r = subprocess.run([CADDY, "validate", "--config", p, "--adapter", "caddyfile"],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_caddy_demo_only_khong_tls_internal_va_validate_thanh_cong(self):
        nd = render_mau("Caddyfile.j2", **nap_bien(
            onebee_https_hieu_luc=False,
            onebee_box_che_do_demo=True,
            onebee_box_domain="demo.onebee.vn",
        ))
        self.assertIn("https://demo.onebee.vn {", nd)
        self.assertNotIn("tls internal", nd)
        self.assertIn("X-OneBee-Demo-Mode 1", nd)
        self.assertIn("X-OneBee-RateLimit-AI 10r/m", nd)
        self.assertIn("max_size 5MB", nd)
        self._validate(nd)

    def test_caddy_lan_https_cung_demo_host_validate_thanh_cong(self):
        nd = render_mau("Caddyfile.j2", **nap_bien(
            onebee_https_hieu_luc=True,
            onebee_box_che_do_demo=True,
            onebee_box_domain="demo.onebee.vn",
        ))
        self.assertIn("https://box.anphu.onebee.internal:443 {", nd)
        self.assertIn("https://demo.onebee.vn {", nd)
        khoi_demo = nd.split("https://demo.onebee.vn {", 1)[1]
        self.assertNotIn("tls internal", khoi_demo)
        self._validate(nd)


if __name__ == "__main__":
    unittest.main()
