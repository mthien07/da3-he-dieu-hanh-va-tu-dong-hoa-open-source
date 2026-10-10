# Chính sách bảo mật

OneBee Box giữ mật khẩu kho sao lưu và có quyền quản trị trên mọi máy trạm, nên lỗ hổng ở đây ảnh hưởng tới **cả đơn vị dùng nó**.
Cảm ơn bạn đã báo riêng trước khi công bố.

## Phiên bản được hỗ trợ
| Phiên bản | Nhận bản vá bảo mật |
|---|---|
| Nhánh `main` và bản phát hành mới nhất (`v1.0.0-rc.*`) | ✅ |
| Bản cũ hơn | ❌ — hãy nâng cấp (chạy lại bộ cài trên bản mới) |

## Báo lỗ hổng
- **Không** mở Issue công khai cho lỗ hổng bảo mật.
- Báo riêng qua GitHub: tab **Security** của repo → **Report a vulnerability** (Private vulnerability reporting).
- Nếu không dùng được GitHub: liên hệ HTX OneBee theo mục **Liên hệ** trong [README](README.md) và đề nghị kênh trao đổi riêng.

Nội dung nên có: thành phần (Box / máy trạm / tài liệu), phiên bản hoặc commit (`git rev-parse --short HEAD`), các bước tái hiện,
tác động bạn đánh giá. **Xóa mật khẩu, khóa (`in-khoa`), địa chỉ IP thật** khỏi nhật ký trước khi gửi.

## Chúng tôi làm gì
- Xác nhận đã nhận trong vòng **7 ngày** (mục tiêu của nhóm nhỏ, không phải cam kết hợp đồng).
- Sửa, viết kiểm thử hồi quy, ghi vào [docs/project-changelog.md](docs/project-changelog.md) và ghi công người báo (nếu bạn đồng ý).

## Tài liệu liên quan
- Rà soát bảo mật và trạng thái từng mục: [docs/security-audit.md](docs/security-audit.md) · [docs/tong-ket-ra-soat-bao-mat.md](docs/tong-ket-ra-soat-bao-mat.md)
- Kiểm thử trên máy thật, lỗi đã biết còn mở: [docs/kiem-thu-tren-may-that.md](docs/kiem-thu-tren-may-that.md)
- Thiết kế HTTPS nội bộ: [docs/adr/0005-https-noi-bo-caddy-ca-rang-buoc-ten.md](docs/adr/0005-https-noi-bo-caddy-ca-rang-buoc-ten.md)
