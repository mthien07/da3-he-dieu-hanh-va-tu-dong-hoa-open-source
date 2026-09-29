#!/usr/bin/env python3
"""Chấm Trợ lý OneBee: chạy bộ câu hỏi tiếng Việt qua từng model trên Ollama, so với ngưỡng, xuất báo cáo.

Ví dụ (trên OneBee Box, Ollama chạy trong container onebee-ollama):
  python3 tests/ai/cham-diem-model.py --ollama http://<ip-ollama>:11434 \\
      --model gemma3:4b --model gemma4:e2b-it-qat --may "Box HTX (i5-8500, 16GB)" --may-box-that
"""
import argparse
import datetime
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onebee_ai_eval.ollama_client import OllamaClient  # noqa: E402
from onebee_ai_eval.report import summarize, write_csv, write_markdown  # noqa: E402
from onebee_ai_eval.scoring import score_answer  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOI_DAN = os.path.join(REPO, "box/ansible/roles/box-ai/files/tro-ly-onebee-loi-dan.md")
# Tùy chọn sinh chữ GIỐNG "Trợ lý OneBee" trên Box (box-ai/files/onebee-webui.py) để chấm đúng cấu hình thật
TUY_CHON_MODEL = {"temperature": 0.3}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="append", required=True, help="tên model Ollama (lặp lại để chấm nhiều model)")
    ap.add_argument("--ollama", default="http://127.0.0.1:11434")
    ap.add_argument("--bo-cau-hoi", default=os.path.join(os.path.dirname(__file__), "bo-cau-hoi-tieng-viet.yaml"))
    ap.add_argument("--loi-dan", default=LOI_DAN, help="file lời dặn hệ thống của Trợ lý")
    ap.add_argument("--so-lan", type=int, help="số lần chạy mỗi câu (mặc định theo ngưỡng trong bộ câu hỏi)")
    ap.add_argument("--nhom", type=int, action="append", help="chỉ chấm các nhóm này")
    ap.add_argument("--may", default=os.uname().nodename, help="mô tả máy chạy (ghi vào báo cáo)")
    ap.add_argument("--may-box-that", action="store_true", help="đang chạy trên máy Box thật → xét cả ngưỡng tốc độ")
    ap.add_argument("--khong-tai", action="store_true", help="không tự tải model")
    ap.add_argument("--ra", default=os.path.join(REPO, "reports/ai"), help="thư mục xuất báo cáo")
    a = ap.parse_args()

    with open(a.bo_cau_hoi, encoding="utf-8") as f:
        bo = yaml.safe_load(f)
    with open(a.loi_dan, encoding="utf-8") as f:
        loi_dan = f.read()
    nguong, ten_nhom = bo["nguong"], {int(k): v for k, v in bo["nhom"].items()}
    cau_hoi = [q for q in bo["cau_hoi"] if not a.nhom or q["nhom"] in a.nhom]
    so_lan = a.so_lan or nguong["so_lan_chay"]
    client = OllamaClient(a.ollama)

    results, all_rows = {}, []
    for model in a.model:
        if not a.khong_tai:
            print(f"== Tải {model} (nếu chưa có)...", flush=True)
            client.pull(model)
        rows = []
        for q in cau_hoi:
            for lan in range(1, so_lan + 1):
                try:
                    r = client.chat(model, loi_dan, q["hoi"], options=TUY_CHON_MODEL)
                except Exception as e:  # lỗi 1 câu (Ollama quá tải, hết giờ...) không làm hỏng cả lượt chấm
                    r = {"tra_loi": f"LỖI GỌI MODEL: {e}", "cho_chu_dau_giay": 0.0, "token_moi_giay": 0.0, "tong_giay": 0.0}
                row = {"model": model, "id": q["id"], "nhom": q["nhom"], "lan": lan, "hoi": q["hoi"], **r,
                       **score_answer(q, r["tra_loi"])}
                rows.append(row)
                mark = "✓" if not row["y_thieu"] and not row["cam_pham"] else "✗"
                print(f"   {mark} {model} {q['id']} lần {lan}: {row['y_dat']}/{row['y_tong']} ý, "
                      f"{r['cho_chu_dau_giay']}s, {r['token_moi_giay']} tok/s", flush=True)
        size = client.loaded_size_gb(model)
        s, loi = summarize(rows, nguong, ten_nhom, a.may_box_that)
        results[model] = (s, loi, size, rows)
        all_rows += rows
        print(f"== {model}: {'ĐẠT' if not loi else 'KHÔNG ĐẠT: ' + '; '.join(loi)}", flush=True)

    os.makedirs(a.ra, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%y%m%d-%H%M")
    base = os.path.join(a.ra, f"{stamp}-cham-tro-ly")
    meta = {"ngay": datetime.date.today().strftime("%d/%m/%Y"), "may": a.may, "may_box_that": a.may_box_that,
            "so_cau": len(cau_hoi), "so_lan": so_lan, "ten_nhom": {g: ten_nhom[g] for g in {q['nhom'] for q in cau_hoi}},
            "loi_dan": os.path.relpath(a.loi_dan, REPO)}
    write_markdown(base + ".md", results, meta)
    write_csv(base + "-tra-loi.csv", all_rows, base + "-phieu-cham-tay.csv")
    print(f"Báo cáo: {base}.md")
    return 0 if all(not r[1] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
