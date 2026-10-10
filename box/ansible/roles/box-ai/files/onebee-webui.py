#!/usr/bin/env python3
"""Quản lý Open WebUI của OneBee Box qua API (chỉ thư viện chuẩn). Được lệnh onebee-box gọi.

  onebee-webui.py dong-bo-tro-ly   Tạo/cập nhật model "Trợ lý OneBee" (model nền + lời dặn tiếng Việt), mở cho mọi người
  onebee-webui.py cap-khoa <ten>   Tạo tài khoản máy trạm may-<ten> (nếu chưa có) và in khóa API để máy trạm dùng lệnh hoi
  onebee-webui.py lay-khoa <ten>   CHỈ ĐỌC: in khóa API đã có của tài khoản may-<ten> (không tạo tài khoản/khóa; chưa có thì thoát lỗi, mã 1)
  onebee-webui.py xoa-tai-khoan <ten>   Xóa tài khoản may-<ten> (thu hồi khóa hoi của máy; idempotent)

Đọc cấu hình từ biến môi trường: WEBUI_URL, WEBUI_ADMIN_EMAIL, WEBUI_ADMIN_PASSWORD, ONEBEE_AI_MODEL,
ONEBEE_LOI_DAN (đường dẫn file lời dặn), ONEBEE_SECRETS (thư mục bí mật).
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


def enforce_settings(token):
    """Tắt đăng ký tự do, bật + giới hạn khóa API, tắt chia sẻ cộng đồng, đặt thời hạn phiên, chỉnh quyền mặc định của người dùng."""
    changed = False
    status, cfg = call("GET", "/api/v1/auths/admin/config", token)
    if status != 200:
        sys.exit(f"LỖI: không đọc được cài đặt quản trị ({status}): {cfg}")
    if any(cfg.get(k) != v for k, v in ADMIN_CONFIG.items()):
        # bỏ trường rỗng (vd I18N=null) — gửi lại null bị Open WebUI từ chối
        payload = {k: v for k, v in {**cfg, **ADMIN_CONFIG}.items() if v is not None}
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


def dong_bo_tro_ly():
    with open(os.environ["ONEBEE_LOI_DAN"], encoding="utf-8") as f:
        loi_dan = f.read()
    base = os.environ["ONEBEE_AI_MODEL"]
    # Open WebUI (từ v0.11): người dùng thường chỉ dùng được Trợ lý khi model nền cũng có bản ghi + quyền đọc.
    # Ẩn model nền khỏi danh sách chọn để nhân viên luôn dùng "Trợ lý OneBee" (có lời dặn tiếng Việt).
    base_form = {"id": base, "name": base, "base_model_id": None, "meta": {"hidden": True},
                 "params": {}, "access_grants": PUBLIC_READ, "is_active": True}
    form = {"id": PRESET_ID, "name": PRESET_NAME, "base_model_id": base,
            # Tắt "công cụ có sẵn" của Open WebUI (lịch, ghi chú, tìm kiếm…): model nhỏ hay gọi nhầm (vd tạo lịch thay vì
            # soạn thông báo) rồi trả lời tiếng Anh; lệnh hoi (API) vốn không dùng công cụ → web và hoi trả lời như nhau
            "meta": {"description": "Trợ lý AI chạy tại chỗ trên OneBee Box — trả lời tiếng Việt, không bịa số liệu.",
                     "capabilities": {"builtin_tools": False}},
            "params": {**PARAMS, "system": loi_dan}, "access_grants": PUBLIC_READ, "is_active": True}
    token = admin_token()
    settings_changed = enforce_settings(token)
    base_verb = luu_model(token, base_form)
    verb = luu_model(token, form)
    if verb or base_verb:
        print(f"Trợ lý OneBee: {verb or 'đã cập nhật quyền model nền'} (model nền {base})")
    else:
        print("Trợ lý OneBee: đã cập nhật cài đặt quản trị" if settings_changed else "Trợ lý OneBee: không đổi")


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
    elif len(sys.argv) == 3 and sys.argv[1] == "cap-khoa":
        cap_khoa(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "lay-khoa":
        lay_khoa(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "xoa-tai-khoan":
        xoa_tai_khoan(sys.argv[2])
    else:
        sys.exit(__doc__)
