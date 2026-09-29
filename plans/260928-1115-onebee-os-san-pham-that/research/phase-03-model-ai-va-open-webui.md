# Research Phase 3 — model AI trên Ollama + cấu hình Open WebUI (29/9/2026)

## Model ứng viên (trang ollama.com/library, xem 29/9)
| Model | Tag | Dung lượng tải | Ghi chú trang Ollama |
|---|---|---|---|
| Qwen 3.5 | `qwen3.5:4b` / `:9b` / `:27b` | 3.4 / 6.6 / 17 GB | Đa phương thức, ngữ cảnh 256K |
| Gemma 4 | `gemma4:12b` / `:26b` | 7.6 / 19 GB | Ngữ cảnh 256K, có chế độ "thinking" |
| Qwen 3, Gemma 3, Llama 3.1 | nhiều cỡ | — | Đời trước, dùng làm mốc so sánh |
| bge-m3 | `bge-m3` | — | Model nhúng đa ngôn ngữ (cho kho tri thức nếu cần) |

- Trang Ollama **không ghi** mức hỗ trợ tiếng Việt của từng model → chỉ số đo 3C mới quyết định.
- Giấy phép từng model (Qwen: Apache-2.0 hay giấy phép riêng tùy cỡ; Gemma: điều khoản Gemma) — **cần kiểm trước khi chọn**,
  ghi vào LICENSES.md.

## Open WebUI v0.11.4 — biến môi trường (đọc trực tiếp mã nguồn trong image `v0.11.4-slim`)
- `ENABLE_API_KEYS` — mặc định `False` (config.py).
- `ENABLE_API_KEY_ENDPOINT_RESTRICTIONS` + `API_KEYS_ALLOWED_ENDPOINTS` — giới hạn khóa API chỉ gọi endpoint cho phép.
- `WEBUI_ADMIN_EMAIL` + `WEBUI_ADMIN_PASSWORD` (env.py) — lúc khởi động tạo tài khoản quản trị rồi **tự tắt đăng ký**
  (main.py: `create_admin_user` → `ui.enable_signup = False`).
- `OFFLINE_MODE` — có thật (env.py), tắt tự tải/cập nhật model nhúng, whisper… (Box v0.1 đang bật).
- `ENABLE_OPENAI_API` — mặc định `True`; Box v0.1 đặt `false`.

## Nguồn
- https://ollama.com/library · https://ollama.com/library/qwen3.5/tags · https://ollama.com/library/gemma4
- Mã nguồn Open WebUI trong image `ghcr.io/open-webui/open-webui:v0.11.4-slim`: `backend/open_webui/{config,env,main}.py`
