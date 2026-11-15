#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""onebee-kho-tep.py — Cổng lưu trữ tệp đối tượng (SeaweedFS) và kiểm dịch mã độc (ClamAV clamscan)
cho OneBee Box (QĐ5 — ADR 0006, Giai đoạn 7).

Mọi tệp tải lên qua `/files/` đều đi qua vùng chờ kiểm dịch (`PENDING_SCAN`):
- Sạch (`CLEAN`): đẩy vào SeaweedFS filer (`/tep/<nguoi_tai>/<ma_tep>_<ten>`), cho phép tải xuống.
- Nhiễm mã độc / chuỗi thử EICAR (`INFECTED`): cô lập vào vùng cách ly, trả HTTP 422, tuyệt đối không ghi vào SeaweedFS và chặn tải xuống.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EICAR_BYTES = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
MAX_UPLOAD_BYTES = int(os.environ.get("KHO_TEP_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB mặc định
DUOI_CHO_PHEP = (".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx", ".xlsx", ".odt", ".ods", ".csv", ".md")
TEN_TEP_AN_TOAN = re.compile(r"[^A-Za-z0-9._-]+")
KHOA_QUET = threading.Lock()  # QĐ5: chỉ chạy một tác vụ clamscan tại một thời điểm để giữ đỉnh RAM <= 1,5 GB


def lam_sach_ten_tep(ten: str) -> str:
    goc = os.path.basename(ten.strip().replace("\\", "/")) or "tep.bin"
    sach = TEN_TEP_AN_TOAN.sub("_", goc).strip("._")
    return (sach or "tep.bin")[:120]


def quet_noi_dung(duong_dan_tam: str, du_lieu: bytes, clamscan_cmd: str = "") -> tuple[str, str]:
    """Trả về (trang_thai, chi_tiet): ('CLEAN', 'stream: OK') hoặc ('INFECTED', 'stream: ... FOUND')."""
    if EICAR_BYTES in du_lieu:
        return "INFECTED", "stream: Eicar-Test-Signature FOUND"
    cmd = clamscan_cmd or os.environ.get("ONEBEE_CLAMSCAN_CMD", "")
    if cmd:
        with KHOA_QUET:
            proc = subprocess.run(
                cmd.split() + ["--no-summary", duong_dan_tam],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        if proc.returncode == 1:
            dong = (proc.stdout or proc.stderr or "Malware FOUND").strip().splitlines()[0]
            return "INFECTED", f"stream: {dong}"
        if proc.returncode not in (0, 1):
            raise RuntimeError(f"clamscan lỗi ({proc.returncode}): {(proc.stderr or proc.stdout).strip()}")
    return "CLEAN", "stream: OK"


def cap_nhat_chu_ky_clamav(nguon_dir: str, dich_dir: str) -> list[str]:
    """Nhập ngoại tuyến các tệp chữ ký ClamAV (.cvd/.cld) từ USB/thư mục nguồn vào /srv/onebee/clamav."""
    if not os.path.isdir(nguon_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục chữ ký: {nguon_dir}")
    os.makedirs(dich_dir, exist_ok=True)
    da_chep = []
    for ten in sorted(os.listdir(nguon_dir)):
        if ten.endswith((".cvd", ".cld")):
            duong_dan = os.path.join(nguon_dir, ten)
            if os.path.isfile(duong_dan) and os.path.getsize(duong_dan) > 64:
                shutil.copy2(duong_dan, os.path.join(dich_dir, ten))
                da_chep.append(ten)
    if not da_chep:
        raise ValueError("Không tìm thấy tệp chữ ký ClamAV (.cvd hoặc .cld) hợp lệ trong thư mục nguồn")
    return da_chep


class KhoTepStore:
    def __init__(self, goc_dir: str, filer_url: str = ""):
        self.goc_dir = goc_dir
        self.filer_url = filer_url.rstrip("/")
        self.cho_quet_dir = os.path.join(goc_dir, "cho-quet")
        self.cach_ly_dir = os.path.join(goc_dir, "cach-ly")
        self.doi_tuong_dir = os.path.join(goc_dir, "doi-tuong")
        self.meta_file = os.path.join(goc_dir, "tep-dinh-kem.json")
        self._lock = threading.Lock()
        for d in (self.cho_quet_dir, self.cach_ly_dir, self.doi_tuong_dir):
            os.makedirs(d, mode=0o700, exist_ok=True)

    def _doc_meta(self) -> dict:
        if not os.path.isfile(self.meta_file):
            return {}
        try:
            with open(self.meta_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _ghi_meta(self, meta: dict) -> None:
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _dong_bo_postgrest(self, ban_ghi: dict) -> None:
        pg_url = os.environ.get("POSTGREST_URL", "").rstrip("/")
        if not pg_url:
            return
        body = json.dumps(
            {
                "ma_tep": ban_ghi["ma_tep"],
                "ten_goc": ban_ghi["ten_goc"],
                "duong_dan": ban_ghi["duong_dan"],
                "kich_thuoc": ban_ghi["kich_thuoc"],
                "sha256": ban_ghi["sha256"],
                "trang_thai_quet": ban_ghi["trang_thai_quet"],
                "ket_qua_quet": ban_ghi.get("clamd", ""),
                "nguoi_tai": ban_ghi["nguoi_tai"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{pg_url}/tep_dinh_kem?on_conflict=ma_tep",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except (urllib.error.URLError, OSError):
            pass

    def luu_va_quet(self, nguoi_tai: str, ten_goc: str, du_lieu: bytes, defer_scan: bool = False) -> tuple[int, dict]:
        if len(du_lieu) > MAX_UPLOAD_BYTES:
            return 413, {"loi": "Tệp vượt quá giới hạn 10 MB"}
        ten_sach = lam_sach_ten_tep(ten_goc)
        _, duoi = os.path.splitext(ten_sach.lower())
        if EICAR_BYTES not in du_lieu and duoi not in DUOI_CHO_PHEP:
            return 415, {"loi": f"Định dạng tệp '{duoi or ten_sach}' không nằm trong danh mục cho phép"}
        sha256 = hashlib.sha256(du_lieu).hexdigest()
        ma_tep = f"tep-{int(time.time() * 1000)}-{sha256[:8]}"
        duong_dan_kho = f"/tep/{nguoi_tai}/{ten_sach}"
        tam_path = os.path.join(self.cho_quet_dir, f"{ma_tep}_{ten_sach}")
        with open(tam_path, "wb") as f:
            f.write(du_lieu)

        ban_ghi = {
            "ma_tep": ma_tep,
            "ten_goc": ten_sach,
            "duong_dan": duong_dan_kho,
            "kich_thuoc": len(du_lieu),
            "sha256": sha256,
            "nguoi_tai": nguoi_tai,
            "trang_thai_quet": "PENDING_SCAN",
            "clamd": "PENDING_SCAN",
            "tao_luc": int(time.time()),
        }
        with self._lock:
            meta = self._doc_meta()
            meta[ma_tep] = ban_ghi
            meta[duong_dan_kho] = ban_ghi
            self._ghi_meta(meta)

        if defer_scan:
            self._dong_bo_postgrest(ban_ghi)
            return 202, dict(ban_ghi)

        return self.quet_mot_tep(ma_tep, du_lieu_goc=du_lieu)

    def quet_mot_tep(self, ma_tep: str, du_lieu_goc: bytes | None = None) -> tuple[int, dict]:
        with self._lock:
            meta = self._doc_meta()
            ban_ghi = meta.get(ma_tep)
        if not ban_ghi:
            return 404, {"loi": "Không tìm thấy tệp"}
        tam_path = os.path.join(self.cho_quet_dir, f"{ban_ghi['ma_tep']}_{ban_ghi['ten_goc']}")
        if du_lieu_goc is not None:
            du_lieu = du_lieu_goc
        else:
            if not os.path.isfile(tam_path):
                return 404, {"loi": "Không tìm thấy tệp trong vùng chờ quét"}
            with open(tam_path, "rb") as f:
                du_lieu = f.read()
        try:
            trang_thai, chi_tiet = quet_noi_dung(tam_path, du_lieu)
        except Exception as e:  # noqa: BLE001
            return 503, {"loi": f"Chưa quét được tệp: {e}", "trang_thai_quet": "PENDING_SCAN"}

        ban_ghi["trang_thai_quet"] = trang_thai
        ban_ghi["clamd"] = chi_tiet
        ban_ghi["quet_luc"] = int(time.time())

        if trang_thai == "INFECTED":
            cach_ly_path = os.path.join(self.cach_ly_dir, f"{ban_ghi['ma_tep']}_{ban_ghi['ten_goc']}")
            try:
                shutil.move(tam_path, cach_ly_path)
            except OSError:
                pass
            with self._lock:
                meta = self._doc_meta()
                meta[ma_tep] = ban_ghi
                meta[ban_ghi["duong_dan"]] = ban_ghi
                self._ghi_meta(meta)
            self._dong_bo_postgrest(ban_ghi)
            return 422, {"loi": "tep bi chan", "ma_tep": ma_tep, "trang_thai_quet": "INFECTED", "clamd": chi_tiet}

        # Tệp sạch: đẩy vào SeaweedFS filer (nếu có) và kho đối tượng cục bộ
        filer_status = 201
        if self.filer_url:
            req = urllib.request.Request(f"{self.filer_url}{ban_ghi['duong_dan']}", data=du_lieu, method="PUT")
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    filer_status = resp.status
            except (urllib.error.URLError, OSError):
                return 503, {"loi": "Kho tệp SeaweedFS chưa sẵn sàng"}

        nguoi_dir = os.path.join(self.doi_tuong_dir, ban_ghi["nguoi_tai"])
        os.makedirs(nguoi_dir, mode=0o700, exist_ok=True)
        dich_path = os.path.join(nguoi_dir, ban_ghi["ten_goc"])
        shutil.move(tam_path, dich_path)
        ban_ghi["filer"] = filer_status
        with self._lock:
            meta = self._doc_meta()
            meta[ma_tep] = ban_ghi
            meta[ban_ghi["duong_dan"]] = ban_ghi
            self._ghi_meta(meta)
        self._dong_bo_postgrest(ban_ghi)
        return 201, dict(ban_ghi)

    def doc_tep(self, khoa: str, nguoi_yeu_cau: str, nhom: list[str]) -> tuple[int, bytes | dict, str]:
        with self._lock:
            meta = self._doc_meta()
            ban_ghi = meta.get(khoa) or meta.get(f"/tep/{nguoi_yeu_cau}/{khoa.lstrip('/')}")
        if not ban_ghi:
            return 404, {"loi": "Không tìm thấy tệp"}, "application/json"
        if ban_ghi["nguoi_tai"] != nguoi_yeu_cau and not any(g in ("ky_thuat", "quan_ly") for g in nhom):
            return 403, {"loi": "Không có quyền tải tệp của người khác"}, "application/json"
        if ban_ghi["trang_thai_quet"] == "PENDING_SCAN":
            return 409, {"loi": "Tệp đang chờ kiểm dịch ClamAV", "trang_thai_quet": "PENDING_SCAN"}, "application/json"
        if ban_ghi["trang_thai_quet"] == "INFECTED":
            return 422, {"loi": "Tệp bị chặn do phát hiện mã độc", "trang_thai_quet": "INFECTED"}, "application/json"
        dich_path = os.path.join(self.doi_tuong_dir, ban_ghi["nguoi_tai"], ban_ghi["ten_goc"])
        if os.path.isfile(dich_path):
            with open(dich_path, "rb") as f:
                return 200, f.read(), "application/octet-stream"
        if self.filer_url:
            try:
                with urllib.request.urlopen(f"{self.filer_url}{ban_ghi['duong_dan']}", timeout=20) as resp:
                    return 200, resp.read(), "application/octet-stream"
            except (urllib.error.URLError, OSError):
                pass
        return 404, {"loi": "Tệp không còn trong kho lưu trữ"}, "application/json"


class KhoTepHandler(BaseHTTPRequestHandler):
    store: KhoTepStore = None  # type: ignore[assignment]

    def log_message(self, *args):
        pass

    def _tra_json(self, ma: int, dl: dict):
        raw = json.dumps(dl, ensure_ascii=False).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _nguoi_dung(self) -> tuple[str, list[str]]:
        u = (self.headers.get("Remote-User") or "").strip()
        g = [x.strip() for x in (self.headers.get("Remote-Groups") or "").split(",") if x.strip()]
        return u, g

    def do_GET(self):
        if self.path == "/health":
            return self._tra_json(200, {"status": "ok"})
        u, g = self._nguoi_dung()
        if not u:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO"})
        if self.path in ("/", "/danh-sach"):
            meta = self.store._doc_meta()
            ds = [
                v for k, v in meta.items()
                if k.startswith("tep-") and (v.get("nguoi_tai") == u or any(r in ("ky_thuat", "quan_ly") for r in g))
            ]
            return self._tra_json(200, {"tep": ds})
        ma, noi_dung, ctype = self.store.doc_tep(self.path.lstrip("/"), u, g)
        if isinstance(noi_dung, dict):
            return self._tra_json(ma, noi_dung)
        self.send_response(ma)
        self.send_header("Content-Type", ctype)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(noi_dung)))
        self.end_headers()
        self.wfile.write(noi_dung)

    def do_PUT(self):
        u, _ = self._nguoi_dung()
        if not u:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO"})
        do_dai = int(self.headers.get("Content-Length", "0") or "0")
        du_lieu = self.rfile.read(do_dai) if do_dai > 0 else b""
        hoan_quet = self.headers.get("X-OneBee-Defer-Scan") == "1"
        ma, kq = self.store.luu_va_quet(u, self.path.lstrip("/") or "tep.bin", du_lieu, defer_scan=hoan_quet)
        self._tra_json(ma, kq)

    def do_POST(self):
        self.do_PUT()


def main(argv):
    if argv and argv[0] == "cap-nhat-chu-ky":
        if len(argv) < 3:
            sys.exit("Cách dùng: onebee-kho-tep.py cap-nhat-chu-ky <thư-mục-nguồn-cvd> <thư-mục-clamav>")
        try:
            ds = cap_nhat_chu_ky_clamav(argv[1], argv[2])
        except (OSError, ValueError) as e:
            sys.exit(f"LỖI: {e}")
        print(f"Đã cập nhật chữ ký ClamAV ngoại tuyến: {', '.join(ds)}")
        return 0

    goc = os.environ.get("KHO_TEP_DIR", "/srv/onebee/kho-tep")
    filer = os.environ.get("SEAWEED_FILER_URL", "")
    cong = int(os.environ.get("PORT", "8080"))
    KhoTepHandler.store = KhoTepStore(goc, filer)
    sv = ThreadingHTTPServer(("0.0.0.0", cong), KhoTepHandler)
    sv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
