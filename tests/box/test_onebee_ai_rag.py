#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử toàn diện dịch vụ Trợ lý AI & RAG nhẹ trên lõi (onebee-ai-rag.py)."""

from datetime import date
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
AI_FILES = os.path.join(ROOT, "box/ansible/roles/box-ai/files")
AI_RAG_PY = os.path.join(AI_FILES, "onebee-ai-rag.py")
KNOWLEDGE_DIR = os.path.join(AI_FILES, "knowledge")
PROMPTS_DIR = os.path.join(AI_FILES, "prompts")

spec = importlib.util.spec_from_file_location("onebee_ai_rag", AI_RAG_PY)
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


class TestChunkVaRag(unittest.TestCase):
    def test_chunk_markdown_giu_tieu_de_va_gioi_han_do_dai(self):
        md = "# Nghị định 30\n\n## Khổ giấy\n" + ("Đoạn văn bản mẫu. " * 60) + "\n### Lề trang\nLề trái 30-35 mm."
        chunks = onebee_ai_rag.chunk_markdown(md, "nd30.md", max_chars=250)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[-1]["tieu_de"], "Nghị định 30 — Khổ giấy — Lề trang")
        self.assertEqual(chunks[-1]["nguon"], "nd30.md")

    def test_tim_doan_lien_quan_truy_xuat_dung_nd30_va_luat_htx(self):
        with _EnvTam(ONEBEE_KNOWLEDGE_DIRS=KNOWLEDGE_DIR):
            chunks = onebee_ai_rag.nap_kho_tri_thuc_tu_tep()
        kq_nd30 = onebee_ai_rag.tim_doan_lien_quan("Kho giay A4 va le trai nghi dinh 30 quy dinh the nao?", chunks)
        self.assertTrue(kq_nd30)
        self.assertEqual(kq_nd30[0]["nguon"], "nghi-dinh-30-2020-nd-cp.md")

        kq_htx = onebee_ai_rag.tim_doan_lien_quan("Thành lập hợp tác xã cần tối thiểu bao nhiêu thành viên?", chunks)
        self.assertTrue(kq_htx)
        self.assertEqual(kq_htx[0]["nguon"], "luat-hop-tac-xa-2023.md")


class TestChanPiiTomTat(unittest.TestCase):
    def test_cho_phep_so_lieu_tong_hop(self):
        ok, err = onebee_ai_rag.kiem_tra_pii_tom_tat({
            "ky_bao_cao": "2026-10",
            "tong_don_hang": 142,
            "doanh_thu_trieu": 512.8,
            "phan_loai": [{"nhom": "Nông sản", "so_luong": 80}],
        })
        self.assertTrue(ok, err)
        self.assertIsNone(err)

    def test_tu_choi_truong_hoac_chuoi_chua_pii(self):
        for payload in (
            {"ho_ten": "Nguyễn Văn An", "tong": 10},
            {"ten_khach_hang": "Cô Ba"},
            {"ghi_chu": "Liên hệ mail an@htx.vn gấp"},
            {"chi_tiet": ["SĐT khách: 0912345678"]},
            {"thong_ke": {"ma": "CCCD 079200012345"}},
        ):
            ok, err = onebee_ai_rag.kiem_tra_pii_tom_tat(payload)
            self.assertFalse(ok, f"Đáng lẽ phải chặn: {payload}")
            self.assertTrue(err)


class TestCliKhoaVaMatKhau(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        self.secrets = os.path.join(self.tmp.name, "secrets")
        os.makedirs(self.data)
        os.makedirs(self.secrets)

    def test_cap_lay_xoay_xoa_khoa_va_khong_luu_tho(self):
        with _EnvTam(ONEBEE_AI_DATA=self.data, ONEBEE_SECRETS=self.secrets):
            k1 = onebee_ai_rag._cap_hoac_xoay_khoa("ketoan-01", xoay=False)
            self.assertTrue(k1.startswith("sk-ob-"))
            with open(os.path.join(self.secrets, "ai-tokens.json"), encoding="utf-8") as f:
                tokens_raw = f.read()
            self.assertNotIn(k1, tokens_raw)  # chỉ lưu SHA-256

            # Mô phỏng onebee-box ghi file bí mật máy trạm
            with open(os.path.join(self.secrets, "may-ketoan-01-hoi"), "w", encoding="utf-8") as f:
                f.write(k1 + "\n")
            self.assertEqual(onebee_ai_rag._cap_hoac_xoay_khoa("ketoan-01", xoay=False), k1)  # idempotent
            self.assertEqual(onebee_ai_rag.lay_khoa("ketoan-01"), k1)
            self.assertEqual(onebee_ai_rag.xac_thuc_bearer_token(k1)["email"], "may-ketoan-01@onebee.lan")

            # Xoay khóa -> khóa cũ hết hiệu lực ngay
            k2 = onebee_ai_rag._cap_hoac_xoay_khoa("ketoan-01", xoay=True)
            self.assertNotEqual(k1, k2)
            self.assertIsNone(onebee_ai_rag.xac_thuc_bearer_token(k1))
            self.assertEqual(onebee_ai_rag.xac_thuc_bearer_token(k2)["email"], "may-ketoan-01@onebee.lan")

            # Xóa tài khoản -> vô hiệu hóa & idempotent
            onebee_ai_rag.xoa_tai_khoan("ketoan-01")
            onebee_ai_rag.xoa_tai_khoan("ketoan-01")
            self.assertIsNone(onebee_ai_rag.xac_thuc_bearer_token(k2))

    def test_doi_mat_khau_quan_tri(self):
        with _EnvTam(ONEBEE_AI_DATA=self.data, ONEBEE_SECRETS=self.secrets, AI_ADMIN_PASSWORD="", AI_ADMIN_PASSWORD_FILE=""):
            os.environ.pop("AI_ADMIN_PASSWORD", None)
            os.environ.pop("AI_ADMIN_PASSWORD_FILE", None)
            onebee_ai_rag.doi_mat_khau_quan_tri("MatKhauMoi2026")
            pw_file = os.path.join(self.secrets, "ai-admin-password")
            with open(pw_file, encoding="utf-8") as f:
                self.assertEqual(f.read(), "MatKhauMoi2026")
            self.assertEqual(stat.S_IMODE(os.stat(pw_file).st_mode), 0o600)
            self.assertIsNotNone(onebee_ai_rag.xac_thuc_tai_khoan("quantri@onebee.lan", "MatKhauMoi2026"))
            self.assertIsNone(onebee_ai_rag.xac_thuc_tai_khoan("quantri@onebee.lan", "SaiMatKhau"))

            with self.assertRaises(SystemExit):
                onebee_ai_rag.doi_mat_khau_quan_tri("ngan")

    def test_cli_chay_subcommand(self):
        env = dict(os.environ, ONEBEE_AI_DATA=self.data, ONEBEE_SECRETS=self.secrets)
        r = subprocess.run([sys.executable, AI_RAG_PY, "cap-khoa", "vanphong-01"], env=env, capture_output=True, text=True, check=True)
        self.assertTrue(r.stdout.strip().startswith("sk-ob-"))


class TestHttpDichVuVaBaoMat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = os.path.join(cls.tmp.name, "data")
        cls.secrets = os.path.join(cls.tmp.name, "secrets")
        os.makedirs(cls.data)
        os.makedirs(cls.secrets)
        with open(os.path.join(cls.secrets, "ai-admin-password"), "w", encoding="utf-8") as f:
            f.write("QuanTriTest2026")
        with open(os.path.join(cls.secrets, "ai-secret-key"), "w", encoding="utf-8") as f:
            f.write("BiMatTestKhongDeLo0123456789ABCDEF")

        cls.ollama_calls = []

        class MockOllama(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/version":
                    body = b'{"version":"0.6.0"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(n).decode("utf-8"))
                cls.ollama_calls.append(payload)
                sys_msg = payload["messages"][0]["content"]
                has_rag = "TÀI LIỆU THAM KHẢO NỘI BỘ" in sys_msg
                body = json.dumps({
                    "message": {
                        "role": "assistant",
                        "content": f"Trả lời nội bộ (RAG={has_rag}): Theo Nghị định 30/2020/NĐ-CP.",
                    }
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.ollama_sv = ThreadingHTTPServer(("127.0.0.1", 0), MockOllama)
        threading.Thread(target=cls.ollama_sv.serve_forever, daemon=True).start()

        cls.env_ctx = _EnvTam(
            ONEBEE_AI_DATA=cls.data,
            ONEBEE_SECRETS=cls.secrets,
            ONEBEE_PROMPTS_DIR=PROMPTS_DIR,
            ONEBEE_KNOWLEDGE_DIRS=KNOWLEDGE_DIR,
            ONEBEE_LOI_DAN=os.path.join(AI_FILES, "tro-ly-onebee-loi-dan.md"),
            ONEBEE_GOI_Y=os.path.join(AI_FILES, "goi-y.json"),
            OLLAMA_URL=f"http://127.0.0.1:{cls.ollama_sv.server_port}",
            CORS_ALLOW_ORIGIN="http://192.168.1.10:3000;https://box.kiem-thu.onebee.internal",
            AI_SESSION_COOKIE_SECURE="true",
            AI_ADMIN_PASSWORD="",
            AI_ADMIN_PASSWORD_FILE="",
            AI_RAG_SECRET_KEY="",
            AI_SECRET_KEY_FILE="",
        )
        cls.env_ctx.__enter__()
        os.environ.pop("AI_ADMIN_PASSWORD", None)
        os.environ.pop("AI_RAG_SECRET_KEY", None)
        onebee_ai_rag.dong_bo_tri_thuc()

        cls.sv = ThreadingHTTPServer(("127.0.0.1", 0), onebee_ai_rag.OneBeeAiHandler)
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.sv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown()
        cls.sv.server_close()
        cls.ollama_sv.shutdown()
        cls.ollama_sv.server_close()
        cls.env_ctx.__exit__(None, None, None)
        cls.tmp.cleanup()

    def req(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode("utf-8") if isinstance(body, (dict, list)) else body
        hdrs = dict(headers or {})
        if isinstance(body, (dict, list)) and "Content-Type" not in hdrs:
            hdrs["Content-Type"] = "application/json"
        r = urllib.request.Request(self.base + path, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, dict(resp.headers), resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf-8")

    def test_health_va_giao_dien_html_an_toan(self):
        st, _, txt = self.req("GET", "/ai/health")
        self.assertEqual(st, 200)
        d = json.loads(txt)
        self.assertEqual(d["service"], "onebee-ai-rag")
        self.assertTrue(d["ollama"])
        self.assertGreaterEqual(d["knowledge_chunks"], 4)

        st, _, cfg = self.req("GET", "/api/config")
        self.assertEqual(st, 200)
        self.assertIs(json.loads(cfg)["signup_enabled"], False)

        st, _, html_ui = self.req("GET", "/ai?q=Soan+to+trinh")
        self.assertEqual(st, 200)
        self.assertIn("Trợ lý AI", html_ui)
        self.assertIn(onebee_ai_rag.NHAC_KIEM_TRA, html_ui)
        self.assertIn("URLSearchParams", html_ui)
        self.assertNotIn("innerHTML", html_ui)
        self.assertNotIn("cdn.", html_ui)

    def test_chan_chua_xac_thuc_gia_mao_sso_va_signup(self):
        st, _, _ = self.req("POST", "/api/v1/auths/signup", {"email": "a@b.c", "password": "x"})
        self.assertEqual(st, 403)
        for path in ("/ai/mau", "/api/models"):
            self.assertEqual(self.req("GET", path)[0], 401)
            # Giả mạo Remote-User khi không có X-OneBee-SSO=1 từ Caddy phải bị chặn
            self.assertEqual(self.req("GET", path, headers={"Remote-User": "quanly"})[0], 401)
        for path in ("/ai/hoi", "/ai/tom-tat", "/api/chat/completions"):
            self.assertEqual(self.req("POST", path, {"cau_hoi": "hi"})[0], 401)

    def test_dang_nhap_cookie_secure_api_key_rag_va_tom_tat(self):
        self.assertEqual(self.req("POST", "/api/v1/auths/signin", {"email": "quantri@onebee.lan", "password": "sai"})[0], 400)

        st, hdrs, txt = self.req("POST", "/api/v1/auths/signin", {"email": "quantri@onebee.lan", "password": "QuanTriTest2026"})
        self.assertEqual(st, 200)
        self.assertIn("HttpOnly", hdrs.get("Set-Cookie", ""))
        self.assertIn("Secure", hdrs.get("Set-Cookie", ""))
        sess_tok = json.loads(txt)["token"]

        # Cấp API key qua phiên đăng nhập
        st, _, key_txt = self.req("POST", "/api/v1/auths/api_key", {}, headers={"Authorization": f"Bearer {sess_tok}"})
        self.assertEqual(st, 200)
        api_key = json.loads(key_txt)["api_key"]
        auth = {"Authorization": f"Bearer {api_key}"}

        self.assertEqual(self.req("GET", "/api/v1/auths/api_key", headers=auth)[0], 200)
        self.assertEqual(self.req("GET", "/api/models", headers=auth)[0], 200)

        st, _, mau_txt = self.req("GET", "/ai/mau", headers=auth)
        self.assertEqual(st, 200)
        self.assertEqual(len(json.loads(mau_txt)["prompts"]), 4)

        # Hỏi đáp RAG có trích dẫn nguồn + dòng nhắc kiểm tra
        self.ollama_calls.clear()
        st, _, hoi_txt = self.req("POST", "/ai/hoi", {"cau_hoi": "Khổ giấy A4 theo Nghị định 30?"}, headers=auth)
        self.assertEqual(st, 200)
        hoi_res = json.loads(hoi_txt)
        self.assertIn("RAG=True", hoi_res["tra_loi"])
        self.assertTrue(hoi_res["nguon"])
        self.assertEqual(hoi_res["nhac_kiem_tra"], onebee_ai_rag.NHAC_KIEM_TRA)

        # Chat completions tương thích CLI `hoi`
        st, _, cc_txt = self.req(
            "POST",
            "/api/chat/completions",
            {"model": "onebee-tro-ly", "messages": [{"role": "user", "content": "Luật HTX 2023"}]},
            headers=auth,
        )
        self.assertEqual(st, 200)
        self.assertIn("choices", json.loads(cc_txt))

        # Tóm tắt số liệu chặn PII, cho phép tổng hợp
        st, _, _ = self.req("POST", "/ai/tom-tat", {"ho_ten": "Nguyễn Văn B", "tong": 2}, headers=auth)
        self.assertEqual(st, 400)
        st, _, tt_txt = self.req("POST", "/ai/tom-tat", {"thang": "10/2026", "so_don": 88}, headers=auth)
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(tt_txt)["nhac_kiem_tra"], onebee_ai_rag.NHAC_KIEM_TRA)

    def test_sso_trusted_cors_va_gioi_han_kich_thuoc(self):
        # X-OneBee-SSO=1 + Remote-User hợp lệ -> lấy danh sách mẫu được
        st, _, _ = self.req("GET", "/ai/mau", headers={"X-OneBee-SSO": "1", "Remote-User": "binh", "Remote-Groups": "nhan_vien"})
        self.assertEqual(st, 200)

        # Nhân viên thường không được tạo user
        st, _, _ = self.req(
            "POST",
            "/api/v1/auths/add",
            {"email": "moi@onebee.lan", "password": "MatKhauDuDai1"},
            headers={"X-OneBee-SSO": "1", "Remote-User": "binh", "Remote-Groups": "nhan_vien"},
        )
        self.assertEqual(st, 403)

        # Origin hợp lệ được CORS, Origin lạ không có header CORS
        st, hdrs_ok, _ = self.req("GET", "/api/config", headers={"Origin": "http://192.168.1.10:3000"})
        self.assertEqual(st, 200)
        self.assertEqual(hdrs_ok.get("Access-Control-Allow-Origin"), "http://192.168.1.10:3000")

        st, hdrs_bad, _ = self.req("GET", "/api/config", headers={"Origin": "https://evil.example"})
        self.assertEqual(st, 200)
        self.assertIsNone(hdrs_bad.get("Access-Control-Allow-Origin"))

        # Payload vượt 1 MB -> 413 (dùng HTTPConnection kiểm header Content-Length)
        conn = http.client.HTTPConnection("127.0.0.1", self.sv.server_port, timeout=10)
        conn.putrequest("POST", "/ai/hoi")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(1024 * 1024 + 50))
        conn.endheaders()
        resp = conn.getresponse()
        self.assertEqual(resp.status, 413)
        conn.close()


class TestLoiDanVaCauHinh(unittest.TestCase):
    def test_nap_loi_dan_thay_ngay_hom_nay(self):
        with _EnvTam(ONEBEE_LOI_DAN=os.path.join(AI_FILES, "tro-ly-onebee-loi-dan.md")):
            nd = onebee_ai_rag.nap_loi_dan()
        self.assertIn("Trợ lý OneBee", nd)
        self.assertNotIn("{{CURRENT_DATE}}", nd)
        self.assertIn(date.today().strftime("%d/%m/%Y"), nd)

    def test_loi_dan_huong_dan_pdf_bang_libreoffice(self):
        with open(os.path.join(AI_FILES, "tro-ly-onebee-loi-dan.md"), encoding="utf-8") as f:
            nd = f.read()
        self.assertIn("PDF", nd)
        self.assertIn("LibreOffice", nd)


if __name__ == "__main__":
    unittest.main()
