#!/usr/bin/env python3
"""Mẫu n8n (thông tin đăng nhập + quy trình nhận tình trạng) ở hai chế độ khóa gửi tình trạng dùng chung: JSON hợp lệ, đúng xác thực.
Chạy: python3 -m unittest"""
import json
import os
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
TPL = os.path.join(ROOT, "box/ansible/roles/box-n8n/templates")


def ve(ten, khoa_chung):
    v = yaml.safe_load(open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8"))
    v.update(yaml.safe_load(open(os.path.join(ROOT, "box/ansible/roles/box-n8n/vars/main.yml"), encoding="utf-8")) or {})
    v.update(onebee_box_khoa_tinh_trang_chung=khoa_chung, onebee_smtp_password="s", onebee_webhook_key="w", onebee_tram_key="k" if khoa_chung else "",
             onebee_form_password="f", onebee_kythuat_password="t", onebee_https_hieu_luc=False, onebee_box_ip="192.168.1.10")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TPL), keep_trailing_newline=True, trim_blocks=True)
    env.filters["to_json"] = lambda x: json.dumps(x, ensure_ascii=False)
    env.filters["bool"] = bool
    return json.loads(env.get_template(ten).render(**v))


class MauN8n(unittest.TestCase):
    def test_credentials_hai_che_do(self):
        co = [c["id"] for c in ve("credentials.json.j2", True)]
        khong = [c["id"] for c in ve("credentials.json.j2", False)]
        self.assertIn("onebeeTram000001", co)
        self.assertNotIn("onebeeTram000001", khong)
        self.assertEqual([i for i in co if i != "onebeeTram000001"], khong)   # chỉ khác đúng thông tin đăng nhập của khóa chung

    def test_quy_trinh_nhan_tinh_trang_hai_che_do(self):
        wf = ve("workflows/06-nhan-tinh-trang-may-tram.json.j2", True)
        hook = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
        self.assertEqual(hook["parameters"]["authentication"], "headerAuth")
        self.assertEqual(hook["credentials"]["httpHeaderAuth"]["id"], "onebeeTram000001")
        wf = ve("workflows/06-nhan-tinh-trang-may-tram.json.j2", False)
        hook = next(n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
        self.assertEqual(hook["parameters"]["authentication"], "none")
        self.assertNotIn("credentials", hook)
        # dù bỏ khóa chung, vẫn chỉ máy ĐÃ CẤP (file đánh dấu) mới được ghi
        doc = next(n for n in wf["nodes"] if n["name"] == "Máy đã được cấp?")
        self.assertIn("may-da-cap", doc["parameters"]["fileSelector"])

    def test_moi_quy_trinh_deu_la_json_hop_le_o_ca_hai_che_do(self):
        for f in sorted(os.listdir(f"{TPL}/workflows")):
            if f.endswith(".json.j2") and not f.startswith("_"):
                for che_do in (True, False):
                    try:
                        ve(f"workflows/{f}", che_do)
                    except Exception as e:   # noqa: BLE001 — báo rõ file nào hỏng
                        self.fail(f"{f} (khóa chung={che_do}): {e}")


if __name__ == "__main__":
    unittest.main()
