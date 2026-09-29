#!/usr/bin/env python3
"""Đo 1 máy trạm Linux (trước/sau khi cài OneBee OS) → thêm 1 dòng vào file CSV. Máy Windows: đo tay theo
docs/huong-dan/do-truoc-sau.md, ghi vào cùng file với cùng các cột. Chỉ so sánh số đo trên CÙNG một máy.

  python3 tests/do-dac/do-may.py --don-vi htx-onebee --may ketoan-01 --giai-doan sau \\
      --bam-gio-khoi-dong 48 --bam-gio-van-ban 6.5 --bam-gio-trinh-duyet 4 -o reports/do-dac/htx-onebee.csv

Cột "bam_gio_*": đo bằng đồng hồ bấm giờ, CÙNG cách trên Windows và OneBee OS → cột dùng để so sánh trước/sau.
Cột "tu_do_*": máy tự đo (chỉ có trên Linux) → dùng so sánh giữa các lần đo trên Linux.
Chạy ngay sau khi khởi động và đăng nhập (chưa mở ứng dụng nào); tự đo lúc mở ứng dụng lần đầu (khởi động nguội).
Cần: systemd-analyze, xdotool (sudo apt install xdotool).
"""
import argparse
import csv
import datetime
import os
import re
import shutil
import subprocess
import time

COT = ["ngay", "don_vi", "may", "giai_doan", "he_dieu_hanh", "cpu", "ram_tong_mb", "loai_o",
       "bam_gio_khoi_dong_giay", "bam_gio_mo_van_ban_giay", "bam_gio_mo_trinh_duyet_giay", "ram_trong_mb", "o_trong_gb",
       "tu_do_khoi_dong_giay", "tu_do_mo_van_ban_giay", "tu_do_mo_trinh_duyet_giay", "da_bat_phut", "ghi_chu"]


def chay(lenh, timeout=30):
    try:
        return subprocess.run(lenh, capture_output=True, text=True, timeout=timeout,
                              env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def giay(chuoi):
    """'1min 2.345s' / '23.4s' / '850ms' → số giây."""
    tong = 0.0
    for so, dv in re.findall(r"([\d.]+)(min|ms|s)\b", chuoi):
        tong += float(so) * {"min": 60, "s": 1, "ms": 0.001}[dv]
    return round(tong, 1) if tong else ""


def khoi_dong():
    m = re.search(r"^Startup finished in .*?=\s*(.+?)\s*$", chay(["systemd-analyze"]), re.M)
    return giay(m.group(1)) if m else ""


def meminfo(khoa):
    with open("/proc/meminfo") as f:
        for dong in f:
            if dong.startswith(khoa + ":"):
                return int(dong.split()[1]) // 1024
    return ""


def loai_o():
    nguon = chay(["findmnt", "-no", "SOURCE", "/"]).strip()
    goc = chay(["lsblk", "-no", "PKNAME", nguon]).strip().splitlines() if nguon else []
    ten = (goc[0] if goc and goc[0] else os.path.basename(nguon)).strip()
    try:
        with open(f"/sys/block/{ten}/queue/rotational") as f:
            return "HDD" if f.read().strip() == "1" else "SSD"
    except OSError:
        return ""


def mo_ung_dung(lenh, ten_cua_so, cho=120):
    """Giây từ lúc bấm mở tới khi cửa sổ hiện ra; rồi đóng ứng dụng. '' nếu không có ứng dụng/xdotool/màn hình."""
    if not (shutil.which(lenh[0]) and shutil.which("xdotool") and os.environ.get("DISPLAY")):
        return ""
    bat_dau = time.monotonic()
    p = subprocess.Popen(lenh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        while time.monotonic() - bat_dau < cho:
            if chay(["xdotool", "search", "--onlyvisible", "--name", ten_cua_so], timeout=5).strip():
                return round(time.monotonic() - bat_dau, 1)
            time.sleep(0.2)
        return ""
    finally:
        try:
            os.killpg(p.pid, 15)
        except ProcessLookupError:
            pass
        time.sleep(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--don-vi", required=True)
    ap.add_argument("--may", required=True)
    ap.add_argument("--giai-doan", required=True, choices=["truoc", "sau"])
    for ten in ("khoi-dong", "van-ban", "trinh-duyet"):
        ap.add_argument(f"--bam-gio-{ten}", type=float, default=None, metavar="GIÂY")
    ap.add_argument("--ghi-chu", default="")
    ap.add_argument("-o", "--csv", required=True)
    a = ap.parse_args()

    with open("/proc/uptime") as f:
        da_bat = round(float(f.read().split()[0]) / 60, 1)
    ghi_chu = [a.ghi_chu] if a.ghi_chu else []
    if da_bat > 15:
        ghi_chu.append(f"đo sau khi bật {da_bat:g} phút — RAM trống kém tin cậy")
    os_rel = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', open("/etc/os-release").read(), re.M))
    cpu = re.search(r"^model name\s*:\s*(.+)$", open("/proc/cpuinfo").read(), re.M)
    dong = {
        "ngay": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "don_vi": a.don_vi, "may": a.may,
        "giai_doan": a.giai_doan, "he_dieu_hanh": os_rel.get("PRETTY_NAME", ""),
        "cpu": cpu.group(1).strip() if cpu else "", "ram_tong_mb": meminfo("MemTotal"), "loai_o": loai_o(),
        "bam_gio_khoi_dong_giay": a.bam_gio_khoi_dong if a.bam_gio_khoi_dong is not None else "",
        "bam_gio_mo_van_ban_giay": a.bam_gio_van_ban if a.bam_gio_van_ban is not None else "",
        "bam_gio_mo_trinh_duyet_giay": a.bam_gio_trinh_duyet if a.bam_gio_trinh_duyet is not None else "",
        "ram_trong_mb": meminfo("MemAvailable"), "o_trong_gb": round(shutil.disk_usage("/").free / 1e9, 1),
        "tu_do_khoi_dong_giay": khoi_dong(),
        "tu_do_mo_van_ban_giay": mo_ung_dung(["libreoffice", "--writer", "--norestore"], "LibreOffice Writer"),
        "tu_do_mo_trinh_duyet_giay": mo_ung_dung(["firefox", "--new-window", "about:blank"], "Mozilla Firefox"),
        "da_bat_phut": da_bat, "ghi_chu": "; ".join(ghi_chu),
    }
    moi = not os.path.exists(a.csv)
    os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
    with open(a.csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COT)
        if moi:
            w.writeheader()
        w.writerow(dong)
    for k in COT:
        print(f"{k:>20}: {dong[k] if dong[k] != '' else '(không đo được)'}")
    print(f"\nĐã ghi vào {a.csv}")


if __name__ == "__main__":
    main()
