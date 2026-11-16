#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
"""Kiểm tra kho mẫu soạn văn bản và kho tri thức được dịch vụ Trợ lý AI nạp vào CSDL (không cần Docker).

Tệp mẫu và tài liệu phải nằm đúng thư mục role box-ai chép vào container; lệnh quản trị phải nối đúng vào
onebee-ai-rag.py. Phần phân đoạn, nhúng, dựng lời nhắc có trích nguồn kiểm ở tests/box/test_onebee_ai_rag.py.
Chạy: python3 -m unittest"""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
AI_DIR = os.path.join(ROOT, "box/ansible/roles/box-ai")
PROMPTS_DIR = os.path.join(AI_DIR, "files/prompts")
KNOWLEDGE_DIR = os.path.join(AI_DIR, "files/knowledge")
SCRIPT = os.path.join(AI_DIR, "files/onebee-ai-rag.py")
ROLE = os.path.join(AI_DIR, "tasks/main.yml")
BOX_SCRIPT = os.path.join(ROOT, "box/ansible/roles/box-stack/templates/onebee-box.sh.j2")


def doc(*duong_dan):
    with open(os.path.join(*duong_dan), encoding="utf-8") as f:
        return f.read()


class KhoMauVaTriThuc(unittest.TestCase):
    def test_bon_mau_soan_van_ban_dung_cau_truc(self):
        for ten in ("to-trinh.json", "bien-ban.json", "hop-dong.json", "bao-cao.json"):
            with self.subTest(ten=ten):
                d = json.loads(doc(PROMPTS_DIR, ten))
                self.assertTrue(d.get("command", "").startswith("/"))
                self.assertTrue(d.get("title"))
                self.assertTrue(d.get("content") and isinstance(d["content"], str))

    def test_hai_tai_lieu_tri_thuc_goc_co_noi_dung_cot_loi(self):
        nd30 = doc(KNOWLEDGE_DIR, "nghi-dinh-30-2020-nd-cp.md")
        htx = doc(KNOWLEDGE_DIR, "luat-hop-tac-xa-2023.md")
        self.assertIn("Thể thức văn bản hành chính", nd30)
        self.assertIn("Tài sản chung không chia", htx)


class NoiLenhQuanTri(unittest.TestCase):
    def test_dich_vu_co_lenh_nap_tri_thuc_va_hai_duong_hoi_dap(self):
        src = doc(SCRIPT)
        self.assertIn('lenh == "nap-tri-thuc"', src)
        self.assertIn('"/ai/hoi", "/ai/tom-tat"', src)
        self.assertIn("ON CONFLICT (nguon, doan) DO UPDATE", src)

    def test_onebee_box_noi_lenh_nap_tri_thuc_va_cap_khoa(self):
        src = doc(BOX_SCRIPT)
        # Bộ cài gọi lệnh này khi lệnh gọi đang giữ khóa (tat-sso-tam, xoay-khoa --box) → không được lấy khóa lần nữa
        self.assertIn("nap-tri-thuc) cmd_nap_tri_thuc ;;", src)
        self.assertNotIn("nap-tri-thuc) with_lock", src)
        self.assertIn("cap-khoa-hoi) shift; cmd_cap_khoa_hoi \"$@\" ;;", src)
        self.assertIn("go-khoa-hoi) shift; cmd_go_khoa_hoi \"$@\" ;;", src)
        self.assertIn('/app/onebee-ai-rag.py nap-tri-thuc', src)

    def test_role_chep_mau_va_tri_thuc_vao_thu_muc_ma_dich_vu_doc(self):
        src = doc(ROLE)
        self.assertIn("dest: \"{{ onebee_box_dir }}/ai-rag/{{ item.dest }}/\"", src)
        self.assertIn("{src: prompts, dest: prompts}", src)
        self.assertIn("{src: knowledge, dest: knowledge}", src)
        self.assertIn("onebee_box_data }}/knowledge:/du-lieu-tri-thuc:ro", doc(
            ROOT, "box/ansible/roles/box-stack/templates/docker-compose.yml.j2"))

    def test_khong_con_tep_dich_vu_cu(self):
        self.assertFalse(os.path.exists(os.path.join(AI_DIR, "files/onebee-webui.py")))


if __name__ == "__main__":
    unittest.main()
