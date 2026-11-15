#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm thử dịch vụ Trợ lý AI & RAG nội bộ (onebee-ai-rag.py): kho tri thức RAG, 4 mẫu văn bản Nghị định 30 và quản lý khóa API."""
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
AI_RAG_PY = os.path.join(ROOT, "box/ansible/roles/box-ai/files/onebee-ai-rag.py")
PROMPTS_DIR = os.path.join(ROOT, "box/ansible/roles/box-ai/files/prompts")
RAG_DIR = os.path.join(ROOT, "box/ansible/roles/box-ai/files/knowledge")

SPEC = importlib.util.spec_from_file_location("onebee_ai_rag", AI_RAG_PY)
ai_rag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ai_rag)


class TestOneBeeAiRag(unittest.TestCase):
    def test_4_mau_soan_van_ban_nghi_dinh_30(self):
        ds = ai_rag.nap_danh_sach_mau(PROMPTS_DIR)
        self.assertEqual(len(ds), 4)
        ma_set = {m["ma"] for m in ds}
        self.assertEqual(ma_set, {"bao-cao", "bien-ban", "hop-dong", "to-trinh"})
        for m in ds:
            self.assertTrue(m["title"])
            self.assertIn("[", m["content"])

    def test_nap_kho_tri_thuc_va_truy_xuat_rag_tieng_viet(self):
        kho = ai_rag.nap_kho_tri_thuc([RAG_DIR])
        self.assertGreaterEqual(len(kho), 3)
        kq = ai_rag.truy_xuat_rag("Thể thức văn bản hành chính Nghị định 30 quốc hiệu tiêu ngữ", kho, top_k=2)
        self.assertGreaterEqual(len(kq), 1)
        self.assertTrue(any("30" in d["noi_dung"] or "văn bản" in d["noi_dung"].lower() for d in kq))

    def test_quan_ly_khoa_api_may_tram_luy_dang_va_xoay_khoa(self):
        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data")
            sec_dir = os.path.join(d, "secrets")
            lib_dir = os.path.join(ROOT, "box/ansible/roles/box-ai/files")
            os.makedirs(sec_dir)
            ql = ai_rag.QuanLyAiRag(data_dir, sec_dir, lib_dir)
            k1 = ql.cap_khoa("ketoan-01")
            k2 = ql.cap_khoa("ketoan-01")
            self.assertEqual(k1, k2)
            self.assertEqual(ql.xac_thuc_khoa(k1), "may-ketoan-01")
            k3 = ql.cap_khoa("ketoan-01", xoay=True)
            self.assertNotEqual(k1, k3)
            self.assertEqual(ql.xac_thuc_khoa(k3), "may-ketoan-01")
            ql.xoa_tai_khoan("ketoan-01")
            self.assertIsNone(ql.xac_thuc_khoa(k3))


if __name__ == "__main__":
    unittest.main()
