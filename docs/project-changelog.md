# Nhật ký thay đổi

## [0.1.0] — 28/9/2026 — OneBee OS Desktop v0.1
### Thêm
- `desktop/onebee-install.sh` + playbook Ansible: tiếng Việt (locale, gói ngôn ngữ, IBus + Bamboo), font tương thích
  Microsoft, LibreOffice tiếng Việt lưu mặc định .docx/.xlsx/.pptx, hình nền OneBee, tự động cập nhật mintupdate.
- Kiểm thử tự động trong container Linux Mint 22.3 (có mint-artwork như máy thật): cài 2 lần (idempotent), 31 mục kiểm tra + 4 mục LibreOffice kiểm qua UNO.
- Bảo mật: PPA ibus-bamboo bị giới hạn chỉ cấp gói `ibus-bamboo` (apt pin), khóa ký lưu sẵn trong repo.
- Chờ khóa dpkg tối đa 10 phút (máy mới cài thường đang tự cập nhật ngầm).
- CI GitHub Actions: shellcheck, yamllint, ansible-lint, cài thử trên Mint 22.3.
- ADR 0001 (chọn nền tảng), `LICENSES.md` (giấy phép thành phần), hướng dẫn cài đặt.
### Đổi
- Chuyển hồ sơ dự thi vào `docs/hoi-thi/`.
- Demo web: bỏ số "80.000.000đ" và "Giảm 80%" chưa có nguồn đo — thay bằng "Theo báo giá" / "Đo khi thí điểm".
