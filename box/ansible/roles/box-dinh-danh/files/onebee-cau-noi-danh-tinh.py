#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cầu nối danh tính của OneBee Box (ADR 0006, QĐ4): đứng sau Caddy forward_auth (Authelia), trước dịch vụ dữ liệu (PostgREST).

- Chỉ tin Remote-User / Remote-Groups do Caddy chép từ Authelia (Caddy xóa bản do máy khách gửi; cầu nối chỉ nằm trong mạng
  Docker nội bộ "sso" cùng Caddy, không công bố cổng). Thiếu → 401; không thuộc nhóm nào đã biết → 403.
- Ký JWT HS256 sống 60 giây (sub = tên đăng nhập, role = vai trò cao nhất, aud = onebee-api, iat, exp) cho MỖI yêu cầu.
  Authorization, Proxy-Authorization, Cookie, Remote-* của máy khách không bao giờ được chuyển tiếp.
- GET /api/toi trả {"ten", "vai_tro"} của phiên, không gọi phía sau. Đường dẫn khác dưới /api/ chuyển tới phía sau, bỏ tiền tố /api.
- Thân yêu cầu tối đa 1 MB (413). Phía sau không trả lời → 502.
- Nhật ký (stderr, docker logs) mỗi yêu cầu một dòng: thời gian, người dùng, phương thức, đường dẫn (không có chuỗi truy vấn), mã trả về.

Biến môi trường: CAU_NOI_JWT_SECRET_FILE (bắt buộc, ≥ 32 ký tự), CAU_NOI_PHIA_SAU (mặc định http://postgrest:3000),
CAU_NOI_DIA_CHI (mặc định 0.0.0.0), CAU_NOI_CONG (mặc định 8080)."""
import base64
import hashlib
import hmac
import http.client
import json
import os
import re
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VAI_TRO = ("quan_ly", "ke_toan", "thu_kho", "ky_thuat", "nhan_vien")   # thứ tự ưu tiên: cao → thấp
KHAN_GIA = "onebee-api"
SONG_GIAY = 60
TOI_DA = 1024 * 1024
TEN_HOP_LE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
# Không chuyển tiếp: tiêu đề nối kết (hop-by-hop), danh tính/quyền do máy khách tự gửi, độ dài (tính lại)
BO_DI = {"connection", "keep-alive", "proxy-connection", "proxy-authenticate", "proxy-authorization", "te", "trailer",
         "transfer-encoding", "upgrade", "host", "content-length", "authorization", "cookie", "expect"}
BO_DI_TRA_VE = {"connection", "keep-alive", "proxy-authenticate", "te", "trailer", "transfer-encoding", "upgrade",
                "content-length", "set-cookie", "server", "date"}


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ky_jwt(khoa, sub, role):
    bay_gio = int(time.time())
    dau = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    than = b64(json.dumps({"sub": sub, "role": role, "aud": KHAN_GIA, "iat": bay_gio, "exp": bay_gio + SONG_GIAY},
                          separators=(",", ":")).encode())
    chu_ky = hmac.new(khoa, f"{dau}.{than}".encode(), hashlib.sha256).digest()
    return f"{dau}.{than}.{b64(chu_ky)}"


class QuaLon(Exception):
    pass


def tao_xu_ly(khoa, phia_sau):
    goc = urllib.parse.urlsplit(phia_sau)

    class XuLy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "onebee-cau-noi"
        sys_version = ""

        def log_message(self, *a):   # nhật ký mặc định in cả dòng yêu cầu (có chuỗi truy vấn) → tắt, dùng ghi_nhat_ky
            pass

        def ghi_nhat_ky(self, nguoi, ma):
            duong_dan = urllib.parse.urlsplit(self.path).path
            print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {nguoi or '-'} {self.command} {duong_dan} {ma}", file=sys.stderr, flush=True)

        def tra(self, ma, du_lieu, nguoi=None, dong=False):
            than = json.dumps(du_lieu, ensure_ascii=False).encode()
            self.send_response_only(ma)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(than)))
            self.send_header("Cache-Control", "no-store")
            if dong:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(than)
            self.ghi_nhat_ky(nguoi, ma)

        def doc_than(self):
            """Đọc thân yêu cầu (Content-Length hoặc chunked), tối đa TOI_DA byte; quá thì QuaLon."""
            if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
                phan, tong = [], 0
                while True:
                    dong = self.rfile.readline(1024)
                    co = int(dong.split(b";")[0].strip() or b"0", 16)
                    if co == 0:
                        while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                            pass
                        break
                    tong += co
                    if tong > TOI_DA:
                        # đọc bỏ phần còn lại (tối đa thêm TOI_DA) để máy khách nhận được câu trả lời 413
                        da_bo = 0
                        while co and da_bo <= TOI_DA:
                            self.rfile.read(co + 2)
                            da_bo += co
                            co = int(self.rfile.readline(1024).split(b";")[0].strip() or b"0", 16)
                        if not co:
                            while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                                pass
                        raise QuaLon
                    phan.append(self.rfile.read(co))
                    self.rfile.read(2)
                return b"".join(phan)
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0:
                raise QuaLon
            if n > TOI_DA:
                # Đọc bỏ thân (tối đa 2 MB, chờ tối đa 5 giây) rồi mới trả 413: đóng kết nối khi bên gửi (Caddy) còn đang gửi
                # thì bên gửi chỉ thấy kết nối đứt (502) thay vì câu trả lời 413
                self.connection.settimeout(5)
                con = min(n, 2 * TOI_DA)
                try:
                    while con > 0 and (manh := self.rfile.read(min(con, 65536))):
                        con -= len(manh)
                except OSError:
                    pass
                raise QuaLon
            return self.rfile.read(n) if n else b""

        def xu_ly(self):
            nguoi_ds = self.headers.get_all("Remote-User") or []
            nhom_ds = self.headers.get_all("Remote-Groups") or []
            if len(nguoi_ds) != 1 or len(nhom_ds) != 1 or not nhom_ds[0].strip() or not TEN_HOP_LE.fullmatch(nguoi_ds[0]):
                return self.tra(401, {"loi": "Chưa đăng nhập: mở trang đăng nhập OneBee rồi thử lại"}, dong=True)
            nguoi = nguoi_ds[0]
            nhom = {n.strip() for n in nhom_ds[0].split(",")}
            vai_tro = next((v for v in VAI_TRO if v in nhom), None)
            if not vai_tro:
                return self.tra(403, {"loi": "Tài khoản không thuộc nhóm nào được dùng dữ liệu của Box"}, nguoi, dong=True)
            url = urllib.parse.urlsplit(self.path)
            if not url.path.startswith("/api/"):
                return self.tra(404, {"loi": "Không có đường dẫn này"}, nguoi, dong=True)
            if url.path == "/api/toi":
                if self.command not in ("GET", "HEAD"):
                    return self.tra(405, {"loi": "Chỉ đọc được /api/toi"}, nguoi, dong=True)
                return self.tra(200, {"ten": nguoi, "vai_tro": vai_tro}, nguoi)
            try:
                than = self.doc_than()
            except (QuaLon, ValueError):
                return self.tra(413, {"loi": "Dữ liệu gửi lên quá 1 MB"}, nguoi, dong=True)
            tieu_de = {k: v for k, v in self.headers.items()
                       if k.lower() not in BO_DI and not k.lower().startswith("remote-")}
            tieu_de["Authorization"] = "Bearer " + ky_jwt(khoa, nguoi, vai_tro)
            tieu_de["Host"] = goc.netloc
            if than or self.command in ("POST", "PUT", "PATCH"):
                tieu_de["Content-Length"] = str(len(than))
            dich = url.path[len("/api"):] + (f"?{url.query}" if url.query else "")
            try:
                c = http.client.HTTPConnection(goc.hostname, goc.port or 80, timeout=60)
                c.request(self.command, dich, body=than or None, headers=tieu_de)
                r = c.getresponse()
                tl = r.read()
                c.close()
            except (OSError, http.client.HTTPException):
                return self.tra(502, {"loi": "Dịch vụ dữ liệu của Box chưa sẵn sàng hoặc không trả lời — thử lại sau ít phút"},
                                nguoi, dong=True)
            self.send_response_only(r.status, r.reason)
            for k, v in r.getheaders():
                if k.lower() not in BO_DI_TRA_VE:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(tl)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(tl)
            self.ghi_nhat_ky(nguoi, r.status)

        do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = xu_ly

    return XuLy


def main():
    tep = os.environ.get("CAU_NOI_JWT_SECRET_FILE", "")
    try:
        with open(tep, encoding="utf-8") as f:
            khoa = f.read().strip()
    except OSError as e:
        sys.exit(f"LỖI: không đọc được khóa ký JWT ({tep}): {e.strerror}")
    if len(khoa) < 32:
        sys.exit(f"LỖI: khóa ký JWT trong {tep} phải dài ít nhất 32 ký tự")
    phia_sau = os.environ.get("CAU_NOI_PHIA_SAU", "http://postgrest:3000")
    may_chu = ThreadingHTTPServer((os.environ.get("CAU_NOI_DIA_CHI", "0.0.0.0"), int(os.environ.get("CAU_NOI_CONG", "8080"))),
                                  tao_xu_ly(khoa.encode(), phia_sau))
    may_chu.daemon_threads = True
    print(f"Cầu nối danh tính: nghe cổng {may_chu.server_address[1]}, chuyển tới {phia_sau}", file=sys.stderr, flush=True)
    may_chu.serve_forever()


if __name__ == "__main__":
    main()
