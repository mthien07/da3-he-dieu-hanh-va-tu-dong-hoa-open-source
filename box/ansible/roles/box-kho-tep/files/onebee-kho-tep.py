#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Dịch vụ kho tệp của OneBee Box (ADR 0006): tải lên → kiểm dịch ClamAV từng lượt → ghi SeaweedFS → ghi metadata.

- Chỉ Caddy chuyển yêu cầu người dùng tới (mạng Docker riêng, không công bố cổng); tin Remote-User / Remote-Groups do Caddy
  chép từ Authelia. Caddy xóa bản do máy khách gửi trước khi xác thực. Thiếu danh tính → 401.
- Tệp tải lên đi qua vùng chờ quét. `clamscan` chạy từng lượt (một tác vụ tại một thời điểm, không có clamd thường trú — QĐ5):
  sạch (`CLEAN`) mới được đẩy vào SeaweedFS; nhiễm (`INFECTED`) bị giữ trong vùng cách ly và không tải xuống được.
- Metadata tệp ghi/đọc bảng onebee.tep_dinh_kem qua cầu nối danh tính (JWT 60 giây của chính người dùng, RLS trong CSDL);
  dịch vụ không có quyền chủ CSDL và không tự viết thẳng vào PostgreSQL.
- Giới hạn 10 MB, đuôi tệp theo danh mục cho phép; SHA-256 kiểm lại ở mỗi lần tải xuống.

Biến môi trường: KHO_TEP_DIR, SEAWEED_FILER_URL, CAU_NOI_URL, CLAMSCAN_CMD, CLAMAV_DATABASE_DIR, PORT.
Lệnh phụ: `onebee-kho-tep.py cap-nhat-chu-ky <thư-mục-nguồn> <thư-mục-đích>` nộp chữ ký ClamAV ngoại tuyến.
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
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB theo đặc tả kho tệp
DUOI_CHO_PHEP = (".pdf", ".png", ".jpg", ".txt", ".docx", ".xlsx", ".odt", ".ods")
TEN_TEP_AN_TOAN = re.compile(r"[^A-Za-z0-9._-]+")
TEN_NGUOI = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")   # cùng quy tắc tên đăng nhập của Authelia/cầu nối danh tính
KHOA_QUET = threading.Lock()   # QĐ5: chỉ một tác vụ clamscan tại một thời điểm để giữ đỉnh RAM trong ngưỡng
RANH_GIOI = "----onebee-kho-tep"


def lam_sach_ten_tep(ten: str) -> str:
    """Bỏ đường dẫn và ký tự lạ khỏi tên tệp (tên hiển thị và khóa đối tượng chỉ dùng ASCII an toàn)."""
    goc = os.path.basename(ten.strip().replace("\\", "/")) or "tep.bin"
    sach = TEN_TEP_AN_TOAN.sub("_", goc).strip("._")
    return (sach or "tep.bin")[:120]


def quet_noi_dung(duong_dan: str, clamscan_cmd: str = "clamscan", clamav_dir: str = "/var/lib/clamav") -> tuple[str, str]:
    """Quét một tệp bằng clamscan. Trả ('CLEAN', ...) hoặc ('INFECTED', ...); lỗi công cụ thì ném RuntimeError."""
    with KHOA_QUET:
        proc = subprocess.run(
            [clamscan_cmd, "--no-summary", f"--database={clamav_dir}", duong_dan],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    if proc.returncode == 0:
        return "CLEAN", "OK"
    if proc.returncode == 1:
        dong = (proc.stdout or proc.stderr or "Malware FOUND").strip().splitlines()
        return "INFECTED", (dong[0] if dong else "Malware FOUND")
    chi_tiet = (proc.stderr or proc.stdout or "").strip().splitlines()
    raise RuntimeError(chi_tiet[0] if chi_tiet else f"clamscan lỗi (mã {proc.returncode})")


def cap_nhat_chu_ky_clamav(nguon_dir: str, dich_dir: str) -> list[str]:
    """Nạp ngoại tuyến các tệp chữ ký ClamAV (.cvd/.cld) từ USB vào thư mục chữ ký của Box."""
    if not os.path.isdir(nguon_dir):
        raise FileNotFoundError(f"Không tìm thấy thư mục chữ ký: {nguon_dir}")
    os.makedirs(dich_dir, exist_ok=True)
    da_chep = []
    for ten in sorted(os.listdir(nguon_dir)):
        if ten.endswith((".cvd", ".cld")):
            duong_dan = os.path.join(nguon_dir, ten)
            if os.path.isfile(duong_dan) and os.path.getsize(duong_dan) > 64:
                dich = os.path.join(dich_dir, ten)
                tam = dich + ".moi"
                shutil.copy2(duong_dan, tam)   # chép xong mới thay: lượt clamscan đang chạy không đọc tệp dở
                os.replace(tam, dich)
                da_chep.append(ten)
    if not da_chep:
        raise ValueError("Không tìm thấy tệp chữ ký ClamAV (.cvd hoặc .cld) hợp lệ trong thư mục nguồn")
    return da_chep


class KhoTepStore:
    def __init__(self, goc_dir: str, filer_url: str, cau_noi_url: str,
                 clamscan_cmd: str = "clamscan", clamav_dir: str = "/var/lib/clamav"):
        self.goc_dir = goc_dir
        self.filer_url = filer_url.rstrip("/")
        self.cau_noi_url = cau_noi_url.rstrip("/")
        self.clamscan_cmd = clamscan_cmd
        self.clamav_dir = clamav_dir
        self.cho_quet_dir = os.path.join(goc_dir, "cho-quet")
        self.cach_ly_dir = os.path.join(goc_dir, "cach-ly")
        for d in (self.cho_quet_dir, self.cach_ly_dir):
            os.makedirs(d, mode=0o700, exist_ok=True)

    # ---- Gọi cầu nối danh tính (JWT của người dùng, RLS trong CSDL) ----
    def _goi_cau_noi(self, method: str, duong: str, nguoi: str, nhom: list[str],
                     than=None, prefer: str = "") -> tuple[int, object]:
        tieu_de = {"Remote-User": nguoi, "Remote-Groups": ",".join(nhom), "Accept": "application/json"}
        du_lieu = None
        if than is not None:
            du_lieu = json.dumps(than, ensure_ascii=False).encode("utf-8")
            tieu_de["Content-Type"] = "application/json"
        if prefer:
            tieu_de["Prefer"] = prefer
        yeu_cau = urllib.request.Request(f"{self.cau_noi_url}/api/{duong}", data=du_lieu, headers=tieu_de, method=method)
        try:
            with urllib.request.urlopen(yeu_cau, timeout=15) as tra_loi:
                raw = tra_loi.read()
                return tra_loi.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                noi_dung = json.loads(raw) if raw else {"loi": f"dịch vụ dữ liệu trả mã {e.code}"}
            except ValueError:
                noi_dung = {"loi": raw.decode("utf-8", "replace")[:300]}
            return e.code, noi_dung
        except (urllib.error.URLError, OSError) as e:
            return 502, {"loi": f"Không gọi được dịch vụ dữ liệu: {e}"}

    def _ghi_metadata(self, ban_ghi: dict, nguoi: str, nhom: list[str]) -> tuple[int, object]:
        return self._goi_cau_noi("POST", "tep_dinh_kem", nguoi, nhom, than=ban_ghi, prefer="return=representation")

    def _doc_metadata(self, ma: int, nguoi: str, nhom: list[str]) -> tuple[int, object]:
        truy_van = urllib.parse.urlencode({
            "id": f"eq.{ma}",
            "select": "id,ten_tep,kich_thuoc,sha256,khoa_luu_tru,trang_thai_quet",
        })
        return self._goi_cau_noi("GET", f"tep_dinh_kem?{truy_van}", nguoi, nhom)

    def danh_sach(self, nguoi: str, nhom: list[str]) -> tuple[int, object]:
        truy_van = urllib.parse.urlencode({
            "select": "id,ten_tep,kich_thuoc,sha256,trang_thai_quet,tao_luc",
            "order": "id.desc",
        })
        return self._goi_cau_noi("GET", f"tep_dinh_kem?{truy_van}", nguoi, nhom)

    # ---- SeaweedFS filer ----
    def _filer_luu(self, khoa: str, ten: str, du_lieu: bytes) -> None:
        than = (
            f"--{RANH_GIOI}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{ten}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + du_lieu + f"\r\n--{RANH_GIOI}--\r\n".encode("utf-8")
        yeu_cau = urllib.request.Request(
            f"{self.filer_url}{khoa}", data=than, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={RANH_GIOI}"},
        )
        with urllib.request.urlopen(yeu_cau, timeout=60) as tra_loi:
            if not 200 <= tra_loi.status < 300:
                raise RuntimeError(f"filer trả mã {tra_loi.status}")

    def _filer_doc(self, khoa: str) -> bytes | None:
        try:
            with urllib.request.urlopen(f"{self.filer_url}{khoa}", timeout=60) as tra_loi:
                return tra_loi.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except (urllib.error.URLError, OSError):
            raise

    def _filer_xoa(self, khoa: str) -> None:
        try:
            urllib.request.urlopen(urllib.request.Request(f"{self.filer_url}{khoa}", method="DELETE"), timeout=15).close()
        except (urllib.error.URLError, OSError):
            pass

    def _filer_san_sang(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.filer_url}/", timeout=5).close()
            return True
        except urllib.error.HTTPError:
            return True   # máy chủ trả lời (dù 404) là đủ
        except (urllib.error.URLError, OSError):
            return False

    # ---- Luồng tệp ----
    def luu_va_quet(self, nguoi: str, nhom: list[str], ten_goc: str, du_lieu: bytes) -> tuple[int, dict]:
        if len(du_lieu) > MAX_UPLOAD_BYTES:
            return 413, {"loi": "Tệp vượt quá giới hạn 10 MB"}
        ten_sach = lam_sach_ten_tep(ten_goc)
        _, duoi = os.path.splitext(ten_sach.lower())
        if duoi not in DUOI_CHO_PHEP:
            return 415, {"loi": f"Định dạng tệp '{duoi or ten_sach}' không nằm trong danh mục cho phép"}
        sha256 = hashlib.sha256(du_lieu).hexdigest()
        ma_tep = f"tep-{int(time.time() * 1000)}-{sha256[:12]}"
        tam = os.path.join(self.cho_quet_dir, f"{ma_tep}_{ten_sach}")
        with open(tam, "wb") as f:
            f.write(du_lieu)
        os.chmod(tam, 0o600)

        try:
            trang_thai, chi_tiet = quet_noi_dung(tam, self.clamscan_cmd, self.clamav_dir)
        except Exception as e:  # noqa: BLE001 — lỗi công cụ quét thì chưa được coi là sạch
            os.unlink(tam)
            return 503, {"loi": f"Chưa quét được tệp: {e}"}

        ban_ghi = {
            "ten_tep": ten_sach,
            "kich_thuoc": len(du_lieu),
            "sha256": sha256,
            "trang_thai_quet": trang_thai,
            "ket_qua_quet": chi_tiet,
        }

        if trang_thai == "INFECTED":
            os.replace(tam, os.path.join(self.cach_ly_dir, f"{ma_tep}_{ten_sach}"))
            ma, kq = self._ghi_metadata(ban_ghi, nguoi, nhom)
            if ma not in (200, 201):
                return 503, {"loi": "Tệp đã bị cách ly nhưng chưa ghi được metadata", "chi_tiet": kq}
            return 422, {"loi": "Tệp bị chặn do phát hiện mã độc", "tep": kq[0] if isinstance(kq, list) and kq else kq}

        khoa_luu_tru = f"/tep/{nguoi}/{ma_tep}_{ten_sach}"
        try:
            self._filer_luu(khoa_luu_tru, ten_sach, du_lieu)
        except (urllib.error.URLError, OSError, RuntimeError) as e:
            os.unlink(tam)
            return 503, {"loi": f"Kho tệp chưa sẵn sàng: {e}"}
        os.unlink(tam)

        ban_ghi["khoa_luu_tru"] = khoa_luu_tru
        ma, kq = self._ghi_metadata(ban_ghi, nguoi, nhom)
        if ma not in (200, 201):
            self._filer_xoa(khoa_luu_tru)
            return 503, {"loi": "Chưa ghi được metadata tệp — tệp chưa vào kho", "chi_tiet": kq}
        return 201, {"tep": kq[0] if isinstance(kq, list) and kq else kq}

    def doc_tep(self, nguoi: str, nhom: list[str], ma_tep: int) -> tuple[int, bytes | dict, str]:
        ma, kq = self._doc_metadata(ma_tep, nguoi, nhom)
        if ma != 200:
            return (ma if ma in (401, 403) else 502), {"loi": "Chưa đọc được metadata tệp"}, "application/json"
        ban_ghi = kq[0] if isinstance(kq, list) and kq else None
        if not ban_ghi:
            return 404, {"loi": "Không tìm thấy tệp"}, "application/json"
        trang_thai = ban_ghi.get("trang_thai_quet")
        if trang_thai == "PENDING_SCAN":
            return 409, {"loi": "Tệp đang chờ kiểm dịch ClamAV"}, "application/json"
        if trang_thai == "INFECTED":
            return 422, {"loi": "Tệp bị chặn do phát hiện mã độc"}, "application/json"
        khoa = ban_ghi.get("khoa_luu_tru")
        if not khoa:
            return 404, {"loi": "Tệp không còn trong kho lưu trữ"}, "application/json"
        try:
            du_lieu = self._filer_doc(khoa)
        except (urllib.error.URLError, OSError):
            return 502, {"loi": "Kho tệp chưa sẵn sàng"}, "application/json"
        if du_lieu is None:
            return 404, {"loi": "Tệp không còn trong kho lưu trữ"}, "application/json"
        if hashlib.sha256(du_lieu).hexdigest() != ban_ghi.get("sha256"):
            print(f"LỖI: SHA-256 tệp {ma_tep} không khớp metadata", file=sys.stderr, flush=True)
            return 502, {"loi": "Tệp trong kho không khớp SHA-256 đã ghi — không trả tệp hỏng"}, "application/json"
        return 200, du_lieu, "application/octet-stream"


class KhoTepHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "onebee-kho-tep"
    sys_version = ""
    store: KhoTepStore = None  # type: ignore[assignment]

    def log_message(self, *args):
        pass

    def _tra_json(self, ma: int, du_lieu: dict) -> None:
        raw = json.dumps(du_lieu, ensure_ascii=False).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _nguoi_dung(self) -> tuple[str, list[str]]:
        nguoi = (self.headers.get("Remote-User") or "").strip()
        if not TEN_NGUOI.fullmatch(nguoi):
            return "", []   # tên lạ (không thể xuất hiện từ Authelia) → coi như chưa đăng nhập
        nhom = [x.strip() for x in (self.headers.get("Remote-Groups") or "").split(",") if x.strip()]
        return nguoi, nhom

    def _doc_than(self) -> bytes | None:
        """Đọc thân yêu cầu tối đa MAX_UPLOAD_BYTES; quá giới hạn trả None (đã trả 413)."""
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
                if tong > MAX_UPLOAD_BYTES:
                    return None
                phan.append(self.rfile.read(co))
                self.rfile.read(2)
            return b"".join(phan)
        do_dai = int(self.headers.get("Content-Length") or 0)
        if do_dai > MAX_UPLOAD_BYTES:
            # Đọc bỏ thân (tối đa gấp đôi giới hạn) rồi mới trả 413: đóng kết nối khi bên gửi còn đang gửi
            # thì Caddy chỉ thấy kết nối đứt (502) thay vì câu trả lời 413
            con = min(do_dai, 2 * MAX_UPLOAD_BYTES)
            while con > 0 and (manh := self.rfile.read(min(con, 65536))):
                con -= len(manh)
            return None
        return self.rfile.read(do_dai) if do_dai else b""

    def _duong_dan(self) -> str:
        return urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)

    def do_GET(self):  # noqa: N802 — tên do thư viện chuẩn quy định
        duong = self._duong_dan()
        if duong == "/suc-khoe":
            if self.store._filer_san_sang():
                return self._tra_json(200, {"trang_thai": "ok"})
            return self._tra_json(503, {"trang_thai": "chua-san-sang", "loi": "SeaweedFS chưa trả lời"})
        nguoi, nhom = self._nguoi_dung()
        if not nguoi:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO"})
        if duong in ("/", "/danh-sach"):
            ma, kq = self.store.danh_sach(nguoi, nhom)
            return self._tra_json(ma if ma in (200, 401, 403) else 502, kq if isinstance(kq, dict) else {"tep": kq})
        ma_tep = duong.lstrip("/")
        if not ma_tep.isdigit():
            return self._tra_json(404, {"loi": "Không có đường dẫn này"})
        ma, noi_dung, loai = self.store.doc_tep(nguoi, nhom, int(ma_tep))
        if isinstance(noi_dung, dict):
            return self._tra_json(ma, noi_dung)
        self.send_response(ma)
        self.send_header("Content-Type", loai)
        self.send_header("Content-Length", str(len(noi_dung)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(noi_dung)

    def do_PUT(self):  # noqa: N802
        nguoi, nhom = self._nguoi_dung()
        if not nguoi:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO"})
        ten = self._duong_dan().lstrip("/")
        if not ten:
            return self._tra_json(400, {"loi": "Thiếu tên tệp trên đường dẫn"})
        du_lieu = self._doc_than()
        if du_lieu is None:
            return self._tra_json(413, {"loi": "Tệp vượt quá giới hạn 10 MB"})
        ma, kq = self.store.luu_va_quet(nguoi, nhom, ten, du_lieu)
        self._tra_json(ma, kq)

    def do_POST(self):  # noqa: N802
        self.do_PUT()


def main(argv: list[str]) -> int:
    if argv and argv[0] == "cap-nhat-chu-ky":
        if len(argv) < 3:
            sys.exit("Cách dùng: onebee-kho-tep.py cap-nhat-chu-ky <thư-mục-nguồn-cvd> <thư-mục-clamav>")
        try:
            da_chep = cap_nhat_chu_ky_clamav(argv[1], argv[2])
        except (OSError, ValueError) as e:
            sys.exit(f"LỖI: {e}")
        print(f"Đã cập nhật chữ ký ClamAV ngoại tuyến: {', '.join(da_chep)}")
        return 0

    KhoTepHandler.store = KhoTepStore(
        goc_dir=os.environ.get("KHO_TEP_DIR", "/srv/onebee/kho-tep"),
        filer_url=os.environ.get("SEAWEED_FILER_URL", "http://seaweedfs:8888"),
        cau_noi_url=os.environ.get("CAU_NOI_URL", "http://cau-noi:8080"),
        clamscan_cmd=os.environ.get("CLAMSCAN_CMD", "clamscan"),
        clamav_dir=os.environ.get("CLAMAV_DATABASE_DIR", "/var/lib/clamav"),
    )
    may_chu = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), KhoTepHandler)
    may_chu.daemon_threads = True
    print("Dịch vụ kho tệp OneBee: đang nghe cổng %s" % may_chu.server_address[1], file=sys.stderr, flush=True)
    may_chu.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
