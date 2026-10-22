#!/usr/bin/env bash
"""Kiểm thử unit test cho module Prompts và Knowledge Base RAG."""
import json
import os
import unittest
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
    def test_dong_bo_prompts_api_calls(self, mock_call):
        # Giả lập Open WebUI trả về danh sách prompt hiện có rỗng
        mock_call.side_effect = [
            (200, []),  # GET /api/v1/prompts/
            (200, {"status": True}),  # POST /api/v1/prompts/create (to-trinh)
            (200, {"status": True}),  # POST /api/v1/prompts/create (bien-ban)
            (200, {"status": True}),  # POST /api/v1/prompts/create (hop-dong)
            (200, {"status": True}),  # POST /api/v1/prompts/create (bao-cao)
        ]
        count = onebee_webui.dong_bo_prompts(token="test-token")
        self.assertEqual(count, 4)
        self.assertEqual(mock_call.call_count, 5)

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
