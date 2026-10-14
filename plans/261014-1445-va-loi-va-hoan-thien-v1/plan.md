# Kế hoạch xử lý các lỗi còn mở (N13, N2, N4–N9) và hoàn thiện v1.0.0

Lập ngày: 14/10/2026  
Dự án: **OneBee OS (DA3)** — `https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source`  
Nhánh gốc: **`main`** (commit nền: `c0a0ccb`, CI xanh)  
Tác giả dự án: **Dương Minh Thiện** (`thien20071005@gmail.com` · SĐT: 0777 794 089) · HTX OneBee (MST 1102128064)

---

## 1. Bối cảnh & Mục tiêu

Sau đợt rà soát bảo mật Pha 1–5 (PR #1 đã gộp vào `main`), hệ thống đã đạt:
- **122 PASS / 0 FAIL** trên bài kiểm thử Box runner đầy đủ trong container systemd + Docker Desktop (MacBook Intel).
- Đã sửa các lỗi phát hiện khi chạy thật: **N11** (SIGHUP rest-server), **N12** (chuyển sang `docker exec kill -HUP 1`), **T1–T3** (sửa script test).

Kế hoạch này tập trung giải quyết toàn bộ các vấn đề còn mở được bàn giao trong `docs/kiem-thu-tren-may-that.md` và `onebee-os-ban-giao.md`, xếp theo thứ tự ưu tiên giảm dần, hướng tới việc đóng gói bản phát hành chính thức **v1.0.0**.

---

## 2. Quy ước bắt buộc khi thực hiện (Claude Code cần tuân thủ)

1. **Thông tin tác giả commit:**
   - Author name: `Dương Minh Thiện`
   - Author email: `thien20071005@gmail.com`
   - Tuyệt đối không commit bằng tên bot/tài khoản lạ.
2. **Quy cách commit:**
   - Tuân thủ [Conventional Commits](https://www.conventionalcommits.org/): `fix(box): ...`, `fix(desktop): ...`, `test(box): ...`, `docs: ...`.
   - Tiêu đề và mô tả bằng **tiếng Việt**, giải thích rõ *nguyên nhân* và *đã kiểm bằng lệnh gì*.
3. **Quy chuẩn chất lượng bộ cài:**
   - **Tính lũy nghiệm (Idempotency):** Chạy lại bộ cài lần 2 trên cùng hệ thống bắt buộc `changed=0 failed=0`.
   - **Kiểm thử hồi quy (TDD):** Mọi bản vá lỗi bắt buộc phải có unit test / regression test chứng minh (test phải FAIL khi chưa có bản sửa, và PASS sau khi sửa).
4. **Bảo mật & Tính xác thực:**
   - Không commit file cấu hình chứa bí mật (`.env`, private key, password, v.v.).
   - Không tự ý thêm số liệu hiệu năng/tốc độ nếu chưa đo đạc thực tế lưu trong thư mục `reports/`.
5. **Môi trường thao tác đề xuất:**
   - Thư mục làm việc: `~/onebee-da3-test` (hoặc workspace repo đã đồng bộ với `main`).
   - Nếu chạy bài Box nặng, cần cấu hình Docker Desktop cấp ≥ 8 GB RAM (khuyến nghị 16 GB).

---

## 3. Bảng tổng hợp các hạng mục công việc

| Mã | Hạng mục | Mức độ | Trạng thái kỹ thuật | File chi tiết |
| :--- | :--- | :---: | :---: | :--- |
| **N13** | CORS ở chế độ HTTP: chặn Origin lạ, sửa test curl | **Cao** | **ĐÃ HOÀN TẤT** (`16057f5`, `949f439`) | [task-01-n13-cors-che-do-http.md](task-01-n13-cors-che-do-http.md) |
| **N4** | CA trung gian: đưa gia hạn lên trước kiểm tra ổ sao lưu | **Trung bình** | **ĐÃ HOÀN TẤT** (`ae356da`) | [task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md](task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md) |
| **N5** | `hoi --dan-khoa`: chặn bypass ghim CA khi redirect 308 | **Thấp** | **ĐÃ HOÀN TẤT** (`a5401dd`) | [task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md](task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md) |
| **N8** | `xoay-khoa --box`: tự động gọi `dong-bo-may --tat-ca` | **Trung bình** | **ĐÃ HOÀN TẤT** (`bbd628b`) | [task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md](task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md) |
| **N9** | `xoay-khoa --may`: xử lý máy trạm đang tắt + lock an toàn | **Thấp** | **ĐÃ HOÀN TẤT** (`79502e9`) | [task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md](task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md) |
| **N2** | Xoay CA: gỡ CA cũ khỏi hồ sơ Firefox theo vân tay | **Trung bình** | **ĐÃ HOÀN TẤT** (`95643e3`) | [task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md](task-02-va-loi-xac-nhan-n2-n4-n5-n8-n9.md) |
| **N6** | Thứ tự iptables giữa Tailscale và tường lửa OneBee | **Thấp** | **ĐÃ HOÀN TẤT** (`7fbc274`) | [task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md](task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md) |
| **N7** | IPv6 toàn cầu: tránh treo timeout khi Windows mở Samba | **Thấp** | **ĐÃ HOÀN TẤT** (`7fbc274`) | [task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md](task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md) |
| **N10** | Đồng bộ tài liệu không khớp code (12 dòng, lệnh quản trị) | **Thấp** | **ĐÃ HOÀN TẤT** (`5240e99`) | [task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md](task-03-khao-sat-loi-mang-n6-n7-va-tai-lieu-n10.md) |
| **V1** | Kiểm thử máy thật & Quy trình đóng gói phát hành v1.0.0 | **Cao** | **ĐANG TIẾN HÀNH** | [ke-hoach-kiem-thu-may-that-va-dong-goi-v1.md](ke-hoach-kiem-thu-may-that-va-dong-goi-v1.md) |

---

## 4. Các giai đoạn triển khai (Milestones)

### Giai đoạn 1: Vá lỗi bảo mật cấp bách N13 — [ĐÃ HOÀN TẤT]
- Sửa template `docker-compose.yml.j2` đặt `CORS_ALLOW_ORIGIN` ở cả chế độ HTTP.
- Siết chặt assertion trong `tests/box/check-https.sh:53` để loại bỏ ca đạt giả khi curl lỗi.
- Viết unit test trong `test_onebee_compose_https.py` kiểm tra sinh cấu hình đúng.

### Giai đoạn 2: Xử lý nhóm lỗi mã nguồn đã XÁC NHẬN (N4, N5, N8, N9, N2) — [ĐÃ HOÀN TẤT]
- **N4:** Tách logic gia hạn CA trung gian trong `onebee-box-sao-luu.sh.j2` chạy trước bước kiểm tra ổ gắn ngoài.
- **N5:** Cập nhật hàm `mo()` và `dan_khoa()` trong `desktop/ansible/roles/ai-cli/files/hoi` chặn redirect theo 308 bằng CA công cộng.
- **N8:** Trong lệnh `cmd_xoay_khoa` (`onebee-box.sh.j2`), tự động đồng bộ khóa tình trạng mới xuống toàn bộ máy trạm trực tuyến.
- **N9:** Thêm `with_lock` cho `xoay-khoa` và cảnh báo thân thiện khi máy đích tắt thay vì làm gián đoạn lệnh.
- **N2:** Trong `onebee-chinh-sach-trinh-duyet.py`, dọn sạch chứng chỉ CA cũ khỏi `cert9.db` của Firefox theo vân tay SHA-256.

### Giai đoạn 3: Khảo sát & xử lý lỗi mạng (N6, N7) & Chuẩn hóa tài liệu (N10) — [ĐÃ HOÀN TẤT]
- **N6 & N7:** Lọc kết nối `tailscale0` ở bảng `mangle/PREROUTING`; chuyển từ chối IPv6 sang `REJECT` (`tcp-reset`, `icmp6-port-unreachable`).
- **N10:** Đồng bộ toàn bộ 8 file tài liệu trong `docs/` (chuẩn 12 dòng, biến bắt buộc, lệnh thực tế).
- **Lũy nghiệm:** Thêm `changed_when: false` cho task `Cập nhật danh mục gói` ở cả box-base và desktop base (`8328dbf`).

### Giai đoạn 4: Nghiệm thu Docker, Kiểm thử máy thật & Đóng gói v1.0.0 — [ĐANG TIẾN HÀNH]
- Nghiệm thu Docker: Desktop Mint 22.3 (100% ĐẠT), Box Runner (100% ĐẠT).
- Kế hoạch kiểm thử máy thật: Chi tiết xem tại [ke-hoach-kiem-thu-may-that-va-dong-goi-v1.md](ke-hoach-kiem-thu-may-that-va-dong-goi-v1.md).
- Đóng gói phát hành: Tạo thẻ tag `v1.0.0`, cập nhật CHANGELOG và công bố GitHub Release.

---

## 5. Lệnh kiểm tra xác nhận sau mỗi giai đoạn

```bash
# 1. Bộ kiểm tra nhanh (chạy thường xuyên):
python3 -m unittest discover -s tests/box -p 'test_*.py'
python3 -m unittest discover -s tests/desktop -p 'test_*.py'
python3 tests/kiem-tra-mau-jinja.py

# 2. Kiểm tra cú pháp và lint:
yamllint .
(cd box/ansible && ansible-lint site.yml)
(cd desktop/ansible && ansible-lint site.yml)

# 3. Kiểm tra cài đặt máy trạm (Mint container):
tests/desktop/run-desktop-test-in-mint-container.sh

# 4. Kiểm tra toàn diện Box (chạy khi sửa file box/ansible hoặc scripts quản trị):
tests/box/run-box-test-in-systemd-container.sh
```
