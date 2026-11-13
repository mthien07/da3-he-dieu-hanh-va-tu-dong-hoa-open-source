#!/usr/bin/env python3
"""Kiểm thử đơn vị cho công cụ quản lý Open WebUI (box-ai/files/onebee-webui.py) bằng máy chủ Open WebUI giả.
Kiểm: enforce_settings đặt đúng cài đặt bảo mật + quyền mặc định + bản dịch giao diện tiếng Việt bổ sung, chạy lần 2 không đổi gì. Chạy: python3 -m unittest"""
import importlib.util
import io
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.parse
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DUONG_DAN = os.path.join(HERE, "../../box/ansible/roles/box-ai/files/onebee-webui.py")


def bien_noi_suy(chu):
    return {m.strip() for m in re.findall(r"\{\{\s*-?\s*([^},]+)(?:,[^}]+)?\s*\}\}", chu)}


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
        if self.path.startswith("/api/v1/users/?query="):
            q = self.path.split("=", 1)[1].replace("%40", "@")
            return self._gui(200, {"users": [u for u in self.state.get("users", []) if q in u["email"]]})
        if self.path == "/api/v1/auths/api_key":
            khoa = self.state.get("khoa", {}).get(self.headers.get("Authorization", "").replace("Bearer ", ""))
            return self._gui(200, {"api_key": khoa}) if khoa else self._gui(404, {"detail": "none"})
        if self.path.startswith("/api/v1/models/model?id="):
            mid = urllib.parse.unquote(self.path.split("?id=", 1)[1])
            m = self.state.get("models", {}).get(mid)
            return self._gui(200, m) if m else self._gui(404, {"detail": "not found"})
        if self.path == "/api/v1/prompts/":
            return self._gui(200, list(self.state.get("prompts", {}).values()))
        if self.path == "/api/v1/configs/banners":
            return self._gui(200, self.state.get("banners", []))
        self._gui(404, {"detail": "not found"})

    def do_DELETE(self):
        self.state.setdefault("posts", []).append("DELETE " + self.path)
        uid = self.path.rsplit("/", 1)[1]
        self.state["users"] = [u for u in self.state.get("users", []) if u["id"] != uid]
        self._gui(200, True)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        self.state.setdefault("posts", []).append(self.path)
        if self.path == "/api/v1/auths/signin":
            mk = self.state.get("mat_khau", {}).get(body.get("email"))
            if mk and mk == body.get("password"):
                return self._gui(200, {"token": "tok-" + body["email"]})
            return self._gui(400, {"detail": "sai"})
        if self.path == "/api/v1/auths/admin/config":
            # Open WebUI từ chối giá trị null cho các trường bắt buộc
            if any(v is None for k, v in body.items() if k not in ("ADMIN_EMAIL", "I18N", "DEFAULT_INTERFACE_SETTINGS")):
                return self._gui(422, {"detail": "null"})
            # Như AdminConfig.validate_i18n + update_admin_config của v0.11.4 (routers/auths.py): không gửi I18N thì giữ
            # bản đang lưu; gửi null thì 422; bản dịch rỗng bị bỏ; {{biến}} của khóa và bản dịch phải khớp
            if "I18N" not in body:
                body["I18N"] = (self.state.get("config") or {}).get("I18N")
            else:
                if not isinstance(body["I18N"], dict):
                    return self._gui(422, {"detail": "I18N must be a dictionary"})
                sach = {}
                for loc, muc in body["I18N"].items():
                    giu = {}
                    for khoa, chu in muc.items():
                        if not isinstance(chu, str):
                            return self._gui(422, {"detail": "StrictStr"})
                        if chu.strip():
                            if bien_noi_suy(khoa) != bien_noi_suy(chu):
                                return self._gui(422, {"detail": "Interpolation placeholders do not match"})
                            giu[khoa] = chu
                    if giu:
                        sach[loc] = giu
                body["I18N"] = sach
            self.state["config"] = body
            return self._gui(200, body)
        if self.path == "/api/v1/users/default/permissions":
            self.state["perms"] = body
            return self._gui(200, body)
        if self.path == "/api/v1/auths/api_key":   # tạo lại khóa: khóa cũ mất hiệu lực
            email = self.headers.get("Authorization", "").replace("Bearer tok-", "")
            moi = f"sk-moi-{len(self.state.setdefault('khoa_da_cap', []))}"
            self.state["khoa_da_cap"].append(moi)
            self.state.setdefault("khoa", {})["tok-" + email] = moi
            return self._gui(200, {"api_key": moi})
        if self.path == "/api/v1/auths/update/password":
            email = self.headers.get("Authorization", "").replace("Bearer tok-", "")
            if self.state.get("mat_khau", {}).get(email) != body.get("password"):
                return self._gui(400, {"detail": "sai"})
            self.state["mat_khau"][email] = body["new_password"]
            return self._gui(200, True)
        if self.path == "/api/v1/models/create" or self.path.startswith("/api/v1/models/model/update"):
            self.state.setdefault("models", {})[body["id"]] = body
            return self._gui(200, body)
        if self.path == "/api/v1/prompts/create":
            prompts = self.state.setdefault("prompts", {})
            rec = {"id": f"p-{len(prompts)}", **body}
            prompts[body["command"]] = rec
            return self._gui(200, rec)
        if self.path.startswith("/api/v1/prompts/id/") and self.path.endswith("/update"):
            prompts = self.state.setdefault("prompts", {})
            pid = self.path.split("/")[5]
            rec = {"id": pid, **body}
            prompts[body["command"]] = rec
            return self._gui(200, rec)
        if self.path == "/api/v1/configs/banners":
            # Như BannerModel của v0.11.4 (config.py): lưu qua pydantic nên GET trả thêm trường mặc định i18n=None
            self.state["banners"] = [{"i18n": b.get("i18n"), "id": b["id"], "type": b["type"], "title": b.get("title"),
                                      "content": b["content"], "dismissible": b["dismissible"],
                                      "timestamp": b["timestamp"]} for b in body["banners"]]
            return self._gui(200, self.state["banners"])
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

    def test_dat_va_go_dia_chi_cong_khai_khi_bat_tat_https(self):
        try:
            os.environ["ONEBEE_WEBUI_PUBLIC_URL"] = "https://192.168.1.10:3000"
            self.assertTrue(self.w.enforce_settings("tok"))
            self.assertEqual(WebuiGia.state["config"]["WEBUI_URL"], "https://192.168.1.10:3000")
            self.assertFalse(self.w.enforce_settings("tok"))      # chạy lại không đổi
            os.environ["ONEBEE_WEBUI_PUBLIC_URL"] = ""            # hoàn tác HTTPS
            self.assertTrue(self.w.enforce_settings("tok"))
            self.assertEqual(WebuiGia.state["config"]["WEBUI_URL"], "")
        finally:
            os.environ.pop("ONEBEE_WEBUI_PUBLIC_URL", None)

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

    def test_tep_goi_y_hop_le(self):
        with open(self.w.GOI_Y, encoding="utf-8") as f:
            ds = json.load(f)
        self.assertIsInstance(ds, list)
        self.assertIn(len(ds), (3, 4))
        for muc in ds:
            self.assertIsInstance(muc.get("title"), list)
            self.assertIn(len(muc["title"]), (1, 2))
            self.assertTrue(all(isinstance(s, str) and s.strip() for s in muc["title"]))
            self.assertTrue(isinstance(muc.get("content"), str) and muc["content"].strip())

    def test_tro_ly_mang_goi_y_va_chay_lai_khong_doi(self):
        WebuiGia.state["mat_khau"] = {"quantri@onebee.lan": "admin-mk"}
        with open(self.w.GOI_Y, encoding="utf-8") as f:
            mong_doi = json.load(f)
        loi_dan = os.path.join(HERE, "../../box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md")
        try:
            os.environ["WEBUI_ADMIN_EMAIL"] = "quantri@onebee.lan"
            os.environ["WEBUI_ADMIN_PASSWORD"] = "admin-mk"
            os.environ["ONEBEE_AI_MODEL"] = "gemma4:e2b-it-qat"
            os.environ["ONEBEE_LOI_DAN"] = loi_dan
            with redirect_stdout(io.StringIO()):
                self.w.dong_bo_tro_ly()
            m = WebuiGia.state.get("models", {}).get("onebee-tro-ly")
            self.assertIsNotNone(m)
            self.assertEqual(m["meta"].get("suggestion_prompts"), mong_doi)
            WebuiGia.state["posts"] = []
            with redirect_stdout(io.StringIO()):
                self.w.dong_bo_tro_ly()
            model_posts = [p for p in WebuiGia.state["posts"] if "models/model/update" in p or "models/create" in p]
            self.assertEqual(model_posts, [])
        finally:
            for k in ("WEBUI_ADMIN_EMAIL", "WEBUI_ADMIN_PASSWORD", "ONEBEE_AI_MODEL", "ONEBEE_LOI_DAN"):
                os.environ.pop(k, None)

    def test_mac_dinh_chen_goi_y_vao_o_nhap_va_giu_cai_dat_khac(self):
        WebuiGia.state["config"]["DEFAULT_INTERFACE_SETTINGS"] = {"chatDirection": "auto"}
        self.assertTrue(self.w.enforce_settings("tok"))
        self.assertEqual(
            WebuiGia.state["config"].get("DEFAULT_INTERFACE_SETTINGS"),
            {"chatDirection": "auto", "insertSuggestionPrompt": True},
        )

    def test_tep_giao_dien_tieng_viet_hop_le(self):
        with open(self.w.GIAO_DIEN, encoding="utf-8") as f:
            bd = json.load(f)
        self.assertEqual(list(bd), ["vi-VN"])            # chỉ bổ sung bản dịch tiếng Việt
        self.assertTrue(bd["vi-VN"])
        for khoa, chu in bd["vi-VN"].items():
            self.assertTrue(isinstance(khoa, str) and khoa.strip() and khoa not in ("__proto__", "prototype", "constructor"))
            self.assertTrue(isinstance(chu, str) and chu.strip(), khoa)
            self.assertNotEqual(chu, khoa)
            self.assertEqual(bien_noi_suy(khoa), bien_noi_suy(chu), khoa)

    def test_gui_ban_dich_giao_dien_va_chay_lai_khong_doi(self):
        with open(self.w.GIAO_DIEN, encoding="utf-8") as f:
            bd = json.load(f)
        self.assertTrue(self.w.enforce_settings("tok"))
        self.assertEqual(WebuiGia.state["config"]["I18N"], bd)
        self.assertFalse(WebuiGia.state["config"]["ENABLE_SIGNUP"])     # vẫn gửi đủ cài đặt bảo mật cùng lần
        WebuiGia.state["posts"] = []
        self.assertFalse(self.w.enforce_settings("tok"))
        self.assertEqual(WebuiGia.state["posts"], [])

    def test_giu_ban_dich_quan_tri_tu_them_va_sua_lai_ban_dich_bi_doi(self):
        with open(self.w.GIAO_DIEN, encoding="utf-8") as f:
            bd = json.load(f)["vi-VN"]
        khoa = sorted(bd)[0]
        WebuiGia.state["config"]["I18N"] = {"vi-VN": {"Library": "Thư viện", khoa: "bị sửa trên giao diện"},
                                            "fr-FR": {"Library": "Bibliothèque"}}
        self.assertTrue(self.w.enforce_settings("tok"))
        luu = WebuiGia.state["config"]["I18N"]
        self.assertEqual(luu["vi-VN"], {"Library": "Thư viện", **bd})
        self.assertEqual(luu["fr-FR"], {"Library": "Bibliothèque"})
        WebuiGia.state["posts"] = []
        self.assertFalse(self.w.enforce_settings("tok"))
        self.assertEqual(WebuiGia.state["posts"], [])

    def test_thieu_tep_giao_dien_thi_dung_ro_rang(self):
        cu = self.w.GIAO_DIEN
        self.w.GIAO_DIEN = os.path.join(tempfile.gettempdir(), "khong-co-giao-dien-tieng-viet.json")
        try:
            with self.assertRaises(SystemExit) as loi:
                self.w.enforce_settings("tok")
            self.assertIn("giao-dien-tieng-viet", str(loi.exception.code))
        finally:
            self.w.GIAO_DIEN = cu
        self.assertNotIn("/api/v1/auths/admin/config", WebuiGia.state.get("posts", []))

    def test_ansible_cai_tep_giao_dien_canh_cong_cu(self):
        with open(os.path.join(HERE, "../../box/ansible/roles/box-ai/tasks/main.yml"), encoding="utf-8") as f:
            tasks = yaml.safe_load(f)
        cai = next(t for t in tasks if t.get("name") == "Cài lời dặn và công cụ quản lý Open WebUI")
        self.assertEqual(cai["ansible.builtin.copy"]["dest"], "/usr/local/lib/onebee-box/{{ item.src }}")
        self.assertIn("giao-dien-tieng-viet.json", [m["src"] for m in cai["loop"]])
        self.assertEqual(os.path.basename(self.w.GIAO_DIEN), "giao-dien-tieng-viet.json")

    def test_bang_nhac_them_mot_lan_va_giu_bang_cua_quan_tri(self):
        khac = {
            "id": "khac",
            "type": "info",
            "title": "",
            "content": "Thông báo của quản trị",
            "dismissible": True,
            "timestamp": 1700000000,
        }
        WebuiGia.state["banners"] = [khac]
        WebuiGia.state["posts"] = []
        with redirect_stdout(io.StringIO()):
            self.w.dong_bo_bang_nhac("tok")
        self.assertEqual(WebuiGia.state["posts"], ["/api/v1/configs/banners"])
        self.assertEqual([b["id"] for b in WebuiGia.state["banners"]], ["khac", self.w.BANG_NHAC["id"]])
        self.assertEqual(WebuiGia.state["banners"][0]["content"], khac["content"])
        luu = WebuiGia.state["banners"][1]
        self.assertEqual({k: luu[k] for k in self.w.BANG_NHAC}, self.w.BANG_NHAC)
        WebuiGia.state["posts"] = []   # lần 2: Open WebUI trả băng có thêm i18n=None → vẫn phải coi là không đổi
        with redirect_stdout(io.StringIO()):
            self.w.dong_bo_bang_nhac("tok")
        self.assertEqual(WebuiGia.state["posts"], [])


class TaiKhoanMay(unittest.TestCase):
    """lay-khoa (chỉ đọc) và xoa-tai-khoan (thu hồi máy) — rà soát bảo mật F2: thu hồi/in lại cấu hình không có tác dụng phụ."""

    @classmethod
    def setUpClass(cls):
        EnforceSettings.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["ONEBEE_SECRETS"] = self.tmp.name
        os.environ["WEBUI_ADMIN_EMAIL"], os.environ["WEBUI_ADMIN_PASSWORD"] = "quantri@onebee.lan", "admin-mk"
        WebuiGia.state = {"mat_khau": {"quantri@onebee.lan": "admin-mk", "may-a@onebee.lan": "mk-may-a"},
                          "khoa": {"tok-may-a@onebee.lan": "sk-khoa-a"},
                          "users": [{"id": "u1", "email": "may-a@onebee.lan"}, {"id": "u2", "email": "nv@onebee.lan"}]}

    def ghi_mk(self, ten, mk):
        with open(os.path.join(self.tmp.name, f"may-{ten}-webui"), "w") as f:
            f.write(mk + "\n")

    def ghi_gi(self):
        """Các lời gọi làm thay đổi dữ liệu (bỏ đăng nhập)."""
        return [p for p in WebuiGia.state.get("posts", []) if p != "/api/v1/auths/signin"]

    def chay(self, ham, *a):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ham(*a)
        return buf.getvalue().strip()

    def test_lay_khoa_in_khoa_da_co_va_khong_tao_gi(self):
        self.ghi_mk("a", "mk-may-a")
        self.assertEqual(self.chay(self.w.lay_khoa, "a"), "sk-khoa-a")
        self.assertEqual(self.ghi_gi(), [])  # chỉ đăng nhập + đọc, không tạo/xóa gì

    def test_lay_khoa_thieu_gi_thi_dung(self):
        with self.assertRaises(SystemExit):
            self.w.lay_khoa("a")  # chưa có file mật khẩu → không tự tạo tài khoản
        self.ghi_mk("a", "sai-mat-khau")
        with self.assertRaises(SystemExit):
            self.w.lay_khoa("a")
        self.assertEqual(self.ghi_gi(), [])
        self.ghi_mk("a", "mk-may-a")
        WebuiGia.state["khoa"] = {}
        with self.assertRaises(SystemExit):
            self.w.lay_khoa("a")  # có tài khoản nhưng chưa có khóa → không tạo khóa

    def test_xoay_khoa_doi_khoa_va_khong_tao_tai_khoan(self):
        self.ghi_mk("a", "mk-may-a")
        moi = self.chay(self.w.xoay_khoa, "a")
        self.assertEqual(moi, "sk-moi-0")
        self.assertEqual(self.chay(self.w.lay_khoa, "a"), "sk-moi-0")                 # khóa đọc lại là khóa mới
        self.assertEqual([p for p in self.ghi_gi() if "add" in p or "DELETE" in p], [])
        with self.assertRaises(SystemExit):
            self.w.xoay_khoa("khong-co")                                                  # chưa có tài khoản → không tự tạo

    def test_doi_mat_khau_quan_tri_doi_trong_csdl(self):
        try:
            os.environ["ONEBEE_MAT_KHAU_MOI"] = "Mat-Khau-Moi-123456"
            self.chay(self.w.doi_mat_khau_quan_tri)
            self.assertEqual(WebuiGia.state["mat_khau"]["quantri@onebee.lan"], "Mat-Khau-Moi-123456")
            os.environ["ONEBEE_MAT_KHAU_MOI"] = "ngan"
            with self.assertRaises(SystemExit):
                self.w.doi_mat_khau_quan_tri()                                            # quá ngắn → từ chối
        finally:
            os.environ.pop("ONEBEE_MAT_KHAU_MOI", None)

    def test_xoa_tai_khoan_chi_xoa_dung_tai_khoan_may(self):
        self.assertIn("Đã xóa", self.chay(self.w.xoa_tai_khoan, "a"))
        self.assertEqual([u["email"] for u in WebuiGia.state["users"]], ["nv@onebee.lan"])  # tài khoản nhân viên còn nguyên
        self.assertIn("Không có", self.chay(self.w.xoa_tai_khoan, "a"))  # chạy lại không lỗi


if __name__ == "__main__":
    unittest.main()
