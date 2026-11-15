# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử động cơ quy trình Node-RED 5.0.9 (role box-quy-trinh, Apache-2.0) và ADR 0007."""
import glob
import json
import os
import shutil
import subprocess
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ROLE = os.path.join(ROOT, "box/ansible/roles/box-quy-trinh")


def render_role_template(rel_path):
    with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
        gvars = yaml.safe_load(f)
    with open(os.path.join(ROLE, "vars/main.yml"), encoding="utf-8") as f:
        rvars = yaml.safe_load(f)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(ROLE, "templates")),
        undefined=jinja2.StrictUndefined,
    )
    env.filters["bool"] = bool
    env.filters["to_json"] = lambda v: json.dumps(v, ensure_ascii=False)
    ctx = dict(gvars)
    ctx.update(rvars)
    ctx.update({
        "onebee_webhook_key": "test-webhook-key-123",
        "onebee_tram_key": "test-tram-key-456",
        "onebee_smtp_password": "test-smtp-password",
    })
    return env.get_template(rel_path).render(**ctx)


class TestBoxQuyTrinhNodeRed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flows_raw = render_role_template("flows.json.j2")
        cls.flows = json.loads(cls.flows_raw)
        cls.settings = render_role_template("settings.js.j2")
        with open(os.path.join(ROLE, "vars/main.yml"), encoding="utf-8") as f:
            cls.vars_data = yaml.safe_load(f)

    def test_node_red_image_va_cong_osi(self):
        with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
            gvars = yaml.safe_load(f)
        self.assertIn("nodered/node-red:5.0.9@sha256:", gvars["onebee_box_images"]["node_red"])
        self.assertEqual(gvars["onebee_box_ports"]["quy_trinh"], 5678)
        self.assertNotIn("n" + "8n", gvars["onebee_box_images"])
        self.assertNotIn("n" + "8n", gvars["onebee_box_ports"])

    def test_settings_js_an_toan_ngoai_tuyen(self):
        for expected in (
            'httpAdminRoot: "/quy-trinh"',
            "functionExternalModules: false",
            "exportGlobalContextKeys: false",
            "autoInstall: false",
            "allowInstall: false",
            "allowUpload: false",
            "palette: { catalogue: [] }",
        ):
            self.assertIn(expected, self.settings)

    def test_du_11_quy_trinh_va_khong_co_nut_chay_lenh(self):
        flow_defs = self.vars_data["onebee_quy_trinh_flows"]
        self.assertEqual(len(flow_defs), 11)
        node_ids = {n["id"] for n in self.flows if "id" in n}
        for fl in flow_defs:
            self.assertIn(fl["id"], node_ids, f"Thiếu node {fl['id']}")

        http_urls = {n["url"] for n in self.flows if n.get("type") == "http in"}
        self.assertIn("/healthz", http_urls)
        expected_webhooks = {fl["webhook"] for fl in flow_defs if fl["webhook"]}
        self.assertEqual(len(expected_webhooks), 9)
        for url in expected_webhooks:
            self.assertIn(url, http_urls, f"Thiếu webhook {url}")
        self.assertIn("/webhook/onebee-phe-duyet", http_urls)

        types = {n.get("type") for n in self.flows}
        self.assertNotIn("exec", types)
        self.assertNotIn("executeCommand", types)

    def test_adr_0007_va_role_box_quy_trinh_ton_tai(self):
        adr_files = glob.glob(os.path.join(ROOT, "docs/adr/0007-*.md"))
        self.assertEqual(len(adr_files), 1)
        with open(adr_files[0], encoding="utf-8") as f:
            adr = f.read()
        self.assertIn("Node-RED 5.0.9", adr)
        self.assertIn("Apache-2.0", adr)
        for idx in range(1, 12):
            self.assertIn(f"| `{idx:02d}` |", adr)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "box/ansible/roles/box-" + "n" + "8n")))
        self.assertTrue(os.path.isdir(ROLE))

    def test_chot_chan_poka_yoke_phe_duyet_va_csv(self):
        fn_map = {n["id"]: n["func"] for n in self.flows if n.get("type") == "function"}
        phe_duyet_js = fn_map["fn_11_phe_duyet"]
        self.assertIn("quan_ly", phe_duyet_js)
        self.assertIn("nguoiDuyet === nguoiTao", phe_duyet_js)
        self.assertIn("409", phe_duyet_js)
        self.assertIn("422", phe_duyet_js)

        if not shutil.which("node"):
            return

        nhap_dh_js = fn_map["fn_04_nhap_don_hang"]
        script = f"""
const runPheDuyet = (headers, payload) => {{
  const msg = {{ req: {{ headers }}, payload }};
  {phe_duyet_js}
}};
const r1 = runPheDuyet({{ "remote-user": "nhanvien1", "remote-groups": "nhan_vien" }}, {{ nguoi_tao: "lan", trang_thai_duyet: "DA_DUYET" }});
if (r1.statusCode !== 403) process.exit(11);
const r2 = runPheDuyet({{ "remote-user": "lan", "remote-groups": "quan_ly" }}, {{ nguoi_tao: "lan", trang_thai_duyet: "DA_DUYET" }});
if (r2.statusCode !== 409) process.exit(12);
const r3 = runPheDuyet({{ "remote-user": "minh", "remote-groups": "quan_ly" }}, {{ nguoi_tao: "lan", trang_thai_duyet: "TU_CHOI", ly_do_duyet: "" }});
if (r3.statusCode !== 422) process.exit(13);
const r4 = runPheDuyet({{ "remote-user": "minh", "remote-groups": "quan_ly" }}, {{ ma_don: "DH-1", nguoi_tao: "lan", trang_thai_duyet: "DA_DUYET", ly_do_duyet: "OK" }});
if (r4.statusCode !== 200 || r4.payload.nguoi_duyet !== "minh") process.exit(14);

const runCsv = (payload) => {{
  const msg = {{ req: {{ headers: {{}} }}, payload }};
  {nhap_dh_js}
}};
const c1 = runCsv({{ ma_don: "DH-2", khach_hang: "=CMD()\\nA", mat_hang: "Mật ong" }});
if (c1.statusCode !== 201 || !c1.payload.csv_dong.includes("'=CMD() A") || !c1.payload.csv_dong.includes("CHO_DUYET")) process.exit(15);
"""
        r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"node failed ({r.returncode}): {r.stderr} {r.stdout}")


if __name__ == "__main__":
    unittest.main()
