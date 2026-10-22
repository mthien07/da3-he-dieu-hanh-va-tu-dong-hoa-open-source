#!/usr/bin/env python3
"""Số liệu tình trạng Box cho trang chủ (ô "Tình trạng hệ thống"): CPU, RAM, ổ dữ liệu còn trống, Trợ lý AI / thư mục chung / sao lưu.
Ghi 1 tệp JSON tĩnh trong thư mục trang chủ để Caddy phục vụ (không mở thêm cổng hay API nào). Chỉ số phần trăm và trạng thái —
không có tên máy, IP, tên người dùng. Lịch onebee-trang-thai-web.timer chạy mỗi phút.
Cách dùng: onebee-trang-thai-web.py <tệp-json-ra> <thư-mục-dữ-liệu> <tệp-kết-quả-sao-lưu-lần-cuối>"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

PROC = os.environ.get("ONEBEE_PROC", "/proc")
CPU_CHO = float(os.environ.get("ONEBEE_CPU_CHO", "1"))   # giây giữa 2 lần đọc /proc/stat
SAO_LUU_QUA_HAN = 2 * 86400                                # sao lưu hằng đêm: quá 2 ngày chưa có bản mới là có chuyện


def phan_tram_cpu(truoc, sau):
    """% CPU bận giữa 2 dòng "cpu ..." của /proc/stat (idle + iowait là rảnh)."""
    a = [int(x) for x in truoc.split()[1:]]
    b = [int(x) for x in sau.split()[1:]]
    tong = sum(b) - sum(a)
    ranh = (b[3] + b[4]) - (a[3] + a[4])
    return round(100 * (tong - ranh) / tong) if tong > 0 else 0


def doc_cpu():
    def dong():
        with open(os.path.join(PROC, "stat"), encoding="ascii") as f:
            return f.readline()
    truoc = dong()
    time.sleep(CPU_CHO)
    return phan_tram_cpu(truoc, dong())


def phan_tram_ram(meminfo):
    v = {k: int(r.split()[0]) for k, _, r in (d.partition(":") for d in meminfo.splitlines()) if r.strip()}
    return round(100 * (v["MemTotal"] - v["MemAvailable"]) / v["MemTotal"])


def o_dia(thu_muc):
    d = shutil.disk_usage(thu_muc)
    return {"con_trong_gb": round(d.free / 1e9, 1), "da_dung_phan_tram": round(100 * d.used / d.total)}


def container_chay(*ten):
    """True khi mọi container đều đang chạy; không có docker / container thì False."""
    try:
        r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", *ten], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and r.stdout.split() == ["true"] * len(ten)


def dich_vu_chay(ten):
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", ten], timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def sao_luu(tep, bay_gio):
    """Kết quả lần sao lưu Box cuối (onebee-box sao-luu ghi "DAT|LOI <giây epoch>"): tot | qua_han | loi | chua_co."""
    try:
        with open(tep, encoding="ascii") as f:
            ket_qua, luc = f.read().split()
        luc = int(luc)
    except FileNotFoundError:
        return "chua_co"
    except (ValueError, UnicodeDecodeError):
        return "loi"
    if ket_qua != "DAT":
        return "loi"
    return "tot" if bay_gio - luc <= SAO_LUU_QUA_HAN else "qua_han"


def ghi_nguyen_tu(duong_dan, du_lieu):
    """Ghi tệp tạm cùng thư mục rồi đổi tên: Caddy không bao giờ đọc phải tệp ghi dở."""
    fd, tam = tempfile.mkstemp(dir=os.path.dirname(duong_dan), prefix=".trang-thai-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(du_lieu, f, ensure_ascii=False)
        os.chmod(tam, 0o644)
        os.replace(tam, duong_dan)
    except BaseException:
        os.unlink(tam)
        raise


def main(argv):
    if len(argv) != 4:
        sys.exit(__doc__.rsplit("Cách dùng: ", 1)[1])
    ra, du_lieu, tep_sao_luu = argv[1:]
    with open(os.path.join(PROC, "meminfo"), encoding="ascii") as f:
        ram = phan_tram_ram(f.read())
    ghi_nguyen_tu(ra, {
        "cap_nhat": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "cpu_phan_tram": doc_cpu(),
        "ram_phan_tram": ram,
        "o_dia": o_dia(du_lieu),
        "dich_vu": {
            # Trợ lý dùng được khi cả giao diện (Open WebUI) lẫn bộ chạy model (Ollama) đều chạy
            "tro_ly_ai": "chay" if container_chay("onebee-open-webui", "onebee-ollama") else "dung",
            "thu_muc_chung": "chay" if dich_vu_chay("smbd") else "dung",
            "sao_luu": sao_luu(tep_sao_luu, time.time()),
        },
    })


if __name__ == "__main__":
    main(sys.argv)
