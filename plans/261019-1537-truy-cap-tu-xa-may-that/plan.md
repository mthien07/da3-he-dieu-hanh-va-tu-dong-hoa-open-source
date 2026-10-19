# Kế hoạch: truy cập từ xa để cài máy Dell thật đầu tiên

Lập ngày: 19/10/2026 · Nhánh: `claude/confident-gauss-ntiwuc` · Liên quan: giai đoạn 4 của [../261014-1445-va-loi-va-hoan-thien-v1/plan.md](../261014-1445-va-loi-va-hoan-thien-v1/plan.md)

## 1. Bối cảnh
Máy Dell thật đầu tiên đã được cài hệ điều hành tại đơn vị (anh Lê Thành Tuấn). Ảnh chụp màn hình trông giống Ubuntu GNOME (chưa xác nhận phiên bản).
Máy chỉ có wifi, chưa cài OneBee. Kỹ thuật (anh Thiện) vào từ xa tối nay để cài tiếp. Đây là lần đầu bộ cài OneBee gặp máy thật.

## 2. Mục tiêu
Kỹ thuật vào được máy từ xa, không cần ai ngồi máy, không gửi mật khẩu qua tin nhắn; cài xong thì tắt hẳn cầu nối. Không thay `onebee-ho-tro` (ADR 0004).

## 3. Việc đã làm
- Script `scripts/mo-truy-cap-tu-xa.sh` (bật; `--tat` để tắt): Tailscale SSH + chia sẻ màn hình GNOME (RDP).
- Test `tests/desktop/test_mo_truy_cap_tu_xa.py` dùng lệnh giả (11 ca). Chưa chạy trên máy thật.
- Kiểm trên gói Ubuntu 24.04 thật (container): `grdctl` 46.3 đúng cú pháp, cert openssl tự ký được nhận, 3 khóa gsettings có,
  kho Tailscale cài được 1.104.1. Sửa 2 lỗi tìm ra: vừa vào tailnet chưa có IP thì script dừng im lặng; keyring GNOME khóa
  (máy tự đăng nhập) thì `grdctl set-credentials` lỗi làm script dừng → giờ bỏ qua RDP, giữ SSH, báo cách sửa.
- Tài liệu: `docs/huong-dan/truy-cap-tu-xa-khi-cai-may.md`, nối từ `quan-ly-may-tram.md`, `huong-dan-cai-dat-tu-a-den-z.md`, `README.md`;
  `docs/project-changelog.md` mục `[Chưa phát hành]`; `tests/README.md`; phiếu `docs/kiem-thu-tren-may-that.md` mục E2.

## 4. Việc còn lại
- [ ] Chạy thật tối nay theo mục E2 của phiếu; ghi kết quả (đạt/lỗi, client RDP đã thử) vào phiếu.
- [ ] Xác nhận hệ điều hành thật của máy (Ubuntu 24.04 GNOME hay khác); script chỉ hỗ trợ nền noble, amd64.
- [ ] Quyết định máy này làm Box hay máy trạm. Nếu làm Box: khai IP Tailscale của máy kỹ thuật vào `onebee_box_tailscale_cho_phep` để xem web/RDP của Box qua Tailscale (Tailscale SSH không bị chặn; xem hướng dẫn, mục "Lưu ý khi máy này thành OneBee Box").
- [ ] Tắt cầu nối (`--tat`) khi bàn giao máy; kiểm kỹ thuật không còn vào được.

## 5. Tiêu chí xong
- Mục E2.1–E2.5 của phiếu có kết quả ghi lại từ máy thật (đạt hoặc ghi rõ lỗi và cách sửa).
- Máy đã cài OneBee với vai trò rõ ràng (Box hoặc máy trạm) hoặc có lý do ghi lại vì sao chưa.
- `--tat` đã chạy, kỹ thuật không còn vào được bằng `tailscale ssh` và RDP.
- Lỗi tìm được từ máy thật (nếu có) có bản sửa kèm test, và hướng dẫn được sửa cho khớp.

Câu hỏi mở: chưa biết máy có cắm điện cố định hay không; máy có phải GNOME thật không.
