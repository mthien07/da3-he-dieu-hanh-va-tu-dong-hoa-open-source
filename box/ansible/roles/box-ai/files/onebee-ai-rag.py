#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""onebee-ai-rag.py — Dịch vụ Trợ lý AI & RAG thuần nguồn mở (MIT) trên lõi DX-OS,
thay thế hoàn toàn giao diện AI bên thứ ba (Giai đoạn 8, ADR 0006).

Chế độ dịch vụ HTTP (chạy trong container onebee-ai-rag hoặc trực tiếp):
  onebee-ai-rag.py serve
Các tuyến HTTP:
  GET  /health                  Kiểm tra sức khỏe dịch vụ
  GET  /ai/mau                  Danh sách 4 mẫu soạn thảo hành chính (NĐ 30/2020/NĐ-CP) + gợi ý
  POST /ai/hoi                  Hỏi đáp AI kèm truy xuất tri thức RAG (trả về tra_loi + nguon_trich_dan)
  POST /ai/tom-tat              Tóm tắt văn bản / báo cáo tuần (ẩn danh, không lộ PII)
  GET  /api/models              Tương thích lệnh `hoi` trên máy trạm
  POST /api/chat/completions    Tương thích lệnh `hoi` trên máy trạm
  POST /api/v1/auths/signin     Tương thích `hoi --dang-nhap`
  GET|POST /api/v1/auths/api_key Tương thích `hoi --dang-nhap`

Chế độ quản trị dòng lệnh (được `onebee-box` gọi):
  onebee-ai-rag.py dong-bo-tro-ly
  onebee-ai-rag.py dong-bo-prompts
  onebee-ai-rag.py dong-bo-tri-thuc
  onebee-ai-rag.py cap-khoa <ten-may>
  onebee-ai-rag.py lay-khoa <ten-may>
  onebee-ai-rag.py xoay-khoa <ten-may>
  onebee-ai-rag.py xoa-tai-khoan <ten-may>
  onebee-ai-rag.py doi-mat-khau-quan-tri
"""
import glob
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def doc_tep(duong_dan: str, mac_dinh: str = "") -> str:
    try:
        with open(duong_dan, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return mac_dinh


def nap_danh_sach_mau(prompts_dir: str) -> list[dict]:
    ds = []
    if not os.path.isdir(prompts_dir):
        return ds
    for tep in sorted(os.listdir(prompts_dir)):
        if tep.endswith(".json"):
            try:
                with open(os.path.join(prompts_dir, tep), encoding="utf-8") as f:
                    d = json.load(f)
                ds.append({
                    "command": d.get("command", ""),
                    "ma": d.get("command", "").lstrip("/"),
                    "title": d.get("title", ""),
                    "content": d.get("content", ""),
                })
            except (OSError, ValueError):
                continue
    return ds


def nap_kho_tri_thuc(cac_thu_muc: list[str]) -> list[dict]:
    """Đọc và chia đoạn các tài liệu Markdown trong kho tri thức pháp lý (NĐ 30, Luật HTX...)."""
    doan_list = []
    for tm in cac_thu_muc:
        if not tm or not os.path.isdir(tm):
            continue
        for duong_dan in sorted(glob.glob(os.path.join(tm, "*.md"))):
            ten_tep = os.path.basename(duong_dan)
            nd = doc_tep(duong_dan)
            if not nd.strip():
                continue
            cac_phan = re.split(r"\n(?=##?\s+)", nd.strip())
            for idx, phan in enumerate(cac_phan):
                phan = phan.strip()
                if not phan:
                    continue
                dong_dau = phan.splitlines()[0].lstrip("# ").strip()
                doan_list.append({
                    "ma_tai_lieu": ten_tep,
                    "tieu_de": dong_dau or ten_tep,
                    "doan_so": idx,
                    "noi_dung": phan,
                })
    return doan_list


def truy_xuat_rag(cau_hoi: str, kho_doan: list[dict], top_k: int = 3) -> list[dict]:
    """Chấm điểm từ khóa tiếng Việt để lấy tối đa top_k đoạn tri thức sát câu hỏi nhất."""
    tu_khoa = {w for w in re.findall(r"\w+", cau_hoi.lower()) if len(w) >= 2}
    if not tu_khoa or not kho_doan:
        return []
    ket_qua = []
    for d in kho_doan:
        van_ban = (d["tieu_de"] + " " + d["noi_dung"]).lower()
        diem = sum(3 if w in d["tieu_de"].lower() else 1 for w in tu_khoa if w in van_ban)
        if diem > 0:
            ket_qua.append((diem, d))
    ket_qua.sort(key=lambda x: (-x[0], x[1]["ma_tai_lieu"], x[1]["doan_so"]))
    return [x[1] for x in ket_qua[:top_k]]


def goi_ollama(ollama_url: str, model: str, loi_dan: str, cau_hoi: str, ngu_canh_rag: list[dict]) -> str:
    he_thong = loi_dan.strip()
    if ngu_canh_rag:
        trich = "\n\n---\n".join(f"[{d['ma_tai_lieu']} — {d['tieu_de']}]\n{d['noi_dung']}" for d in ngu_canh_rag)
        he_thong += "\n\nTài liệu tham chiếu nội bộ (ưu tiên trích dẫn khi trả lời):\n" + trich
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": he_thong},
            {"role": "user", "content": cau_hoi},
        ],
    }
    req = urllib.request.Request(
        ollama_url.rstrip("/") + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        dl = json.loads(resp.read())
    return (dl.get("message") or {}).get("content", "").strip()


# ---- Quản lý trạng thái khóa API & đồng bộ ----

class QuanLyAiRag:
    def __init__(self, data_dir: str, secrets_dir: str, lib_dir: str):
        self.data_dir = data_dir
        self.secrets_dir = secrets_dir
        self.lib_dir = lib_dir
        self.state_file = os.path.join(data_dir, "ai-rag-state.json")
        os.makedirs(data_dir, mode=0o700, exist_ok=True)

    def doc_state(self) -> dict:
        if not os.path.isfile(self.state_file):
            return {"khoa_may": {}, "khoa_nguoi_dung": {}, "prompts_hash": "", "rag_hash": "", "tro_ly_hash": ""}
        try:
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"khoa_may": {}, "khoa_nguoi_dung": {}, "prompts_hash": "", "rag_hash": "", "tro_ly_hash": ""}

    def ghi_state(self, st: dict) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        os.chmod(self.state_file, 0o600)

    def xac_thuc_khoa(self, bearer: str) -> str | None:
        if not bearer:
            return None
        st = self.doc_state()
        for ten, k in (st.get("khoa_may") or {}).items():
            if k == bearer:
                return f"may-{ten}"
        for email, k in (st.get("khoa_nguoi_dung") or {}).items():
            if k == bearer:
                return email
        # Kiểm tra cả khóa máy trong thư mục secrets (nếu có)
        if os.path.isdir(self.secrets_dir):
            for fn in os.listdir(self.secrets_dir):
                if fn.startswith("may-") and fn.endswith("-hoi"):
                    if doc_tep(os.path.join(self.secrets_dir, fn)).strip() == bearer:
                        return fn[:-4]
        return None

    def cap_khoa(self, ten: str, xoay: bool = False) -> str:
        st = self.doc_state()
        km = st.setdefault("khoa_may", {})
        if not xoay and ten in km and km[ten]:
            return km[ten]
        khoa = f"sk-onebee-{ten}-{secrets.token_hex(16)}"
        km[ten] = khoa
        self.ghi_state(st)
        if os.path.isdir(self.secrets_dir):
            with open(os.path.join(self.secrets_dir, f"may-{ten}-ai"), "w", encoding="utf-8") as f:
                f.write("managed-by-ai-rag\n")
        return khoa

    def xoa_tai_khoan(self, ten: str) -> None:
        st = self.doc_state()
        (st.get("khoa_may") or {}).pop(ten, None)
        self.ghi_state(st)

    def dong_bo_prompts(self) -> tuple[int, bool]:
        prompts = nap_danh_sach_mau(os.path.join(self.lib_dir, "prompts"))
        h = hashlib.sha256(json.dumps(prompts, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        st = self.doc_state()
        doi = st.get("prompts_hash") != h
        st["prompts_hash"] = h
        st["prompts"] = prompts
        self.ghi_state(st)
        return len(prompts), doi

    def dong_bo_tri_thuc(self) -> tuple[int, bool]:
        kho = nap_kho_tri_thuc([
            os.path.join(self.lib_dir, "knowledge"),
            "/usr/local/share/onebee-box/knowledge",
        ])
        h = hashlib.sha256(json.dumps(kho, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        st = self.doc_state()
        doi = st.get("rag_hash") != h
        st["rag_hash"] = h
        st["rag_chunks"] = len(kho)
        self.ghi_state(st)
        return len(kho), doi

    def dong_bo_tro_ly(self) -> bool:
        loi_dan = doc_tep(os.path.join(self.lib_dir, "tro-ly-onebee-loi-dan.md"))
        model = os.environ.get("ONEBEE_AI_MODEL", "gemma4:e2b-it-qat")
        h = hashlib.sha256(f"{model}:{loi_dan}".encode("utf-8")).hexdigest()
        st = self.doc_state()
        doi_tl = st.get("tro_ly_hash") != h
        st["tro_ly_hash"] = h
        st["model"] = model
        self.ghi_state(st)
        _, doi_p = self.dong_bo_prompts()
        _, doi_k = self.dong_bo_tri_thuc()
        return doi_tl or doi_p or doi_k


class AiRagHandler(BaseHTTPRequestHandler):
    ql: QuanLyAiRag = None  # type: ignore[assignment]
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
    model = os.environ.get("ONEBEE_AI_MODEL", "gemma4:e2b-it-qat")

    def log_message(self, *args):
        pass

    def _tra_json(self, ma: int, dl: dict | list):
        raw = json.dumps(dl, ensure_ascii=False).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _nguoi_dung(self) -> str | None:
        u = (self.headers.get("Remote-User") or "").strip()
        if u:
            return u
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            return self.ql.xac_thuc_khoa(auth[7:].strip())
        return None

    def do_GET(self):
        if self.path in ("/health", "/ai/health"):
            return self._tra_json(200, {"status": "ok", "model": self.model})
        if self.path in ("/ai/mau", "/mau", "/api/v1/prompts/"):
            prompts = nap_danh_sach_mau(os.path.join(self.ql.lib_dir, "prompts"))
            goi_y_raw = doc_tep(os.path.join(self.ql.lib_dir, "goi-y.json"), "[]")
            try:
                goi_y = json.loads(goi_y_raw)
            except ValueError:
                goi_y = []
            if self.path == "/api/v1/prompts/":
                return self._tra_json(200, prompts)
            return self._tra_json(200, {"mau": prompts, "goi_y": goi_y, "model": self.model})
        if self.path == "/api/models":
            if not self._nguoi_dung():
                return self._tra_json(401, {"loi": "Chưa xác thực"})
            return self._tra_json(200, {"data": [{"id": "onebee-tro-ly", "name": "Trợ lý OneBee"}]})
        if self.path == "/api/v1/auths/api_key":
            u = self._nguoi_dung()
            if not u:
                return self._tra_json(401, {"detail": "Chưa đăng nhập"})
            st = self.ql.doc_state()
            k = (st.get("khoa_nguoi_dung") or {}).get(u)
            return self._tra_json(200, {"api_key": k}) if k else self._tra_json(404, {"detail": "none"})
        self._tra_json(404, {"loi": "Không tìm thấy đường dẫn"})

    def do_POST(self):
        do_dai = int(self.headers.get("Content-Length", "0") or "0")
        try:
            body = json.loads(self.rfile.read(do_dai) or b"{}") if do_dai > 0 else {}
        except ValueError:
            return self._tra_json(400, {"loi": "JSON không hợp lệ"})

        if self.path == "/api/v1/auths/signin":
            email = (body.get("email") or "").strip()
            pw = body.get("password") or ""
            admin_pw = doc_tep(os.path.join(self.ql.secrets_dir, "sso-quantri-password")).strip() or doc_tep(
                os.path.join(self.ql.secrets_dir, "ai-admin-password")
            ).strip()
            if email and pw and (pw == admin_pw):
                st = self.ql.doc_state()
                k = st.setdefault("khoa_nguoi_dung", {}).setdefault(email, f"sk-user-{secrets.token_hex(16)}")
                self.ql.ghi_state(st)
                return self._tra_json(200, {"token": k})
            return self._tra_json(400, {"detail": "Sai thông tin đăng nhập"})

        if self.path == "/api/v1/auths/api_key":
            u = self._nguoi_dung()
            if not u:
                return self._tra_json(401, {"detail": "Chưa đăng nhập"})
            st = self.ql.doc_state()
            k = f"sk-user-{secrets.token_hex(16)}"
            st.setdefault("khoa_nguoi_dung", {})[u] = k
            self.ql.ghi_state(st)
            return self._tra_json(200, {"api_key": k})

        nguoi_dung = self._nguoi_dung()
        if not nguoi_dung:
            return self._tra_json(401, {"loi": "Chưa đăng nhập SSO hoặc khóa không hợp lệ"})

        if self.path in ("/ai/tom-tat", "/tom-tat"):
            van_ban = (body.get("noi_dung") or body.get("van_ban") or "").strip()
            if not van_ban:
                return self._tra_json(400, {"loi": "Thiếu nội dung cần tóm tắt"})
            loi_dan = doc_tep(os.path.join(self.ql.lib_dir, "tro-ly-onebee-loi-dan.md"))
            cau_hoi = (
                "Hãy tóm tắt ngắn gọn, rõ các ý chính và việc cần làm từ nội dung sau "
                "(tuyệt đối không suy diễn thêm số liệu ngoài văn bản):\n\n" + van_ban
            )
            try:
                tra_loi = goi_ollama(self.ollama_url, self.model, loi_dan, cau_hoi, [])
            except (urllib.error.URLError, TimeoutError, OSError):
                return self._tra_json(503, {"loi": "Bộ chạy mô hình AI (Ollama) chưa sẵn sàng"})
            return self._tra_json(200, {"tom_tat": tra_loi, "model": self.model})

        if self.path in ("/ai/hoi", "/hoi", "/api/chat/completions"):
            cau_hoi = (body.get("cau_hoi") or body.get("question") or "").strip()
            if not cau_hoi and isinstance(body.get("messages"), list) and body["messages"]:
                cau_hoi = (body["messages"][-1].get("content") or "").strip()
            if not cau_hoi:
                return self._tra_json(400, {"loi": "Thiếu câu hỏi"})
            kho = nap_kho_tri_thuc([
                os.path.join(self.ql.lib_dir, "knowledge"),
                "/usr/local/share/onebee-box/knowledge",
            ])
            trich_dan = truy_xuat_rag(cau_hoi, kho, top_k=3)
            loi_dan = doc_tep(os.path.join(self.ql.lib_dir, "tro-ly-onebee-loi-dan.md"))
            bat_dau = time.time()
            try:
                tra_loi = goi_ollama(self.ollama_url, self.model, loi_dan, cau_hoi, trich_dan)
            except (urllib.error.URLError, TimeoutError, OSError):
                return self._tra_json(503, {"loi": "Bộ chạy mô hình AI (Ollama) chưa sẵn sàng"})
            ms = int((time.time() - bat_dau) * 1000)
            return self._tra_json(200, {
                "tra_loi": tra_loi,
                "nguon_trich_dan": [{"tai_lieu": d["ma_tai_lieu"], "muc": d["tieu_de"]} for d in trich_dan],
                "thoi_gian_ms": ms,
                "choices": [{"message": {"role": "assistant", "content": tra_loi}}],
            })

        self._tra_json(404, {"loi": "Không tìm thấy đường dẫn"})


def main(argv):
    data_dir = os.environ.get("ONEBEE_AI_RAG_DATA", "/srv/onebee/ai-rag")
    secrets_dir = os.environ.get("ONEBEE_SECRETS", "/etc/onebee-box/secrets")
    lib_dir = os.environ.get("ONEBEE_LIB_DIR", HERE)
    ql = QuanLyAiRag(data_dir, secrets_dir, lib_dir)

    if not argv or argv[0] == "serve":
        cong = int(os.environ.get("PORT", "8080"))
        AiRagHandler.ql = ql
        sv = ThreadingHTTPServer(("0.0.0.0", cong), AiRagHandler)
        sv.serve_forever()
        return 0

    lenh = argv[0]
    if lenh == "dong-bo-tro-ly":
        doi = ql.dong_bo_tro_ly()
        print("Trợ lý OneBee: đã cập nhật" if doi else "Trợ lý OneBee: không đổi")
        return 0
    if lenh == "dong-bo-prompts":
        so_luong, doi = ql.dong_bo_prompts()
        print(f"Kho mẫu prompt: {'đã cập nhật' if doi else 'không đổi'} ({so_luong} mẫu)")
        return 0
    if lenh == "dong-bo-tri-thuc":
        so_doan, doi = ql.dong_bo_tri_thuc()
        print(f"Bộ tri thức RAG: {'đã cập nhật' if doi else 'không đổi'} ({so_doan} đoạn)")
        return 0
    if lenh in ("cap-khoa", "lay-khoa"):
        if len(argv) < 2:
            sys.exit(f"Cách dùng: onebee-ai-rag.py {lenh} <tên-máy>")
        print(ql.cap_khoa(argv[1], xoay=False))
        return 0
    if lenh == "xoay-khoa":
        if len(argv) < 2:
            sys.exit("Cách dùng: onebee-ai-rag.py xoay-khoa <tên-máy>")
        print(ql.cap_khoa(argv[1], xoay=True))
        return 0
    if lenh == "xoa-tai-khoan":
        if len(argv) < 2:
            sys.exit("Cách dùng: onebee-ai-rag.py xoa-tai-khoan <tên-máy>")
        ql.xoa_tai_khoan(argv[1])
        return 0
    if lenh == "doi-mat-khau-quan-tri":
        return 0
    sys.exit(f"Lệnh không rõ: {lenh}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
