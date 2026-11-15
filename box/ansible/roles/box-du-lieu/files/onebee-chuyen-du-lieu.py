#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Chuyển dữ liệu lịch sử từ tệp CSV/JSON (đơn hàng, hỗ trợ, khảo sát, tình trạng máy)
sang PostgreSQL (lũy đẳng: ON CONFLICT DO NOTHING / DO UPDATE).

Cách dùng:
  onebee-chuyen-du-lieu.py <thu-muc-data> [--sql-out <tep.sql>] [--thuc-thi]
Mặc định in câu lệnh SQL chuẩn UTF-8 ra stdout hoặc nạp vào container onebee-postgres khi có --thuc-thi.
"""
import csv
import glob
import json
import os
import subprocess
import sys


def sql_str(val):
    if val is None:
        return "NULL"
    s = str(val).replace("\x00", "").replace("'", "''")
    return f"'{s}'"


def sql_num(val, mac_dinh=0):
    try:
        return str(float(str(val).strip()))
    except (ValueError, TypeError):
        return str(mac_dinh)


def sql_int(val, mac_dinh=0):
    try:
        return str(int(float(str(val).strip())))
    except (ValueError, TypeError):
        return str(mac_dinh)


def doc_csv_an_toan(duong_dan):
    if not os.path.isfile(duong_dan):
        return []
    try:
        with open(duong_dan, newline="", encoding="utf-8") as f:
            return [r for r in csv.reader(f) if r]
    except OSError:
        return []


def sinh_sql_chuyen_du_lieu(data_dir):
    cau_lenh = ["BEGIN;"]
    dem = {"don_hang": 0, "yeu_cau": 0, "xu_ly": 0, "khao_sat": 0, "may_tram": 0}

    # 1. Đơn hàng: quét mọi tệp *.csv trong <data_dir>/chung/don-hang hoặc <data_dir>/don-hang
    for mau in (
        os.path.join(data_dir, "*", "don-hang", "*.csv"),
        os.path.join(data_dir, "don-hang", "*.csv"),
    ):
        for tep in sorted(glob.glob(mau)):
            for idx, r in enumerate(doc_csv_an_toan(tep)):
                if len(r) < 5:
                    continue
                if r[0].strip().lower() in ("mã đơn", "ma_don", "thời gian", "ngay"):
                    continue
                ma_don = r[0].strip() or f"DH-{os.path.basename(tep)}-{idx}"
                ngay = r[1].strip() if len(r) > 1 and r[1].strip() else None
                khach = r[2].strip() if len(r) > 2 else "Khách lẻ"
                hang = r[3].strip() if len(r) > 3 else "Hàng hóa"
                so_luong = sql_num(r[4] if len(r) > 4 else 1, 1)
                if float(so_luong) <= 0:
                    so_luong = "1"
                don_gia = sql_num(r[5] if len(r) > 5 else 0, 0)
                ghi_chu = r[6].strip() if len(r) > 6 else ""
                ngay_sql = f"{sql_str(ngay)}::timestamptz" if ngay else "now()"
                cau_lenh.append(
                    "INSERT INTO api.don_hang (ma_don, ngay_tao, nguoi_tao, khach_hang, mat_hang, so_luong, don_gia, ghi_chu, trang_thai_duyet) "
                    f"VALUES ({sql_str(ma_don)}, {ngay_sql}, 'lich_su_csv', {sql_str(khach)}, {sql_str(hang)}, {so_luong}, {don_gia}, {sql_str(ghi_chu)}, 'DA_DUYET') "
                    "ON CONFLICT (ma_don) DO NOTHING;"
                )
                dem["don_hang"] += 1

    # 2. Yêu cầu hỗ trợ: <data_dir>/ho-tro/yeu-cau.csv
    ho_tro_dir = os.path.join(data_dir, "ho-tro")
    for r in doc_csv_an_toan(os.path.join(ho_tro_dir, "yeu-cau.csv")):
        if len(r) < 5 or r[0].strip().lower() in ("mã", "ma"):
            continue
        ma, gio, may, loai, muc_do = r[0].strip(), r[1].strip(), r[2].strip(), r[3].strip(), r[4].strip()
        nguoi_bao = (r[5].strip() if len(r) > 5 and r[5].strip() else "nhan_vien")
        mo_ta = (r[6].strip() if len(r) > 6 else "")
        muc = "gap" if muc_do == "gap" else "thuong"
        cau_lenh.append(
            "INSERT INTO api.yeu_cau_ho_tro (ma, thoi_gian, may_tram, loai, muc_do, nguoi_bao, mo_ta, trang_thai_duyet) "
            f"VALUES ({sql_str(ma)}, {sql_str(gio)}::timestamptz, {sql_str(may)}, {sql_str(loai)}, {sql_str(muc)}, {sql_str(nguoi_bao)}, {sql_str(mo_ta)}, 'DA_DUYET') "
            "ON CONFLICT (ma) DO NOTHING;"
        )
        dem["yeu_cau"] += 1

    # 3. Xử lý hỗ trợ: <data_dir>/ho-tro/xu-ly.csv
    for r in doc_csv_an_toan(os.path.join(ho_tro_dir, "xu-ly.csv")):
        if len(r) < 4 or r[0].strip().lower() in ("mã", "ma"):
            continue
        ma, gio, cach, phut = r[0].strip(), r[1].strip(), r[2].strip(), sql_int(r[3], 0)
        ghi_chu = r[4].strip() if len(r) > 4 else ""
        cau_lenh.append(
            "INSERT INTO api.xu_ly_ho_tro (ma_yeu_cau, thoi_gian, nguoi_xu_ly, cach_xu_ly, so_phut, ghi_chu) "
            f"SELECT {sql_str(ma)}, {sql_str(gio)}::timestamptz, 'ky_thuat', {sql_str(cach)}, {phut}, {sql_str(ghi_chu)} "
            f"WHERE EXISTS (SELECT 1 FROM api.yeu_cau_ho_tro WHERE ma = {sql_str(ma)}) "
            f"AND NOT EXISTS (SELECT 1 FROM api.xu_ly_ho_tro WHERE ma_yeu_cau = {sql_str(ma)} AND thoi_gian = {sql_str(gio)}::timestamptz);"
        )
        dem["xu_ly"] += 1

    # 4. Khảo sát: <data_dir>/ho-tro/khao-sat.csv
    for r in doc_csv_an_toan(os.path.join(ho_tro_dir, "khao-sat.csv")):
        if len(r) < 6 or not r[1].strip().isdigit():
            continue
        gio = r[0].strip()
        d = [max(1, min(5, int(r[i].strip()))) for i in range(1, 6)]
        gop_y = r[6].strip() if len(r) > 6 else ""
        cau_lenh.append(
            "INSERT INTO api.khao_sat (thoi_gian, diem_on_dinh, diem_van_ban, diem_tieng_viet, diem_ho_tro, diem_tiep_tuc, gop_y) "
            f"SELECT {sql_str(gio)}::timestamptz, {d[0]}, {d[1]}, {d[2]}, {d[3]}, {d[4]}, {sql_str(gop_y)} "
            f"WHERE NOT EXISTS (SELECT 1 FROM api.khao_sat WHERE thoi_gian = {sql_str(gio)}::timestamptz AND gop_y = {sql_str(gop_y)});"
        )
        dem["khao_sat"] += 1

    # 5. Tình trạng máy trạm: <data_dir>/tinh-trang-may/*.json
    tt_dir = os.path.join(data_dir, "tinh-trang-may")
    if os.path.isdir(tt_dir):
        for tep in sorted(glob.glob(os.path.join(tt_dir, "*.json"))):
            try:
                with open(tep, encoding="utf-8") as f:
                    raw = json.load(f)
                tt = json.loads(raw["du_lieu"]) if isinstance(raw.get("du_lieu"), str) else raw
                ten = tt.get("ten") or os.path.splitext(os.path.basename(tep))[0]
                cau_lenh.append(
                    "INSERT INTO api.tinh_trang_may (ten_may, ip, phien_ban, goi_cho, goi_bao_mat, can_khoi_dong_lai, o_dia_trong_gb, gio_da_bat, lan_sao_luu_cuoi, so_tai_khoan_sudo, hop_le_chu_ky, du_lieu_goc) "
                    f"VALUES ({sql_str(ten)}, {sql_str(tt.get('ip', ''))}, {sql_str(tt.get('phien_ban', ''))}, "
                    f"{sql_int(tt.get('goi_cho'), 0)}, {sql_int(tt.get('goi_bao_mat'), 0)}, "
                    f"{'true' if tt.get('can_khoi_dong_lai') else 'false'}, {sql_num(tt.get('o_dia_trong_gb'), 0)}, "
                    f"{sql_num(tt.get('gio_da_bat'), 0)}, {sql_str(tt.get('lan_sao_luu_cuoi', ''))}, "
                    f"{sql_int(tt.get('so_tai_khoan_sudo'), 0)}, {'true' if 'ky' in raw else 'false'}, "
                    f"{sql_str(json.dumps(tt, ensure_ascii=False))}::jsonb) "
                    "ON CONFLICT (ten_may) DO UPDATE SET "
                    "ip = EXCLUDED.ip, phien_ban = EXCLUDED.phien_ban, goi_cho = EXCLUDED.goi_cho, "
                    "goi_bao_mat = EXCLUDED.goi_bao_mat, can_khoi_dong_lai = EXCLUDED.can_khoi_dong_lai, "
                    "o_dia_trong_gb = EXCLUDED.o_dia_trong_gb, du_lieu_goc = EXCLUDED.du_lieu_goc, cap_nhat_luc = now();"
                )
                dem["may_tram"] += 1
            except (OSError, ValueError, KeyError):
                continue

    cau_lenh.append("COMMIT;")
    return "\n".join(cau_lenh) + "\n", dem


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    data_dir = argv[0]
    sql_text, dem = sinh_sql_chuyen_du_lieu(data_dir)
    if "--sql-out" in argv:
        idx = argv.index("--sql-out")
        with open(argv[idx + 1], "w", encoding="utf-8") as f:
            f.write(sql_text)
    if "--thuc-thi" in argv:
        proc = subprocess.run(
            ["docker", "exec", "-i", "onebee-postgres", "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "onebee"],
            input=sql_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            print(f"LỖI nạp dữ liệu vào PostgreSQL: {proc.stderr}", file=sys.stderr)
            return 1
        print(
            f"Đã chuyển dữ liệu sang PostgreSQL: {dem['don_hang']} đơn hàng, "
            f"{dem['yeu_cau']} yêu cầu hỗ trợ, {dem['xu_ly']} lượt xử lý, "
            f"{dem['khao_sat']} phiếu khảo sát, {dem['may_tram']} máy trạm."
        )
        return 0
    if "--sql-out" not in argv:
        sys.stdout.write(sql_text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
