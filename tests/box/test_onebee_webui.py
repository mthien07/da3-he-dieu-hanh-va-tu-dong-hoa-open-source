#!/usr/bin/env python3
"""Kiểm thử đơn vị cho công cụ quản lý Open WebUI (box-ai/files/onebee-webui.py) bằng máy chủ Open WebUI giả.
Kiểm: enforce_settings đặt đúng cài đặt bảo mật + quyền mặc định, chạy lần 2 không đổi gì. Chạy: python3 -m unittest"""
import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DUONG_DAN = os.path.join(HERE, "../../box/ansible/roles/box-ai/files/onebee-webui.py")


class WebuiGia(BaseHTTPRequestHandler):
    """Giống phần API quản trị của Open WebUI v0.11.4 mà onebee-webui.py gọi (đọc mã nguồn routers/auths.py, users.py)."""
    state = {}

    def log_message(self, *a):
        pass

    def _gui(self, ma, du_lieu):
        raw = json.dumps(du_lieu).encode()
        self.send_response(ma)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/v1/auths/admin/config":
            return self._gui(200, self.state["config"])
        if self.path == "/api/v1/users/default/permissions":
            return self._gui(200, self.state["perms"])
        self._gui(404, {"detail": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        self.state.setdefault("posts", []).append(self.path)
        if self.path == "/api/v1/auths/admin/config":
            # Open WebUI từ chối giá trị null cho các trường bắt buộc
            if any(v is None for k, v in body.items() if k not in ("ADMIN_EMAIL", "I18N", "DEFAULT_INTERFACE_SETTINGS")):
                return self._gui(422, {"detail": "null"})
            self.state["config"] = body
            return self._gui(200, body)
        if self.path == "/api/v1/users/default/permissions":
            self.state["perms"] = body
            return self._gui(200, body)
        self._gui(404, {"detail": "not found"})


class EnforceSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), WebuiGia)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        os.environ["WEBUI_URL"] = f"http://127.0.0.1:{cls.server.server_port}"
        spec = importlib.util.spec_from_file_location("onebee_webui", DUONG_DAN)
        cls.w = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.w)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        # Trạng thái mặc định của một Open WebUI mới cài (khớp mặc định trong mã nguồn v0.11.4)
        WebuiGia.state = {
            "config": {"ENABLE_SIGNUP": True, "ENABLE_API_KEYS": False, "ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS": False,
                       "API_KEYS_ALLOWED_ENDPOINTS": "", "ENABLE_COMMUNITY_SHARING": True, "JWT_EXPIRES_IN": "4w",
                       "WEBUI_URL": "", "I18N": None},
            "perms": {"features": {"api_keys": False, "web_search": True}, "chat": {"share": True, "export": True}},
        }

    def test_ap_dung_cai_dat_bao_mat_va_quyen_mac_dinh(self):
        self.assertTrue(self.w.enforce_settings("tok"))
        cfg, perms = WebuiGia.state["config"], WebuiGia.state["perms"]
        self.assertFalse(cfg["ENABLE_SIGNUP"])
        self.assertTrue(cfg["ENABLE_API_KEYS"])
        self.assertTrue(cfg["ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS"])
        self.assertEqual(cfg["API_KEYS_ALLOWED_ENDPOINTS"], "/api/chat/completions,/api/models")
        self.assertFalse(cfg["ENABLE_COMMUNITY_SHARING"])
        self.assertEqual(cfg["JWT_EXPIRES_IN"], "30d")
        self.assertTrue(perms["features"]["api_keys"])      # nhân viên tạo được khóa API cho lệnh hoi
        self.assertFalse(perms["chat"]["share"])             # nhưng không chia sẻ chat
        self.assertTrue(perms["features"]["web_search"])     # không đụng quyền khác
        self.assertTrue(perms["chat"]["export"])

    def test_chay_lan_2_khong_doi_gi(self):
        self.assertTrue(self.w.enforce_settings("tok"))
        WebuiGia.state["posts"] = []
        self.assertFalse(self.w.enforce_settings("tok"))
        self.assertEqual(WebuiGia.state["posts"], [])  # không ghi gì → bộ cài ra changed=0

    def test_chi_quyen_mac_dinh_lech(self):
        self.w.enforce_settings("tok")
        WebuiGia.state["posts"] = []
        WebuiGia.state["perms"]["chat"]["share"] = True  # ai đó bật lại trên giao diện
        self.assertTrue(self.w.enforce_settings("tok"))
        self.assertEqual(WebuiGia.state["posts"], ["/api/v1/users/default/permissions"])
        self.assertFalse(WebuiGia.state["perms"]["chat"]["share"])

    def test_loi_doc_quyen_thi_dung_khong_bo_qua(self):
        WebuiGia.state["perms"] = None
        orig = WebuiGia.do_GET

        def get_loi(self_):
            if self_.path == "/api/v1/users/default/permissions":
                return self_._gui(500, {"detail": "loi"})
            return orig(self_)
        WebuiGia.do_GET = get_loi
        try:
            with self.assertRaises(SystemExit):
                self.w.enforce_settings("tok")
        finally:
            WebuiGia.do_GET = orig


if __name__ == "__main__":
    unittest.main()
