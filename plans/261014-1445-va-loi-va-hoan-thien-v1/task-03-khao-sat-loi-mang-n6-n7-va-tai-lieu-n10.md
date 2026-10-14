# Task 03 — Khảo sát lỗi mạng N6, N7 & Chuẩn hóa tài liệu N10

**Ưu tiên:** Thấp / Khảo sát & Chuẩn hóa  
**Trạng thái:** Sẵn sàng thực hiện  
**Hạng mục:** N6, N7, N10 theo `docs/kiem-thu-tren-may-that.md`.

---

## 1. N6 — Thứ tự iptables giữa Tailscale và tường lửa OneBee

### Hiện tượng & Rủi ro nghi ngờ
- `onebee-tuong-lua` chèn quy tắc lọc tại vị trí đầu tiên của chuỗi `INPUT` và `FORWARD` khi chạy.
- Tuy nhiên, `tailscaled` khi khởi động hoặc nạp lại cấu hình cũng tự động chèn các chuỗi `ts-input` và `ts-forward` lên đầu danh sách `iptables`.
- Nếu các chuỗi của Tailscale đứng trước và chấp nhận (ACCEPT) các gói tin từ giao diện `tailscale0`, thì bất kỳ thiết bị nào cùng mạng tailnet đều có thể truy cập các cổng dịch vụ của Box mà không bị ràng buộc bởi danh sách cho phép trong biến `onebee_box_tailscale_cho_phep`.

### Giải pháp kỹ thuật
1. Trong file service systemd `onebee-tuong-lua.service`:
   - Thêm `After=tailscaled.service` (hoặc `Wants=tailscaled.service`).
2. Trong script `onebee-tuong-lua`:
   - Kiểm tra nếu có giao diện `tailscale0`, đảm bảo các quy tắc lọc của OneBee áp dụng cho `tailscale0` trước khi các chuỗi mặc định của Tailscale can thiệp.
   - Trường hợp không thể kiểm soát thứ tự chèn động của Tailscale: Bổ sung cảnh báo trong tài liệu khuyến nghị quản trị viên thiết lập ACL trực tiếp trên Tailscale Admin Console để cô lập cổng Box.

---

## 2. N7 — IPv6 toàn cầu và dịch vụ Samba / SSH

### Hiện tượng & Rủi ro nghi ngờ
- Quy tắc tường lửa `onebee-tuong-lua` hiện tại cho IPv6 chỉ cho phép dải link-local và unique local: `fe80::/10` và `fc00::/7`, mọi gói tin IPv6 khác bị DROP âm thầm.
- Trong các mạng LAN gia đình hoặc doanh nghiệp nhỏ có bật IPv6 từ nhà mạng (SLAAC / DHCPv6 cấp IPv6 toàn cầu), hệ điều hành Windows thường ưu tiên kết nối tới máy chủ (ví dụ `\\onebee-box`) qua IPv6 trước. Khi gói tin bị DROP (không phản hồi), Windows sẽ bị treo timeout từ 10–30 giây trước khi thử lùi về IPv4, gây cảm giác "máy chủ bị đơ" hoặc "không kết nối được ổ mạng chung".

### Giải pháp kỹ thuật
1. Trong `box/ansible/roles/box-firewall/files/onebee-tuong-lua`:
   - Thay vì DROP âm thầm các kết nối IPv6 không hợp lệ trên cổng Samba (445) và SSH (22), chuyển sang `REJECT --reject-with icmp6-port-unreachable` (hoặc `tcp-reset`).
   - Việc trả về REJECT lập tức giúp Windows nhận biết cổng không mở trên IPv6 và chuyển sang kết nối IPv4 ngay trong vài mili-giây, không bị nghẽn timeout.

---

## 3. N10 — Đồng bộ tài liệu hướng dẫn khớp với mã nguồn thực tế

### Các điểm cần chỉnh sửa trong tài liệu
1. **Số dòng cấu hình máy trạm:**
   - Sửa trong `docs/huong-dan/cai-dat-onebee-box.md:91` và `docs/huong-dan/thu-nghiem-tren-may-ao.md:38`:
   - Sửa "9 dòng" thành **"12 dòng cấu hình"** (bao gồm `BOX_CA`, `BOX_CA_VAN_TAY`, `BOX_HTTPS`, v.v.).
2. **Khai báo biến bắt buộc trước khi cài đặt:**
   - Trong `docs/huong-dan/thu-nghiem-tren-may-ao.md` và `cai-dat-onebee-box.md`: Nêu rõ ràng `onebee_box_ma_don_vi` là biến bắt buộc phải khai báo (bộ cài sẽ dừng nếu thiếu để bảo đảm an toàn sinh CA).
3. **Cơ chế đồng bộ máy trạm tự động:**
   - Trong `docs/huong-dan/quan-ly-may-tram.md` và ghi chú trong `onebee-box.sh.j2`: Cập nhật nội dung giải thích rằng playbook `dong-bo-may-tram.yml` đã tự động chạy lại các task cấu hình `cau-hinh-hoi`, `muc-menu`, và `ket-noi-box`, người dùng không cần chạy lại bộ cài desktop bằng tay.
4. **Chuẩn hóa danh mục lệnh quản trị:**
   - Rà soát `docs/security-audit.md`: Ghi chú rõ các lệnh dự kiến cho tương lai (như `doi-khoa-quan-tri`, `doi-ca`) so với các lệnh đã được hiện thực hóa trong `onebee-box`.

---

## 4. Tiêu chuẩn hoàn thành
- [ ] Script tường lửa được kiểm tra với các kịch bản IPv6 và Tailscale.
- [ ] Toàn bộ các file tài liệu trong `docs/huong-dan/` được rà soát và không còn mâu thuẫn với mã nguồn.
- [ ] Commit: `docs: đồng bộ tài liệu hướng dẫn và tinh chỉnh tường lửa IPv6 (N6, N7, N10)`.
