#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử kho mẫu prompt hành chính NĐ 30 và bộ tri thức RAG trên onebee-ai-rag.py."""

import importlib.util
import json
import os
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
AI_FILES = os.path.join(ROOT, "box/ansible/roles/box-ai/files")
PROMPTS_DIR = os.path.join(AI_FILES, "prompts")
KNOWLEDGE_DIR = os.path.join(AI_FILES, "knowledge")

spec = importlib.util.spec_from_file_location("onebee_ai_rag", os.path.join(AI_FILES, "onebee-ai-rag.py"))
onebee_ai_rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(onebee_ai_rag)


class _EnvTam:
    def __init__(self, **pairs):
        self.pairs = pairs
        self.old = {}

    def __enter__(self):
        for k, v in self.pairs.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def __exit__(self, *args):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestDongBoRagVaPrompts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        self.secrets = os.path.join(self.tmp.name, "secrets")
        os.makedirs(self.data)
        os.makedirs(self.secrets)

    def test_dong_bo_prompts_day_du_va_idempotent(self):
        with _EnvTam(
            ONEBEE_AI_DATA=self.data,
            ONEBEE_SECRETS=self.secrets,
            ONEBEE_PROMPTS_DIR=PROMPTS_DIR,
        ):
            n1 = onebee_ai_rag.dong_bo_prompts()
            self.assertEqual(n1, 4)
            cache_path = os.path.join(self.data, "prompts-cache.json")
            self.assertTrue(os.path.isfile(cache_path))
            lan1 = open(cache_path, encoding="utf-8").read()
            ds = json.loads(lan1)
            self.assertEqual({d["command"] for d in ds}, {"to-trinh", "bien-ban", "hop-dong", "bao-cao"})
            for d in ds:
                self.assertTrue(d["title"] and d["content"])

            n2 = onebee_ai_rag.dong_bo_prompts()
            self.assertEqual(n2, 4)
            self.assertEqual(open(cache_path, encoding="utf-8").read(), lan1)

    def test_dong_bo_prompts_bo_qua_file_json_hong(self):
        thu_mau = os.path.join(self.tmp.name, "prompts")
        os.makedirs(thu_mau)
        open(os.path.join(thu_mau, "hop-le.json"), "w", encoding="utf-8").write(
            json.dumps({"command": "/thu-nghiem", "title": "Thử nghiệm", "content": "Nội dung"})
        )
        open(os.path.join(thu_mau, "hong.json"), "w", encoding="utf-8").write("{khong phai json")
        with _EnvTam(ONEBEE_AI_DATA=self.data, ONEBEE_PROMPTS_DIR=thu_mau):
            n = onebee_ai_rag.dong_bo_prompts()
        self.assertEqual(n, 1)

    def test_dong_bo_tri_thuc_idempotent_khong_trung_lap(self):
        with _EnvTam(
            ONEBEE_AI_DATA=self.data,
            ONEBEE_KNOWLEDGE_DIRS=KNOWLEDGE_DIR,
            POSTGREST_URL="",
        ):
            n1 = onebee_ai_rag.dong_bo_tri_thuc()
            self.assertGreaterEqual(n1, 4)
            idx_path = os.path.join(self.data, "knowledge-index.json")
            raw1 = open(idx_path, encoding="utf-8").read()
            chunks = json.loads(raw1)["chunks"]
            self.assertEqual(len(chunks), n1)
            self.assertEqual(len({c["id"] for c in chunks}), len(chunks))
            self.assertEqual({c["nguon"] for c in chunks}, {"luat-hop-tac-xa-2023.md", "nghi-dinh-30-2020-nd-cp.md"})

            n2 = onebee_ai_rag.dong_bo_tri_thuc()
            self.assertEqual(n2, n1)
            self.assertEqual(open(idx_path, encoding="utf-8").read(), raw1)

    def test_dong_bo_tri_thuc_day_len_postgrest_neu_cau_hinh(self):
        received = []

        class MockPg(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0"))
                received.append((self.path, json.loads(self.rfile.read(n).decode("utf-8"))))
                self.send_response(201)
                self.end_headers()

            def log_message(self, *args):
                pass

        sv = ThreadingHTTPServer(("127.0.0.1", 0), MockPg)
        t = threading.Thread(target=sv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(sv.shutdown)
        self.addCleanup(sv.server_close)

        with _EnvTam(
            ONEBEE_AI_DATA=self.data,
            ONEBEE_KNOWLEDGE_DIRS=KNOWLEDGE_DIR,
            POSTGREST_URL=f"http://127.0.0.1:{sv.server_port}",
        ):
            n = onebee_ai_rag.dong_bo_tri_thuc()
        self.assertGreaterEqual(n, 4)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "/tai_lieu_tri_thuc")
        self.assertEqual(len(received[0][1]), n)

    def test_dong_bo_tro_ly_tao_cap_nhat_va_khong_doi(self):
        loi_dan_tam = os.path.join(self.tmp.name, "loi-dan.md")
        open(loi_dan_tam, "w", encoding="utf-8").write("Lời dặn v1\n")
        with _EnvTam(
            ONEBEE_AI_DATA=self.data,
            ONEBEE_LOI_DAN=loi_dan_tam,
            ONEBEE_GOI_Y=os.path.join(AI_FILES, "goi-y.json"),
        ):
            self.assertEqual(onebee_ai_rag.dong_bo_tro_ly(), "created")
            self.assertEqual(onebee_ai_rag.dong_bo_tro_ly(), "unchanged")
            open(loi_dan_tam, "w", encoding="utf-8").write("Lời dặn v2\n")
            self.assertEqual(onebee_ai_rag.dong_bo_tro_ly(), "updated")


class TestCaiDatTrenBox(unittest.TestCase):
    def test_ansible_tasks_chay_dong_bo_tro_ly_prompts_va_tri_thuc(self):
        tasks_path = os.path.join(ROOT, "box/ansible/roles/box-ai/tasks/main.yml")
        txt = open(tasks_path, encoding="utf-8").read()
        self.assertIn("onebee-ai-rag.py", txt)
        for cmd in ("dong-bo-tro-ly", "dong-bo-prompts", "dong-bo-tri-thuc"):
            self.assertIn(cmd, txt)

    def test_cli_onebee_box_co_dong_bo_prompts_va_tri_thuc(self):
        box_sh = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/onebee-box.sh.j2")
        txt = open(box_sh, encoding="utf-8").read()
        self.assertIn("dong-bo-prompts) tro_ly_ai dong-bo-prompts ;;", txt)
        self.assertIn("dong-bo-tri-thuc) tro_ly_ai dong-bo-tri-thuc ;;", txt)

    def test_du_4_mau_prompt_va_2_tri_thuc(self):
        for ten in ("to-trinh.json", "bien-ban.json", "hop-dong.json", "bao-cao.json"):
            self.assertTrue(os.path.isfile(os.path.join(PROMPTS_DIR, ten)), ten)
        for ten in ("nghi-dinh-30-2020-nd-cp.md", "luat-hop-tac-xa-2023.md"):
            self.assertTrue(os.path.isfile(os.path.join(KNOWLEDGE_DIR, ten)), ten)
        self.assertTrue(os.path.isfile(os.path.join(AI_FILES, "goi-y.json")))
        self.assertTrue(os.path.isfile(os.path.join(AI_FILES, "tro-ly-onebee-loi-dan.md")))


if __name__ == "__main__":
    unittest.main()
