# Task 02 — Xử lý nhóm lỗi mã nguồn đã XÁC NHẬN (N4, N5, N8, N9, N2)

**Ưu tiên:** Trung bình  
**Trạng thái:** Sẵn sàng thực hiện  
**Danh sách lỗi:** N4, N5, N8, N9, N2 theo mục "Nghi ngờ lỗi cần xác nhận" trong `docs/kiem-thu-tren-may-that.md`.

---

## 1. N4 — Gia hạn CA trung gian chạy độc lập với việc gắn ổ sao lưu

### Hiện tượng & Nguyên nhân
- Trong `box/ansible/roles/box-stack/templates/onebee-box-sao-luu.sh.j2` (dòng 47–49), lệnh `require_backup_disk` và `restic cat config || die` nằm trước khối `gia_han_ca` (dòng 52–57).
- Nếu người dùng chưa gắn ổ cứng sao lưu, tiến trình sao lưu chết ngay (`die`) trước khi kiểm tra và gia hạn CA. Hậu quả: sau 1 năm CA trung gian hết hạn, hệ thống HTTPS sập dù tài liệu cam kết "tự động gia hạn mỗi đêm".

### Hướng sửa
Đưa khối kiểm tra & gia hạn CA lên đầu hàm `cmd_sao_luu()`, trước bất kỳ kiểm tra nào liên quan đến ổ đĩa sao lưu:
```bash
cmd_sao_luu() {
  # CA trung gian hết hạn thì HTTPS ngừng: gia hạn khi còn < 60 ngày, độc lập với việc có gắn ổ sao lưu hay không
  if [[ -s "${CA_DIR}/root.crt" ]]; then
    gia_han_ca >/dev/null || warn "Không gia hạn được CA riêng của Box — xem: sudo onebee-box in-ca"
    [[ "$(ca_con_ngay inter)" -ge 30 ]] || warn "CA trung gian của Box còn dưới 30 ngày hoặc đã hết hạn — chạy bộ cài OneBee Box"
    [[ "$(ca_con_ngay root)" -ge 365 ]] || warn "CA gốc của Box còn dưới 1 năm — lên kế hoạch xoay CA (onebee_box_xoay_ca trong group_vars/all.yml)"
  fi

  require_backup_disk
  box_repo_env
  restic cat config >/dev/null 2>&1 || die "Chưa tạo kho sao lưu Box. Chạy: sudo onebee-box khoi-tao"
  [[ "$(stat -c %d "${BACKUP_MOUNT}")" != "$(stat -c %d "${DATA}")" ]] || warn "Ổ sao lưu cùng ổ với dữ liệu — hỏng ổ là mất cả hai"
  ...
```

### Test hồi quy
Trong `tests/box/test_onebee_box_shell.py`: Viết test case giả lập ổ sao lưu chưa gắn (`BACKUP_MOUNT` trống hoặc `require_backup_disk` trả về lỗi), gọi hàm sao lưu và xác nhận lệnh `gia_han_ca` vẫn được thực thi thành công.

---

## 2. N5 — `hoi` không theo chuyển hướng tự động bằng CA công cộng khi nhận 308

### Hiện tượng & Nguyên nhân
- Trong `desktop/ansible/roles/ai-cli/files/hoi` (`dan_khoa`), lời gọi `GET /api/models` sử dụng `urllib.request.urlopen`.
- Trong Python ≥ 3.11, đối với yêu cầu GET, `urllib.request.urlopen` mặc định tự động theo chuyển hướng HTTP 301/308 thông qua `HTTPRedirectHandler`.
- Khi URL ban đầu là `http://...`, ngữ cảnh SSL truyền vào là `None`. Khi `urllib` chuyển hướng sang `https://...`, nó tự động dùng ngữ cảnh SSL mặc định của hệ điều hành (chứa các CA công cộng) thay vì ghim chỉ tin CA OneBee. Điều này đi vòng qua cơ chế bảo vệ trong `mo()`.

### Hướng sửa
Tạo một `OpenerDirector` tùy chỉnh không kích hoạt `HTTPRedirectHandler` ngầm định, hoặc chặn chuyển hướng ngầm định để toàn bộ mã phản hồi 301/308 được bắt tại khối `except urllib.error.HTTPError as e:` của hàm `mo()`. Tại đó, chuyển hướng chỉ được chấp nhận nếu thỏa mãn điều kiện nghiêm ngặt: cùng máy chủ, chuyển sang HTTPS và sử dụng CA OneBee (`cafile=CA_ONEBEE`).

```python
class ChặnChuyểnHướngTựĐộng(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Trả về None để urllib không tự nhảy, ném HTTPError để hàm mo() xử lý an toàn
        return None

opener = urllib.request.build_opener(ChặnChuyểnHướngTựĐộng)
```

### Test hồi quy
Trong `tests/desktop/test_onebee_hoi.py`: Viết test mô phỏng phản hồi 308 từ máy chủ lạ hoặc chuyển hướng sang CA không phải OneBee để đảm bảo `hoi` từ chối kết nối ngay lập tức.

---

## 3. N8 — `xoay-khoa --box` tự động đồng bộ sang máy trạm khi dùng khóa tình trạng chung

### Hiện tượng & Nguyên nhân
- Khi chạy `onebee-box xoay-khoa --box`, lệnh xóa `tinh-trang-key` (`onebee-box.sh.j2:359`).
- Tuy nhiên, bộ cài chỉ tự kích hoạt `dong-bo-may` khi phát hiện chứng chỉ CA hoặc cờ HTTPS thay đổi (`box-fleet/tasks/main.yml:75`).
- Kết quả: Các máy trạm gửi báo cáo tình trạng bị lỗi `403 Forbidden` liên tục cho đến khi người quản trị tự nhớ để chạy lệnh `onebee-box dong-bo-may --tat-ca`.

### Hướng sửa
Trong hàm `cmd_xoay_khoa()` của `box/ansible/roles/box-stack/templates/onebee-box.sh.j2`, nếu cờ `--box` được truyền và `TINH_TRANG_KHOA_CHUNG=true`, tự động kích hoạt `cmd_dong_bo_may_tat_ca`:
```bash
if [[ "${doi_box}" == "true" ]] && [[ "${TINH_TRANG_KHOA_CHUNG:-true}" == "true" ]]; then
  echo "Đang tự động đồng bộ khóa tình trạng mới xuống tất cả máy trạm trực tuyến..."
  cmd_dong_bo_may_tat_ca || warn "Một số máy trạm ngoại tuyến chưa nhận được khóa mới. Chạy lại khi máy bật."
fi
```

### Test hồi quy
Trong `tests/box/test_onebee_box_shell.py`: Viết bài test giả lập chạy `xoay-khoa --box` với `TINH_TRANG_KHOA_CHUNG=true` và xác nhận lệnh đồng bộ máy trạm được gọi.

---

## 4. N9 — Xử lý an toàn khi `xoay-khoa --may` gặp máy trạm đang tắt & thêm lock

### Hiện tượng & Nguyên nhân
- Khi chạy `onebee-box xoay-khoa --may <máy-đang-tắt>`, sau khi mật khẩu kho sao lưu đã được đổi, lệnh `cmd_dong_bo_may_da_chon` gặp lỗi `die "Không có máy nào để làm"` (`onebee-box.sh.j2:277`). Lệnh `die` thoát tiến trình ngay với mã 1 khiến dòng thông báo cảnh báo không thể in ra.
- Thêm vào đó, `xoay-khoa` chưa được bao bọc bởi `with_lock`, dẫn tới nguy cơ xung đột nếu chạy cùng lúc với cronjob sao lưu ban đêm.

### Hướng sửa
1. Bọc thân hàm `cmd_xoay_khoa` trong `with_lock` để đảm bảo độc quyền tiến trình.
2. Trong xử lý đồng bộ sau xoay khóa máy trạm: Bắt trường hợp máy trạm ngoại tuyến, không dùng `die` làm sập script, mà in cảnh báo rõ ràng: `"Máy trạm <tên> hiện đang tắt — mật khẩu kho đã đổi trên Box. Khi máy bật lại, quản trị viên cần chạy: sudo onebee-box dong-bo-may <tên>"`.

### Test hồi quy
Trong `tests/box/test_onebee_box_shell.py`: Kiểm tra ca xoay khóa cho máy trạm ngoại tuyến, xác nhận lệnh trả về mã hợp lệ kèm cảnh báo, không vỡ tiến trình.

---

## 5. N2 — Xoay CA dọn dẹp sạch CA cũ trong hồ sơ Firefox theo vân tay

### Hiện tượng & Nguyên nhân
- Trong `desktop/ansible/roles/ket-noi-box/files/onebee-chinh-sach-trinh-duyet.py`, hàm `cai()` chỉ thêm CA mới vào chính sách.
- Khi người quản trị xoay CA (đặc biệt khi lộ khóa CA cũ), nếu mã đơn vị không đổi thì tên CA mới trùng tên CA cũ (`OneBee Box <mã> Root CA`). Firefox đã nạp chứng chỉ cũ vào CSDL `cert9.db` trong hồ sơ người dùng sẽ tiếp tục tin CA cũ bị lộ.

### Hướng sửa
Trước khi cài đặt CA mới trong `onebee-chinh-sach-trinh-duyet.py`:
1. Đọc vân tay SHA-256 đã lưu của Box tại `/var/lib/onebee/ket-noi-box`.
2. Nếu vân tay cũ tồn tại và khác với vân tay của CA mới:
   - Dùng `certutil` duyệt qua tất cả các profile `cert9.db` của người dùng và root.
   - Tìm và xóa bỏ mọi chứng chỉ có vân tay trùng với vân tay cũ (hoặc xóa theo nickname `OneBee Box * Root CA`) trước khi ghi nhận chính sách mới.

### Test hồi quy
Trong `tests/desktop/test_onebee_ket_noi_box.py`: Mô phỏng kịch bản xoay CA có sẵn CA cũ trong database Firefox giả lập, xác nhận CA cũ bị xóa sạch và chỉ còn CA mới.

---

## 6. Lệnh kiểm tra xác minh

```bash
python3 -m unittest tests.box.test_onebee_box_shell
python3 -m unittest tests.desktop.test_onebee_hoi
python3 -m unittest tests.desktop.test_onebee_ket_noi_box
```

---

## 7. Tiêu chuẩn hoàn thành
- [ ] Toàn bộ 5 lỗi N4, N5, N8, N9, N2 đều có code sửa và test hồi quy tương ứng.
- [ ] Chạy toàn bộ test suite `tests/box` và `tests/desktop` đạt 100% OK.
- [ ] Commit theo từng lỗi riêng biệt theo chuẩn Conventional Commits tiếng Việt.
