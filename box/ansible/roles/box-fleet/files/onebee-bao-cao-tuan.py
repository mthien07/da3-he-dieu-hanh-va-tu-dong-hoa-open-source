#!/usr/bin/env python3
"""Nhật ký tuần (Markdown) cho đợt chạy thử / gói bảo trì — được lệnh `onebee-box bao-cao-tuan` gọi.

  onebee-bao-cao-tuan.py <thu-muc-ho-tro> [YYYY-MM-DD] < tinh-trang-may.json

Đọc sổ do n8n ghi: yeu-cau.csv (mã, giờ, máy, loại, mức độ, người báo, mô tả), xu-ly.csv (mã, giờ, cách xử lý, số phút,
ghi chú), khao-sat.csv (giờ, 5 điểm, góp ý). Tuần = thứ Hai–Chủ nhật chứa ngày đưa vào (mặc định hôm nay).
KHÔNG in tên người báo, nội dung mô tả, ghi chú, góp ý (có thể lộ thông tin cá nhân/kinh doanh) → dán được vào báo cáo.
Khảo sát chỉ hiện điểm khi tuần có từ 3 phiếu (giữ ẩn danh).
"""
import csv
import datetime as dt
import json
import os
import statistics
import sys
from collections import Counter

# Nhãn phải khớp box-n8n/vars/main.yml (onebee_ho_tro_loai, onebee_ho_tro_cach_xu_ly) — unit test kiểm
LOAI = ["File không mở được / sai định dạng", "Phần mềm chỉ chạy trên Windows", "Máy in / máy quét", "Mạng / Internet",
        "Gõ tiếng Việt", "Máy chậm / treo", "Sao lưu / mất file", "Khác"]
CACH_XU_LY = ["Hướng dẫn người dùng", "Sửa cấu hình", "Cài thêm phần mềm", "Thay phần cứng",
              "Quay về Windows (máy/phần mềm)", "Chưa xử lý được"]
CHUA_XONG, VE_WINDOWS = "Chưa xử lý được", "Quay về Windows (máy/phần mềm)"
CAU_KHAO_SAT = ["Máy ổn định, nhanh", "Mở/sửa/gửi file Word, Excel", "Gõ tiếng Việt", "Được hỗ trợ kịp thời",
                "Muốn tiếp tục dùng"]
PHIEU_TOI_THIEU = 3


def doc_csv(thu_muc, ten):
    try:
        with open(os.path.join(thu_muc, ten), newline="", encoding="utf-8") as f:
            return [r for r in csv.reader(f) if r]
    except OSError:
        return []


def gio(chuoi):
    try:
        return dt.datetime.strptime(chuoi.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def so_gon(x):
    return f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def bao_cao(thu_muc, ngay, may_tram):
    dau = dt.datetime.combine(ngay - dt.timedelta(days=ngay.weekday()), dt.time())
    cuoi = dau + dt.timedelta(days=7)
    # Chỉ in nhãn có sẵn (không in chữ tự do người dùng gõ); mã xử lý phải có trong sổ yêu cầu
    yeu_cau = [r for r in doc_csv(thu_muc, "yeu-cau.csv") if len(r) >= 5 and gio(r[1])]
    ma_co = {r[0] for r in yeu_cau}
    lan_xu_ly = [r for r in doc_csv(thu_muc, "xu-ly.csv")
                 if len(r) >= 4 and r[0] in ma_co and gio(r[1]) and gio(r[1]) < cuoi]
    xu_ly = {}
    for r in sorted(lan_xu_ly, key=lambda r: gio(r[1])):
        xu_ly[r[0]] = r  # lần ghi sau cùng của 1 mã là kết quả cuối
    tuan = [r for r in yeu_cau if dau <= gio(r[1]) < cuoi]
    xong_tuan = [r for r in xu_ly.values() if dau <= gio(r[1]) < cuoi and r[2] != CHUA_XONG]
    con_mo = [r for r in yeu_cau if gio(r[1]) < cuoi and (r[0] not in xu_ly or xu_ly[r[0]][2] == CHUA_XONG)]

    out = [f"# Nhật ký tuần {dau:%d/%m} – {(cuoi - dt.timedelta(days=1)):%d/%m/%Y}",
           f"_Tự tổng hợp từ OneBee Box lúc {dt.datetime.now():%H:%M %d/%m/%Y}. Không chứa tên người báo, nội dung mô tả._", "",
           "## Yêu cầu hỗ trợ",
           f"- Mới trong tuần: **{len(tuan)}** (gấp: {sum(1 for r in tuan if r[4] == 'gap')})",
           f"- Xử lý xong trong tuần: **{len(xong_tuan)}** · "
           f"Còn mở đến cuối tuần: **{len(con_mo)}**" + (f" (mã: {', '.join(r[0] for r in con_mo)})" if con_mo else "")]
    if tuan:
        out += ["", "| Loại | Số yêu cầu |", "|---|---|"]
        out += [f"| {loai} | {n} |" for loai, n in Counter(r[3] if r[3] in LOAI else "Khác" for r in tuan).most_common()]
    # Công xử lý: cộng mọi lần xử lý trong tuần (kể cả lần chưa xong)
    phut = [int(r[3]) for r in lan_xu_ly if dau <= gio(r[1]) < cuoi and r[3].strip().isdigit()]
    cho = [(gio(xu_ly[r[0]][1]) - gio(r[1])).total_seconds() / 3600 for r in yeu_cau
           if r[0] in xu_ly and xu_ly[r[0]] in xong_tuan and gio(xu_ly[r[0]][1]) >= gio(r[1])]
    if phut:
        out.append(f"- Công xử lý: tổng {sum(phut)} phút, trung vị {so_gon(statistics.median(phut))} phút/lần")
    if cho:
        out.append(f"- Từ lúc báo đến lúc xong: trung vị {so_gon(statistics.median(cho))} giờ, lâu nhất {so_gon(max(cho))} giờ")
    cach = Counter(r[2] if r[2] in CACH_XU_LY else "Khác" for r in xong_tuan)
    if cach:
        out.append("- Cách xử lý: " + "; ".join(f"{k}: {n}" for k, n in cach.most_common()))
    out.append(f"- Phải quay về Windows trong tuần: **{cach.get(VE_WINDOWS, 0)}** lần")

    phieu = [r for r in doc_csv(thu_muc, "khao-sat.csv") if len(r) >= 6 and gio(r[0]) and dau <= gio(r[0]) < cuoi]
    out += ["", "## Khảo sát hài lòng (1–5, ẩn danh)"]
    if not phieu:
        out.append("- Không có phiếu trong tuần.")
    elif len(phieu) < PHIEU_TOI_THIEU:
        out.append(f"- {len(phieu)} phiếu — chưa đủ {PHIEU_TOI_THIEU} phiếu nên không hiện điểm (giữ ẩn danh).")
    else:
        out += [f"- {len(phieu)} phiếu" + (f", {sum(1 for r in phieu if len(r) > 6 and r[6].strip())} phiếu có góp ý"
                                           " (xem trực tiếp trên Box)" if any(len(r) > 6 and r[6].strip() for r in phieu) else ""),
                "", "| Câu | Điểm trung bình |", "|---|---|"]
        for i, cau in enumerate(CAU_KHAO_SAT, start=1):
            diem = [int(r[i]) for r in phieu if r[i].strip().isdigit()]
            out.append(f"| {cau} | {so_gon(statistics.mean(diem)) if diem else '—'} |")

    rows = may_tram.get("may_tram", []) if isinstance(may_tram, dict) else []
    out += ["", "## Tình trạng máy trạm (lúc tổng hợp)",
            f"- {len(rows)} máy, {sum(1 for r in rows if r.get('canh_bao'))} máy cần xử lý"]
    out += [f"- {r['ten']}: " + "; ".join(r["canh_bao"]) for r in rows if r.get("canh_bao")]
    out += ["", "## Kỹ thuật ghi thêm (điền tay)",
            "- File không mở được (loại file, phần mềm tạo ra): ",
            "- Phần mềm phải giữ Windows: ",
            "- Giờ công trong tuần (cài / đào tạo / hỗ trợ): ",
            "- Phần cứng phải thay (SSD, RAM…), chi phí: ",
            "- Mất dữ liệu: không / có (mô tả): ",
            "- Việc sửa trong tuần tới: "]
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        ngay = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today()
    except ValueError:
        sys.exit(f"Ngày không hợp lệ: {sys.argv[2]} (dạng YYYY-MM-DD)")
    try:
        may_tram = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except ValueError:
        may_tram = {}
    print(bao_cao(sys.argv[1], ngay, may_tram))


if __name__ == "__main__":
    main()
