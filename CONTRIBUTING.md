# Đóng góp cho OneBee OS

Cảm ơn bạn quan tâm! Dự án nhắm tới HTX, hộ kinh doanh, doanh nghiệp nhỏ **không có người chuyên CNTT** — mọi thay đổi nên giữ cho việc cài và vận hành đơn giản.

## Cách đóng góp
| Bạn muốn | Làm gì |
|---|---|
| Báo lỗi | Mở Issue theo mẫu **"Báo lỗi"** (kèm phiên bản/commit, môi trường, các bước, nhật ký đã xóa mật khẩu) |
| Đề xuất tính năng | Mở Issue theo mẫu **"Đề xuất"** — nêu đơn vị dùng nó thế nào, không chỉ giải pháp kỹ thuật |
| Lỗ hổng bảo mật | **Không** mở Issue công khai — xem [SECURITY.md](SECURITY.md) |
| Sửa tài liệu / code | Fork → nhánh mới → Pull Request theo mẫu |

## Chuẩn bị môi trường
Linux (hoặc macOS / Windows WSL2) có **Docker**, Python ≥ 3.10, `shellcheck`, `openssl`, `htpasswd` (`apache2-utils`), `ssh-keygen`.
```bash
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee && cd onebee
pip install -r requirements-dev.txt pyyaml jinja2
```

## Trước khi mở Pull Request
Chạy phần liên quan tới thay đổi của bạn (chi tiết: [tests/README.md](tests/README.md)):
```bash
# Nhanh (vài chục giây) — luôn chạy
python3 -m unittest discover -s tests/box -p 'test_*.py'
python3 -m unittest discover -s tests/desktop -p 'test_*.py'
python3 tests/kiem-tra-mau-jinja.py
yamllint . && (cd box/ansible && ansible-lint site.yml) && (cd desktop/ansible && ansible-lint site.yml)

# Đổi phần máy trạm → cài thử trong container Linux Mint (~2–10 phút)
tests/desktop/run-desktop-test-in-mint-container.sh

# Đổi phần Box → kiểm thử đầy đủ trong container systemd + Docker lồng (≥ 50 phút, ≥ 30 GB trống, RAM ≥ 8 GB cho Docker)
tests/box/run-box-test-in-systemd-container.sh
```
Mạng có proxy HTTPS tự ký: `export ONEBEE_TEST_EXTRA_CA=/đường/dẫn/ca.crt`.

## Quy ước
- **Commit**: kiểu [Conventional Commits](https://www.conventionalcommits.org/), mô tả bằng tiếng Việt, ví dụ `fix(box): …`, `test(box): …`, `docs: …`.
  Thân commit nêu **vì sao** và **đã kiểm bằng gì**.
- **Bộ cài phải chạy lại được nhiều lần**: lần 2 phải `changed=0`. Thêm task Ansible mới thì kiểm điều này.
- **Không đưa bí mật vào repo** (mật khẩu, khóa, file `.env`, nhật ký có khóa). Bí mật sinh trên Box, nằm ở `/etc/onebee-box/secrets/`.
- **Trung thực về số liệu**: không ghi tốc độ, chi phí, tiết kiệm nếu chưa có file đo trong `reports/`. Phân biệt rõ "đã kiểm trong container" và "đã chạy trên máy thật".
- **Tài liệu cho người dùng** viết tiếng Việt, câu ngắn, lệnh dán được; cập nhật hướng dẫn trong `docs/huong-dan/` cùng lúc với thay đổi hành vi.
- Sửa lỗi thì thêm **kiểm thử hồi quy** (test phải FAIL khi bỏ bản sửa).
- Quyết định kiến trúc mới: thêm ADR trong `docs/adr/`.

## Ứng xử
Tham gia dự án đồng nghĩa với việc đồng ý [Quy tắc ứng xử](CODE_OF_CONDUCT.md).
