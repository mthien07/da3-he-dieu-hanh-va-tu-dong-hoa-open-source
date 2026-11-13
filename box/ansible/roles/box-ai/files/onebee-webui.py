#!/usr/bin/env python3
"""Quản lý Open WebUI của OneBee Box qua API (chỉ thư viện chuẩn). Được lệnh onebee-box gọi.

  onebee-webui.py dong-bo-tro-ly   Tạo/cập nhật model "Trợ lý OneBee" (model nền + lời dặn tiếng Việt), mở cho mọi người
  onebee-webui.py dong-bo-prompts  Đồng bộ kho mẫu prompt hành chính chuẩn (NĐ 30, Luật HTX)
  onebee-webui.py dong-bo-tri-thuc Đồng bộ bộ tri thức RAG (Thư viện Pháp lý HTX)
  onebee-webui.py cap-khoa <ten>   Tạo tài khoản máy trạm may-<ten> (nếu chưa có) và in khóa API để máy trạm dùng lệnh hoi
  onebee-webui.py lay-khoa <ten>   CHỈ ĐỌC: in khóa API đã có của tài khoản may-<ten> (không tạo tài khoản/khóa; chưa có thì thoát lỗi, mã 1)
  onebee-webui.py xoa-tai-khoan <ten>   Xóa tài khoản may-<ten> (thu hồi khóa hoi của máy; idempotent)

Đọc cấu hình từ biến môi trường: WEBUI_URL, WEBUI_ADMIN_EMAIL, WEBUI_ADMIN_PASSWORD, ONEBEE_AI_MODEL,
ONEBEE_LOI_DAN (đường dẫn file lời dặn), ONEBEE_SECRETS (thư mục bí mật),
ONEBEE_WEBUI_PUBLIC_URL (địa chỉ công khai của Open WebUI, rỗng = chưa bật HTTPS).
Mã thoát: 0 xong · 1 Open WebUI chưa sẵn sàng/lỗi khác (thử lại được) · 3 sai mật khẩu quản trị (không thử lại).
"""
import json
import os
import secrets
import string
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ.get("WEBUI_URL", "http://127.0.0.1:3000").rstrip("/")
PRESET_ID, PRESET_NAME = "onebee-tro-ly", "Trợ lý OneBee"
PUBLIC_READ = [{"principal_type": "user", "principal_id": "*", "permission": "read"}]
PARAMS = {"temperature": 0.3}  # ổn định câu trả lời; công cụ chấm tests/ai dùng cùng giá trị
# Cài đặt bắt buộc — đặt lại qua API mỗi lần chạy (Open WebUI ưu tiên giá trị đã lưu trong CSDL hơn biến môi trường)
ADMIN_CONFIG = {"ENABLE_SIGNUP": False, "ENABLE_API_KEYS": True, "ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS": True,
                "API_KEYS_ALLOWED_ENDPOINTS": "/api/chat/completions,/api/models",
                "ENABLE_COMMUNITY_SHARING": False,  # Box chạy offline, không chia sẻ lên cộng đồng (GHSA-vpq8-f445-hcq7)
                "JWT_EXPIRES_IN": "30d"}            # phiên đăng nhập 1 tháng (mặc định của Open WebUI: 4w)
GOI_Y = os.environ.get("ONEBEE_GOI_Y", os.path.join(os.path.dirname(os.path.abspath(__file__)), "goi-y.json"))
GIAO_DIEN = os.environ.get("ONEBEE_GIAO_DIEN",
                           os.path.join(os.path.dirname(os.path.abspath(__file__)), "giao-dien-tieng-viet.json"))
# Quyền mặc định của người dùng thường: (nhóm, quyền) → giá trị. Nhân viên tạo được khóa API (cho lệnh hoi) nhưng không
# chia sẻ đoạn chat cho nhau.
DEFAULT_PERMISSIONS = {("features", "api_keys"): True, ("chat", "share"): False}


def call(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(URL + path, method=method, headers=headers,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def signin(email, password):
    """Trả về token, hoặc None nếu sai tài khoản/mật khẩu. Lỗi khác (chưa chạy xong...) → thoát mã 1."""
    status, data = call("POST", "/api/v1/auths/signin", body={"email": email, "password": password})
    if status in (400, 401, 403):
        return None
    if status != 200:
        sys.exit(f"LỖI: Open WebUI chưa sẵn sàng ({status}): {data}")
    return data["token"]


def admin_token():
    token = signin(os.environ["WEBUI_ADMIN_EMAIL"], os.environ["WEBUI_ADMIN_PASSWORD"])
    if not token:
        print("LỖI: sai mật khẩu quản trị Open WebUI. Nếu đã đổi mật khẩu trên web, ghi mật khẩu mới vào "
              "/etc/onebee-box/secrets/webui-admin-password rồi chạy lại.", file=sys.stderr)
        sys.exit(3)
    return token


def ban_dich_giao_dien(dang_luu):
    """I18N muốn có: bản dịch đang lưu (giữ phần quản trị tự thêm) gộp bản dịch bổ sung của OneBee (ghi đè khóa trùng)."""
    try:
        with open(GIAO_DIEN, encoding="utf-8") as f:
            cua_onebee = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"LỖI: không đọc được bản dịch giao diện {GIAO_DIEN}: {e}")
    gop = {ngon_ngu: dict(muc) for ngon_ngu, muc in (dang_luu or {}).items()}
    for ngon_ngu, muc in cua_onebee.items():
        gop.setdefault(ngon_ngu, {}).update(muc)
    return gop


def enforce_settings(token):
    """Tắt đăng ký tự do, bật + giới hạn khóa API, tắt chia sẻ cộng đồng, đặt thời hạn phiên, bổ sung bản dịch tiếng Việt
    cho giao diện, chỉnh quyền mặc định của người dùng."""
    changed = False
    status, cfg = call("GET", "/api/v1/auths/admin/config", token)
    if status != 200:
        sys.exit(f"LỖI: không đọc được cài đặt quản trị ({status}): {cfg}")
    # WEBUI_URL (địa chỉ công khai: https://<IP>:3000 khi Box bật HTTPS, rỗng khi còn HTTP) lưu trong CSDL → đặt qua API như các cài đặt khác
    muon = {**ADMIN_CONFIG, "WEBUI_URL": os.environ.get("ONEBEE_WEBUI_PUBLIC_URL", "")}
    muon["DEFAULT_INTERFACE_SETTINGS"] = {**(cfg.get("DEFAULT_INTERFACE_SETTINGS") or {}), "insertSuggestionPrompt": True}
    # Bản vi-VN của Open WebUI còn thiếu chuỗi → chữ tiếng Anh. I18N ghi đè bản dịch gốc, khóa là đúng chuỗi giao diện gọi
    # $i18n.t(...): chữ tiếng Anh gốc, riêng trang Cài đặt là khóa "settings.…". /api/config trả I18N cả trước khi đăng nhập.
    muon["I18N"] = ban_dich_giao_dien(cfg.get("I18N"))
    if any(cfg.get(k) != v for k, v in muon.items()):
        # bỏ trường rỗng (vd I18N=null) — gửi lại null bị Open WebUI từ chối
        payload = {k: v for k, v in {**cfg, **muon}.items() if v is not None}
        status, data = call("POST", "/api/v1/auths/admin/config", token, payload)
        if status != 200:
            sys.exit(f"LỖI: không lưu được cài đặt quản trị ({status}): {data}")
        changed = True
    status, perms = call("GET", "/api/v1/users/default/permissions", token)
    if status != 200:
        sys.exit(f"LỖI: không đọc được quyền mặc định của người dùng ({status}): {perms}")
    if any(perms.get(g, {}).get(k) != v for (g, k), v in DEFAULT_PERMISSIONS.items()):
        for (g, k), v in DEFAULT_PERMISSIONS.items():
            perms.setdefault(g, {})[k] = v
        status, data = call("POST", "/api/v1/users/default/permissions", token, perms)
        if status != 200:
            sys.exit(f"LỖI: không lưu được quyền mặc định của người dùng ({status}): {data}")
        changed = True
    return changed


def luu_model(token, form):
    """Tạo/cập nhật 1 bản ghi model (mở quyền đọc cho mọi người). Trả về "đã tạo" / "đã cập nhật" / None (không đổi)."""
    status, current = call("GET", f"/api/v1/models/model?id={urllib.parse.quote(form['id'])}", token)
    if status == 200 and current:
        cur_params, cur_meta = current.get("params") or {}, current.get("meta") or {}
        if (current.get("base_model_id") == form["base_model_id"] and current.get("name") == form["name"]
                and all(cur_params.get(k) == v for k, v in form["params"].items())
                and all(cur_meta.get(k) == v for k, v in form["meta"].items())
                and any(g.get("principal_id") == "*" for g in current.get("access_grants") or [])):
            return None
        status, data = call("POST", f"/api/v1/models/model/update?id={urllib.parse.quote(form['id'])}", token, form)
        verb = "đã cập nhật"
    else:
        status, data = call("POST", "/api/v1/models/create", token, form)
        verb = "đã tạo"
    if status != 200:
        sys.exit(f"LỖI: không lưu được model {form['id']} ({status}): {data}")
    return verb


PROMPTS_DIR = os.environ.get("ONEBEE_PROMPTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts"))
KNOWLEDGE_DIR = os.environ.get("ONEBEE_KNOWLEDGE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge"))
BANG_NHAC = {
    "id": "onebee-ai-co-the-sai",
    "type": "info",
    "title": "",
    "content": "Trợ lý AI có thể sai. Hãy đọc lại số liệu, tên, ngày tháng trước khi dùng. Không nhập mật khẩu hay số tài khoản vào đây.",
    "dismissible": True,
    "timestamp": 1762905600,
}


def dong_bo_prompts(token=None):
    """Nạp sẵn kho mẫu prompt hành chính chuẩn (Tờ trình NĐ 30, Biên bản, Hợp đồng HTX, Báo cáo tài chính)."""
    if token is None:
        token = admin_token()
    if not os.path.isdir(PROMPTS_DIR):
        print(f"Kho mẫu soạn văn bản: thư mục {PROMPTS_DIR} không tồn tại")
        return 0
    status, current_prompts = call("GET", "/api/v1/prompts/", token)
    if status != 200 or not isinstance(current_prompts, list):
        sys.exit(f"LỖI: không đọc được danh sách mẫu soạn văn bản ({status}): {current_prompts}")
    existing_cmds = {}
    for p in current_prompts:
        if isinstance(p, dict) and "command" in p:
            existing_cmds[p["command"].lstrip("/")] = p
    count, tao, cap_nhat = 0, 0, 0
    for fname in sorted(os.listdir(PROMPTS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(PROMPTS_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"CẢNH BÁO: không đọc được mẫu prompt {fname}: {e}", file=sys.stderr)
            continue
        cmd = data.get("command")
        title = data.get("title")
        content = data.get("content")
        if not cmd or not title or not content:
            continue
        lenh = cmd.lstrip("/")
        ten = title
        body = {"command": lenh, "name": ten, "content": content, "tags": [], "access_grants": PUBLIC_READ}
        cur = existing_cmds.get(lenh)
        if cur is None:
            st, d = call("POST", "/api/v1/prompts/create", token, body)
            if st != 200:
                sys.exit(f"LỖI: không lưu được mẫu soạn văn bản {lenh} ({st}): {d}")
            tao += 1
        elif (cur.get("name") != ten or cur.get("content") != content
              or not any(g.get("principal_id") == "*" for g in (cur.get("access_grants") or []))):
            st, d = call("POST", f"/api/v1/prompts/id/{urllib.parse.quote(str(cur['id']))}/update", token, body)
            if st != 200:
                sys.exit(f"LỖI: không lưu được mẫu soạn văn bản {lenh} ({st}): {d}")
            cap_nhat += 1
        count += 1
    if tao or cap_nhat:
        print(f"Kho mẫu soạn văn bản: đã tạo {tao}, đã cập nhật {cap_nhat} (tổng {count} mẫu)")
    else:
        print(f"Kho mẫu soạn văn bản: {count} mẫu, không đổi")
    return count


def tim_bo_tri_thuc(token, ten):
    page, da_gom = 1, 0
    while True:
        st, d = call("GET", f"/api/v1/knowledge/search?query={urllib.parse.quote(ten)}&page={page}", token)
        if st != 200 or not isinstance(d, dict):
            sys.exit(f"LỖI: không liệt kê được bộ tri thức ({st}): {d}")
        for it in d["items"]:
            if it.get("name") == ten:
                return it
        da_gom += len(d["items"])
        if not d["items"] or da_gom >= d["total"]:
            return None
        page += 1


def dong_bo_tri_thuc(token=None):
    """Tạo hoặc cập nhật Bộ tri thức cơ sở RAG (Thư viện Pháp lý HTX) trên Open WebUI."""
    if token is None:
        token = admin_token()
    ten = "Thư viện Pháp lý HTX"
    cur = tim_bo_tri_thuc(token, ten)
    if cur:
        print(f"Bộ tri thức: '{ten}' đã có, không đổi")
        return cur["id"]
    payload = {
        "name": ten,
        "description": "Bộ văn bản pháp luật và quy chuẩn hành chính cơ sở (Luật HTX 2023, Nghị định 30/2020/NĐ-CP)",
        "access_grants": PUBLIC_READ,
    }
    st, d = call("POST", "/api/v1/knowledge/create", token, payload)
    if st != 200 or not isinstance(d, dict):
        sys.exit(f"LỖI: không tạo được bộ tri thức '{ten}' ({st}): {d}")
    print(f"Bộ tri thức: đã tạo '{ten}'")
    return d["id"]


def dong_bo_bang_nhac(token):
    st, ds = call("GET", "/api/v1/configs/banners", token)
    if st != 200 or not isinstance(ds, list):
        sys.exit(f"LỖI: không đọc được danh sách băng nhắc ({st}): {ds}")
    # Chỉ so các trường OneBee đặt: Open WebUI lưu qua BannerModel nên trả thêm trường mặc định (vd i18n=None)
    if any(isinstance(b, dict) and all(b.get(k) == v for k, v in BANG_NHAC.items()) for b in ds):
        return
    moi = [b for b in ds if isinstance(b, dict) and b.get("id") != BANG_NHAC["id"]] + [BANG_NHAC]
    st, d = call("POST", "/api/v1/configs/banners", token, {"banners": moi})
    if st != 200:
        sys.exit(f"LỖI: không lưu được băng nhắc ({st}): {d}")
    print("Băng nhắc: đã cập nhật")


def dong_bo_tro_ly():
    with open(os.environ["ONEBEE_LOI_DAN"], encoding="utf-8") as f:
        loi_dan = f.read()
    with open(GOI_Y, encoding="utf-8") as f:
        goi_y = json.load(f)
    base = os.environ["ONEBEE_AI_MODEL"]
    # Open WebUI (từ v0.11): người dùng thường chỉ dùng được Trợ lý khi model nền cũng có bản ghi + quyền đọc.
    # Ẩn model nền khỏi danh sách chọn để nhân viên luôn dùng "Trợ lý OneBee" (có lời dặn tiếng Việt).
    base_form = {"id": base, "name": base, "base_model_id": None, "meta": {"hidden": True},
                 "params": {}, "access_grants": PUBLIC_READ, "is_active": True}
    form = {"id": PRESET_ID, "name": PRESET_NAME, "base_model_id": base,
            # Tắt "công cụ có sẵn" của Open WebUI (lịch, ghi chú, tìm kiếm…): model nhỏ hay gọi nhầm (vd tạo lịch thay vì
            # soạn thông báo) rồi trả lời tiếng Anh; lệnh hoi (API) vốn không dùng công cụ → web và hoi trả lời như nhau
            "meta": {"description": "Trợ lý AI chạy tại chỗ trên OneBee Box — trả lời tiếng Việt, không bịa số liệu.",
                     "capabilities": {"builtin_tools": False},
                     "suggestion_prompts": goi_y},
            "params": {**PARAMS, "system": loi_dan}, "access_grants": PUBLIC_READ, "is_active": True}
    token = admin_token()
    settings_changed = enforce_settings(token)
    base_verb = luu_model(token, base_form)
    verb = luu_model(token, form)
    if verb or base_verb:
        print(f"Trợ lý OneBee: {verb or 'đã cập nhật quyền model nền'} (model nền {base})")
    else:
        print("Trợ lý OneBee: đã cập nhật cài đặt quản trị" if settings_changed else "Trợ lý OneBee: không đổi")
    dong_bo_prompts(token)
    dong_bo_bang_nhac(token)


def cap_khoa(ten):
    """Tạo (hoặc tạo lại nếu quản trị đã xóa) tài khoản máy trạm may-<ten> và in khóa API của nó."""
    pw_file = os.path.join(os.environ["ONEBEE_SECRETS"], f"may-{ten}-webui")
    email = f"may-{ten}@onebee.lan"
    token = None
    if os.path.exists(pw_file):
        with open(pw_file) as f:
            token = signin(email, f.read().strip())
    if not token:  # chưa có, hoặc tài khoản đã bị xóa để thu hồi khóa → tạo lại với mật khẩu mới
        admin = admin_token()
        status, users = call("GET", f"/api/v1/users/?query={email}", admin)
        for u in (users or {}).get("users", []) if status == 200 and isinstance(users, dict) else []:
            if u.get("email") == email:  # còn tài khoản nhưng lệch mật khẩu → xóa để tạo lại
                call("DELETE", f"/api/v1/users/{u['id']}", admin)
        pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        status, data = call("POST", "/api/v1/auths/add", admin,
                            {"name": f"Máy trạm {ten}", "email": email, "password": pw, "role": "user"})
        if status != 200:
            sys.exit(f"LỖI: không tạo được tài khoản {email} ({status}): {data}")
        old = os.umask(0o077)
        with open(pw_file, "w") as f:
            f.write(pw)
        os.umask(old)
        token = signin(email, pw)
    status, data = call("GET", "/api/v1/auths/api_key", token)
    if status != 200 or not (data or {}).get("api_key"):
        status, data = call("POST", "/api/v1/auths/api_key", token)
        if status != 200:
            sys.exit(f"LỖI: không cấp được khóa API cho {email} ({status}): {data}")
    print(data["api_key"])


def lay_khoa(ten):
    """Chỉ đọc khóa API đã cấp cho máy. Không tạo gì: dùng khi chỉ cần in lại cấu hình (dong-bo-may), tránh tác dụng phụ."""
    pw_file = os.path.join(os.environ["ONEBEE_SECRETS"], f"may-{ten}-webui")
    try:
        with open(pw_file, encoding="utf-8") as f:
            pw = f.read().strip()
    except OSError:
        sys.exit(f"Máy {ten} chưa có tài khoản Trợ lý AI (chạy: onebee-box them-may {ten})")
    token = signin(f"may-{ten}@onebee.lan", pw)
    if not token:
        sys.exit(f"Tài khoản may-{ten}@onebee.lan không đăng nhập được (đã bị xóa?) — chạy lại: onebee-box them-may {ten}")
    status, data = call("GET", "/api/v1/auths/api_key", token)
    if status != 200 or not (data or {}).get("api_key"):
        sys.exit(f"Tài khoản may-{ten}@onebee.lan chưa có khóa API — chạy lại: onebee-box them-may {ten}")
    print(data["api_key"])


def xoay_khoa(ten):
    """Đổi khóa API của tài khoản máy trạm may-<ten> (khóa cũ mất hiệu lực), in khóa mới. Không tạo tài khoản."""
    pw_file = os.path.join(os.environ["ONEBEE_SECRETS"], f"may-{ten}-webui")
    try:
        with open(pw_file, encoding="utf-8") as f:
            pw = f.read().strip()
    except OSError:
        sys.exit(f"Máy {ten} chưa có tài khoản Trợ lý AI")
    token = signin(f"may-{ten}@onebee.lan", pw)
    if not token:
        sys.exit(f"Tài khoản may-{ten}@onebee.lan không đăng nhập được (đã bị xóa?)")
    status, data = call("POST", "/api/v1/auths/api_key", token)   # POST tạo lại khóa: khóa cũ không còn dùng được
    if status != 200 or not (data or {}).get("api_key"):
        sys.exit(f"LỖI: không đổi được khóa API của may-{ten}@onebee.lan ({status}): {data}")
    print(data["api_key"])


def doi_mat_khau_quan_tri():
    """Đổi mật khẩu tài khoản quản trị Open WebUI trong CSDL (mật khẩu mới: ONEBEE_MAT_KHAU_MOI). Phiên cũ của quản trị mất hiệu lực."""
    moi = os.environ.get("ONEBEE_MAT_KHAU_MOI", "")
    if len(moi) < 12:
        sys.exit("LỖI: thiếu mật khẩu mới (ONEBEE_MAT_KHAU_MOI)")
    token = admin_token()
    status, data = call("POST", "/api/v1/auths/update/password", token, {"password": os.environ["WEBUI_ADMIN_PASSWORD"], "new_password": moi})
    if status != 200 or data is not True:
        sys.exit(f"LỖI: không đổi được mật khẩu quản trị Open WebUI ({status}): {data}")
    print("Đã đổi mật khẩu quản trị Open WebUI")


def xoa_tai_khoan(ten):
    """Xóa tài khoản máy trạm may-<ten> (khóa API đi theo tài khoản). Không có tài khoản thì coi như xong."""
    email = f"may-{ten}@onebee.lan"
    admin = admin_token()
    status, users = call("GET", f"/api/v1/users/?query={urllib.parse.quote(email)}", admin)
    if status != 200 or not isinstance(users, dict):
        sys.exit(f"LỖI: không tìm được tài khoản {email} ({status}): {users}")
    xoa = 0
    for u in users.get("users", []):
        if u.get("email") == email:
            status, data = call("DELETE", f"/api/v1/users/{u['id']}", admin)
            if status != 200:
                sys.exit(f"LỖI: không xóa được tài khoản {email} ({status}): {data}")
            xoa += 1
    print(f"Đã xóa tài khoản {email}" if xoa else f"Không có tài khoản {email}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "dong-bo-tro-ly":
        dong_bo_tro_ly()
    elif len(sys.argv) >= 2 and sys.argv[1] == "dong-bo-prompts":
        dong_bo_prompts()
    elif len(sys.argv) >= 2 and sys.argv[1] == "dong-bo-tri-thuc":
        dong_bo_tri_thuc()
    elif len(sys.argv) == 3 and sys.argv[1] == "cap-khoa":
        cap_khoa(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "lay-khoa":
        lay_khoa(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "xoay-khoa":
        xoay_khoa(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "doi-mat-khau-quan-tri":
        doi_mat_khau_quan_tri()
    elif len(sys.argv) == 3 and sys.argv[1] == "xoa-tai-khoan":
        xoa_tai_khoan(sys.argv[2])
    else:
        sys.exit(__doc__)
