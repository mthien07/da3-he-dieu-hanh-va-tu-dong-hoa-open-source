---
phase: 9
title: "Giai đoạn 9: Bản chạy thử công khai trên host Internet"
status: todo
priority: P1
effort: "2d"
dependencies: [4, 6]
---

# Giai đoạn 9: Bản chạy thử công khai trên host Internet

Nhánh: `feat/ban-chay-thu-cong-khai-host`. Đề thi (mục 6) khuyến khích vận hành thử trên môi trường Internet để ban giám khảo và cộng đồng trải nghiệm trước và trong buổi chung kết; giúp nâng điểm tiêu chí 8, 9, 11.

## Mục tiêu
Có một địa chỉ `https://<tên-miền>/` công khai, ổn định, bảo mật bằng HTTPS thật (Let's Encrypt) và dữ liệu demo độc lập hoàn toàn với dữ liệu thật của đơn vị, có tài khoản demo sẵn cho ban giám khảo dùng thử trong 1 click.

## Điều cần biết
- **Tuyệt đối tách biệt**: bản trên host chỉ chứa **dữ liệu giả lập (demo)**, **không** nối với Box hoặc máy trạm của đơn vị đang thử nghiệm thật.
- Để không vướng chứng chỉ CA nội bộ trên trình duyệt của giám khảo, Caddy trên host dùng chế độ tên miền thật (ACME / Let's Encrypt tự động của Caddy).
- Host công khai cần cấu hình tối thiểu: Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 80 GB SSD (hoặc 16 GB RAM nếu chạy Ollama model vừa; nếu host không đủ RAM cho Gemma 4, cấu hình fallback mô hình nhẹ hơn như `qwen2.5:1.5b` hoặc `gemma3:1b` trên host demo và ghi rõ).

## Nhiệm vụ

### Nhiệm vụ 9.1 — Chuẩn bị hạ tầng host (phối hợp anh Thiện)
- Các bước: anh Thiện thuê VPS / chuẩn bị máy chủ và trỏ bản ghi DNS A tới IP máy chủ, cung cấp khóa SSH truy cập quyền triển khai. Em chuẩn bị biến cấu hình Ansible riêng cho chế độ công khai (`onebee_box_che_do_demo: true`, `onebee_box_domain: <tên miền>`, bật tường lửa chỉ mở `22`, `80`, `443`).
- Kiểm chứng: `ansible -i inventory.demo.ini all -m ping` thành công; cổng `5432`, `11434`, `8080`, `9000`... đóng hoàn toàn từ bên ngoài (`nmap` / `nc` từ máy trạm báo timeout/refused).

### Nhiệm vụ 9.2 — Triển khai lõi và bộ dữ liệu demo tự đặt lại
- Các bước: viết script `scripts/nap-du-lieu-demo.sql` tạo dữ liệu mẫu sinh động (3 tài khoản minh họa: `nhanvien1`, `kythuat1`, `quanly1` kèm mật khẩu công khai ở màn hình chào demo, vài đơn hàng, yêu cầu hỗ trợ, tệp PDF mẫu `CLEAN`, tài liệu tri thức NĐ 30); thiết lập systemd timer / cron đặt lại dữ liệu demo lúc `03:00` sáng hằng ngày để tránh rác do người dùng thử tạo ra.
- Kiểm chứng: chạy `nap-du-lieu-demo.sql` hai lần liên tiếp không lỗi; dịch vụ trên host chạy ổn định sau khởi động lại.

### Nhiệm vụ 9.3 — Đưa ứng dụng H-P-D-I lên host và kiểm khói từ ngoài mạng
- Các bước: triển khai bản mới nhất sau khi gộp giai đoạn 6, 7, 8 lên host; thêm thanh thông báo nhỏ "Bản chạy thử công khai OLP 2026 — Dữ liệu giả lập, tự đặt lại lúc 03:00" ở đầu ứng dụng khi bật `onebee_box_che_do_demo: true`.
- Kiểm chứng: từ mạng ngoài (máy của anh Thiện / GitHub Actions):
  1. `curl -fsS https://<tên-miền>/` trả mã 200, chứng chỉ TLS hợp lệ.
  2. Gọi trực tiếp `/api/don_hang` không đăng nhập nhận 401.
  3. Đăng nhập thử bằng tài khoản `nhanvien1` → gửi đơn + tệp đính kèm → đăng nhập `quanly1` duyệt → vào dashboard xem số liệu cập nhật → hỏi Trợ lý AI trả lời tiếng Việt.

## Todo
- [ ] 9.1 Chuẩn bị host, tên miền và inventory demo
- [ ] 9.2 Triển khai lõi + dữ liệu demo + cron đặt lại hằng đêm
- [ ] 9.3 Đưa ứng dụng lên host và chạy kiểm khói công khai

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| VPS RAM 8 GB chạy Ollama + toàn bộ lõi bị chậm hoặc OOM | Yêu cầu AI trên bản demo quá 60s hoặc timeout | Trên host demo dùng model nhẹ hơn (vd `qwen2.5:1.5b` hoặc `gemma3:1b`) qua biến cấu hình trong `inventory.demo.ini`, không sửa cấu hình Box thật; kèm kịch bản video dự phòng. |
| Người dùng lạ tấn công hoặc spam form trên bản công khai | Log lỗi 429/500 liên tục, đầy đĩa | Giới hạn tần suất (rate limit) trên Caddy + giới hạn dung lượng tệp 5 MB ở chế độ demo + cron đặt lại dữ liệu hằng đêm. |

## Bảo mật
Không dùng chung khóa ký, mật khẩu hay dữ liệu của bất kỳ đơn vị nào lên host demo. Tuyệt đối không commit IP, khóa SSH hay mật khẩu quản trị VPS vào kho mã (chỉ lưu file mẫu `.example`).

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.

