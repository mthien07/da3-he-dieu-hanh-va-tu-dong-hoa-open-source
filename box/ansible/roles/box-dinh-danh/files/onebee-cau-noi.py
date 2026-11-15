#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""onebee-cau-noi.py — Cầu nối danh tính (Authelia forward_auth -> JWT 60 giây cho PostgREST)
và công cụ quản lý người dùng SSO (`users.yml`) cho OneBee Box (QĐ4 — ADR 0006).

Chế độ dịch vụ HTTP:
  onebee-cau-noi.py serve
Chế độ quản trị dòng lệnh:
  onebee-cau-noi.py them-nguoi <users.yml> <ten> <nhom> [mat-khau] [ho-ten]
  onebee-cau-noi.py xoa-nguoi <users.yml> <ten>
  onebee-cau-noi.py danh-sach <users.yml>
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NHOM_HOP_LE = ("nhan_vien", "ky_thuat", "quan_ly")
THU_TU_VAI_TRO = {"quan_ly": 3, "ky_thuat": 2, "nhan_vien": 1}
TEN_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def giai_ma_header_utf8(raw_val: str) -> str:
    if not raw_val:
        return ""
    try:
        return raw_val.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return raw_val


def chon_vai_tro(groups_header: str) -> tuple[list[str], str]:
    ds = [g.strip() for g in (groups_header or "").split(",") if g.strip() in THU_TU_VAI_TRO]
    if not ds:
        return [], ""
    tot_nhat = max(ds, key=lambda g: THU_TU_VAI_TRO[g])
    return ds, tot_nhat


def ky_jwt(sub: str, role: str, bi_mat: bytes, ttl: int = 60, aud: str = "onebee-api", now: int | None = None) -> str:
    bay_gio = int(time.time()) if now is None else int(now)
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload = b64url(
        json.dumps(
            {"sub": sub, "role": role, "aud": aud, "iat": bay_gio, "exp": bay_gio + ttl},
            separators=(",", ":"),
        ).encode("utf-8")
    )
    ky = hmac.new(bi_mat, f"{header}.{payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(ky)}"


def kiem_tra_khan_cap(duong_dan_dau: str) -> dict | None:
    """Kiểm tra dấu tắt SSO tạm thời (tối đa 24 giờ)."""
    if not duong_dan_dau or not os.path.isfile(duong_dan_dau):
        return None
    try:
        with open(duong_dan_dau, encoding="utf-8") as f:
            dl = json.load(f)
        het_han = int(dl.get("het_han", 0))
        if time.time() < het_han:
            return dl
    except (OSError, ValueError, TypeError):
        return None
    return None


# ---- Quản lý tệp users.yml của Authelia ----

def bam_pbkdf2_authelia(mat_khau: str, salt_bytes: bytes | None = None, iterations: int = 310000) -> str:
    """Sinh chuỗi băm mật khẩu chuẩn PHC ($pbkdf2-sha512$...) tương thích với Authelia khi không có container authelia."""
    salt = salt_bytes or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha512", mat_khau.encode("utf-8"), salt, iterations)
    s_b64 = base64.b64encode(salt).rstrip(b"=").decode("ascii").replace("+", ".")
    h_b64 = base64.b64encode(dk).rstrip(b"=").decode("ascii").replace("+", ".")
    return f"$pbkdf2-sha512${iterations}${s_b64}${h_b64}"


def doc_users_yml(duong_dan: str) -> dict:
    if not os.path.isfile(duong_dan):
        return {"users": {}}
    try:
        import yaml
        with open(duong_dan, encoding="utf-8") as f:
            dl = yaml.safe_load(f) or {}
        if not isinstance(dl.get("users"), dict):
            dl["users"] = {}
        return dl
    except ImportError:
        # Dự phòng JSON-compatible YAML khi chạy môi trường tối giản không có PyYAML
        with open(duong_dan, encoding="utf-8") as f:
            nd = f.read().strip()
        return json.loads(nd) if nd.startswith("{") else {"users": {}}


def ghi_users_yml(duong_dan: str, dl: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    try:
        import yaml
        van_ban = yaml.safe_dump(dl, allow_unicode=True, sort_keys=False)
    except ImportError:
        van_ban = json.dumps(dl, ensure_ascii=False, indent=2) + "\n"
    with open(duong_dan, "w", encoding="utf-8") as f:
        f.write("# SPDX-License-Identifier: MIT\n# Quản lý bởi onebee-box them-nguoi / xoa-nguoi\n" + van_ban)
    os.chmod(duong_dan, 0o600)


def them_nguoi(duong_dan: str, ten: str, nhom: str, mat_khau: str = "", ho_ten: str = "", ma_don_vi: str = "onebee") -> tuple[str, bool]:
    if not TEN_HOP_LE.match(ten):
        raise ValueError("Tên tài khoản chỉ gồm chữ thường không dấu, số, dấu chấm/gạch (tối đa 32 ký tự)")
    if nhom not in NHOM_HOP_LE:
        raise ValueError(f"Nhóm không hợp lệ: {nhom} (chỉ nhận: {', '.join(NHOM_HOP_LE)})")
    mk = mat_khau or secrets.token_urlsafe(12)
    dl = doc_users_yml(duong_dan)
    da_co = ten in dl["users"]
    dl["users"][ten] = {
        "displayname": ho_ten or ten,
        "password": bam_pbkdf2_authelia(mk),
        "email": f"{ten}@{ma_don_vi}.onebee.internal",
        "groups": [nhom],
        "disabled": False,
    }
    ghi_users_yml(duong_dan, dl)
    return mk, not da_co


def xoa_nguoi(duong_dan: str, ten: str) -> bool:
    dl = doc_users_yml(duong_dan)
    if ten not in dl.get("users", {}):
        return False
    del dl["users"][ten]
    ghi_users_yml(duong_dan, dl)
    return True


# ---- Máy chủ HTTP cầu nối danh tính ----

class CauNoiHandler(BaseHTTPRequestHandler):
    postgrest_url = os.environ.get("POSTGREST_URL", "http://postgrest:3000").rstrip("/")
    jwt_secret = os.environ.get("PGRST_JWT_SECRET", "").encode("utf-8")
    khan_cap_file = os.environ.get("ONEBEE_SSO_KHAN_CAP_FILE", "/var/lib/onebee-box/sso-khan-cap.json")
    demo_mode = os.environ.get("ONEBEE_CHE_DO_DEMO", "false").lower() == "true"

    def log_message(self, *args):
        pass

    def _tra_json(self, ma: int, dl: dict):
        raw = json.dumps(dl, ensure_ascii=False).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _xac_dinh_danh_tinh(self):
        user = giai_ma_header_utf8(self.headers.get("Remote-User", "")).strip()
        groups_raw = giai_ma_header_utf8(self.headers.get("Remote-Groups", "")).strip()
        email = giai_ma_header_utf8(self.headers.get("Remote-Email", "")).strip()
        name = giai_ma_header_utf8(self.headers.get("Remote-Name", "")).strip()
        khan_cap = kiem_tra_khan_cap(self.khan_cap_file)

        if not user and khan_cap:
            user = khan_cap.get("nguoi_dung", "khan_cap_quan_ly")
            groups_raw = khan_cap.get("nhom", "quan_ly")
            name = "Phiên khẩn cấp (tắt SSO tạm)"
        elif not user:
            return None

        ds_nhom, vai_tro = chon_vai_tro(groups_raw)
        if not vai_tro:
            return None
        return {
            "user": user,
            "name": name or user,
            "email": email,
            "groups": ds_nhom,
            "role": vai_tro,
            "che_do_khan_cap": bool(khan_cap),
            "che_do_demo": self.demo_mode,
        }

    def _xu_ly(self, phuong_thuc: str):
        if self.path == "/health":
            return self._tra_json(200, {"status": "ok"})

        danh_tinh = self._xac_dinh_danh_tinh()
        if not danh_tinh:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO hoặc nhóm không có quyền truy cập API"})

        if self.path in ("/ho-so", "/whoami"):
            return self._tra_json(200, danh_tinh)

        if len(self.jwt_secret) < 32:
            return self._tra_json(500, {"loi": "Chưa cấu hình PGRST_JWT_SECRET hợp lệ (cần tối thiểu 32 ký tự)"})

        token = ky_jwt(danh_tinh["user"], danh_tinh["role"], self.jwt_secret)
        do_dai = int(self.headers.get("Content-Length", "0") or "0")
        than = self.rfile.read(do_dai) if do_dai > 0 else None

        # Chỉ giữ các header an toàn cho PostgREST; loại bỏ hoàn toàn Authorization, Cookie, Remote-* của máy khách
        hdr_chuyen = {"Authorization": f"Bearer {token}", "Accept": self.headers.get("Accept", "application/json")}
        for k in ("Content-Type", "Prefer", "Range", "Range-Unit", "Accept-Profile", "Content-Profile"):
            if k in self.headers:
                hdr_chuyen[k] = self.headers[k]

        dich = f"{self.postgrest_url}{self.path}"
        req = urllib.request.Request(dich, data=than, headers=hdr_chuyen, method=phuong_thuc)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                self.send_response(resp.status)
                for hk in ("Content-Type", "Content-Range", "Preference-Applied", "Location"):
                    if hk in resp.headers:
                        self.send_header(hk, resp.headers[hk])
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (urllib.error.URLError, TimeoutError, OSError):
            self._tra_json(503, {"loi": "Dịch vụ cơ sở dữ liệu (PostgREST) chưa sẵn sàng"})

    def do_GET(self):
        self._xu_ly("GET")

    def do_POST(self):
        self._xu_ly("POST")

    def do_PATCH(self):
        self._xu_ly("PATCH")

    def do_DELETE(self):
        self._xu_ly("DELETE")


def main(argv):
    if not argv or argv[0] == "serve":
        cong = int(os.environ.get("PORT", "8080"))
        sv = ThreadingHTTPServer(("0.0.0.0", cong), CauNoiHandler)
        sv.serve_forever()
        return 0
    lenh = argv[0]
    if lenh == "them-nguoi":
        if len(argv) < 4:
            sys.exit("Cách dùng: onebee-cau-noi.py them-nguoi <users.yml> <tên> <nhóm> [mật-khẩu] [họ-tên]")
        tep, ten, nhom = argv[1], argv[2], argv[3]
        mk_vao = argv[4] if len(argv) > 4 else ""
        ho_ten = argv[5] if len(argv) > 5 else ""
        ma_dv = os.environ.get("BOX_MA_DON_VI", "onebee")
        try:
            mk, tao_moi = them_nguoi(tep, ten, nhom, mk_vao, ho_ten, ma_dv)
        except ValueError as e:
            sys.exit(f"LỖI: {e}")
        trang_thai = "Đã tạo" if tao_moi else "Đã cập nhật"
        print(f"{trang_thai} tài khoản SSO: {ten} (nhóm: {nhom})")
        print(f"MAT_KHAU_BAN_DAU={mk}")
        return 0
    if lenh == "xoa-nguoi":
        if len(argv) < 3:
            sys.exit("Cách dùng: onebee-cau-noi.py xoa-nguoi <users.yml> <tên>")
        if not xoa_nguoi(argv[1], argv[2]):
            sys.exit(f"LỖI: Không tìm thấy tài khoản {argv[2]}")
        print(f"Đã xóa tài khoản SSO: {argv[2]}")
        return 0
    if lenh == "danh-sach":
        dl = doc_users_yml(argv[1]) if len(argv) > 1 else {"users": {}}
        for u, info in sorted((dl.get("users") or {}).items()):
            nhom = ",".join(info.get("groups") or [])
            print(f"{u}\t{nhom}\t{info.get('displayname', u)}")
        return 0
    sys.exit(f"Lệnh không rõ: {lenh}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
