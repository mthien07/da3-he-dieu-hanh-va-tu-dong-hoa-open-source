---
phase: 1
title: "Giai đoạn 1: Vá điểm PoF — giấy phép và đóng gói"
status: todo
priority: P1
effort: "1.5d"
dependencies: []
---

# Giai đoạn 1: Vá điểm PoF — giấy phép và đóng gói

Nhánh: `chore/giay-phep-tung-tep-va-dong-goi` từ `main`. Không phụ thuộc giai đoạn nào, làm ngay được.

## Mục tiêu
Không còn bị trừ điểm ở tiêu chí 2 (giấy phép trong từng tệp, bản sao toàn văn) và tiêu chí 6 (changelog dễ thấy) của Thể lệ.

## Điều cần biết
- 150 tệp mã được theo dõi (`.sh`, `.py`, `.yml`, `.yaml`, `.j2`, `.js`, `.html` và các lệnh không đuôi như `hoi`, `onebee-*`), 0 tệp có dòng giấy phép.
- Dòng chuẩn: `SPDX-License-Identifier: MIT` và `Copyright (c) 2026 Dương Minh Thiện, HTX OneBee`, viết trong chú thích đúng cú pháp của từng loại tệp.
- Không chèn vào: tệp JSON thuần (không có chú thích), ảnh, PDF, `.asc`, tệp của bên thứ ba, mọi thứ dưới `plans/` và `reports/`.
- Tệp có dòng `#!` thì chèn **sau** dòng đó; tệp YAML bắt đầu bằng `---` thì chèn **sau** dòng `---`; mẫu Jinja dùng chú thích của ngôn ngữ đích (ví dụ `#` cho shell, `<!-- -->` cho HTML) hoặc `{# #}` khi đích là JSON.
- Mẫu JSON của quy trình n8n sẽ bị xóa ở giai đoạn 5: bỏ qua thư mục `box/ansible/roles/box-n8n/templates/workflows/`.
- `tests/desktop/test_onebee_phien_ban.py` và `scripts/dong-goi-ban-phat-hanh.sh` đang đọc `docs/project-changelog.md`.
- Thể lệ trừ 5đ nếu "không có thông báo về mục đích của giấy phép", trừ 5đ nếu "phát hành cùng gói đính kèm của các dự án khác mà nó phụ thuộc vào", và trừ điểm nếu hệ thống ghi nhận lỗi (bug tracker) trên thực tế không được sử dụng.

## Nhiệm vụ

### Nhiệm vụ 1.1 — Test giấy phép từng tệp (phải ĐỎ trước)
- File: tạo `tests/desktop/test_onebee_giay_phep.py`.
- Các bước: test lấy danh sách tệp bằng `git ls-files`, lọc đúng tập nêu ở "Điều cần biết" (danh sách loại trừ ghi thành hằng trong test), và kiểm 5 dòng đầu mỗi tệp có `SPDX-License-Identifier: MIT`. Thêm kiểm: gốc repo có `LICENSE` chứa chữ `MIT License`.
- Kiểm chứng (trạng thái ĐỎ là đúng): `~/.cache/onebee-kiem/bin/python -m unittest tests/desktop/test_onebee_giay_phep.py` thoát mã khác 0.

### Nhiệm vụ 1.2 — Chèn dòng giấy phép vào mọi tệp mã
- File: tạo `scripts/chen-giay-phep.py` (chạy lại nhiều lần không chèn trùng; có `--kiem` chỉ báo tệp thiếu); sửa các tệp mã.
- Các bước: viết script theo quy tắc ở "Điều cần biết"; chạy; xem `git diff --stat`; chạy lại toàn bộ test máy trạm.
- Kiểm chứng (đủ 3 lệnh): test của 1.1 thoát mã 0; `python3 scripts/chen-giay-phep.py --kiem` thoát mã 0; `~/.cache/onebee-kiem/bin/python -m unittest discover -s tests/desktop -p 'test_*.py'` thoát mã 0.

### Nhiệm vụ 1.3 — Gói phát hành có LICENSE; CHANGELOG ở gốc; mục đích giấy phép
- File: `scripts/dong-goi-ban-phat-hanh.sh`, tạo `CHANGELOG.md`, `docs/project-changelog.md`, `tests/desktop/test_onebee_phien_ban.py`, `README.md`, `CONTRIBUTING.md`, `tests/README.md`.
- Các bước:
  1. Thêm `LICENSE CHANGELOG.md CONTRIBUTING.md SECURITY.md` vào danh sách `git archive`. Tuyệt đối không đóng gói mã nguồn, `.deb`, hay Docker image của dự án thứ ba (`scripts/dong-goi-usb-offline.sh` không gắn vào GitHub Release).
  2. `git mv docs/project-changelog.md CHANGELOG.md`; tạo lại `docs/project-changelog.md` chỉ gồm một dòng trỏ tới `../CHANGELOG.md`.
  3. Đổi mọi nơi đọc đường dẫn cũ sang `CHANGELOG.md`: liệt kê bằng `git grep -n "project-changelog" -- . ':!plans'` và sửa từng nơi (script đóng gói, test phiên bản, README, CONTRIBUTING, tests/README).
  4. Trong mục Giấy phép của `README.md`, bổ sung đoạn ngắn nêu rõ **mục đích cấp phép MIT**: cho phép mọi tổ chức, doanh nghiệp, sinh viên tự do sử dụng, nghiên cứu, sửa đổi và phân phối lại (kể cả thương mại) nhằm bảo đảm chủ quyền số và không khóa chặt nhà cung cấp.
- Kiểm chứng (đủ 4 lệnh): `git grep -n "project-changelog" -- . ':!plans' ':!docs/project-changelog.md'` không in gì; `~/.cache/onebee-kiem/bin/python -m unittest tests/desktop/test_onebee_phien_ban.py` thoát mã 0; `grep -q "tự do sử dụng" README.md`; sau khi commit, `scripts/dong-goi-ban-phat-hanh.sh 1.3.0-dev` in `Đã tạo:` và `tar tzf dist/onebee-os-1.3.0-dev.tar.gz | grep -c "/LICENSE$"` in `1` (rồi giải nén sang `/tmp/kiem-thu-ngoai-thu-muc` kiểm tra `python3 scripts/chen-giay-phep.py --kiem` thoát mã 0, cuối cùng `rm -rf dist /tmp/kiem-thu-ngoai-thu-muc`).

### Nhiệm vụ 1.4 — CI chặn tệp mới thiếu giấy phép; Issue Tracker; PR
- File: `.github/workflows/ci.yml` (thêm dòng `python3 scripts/chen-giay-phep.py --kiem` vào bước test đơn vị), `CHANGELOG.md` (mục `[Unreleased]` cho bản `1.3.0` tiếp theo vì `v1.2.0` đã phát hành).
- Các bước ngoài mã: tạo các GitHub Issue đại diện cho từng giai đoạn của plan trên repo (và ghi `Closes #<id>` vào mô tả PR tương ứng) để ban giám khảo kiểm tra thấy bug tracker hoạt động thực tế.
- Kiểm chứng: `gh pr checks --watch` thoát mã 0; `gh issue list --limit 10` có ít nhất 5 issue đang mở cho kế hoạch OLP 2026. Dừng ở đây, không gộp.

## Todo
- [ ] 1.1 Test giấy phép từng tệp (đỏ)
- [ ] 1.2 Chèn dòng giấy phép
- [ ] 1.3 LICENSE trong gói, CHANGELOG ở gốc, mục đích giấy phép
- [ ] 1.4 CI kiểm, Issue tracker, PR xanh

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Chú thích chèn sai làm hỏng tệp (YAML, Jinja sinh JSON, unit systemd) | CI đỏ ở lint hoặc ở bước cài thử | Hoàn tác đúng tệp đó, thêm vào danh sách loại trừ có ghi lý do. |
| Nhánh khác đang sửa cùng tệp | Xung đột khi rebase | Chạy lại `scripts/chen-giay-phep.py` sau khi rebase; script không chèn trùng. |

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
