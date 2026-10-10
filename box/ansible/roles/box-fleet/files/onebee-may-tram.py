#!/usr/bin/env python3
"""Tình trạng các máy trạm OneBee (được lệnh onebee-box gọi, chỉ thư viện chuẩn).

  onebee-may-tram.py bang    <thu-muc-tinh-trang> ten=gio ...        In bảng cho người quản trị
  onebee-may-tram.py payload <thu-muc-tinh-trang> <trang_thai> <noi_dung> ten=gio ...
                                                                     JSON báo cáo gửi n8n (email hằng ngày)
  onebee-may-tram.py kho     <thu-muc-tinh-trang> ten ...            In "ten ip [ghim|chua-ghim]" của máy có thể SSH tới (cập nhật qua SSH)

Biến môi trường (do lệnh onebee-box đặt):
  ONEBEE_BI_MAT  thư mục bí mật của Box (có may-<ten>-repo): bật kiểm chữ ký báo cáo. Không đặt → không kiểm (chỉ dùng khi thử).
  ONEBEE_DA_GHIM danh sách máy đã ghim khóa SSH (ngăn cách bằng dấu phẩy): bật cột thứ 3 và quy tắc tin IP của lệnh kho.

Chữ ký báo cáo (rà soát bảo mật 10/10, F2): máy trạm gửi {"ten", "du_lieu": "<JSON dạng chuỗi>", "ky": HMAC-SHA256}. Khóa ký suy từ
mật khẩu kho sao lưu của máy (RESTIC_PASSWORD — chưa từng đi qua mạng), n8n KHÔNG giữ khóa nên không giả được báo cáo; Box tự kiểm ở đây.
Báo cáo cũ (JSON phẳng, không chữ ký) vẫn đọc được nhưng bị gắn nhãn "chưa ký" và không được tin để chọn địa chỉ SSH máy chưa ghim.

ten=gio: tên máy trạm đã cấp (onebee-box them-may) = số giờ từ lần sao lưu cuối (Box tự đọc kho sao lưu;
"null" = chưa có bản nào, "loi" = không đọc được kho, ví dụ đang bận dọn; số âm = có bản ghi ngày tương lai).
Tình trạng khác (cập nhật, ổ đĩa...) do máy trạm tự gửi mỗi giờ qua n8n → <thu-muc>/<ten>.json.
"""
import hashlib
import hmac
import ipaddress
import json
import os
import re
import sys
import time

NGUONG_SAO_LUU_GIO = 72      # quá 3 ngày chưa sao lưu → cảnh báo
NGUONG_IM_LANG_GIO = 48      # quá 2 ngày không báo tình trạng → máy tắt/mất mạng/gỡ bộ cài?
NGUONG_O_TRONG = 10          # ổ hệ thống còn dưới 10% → sắp đầy
NGUONG_GOI_CHO = 30          # quá 30 gói chờ cập nhật → tự động cập nhật có vấn đề
NGUONG_TAI_KHOAN_SUDO = 1    # quá 1 tài khoản có sudo → cảnh báo (chủ trương: nhân viên không có sudo)
NGUONG_IP_GIO = 2            # máy CHƯA ghim khóa SSH: chỉ SSH tới IP báo (có chữ ký hợp lệ) trong 2 giờ gần nhất
NGUONG_IP_DA_GHIM_NGAY = 30  # máy ĐÃ ghim khóa SSH: IP cũ tới 30 ngày vẫn thử (nếu IP đã sang máy khác, khóa host lệch → SSH dừng)
SAI_LECH_DONG_HO_GIAY = 600  # giờ máy trạm ký (gui_luc) lệch giờ Box nhận quá 10 phút → coi là phát lại / đồng hồ sai
MUC_DICH_KY = b"onebee-tinh-trang-v1"
TEN_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")


def ky_bao_cao(mat_khau, du_lieu):
    """Chữ ký HMAC-SHA256 (hex) của chuỗi du_lieu. Khóa ký = HMAC(mật khẩu kho sao lưu, mục đích) để tách mục đích dùng mật khẩu."""
    khoa = hmac.new(mat_khau.encode("utf-8"), MUC_DICH_KY, hashlib.sha256).digest()
    return hmac.new(khoa, du_lieu.encode("utf-8"), hashlib.sha256).hexdigest()


def doc_mat_khau(bi_mat, ten):
    try:
        with open(os.path.join(bi_mat, f"may-{ten}-repo"), encoding="utf-8") as f:
            mk = f.read().strip()
        return mk or None
    except OSError:
        return None


def kiem_chu_ky(env, ten, bi_mat):
    """Giải bao bì báo cáo có chữ ký. Trả về (tt, trang_thai): tt là dict (hoặc None), trang_thai: hop-le | sai."""
    mk = doc_mat_khau(bi_mat, ten)
    du_lieu, ky = env.get("du_lieu"), env.get("ky")
    if not mk or not isinstance(du_lieu, str) or not isinstance(ky, str):
        return None, "sai"
    if not hmac.compare_digest(ky_bao_cao(mk, du_lieu), ky):
        return None, "sai"
    try:
        tt = json.loads(du_lieu)
    except ValueError:
        return None, "sai"
    gui_luc, nhan_luc = so(tt, "gui_luc") if isinstance(tt, dict) else None, so(env, "nhan_luc")
    if not isinstance(tt, dict) or tt.get("ten") != ten or gui_luc is None or nhan_luc is None \
            or abs(nhan_luc - gui_luc) > SAI_LECH_DONG_HO_GIAY:
        return None, "sai"
    return dict(tt, nhan_luc=nhan_luc), "hop-le"


def doc_tinh_trang(thu_muc, ten, bi_mat=None):
    """Đọc <ten>.json. Có bi_mat thì kiểm chữ ký và gắn nhãn tt["_ky"]: hop-le | sai | chua-ky (báo cáo cũ, JSON phẳng)."""
    try:
        with open(os.path.join(thu_muc, f"{ten}.json"), encoding="utf-8") as f:
            tt = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(tt, dict) or tt.get("ten") != ten:
        return None
    if bi_mat is None:
        return tt
    if "du_lieu" in tt:
        goc, trang_thai = kiem_chu_ky(tt, ten, bi_mat)
        return dict(goc, _ky=trang_thai) if goc else {"ten": ten, "_ky": "sai"}
    return dict(tt, _ky="chua-ky")


def so(tt, khoa):
    v = tt.get(khoa)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def gio_truoc(gio):
    if gio < 1:
        return "vừa xong"
    return f"{int(gio)} giờ trước" if gio < 48 else f"{int(gio // 24)} ngày trước"


def danh_gia(ten, gio_sao_luu, tt, bay_gio):
    """Trả về (danh sách cảnh báo, tóm tắt 1 dòng) cho 1 máy trạm."""
    canh_bao, tom_tat = [], []
    if gio_sao_luu == "loi":
        canh_bao.append("Box không đọc được kho sao lưu của máy này (đang bận? thử lại sau)")
    elif gio_sao_luu is None:
        canh_bao.append("chưa từng sao lưu lên Box")
    elif gio_sao_luu < 0:
        canh_bao.append("có bản sao lưu ghi ngày tương lai — nghi bị giả mạo, kiểm tra máy ngay")
    else:
        tom_tat.append(f"sao lưu {gio_truoc(gio_sao_luu)}")
        if gio_sao_luu > NGUONG_SAO_LUU_GIO:
            canh_bao.append(f"quá {NGUONG_SAO_LUU_GIO // 24} ngày chưa sao lưu")
    if tt is None:
        canh_bao.append("chưa báo tình trạng (máy chưa cài bản mới hoặc chưa bật lần nào)")
        return canh_bao, "; ".join(tom_tat)
    if tt.get("_ky") == "sai":
        canh_bao.append("báo cáo tình trạng sai chữ ký (giả mạo, hoặc mật khẩu sao lưu trên máy khác với Box) — kiểm tra máy này")
        return canh_bao, "; ".join(tom_tat)
    if tt.get("_ky") == "chua-ky":
        canh_bao.append("báo cáo chưa có chữ ký (máy chạy mã cũ) — chạy lại bộ cài OneBee OS trên máy này")
    nhan = so(tt, "nhan_luc")
    if nhan is not None:
        im_lang = (bay_gio - nhan) / 3600
        tom_tat.append(f"báo tình trạng {gio_truoc(im_lang)}")
        if im_lang > NGUONG_IM_LANG_GIO:
            canh_bao.append(f"{int(im_lang // 24)} ngày không liên lạc (máy tắt hoặc mất mạng?)")
    o_trong = so(tt, "o_trong_phan_tram")
    if o_trong is not None:
        tom_tat.append(f"ổ trống {o_trong:g}%")
        if o_trong < NGUONG_O_TRONG:
            canh_bao.append(f"ổ đĩa sắp đầy (còn {o_trong:g}%)")
    bao_mat, cho = so(tt, "bao_mat_cho") or 0, so(tt, "cap_nhat_cho") or 0
    if bao_mat:
        canh_bao.append(f"{bao_mat} bản vá bảo mật chưa cài")
    elif cho >= NGUONG_GOI_CHO:
        canh_bao.append(f"{cho} gói chờ cập nhật")
    else:
        tom_tat.append("đã cập nhật" if not cho else f"{cho} gói chờ cập nhật")
    if tt.get("can_khoi_dong_lai") is True:
        canh_bao.append("cần khởi động lại để hoàn tất cập nhật")
    sudo_so = so(tt, "sudo_so")
    if sudo_so is not None and sudo_so > NGUONG_TAI_KHOAN_SUDO:
        canh_bao.append(f"{int(sudo_so)} tài khoản có quyền sudo (chỉ quản trị máy nên có — nhân viên dùng tài khoản thường)")
    return canh_bao, " · ".join(tom_tat)


def tong_hop(thu_muc, cap):
    bay_gio = time.time()
    bi_mat = os.environ.get("ONEBEE_BI_MAT") or None
    rows = []
    for muc in cap:
        ten, _, gio = muc.partition("=")
        if not TEN_HOP_LE.match(ten):
            continue
        gio_sao_luu = None if gio in ("", "null") else int(gio) if re.fullmatch(r"-?\d+", gio) else "loi"
        tt = doc_tinh_trang(thu_muc, ten, bi_mat)
        canh_bao, tom_tat = danh_gia(ten, gio_sao_luu, tt, bay_gio)
        rows.append({"ten": ten, "gio_tu_lan_cuoi": gio_sao_luu if gio_sao_luu != "loi" else None, "canh_bao": canh_bao, "tom_tat": tom_tat,
                     "ip": (tt or {}).get("ip"), "phien_ban": (tt or {}).get("phien_ban")})
    return rows


def in_bang(rows):
    if not rows:
        print("Chưa cấp máy trạm nào (sudo onebee-box them-may <tên-máy>).")
        return 0
    rong = max(len(r["ten"]) for r in rows)
    for r in rows:
        trang = "CẦN XỬ LÝ" if r["canh_bao"] else "ỔN"
        print(f"{r['ten']:<{rong}}  {trang:<9}  {r['tom_tat']}")
        for c in r["canh_bao"]:
            print(f"{'':<{rong}}  → {c}")
    can = sum(1 for r in rows if r["canh_bao"])
    print(f"\n{len(rows)} máy trạm, {can} máy cần xử lý.")
    return 0


def in_kho(thu_muc, danh_sach):
    """In "ten ip" (thêm cột ghim|chua-ghim khi có ONEBEE_DA_GHIM) cho máy có thể SSH tới.

    Máy ĐÃ ghim khóa SSH: tin IP báo trong 30 ngày (khóa host lệch thì SSH tự dừng), chỉ loại báo cáo sai chữ ký.
    Máy CHƯA ghim: chỉ tin IP trong báo cáo CÓ CHỮ KÝ HỢP LỆ, mới trong 2 giờ — báo cáo chưa ký (khóa chung gửi qua HTTP) không đủ tin để
    Box đem khóa quản trị tới đúng địa chỉ đó.
    """
    bi_mat = os.environ.get("ONEBEE_BI_MAT") or None
    da_ghim_env = os.environ.get("ONEBEE_DA_GHIM")
    da_ghim = {t for t in (da_ghim_env or "").split(",") if t}
    for ten in danh_sach:
        tt = doc_tinh_trang(thu_muc, ten, bi_mat) if TEN_HOP_LE.match(ten) else None
        nhan = so(tt or {}, "nhan_luc")
        if nhan is None:
            continue
        ghim = ten in da_ghim
        if bi_mat is not None and da_ghim_env is not None:
            ky = (tt or {}).get("_ky")
            if ky == "sai" or (not ghim and ky != "hop-le"):
                continue
        tuoi_toi_da = NGUONG_IP_DA_GHIM_NGAY * 86400 if ghim else NGUONG_IP_GIO * 3600
        if time.time() - nhan > tuoi_toi_da:
            continue
        try:
            ip = str(ipaddress.IPv4Address((tt or {}).get("ip", "")))
        except ValueError:
            continue
        cot = [ten, ip]
        if da_ghim_env is not None:
            cot.append("ghim" if ghim else "chua-ghim")
        print(*cot)
    return 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("bang", "payload", "kho"):
        sys.exit(__doc__)
    lenh, thu_muc = argv[1], argv[2]
    if lenh == "kho":
        return in_kho(thu_muc, argv[3:])
    if lenh == "bang":
        return in_bang(tong_hop(thu_muc, argv[3:]))
    trang_thai, noi_dung = argv[3], argv[4]
    rows = [] if trang_thai == "THU" else tong_hop(thu_muc, argv[5:])
    print(json.dumps({"trang_thai": trang_thai, "noi_dung": noi_dung, "nguong_gio": NGUONG_SAO_LUU_GIO,
                      "may_tram": rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
