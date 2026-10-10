# Tổng kết rà soát bảo mật — đã làm, chưa làm, cách clone về test

Nhánh: `claude/confident-gauss-ntiwuc` (chưa tạo PR). Kế hoạch gốc: `docs/security-audit.md`. Phiếu kiểm chi tiết: `docs/kiem-thu-tren-may-that.md`.
Quy ước: phần "chưa kiểm" là chưa chạy được trong môi trường làm việc (không có Docker daemon, ansible-core 2.16, Box/Mint/Windows thật). [Unverified] = chưa có bằng chứng.

## 1. Đã làm

| Pha | Nội dung | Trạng thái kiểm |
|---|---|---|
| 1 | n8n lên 2.42.6, ghim digest mọi image, tắt Agents/MCP/Plugins của Open WebUI, cảnh báo tài khoản sudo | Chạy thử đã được kiểm và Opus rà soát |
| 2 | Báo cáo tình trạng có chữ ký; SSH máy trạm phải chứng minh biết mật khẩu kho rồi mới ghim khóa; `thu-hoi-may`, `dong-bo-may` | Chạy thử đã được kiểm và Opus rà soát |
| 3 | CA riêng mỗi Box, giới hạn chỉ cấp cho IP Box và `<mã>.onebee.internal`; role `ket-noi-box` cài CA lên máy trạm | Thử chuỗi CA thật bằng openssl, Python, curl |
| 4 | HTTPS qua Caddy, bật bằng `onebee_box_https: true` (mặc định `false`) | Caddy 2.11.4 thật; Ansible 2.19 chạy được |
| 4b | `onebee-box xoay-khoa [--may\|--tat-ca] [--box]` | Test giả lập, chưa chạy trên Box thật |
| 4c | `hoi --dang-nhap`, `--dan-khoa`, `--dang-xuat` (khóa riêng từng nhân viên) | 10 test qua TLS thật |
| 5 | Tường lửa lọc mọi cổng mạng; Samba chỉ SMB 3.1.1 + mã hóa; `no-new-privileges` cho container; làm sạch CSV/email; ghim GitHub Actions theo SHA; `renovate.json`; nhật ký giữ 90 ngày | Test giả lập (iptables giả, node thật cho CSV) |

Chi tiết quan trọng:
- Khóa gốc CA nằm ở `/etc/onebee-box/secrets/ca`, không gắn vào container nào. CA trung gian tự gia hạn khi còn dưới 60 ngày.
- Bật HTTPS có chốt chặn: còn máy chưa nhận CA thì bộ cài giữ HTTP và nêu tên máy. Hoàn tác bằng `onebee_box_https: false`.
- Máy trạm (`hoi`, báo tình trạng, `onebee-sao-luu`) chỉ tin CA OneBee và từ chối `http://` khi đã bật HTTPS.
- Chuyển tiếp: khóa `hoi` theo máy (`onebee_box_hoi_khoa_may`) và khóa gửi tình trạng dùng chung (`onebee_box_khoa_tinh_trang_chung`) vẫn bật mặc định.
- Opus rà soát Pha 3–4 và tìm ra 2 lỗi nghiêm trọng, đã sửa: CA giả qua mặt bước kiểm tra tên bằng dòng `Excluded:` chèn vào tên DNS; gia hạn CA trung gian không tới được Caddy. Các lỗi vừa cũng đã sửa: bộ cài không idempotent, chuyển HTTP↔HTTPS kẹt, khôi phục còn chứng chỉ cũ của Caddy, máy mất liên lạc khi CA mới không đạt.
- Sau phiếu kiểm đã sửa thêm: N1 (xoay CA khi mã/IP không đổi), N3 (cài `certutil`), một phần N10 (tài liệu).

## 2. Chưa làm

- F9: tài khoản biểu mẫu n8n theo phòng hoặc người. Cần quyết định thiết kế riêng.
- `doi-khoa-quan-tri` (xoay khóa SSH quản trị). Cần giai đoạn chạy song song hai khóa trên mọi máy; thiết kế đề xuất ở `docs/security-audit.md`, khối Pha 5.
- Ký bản phát hành, cờ phiên bản desktop tối thiểu, thẻ restic `truoc-nang-cap`, nâng Ollama 0.40, quét image rest-server.
- Lỗi nghi ngờ còn mở trong phiếu kiểm:
  - N2: xoay CA không gỡ CA cũ khỏi hồ sơ Firefox.
  - N4: gia hạn CA đêm chỉ chạy khi đã gắn ổ sao lưu.
  - N6: `tailscaled` có thể chèn quy tắc đè lên quy tắc Tailscale của OneBee.
  - N5, N7, N8, N9: lỗi mức thấp, mô tả trong phiếu.

## 3. Chưa kiểm được

- Toàn bộ script Docker lồng chưa từng chạy: `check-https.sh`, `check-xoay-khoa.sh`, các sửa trong `run-box-test-in-systemd-container.sh`, `check-khoi-phuc-toan-bo.sh`, `verify-box-install.sh`. Bộ cài trong đó dùng ansible-core 2.16 của Ubuntu, nên đây là lần đầu code mới chạy trên 2.16.
- [Unverified] Firefox và Chrome có áp ràng buộc tên của CA hay không; Windows có áp cho CA tự cài hay không.
- n8n 2.42.6 nhận quy trình 06 và áp mật khẩu chủ mới khi khởi động lại.
- Open WebUI v0.11.4 và Uptime Kuma 2.5.5 chạy đúng các lệnh đổi mật khẩu/khóa API.
- Hệ quả của việc đổi `WEBUI_SECRET_KEY`.
- Tường lửa thật, Tailscale, Samba với Windows 10 và Mint, WebSocket chat qua Caddy, restic tải lớn qua Caddy.

## 4. Clone về test

```bash
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee && git checkout claude/confident-gauss-ntiwuc
```

1. **Khai biến bắt buộc** trong `box/ansible/group_vars/all.yml`: `onebee_box_ma_don_vi` (viết tắt tên khách, thiếu thì bộ cài dừng) và `onebee_box_dia_chi` (IP tĩnh). Biến cũ `onebee_box_address` đã đổi tên.
2. **Test tự động trước:**
   ```bash
   python3 -m unittest discover -s tests/box -p 'test_*.py'
   python3 -m unittest discover -s tests/desktop -p 'test_*.py'
   ONEBEE_TEST_CADDY=/đường/dẫn/caddy python3 -m unittest tests.box.test_onebee_caddy_https
   ```
3. **Script Docker lồng**, làm theo nhóm A của `docs/kiem-thu-tren-may-that.md`:
   - `tests/desktop/run-desktop-test-in-mint-container.sh`
   - `tests/box/run-box-test-in-systemd-container.sh`
4. **Sau đó** làm các nhóm B–E của phiếu kiểm: Box thật, Mint (Firefox, Chromium), thiết bị ngoài quản lý, hỏng ổ và xoay khóa.

Hai thay đổi có thể làm mất đường vào:
- Box đang nối Tailscale mà chưa khai `onebee_box_tailscale_cho_phep` thì mọi kết nối Tailscale tới Box bị chặn.
- Samba bắt buộc SMB 3.1.1 + mã hóa nên Windows 7/8 và máy quét cũ không nối được. Tắt bằng `onebee_box_samba_smb3: false`.
