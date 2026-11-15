#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Dịch vụ Trợ lý AI & RAG nhẹ trên lõi (Python 3.14 stdlib, MIT) cho OneBee Box.

Hỗ trợ cả chạy làm dịch vụ HTTP nội bộ (cổng 8092, sau Caddy) và CLI quản trị (`onebee-box`):
  onebee-ai-rag.py chay-dich-vu        Chạy HTTP server phục vụ Web UI + /ai/* + /api/*
  onebee-ai-rag.py dong-bo-tro-ly      Đồng bộ lời dặn & gợi ý cho "Trợ lý OneBee"
  onebee-ai-rag.py dong-bo-prompts     Đồng bộ kho mẫu prompt hành chính (NĐ 30, Luật HTX)
  onebee-ai-rag.py dong-bo-tri-thuc    Lập chỉ mục RAG (knowledge/*.md) & đồng bộ PostgREST (nếu có)
  onebee-ai-rag.py cap-khoa <ten>      Cấp khóa API cho máy trạm may-<ten> (băm SHA-256)
  onebee-ai-rag.py lay-khoa <ten>      Đọc khóa API hiện có của máy trạm may-<ten>
  onebee-ai-rag.py xoay-khoa <ten>     Sinh khóa mới cho may-<ten>, vô hiệu khóa cũ ngay
  onebee-ai-rag.py doi-mat-khau-quan-tri  Đổi mật khẩu quản trị (biến ONEBEE_MAT_KHAU_MOI)
  onebee-ai-rag.py xoa-tai-khoan <ten> Xóa khóa & tài khoản may-<ten> (idempotent)
"""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import html
import json
import math
import os
import re
import secrets
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NHAC_KIEM_TRA = "AI có thể sai sót, vui lòng đối chiếu lại văn bản gốc trước khi ký ban hành."
MAX_BODY_BYTES = 1024 * 1024  # 1 MB

PII_KEY_CAM = {
    "ten", "ho_ten", "fullname", "full_name", "name", "ten_nhan_vien", "ten_khach_hang",
    "nguoi_gui", "nguoi_nhan", "email", "mail", "sdt", "so_dien_thoai", "dien_thoai",
    "phone", "mobile", "cccd", "so_cccd", "cmnd", "so_cmnd", "ho_chieu", "passport",
    "dia_chi", "address", "mat_khau", "password", "token", "secret", "api_key",
    "so_tai_khoan", "stk", "tai_khoan_ngan_hang",
}
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_SDT_VN = re.compile(r"(?<!\d)(?:\+84|84|0)(?:3|5|7|8|9)\d{8}(?!\d)")
RE_CCCD = re.compile(r"(?<!\d)\d{12}(?!\d)")

STOPWORDS_VI = {
    "la", "va", "cua", "cho", "trong", "khi", "nao", "the", "ve", "nhu", "voi",
    "duoc", "khong", "co", "cac", "nhung", "mot", "hay", "gi", "sao", "tai",
    "toi", "minh", "ban", "anh", "chi", "em", "de", "tu", "den", "theo", "tren",
    "duoi", "nay", "do", "day", "kia", "thi", "ma", "neu", "vi", "nen", "da",
    "se", "dang", "rat", "lam", "bao", "nhieu", "ai", "o", "dau",
}


def cfg_secrets_dir() -> str:
    return os.environ.get("ONEBEE_SECRETS", "/etc/onebee-box/secrets")


def cfg_data_dir() -> str:
    env_dir = os.environ.get("ONEBEE_AI_DATA")
    if env_dir:
        return env_dir
    if os.path.isdir("/data") and os.access("/data", os.W_OK):
        return "/data"
    if os.path.isdir("/srv/onebee/ai-rag") and os.access("/srv/onebee/ai-rag", os.W_OK):
        return "/srv/onebee/ai-rag"
    return os.path.join(BASE_DIR, ".ai-rag-data")


def cfg_prompts_dir() -> str:
    return os.environ.get("ONEBEE_PROMPTS_DIR", os.path.join(BASE_DIR, "prompts"))


def cfg_knowledge_dirs() -> list[str]:
    raw = os.environ.get("ONEBEE_KNOWLEDGE_DIRS", "")
    if raw.strip():
        return [p for p in raw.split(os.pathsep) if p.strip()]
    return [os.path.join(BASE_DIR, "knowledge"), "/usr/local/share/onebee-box/knowledge"]


def cfg_loi_dan_path() -> str:
    return os.environ.get("ONEBEE_LOI_DAN", os.path.join(BASE_DIR, "tro-ly-onebee-loi-dan.md"))


def cfg_goi_y_path() -> str:
    return os.environ.get("ONEBEE_GOI_Y", os.path.join(BASE_DIR, "goi-y.json"))


def cfg_tokens_file() -> str:
    return os.environ.get("ONEBEE_AI_TOKENS_FILE", os.path.join(cfg_secrets_dir(), "ai-tokens.json"))


def cfg_users_file() -> str:
    return os.environ.get("ONEBEE_AI_USERS_FILE", os.path.join(cfg_data_dir(), "ai-users.json"))


def cfg_ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")


def cfg_model_nen() -> str:
    return os.environ.get("ONEBEE_AI_MODEL", "gemma4:e2b-it-qat")


def cfg_admin_email() -> str:
    return os.environ.get("AI_ADMIN_EMAIL", "quantri@onebee.lan").strip().lower()


def _doc_secret(path_env: str, val_env: str, default_name: str, fallback: str = "") -> str:
    val = os.environ.get(val_env, "").strip()
    if val:
        return val
    path = os.environ.get(path_env, "").strip() or os.path.join(cfg_secrets_dir(), default_name)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return fallback


def cfg_admin_password() -> str:
    return _doc_secret("AI_ADMIN_PASSWORD_FILE", "AI_ADMIN_PASSWORD", "ai-admin-password", "")


_EPHEMERAL_KEY = secrets.token_bytes(32)


def cfg_secret_key() -> bytes:
    raw = _doc_secret("AI_SECRET_KEY_FILE", "AI_RAG_SECRET_KEY", "ai-secret-key", "")
    if raw:
        return hashlib.sha256(raw.encode("utf-8")).digest()
    return _EPHEMERAL_KEY


def cfg_cors_origins() -> set[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGIN", "")
    return {x.strip() for x in raw.split(";") if x.strip()}


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        alg, it_s, salt, expected = stored.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(it_s))
        return hmac.compare_digest(dk.hex(), expected)
    except (ValueError, TypeError):
        return False


def _atomic_write_json(path: str, data: object, mode: int = 0o600) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=parent)
    try:
        os.chmod(tmp_path, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _read_json(path: str, default: object) -> object:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def bo_dau(text: str) -> str:
    """Chuẩn hóa tiếng Việt về không dấu chữ thường để tăng độ phủ tìm kiếm RAG."""
    nfd = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "d"))
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn").lower()


def tach_tu(text: str) -> list[str]:
    norm = bo_dau(text)
    tokens = re.findall(r"[a-z0-9]{2,}", norm)
    return [t for t in tokens if t not in STOPWORDS_VI] or tokens


def chunk_markdown(text: str, nguon: str, max_chars: int = 750) -> list[dict]:
    """Tách tài liệu Markdown thành các đoạn tri thức có giữ tiêu đề mục (heading breadcrumb)."""
    ten_goc = nguon
    sections: list[tuple[str, list[str]]] = []
    h1 = ""
    h2 = ""
    h3 = ""
    buf: list[str] = []

    def title_hien_tai() -> str:
        parts = [p for p in (h1, h2, h3) if p]
        return " — ".join(parts) if parts else ten_goc

    def flush() -> None:
        nonlocal buf
        nd = "\n".join(buf).strip()
        if nd:
            sections.append((title_hien_tai(), [nd]))
        buf = []

    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            flush()
            h1 = s[2:].strip()
            if ten_goc == nguon and h1:
                ten_goc = h1
            h2, h3 = "", ""
        elif s.startswith("## "):
            flush()
            h2 = s[3:].strip()
            h3 = ""
        elif s.startswith("### "):
            flush()
            h3 = s[4:].strip()
        else:
            buf.append(line)
    flush()

    chunks: list[dict] = []
    idx = 0
    for tieu_de, blocks in sections:
        nd = "\n".join(blocks).strip()
        if not nd:
            continue
        if len(nd) <= max_chars:
            idx += 1
            chunks.append({
                "id": f"{nguon}#{idx}",
                "nguon": nguon,
                "tieu_de": tieu_de,
                "doan": nd,
            })
            continue
        # Mục dài: tách theo đoạn trống hoặc gạch đầu dòng; nếu vẫn vượt max_chars thì ngắt theo từ
        paragraphs = re.split(r"\n(?=\d+\.\s|-\s|\n)", nd)
        pieces: list[str] = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if len(p) <= max_chars:
                pieces.append(p)
                continue
            cur_w = ""
            for w in p.split():
                if cur_w and len(cur_w) + 1 + len(w) > max_chars:
                    pieces.append(cur_w)
                    cur_w = w
                else:
                    cur_w = f"{cur_w} {w}".strip() if cur_w else w
            if cur_w:
                pieces.append(cur_w)
        cur = ""
        for p in pieces:
            if cur and len(cur) + 1 + len(p) > max_chars:
                idx += 1
                chunks.append({
                    "id": f"{nguon}#{idx}",
                    "nguon": nguon,
                    "tieu_de": tieu_de,
                    "doan": cur,
                })
                cur = p
            else:
                cur = f"{cur}\n{p}".strip() if cur else p
        if cur:
            idx += 1
            chunks.append({
                "id": f"{nguon}#{idx}",
                "nguon": nguon,
                "tieu_de": tieu_de,
                "doan": cur,
            })
    return chunks


def nap_kho_tri_thuc_tu_tep() -> list[dict]:
    """Đọc toàn bộ *.md trong KNOWLEDGE_DIRS (không trùng tên file ưu tiên thư mục trước)."""
    da_thay: set[str] = set()
    chunks: list[dict] = []
    for d in cfg_knowledge_dirs():
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".md") or fname in da_thay:
                continue
            da_thay.add(fname)
            fpath = os.path.join(d, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, encoding="utf-8") as f:
                chunks.extend(chunk_markdown(f.read(), fname))
    return chunks


def tai_chi_muc_tri_thuc() -> list[dict]:
    index_path = os.path.join(cfg_data_dir(), "knowledge-index.json")
    du_lieu = _read_json(index_path, None)
    if isinstance(du_lieu, dict) and isinstance(du_lieu.get("chunks"), list):
        return du_lieu["chunks"]
    return nap_kho_tri_thuc_tu_tep()


def tim_doan_lien_quan(cau_hoi: str, chunks: list[dict] | None = None, top_k: int = 4) -> list[dict]:
    """Truy xuất top-K đoạn tri thức liên quan nhất bằng BM25 tiếng Việt không dấu."""
    if chunks is None:
        chunks = tai_chi_muc_tri_thuc()
    if not chunks or not cau_hoi.strip():
        return []

    q_tokens = tach_tu(cau_hoi)
    if not q_tokens:
        return []
    q_norm = bo_dau(cau_hoi)

    docs_tokens: list[list[str]] = []
    title_tokens: list[list[str]] = []
    df: dict[str, int] = {}
    for ch in chunks:
        t_tok = tach_tu(ch.get("tieu_de", ""))
        b_tok = tach_tu(ch.get("doan", ""))
        title_tokens.append(t_tok)
        docs_tokens.append(b_tok)
        for tok in set(t_tok + b_tok):
            df[tok] = df.get(tok, 0) + 1

    n_docs = len(chunks)
    avgdl = sum(len(d) for d in docs_tokens) / max(n_docs, 1)
    k1, b = 1.5, 0.75
    scored: list[tuple[float, dict]] = []

    for i, ch in enumerate(chunks):
        b_tok = docs_tokens[i]
        t_tok = title_tokens[i]
        dl = len(b_tok) or 1
        tf_body: dict[str, int] = {}
        for tok in b_tok:
            tf_body[tok] = tf_body.get(tok, 0) + 1
        tf_title = set(t_tok)

        score = 0.0
        for qt in set(q_tokens):
            n_q = df.get(qt, 0)
            if n_q == 0:
                continue
            idf = math.log(1.0 + (n_docs - n_q + 0.5) / (n_q + 0.5))
            tf = tf_body.get(qt, 0)
            if tf > 0:
                score += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (dl / max(avgdl, 1.0)))))
            if qt in tf_title:
                score += idf * 1.4
        # Cụm từ 2 âm tiết liên tiếp (tiếng Việt) + mã điều khoản quan trọng
        haystack_words = " ".join(t_tok + b_tok)
        for j in range(len(q_tokens) - 1):
            if f"{q_tokens[j]} {q_tokens[j + 1]}" in haystack_words:
                score += 2.2
        haystack = bo_dau(ch.get("tieu_de", "") + "\n" + ch.get("doan", ""))
        for special in re.findall(r"(?:30/2020|nd-cp|htx|2023|30%|5%|50%|dieu \d+)", q_norm):
            if special in haystack:
                score += 2.5

        if score > 0:
            scored.append((score, ch))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "nguon": ch["nguon"],
            "tieu_de": ch["tieu_de"],
            "doan": ch["doan"],
            "score": round(sc, 3),
        }
        for sc, ch in scored[:top_k]
    ]


def kiem_tra_pii_tom_tat(payload: object) -> tuple[bool, str | None]:
    """Chặn dữ liệu định danh cá nhân (PII) trước khi tóm tắt số liệu bằng LLM."""
    if not isinstance(payload, dict) or not payload:
        return False, "Yêu cầu dữ liệu JSON dạng đối tượng gồm các số liệu tổng hợp."

    def quet(obj: object, prefix: str = "") -> str | None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_str = str(k).strip()
                k_norm = bo_dau(k_str).replace("-", "_").replace(" ", "_")
                if k_norm in PII_KEY_CAM or any(
                    k_norm.startswith(p + "_") or k_norm.endswith("_" + p)
                    for p in ("email", "sdt", "cccd", "cmnd", "ho_ten", "password", "mat_khau", "token", "dia_chi", "phone")
                ):
                    return f"Từ chối trường chứa thông tin cá nhân/nhạy cảm: '{k_str}'"
                err = quet(v, f"{prefix}.{k_str}" if prefix else k_str)
                if err:
                    return err
        elif isinstance(obj, list):
            for item in obj:
                err = quet(item, prefix)
                if err:
                    return err
        elif isinstance(obj, str):
            if RE_EMAIL.search(obj):
                return f"Từ chối giá trị chứa email ở trường '{prefix}'"
            if RE_SDT_VN.search(obj):
                return f"Từ chối giá trị chứa số điện thoại ở trường '{prefix}'"
            if RE_CCCD.search(obj):
                return f"Từ chối giá trị chứa số CCCD/định danh ở trường '{prefix}'"
        return None

    err = quet(payload)
    if err:
        return False, err
    return True, None


def nap_loi_dan() -> str:
    path = cfg_loi_dan_path()
    try:
        with open(path, encoding="utf-8") as f:
            nd = f.read()
    except OSError:
        nd = "Bạn là Trợ lý OneBee. Hôm nay là {{CURRENT_DATE}}. Hãy trả lời ngắn gọn bằng tiếng Việt."
    return nd.replace("{{CURRENT_DATE}}", date.today().strftime("%d/%m/%Y"))


def nap_goi_y() -> list[dict]:
    raw = _read_json(cfg_goi_y_path(), [])
    return raw if isinstance(raw, list) else []


def nap_prompts() -> list[dict]:
    pdir = cfg_prompts_dir()
    if not os.path.isdir(pdir):
        return []
    ds: list[dict] = []
    for fname in sorted(os.listdir(pdir)):
        if not fname.endswith(".json"):
            continue
        d = _read_json(os.path.join(pdir, fname), None)
        if not isinstance(d, dict) or not d.get("command") or not d.get("content"):
            continue
        cmd = str(d["command"]).lstrip("/")
        title = str(d.get("title") or d.get("name") or cmd)
        ds.append({
            "id": cmd,
            "command": cmd,
            "title": title,
            "name": title,
            "content": str(d["content"]),
        })
    return ds


def _load_tokens_store() -> dict:
    du_lieu = _read_json(cfg_tokens_file(), {"tokens": {}})
    if not isinstance(du_lieu, dict) or not isinstance(du_lieu.get("tokens"), dict):
        return {"tokens": {}}
    return du_lieu


def _save_tokens_store(store: dict) -> None:
    _atomic_write_json(cfg_tokens_file(), store, mode=0o600)


def _load_users_store() -> dict:
    du_lieu = _read_json(cfg_users_file(), {"users": {}})
    if not isinstance(du_lieu, dict) or not isinstance(du_lieu.get("users"), dict):
        return {"users": {}}
    return du_lieu


def _save_users_store(store: dict) -> None:
    _atomic_write_json(cfg_users_file(), store, mode=0o600)


def xac_thuc_tai_khoan(email: str, password: str) -> dict | None:
    em = email.strip().lower()
    if not em or not password:
        return None
    if em == cfg_admin_email():
        pw_file = cfg_admin_password()
        if pw_file and hmac.compare_digest(password, pw_file):
            return {"id": "admin", "email": em, "name": "Quản trị OneBee", "role": "admin"}
    users = _load_users_store().get("users", {})
    for u in users.values():
        if u.get("email", "").lower() == em and _verify_password(password, u.get("password_hash", "")):
            return {"id": u.get("id", em), "email": em, "name": u.get("name", em), "role": u.get("role", "user")}
    return None


def tao_phien_token(user: dict, ttl_seconds: int = 86400 * 30) -> str:
    payload = json.dumps({
        "sub": user["email"],
        "role": user["role"],
        "exp": int(datetime.now(timezone.utc).timestamp()) + ttl_seconds,
    }, separators=(",", ":")).encode("utf-8")
    b64 = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    sig = hmac.new(cfg_secret_key(), b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"ob1.{b64}.{sig}"


def giai_ma_phien_token(token: str) -> dict | None:
    if not token or not token.startswith("ob1."):
        return None
    parts = token.split(".", 2)
    if len(parts) != 3:
        return None
    _, b64, sig = parts
    expected = hmac.new(cfg_secret_key(), b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        pad = "=" * ((4 - len(b64) % 4) % 4)
        data = json.loads(base64.urlsafe_b64decode((b64 + pad).encode("ascii")).decode("utf-8"))
        if int(data.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return {"email": data["sub"], "role": data.get("role", "user"), "via": "session"}
    except (ValueError, KeyError, TypeError):
        return None


def xac_thuc_bearer_token(token: str) -> dict | None:
    if not token:
        return None
    sess = giai_ma_phien_token(token)
    if sess:
        return sess
    digest = sha256_hex(token)
    tokens = _load_tokens_store().get("tokens", {})
    for tid, info in tokens.items():
        stored_hash = info.get("sha256", "")
        if stored_hash and hmac.compare_digest(digest, stored_hash):
            return {
                "id": tid,
                "email": info.get("email", f"{tid}@onebee.lan"),
                "name": info.get("name", tid),
                "role": info.get("role", "user"),
                "via": "api_key",
            }
    return None


def _sync_postgrest_rag(chunks: list[dict]) -> bool:
    """Đồng bộ bảng `tai_lieu_tri_thuc` qua PostgREST nếu được cấu hình (best-effort)."""
    pg_url = os.environ.get("POSTGREST_URL", "").rstrip("/")
    if not pg_url:
        return False
    rows = [{"nguon": c["nguon"], "tieu_de": c["tieu_de"], "noi_dung_doan": c["doan"]} for c in chunks]
    try:
        req = urllib.request.Request(
            f"{pg_url}/tai_lieu_tri_thuc",
            data=json.dumps(rows).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200, 201, 204)
    except Exception:
        return False


def _doc_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def dong_bo_tro_ly() -> str:
    """Nạp lời dặn, 4 gợi ý và cấu hình model cho Trợ lý OneBee (idempotent)."""
    path = os.path.join(cfg_data_dir(), "assistant-config.json")
    moi = {
        "id": "onebee-tro-ly",
        "name": "Trợ lý OneBee",
        "base_model_id": cfg_model_nen(),
        "system_raw": _doc_text(cfg_loi_dan_path()),
        "suggestion_prompts": nap_goi_y(),
        "public_url": os.environ.get("ONEBEE_AI_PUBLIC_URL", ""),
    }
    cu = _read_json(path, None)
    if cu is None:
        _atomic_write_json(path, moi, mode=0o644)
        print("Trợ lý OneBee: đã tạo")
        return "created"
    if cu != moi:
        _atomic_write_json(path, moi, mode=0o644)
        print("Trợ lý OneBee: đã cập nhật")
        return "updated"
    print("Trợ lý OneBee: không đổi")
    return "unchanged"


def dong_bo_prompts() -> int:
    """Đồng bộ kho mẫu prompt hành chính NĐ 30 & Luật HTX 2023 (idempotent)."""
    path = os.path.join(cfg_data_dir(), "prompts-cache.json")
    ds = nap_prompts()
    cu = _read_json(path, None)
    if cu != ds:
        _atomic_write_json(path, ds, mode=0o644)
        trang_thai = "đã tạo" if cu is None else "đã cập nhật"
        print(f"Mẫu soạn thảo: {trang_thai} {len(ds)} mẫu")
    else:
        print(f"Mẫu soạn thảo: không đổi ({len(ds)} mẫu)")
    return len(ds)


def dong_bo_tri_thuc() -> int:
    """Phân đoạn & lập chỉ mục kho tri thức pháp lý RAG (idempotent)."""
    chunks = nap_kho_tri_thuc_tu_tep()
    path = os.path.join(cfg_data_dir(), "knowledge-index.json")
    moi = {"chunks": chunks}
    cu = _read_json(path, None)
    if cu != moi:
        _atomic_write_json(path, moi, mode=0o644)
        _sync_postgrest_rag(chunks)
        print(f"Tri thức RAG: đã đồng bộ {len(chunks)} đoạn")
    else:
        print(f"Tri thức RAG: không đổi ({len(chunks)} đoạn)")
    return len(chunks)


def _cap_hoac_xoay_khoa(ten: str, xoay: bool = False) -> str:
    ten_sach = ten.strip()
    if not ten_sach or not re.fullmatch(r"[A-Za-z0-9._-]+", ten_sach):
        print(f"Tên không hợp lệ: {ten}", file=sys.stderr)
        sys.exit(1)
    tid = f"may-{ten_sach}"
    email = f"{tid}@onebee.lan"
    store = _load_tokens_store()
    raw_file = os.path.join(cfg_secrets_dir(), f"may-{ten_sach}-hoi")
    if not xoay and tid in store["tokens"] and os.path.isfile(raw_file):
        with open(raw_file, encoding="utf-8") as f:
            existing = f.read().strip()
        if existing and hmac.compare_digest(sha256_hex(existing), store["tokens"][tid].get("sha256", "")):
            return existing
    khoa = f"sk-ob-{secrets.token_urlsafe(32)}"
    store["tokens"][tid] = {
        "name": tid,
        "email": email,
        "role": "user",
        "sha256": sha256_hex(khoa),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_tokens_store(store)
    return khoa


def lay_khoa(ten: str) -> str:
    ten_sach = ten.strip()
    tid = f"may-{ten_sach}"
    store = _load_tokens_store()
    entry = store.get("tokens", {}).get(tid)
    raw_file = os.path.join(cfg_secrets_dir(), f"may-{ten_sach}-hoi")
    if entry and os.path.isfile(raw_file):
        with open(raw_file, encoding="utf-8") as f:
            existing = f.read().strip()
        if existing and hmac.compare_digest(sha256_hex(existing), entry.get("sha256", "")):
            return existing
    print(f"Chưa có khóa hợp lệ cho {tid}", file=sys.stderr)
    sys.exit(1)


def xoa_tai_khoan(ten: str) -> None:
    ten_sach = ten.strip()
    tid = ten_sach if ten_sach.startswith("may-") else f"may-{ten_sach}"
    store = _load_tokens_store()
    if tid in store["tokens"]:
        del store["tokens"][tid]
        _save_tokens_store(store)
    ustore = _load_users_store()
    changed = False
    for uid in [k for k, v in ustore["users"].items() if k == tid or v.get("email") == f"{tid}@onebee.lan"]:
        del ustore["users"][uid]
        changed = True
    if changed:
        _save_users_store(ustore)


def doi_mat_khau_quan_tri(mat_khau_moi: str) -> None:
    if len(mat_khau_moi) < 8:
        print("Mật khẩu quản trị phải từ 8 ký tự trở lên.", file=sys.stderr)
        sys.exit(1)
    # Ghi file secret và xóa cache mật khẩu cũ nếu có
    pw_path = os.environ.get("AI_ADMIN_PASSWORD_FILE", os.path.join(cfg_secrets_dir(), "ai-admin-password"))
    parent = os.path.dirname(os.path.abspath(pw_path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-pw-", dir=parent)
    try:
        os.chmod(tmp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(mat_khau_moi)
        os.replace(tmp_path, pw_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def kiem_ollama() -> bool:
    try:
        with urllib.request.urlopen(f"{cfg_ollama_url()}/api/version", timeout=3) as r:
            return r.status == 200 and b"version" in r.read(256)
    except Exception:
        return False


def goi_ollama_chat(messages: list[dict], timeout: int = 240) -> str:
    payload = {
        "model": cfg_model_nen(),
        "messages": messages,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{cfg_ollama_url()}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    msg = data.get("message") or {}
    return str(msg.get("content") or data.get("response") or "").strip()


def tra_loi_rag(cau_hoi: str, lich_su: list[dict] | None = None) -> dict:
    chunks = tim_doan_lien_quan(cau_hoi, top_k=4)
    loi_dan = nap_loi_dan()
    if chunks:
        ngu_canh = "\n\n".join(
            f"[Tài liệu {i + 1}: {c['tieu_de']} ({c['nguon']})]\n{c['doan']}"
            for i, c in enumerate(chunks)
        )
        system_prompt = (
            f"{loi_dan}\n\n---\nTÀI LIỆU THAM KHẢO NỘI BỘ (hãy ưu tiên trích dẫn đúng tên văn bản và số liệu bên dưới nếu liên quan):\n"
            f"{ngu_canh}"
        )
    else:
        system_prompt = loi_dan

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for m in (lich_su or [])[-6:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": str(m["role"]), "content": str(m["content"])})
    messages.append({"role": "user", "content": cau_hoi})

    tra_loi = goi_ollama_chat(messages)
    return {
        "tra_loi": tra_loi,
        "nguon": [{"nguon": c["nguon"], "tieu_de": c["tieu_de"], "doan": c["doan"]} for c in chunks],
        "nhac_kiem_tra": NHAC_KIEM_TRA,
    }


def tao_html_giao_dien(user: dict | None, goi_y: list[dict], prompts: list[dict]) -> str:
    """Dựng giao diện Web HTML5 thuần (MIT, không CDN ngoài, an toàn không innerHTML)."""
    goi_y_json = json.dumps(goi_y, ensure_ascii=False).replace("</", "<\\/")
    prompts_json = json.dumps(prompts, ensure_ascii=False).replace("</", "<\\/")
    da_dn = "true" if user else "false"
    ten_nd = html.escape(user.get("email", "")) if user else ""
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trợ lý AI — OneBee Box</title>
<style>
:root{{--bg:#0d1b2a;--card:#15283d;--text:#f4f1ea;--muted:#b9c4d1;--accent:#e09f3e;--border:#2b4562;--ok:#4caf50}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55}}
header{{background:#091421;border-bottom:1px solid var(--border);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px}}
header h1{{margin:0;font-size:1.15rem;color:var(--accent)}}
main{{max-width:920px;margin:20px auto;padding:0 16px 40px}}
.banner{{background:#2c2210;border:1px solid var(--accent);border-radius:10px;padding:10px 14px;font-size:.92rem;margin-bottom:16px;color:#fce6bd}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}}
button.chip{{background:#1e3652;color:var(--text);border:1px solid var(--border);border-radius:8px;padding:7px 11px;cursor:pointer;font-size:.88rem;text-align:left}}
button.chip:hover{{border-color:var(--accent)}}
textarea,input{{width:100%;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:#0d1b2a;color:var(--text);font:inherit;margin-top:6px}}
button.primary{{background:var(--accent);color:#111;border:0;border-radius:8px;padding:10px 18px;font-weight:700;cursor:pointer;margin-top:10px}}
button.primary:disabled{{opacity:.55;cursor:wait}}
.msg{{padding:12px 14px;border-radius:10px;margin-top:10px;white-space:pre-wrap;border:1px solid var(--border)}}
.msg.user{{background:#1b334d}}
.msg.ai{{background:#102132}}
.sources{{margin-top:10px;padding-top:8px;border-top:1px dashed var(--border);font-size:.86rem;color:var(--muted)}}
.hidden{{display:none}}
</style>
</head>
<body>
<header>
  <h1>Trợ lý AI OneBee</h1>
  <span id="user-badge">{ten_nd or "Chưa đăng nhập"}</span>
</header>
<main>
  <div class="banner">{html.escape(NHAC_KIEM_TRA)}</div>
  <section id="login-box" class="card {"hidden" if user else ""}">
    <h2>Đăng nhập để sử dụng Trợ lý AI</h2>
    <label>Email<input id="email" type="email" value="quantri@onebee.lan"></label>
    <label>Mật khẩu<input id="password" type="password" placeholder="Nhập mật khẩu tài khoản"></label>
    <button id="btn-login" class="primary" type="button">Đăng nhập</button>
    <p id="login-err" style="color:#ff8a80"></p>
  </section>
  <section id="chat-box" class="card {"" if user else "hidden"}">
    <strong>Gợi ý nhanh:</strong>
    <div id="goi-y" class="chips"></div>
    <div style="margin-top:12px"><strong>Mẫu hành chính NĐ 30 &amp; Luật HTX:</strong></div>
    <div id="mau-nhanh" class="chips"></div>
    <div id="history"></div>
    <textarea id="cau-hoi" rows="3" placeholder="Nhập câu hỏi về Nghị định 30, Luật HTX 2023 hoặc yêu cầu soạn văn bản..."></textarea>
    <button id="btn-gui" class="primary" type="button">Hỏi Trợ lý AI</button>
  </section>
</main>
<script>
const GOI_Y = {goi_y_json};
const PROMPTS = {prompts_json};
let daDangNhap = {da_dn};
const elGoiY = document.getElementById("goi-y");
const elMau = document.getElementById("mau-nhanh");
const elInput = document.getElementById("cau-hoi");
const elHist = document.getElementById("history");
const prefix = window.location.pathname.startsWith("/ai") ? "/ai" : "";
const initQ = new URLSearchParams(window.location.search).get("q");
if (initQ) {{ elInput.value = initQ; }}

for (const g of GOI_Y) {{
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = g.title ? (g.title[0] + " " + (g.title[1] || "")).trim() : (g.content || "");
  b.addEventListener("click", () => {{ elInput.value = g.content || ""; elInput.focus(); }});
  elGoiY.appendChild(b);
}}
for (const p of PROMPTS) {{
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = "/" + p.command + " — " + p.title;
  b.addEventListener("click", () => {{ elInput.value = p.content || ""; elInput.focus(); }});
  elMau.appendChild(b);
}}

document.getElementById("btn-login").addEventListener("click", async () => {{
  const errEl = document.getElementById("login-err");
  errEl.textContent = "";
  const r = await fetch("/api/v1/auths/signin", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{
      email: document.getElementById("email").value,
      password: document.getElementById("password").value
    }})
  }});
  if (!r.ok) {{ errEl.textContent = "Sai email hoặc mật khẩu"; return; }}
  const d = await r.json();
  document.getElementById("user-badge").textContent = d.email || "Đã đăng nhập";
  document.getElementById("login-box").classList.add("hidden");
  document.getElementById("chat-box").classList.remove("hidden");
}});

function themTin(role, text, nguon) {{
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  if (Array.isArray(nguon) && nguon.length) {{
    const src = document.createElement("div");
    src.className = "sources";
    src.textContent = "Nguồn tham khảo: " + nguon.map(n => n.tieu_de).join(" | ");
    div.appendChild(src);
  }}
  elHist.appendChild(div);
}}

document.getElementById("btn-gui").addEventListener("click", async () => {{
  const q = elInput.value.trim();
  if (!q) return;
  const btn = document.getElementById("btn-gui");
  btn.disabled = true;
  themTin("user", q);
  elInput.value = "";
  try {{
    const r = await fetch(prefix + "/hoi", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{cau_hoi: q}})
    }});
    const d = await r.json();
    if (!r.ok) {{ themTin("ai", "Lỗi: " + (d.detail || r.status)); return; }}
    themTin("ai", d.tra_loi || "", d.nguon || []);
  }} catch (e) {{
    themTin("ai", "Không kết nối được Trợ lý AI.");
  }} finally {{
    btn.disabled = false;
  }}
}});
</script>
</body>
</html>
"""


class OneBeeAiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[ai-rag] {fmt % args}\n")

    def _apply_common_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        origin = self.headers.get("Origin", "").strip()
        allowed = cfg_cors_origins()
        if origin and origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Vary", "Origin")

    def _send_json(self, status: int, data: object, extra_headers: dict[str, str] | None = None) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._apply_common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, status: int, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self._apply_common_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> tuple[bool, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return False, "Content-Length không hợp lệ"
        if length < 0 or length > MAX_BODY_BYTES:
            return False, "TOO_LARGE"
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return True, json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False, "JSON không hợp lệ"

    def _current_user(self) -> dict | None:
        # 1. Phiên SSO do Caddy forward_auth xác thực (chỉ tin khi X-OneBee-SSO == 1)
        if self.headers.get("X-OneBee-SSO") == "1" and self.headers.get("Remote-User"):
            ru = self.headers.get("Remote-User", "").strip()
            groups = self.headers.get("Remote-Groups", "")
            role = "admin" if "quan_ly" in groups or "ky_thuat" in groups else "user"
            return {"id": ru, "email": f"{ru}@onebee.lan", "role": role, "via": "sso"}
        # 2. Bearer token (từ lệnh hoi / API / đăng nhập trên :3000)
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            u = xac_thuc_bearer_token(auth[7:].strip())
            if u:
                return u
        # 3. Cookie phiên Web :3000
        cookie_hdr = self.headers.get("Cookie", "")
        if cookie_hdr:
            c = SimpleCookie()
            try:
                c.load(cookie_hdr)
            except Exception:
                return None
            if "onebee_ai_session" in c:
                return giai_ma_phien_token(c["onebee_ai_session"].value)
        return None

    def _require_user(self) -> dict | None:
        u = self._current_user()
        if not u:
            self._send_json(401, {"detail": "Chưa xác thực hoặc khóa không hợp lệ"})
            return None
        return u

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._apply_common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/health", "/ai/health"):
            chunks = tai_chi_muc_tri_thuc()
            return self._send_json(200, {
                "status": True,
                "service": "onebee-ai-rag",
                "ollama": kiem_ollama(),
                "knowledge_chunks": len(chunks),
            })
        if path == "/api/config":
            return self._send_json(200, {
                "status": True,
                "name": "Trợ lý AI OneBee",
                "signup_enabled": False,
                "features": {"enable_signup": False},
            })
        if path in ("/", "/ai", "/ai/"):
            u = self._current_user()
            return self._send_html(200, tao_html_giao_dien(u, nap_goi_y(), nap_prompts()))
        if path in ("/ai/mau", "/mau"):
            if not self._require_user():
                return
            return self._send_json(200, {"prompts": nap_prompts(), "goi_y": nap_goi_y()})
        if path == "/api/v1/prompts/":
            if not self._require_user():
                return
            return self._send_json(200, nap_prompts())
        if path == "/api/models":
            if not self._require_user():
                return
            return self._send_json(200, {"data": [{"id": "onebee-tro-ly", "name": "Trợ lý OneBee"}]})
        if path == "/api/v1/auths/api_key":
            u = self._require_user()
            if not u:
                return
            tid = "nv-" + re.sub(r"[^a-z0-9._-]", "-", u["email"].split("@")[0].lower())
            store = _load_tokens_store()
            if tid in store["tokens"]:
                return self._send_json(200, {"has_key": True, "token_id": tid})
            return self._send_json(404, {"detail": "Chưa có khóa API"})
        self._send_json(404, {"detail": "Không tìm thấy đường dẫn"})

    def do_POST(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        ok, body = self._read_json_body()
        if not ok:
            if body == "TOO_LARGE":
                self.close_connection = True
                return self._send_json(413, {"detail": "Dữ liệu vượt quá 1 MB"}, extra_headers={"Connection": "close"})
            return self._send_json(400, {"detail": str(body)})
        if not isinstance(body, dict):
            return self._send_json(400, {"detail": "Body phải là JSON object"})

        if path == "/api/v1/auths/signup":
            return self._send_json(403, {"detail": "Đăng ký tự do đã tắt"})

        if path == "/api/v1/auths/signin":
            u = xac_thuc_tai_khoan(str(body.get("email", "")), str(body.get("password", "")))
            if not u:
                return self._send_json(400, {"detail": "Sai email hoặc mật khẩu"})
            tok = tao_phien_token(u)
            cookie = f"onebee_ai_session={tok}; Path=/; HttpOnly; SameSite=Lax"
            if os.environ.get("AI_SESSION_COOKIE_SECURE", "").lower() in ("1", "true", "yes"):
                cookie += "; Secure"
            return self._send_json(200, {
                "token": tok,
                "email": u["email"],
                "role": u["role"],
                "name": u["name"],
            }, extra_headers={"Set-Cookie": cookie})

        if path == "/api/v1/auths/api_key":
            u = self._require_user()
            if not u:
                return
            tid = "nv-" + re.sub(r"[^a-z0-9._-]", "-", u["email"].split("@")[0].lower())
            khoa = f"sk-ob-{secrets.token_urlsafe(32)}"
            store = _load_tokens_store()
            store["tokens"][tid] = {
                "name": tid,
                "email": u["email"],
                "role": u["role"],
                "sha256": sha256_hex(khoa),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _save_tokens_store(store)
            return self._send_json(200, {"api_key": khoa})

        if path == "/api/v1/auths/add":
            u = self._require_user()
            if not u:
                return
            if u.get("role") != "admin":
                return self._send_json(403, {"detail": "Chỉ quản trị mới được thêm tài khoản"})
            em = str(body.get("email", "")).strip().lower()
            pw = str(body.get("password", ""))
            role = "admin" if body.get("role") == "admin" else "user"
            if not em or len(pw) < 6:
                return self._send_json(400, {"detail": "Thiếu email hoặc mật khẩu quá ngắn"})
            uid = secrets.token_hex(8)
            ustore = _load_users_store()
            ustore["users"][uid] = {
                "id": uid,
                "name": str(body.get("name") or em),
                "email": em,
                "role": role,
                "password_hash": _hash_password(pw),
            }
            _save_users_store(ustore)
            return self._send_json(200, {"id": uid, "email": em, "role": role})

        if path in ("/ai/hoi", "/hoi", "/api/chat/completions"):
            if not self._require_user():
                return
            if path == "/api/chat/completions":
                msgs = body.get("messages") or []
                cau_hoi = next((str(m.get("content", "")) for m in reversed(msgs) if isinstance(m, dict) and m.get("role") == "user"), "")
                lich_su = [m for m in msgs[:-1] if isinstance(m, dict)]
            else:
                cau_hoi = str(body.get("cau_hoi", "")).strip()
                lich_su = body.get("lich_su") if isinstance(body.get("lich_su"), list) else []
            if not cau_hoi:
                return self._send_json(400, {"detail": "Thiếu nội dung câu hỏi"})
            try:
                kq = tra_loi_rag(cau_hoi, lich_su)
            except urllib.error.URLError as e:
                return self._send_json(503, {"detail": f"Chưa gọi được Ollama: {e.reason}"})
            except Exception as e:
                return self._send_json(502, {"detail": f"Lỗi xử lý Trợ lý AI: {e}"})
            if path == "/api/chat/completions":
                return self._send_json(200, {
                    "id": "chatcmpl-" + secrets.token_hex(6),
                    "model": "onebee-tro-ly",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": kq["tra_loi"]}}],
                    "nguon": kq["nguon"],
                    "nhac_kiem_tra": kq["nhac_kiem_tra"],
                })
            return self._send_json(200, kq)

        if path in ("/ai/tom-tat", "/tom-tat"):
            if not self._require_user():
                return
            hop_le, loi_pii = kiem_tra_pii_tom_tat(body)
            if not hop_le:
                return self._send_json(400, {"detail": loi_pii})
            prompt_so_lieu = (
                "Hãy tóm tắt ngắn gọn bằng tiếng Việt tình hình hoạt động dựa trên các số liệu tổng hợp sau "
                "(chỉ nêu nhận xét nghiệp vụ và điểm cần lưu ý, không suy đoán danh tính cá nhân):\n"
                + json.dumps(body, ensure_ascii=False, indent=2)
            )
            try:
                tom_tat = goi_ollama_chat([
                    {"role": "system", "content": nap_loi_dan()},
                    {"role": "user", "content": prompt_so_lieu},
                ])
            except urllib.error.URLError as e:
                return self._send_json(503, {"detail": f"Chưa gọi được Ollama: {e.reason}"})
            except Exception as e:
                return self._send_json(502, {"detail": f"Lỗi tóm tắt số liệu: {e}"})
            return self._send_json(200, {
                "tom_tat": tom_tat,
                "nhac_kiem_tra": NHAC_KIEM_TRA,
            })

        self._send_json(404, {"detail": "Không tìm thấy đường dẫn"})

    def do_DELETE(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/api/v1/users/"):
            u = self._require_user()
            if not u:
                return
            if u.get("role") != "admin":
                return self._send_json(403, {"detail": "Không đủ quyền"})
            uid = path[len("/api/v1/users/"):].strip("/")
            ustore = _load_users_store()
            if uid in ustore["users"]:
                del ustore["users"][uid]
                _save_users_store(ustore)
            return self._send_json(200, {"deleted": True})
        self._send_json(404, {"detail": "Không tìm thấy đường dẫn"})


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd in ("chay-dich-vu", "serve"):
        dia_chi = os.environ.get("ONEBEE_AI_RAG_ADDR", "0.0.0.0")
        cong = int(os.environ.get("ONEBEE_AI_RAG_PORT", "8092"))
        if not os.path.isfile(os.path.join(cfg_data_dir(), "knowledge-index.json")):
            dong_bo_tri_thuc()
        sv = ThreadingHTTPServer((dia_chi, cong), OneBeeAiHandler)
        print(f"onebee-ai-rag đang lắng nghe tại {dia_chi}:{cong}", file=sys.stderr)
        sv.serve_forever()
        return 0
    if cmd == "dong-bo-tro-ly":
        dong_bo_tro_ly()
        return 0
    if cmd == "dong-bo-prompts":
        dong_bo_prompts()
        return 0
    if cmd == "dong-bo-tri-thuc":
        dong_bo_tri_thuc()
        return 0
    if cmd == "cap-khoa" and len(sys.argv) >= 3:
        print(_cap_hoac_xoay_khoa(sys.argv[2], xoay=False))
        return 0
    if cmd == "lay-khoa" and len(sys.argv) >= 3:
        print(lay_khoa(sys.argv[2]))
        return 0
    if cmd == "xoay-khoa" and len(sys.argv) >= 3:
        print(_cap_hoac_xoay_khoa(sys.argv[2], xoay=True))
        return 0
    if cmd == "xoa-tai-khoan" and len(sys.argv) >= 3:
        xoa_tai_khoan(sys.argv[2])
        return 0
    if cmd == "doi-mat-khau-quan-tri":
        doi_mat_khau_quan_tri(os.environ.get("ONEBEE_MAT_KHAU_MOI", ""))
        return 0
    print(f"Lệnh không hợp lệ: {' '.join(sys.argv[1:])}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
