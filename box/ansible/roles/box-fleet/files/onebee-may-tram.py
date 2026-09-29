#!/usr/bin/env python3
"""Tình trạng các máy trạm OneBee (được lệnh onebee-box gọi, chỉ thư viện chuẩn).

  onebee-may-tram.py bang    <thu-muc-tinh-trang> ten=gio ...        In bảng cho người quản trị
  onebee-may-tram.py payload <thu-muc-tinh-trang> <trang_thai> <noi_dung> ten=gio ...
                                                                     JSON báo cáo gửi n8n (email hằng ngày)
  onebee-may-tram.py kho     <thu-muc-tinh-trang> ten ...            In "ten ip" của máy đã báo tình trạng trong 2 giờ qua
                                                                     (để cập nhật qua SSH)

ten=gio: tên máy trạm đã cấp (onebee-box them-may) = số giờ từ lần sao lưu cuối (Box tự đọc kho sao lưu;
"null" = chưa có bản nào, "loi" = không đọc được kho, ví dụ đang bận dọn).
Tình trạng khác (cập nhật, ổ đĩa...) do máy trạm tự gửi mỗi giờ qua n8n → <thu-muc>/<ten>.json.
"""
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
NGUONG_IP_GIO = 2            # chỉ SSH tới IP máy trạm báo trong 2 giờ gần nhất (IP động có thể đã đổi chủ)
TEN_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")


def doc_tinh_trang(thu_muc, ten):
    try:
        with open(os.path.join(thu_muc, f"{ten}.json"), encoding="utf-8") as f:
            tt = json.load(f)
        return tt if isinstance(tt, dict) and tt.get("ten") == ten else None
    except (OSError, ValueError):
        return None


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
    else:
        tom_tat.append(f"sao lưu {gio_truoc(gio_sao_luu)}")
        if gio_sao_luu > NGUONG_SAO_LUU_GIO:
            canh_bao.append(f"quá {NGUONG_SAO_LUU_GIO // 24} ngày chưa sao lưu")
    if tt is None:
        canh_bao.append("chưa báo tình trạng (máy chưa cài bản mới hoặc chưa bật lần nào)")
        return canh_bao, "; ".join(tom_tat)
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
    return canh_bao, " · ".join(tom_tat)


def tong_hop(thu_muc, cap):
    bay_gio = time.time()
    rows = []
    for muc in cap:
        ten, _, gio = muc.partition("=")
        if not TEN_HOP_LE.match(ten):
            continue
        gio_sao_luu = None if gio in ("", "null") else "loi" if not gio.isdigit() else int(gio)
        tt = doc_tinh_trang(thu_muc, ten)
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


def main(argv):
    if len(argv) < 3 or argv[1] not in ("bang", "payload", "kho"):
        sys.exit(__doc__)
    lenh, thu_muc = argv[1], argv[2]
    if lenh == "kho":
        for ten in argv[3:]:
            tt = doc_tinh_trang(thu_muc, ten) if TEN_HOP_LE.match(ten) else None
            nhan = so(tt or {}, "nhan_luc")
            if nhan is None or time.time() - nhan > NGUONG_IP_GIO * 3600:
                continue
            try:
                ip = str(ipaddress.IPv4Address((tt or {}).get("ip", "")))
            except ValueError:
                continue
            print(ten, ip)
        return 0
    if lenh == "bang":
        return in_bang(tong_hop(thu_muc, argv[3:]))
    trang_thai, noi_dung = argv[3], argv[4]
    rows = [] if trang_thai == "THU" else tong_hop(thu_muc, argv[5:])
    print(json.dumps({"trang_thai": trang_thai, "noi_dung": noi_dung, "nguong_gio": NGUONG_SAO_LUU_GIO,
                      "may_tram": rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
