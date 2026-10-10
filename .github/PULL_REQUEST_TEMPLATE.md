## Thay đổi gì, vì sao

<!-- 1–3 câu. Liên kết Issue nếu có: "Sửa #12" -->

## Đã kiểm bằng gì
<!-- Đánh dấu những gì bạn THỰC SỰ đã chạy. Ghi rõ chạy trong container hay máy thật. -->
- [ ] Unit test: `python3 -m unittest discover -s tests/box -p 'test_*.py'` / `tests/desktop`
- [ ] Lint: `yamllint .`, `ansible-lint`, `shellcheck`
- [ ] Container Mint: `tests/desktop/run-desktop-test-in-mint-container.sh`
- [ ] Container Box: `tests/box/run-box-test-in-systemd-container.sh`
- [ ] Máy ảo / máy thật (mô tả):

## Kiểm tra trước khi gửi
- [ ] Bộ cài chạy lại lần 2 vẫn `changed=0` (nếu sửa Ansible)
- [ ] Sửa lỗi có kèm kiểm thử hồi quy (FAIL khi bỏ bản sửa)
- [ ] Không có mật khẩu, khóa, IP thật, dữ liệu khách hàng trong code/nhật ký
- [ ] Đã cập nhật tài liệu trong `docs/huong-dan/` nếu hành vi người dùng thấy bị đổi
- [ ] Không thêm con số tốc độ/chi phí chưa có file đo trong `reports/`
