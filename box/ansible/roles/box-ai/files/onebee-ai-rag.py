#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Trợ lý OneBee: hỏi đáp trên kho tri thức của Box (chỉ thư viện chuẩn Python).

  onebee-ai-rag.py chay-dich-vu            Chạy máy chủ HTTP nội bộ sau cổng Caddy (cổng 8092)
  onebee-ai-rag.py nap-tri-thuc            In câu lệnh SQL nạp kho tri thức (nhúng bằng Ollama) để onebee-box đưa vào PostgreSQL
  onebee-ai-rag.py khoa cap <loai> <ten>   Cấp khóa API (loai: nguoi | may), in khóa MỘT lần
  onebee-ai-rag.py khoa ds                 Liệt kê người/máy đang có khóa (không in khóa)
  onebee-ai-rag.py khoa go <loai> <ten>    Thu hồi khóa

Dịch vụ đứng sau Caddy forward_auth: chỉ tin Remote-User/Remote-Groups do Caddy chép từ dịch vụ định danh, hoặc khóa API
do onebee-box cấp. Chỉ mở hai đường POST /ai/hoi, /ai/tom-tat và GET /suc-khoe; đường khác trả 404. Câu hỏi được nhúng và
tra trong onebee.tai_lieu_tri_thuc qua cầu nối danh tính (PostgREST giữ quyền tới cấp dòng).

Biến môi trường: AI_OLLAMA_URL, AI_CAU_NOI_URL, AI_MO_HINH, AI_MO_HINH_NHUNG, AI_SO_NGUON, AI_DU_LIEU, AI_LOI_DAN,
AI_TRI_THUC, AI_MAU, AI_TRI_THUC_DON_VI, AI_DIA_CHI, AI_CONG.
"""
import hashlib
import datetime
import http.client
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOI_DA_THAN = 1024 * 1024
NHAC_KIEM_TRA = "Trợ lý có thể sai — hãy kiểm tra lại văn bản gốc trước khi dùng."
TEN_HOP_LE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
KHOA_HOP_LE = re.compile(r"obk-[0-9a-f]{48}")
LOAI_KHOA = ("nguoi", "may")
THU_TRONG_TUAN = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")
TIEU_DE_MO_DAU = "Mở đầu"


def _chuoi_json(gia_tri):
    return json.dumps(gia_tri, ensure_ascii=False, separators=(",", ":"))


def phan_doan(van_ban, toi_da=750):
    """Tách văn bản Markdown thành các đoạn có tiêu đề mục, mỗi đoạn không quá toi_da ký tự."""
    ds = []
    tieu_de = TIEU_DE_MO_DAU
    dem = []

    def xa_doan(noi_dung):
        noi_dung = noi_dung.strip()
        if not noi_dung:
            return
        for manh in _cat_theo_do_dai(noi_dung, toi_da):
            ds.append({"tieu_de": tieu_de, "noi_dung": manh})

    for dong in van_ban.splitlines():
        khop = re.match(r"^#{1,6}\s+(.*\S)\s*$", dong)
        if khop:
            xa_doan("\n".join(dem))
            dem = []
            tieu_de = khop.group(1).strip()
        else:
            dem.append(dong)
    xa_doan("\n".join(dem))
    return ds


def _cat_theo_do_dai(noi_dung, toi_da):
    """Chia nội dung thành mảnh <= toi_da: ưu tiên giữ nguyên đoạn văn, đoạn quá dài thì cắt theo từ."""
    if len(noi_dung) <= toi_da:
        return [noi_dung]
    manh, buf = [], ""
    for doan in re.split(r"\n\s*\n", noi_dung):
        doan = doan.strip()
        if not doan:
            continue
        ung_vien = f"{buf}\n\n{doan}" if buf else doan
        if len(ung_vien) <= toi_da:
            buf = ung_vien
            continue
        if buf:
            manh.append(buf)
            buf = ""
        if len(doan) <= toi_da:
            buf = doan
            continue
        for tu in doan.split():
            ung_vien = f"{buf} {tu}" if buf else tu
            if len(ung_vien) <= toi_da:
                buf = ung_vien
                continue
            if buf:
                manh.append(buf)
            while len(tu) > toi_da:
                manh.append(tu[:toi_da])
                tu = tu[toi_da:]
            buf = tu
    if buf:
        manh.append(buf)
    return [m for m in manh if m]


def _doc_md(tep, nguon):
    with open(tep, encoding="utf-8") as f:
        van_ban = f.read()
    return [{"nguon": nguon, "doan": i, "tieu_de": d["tieu_de"], "noi_dung": d["noi_dung"]}
            for i, d in enumerate(phan_doan(van_ban))]


def _doc_mau_json(tep, nguon):
    try:
        with open(tep, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(d, dict):
        return []
    tieu_de, noi_dung = d.get("title"), d.get("content")
    if not isinstance(tieu_de, str) or not isinstance(noi_dung, str) or not noi_dung.strip():
        return []
    return [{"nguon": nguon, "doan": 0, "tieu_de": tieu_de.strip(), "noi_dung": noi_dung.strip()}]


def doc_nguon(ds_nguon):
    """Đọc các thư mục nguồn (loai, đường dẫn), trả về đoạn tri thức có khóa ổn định (nguon, doan)."""
    ket_qua = []
    for loai, goc in ds_nguon:
        if not os.path.isdir(goc):
            continue
        for thu_muc, _, tep_ds in os.walk(goc):
            for ten in sorted(tep_ds):
                tep = os.path.join(thu_muc, ten)
                tuong_doi = os.path.relpath(tep, goc).replace(os.sep, "/")
                nguon = f"{loai}/{tuong_doi}"
                if ten.endswith(".md"):
                    phan = _doc_md(tep, nguon)
                elif ten.endswith(".json"):
                    phan = _doc_mau_json(tep, nguon)
                else:
                    continue
                for d in phan:
                    d["sha256"] = hashlib.sha256((d["tieu_de"] + "\n" + d["noi_dung"]).encode("utf-8")).hexdigest()
                ket_qua.extend(phan)
    return ket_qua


def dung_tin_nhan(loi_dan, cau_hoi, doan, bay_gio):
    """Dựng tin nhắn gửi Ollama: lời dặn + tài liệu tham khảo có đánh số + yêu cầu trích nguồn và kiểm tra lại."""
    he_thong = loi_dan.replace("{{CURRENT_DATE}}", bay_gio.strftime("%Y-%m-%d"))
    he_thong = he_thong.replace("{{CURRENT_WEEKDAY}}", THU_TRONG_TUAN[bay_gio.weekday()])
    he_thong = re.sub(r"\{\{[^}]*\}\}", "", he_thong)
    if doan:
        dong = ["TÀI LIỆU THAM KHẢO:"]
        for i, d in enumerate(doan, 1):
            dong.append(f"[{i}] {d['tieu_de']} ({d['nguon']})")
            dong.append(d["noi_dung"])
        he_thong += ("\n\n" if he_thong else "") + "\n".join(dong)
    he_thong += ("\n\n" if he_thong else "") + (
        "Khi trả lời, trích nguồn bằng số thứ tự của tài liệu tham khảo trong ngoặc vuông. "
        "Nếu tài liệu tham khảo không đủ để trả lời, nói rõ điều đó và đề nghị người dùng kiểm tra lại văn bản gốc.")
    return [{"role": "system", "content": he_thong}, {"role": "user", "content": cau_hoi}]


def them_nhac_kiem_tra(tra_loi):
    tra_loi = (tra_loi or "").rstrip()
    if tra_loi.endswith(NHAC_KIEM_TRA):
        return tra_loi
    return f"{tra_loi}\n\n{NHAC_KIEM_TRA}" if tra_loi else NHAC_KIEM_TRA


def _sql_chuoi(gia_tri):
    return "'" + str(gia_tri).replace("\0", "").replace("'", "''") + "'"


def _sql_vector(vector):
    return "'" + _chuoi_json([float(x) for x in vector]) + "'"


def sql_nap(doan, vectors, mo_hinh_nhung):
    """Sinh câu lệnh SQL nạp đoạn tri thức: cập nhật đúng dòng cũ, xóa đoạn thừa, không tạo bản trùng."""
    if len(doan) != len(vectors):
        raise ValueError("Số đoạn tri thức và số vector nhúng không khớp")
    dong_values = []
    for d, v in zip(doan, vectors):
        dong_values.append("(" + ", ".join((
            _sql_chuoi(d["nguon"]), str(int(d["doan"])), _sql_chuoi(d["tieu_de"]), _sql_chuoi(d["noi_dung"]),
            _sql_vector(v), _sql_chuoi(d["sha256"]), _sql_chuoi(mo_hinh_nhung))) + ")")
    khoa = ", ".join(f"({_sql_chuoi(d['nguon'])}, {int(d['doan'])})" for d in doan)
    return "\n".join((
        "BEGIN;",
        "DELETE FROM onebee.tai_lieu_tri_thuc",
        f" WHERE (nguon, doan) NOT IN ({khoa});",
        "INSERT INTO onebee.tai_lieu_tri_thuc (nguon, doan, tieu_de, noi_dung, nhung, sha256, mo_hinh_nhung) VALUES",
        ",\n".join(dong_values),
        "ON CONFLICT (nguon, doan) DO UPDATE SET",
        "  tieu_de = EXCLUDED.tieu_de, noi_dung = EXCLUDED.noi_dung, nhung = EXCLUDED.nhung,",
        "  sha256 = EXCLUDED.sha256, mo_hinh_nhung = EXCLUDED.mo_hinh_nhung",
        " WHERE (onebee.tai_lieu_tri_thuc.tieu_de, onebee.tai_lieu_tri_thuc.noi_dung,",
        "        onebee.tai_lieu_tri_thuc.nhung, onebee.tai_lieu_tri_thuc.sha256,",
        "        onebee.tai_lieu_tri_thuc.mo_hinh_nhung)",
        "       IS DISTINCT FROM",
        "       (EXCLUDED.tieu_de, EXCLUDED.noi_dung, EXCLUDED.nhung, EXCLUDED.sha256, EXCLUDED.mo_hinh_nhung);",
        "COMMIT;",
    ))


def _doc_kho(tep):
    try:
        with open(tep, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_kho(tep, kho):
    os.makedirs(os.path.dirname(os.path.abspath(tep)) or ".", exist_ok=True)
    fd, tep_tam = _tao_tep_tam(os.path.dirname(os.path.abspath(tep)) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(kho, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.chmod(tep_tam, 0o644)
        os.replace(tep_tam, tep)
    except BaseException:
        try:
            os.unlink(tep_tam)
        except OSError:
            pass
        raise


def _tao_tep_tam(thu_muc):
    for _ in range(10):
        tep = os.path.join(thu_muc, f".khoa-{secrets.token_hex(8)}")
        try:
            return os.open(tep, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), tep
        except FileExistsError:
            continue
    raise OSError("Không tạo được tệp tạm trong " + thu_muc)


def _kiem_ten(loai, chu):
    if loai not in LOAI_KHOA:
        raise ValueError("Loại khóa phải là nguoi hoặc may")
    if not isinstance(chu, str) or not TEN_HOP_LE.fullmatch(chu):
        raise ValueError("Tên chỉ gồm chữ thường không dấu, số, dấu gạch, tối đa 32 ký tự")


def cap_khoa(tep, loai, chu):
    """Cấp khóa mới cho (loại, tên); khóa cũ cùng tên mất hiệu lực ngay. Chỉ lưu bản băm."""
    _kiem_ten(loai, chu)
    kho = _doc_kho(tep)
    for bam, muc in list(kho.items()):
        if isinstance(muc, dict) and muc.get("loai") == loai and muc.get("chu") == chu:
            del kho[bam]
    khoa = "obk-" + secrets.token_hex(24)
    kho[hashlib.sha256(khoa.encode("ascii")).hexdigest()] = {"loai": loai, "chu": chu}
    _ghi_kho(tep, kho)
    return khoa


def tra_khoa(tep, khoa):
    if not isinstance(khoa, str) or not KHOA_HOP_LE.fullmatch(khoa):
        return None
    muc = _doc_kho(tep).get(hashlib.sha256(khoa.encode("ascii")).hexdigest())
    if not isinstance(muc, dict) or muc.get("loai") not in LOAI_KHOA or not isinstance(muc.get("chu"), str):
        return None
    return {"loai": muc["loai"], "chu": muc["chu"]}


def go_khoa(tep, loai, chu):
    _kiem_ten(loai, chu)
    kho = _doc_kho(tep)
    bo = [bam for bam, muc in kho.items() if isinstance(muc, dict) and muc.get("loai") == loai and muc.get("chu") == chu]
    if not bo:
        return False
    for bam in bo:
        del kho[bam]
    _ghi_kho(tep, kho)
    return True


def danh_sach_khoa(tep):
    ds = []
    for muc in _doc_kho(tep).values():
        if isinstance(muc, dict) and muc.get("loai") in LOAI_KHOA and isinstance(muc.get("chu"), str):
            ds.append((muc["loai"], muc["chu"]))
    return sorted(ds)


def _goi_json(url, than, tieu_de=None, timeout=60):
    du_lieu = json.dumps(than, ensure_ascii=False).encode("utf-8") if than is not None else None
    req = urllib.request.Request(url, data=du_lieu, method="POST",
                                 headers={"Content-Type": "application/json", **(tieu_de or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


def _nhung(cau_hinh, cau_hoi):
    _, d = _goi_json(cau_hinh["ollama_url"] + "/api/embed",
                     {"model": cau_hinh["mo_hinh_nhung"], "input": [cau_hoi]})
    return d["embeddings"][0]


def _tim_tri_thuc(cau_hinh, cau_hoi, nguoi, nhom):
    try:
        vector = _nhung(cau_hinh, cau_hoi)
    except (OSError, ValueError, KeyError, IndexError, urllib.error.URLError, http.client.HTTPException):
        return []
    try:
        _, d = _goi_json(cau_hinh["cau_noi_url"] + "/api/rpc/tim_tri_thuc",
                         {"truy_van": _chuoi_json([float(x) for x in vector]), "so_luong": int(cau_hinh["so_nguon"])},
                         {"Remote-User": nguoi, "Remote-Groups": nhom})
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        return []
    return d if isinstance(d, list) else []


def _hoi_ollama(cau_hinh, tin_nhan):
    return _goi_json(cau_hinh["ollama_url"] + "/api/chat",
                     {"model": cau_hinh["mo_hinh"], "messages": tin_nhan, "stream": False}, timeout=300)


def _luu_lich_su(cau_hinh, nguoi, nhom, cau_hoi, tra_loi):
    try:
        _goi_json(cau_hinh["cau_noi_url"] + "/api/lich_su_hoi_ai",
                  {"cau_hoi": cau_hoi, "tra_loi": tra_loi},
                  {"Remote-User": nguoi, "Remote-Groups": nhom})
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        pass


def _dinh_danh(handler, cau_hinh):
    """Trả về (nguoi, nhom) từ Remote-* do Caddy chép, hoặc từ khóa API; None nếu không hợp lệ."""
    nguoi_ds = handler.headers.get_all("Remote-User") or []
    nhom_ds = handler.headers.get_all("Remote-Groups") or []
    if len(nguoi_ds) == 1 and len(nhom_ds) == 1 and nhom_ds[0].strip() and TEN_HOP_LE.fullmatch(nguoi_ds[0]):
        return nguoi_ds[0], nhom_ds[0]
    khoa_tep = cau_hinh.get("khoa_tep") or os.path.join(cau_hinh.get("du_lieu", "/data"), "khoa-hoi.json")
    muc = tra_khoa(khoa_tep, handler.headers.get("X-OneBee-Khoa") or "")
    if muc is None:
        return None
    if muc["loai"] == "may":
        return "may", "nhan_vien"
    return muc["chu"], "nhan_vien"


def tao_may_chu(cau_hinh, dia_chi):
    class XuLy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "onebee-ai-rag"
        sys_version = ""

        def log_message(self, *a):
            pass

        def _tra(self, ma, du_lieu, nguoi="-", dong=False):
            than = json.dumps(du_lieu, ensure_ascii=False).encode("utf-8")
            self.send_response(ma)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(than)))
            self.send_header("Cache-Control", "no-store")
            if dong:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(than)
            duong_dan = urllib.parse.urlsplit(self.path).path
            print(f"{nguoi} {self.command} {duong_dan} {ma}", file=sys.stderr, flush=True)

        def _doc_than(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0:
                return None
            if n > TOI_DA_THAN:
                con = min(n, 2 * TOI_DA_THAN)
                try:
                    while con > 0 and (manh := self.rfile.read(min(con, 65536))):
                        con -= len(manh)
                except OSError:
                    pass
                return False
            raw = self.rfile.read(n) if n else b""
            try:
                d = json.loads(raw) if raw else None
            except ValueError:
                return None
            return d if isinstance(d, dict) else None

        def _xu_ly_hoi(self, nguoi, nhom):
            than = self.than
            if than is None:
                return self._tra(400, {"loi": "Dữ liệu gửi lên không hợp lệ"}, nguoi)
            cau_hoi = than.get("cau_hoi")
            if not isinstance(cau_hoi, str) or not cau_hoi.strip():
                return self._tra(400, {"loi": "Thiếu câu hỏi"}, nguoi)
            cau_hoi = cau_hoi.strip()
            doan = _tim_tri_thuc(cau_hinh, cau_hoi, nguoi, nhom)
            try:
                _, d = _hoi_ollama(cau_hinh, dung_tin_nhan(cau_hinh["loi_dan"], cau_hoi, doan, datetime.datetime.now()))
                tra_loi = them_nhac_kiem_tra(d["message"]["content"])
            except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, http.client.HTTPException):
                return self._tra(503, {"loi": "Ollama chưa sẵn sàng hoặc không trả lời — thử lại sau ít phút"}, nguoi)
            _luu_lich_su(cau_hinh, nguoi, nhom, cau_hoi, tra_loi)
            return self._tra(200, {"tra_loi": tra_loi,
                                   "nguon": [{"nguon": x.get("nguon"), "tieu_de": x.get("tieu_de")}
                                             for x in doan if isinstance(x, dict)]}, nguoi)

        def _xu_ly_tom_tat(self, nguoi):
            than = self.than
            if than is None:
                return self._tra(400, {"loi": "Dữ liệu gửi lên không hợp lệ"}, nguoi)
            noi_dung = than.get("noi_dung")
            if not isinstance(noi_dung, str) or not noi_dung.strip():
                return self._tra(400, {"loi": "Thiếu nội dung cần tóm tắt"}, nguoi)
            he_thong = cau_hinh["loi_dan"].replace("{{CURRENT_DATE}}", datetime.datetime.now().strftime("%Y-%m-%d"))
            he_thong = he_thong.replace("{{CURRENT_WEEKDAY}}", THU_TRONG_TUAN[datetime.datetime.now().weekday()])
            he_thong = re.sub(r"\{\{[^}]*\}\}", "", he_thong)
            he_thong += ("\n\n" if he_thong else "") + (
                "Tóm tắt văn bản người dùng gửi, giữ nguyên số liệu, tên riêng và ngày tháng; không thêm thông tin không có trong văn bản.")
            try:
                _, d = _hoi_ollama(cau_hinh, [{"role": "system", "content": he_thong},
                                              {"role": "user", "content": noi_dung.strip()}])
                tom_tat = them_nhac_kiem_tra(d["message"]["content"])
            except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, http.client.HTTPException):
                return self._tra(503, {"loi": "Ollama chưa sẵn sàng hoặc không trả lời — thử lại sau ít phút"}, nguoi)
            return self._tra(200, {"tom_tat": tom_tat}, nguoi)

        def do_GET(self):
            duong_dan = urllib.parse.urlsplit(self.path).path
            if duong_dan == "/suc-khoe":
                return self._tra(200, {"trang_thai": "ok"})
            return self._tra(404, {"loi": "Không có đường dẫn này"})

        def do_POST(self):
            duong_dan = urllib.parse.urlsplit(self.path).path
            self.than = self._doc_than()
            dinh_danh = _dinh_danh(self, cau_hinh)
            nguoi = dinh_danh[0] if dinh_danh else "-"
            if duong_dan not in ("/ai/hoi", "/ai/tom-tat"):
                return self._tra(404, {"loi": "Không có đường dẫn này"}, nguoi)
            if self.than is False:
                return self._tra(413, {"loi": "Dữ liệu gửi lên quá 1 MB"}, nguoi)
            if dinh_danh is None:
                return self._tra(401, {"loi": "Chưa đăng nhập hoặc khóa API không hợp lệ"}, nguoi)
            if duong_dan == "/ai/hoi":
                return self._xu_ly_hoi(*dinh_danh)
            return self._xu_ly_tom_tat(nguoi)

        def do_HEAD(self):
            return self.do_GET()

        def do_PUT(self):
            return self._tra(404, {"loi": "Không có đường dẫn này"})

        do_DELETE = do_PATCH = do_OPTIONS = do_PUT

    may_chu = ThreadingHTTPServer(dia_chi, XuLy)
    may_chu.daemon_threads = True
    return may_chu


def _cau_hinh_tu_moi_truong():
    return {
        "ollama_url": os.environ.get("AI_OLLAMA_URL", "http://ollama:11434").rstrip("/"),
        "cau_noi_url": os.environ.get("AI_CAU_NOI_URL", "http://cau-noi:8080").rstrip("/"),
        "mo_hinh": os.environ.get("AI_MO_HINH", "gemma4:e2b-it-qat"),
        "mo_hinh_nhung": os.environ.get("AI_MO_HINH_NHUNG", "nomic-embed-text:v1.5"),
        "so_nguon": int(os.environ.get("AI_SO_NGUON", "3")),
        "du_lieu": os.environ.get("AI_DU_LIEU", "/data"),
        "loi_dan": _doc_loi_dan(os.environ.get("AI_LOI_DAN", "/app/tro-ly-onebee-loi-dan.md")),
        "khoa_tep": os.path.join(os.environ.get("AI_DU_LIEU", "/data"), "khoa-hoi.json"),
    }


def _doc_loi_dan(tep):
    try:
        with open(tep, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        sys.exit(f"LỖI: không đọc được lời dặn {tep}: {e.strerror}")


def _nguon_tu_moi_truong():
    return [("tri-thuc", os.environ.get("AI_TRI_THUC", "/app/knowledge")),
            ("mau-soan-thao", os.environ.get("AI_MAU", "/app/prompts")),
            ("don-vi", os.environ.get("AI_TRI_THUC_DON_VI", "/du-lieu-tri-thuc"))]


def _nap_tri_thuc():
    doan = doc_nguon(_nguon_tu_moi_truong())
    if not doan:
        print("Không có tài liệu trong các thư mục tri thức", file=sys.stderr)
        return 1
    ollama_url = os.environ.get("AI_OLLAMA_URL", "http://ollama:11434").rstrip("/")
    mo_hinh = os.environ.get("AI_MO_HINH_NHUNG", "nomic-embed-text:v1.5")
    vectors = []
    try:
        for bat_dau in range(0, len(doan), 32):
            lo = doan[bat_dau:bat_dau + 32]
            _, d = _goi_json(ollama_url + "/api/embed",
                             {"model": mo_hinh, "input": [x["tieu_de"] + "\n" + x["noi_dung"] for x in lo]},
                             timeout=300)
            vectors.extend(d["embeddings"])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Ollama chưa có mô hình nhúng {mo_hinh} — tải trước rồi chạy lại", file=sys.stderr)
            return 3
        print(f"LỖI: Ollama không nhúng được tài liệu (mã {e.code})", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, urllib.error.URLError, http.client.HTTPException) as e:
        print(f"LỖI: không gọi được Ollama để nhúng tài liệu: {e}", file=sys.stderr)
        return 2
    if len(vectors) != len(doan):
        print("LỖI: số vector nhúng không khớp số đoạn tri thức", file=sys.stderr)
        return 2
    print(sql_nap(doan, vectors, mo_hinh))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    lenh = argv[0]
    if lenh == "chay-dich-vu":
        cau_hinh = _cau_hinh_tu_moi_truong()
        may_chu = tao_may_chu(cau_hinh, (os.environ.get("AI_DIA_CHI", "0.0.0.0"), int(os.environ.get("AI_CONG", "8092"))))
        print(f"Trợ lý OneBee: nghe cổng {may_chu.server_address[1]}, mô hình {cau_hinh['mo_hinh']}", file=sys.stderr, flush=True)
        may_chu.serve_forever()
        return 0
    if lenh == "nap-tri-thuc":
        return _nap_tri_thuc()
    if lenh == "kiem-ollama":
        ollama_url = os.environ.get("AI_OLLAMA_URL", "http://ollama:11434").rstrip("/")
        mo_hinh = os.environ.get("AI_MO_HINH", "gemma4:e2b-it-qat")
        bat_dau = time.time()
        try:
            ma, _ = _goi_json(ollama_url + "/api/generate",
                              {"model": mo_hinh, "prompt": "test", "stream": False, "options": {"num_predict": 8}},
                              timeout=120)
        except urllib.error.HTTPError as e:
            ma = e.code
        except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
            print("000 0")
            return 1
        print(f"{ma} {time.time() - bat_dau:.1f}")
        return 0
    if lenh == "khoa":
        tep = os.path.join(os.environ.get("AI_DU_LIEU", "/data"), "khoa-hoi.json")
        if len(argv) == 2 and argv[1] == "ds":
            for loai, chu in danh_sach_khoa(tep):
                print(f"{loai} {chu}")
            return 0
        if len(argv) == 4 and argv[1] in ("cap", "go"):
            try:
                if argv[1] == "cap":
                    print(cap_khoa(tep, argv[2], argv[3]))
                    return 0
                return 0 if go_khoa(tep, argv[2], argv[3]) else 1
            except ValueError as e:
                print(f"LỖI: {e}", file=sys.stderr)
                return 1
        print("Cách dùng: khoa cap|go <nguoi|may> <ten> | khoa ds", file=sys.stderr)
        return 2
    print(f"LỆNH KHÔNG HỢP LỆ: {lenh}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
