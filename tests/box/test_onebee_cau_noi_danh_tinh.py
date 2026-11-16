#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử cầu nối danh tính (box-dinh-danh/files/onebee-cau-noi-danh-tinh.py): chạy THẬT bằng python3 trên một cổng tạm,
dịch vụ dữ liệu phía sau (PostgREST) là máy chủ HTTP giả ghi lại mọi yêu cầu nhận được. Cầu nối đứng sau Caddy forward_auth:
chỉ tin Remote-User/Remote-Groups (Caddy đã xóa bản do máy khách gửi), ký JWT 60 giây cho phía sau.
Chạy: python3 -m unittest"""
import base64
import hashlib
import hmac
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
CAU_NOI = os.path.join(ROOT, "box/ansible/roles/box-dinh-danh/files/onebee-cau-noi-danh-tinh.py")
BI_MAT = "0123456789abcdef" * 4   # 64 ký tự hex như bộ cài sinh
MOT_MB = 1024 * 1024


def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def b64giai(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class PhiaSau(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        self.nhan = []

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def xu_ly(self):
                n = int(self.headers.get("Content-Length") or 0)
                than = self.rfile.read(n) if n else b""
                sv.nhan.append({"method": self.command, "path": self.path, "headers": dict(self.headers), "body": than,
                                "all": self.headers})
                tl = json.dumps([{"chu_so_huu": "an"}]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Range", "0-0/*")
                self.send_header("Content-Length", str(len(tl)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(tl)
            do_GET = do_POST = do_PATCH = do_DELETE = do_HEAD = do_PUT = xu_ly
        sv = self
        super().__init__(("127.0.0.1", 0), H)
        threading.Thread(target=self.serve_forever, daemon=True).start()


class CauNoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.bi_mat_tep = os.path.join(cls.tmp.name, "cau-noi-jwt-secret")
        with open(cls.bi_mat_tep, "w") as f:
            f.write(BI_MAT + "\n")            # bộ cài Ansible (lookup password) ghi kèm xuống dòng
        cls.ps = PhiaSau()
        cls.cong = cong_trong()
        cls.nhat_ky = open(os.path.join(cls.tmp.name, "nhat-ky.txt"), "w+")
        cls.cn = subprocess.Popen([sys.executable, "-I", CAU_NOI], stdout=cls.nhat_ky, stderr=cls.nhat_ky,
                                  env={"PATH": os.environ.get("PATH", ""), "CAU_NOI_CONG": str(cls.cong),
                                       "CAU_NOI_DIA_CHI": "127.0.0.1",
                                       "CAU_NOI_PHIA_SAU": f"http://127.0.0.1:{cls.ps.server_port}",
                                       "CAU_NOI_JWT_SECRET_FILE": cls.bi_mat_tep})
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", cls.cong), 0.2).close()
                return
            except OSError:
                time.sleep(0.05)
        raise AssertionError("cầu nối không lên: " + open(cls.nhat_ky.name).read())

    @classmethod
    def tearDownClass(cls):
        cls.cn.terminate()
        cls.cn.wait(10)
        cls.ps.shutdown()
        cls.nhat_ky.close()
        cls.tmp.cleanup()

    def setUp(self):
        self.ps.nhan.clear()

    def goi(self, method="GET", path="/api/ghi_chu", headers=None, body=None, nguoi=("an", "nhan_vien")):
        h = dict(headers or {})
        if nguoi:
            h.setdefault("Remote-User", nguoi[0])
            h.setdefault("Remote-Groups", nguoi[1])
        c = http.client.HTTPConnection("127.0.0.1", self.cong, timeout=15)
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        than = r.read()
        c.close()
        return r.status, than, r

    def jwt(self):
        self.assertEqual(len(self.ps.nhan), 1)
        tieu_de = self.ps.nhan[0]["headers"]["Authorization"]
        self.assertTrue(tieu_de.startswith("Bearer "))
        return tieu_de[len("Bearer "):]

    def tai_jwt(self, jwt):
        dau, than, ky = jwt.split(".")
        return json.loads(b64giai(dau)), json.loads(b64giai(than)), ky

    # 1
    def test_thieu_remote_user_hoac_remote_groups_tra_401_khong_goi_phia_sau(self):
        for h in ({}, {"Remote-User": "an"}, {"Remote-Groups": "nhan_vien"}, {"Remote-User": "", "Remote-Groups": "nhan_vien"}):
            st, than, _ = self.goi(headers=h, nguoi=None)
            self.assertEqual(st, 401, h)
            self.assertIn("loi", json.loads(than))
        self.assertEqual(self.ps.nhan, [])

    def test_ten_nguoi_dung_la_hoac_trung_tieu_de_tra_401(self):
        for ten in ("An", "an binh", "../an", "a" * 40):
            self.assertEqual(self.goi(nguoi=(ten, "nhan_vien"))[0], 401, ten)
        # hai tiêu đề Remote-User (có thể một do máy khách chèn) → không đoán, từ chối
        c = http.client.HTTPConnection("127.0.0.1", self.cong, timeout=15)
        c.putrequest("GET", "/api/ghi_chu")
        for k, v in (("Remote-User", "an"), ("Remote-User", "binh"), ("Remote-Groups", "nhan_vien")):
            c.putheader(k, v)
        c.endheaders()
        self.assertEqual(c.getresponse().status, 401)
        c.close()
        self.assertEqual(self.ps.nhan, [])

    # 2
    def test_nhom_khong_thuoc_ba_nhom_tra_403(self):
        for nhom in ("admins", "", ",", "nhan_vienx", "quan-ly"):
            st, than, _ = self.goi(nguoi=("an", nhom))
            self.assertEqual(st, 403 if nhom else 401, nhom)
        self.assertEqual(self.ps.nhan, [])

    # 3
    def test_nhieu_nhom_chon_vai_tro_cao_nhat(self):
        for nhom, vai_tro in (("nhan_vien,quan_ly", "quan_ly"), ("ky_thuat, nhan_vien", "ky_thuat"),
                              ("nhan_vien,ky_thuat,quan_ly", "quan_ly"), ("la,nhan_vien", "nhan_vien"), ("ky_thuat", "ky_thuat")):
            self.ps.nhan.clear()
            self.assertEqual(self.goi(nguoi=("binh", nhom))[0], 200)
            self.assertEqual(self.tai_jwt(self.jwt())[1]["role"], vai_tro, nhom)

    # 4
    def test_jwt_hs256_dung_claim_song_toi_da_60_giay_kiem_duoc_bang_hmac(self):
        truoc = int(time.time())
        self.assertEqual(self.goi(nguoi=("an", "nhan_vien"))[0], 200)
        sau = int(time.time())
        jwt = self.jwt()
        dau, than, ky = self.tai_jwt(jwt)
        self.assertEqual(dau, {"alg": "HS256", "typ": "JWT"})
        self.assertEqual(set(than), {"role", "sub", "aud", "iat", "exp"})
        self.assertEqual((than["sub"], than["role"], than["aud"]), ("an", "nhan_vien", "onebee-api"))
        self.assertTrue(truoc <= than["iat"] <= sau)
        self.assertLessEqual(than["exp"] - than["iat"], 60)
        self.assertLessEqual(than["exp"], sau + 60)
        self.assertGreater(than["exp"], sau)
        phan_ky = jwt.rsplit(".", 1)[0].encode()
        mong = base64.urlsafe_b64encode(hmac.new(BI_MAT.encode(), phan_ky, hashlib.sha256).digest()).rstrip(b"=").decode()
        self.assertTrue(hmac.compare_digest(ky, mong))   # khóa đọc từ tệp, bỏ dấu xuống dòng ở cuối

    # 5
    def test_authorization_cookie_remote_cua_may_khach_khong_bao_gio_chuyen_tiep(self):
        gia = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJiaW5oIiwicm9sZSI6InF1YW5fbHkifQ.gia"
        st, than, r = self.goi("POST", "/api/ghi_chu?select=noi_dung", body=b'{"noi_dung":"x"}',
                               headers={"Authorization": gia, "Cookie": "authelia_session=bimat", "Remote-Email": "an@x",
                                        "Remote-Name": "An", "Content-Type": "application/json", "Prefer": "return=representation",
                                        "Proxy-Authorization": "Basic eDp5"})
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(than), [{"chu_so_huu": "an"}])
        self.assertEqual(r.getheader("Content-Range"), "0-0/*")
        yc = self.ps.nhan[0]
        self.assertEqual((yc["method"], yc["path"], yc["body"]), ("POST", "/ghi_chu?select=noi_dung", b'{"noi_dung":"x"}'))
        self.assertEqual(yc["all"].get_all("Authorization"), ["Bearer " + self.jwt()])
        self.assertNotIn(gia, json.dumps(yc["headers"]))
        for k in ("Cookie", "Remote-User", "Remote-Groups", "Remote-Email", "Remote-Name", "Proxy-Authorization"):
            self.assertNotIn(k.lower(), [h.lower() for h in yc["headers"]], k)
        self.assertEqual(yc["headers"]["Prefer"], "return=representation")
        self.assertEqual(yc["headers"]["Content-Type"], "application/json")

    # 6
    def test_api_toi_tra_ten_va_vai_tro_khong_goi_phia_sau(self):
        st, than, r = self.goi("GET", "/api/toi", nguoi=("binh", "nhan_vien,quan_ly"))
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(than), {"ten": "binh", "vai_tro": "quan_ly"})
        self.assertTrue(r.getheader("Content-Type").startswith("application/json"))
        self.assertEqual(self.ps.nhan, [])
        self.assertEqual(self.goi("GET", "/api/toi", nguoi=None)[0], 401)

    # 7
    def test_than_lon_hon_1mb_tra_413_khong_goi_phia_sau(self):
        s = socket.create_connection(("127.0.0.1", self.cong), 10)
        s.sendall(b"POST /api/ghi_chu HTTP/1.1\r\nHost: x\r\nRemote-User: an\r\nRemote-Groups: nhan_vien\r\n"
                  b"Content-Length: %d\r\n\r\n" % (MOT_MB + 1) + b"x" * (MOT_MB + 1))
        self.assertIn(b" 413 ", s.recv(4096).split(b"\r\n")[0])
        s.close()
        # Không có Content-Length (chunked, Caddy chuyển tiếp thân HTTP/2 như vậy): đếm khi đọc
        s = socket.create_connection(("127.0.0.1", self.cong), 10)
        s.sendall(b"POST /api/ghi_chu HTTP/1.1\r\nHost: x\r\nRemote-User: an\r\nRemote-Groups: nhan_vien\r\n"
                  b"Transfer-Encoding: chunked\r\n\r\n")
        manh = b"x" * 65536
        for _ in range(17):
            s.sendall(b"%x\r\n%s\r\n" % (len(manh), manh))
        s.sendall(b"0\r\n\r\n")
        self.assertIn(b" 413 ", s.recv(4096).split(b"\r\n")[0])
        s.close()
        self.assertEqual(self.ps.nhan, [])
        # Đúng 1 MB thì vẫn qua (chunked được ghép lại, gửi kèm Content-Length)
        st, _, _ = self.goi("POST", "/api/ghi_chu", body=b"y" * MOT_MB, headers={"Content-Type": "application/json"})
        self.assertEqual(st, 200)
        self.assertEqual(len(self.ps.nhan[0]["body"]), MOT_MB)

    # 8
    def test_nhat_ky_chi_co_thoi_gian_nguoi_dung_phuong_thuc_duong_dan_ma_tra_ve(self):
        dau = os.path.getsize(self.nhat_ky.name)
        self.goi("POST", "/api/ho_so?ten=eq.Nguyen%20Van%20A", body=b'{"cccd":"079201000001"}',
                 headers={"Authorization": "Bearer khoa-gia-cua-may-khach", "Content-Type": "application/json"},
                 nguoi=("an", "nhan_vien"))
        jwt = self.jwt()
        self.goi("GET", "/api/toi", nguoi=("an", "nhan_vien"))
        self.goi("GET", "/api/ghi_chu", nguoi=None)
        time.sleep(0.3)
        with open(self.nhat_ky.name) as f:
            f.seek(dau)
            dong = [d for d in f.read().splitlines() if d.strip()]
        self.assertEqual(len(dong), 3, dong)
        mau = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d{4} (\S+) (GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (/\S*) (\d{3})$")
        kq = [mau.match(d) for d in dong]
        self.assertTrue(all(kq), dong)
        self.assertEqual([m.groups() for m in kq],
                         [("an", "POST", "/api/ho_so", "200"), ("an", "GET", "/api/toi", "200"), ("-", "GET", "/api/ghi_chu", "401")])
        toan_bo = "\n".join(dong)
        for bi_mat in (jwt, jwt.split(".")[1], "079201000001", "Nguyen", "khoa-gia-cua-may-khach", BI_MAT):
            self.assertNotIn(bi_mat, toan_bo)

    # 9
    def test_phia_sau_khong_tra_loi_tra_502_tieng_viet(self):
        cong = cong_trong()
        tep = os.path.join(self.tmp.name, "nk-502.txt")
        p = subprocess.Popen([sys.executable, "-I", CAU_NOI], stdout=open(tep, "w"), stderr=subprocess.STDOUT,
                             env={"PATH": os.environ.get("PATH", ""), "CAU_NOI_CONG": str(cong), "CAU_NOI_DIA_CHI": "127.0.0.1",
                                  "CAU_NOI_PHIA_SAU": f"http://127.0.0.1:{cong_trong()}", "CAU_NOI_JWT_SECRET_FILE": self.bi_mat_tep})
        try:
            for _ in range(100):
                try:
                    socket.create_connection(("127.0.0.1", cong), 0.2).close()
                    break
                except OSError:
                    time.sleep(0.05)
            c = http.client.HTTPConnection("127.0.0.1", cong, timeout=15)
            c.request("GET", "/api/ghi_chu", headers={"Remote-User": "an", "Remote-Groups": "nhan_vien"})
            r = c.getresponse()
            than = json.loads(r.read())
            self.assertEqual(r.status, 502)
            self.assertRegex(than["loi"], "dữ liệu")
        finally:
            p.terminate()
            p.wait(10)

    def test_duong_dan_ngoai_api_tra_404_khong_goi_phia_sau(self):
        for path in ("/", "/toi", "/apix/ghi_chu", "/files/a"):
            self.assertEqual(self.goi("GET", path)[0], 404, path)
        self.assertEqual(self.ps.nhan, [])

    def test_khong_co_khoa_hop_le_thi_khong_chay(self):
        tep = os.path.join(self.tmp.name, "khoa-ngan")
        with open(tep, "w") as f:
            f.write("ngan\n")
        for khoa in (tep, os.path.join(self.tmp.name, "khong-co")):
            r = subprocess.run([sys.executable, "-I", CAU_NOI], capture_output=True, text=True, timeout=10,
                               env={"PATH": os.environ.get("PATH", ""), "CAU_NOI_CONG": str(cong_trong()),
                                    "CAU_NOI_JWT_SECRET_FILE": khoa})
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("khóa", r.stderr)

    def test_ma_nguon_chi_dung_thu_vien_chuan_va_co_spdx(self):
        nd = open(CAU_NOI, encoding="utf-8").read()
        self.assertIn("SPDX-License-Identifier: MIT", nd.splitlines()[1])
        chuan = set(sys.stdlib_module_names)
        for m in re.findall(r"^(?:from|import) ([a-zA-Z_][\w]*)", nd, re.M):
            self.assertIn(m, chuan, m)


class TrienKhai(unittest.TestCase):
    """Cầu nối trong compose và bộ cài: không cổng, không quyền, chỉ ở mạng sso (với Caddy) và api (với PostgREST); khóa 64 ký tự hex sinh một lần."""

    def test_compose_va_bo_cai(self):
        sys.path.insert(0, HERE)
        import test_onebee_dinh_danh as dd
        for https in (False, True):
            c = dd.compose(https)
            dv = c["services"]["cau-noi"]
            self.assertNotIn("ports", dv)
            self.assertEqual(dv["container_name"], "onebee-cau-noi")
            self.assertEqual(dv["image"], dd.bien()["onebee_box_images"]["python"])
            self.assertIn("no-new-privileges:true", dv["security_opt"])
            self.assertEqual((dv["cap_drop"], dv["read_only"]), (["ALL"], True))
            self.assertEqual(dv["networks"], ["sso", "api"])
            self.assertIn("logging", dv)
            self.assertEqual(dv["command"], ["python3", "-I", "/app/onebee-cau-noi-danh-tinh.py"])
            self.assertIn("./cau-noi:/app:ro", dv["volumes"])
            self.assertIn("/etc/onebee-box/secrets/cau-noi-jwt-secret:/run/secrets/cau-noi-jwt-secret:ro", dv["volumes"])
            env = dv["environment"]
            self.assertEqual(env["CAU_NOI_JWT_SECRET_FILE"], "/run/secrets/cau-noi-jwt-secret")
            self.assertEqual(env["CAU_NOI_PHIA_SAU"], "http://postgrest:3000")
        tasks = open(os.path.join(dd.DINH_DANH, "tasks/main.yml"), encoding="utf-8").read()
        self.assertRegex(tasks, r"lookup\('ansible\.builtin\.password', onebee_box_secrets ~ '/cau-noi-jwt-secret', "
                                r"chars=\['digits', 'abcdef'\], length=64\)")
        noi = [t for t in yaml.safe_load(tasks) if "onebee-cau-noi-danh-tinh.py" in json.dumps(t)]
        self.assertTrue(noi)


if __name__ == "__main__":
    unittest.main()
