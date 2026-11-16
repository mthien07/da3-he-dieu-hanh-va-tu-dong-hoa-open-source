#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử dịch vụ Trợ lý AI (box-ai/files/onebee-ai-rag.py): phân đoạn tri thức, dựng lời nhắc có trích nguồn và dòng nhắc kiểm tra,
sinh câu lệnh nạp tri thức không trùng, kho khóa API, và máy chủ HTTP chạy THẬT trên cổng tạm với Ollama và cầu nối danh tính giả
(ghi lại mọi yêu cầu nhận được). Dịch vụ đứng sau Caddy forward_auth: chỉ tin Remote-User/Remote-Groups, hoặc khóa API do onebee-box cấp.
Chạy: python3 -m unittest tests/box/test_onebee_ai_rag.py"""
import http.client
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import time
import threading
import unittest
from contextlib import redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
AI_FILES = os.path.join(ROOT, "box/ansible/roles/box-ai/files")
spec = importlib.util.spec_from_file_location("onebee_ai_rag", os.path.join(AI_FILES, "onebee-ai-rag.py"))
rag = importlib.util.module_from_spec(spec)
sys.modules["onebee_ai_rag"] = rag
spec.loader.exec_module(rag)

VECTOR = [0.25, -0.5, 0.125]


class MayChuGia(ThreadingHTTPServer):
    """Máy chủ HTTP giả: ghi lại yêu cầu, trả lời theo hàm tra_loi(yeu_cau) -> (mã, đối tượng JSON)."""
    daemon_threads = True

    def __init__(self, tra_loi):
        self.nhan = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def xu_ly(self):
                n = int(self.headers.get("Content-Length") or 0)
                than = self.rfile.read(n) if n else b""
                yc = {"method": self.command, "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                      "body": json.loads(than) if than else None}
                outer.nhan.append(yc)
                ma, dl = outer.tra_loi_ham(yc)
                tl = json.dumps(dl).encode()
                self.send_response(ma)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(tl)))
                self.end_headers()
                self.wfile.write(tl)

            do_GET = do_POST = xu_ly

        self.tra_loi_ham = tra_loi
        super().__init__(("127.0.0.1", 0), H)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"

    def dong(self):
        self.shutdown()
        self.server_close()


def ollama_gia(loi=False):
    def tra(yc):
        if loi:
            return 500, {"error": "hỏng"}
        if yc["path"] == "/api/embed":
            return 200, {"embeddings": [VECTOR for _ in yc["body"]["input"]]}
        if yc["path"] == "/api/chat":
            return 200, {"message": {"role": "assistant", "content": "Câu trả lời thử."}}
        return 404, {}
    return MayChuGia(tra)


def cau_noi_gia(tri_thuc=None, ma_tim=200):
    tri_thuc = tri_thuc if tri_thuc is not None else [
        {"nguon": "tri-thuc/nghi-dinh-30-2020-nd-cp.md", "tieu_de": "Thể thức văn bản", "noi_dung": "Quốc hiệu và tiêu ngữ.", "khoang_cach": 0.2}]

    def tra(yc):
        if yc["path"] == "/api/rpc/tim_tri_thuc":
            return ma_tim, (tri_thuc if ma_tim == 200 else {"message": "lỗi"})
        if yc["path"] == "/api/lich_su_hoi_ai":
            return 201, {}
        return 404, {}
    return MayChuGia(tra)


def goi(may_chu, duong_dan, than=None, tieu_de=None, phuong_thuc="POST", tho=None):
    c = http.client.HTTPConnection("127.0.0.1", may_chu.server_address[1], timeout=20)
    td = {"Content-Type": "application/json"}
    td.update(tieu_de or {})
    if tho is not None:
        body = tho.encode("utf-8") if isinstance(tho, str) else tho
    elif than is not None:
        body = json.dumps(than, ensure_ascii=False).encode("utf-8")
    else:
        body = None
    c.request(phuong_thuc, duong_dan, body=body, headers=td)
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, (json.loads(raw) if raw else None)


class TestPhanDoan(unittest.TestCase):
    def test_tach_theo_tieu_de_va_giu_tieu_de(self):
        ds = rag.phan_doan("# Văn bản\nMở đầu.\n\n## I. Thể thức\nNội dung một.\n\n## II. Ký\nNội dung hai.\n")
        self.assertEqual([d["tieu_de"] for d in ds], ["Văn bản", "I. Thể thức", "II. Ký"])
        self.assertEqual(ds[1]["noi_dung"], "Nội dung một.")

    def test_muc_dai_duoc_tach_theo_doan_van_khong_mat_chu(self):
        doan = ["Câu số %d của đoạn văn khá dài để chiếm chỗ. " % i * 4 for i in range(12)]
        ds = rag.phan_doan("## Mục dài\n" + "\n\n".join(doan), toi_da=500)
        self.assertGreater(len(ds), 3)
        self.assertTrue(all(len(d["noi_dung"]) <= 500 for d in ds))
        self.assertTrue(all(d["tieu_de"] == "Mục dài" for d in ds))
        gop = " ".join(d["noi_dung"] for d in ds)
        for i in range(12):
            self.assertIn("Câu số %d của" % i, gop)

    def test_mot_doan_qua_dai_van_bi_cat(self):
        ds = rag.phan_doan("## Một khối\n" + "chữ " * 600, toi_da=300)
        self.assertTrue(len(ds) >= 8 and all(len(d["noi_dung"]) <= 300 for d in ds))

    def test_van_ban_rong_khong_co_doan(self):
        self.assertEqual(rag.phan_doan(" \n\n"), [])
        self.assertEqual(rag.phan_doan("## Chỉ có tiêu đề\n"), [])


class TestDocNguon(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        for ten, nd in (("tri-thuc", {"a.md": "# A\n## M1\nNội dung 1.\n## M2\nNội dung 2.\n"}),
                        ("mau", {"mau.json": json.dumps({"command": "/to-trinh", "title": "Mẫu tờ trình", "content": "Soạn [loại]."})}),
                        ("don-vi", {"b.md": "Ghi chú đơn vị.\n", "bo-qua.txt": "x"})):
            os.makedirs(f"{self.t}/{ten}")
            for f, nd in nd.items():
                open(f"{self.t}/{ten}/{f}", "w", encoding="utf-8").write(nd)
        self.ds = [("tri-thuc", f"{self.t}/tri-thuc"), ("mau-soan-thao", f"{self.t}/mau"), ("don-vi", f"{self.t}/don-vi"),
                   ("khong-co", f"{self.t}/khong-co")]

    def test_doc_md_va_mau_json_voi_khoa_on_dinh(self):
        ds = rag.doc_nguon(self.ds)
        khoa = [(d["nguon"], d["doan"]) for d in ds]
        self.assertEqual(khoa, [("tri-thuc/a.md", 0), ("tri-thuc/a.md", 1), ("mau-soan-thao/mau.json", 0), ("don-vi/b.md", 0)])
        mau = ds[2]
        self.assertEqual((mau["tieu_de"], mau["noi_dung"]), ("Mẫu tờ trình", "Soạn [loại]."))
        self.assertTrue(all(len(d["sha256"]) == 64 for d in ds))
        self.assertEqual([d["sha256"] for d in ds], [d["sha256"] for d in rag.doc_nguon(self.ds)])

    def test_noi_dung_doi_thi_ma_bam_doi(self):
        truoc = rag.doc_nguon(self.ds)[0]["sha256"]
        open(f"{self.t}/tri-thuc/a.md", "w", encoding="utf-8").write("# A\n## M1\nNội dung 1 đã sửa.\n")
        self.assertNotEqual(truoc, rag.doc_nguon(self.ds)[0]["sha256"])


class TestLoiNhac(unittest.TestCase):
    LOI_DAN = "Bạn là Trợ lý. Hôm nay là {{CURRENT_DATE}}, {{CURRENT_WEEKDAY}}."
    DOAN = [{"nguon": "tri-thuc/nd30.md", "tieu_de": "Thể thức", "noi_dung": "Quốc hiệu và tiêu ngữ."},
            {"nguon": "mau-soan-thao/to-trinh.json", "tieu_de": "Mẫu tờ trình", "noi_dung": "Soạn [loại]."}]

    def test_co_trich_nguon_danh_so_va_dong_nhac_kiem_tra(self):
        tn = rag.dung_tin_nhan(self.LOI_DAN, "Quốc hiệu viết thế nào?", self.DOAN, rag.datetime.datetime(2026, 11, 16, 9, 0))
        self.assertEqual([m["role"] for m in tn], ["system", "user"])
        he_thong = tn[0]["content"]
        self.assertIn("2026-11-16", he_thong)
        self.assertIn("Thứ Hai", he_thong)
        self.assertNotIn("{{", he_thong)
        for chuoi in ("[1] Thể thức (tri-thuc/nd30.md)", "Quốc hiệu và tiêu ngữ.", "[2] Mẫu tờ trình (mau-soan-thao/to-trinh.json)"):
            self.assertIn(chuoi, he_thong)
        self.assertIn("trích nguồn", he_thong.lower())
        self.assertIn("kiểm tra lại", he_thong.lower())
        self.assertEqual(tn[1]["content"], "Quốc hiệu viết thế nào?")

    def test_khong_co_tai_lieu_thi_khong_co_khoi_tham_khao(self):
        tn = rag.dung_tin_nhan(self.LOI_DAN, "Xin chào", [], rag.datetime.datetime(2026, 11, 16))
        self.assertNotIn("TÀI LIỆU THAM KHẢO", tn[0]["content"])
        self.assertNotIn("[1]", tn[0]["content"])

    def test_dong_nhac_kiem_tra_them_dung_mot_lan(self):
        mot = rag.them_nhac_kiem_tra("Trả lời.")
        self.assertTrue(mot.startswith("Trả lời.\n\n") and mot.endswith(rag.NHAC_KIEM_TRA))
        self.assertEqual(rag.them_nhac_kiem_tra(mot), mot)


class TestSqlNap(unittest.TestCase):
    def test_nap_khong_trung_va_thoat_ky_tu(self):
        ds = [{"nguon": "tri-thuc/a.md", "doan": 0, "tieu_de": "Điều 'một'", "noi_dung": "Dòng\n\\n :x 'trích'", "sha256": "a" * 64}]
        sql = rag.sql_nap(ds, [VECTOR], "mo-hinh:1")
        self.assertIn("ON CONFLICT (nguon, doan) DO UPDATE", sql)
        self.assertIn("IS DISTINCT FROM", sql)
        self.assertIn("DELETE FROM onebee.tai_lieu_tri_thuc", sql)
        self.assertIn("'[0.25,-0.5,0.125]'", sql)
        self.assertIn("Điều ''một''", sql)
        self.assertIn("''trích''", sql)
        self.assertNotIn("\0", sql)

    def test_so_vector_khac_so_doan_la_loi(self):
        with self.assertRaises(ValueError):
            rag.sql_nap([{"nguon": "a", "doan": 0, "tieu_de": "t", "noi_dung": "n", "sha256": "a" * 64}], [], "m")


class TestKhoaHoi(unittest.TestCase):
    def setUp(self):
        self.tep = os.path.join(tempfile.mkdtemp(), "khoa-hoi.json")

    def test_cap_khoa_luu_ma_bam_khong_luu_khoa(self):
        khoa = rag.cap_khoa(self.tep, "nguoi", "an")
        self.assertRegex(khoa, r"^obk-[0-9a-f]{48}$")
        self.assertNotIn(khoa, open(self.tep, encoding="utf-8").read())
        self.assertEqual(rag.tra_khoa(self.tep, khoa), {"loai": "nguoi", "chu": "an"})
        self.assertEqual(stat.S_IMODE(os.stat(self.tep).st_mode), 0o644)

    def test_cap_lai_thi_khoa_cu_het_hieu_luc(self):
        cu = rag.cap_khoa(self.tep, "nguoi", "an")
        moi = rag.cap_khoa(self.tep, "nguoi", "an")
        self.assertNotEqual(cu, moi)
        self.assertIsNone(rag.tra_khoa(self.tep, cu))
        self.assertIsNotNone(rag.tra_khoa(self.tep, moi))

    def test_khoa_nguoi_va_khoa_may_cung_ten_la_hai_khoa_khac_nhau(self):
        k1, k2 = rag.cap_khoa(self.tep, "nguoi", "an"), rag.cap_khoa(self.tep, "may", "an")
        self.assertEqual(rag.tra_khoa(self.tep, k1)["loai"], "nguoi")
        self.assertEqual(rag.tra_khoa(self.tep, k2)["loai"], "may")

    def test_go_khoa(self):
        khoa = rag.cap_khoa(self.tep, "may", "ketoan-01")
        self.assertTrue(rag.go_khoa(self.tep, "may", "ketoan-01"))
        self.assertIsNone(rag.tra_khoa(self.tep, khoa))
        self.assertFalse(rag.go_khoa(self.tep, "may", "ketoan-01"))

    def test_khoa_sai_dang_hoac_chua_co_tep(self):
        self.assertIsNone(rag.tra_khoa(self.tep, "obk-" + "0" * 48))
        for sai in ("", "abc", "obk-xyz", "obk-" + "0" * 47, "x" * 5000, None):
            self.assertIsNone(rag.tra_khoa(self.tep, sai))

    def test_ten_chu_khong_hop_le(self):
        for sai in ("An", "a b", "", "-a", "a" * 33, "../x"):
            with self.assertRaises(ValueError):
                rag.cap_khoa(self.tep, "nguoi", sai)
        with self.assertRaises(ValueError):
            rag.cap_khoa(self.tep, "la", "an")

    def test_tep_hong_khong_nhan_khoa_nao(self):
        open(self.tep, "w").write("{hỏng")
        self.assertIsNone(rag.tra_khoa(self.tep, "obk-" + "0" * 48))


class TestMayChu(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.loi_dan = os.path.join(self.t, "loi-dan.md")
        open(self.loi_dan, "w", encoding="utf-8").write(TestLoiNhac.LOI_DAN)
        self.ollama = ollama_gia()
        self.cau_noi = cau_noi_gia()
        self.cau_hinh = {"ollama_url": self.ollama.url, "cau_noi_url": self.cau_noi.url, "mo_hinh": "gemma-thu",
                         "mo_hinh_nhung": "nhung-thu", "du_lieu": self.t, "loi_dan": self.loi_dan, "so_nguon": 3}
        self.may = rag.tao_may_chu(self.cau_hinh, ("127.0.0.1", 0))
        threading.Thread(target=self.may.serve_forever, daemon=True).start()
        self.nhat_ky = io.StringIO()
        self.addCleanup(self.don)

    def don(self):
        self.may.shutdown()
        self.may.server_close()
        self.ollama.dong()
        self.cau_noi.dong()

    def phien(self, nguoi="an", nhom="nhan_vien"):
        return {"Remote-User": nguoi, "Remote-Groups": nhom}

    def test_thieu_remote_user_bi_tu_choi_va_khong_goi_ai(self):
        for td in ({}, {"Remote-User": "an"}, {"Remote-Groups": "nhan_vien"}, {"Remote-User": "An Hoa", "Remote-Groups": "nhan_vien"},
                   {"Remote-User": "an", "Remote-Groups": ""}, {"Authorization": "Bearer abc", "Cookie": "authelia_session=x"}):
            ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, td)
            self.assertEqual(ma, 401, td)
            self.assertIn("loi", dl)
        self.assertEqual(self.ollama.nhan, [])
        self.assertEqual(self.cau_noi.nhan, [])

    def test_khoa_sai_bi_tu_choi_khoa_dung_duoc_nhan(self):
        khoa = rag.cap_khoa(os.path.join(self.t, "khoa-hoi.json"), "nguoi", "binh")
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": "x"}, {"X-OneBee-Khoa": "obk-" + "1" * 48})
        self.assertEqual(ma, 401)
        ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": ""}, {"X-OneBee-Khoa": khoa})
        self.assertEqual((ma, dl["loi"]), (400, "Thiếu câu hỏi"))   # xác thực xong mới kiểm thân: dùng để kiểm khóa mà không gọi AI
        self.assertEqual(self.ollama.nhan, [])

    def test_hoi_dap_co_trich_nguon_luu_lich_su_va_nhac_kiem_tra(self):
        ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": "Quốc hiệu viết thế nào?"}, self.phien("an", "nhan_vien,ky_thuat"))
        self.assertEqual(ma, 200)
        self.assertTrue(dl["tra_loi"].startswith("Câu trả lời thử."))
        self.assertTrue(dl["tra_loi"].endswith(rag.NHAC_KIEM_TRA))
        self.assertEqual(dl["nguon"], [{"nguon": "tri-thuc/nghi-dinh-30-2020-nd-cp.md", "tieu_de": "Thể thức văn bản"}])
        embed = [y for y in self.ollama.nhan if y["path"] == "/api/embed"][0]
        self.assertEqual(embed["body"]["model"], "nhung-thu")
        chat = [y for y in self.ollama.nhan if y["path"] == "/api/chat"][0]["body"]
        self.assertEqual((chat["model"], chat["stream"]), ("gemma-thu", False))
        self.assertIn("[1] Thể thức văn bản (tri-thuc/nghi-dinh-30-2020-nd-cp.md)", chat["messages"][0]["content"])
        tim = [y for y in self.cau_noi.nhan if y["path"] == "/api/rpc/tim_tri_thuc"][0]
        self.assertEqual(tim["headers"]["remote-user"], "an")
        self.assertEqual(tim["headers"]["remote-groups"], "nhan_vien,ky_thuat")
        self.assertEqual(tim["body"], {"truy_van": "[0.25,-0.5,0.125]", "so_luong": 3})
        ls = [y for y in self.cau_noi.nhan if y["path"] == "/api/lich_su_hoi_ai"][0]
        self.assertEqual(ls["body"]["cau_hoi"], "Quốc hiệu viết thế nào?")
        self.assertTrue(ls["body"]["tra_loi"].startswith("Câu trả lời thử."))
        self.assertEqual(ls["headers"]["remote-user"], "an")

    def test_khong_chuyen_tiep_cookie_va_authorization(self):
        td = dict(self.phien(), Cookie="authelia_session=bimat", Authorization="Bearer bimat")
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, td)
        self.assertEqual(ma, 200)
        for y in self.ollama.nhan + self.cau_noi.nhan:
            self.assertNotIn("cookie", y["headers"])
            self.assertNotIn("authorization", y["headers"])

    def test_khoa_nguoi_dung_vao_cau_noi_voi_ten_chu_khoa_va_chi_quyen_nhan_vien(self):
        khoa = rag.cap_khoa(os.path.join(self.t, "khoa-hoi.json"), "nguoi", "binh")
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, {"X-OneBee-Khoa": khoa})
        self.assertEqual(ma, 200)
        for y in self.cau_noi.nhan:
            self.assertEqual((y["headers"]["remote-user"], y["headers"]["remote-groups"]), ("binh", "nhan_vien"))
            self.assertNotIn("x-onebee-khoa", y["headers"])
        for y in self.ollama.nhan:
            self.assertNotIn("x-onebee-khoa", y["headers"])

    def test_khoa_may_dung_danh_tinh_may_chung(self):
        khoa = rag.cap_khoa(os.path.join(self.t, "khoa-hoi.json"), "may", "ketoan-01-rat-dai-toi-da-32-kt")
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, {"X-OneBee-Khoa": khoa})
        self.assertEqual(ma, 200)
        self.assertEqual({y["headers"]["remote-user"] for y in self.cau_noi.nhan}, {"may"})

    def test_remote_user_thang_khoa_khi_co_ca_hai(self):
        khoa = rag.cap_khoa(os.path.join(self.t, "khoa-hoi.json"), "nguoi", "binh")
        goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, dict(self.phien("an"), **{"X-OneBee-Khoa": khoa}))
        self.assertEqual({y["headers"]["remote-user"] for y in self.cau_noi.nhan}, {"an"})

    def test_tom_tat_khong_ghi_ten_nguoi_vao_loi_nhac_va_khong_luu_lich_su(self):
        ma, dl = goi(self.may, "/ai/tom-tat", {"noi_dung": "Tuần này: 12 đơn, doanh thu 34 triệu."}, self.phien("nguyen-van-a"))
        self.assertEqual(ma, 200)
        self.assertTrue(dl["tom_tat"].endswith(rag.NHAC_KIEM_TRA))
        chat = [y for y in self.ollama.nhan if y["path"] == "/api/chat"]
        self.assertEqual(len(chat), 1)
        self.assertNotIn("nguyen-van-a", json.dumps(chat[0]["body"], ensure_ascii=False))
        self.assertIn("12 đơn, doanh thu 34 triệu", chat[0]["body"]["messages"][-1]["content"])
        self.assertEqual(self.cau_noi.nhan, [])   # không tra tri thức, không ghi lịch sử

    def test_tom_tat_thieu_noi_dung(self):
        ma, dl = goi(self.may, "/ai/tom-tat", {"noi_dung": "  "}, self.phien())
        self.assertEqual((ma, dl["loi"]), (400, "Thiếu nội dung cần tóm tắt"))

    def test_duong_dan_khac_va_phuong_thuc_khac_bi_chan(self):
        for p in ("/ai/api/chat", "/ai/api/tags", "/ai/", "/hoi", "/api/chat/completions"):
            ma, _ = goi(self.may, p, {"cau_hoi": "x"}, self.phien())
            self.assertEqual(ma, 404, p)
        ma, _ = goi(self.may, "/ai/hoi", phuong_thuc="GET", tieu_de=self.phien())
        self.assertEqual(ma, 404)
        self.assertEqual(self.ollama.nhan, [])

    def test_than_khong_hop_le(self):
        ma, _ = goi(self.may, "/ai/hoi", tho="{không phải json", tieu_de=self.phien())
        self.assertEqual(ma, 400)
        ma, _ = goi(self.may, "/ai/hoi", tho="[1, 2]", tieu_de=self.phien())
        self.assertEqual(ma, 400)
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": 5}, self.phien())
        self.assertEqual(ma, 400)
        ma, _ = goi(self.may, "/ai/hoi", {"cau_hoi": "x" * (rag.TOI_DA_THAN + 10)}, self.phien())
        self.assertEqual(ma, 413)
        self.assertEqual(self.ollama.nhan, [])

    def test_ollama_hong_thi_bao_503_de_hieu(self):
        self.ollama.tra_loi_ham = lambda yc: (500, {"error": "hỏng"})
        ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, self.phien())
        self.assertEqual(ma, 503)
        self.assertIn("Ollama", dl["loi"])

    def test_tra_cuu_tri_thuc_hong_van_tra_loi_duoc_khong_nguon(self):
        self.cau_noi.tra_loi_ham = cau_noi_gia(ma_tim=500).tra_loi_ham
        ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, self.phien())
        self.assertEqual(ma, 200)
        self.assertEqual(dl["nguon"], [])
        chat = [y for y in self.ollama.nhan if y["path"] == "/api/chat"][0]["body"]
        self.assertNotIn("TÀI LIỆU THAM KHẢO", chat["messages"][0]["content"])

    def test_chua_co_mo_hinh_nhung_van_tra_loi_duoc(self):
        goc = self.ollama.tra_loi_ham
        self.ollama.tra_loi_ham = lambda yc: (404, {"error": "chưa có mô hình"}) if yc["path"] == "/api/embed" else goc(yc)
        ma, dl = goi(self.may, "/ai/hoi", {"cau_hoi": "Xin chào"}, self.phien())
        self.assertEqual((ma, dl["nguon"]), (200, []))

    def test_chi_nhat_ky_ten_va_duong_dan_khong_co_noi_dung(self):
        with redirect_stderr(self.nhat_ky):
            goi(self.may, "/ai/hoi", {"cau_hoi": "Bí mật của tôi"}, self.phien("an"))
            # Máy chủ ghi nhật ký sau khi trả lời; chờ dòng nhật ký thay vì đọc ngay (máy nhanh/chậm khác nhau)
            for _ in range(200):
                if "an POST /ai/hoi 200" in self.nhat_ky.getvalue():
                    break
                time.sleep(0.01)
        dong = self.nhat_ky.getvalue()
        self.assertIn("an POST /ai/hoi 200", dong)
        self.assertNotIn("Bí mật của tôi", dong)

    def test_suc_khoe_khong_can_dang_nhap(self):
        ma, dl = goi(self.may, "/suc-khoe", phuong_thuc="GET")
        self.assertEqual(ma, 200)


class TestNapTriThucDongLenh(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        os.makedirs(f"{self.t}/tri-thuc")
        open(f"{self.t}/tri-thuc/a.md", "w", encoding="utf-8").write("# A\n## M1\nNội dung 1.\n")
        self.ollama = ollama_gia()
        self.addCleanup(self.ollama.dong)
        self.env = {"AI_OLLAMA_URL": self.ollama.url, "AI_MO_HINH_NHUNG": "nhung-thu", "AI_TRI_THUC": f"{self.t}/tri-thuc",
                    "AI_MAU": f"{self.t}/khong-co", "AI_TRI_THUC_DON_VI": f"{self.t}/khong-co"}

    def chay(self, *argv):
        cu = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    ma = rag.main(list(argv))
                except SystemExit as e:
                    ma = e.code if isinstance(e.code, int) else 1
                    err.write(str(e.code) if not isinstance(e.code, int) else "")
            return ma, out.getvalue(), err.getvalue()
        finally:
            for k, v in cu.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_in_sql_nap_voi_vector_tu_ollama(self):
        ma, out, _ = self.chay("nap-tri-thuc")
        self.assertEqual(ma, 0)
        self.assertIn("'tri-thuc/a.md'", out)
        self.assertIn("'[0.25,-0.5,0.125]'", out)
        self.assertIn("'nhung-thu'", out)

    def test_khong_co_tai_lieu_nguon_thi_loi_khong_in_sql_xoa_sach(self):
        self.env["AI_TRI_THUC"] = f"{self.t}/khong-co"
        ma, out, err = self.chay("nap-tri-thuc")
        self.assertNotEqual(ma, 0)
        self.assertEqual(out, "")
        self.assertIn("Không có tài liệu", err)

    def test_chua_co_mo_hinh_nhung_thi_ma_loi_3_de_bo_cai_canh_bao(self):
        self.ollama.tra_loi_ham = lambda yc: (404, {"error": "chưa có mô hình"})
        ma, out, err = self.chay("nap-tri-thuc")
        self.assertEqual(ma, 3)
        self.assertEqual(out, "")
        self.assertIn("mô hình nhúng", err)

    def test_khoa_cap_va_go_qua_dong_lenh(self):
        self.env["AI_DU_LIEU"] = self.t
        ma, out, _ = self.chay("khoa", "cap", "nguoi", "an")
        self.assertEqual(ma, 0)
        khoa = out.strip()
        self.assertRegex(khoa, r"^obk-[0-9a-f]{48}$")
        ma, out, _ = self.chay("khoa", "ds")
        self.assertIn("nguoi an", out)
        self.assertNotIn(khoa, out)
        ma, _, _ = self.chay("khoa", "go", "nguoi", "an")
        self.assertEqual(ma, 0)
        ma, _, _ = self.chay("khoa", "go", "nguoi", "an")
        self.assertEqual(ma, 1)   # không có khóa để gỡ
        ma, _, err = self.chay("khoa", "cap", "nguoi", "An Hoa")
        self.assertNotEqual(ma, 0)


if __name__ == "__main__":
    unittest.main()
