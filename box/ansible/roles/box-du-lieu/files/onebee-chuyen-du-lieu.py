#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chuyển dữ liệu sổ cũ (CSV đơn hàng, hỗ trợ, khảo sát và JSON tình trạng máy) sang PostgreSQL.

  onebee-chuyen-du-lieu.py <thư-mục-dữ-liệu> [--in-sql]
"""
import csv
import datetime as dt
import decimal
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

TEN_MAY_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
DINH_DANG_GIO = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
LENH_PSQL = [
    "docker",
    "exec",
    "-i",
    "onebee-postgres",
    "psql",
    "-U",
    "postgres",
    "-d",
    "onebee",
    "-v",
    "ON_ERROR_STOP=1",
]
THU_TU_BANG = [
    "don_hang",
    "yeu_cau_ho_tro",
    "xu_ly_ho_tro",
    "khao_sat",
    "tinh_trang_may",
]


def kiem_gio(chuoi):
    v = chuoi.strip()
    if not DINH_DANG_GIO.match(v):
        return None
    try:
        dt.datetime.strptime(v, "%Y-%m-%d %H:%M")
        return v
    except ValueError:
        return None


def kiem_so_thuc(chuoi, duong_han=False):
    v = chuoi.strip()
    if not v:
        return None
    try:
        so = decimal.Decimal(v)
    except decimal.InvalidOperation:
        return None
    if not so.is_finite():
        return None
    if duong_han and so <= 0:
        return None
    if not duong_han and so < 0:
        return None
    return v


def kiem_so_nguyen_khong_am(chuoi):
    v = chuoi.strip()
    if not re.fullmatch(r"\d+", v):
        return None
    return str(int(v))


def kiem_diem_khao_sat(chuoi):
    v = chuoi.strip()
    if v not in ("1", "2", "3", "4", "5"):
        return None
    return v


def kiem_dong_don_hang(cot):
    if len(cot) < 7 or len(cot) > 8:
        return None, "số cột không hợp lệ (cần 7–8 cột)"
    du = list(cot) + ([""] if len(cot) == 7 else [])
    thoi_gian = kiem_gio(du[0])
    if not thoi_gian:
        return None, "thời gian không đúng dạng YYYY-MM-DD HH:MM"
    khach_hang, mat_hang = du[1].strip(), du[2].strip()
    if not khach_hang or not mat_hang:
        return None, "thiếu khách hàng hoặc mặt hàng"
    so_luong = kiem_so_thuc(du[3], duong_han=True)
    don_gia = kiem_so_thuc(du[4], duong_han=False)
    thanh_tien = kiem_so_thuc(du[5], duong_han=False)
    if so_luong is None or don_gia is None or thanh_tien is None:
        return None, "số lượng, đơn giá hoặc thành tiền không hợp lệ"
    ngay_giao = du[6].strip()
    if not ngay_giao:
        return None, "thiếu ngày giao"
    return [thoi_gian, du[1], du[2], so_luong, don_gia, thanh_tien, ngay_giao, du[7]], None


def kiem_dong_yeu_cau(cot):
    if len(cot) < 5 or len(cot) > 7:
        return None, "số cột không hợp lệ (cần 5–7 cột)"
    du = list(cot) + [""] * (7 - len(cot))
    ma = du[0].strip()
    if not ma:
        return None, "thiếu mã yêu cầu"
    thoi_gian = kiem_gio(du[1])
    if not thoi_gian:
        return None, "thời gian không đúng dạng YYYY-MM-DD HH:MM"
    if not du[3].strip() or not du[4].strip():
        return None, "thiếu loại hoặc mức độ"
    return [ma, thoi_gian, du[2], du[3], du[4], du[5], du[6]], None


def kiem_dong_xu_ly(cot):
    if len(cot) < 4 or len(cot) > 5:
        return None, "số cột không hợp lệ (cần 4–5 cột)"
    du = list(cot) + ([""] if len(cot) == 4 else [])
    ma = du[0].strip()
    if not ma:
        return None, "thiếu mã yêu cầu"
    thoi_gian = kiem_gio(du[1])
    if not thoi_gian:
        return None, "thời gian không đúng dạng YYYY-MM-DD HH:MM"
    if not du[2].strip():
        return None, "thiếu cách xử lý"
    so_phut = kiem_so_nguyen_khong_am(du[3])
    if so_phut is None:
        return None, "số phút không phải số nguyên hợp lệ"
    return [ma, thoi_gian, du[2], so_phut, du[4]], None


def kiem_dong_khao_sat(cot):
    if len(cot) < 6 or len(cot) > 7:
        return None, "số cột không hợp lệ (cần 6–7 cột)"
    du = list(cot) + ([""] if len(cot) == 6 else [])
    thoi_gian = kiem_gio(du[0])
    if not thoi_gian:
        return None, "thời gian không đúng dạng YYYY-MM-DD HH:MM"
    diem = []
    for i in range(1, 6):
        d = kiem_diem_khao_sat(du[i])
        if d is None:
            return None, f"điểm câu {i} không nằm trong khoảng 1–5"
        diem.append(d)
    return [thoi_gian, *diem, du[6]], None


CA_CSV = {
    "don_hang": (
        kiem_dong_don_hang,
        "nguon text, dong integer, thoi_gian timestamp without time zone, khach_hang text, mat_hang text, so_luong_kg numeric, don_gia numeric, thanh_tien numeric, ngay_giao text, ghi_chu text",
        ["nguon", "dong", "thoi_gian", "khach_hang", "mat_hang", "so_luong_kg", "don_gia", "thanh_tien", "ngay_giao", "ghi_chu"],
        ["thoi_gian", "khach_hang", "mat_hang", "so_luong_kg", "don_gia", "thanh_tien", "ngay_giao", "ghi_chu", "nguoi_tao", "nguon", "dong"],
        ["thoi_gian", "khach_hang", "mat_hang", "so_luong_kg", "don_gia", "thanh_tien", "ngay_giao", "ghi_chu", "'so-cu'", "nguon", "dong"],
    ),
    "yeu_cau_ho_tro": (
        kiem_dong_yeu_cau,
        "nguon text, dong integer, ma text, thoi_gian timestamp without time zone, may text, loai text, muc_do text, nguoi_bao text, mo_ta text",
        ["nguon", "dong", "ma", "thoi_gian", "may", "loai", "muc_do", "nguoi_bao", "mo_ta"],
        ["ma", "thoi_gian", "may", "loai", "muc_do", "nguoi_bao", "mo_ta", "nguoi_tao", "nguon", "dong"],
        ["ma", "thoi_gian", "may", "loai", "muc_do", "nguoi_bao", "mo_ta", "'so-cu'", "nguon", "dong"],
    ),
    "xu_ly_ho_tro": (
        kiem_dong_xu_ly,
        "nguon text, dong integer, ma text, thoi_gian timestamp without time zone, cach_xu_ly text, so_phut integer, ghi_chu text",
        ["nguon", "dong", "ma", "thoi_gian", "cach_xu_ly", "so_phut", "ghi_chu"],
        ["ma", "thoi_gian", "cach_xu_ly", "so_phut", "ghi_chu", "nguoi_tao", "nguon", "dong"],
        ["ma", "thoi_gian", "cach_xu_ly", "so_phut", "ghi_chu", "'so-cu'", "nguon", "dong"],
    ),
    "khao_sat": (
        kiem_dong_khao_sat,
        "nguon text, dong integer, thoi_gian timestamp without time zone, diem_1 smallint, diem_2 smallint, diem_3 smallint, diem_4 smallint, diem_5 smallint, gop_y text",
        ["nguon", "dong", "thoi_gian", "diem_1", "diem_2", "diem_3", "diem_4", "diem_5", "gop_y"],
        ["thoi_gian", "diem_1", "diem_2", "diem_3", "diem_4", "diem_5", "gop_y", "nguon", "dong"],
        ["thoi_gian", "diem_1", "diem_2", "diem_3", "diem_4", "diem_5", "gop_y", "nguon", "dong"],
    ),
}


def doc_va_kiem_csv(duong_dan, nguon, ten_bang):
    """Đọc và kiểm tra toàn bộ một tệp CSV. Trả về (danh_sách_dòng_hợp_lệ, thông_báo_lỗi_hoặc_None)."""
    ham_kiem = CA_CSV[ten_bang][0]
    dong_hop_le = []
    try:
        with open(duong_dan, newline="", encoding="utf-8") as f:
            for so_dong, dong_csv in enumerate(csv.reader(f), start=1):
                if not dong_csv or (len(dong_csv) == 1 and not dong_csv[0].strip()):
                    continue
                da_kiem, loi = ham_kiem(dong_csv)
                if loi is not None:
                    return None, f"Lỗi {duong_dan} ({nguon}) dòng {so_dong}: {loi}"
                dong_hop_le.append([nguon, str(so_dong), *da_kiem])
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        return None, f"Lỗi đọc tệp {duong_dan} ({nguon}) dòng 1: {e}"
    return dong_hop_le, None


def dung_sql_csv(ten_bang, cac_dong):
    """Dựng giao dịch SQL nạp một tệp CSV qua COPY ... FROM STDIN."""
    if not cac_dong:
        return ""
    _, dinh_nghia_tam, cot_tam, cot_dich, bieu_thuc_chon = CA_CSV[ten_bang]
    bang_tam = f"tam_{ten_bang}"
    bo_nho_csv = io.StringIO()
    ghi = csv.writer(bo_nho_csv, lineterminator="\n")
    for dong in cac_dong:
        ghi.writerow(dong)
    du_lieu_copy = bo_nho_csv.getvalue()
    return (
        "BEGIN;\n"
        f"CREATE TEMP TABLE {bang_tam} ({dinh_nghia_tam}) ON COMMIT DROP;\n"
        f"COPY {bang_tam} ({', '.join(cot_tam)}) FROM STDIN WITH (FORMAT csv);\n"
        f"{du_lieu_copy}"
        "\\.\n"
        f"INSERT INTO onebee.{ten_bang} ({', '.join(cot_dich)}) "
        f"SELECT {', '.join(bieu_thuc_chon)} FROM {bang_tam} "
        "ON CONFLICT (nguon, dong) DO NOTHING;\n"
        "COMMIT;\n"
    )


def doc_va_kiem_json_may(duong_dan):
    """Đọc và kiểm tra một tệp JSON tình trạng máy. Trả về ((ten, nguyen_van, nhan_luc), None) hoặc (None, lỗi)."""
    ten_tep = os.path.basename(duong_dan)
    ten, duoi = os.path.splitext(ten_tep)
    if duoi != ".json" or not TEN_MAY_HOP_LE.match(ten):
        return None, f"Lỗi {duong_dan}: tên máy trạm không hợp lệ ({ten_tep})"
    try:
        with open(duong_dan, encoding="utf-8") as f:
            nguyen_van = f.read().strip()
        obj = json.loads(nguyen_van)
    except (OSError, ValueError) as e:
        return None, f"Lỗi {duong_dan}: tệp JSON hỏng ({e})"
    if not isinstance(obj, dict):
        return None, f"Lỗi {duong_dan}: nội dung JSON không phải đối tượng"
    if obj.get("ten") not in (None, ten):
        return None, f"Lỗi {duong_dan}: trường ten trong JSON không khớp tên tệp ({ten})"
    nhan_luc = obj.get("nhan_luc")
    if isinstance(nhan_luc, bool) or not isinstance(nhan_luc, (int, float)):
        return None, f"Lỗi {duong_dan}: thiếu hoặc sai kiểu trường nhan_luc"
    return [ten, nguyen_van, str(int(nhan_luc))], None


def dung_sql_tinh_trang_may(dong_may):
    """Dựng giao dịch SQL cho một tệp JSON tình trạng máy qua COPY ... FROM STDIN."""
    if not dong_may:
        return ""
    bo_nho_csv = io.StringIO()
    ghi = csv.writer(bo_nho_csv, lineterminator="\n")
    ghi.writerow(dong_may)
    du_lieu_copy = bo_nho_csv.getvalue()
    return (
        "BEGIN;\n"
        "CREATE TEMP TABLE tam_tinh_trang_may (ten text, bao_bi jsonb, nhan_luc bigint) ON COMMIT DROP;\n"
        "COPY tam_tinh_trang_may (ten, bao_bi, nhan_luc) FROM STDIN WITH (FORMAT csv);\n"
        f"{du_lieu_copy}"
        "\\.\n"
        "INSERT INTO onebee.tinh_trang_may (ten, bao_bi, nhan_luc) "
        "SELECT ten, bao_bi, nhan_luc FROM tam_tinh_trang_may "
        "ON CONFLICT (ten) DO UPDATE SET bao_bi = EXCLUDED.bao_bi, nhan_luc = EXCLUDED.nhan_luc "
        "WHERE (onebee.tinh_trang_may.bao_bi, onebee.tinh_trang_may.nhan_luc) "
        "IS DISTINCT FROM (EXCLUDED.bao_bi, EXCLUDED.nhan_luc);\n"
        "COMMIT;\n"
    )


def tim_danh_sach_tep_csv(thu_muc):
    """Trả về danh sách (ten_bang, duong_dan, nguon) của các tệp CSV hiện có."""
    ket_qua = []
    tm_don_hang = os.path.join(thu_muc, "chung", "don-hang")
    if not os.path.isdir(tm_don_hang):
        tm_don_hang = os.path.join(thu_muc, "don-hang")
    if os.path.isdir(tm_don_hang):
        for p in sorted(glob.glob(os.path.join(tm_don_hang, "don-hang-*.csv"))):
            if os.path.isfile(p):
                ket_qua.append(("don_hang", p, f"don-hang/{os.path.basename(p)}"))
    for ten_bang, tương_doi in (
        ("yeu_cau_ho_tro", "ho-tro/yeu-cau.csv"),
        ("xu_ly_ho_tro", "ho-tro/xu-ly.csv"),
        ("khao_sat", "ho-tro/khao-sat.csv"),
    ):
        p = os.path.join(thu_muc, tương_doi)
        if os.path.isfile(p):
            ket_qua.append((ten_bang, p, tương_doi))
    return ket_qua


def tim_danh_sach_tep_json(thu_muc):
    tm_may = os.path.join(thu_muc, "tinh-trang-may")
    if not os.path.isdir(tm_may):
        return []
    return [p for p in sorted(glob.glob(os.path.join(tm_may, "*.json"))) if os.path.isfile(p)]


def _chay_psql_mac_dinh(lenh, input_sql=None):
    return subprocess.run(lenh, input=input_sql, capture_output=True, text=True, encoding="utf-8")


def dem_insert_tu_ket_qua(stdout_text):
    tong = 0
    for m in re.finditer(r"^INSERT\s+\d+\s+(\d+)\s*$", stdout_text or "", flags=re.MULTILINE):
        tong += int(m.group(1))
    return tong


def lay_tong_so_dong_bang(chay_psql):
    cau_lenh = " UNION ALL ".join(
        f"SELECT '{b}', count(*) FROM onebee.{b}" for b in THU_TU_BANG
    ) + ";\n"
    lenh = [*LENH_PSQL, "-At"]
    kq = chay_psql(lenh, input_sql=cau_lenh)
    if getattr(kq, "returncode", 0) != 0:
        return None, (getattr(kq, "stderr", "") or "").strip() or "không truy vấn được tổng số dòng"
    tong = {b: 0 for b in THU_TU_BANG}
    for dong in (getattr(kq, "stdout", "") or "").splitlines():
        if "|" in dong:
            ten, _, so = dong.strip().partition("|")
            if ten in tong and so.isdigit():
                tong[ten] = int(so)
    return tong, None


def in_bang_tong_ket(so_dong_tep, so_moi_nap=None, tong_trong_bang=None, luong=None):
    luong = luong or sys.stdout
    if so_moi_nap is None or tong_trong_bang is None:
        print(f"{'Bảng':<18}  {'Số dòng trong tệp':>17}", file=luong)
        for b in THU_TU_BANG:
            print(f"{b:<18}  {so_dong_tep[b]:>17}", file=luong)
        return
    print(
        f"{'Bảng':<18}  {'Số dòng trong tệp':>17}  {'Số dòng mới nạp':>15}  {'Tổng số dòng trong bảng':>23}",
        file=luong,
    )
    for b in THU_TU_BANG:
        print(
            f"{b:<18}  {so_dong_tep[b]:>17}  {so_moi_nap[b]:>15}  {tong_trong_bang[b]:>23}",
            file=luong,
        )


def sao_luu_truoc_chuyen(duong_dan):
    ban_sao = f"{duong_dan}.truoc-chuyen"
    if not os.path.exists(ban_sao):
        shutil.copy2(duong_dan, ban_sao)


def chay(thu_muc, in_sql=False, chay_psql=None):
    chay_psql = chay_psql or _chay_psql_mac_dinh
    ma_thoat = 0
    so_dong_tep = {b: 0 for b in THU_TU_BANG}
    so_moi_nap = {b: 0 for b in THU_TU_BANG}
    cac_giao_dich = []  # (ten_bang, duong_dan_csv_hoac_None, sql)

    for ten_bang, duong_dan, nguon in tim_danh_sach_tep_csv(thu_muc):
        cac_dong, loi = doc_va_kiem_csv(duong_dan, nguon, ten_bang)
        if loi is not None:
            print(loi, file=sys.stderr)
            ma_thoat = 1
            continue
        so_dong_tep[ten_bang] += len(cac_dong)
        sql = dung_sql_csv(ten_bang, cac_dong)
        if sql:
            cac_giao_dich.append((ten_bang, duong_dan, sql))

    for duong_dan in tim_danh_sach_tep_json(thu_muc):
        dong_may, loi = doc_va_kiem_json_may(duong_dan)
        if loi is not None:
            print(loi, file=sys.stderr)
            ma_thoat = 1
            continue
        so_dong_tep["tinh_trang_may"] += 1
        sql = dung_sql_tinh_trang_may(dong_may)
        if sql:
            cac_giao_dich.append(("tinh_trang_may", None, sql))

    if in_sql:
        for _, _, sql in cac_giao_dich:
            sys.stdout.write(sql)
        in_bang_tong_ket(so_dong_tep, luong=sys.stderr)
        return ma_thoat

    for ten_bang, duong_dan_csv, sql in cac_giao_dich:
        if duong_dan_csv is not None:
            try:
                sao_luu_truoc_chuyen(duong_dan_csv)
            except OSError as e:
                print(f"Lỗi tạo bản sao lưu cho {duong_dan_csv}: {e}", file=sys.stderr)
                ma_thoat = 1
                continue
        try:
            kq = chay_psql(LENH_PSQL, input_sql=sql)
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Lỗi gọi PostgreSQL cho bảng {ten_bang}: {e}", file=sys.stderr)
            ma_thoat = 1
            continue
        if getattr(kq, "returncode", 0) != 0:
            chi_tiet = (getattr(kq, "stderr", "") or "").strip()
            print(f"Lỗi nạp dữ liệu vào bảng {ten_bang}: {chi_tiet or 'mã thoát khác 0'}", file=sys.stderr)
            ma_thoat = 1
            continue
        so_moi_nap[ten_bang] += dem_insert_tu_ket_qua(getattr(kq, "stdout", ""))

    try:
        tong_trong_bang, loi_tong = lay_tong_so_dong_bang(chay_psql)
    except (OSError, subprocess.SubprocessError) as e:
        tong_trong_bang, loi_tong = None, str(e)
    if loi_tong is not None:
        print(f"Lỗi đọc tổng số dòng trong cơ sở dữ liệu: {loi_tong}", file=sys.stderr)
        tong_trong_bang = {b: 0 for b in THU_TU_BANG}
        ma_thoat = 1

    in_bang_tong_ket(so_dong_tep, so_moi_nap, tong_trong_bang, luong=sys.stdout)
    return ma_thoat


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    tham_so = argv[1:]
    in_sql = False
    con_lai = []
    for ts in tham_so:
        if ts == "--in-sql":
            in_sql = True
        elif ts.startswith("-"):
            print(f"Tham số không hợp lệ: {ts}", file=sys.stderr)
            return 2
        else:
            con_lai.append(ts)
    if len(con_lai) != 1:
        print("Cách dùng: onebee-chuyen-du-lieu.py <thư-mục-dữ-liệu> [--in-sql]", file=sys.stderr)
        return 2
    return chay(con_lai[0], in_sql=in_sql)


if __name__ == "__main__":
    sys.exit(main())
