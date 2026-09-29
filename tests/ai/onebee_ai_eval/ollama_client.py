"""Gọi Ollama bằng thư viện chuẩn: hỏi đáp (đo thời gian chờ chữ đầu, tốc độ) và đọc dung lượng model đang nạp."""
import json
import time
import urllib.request


class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434", timeout=600):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path, payload, stream=False):
        req = urllib.request.Request(self.base_url + path, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=self.timeout)

    def pull(self, model):
        """Tải model nếu chưa có. Đọc tiến độ dạng luồng để model lớn (vài GB) không bị hết giờ chờ."""
        status = None
        with self._post("/api/pull", {"model": model, "stream": True}) as r:
            for line in r:
                if line.strip():
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise RuntimeError(f"Không tải được model {model}: {chunk['error']}")
                    status = chunk.get("status", status)
        if status != "success":
            raise RuntimeError(f"Không tải được model {model}: {status}")

    def chat(self, model, system_prompt, question, options=None):
        """Hỏi 1 câu. Trả về dict: tra_loi, cho_chu_dau_giay, token_moi_giay, tong_giay."""
        messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + \
                   [{"role": "user", "content": question}]
        payload = {"model": model, "messages": messages, "stream": True, "options": options or {}}
        start = time.monotonic()
        first = None
        parts, final = [], {}
        with self._post("/api/chat", payload, stream=True) as r:
            for line in r:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise RuntimeError(chunk["error"])
                piece = chunk.get("message", {}).get("content", "")
                if piece and first is None:
                    first = time.monotonic() - start
                parts.append(piece)
                if chunk.get("done"):
                    final = chunk
        eval_count, eval_ns = final.get("eval_count", 0), final.get("eval_duration", 0)
        return {
            "tra_loi": "".join(parts).strip(),
            "cho_chu_dau_giay": round(first if first is not None else time.monotonic() - start, 2),
            "token_moi_giay": round(eval_count / (eval_ns / 1e9), 1) if eval_ns else 0.0,
            "tong_giay": round(time.monotonic() - start, 2),
        }

    def loaded_size_gb(self, model):
        """Dung lượng bộ nhớ model đang chiếm (GB), theo /api/ps."""
        with urllib.request.urlopen(self.base_url + "/api/ps", timeout=30) as r:
            for m in json.load(r).get("models", []):
                if m.get("name") == model or m.get("model") == model:
                    return round(m.get("size", 0) / 1e9, 2)
        return None
