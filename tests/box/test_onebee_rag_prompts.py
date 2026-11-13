#!/usr/bin/env bash
"""Kiểm thử unit test cho module Prompts và Knowledge Base RAG."""
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
    def test_dong_bo_tri_thuc_create_collection(self, mock_call):
        mock_call.side_effect = [
            (200, []),  # GET /api/v1/knowledge/ -> chưa có
            (200, {"id": "col-123", "name": "Thư viện Pháp lý HTX"}),  # POST /api/v1/knowledge/create
        ]
        cid = onebee_webui.dong_bo_tri_thuc(token="test-token")
        self.assertEqual(cid, "col-123")


if __name__ == "__main__":
    unittest.main()
