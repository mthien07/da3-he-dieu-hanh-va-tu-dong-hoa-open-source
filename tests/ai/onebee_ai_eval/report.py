"""Tổng hợp kết quả chấm theo ngưỡng anh chốt và xuất báo cáo Markdown + CSV."""
import csv
import statistics


def summarize(rows, nguong, ten_nhom, may_box_that):
    """rows: kết quả từng lần chạy của 1 model. Trả về (tóm tắt, danh sách lỗi so với ngưỡng)."""
    by_group = {}
    for r in rows:
        by_group.setdefault(r["nhom"], []).append(r["y_dat"] / r["y_tong"])
    ty_le_nhom = {g: statistics.mean(v) for g, v in sorted(by_group.items())}
    ty_le_chung = statistics.mean(r["y_dat"] / r["y_tong"] for r in rows)
    bia = sum(1 for r in rows if r["nhom"] == 5 and not r["dat_khong_bia"])
    cam = [r for r in rows if r["cam_pham"]]
    cam_nghiem_ngat = [r for r in cam if r["nhom"] in nguong["y_cam_nhom_nghiem_ngat"]]
    ttft = statistics.median(r["cho_chu_dau_giay"] for r in rows)
    tps = statistics.median(r["token_moi_giay"] for r in rows)
    s = {"ty_le_chung": ty_le_chung, "ty_le_nhom": ty_le_nhom, "bia": bia, "cam": len(cam),
         "cam_ti_le": len(cam) / len(rows), "cam_nghiem_ngat": len(cam_nghiem_ngat),
         "ttft": ttft, "tps": tps, "so_lan": len(rows)}
    loi = []
    if ty_le_chung < nguong["y_bat_buoc_trung_binh"]:
        loi.append(f"Ý bắt buộc chung {ty_le_chung:.0%} < {nguong['y_bat_buoc_trung_binh']:.0%}")
    for g, v in ty_le_nhom.items():
        if v < nguong["y_bat_buoc_moi_nhom"]:
            loi.append(f"Nhóm {g} ({ten_nhom[g]}) {v:.0%} < {nguong['y_bat_buoc_moi_nhom']:.0%}")
    if bia > nguong["nhom_khong_biet_so_lan_bia_toi_da"]:
        loi.append(f"Bịa ở nhóm 5: {bia} lần")
    if cam_nghiem_ngat:
        loi.append(f"Phạm ý cấm ở nhóm {nguong['y_cam_nhom_nghiem_ngat']}: {len(cam_nghiem_ngat)} lần")
    if s["cam_ti_le"] > nguong["y_cam_ti_le_toi_da"]:
        loi.append(f"Tỉ lệ phạm ý cấm {s['cam_ti_le']:.1%} > {nguong['y_cam_ti_le_toi_da']:.0%}")
    if may_box_that:
        if ttft > nguong["cho_chu_dau_toi_da_giay"]:
            loi.append(f"Chờ chữ đầu {ttft:.1f}s > {nguong['cho_chu_dau_toi_da_giay']}s")
        if tps < nguong["token_moi_giay_toi_thieu"]:
            loi.append(f"Tốc độ {tps:.1f} token/s < {nguong['token_moi_giay_toi_thieu']}")
    return s, loi


def write_markdown(path, results, meta):
    """results: {model: (tóm tắt, lỗi, dung lượng GB, rows)}"""
    L = [f"# Chấm Trợ lý OneBee — {meta['ngay']} — máy: {meta['may']}", ""]
    if not meta["may_box_that"]:
        L += ["> **Chạy thử trên máy KHÔNG phải Box thật** — số tốc độ chỉ để tham khảo, không xét ngưỡng tốc độ,",
              "> không dùng cho bảng giá/cấu hình tối thiểu.", ""]
    L += [f"Bộ câu hỏi: {meta['so_cau']} câu × {meta['so_lan']} lần. Lời dặn hệ thống: `{meta['loi_dan']}`.", "",
          "| Model | Kết luận | Ý bắt buộc | " + " | ".join(f"N{g}" for g in sorted(meta['ten_nhom'])) +
          " | Bịa (N5) | Ý cấm | Chờ chữ đầu | Token/s | RAM |",
          "|---|---|---|" + "---|" * len(meta["ten_nhom"]) + "---|---|---|---|---|"]
    for model, (s, loi, size, _rows) in results.items():
        nhom = " | ".join(f"{s['ty_le_nhom'].get(g, 0):.0%}" for g in sorted(meta["ten_nhom"]))
        L.append(f"| `{model}` | {'✅ ĐẠT' if not loi else '❌ KHÔNG ĐẠT'} | {s['ty_le_chung']:.0%} | {nhom} | "
                 f"{s['bia']} | {s['cam']} | {s['ttft']:.1f}s | {s['tps']:.1f} | {size or '?'} GB |")
    L += ["", "Nhóm: " + "; ".join(f"N{g} = {t}" for g, t in sorted(meta["ten_nhom"].items())), ""]
    for model, (s, loi, _size, rows) in results.items():
        L += [f"## `{model}`", ""]
        L += [f"- ❌ {x}" for x in loi] or ["- ✅ Vượt mọi ngưỡng (còn phần chấm tay nhóm 2–3)"]
        sai = [r for r in rows if r["y_thieu"] or r["cam_pham"]]
        if sai:
            L += ["", "Câu chưa đạt (tối đa 15 dòng):", ""]
            for r in sai[:15]:
                L.append(f"- `{r['id']}` lần {r['lan']}: thiếu {r['y_thieu'] or '—'}; phạm cấm {r['cam_pham'] or '—'}")
        L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def write_csv(path, all_rows, hand_scoring_path):
    cols = ["model", "id", "nhom", "lan", "y_dat", "y_tong", "y_thieu", "cam_pham", "cho_chu_dau_giay",
            "token_moi_giay", "tra_loi"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow({**r, "y_thieu": "; ".join(r["y_thieu"]), "cam_pham": "; ".join(r["cam_pham"])})
    # Phiếu chấm tay: nhóm 2 (văn bản hành chính) và 3 (tóm tắt), lần chạy 1 — điểm 1–5
    with open(hand_scoring_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "id", "cau_hoi", "tra_loi", "diem_1_den_5", "ghi_chu"])
        for r in all_rows:
            if r["nhom"] in (2, 3) and r["lan"] == 1:
                w.writerow([r["model"], r["id"], r["hoi"], r["tra_loi"], "", ""])
