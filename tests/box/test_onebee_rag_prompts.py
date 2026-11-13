#!/usr/bin/env bash
"""Kiểm thử unit test cho module Prompts và Knowledge Base RAG."""
import inspect
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
SCRIPT_DIR = os.path.join(ROOT, "box/ansible/roles/box-ai/files")

import sys
sys.path.insert(0, SCRIPT_DIR)
import importlib.util
spec = importlib.util.spec_from_file_location("onebee_webui", os.path.join(SCRIPT_DIR, "onebee-webui.py"))
onebee_webui = importlib.util.module_from_spec(spec)
sys.modules["onebee_webui"] = onebee_webui
spec.loader.exec_module(onebee_webui)


class TestRAGPrompts(unittest.TestCase):
    def test_prompts_files_exist_and_valid(self):
        prompts_dir = os.path.join(SCRIPT_DIR, "prompts")
        self.assertTrue(os.path.isdir(prompts_dir))
        expected_prompts = ["to-trinh.json", "bien-ban.json", "hop-dong.json", "bao-cao.json"]
        for p in expected_prompts:
            p_path = os.path.join(prompts_dir, p)
            self.assertTrue(os.path.isfile(p_path), f"Thiếu file {p}")
            with open(p_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("command", data)
            self.assertIn("title", data)
            self.assertIn("content", data)
            self.assertTrue(data["command"].startswith("/"))

    def test_knowledge_files_exist(self):
        knowledge_dir = os.path.join(SCRIPT_DIR, "knowledge")
        self.assertTrue(os.path.isdir(knowledge_dir))
        self.assertTrue(os.path.isfile(os.path.join(knowledge_dir, "nghi-dinh-30-2020-nd-cp.md")))
        self.assertTrue(os.path.isfile(os.path.join(knowledge_dir, "luat-hop-tac-xa-2023.md")))

    @patch("onebee_webui.call")
    def test_tao_mau_gui_dung_truong(self, mock_call):
        mock_call.side_effect = [
            (200, []),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
        ]
        count = onebee_webui.dong_bo_prompts(token="test-token")
        self.assertEqual(count, 4)
        posts = [c for c in mock_call.call_args_list if c.args[0] == "POST" and c.args[1] == "/api/v1/prompts/create"]
        self.assertEqual(len(posts), 4)
        for c in posts:
            body = c.args[3] if len(c.args) > 3 else c.kwargs.get("body")
            self.assertFalse(body["command"].startswith("/"))
            self.assertTrue(body.get("name"))
            self.assertTrue(body.get("content"))
            self.assertEqual(body.get("access_grants"), onebee_webui.PUBLIC_READ)
            self.assertNotIn("title", body)

    @patch("onebee_webui.call")
    def test_mau_da_dung_thi_khong_goi_gi_them(self, mock_call):
        prompts_dir = os.path.join(SCRIPT_DIR, "prompts")
        existing = []
        for i, fname in enumerate(sorted(os.listdir(prompts_dir))):
            if fname.endswith(".json"):
                with open(os.path.join(prompts_dir, fname), encoding="utf-8") as f:
                    d = json.load(f)
                existing.append({
                    "id": f"p{i}",
                    "command": d["command"].lstrip("/"),
                    "name": d["title"],
                    "content": d["content"],
                    "access_grants": [{"principal_type": "user", "principal_id": "*", "permission": "read"}],
                })
        mock_call.return_value = (200, existing)
        buf = io.StringIO()
        with redirect_stdout(buf):
            onebee_webui.dong_bo_prompts(token="test-token")
        out = buf.getvalue()
        self.assertEqual(mock_call.call_count, 1)
        self.assertNotIn("đã tạo", out)
        self.assertNotIn("đã cập nhật", out)

    @patch("onebee_webui.call")
    def test_mau_khac_noi_dung_thi_cap_nhat_theo_id(self, mock_call):
        mock_call.side_effect = [
            (200, [{"id": "p1", "command": "to-trinh", "name": "cũ", "content": "cũ", "access_grants": []}]),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
            (200, {"id": "p"}),
        ]
        onebee_webui.dong_bo_prompts(token="test-token")
        paths = [(c.args[0], c.args[1]) for c in mock_call.call_args_list]
        self.assertIn(("POST", "/api/v1/prompts/id/p1/update"), paths)
        self.assertFalse(any("/command/" in p for _, p in paths))

    @patch("onebee_webui.call")
    def test_loi_tao_mau_thi_dung(self, mock_call):
        mock_call.side_effect = [
            (200, []),
            (422, "thiếu name"),
        ]
        with self.assertRaises(SystemExit):
            onebee_webui.dong_bo_prompts(token="test-token")

    @patch("onebee_webui.call")
    def test_tri_thuc_da_co_thi_khong_tao_trung(self, mock_call):
        mock_call.return_value = (
            200,
            {
                "items": [
                    {
                        "id": "kb1",
                        "name": "Thư viện Pháp lý HTX",
                        "access_grants": [{"principal_type": "user", "principal_id": "*", "permission": "read"}],
                    }
                ],
                "total": 1,
            },
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            cid = onebee_webui.dong_bo_tri_thuc(token="test-token")
        out = buf.getvalue()
        self.assertEqual(cid, "kb1")
        paths = [(c.args[0], c.args[1]) for c in mock_call.call_args_list]
        self.assertNotIn(("POST", "/api/v1/knowledge/create"), paths)
        self.assertNotIn("đã tạo", out)

    @patch("onebee_webui.call")
    def test_tri_thuc_chua_co_thi_tao_mot_lan_va_cho_moi_nguoi_doc(self, mock_call):
        mock_call.side_effect = [
            (200, {"items": [], "total": 0}),
            (200, {"id": "kb2"}),
        ]
        cid = onebee_webui.dong_bo_tri_thuc(token="test-token")
        self.assertEqual(cid, "kb2")
        posts = [c for c in mock_call.call_args_list if c.args[0] == "POST" and c.args[1] == "/api/v1/knowledge/create"]
        self.assertEqual(len(posts), 1)
        body = posts[0].args[3] if len(posts[0].args) > 3 else posts[0].kwargs.get("body")
        self.assertEqual(body.get("access_grants"), onebee_webui.PUBLIC_READ)

    def test_dong_bo_tro_ly_khong_tu_tao_bo_tri_thuc(self):
        src = inspect.getsource(onebee_webui.dong_bo_tro_ly)
        self.assertNotIn("dong_bo_tri_thuc(", src)


class TestCaiDatTrenBox(unittest.TestCase):
    """Tệp mẫu phải nằm ngay trong thư mục mà onebee-webui.py đọc trên Box (cạnh script), không lồng thêm một cấp."""

    @staticmethod
    def noi_tep_ve(src, dest):
        # Quy tắc của ansible.builtin.copy: src là thư mục không có "/" cuối → chép cả thư mục vào trong dest
        # (dest/<tên src>/...); có "/" cuối → chỉ chép nội dung vào dest
        return dest.rstrip("/") if src.endswith("/") else os.path.join(dest.rstrip("/"), os.path.basename(src))

    def test_mau_va_tri_thuc_cai_dung_thu_muc_script_doc(self):
        import yaml
        with open(os.path.join(ROOT, "box/ansible/roles/box-ai/tasks/main.yml"), encoding="utf-8") as f:
            tasks = yaml.safe_load(f)
        noi = {}
        for t in tasks:
            copy = t.get("ansible.builtin.copy")
            if not copy:
                continue
            for item in t.get("loop", []):
                src = copy["src"].replace("{{ item.src }}", item["src"])
                dest = copy["dest"].replace("{{ item.src }}", item["src"]).replace("{{ item.dest }}", item.get("dest", ""))
                if os.path.isdir(os.path.join(SCRIPT_DIR, src)):
                    noi[src.rstrip("/")] = self.noi_tep_ve(src, dest)
                else:
                    noi[src] = dest
        thu_muc_script = os.path.dirname(noi["onebee-webui.py"])
        self.assertEqual(noi.get("prompts"), os.path.join(thu_muc_script, "prompts"))
        self.assertEqual(noi.get("knowledge"), os.path.join(thu_muc_script, "knowledge"))


if __name__ == "__main__":
    unittest.main()
