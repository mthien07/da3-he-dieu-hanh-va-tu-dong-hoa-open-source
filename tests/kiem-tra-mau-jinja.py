#!/usr/bin/env python3
"""Mọi file mẫu Jinja (*.j2) của Desktop/Box phải đọc được (bắt lỗi kiểu `${#mang[@]}` bị hiểu là chú thích Jinja)."""
import glob
import sys

import jinja2

loi = 0
for f in sorted(glob.glob("*/ansible/**/*.j2", recursive=True)):
    try:
        jinja2.Environment().parse(open(f, encoding="utf-8").read())
    except jinja2.TemplateSyntaxError as e:
        print(f"{f}:{e.lineno}: {e.message}")
        loi += 1
print(f"Đã kiểm {len(glob.glob('*/ansible/**/*.j2', recursive=True))} mẫu, {loi} lỗi")
sys.exit(1 if loi else 0)
