# ADR 0005 — HTTPS nội bộ: Caddy + CA riêng ràng buộc tên

- Ngày: 10/10/2026 · Trạng thái: Đã làm trên nhánh rà soát bảo mật (Pha 3–4); **chưa thử trên Box/máy trạm thật** · Thay quyết định 5 của ADR 0002
- Nguồn: `docs/security-audit.md` mục F3, QĐ3, QĐ5–QĐ8

## Bối cảnh
Mật khẩu (Trợ lý AI, biểu mẫu n8n, kho sao lưu), khóa API `hoi`, báo cáo tình trạng đi qua LAN dạng rõ. LAN văn phòng không phải mạng tin cậy
tuyệt đối (Wi-Fi, máy nhân viên, thiết bị IoT). Không có tên miền công cộng, nhiều thiết bị chỉ có địa chỉ IP, máy in/camera dùng chứng chỉ tự ký.

## Quyết định
1. **CA riêng cho từng Box**, sinh bằng openssl lúc cài (`box-stack/files/onebee-ca.sh`): gốc 10 năm (`pathlen:1`) + trung gian 1 năm (`pathlen:0`),
   **cả hai có `nameConstraints` critical**: chỉ IP của Box (/32) và `<mã đơn vị>.onebee.internal`. Lộ khóa CA không giả được `google.com`, router, NAS.
   Mỗi khách một mã khác nhau → CA khách A không giả được tên của khách B. Đã kiểm: openssl, Python ssl, curl từ chối chuỗi thật gốc→trung gian→lá
   cho tên ngoài ràng buộc (`tests/box/test_onebee_ca.py`).
2. **Khóa gốc không nằm trong container nào**: `/etc/onebee-box/secrets/ca/` (0700, có trong bản sao lưu Box mã hóa). Caddy chỉ nhận chứng chỉ gốc +
   chứng chỉ/khóa trung gian (`portal/pki`). Caddy 2.11.4 chạy được với gốc không kèm khóa (đã chạy thật). Trung gian tự gia hạn khi còn < 60 ngày (lúc sao lưu đêm).
3. **Caddy là dịch vụ duy nhất công bố cổng** khi bật HTTPS: 443 (trang giới thiệu), 3000/5678/3001/8000 (giữ số cổng, URL chỉ đổi `http`→`https`),
   80 (chỉ chứng chỉ gốc + trang hướng dẫn, không hiện vân tay). Open WebUI, n8n, Uptime Kuma, rest-server mất `ports:`. `default_sni <IP>` vì máy nối bằng IP
   không gửi SNI; `http_redirect` trả 308 cho `http://` tới cổng TLS; chỉ HTTP/1.1 + HTTP/2.
4. **Script trên Box gọi qua `https://<IP>:<cổng>`** với kho CA của Box (một đường duy nhất, giống người dùng; không để cổng backend nào mở).
   Dấu `/etc/onebee-box/secrets/https-da-bat` cho các lệnh `onebee-box` biết gọi http hay https.
5. **Máy trạm** (role `ket-noi-box`): nhận `BOX_CA` + `BOX_CA_VAN_TAY` qua `them-may`/`dong-bo-may`; chỉ cài khi vân tay khớp **và** chứng chỉ đúng là CA OneBee
   có ràng buộc (kiểm cấu trúc, không chỉ vân tay — vân tay đi cùng kênh nên chỉ bắt lỗi chép). Cài vào kho hệ thống, Firefox (chính sách) và Chromium/Chrome.
   `hoi`/`onebee-bao-tinh-trang`/`onebee-sao-luu` chỉ tin CA OneBee (không tin CA công cộng) và **từ chối `http://` khi máy có dấu bền `https-bat`**.
6. **Bật có chốt chặn, hoàn tác được**: `onebee_box_https: true` chỉ có hiệu lực khi mọi máy đã cấp đã nhận CA (không thì giữ HTTP, nêu tên máy); cuối bộ cài Box
   tự đẩy cấu hình xuống máy. `false` → quay về HTTP, cờ `BOX_HTTPS=0` xóa dấu trên máy. Mặc định `false` ở bản này; đổi mặc định ở bản sau.
7. **Thiết bị không do OneBee quản lý** (laptop kỹ thuật, điện thoại, máy Windows của quản lý): cài CA thủ công sau khi đối chiếu vân tay qua kênh ngoài
   (`sudo onebee-box in-ca`, bản in `in-khoa`). Kỹ thuật vào Box qua Tailscale bằng `box.<mã>.onebee.internal` (thêm dòng `/etc/hosts`).

## Rủi ro còn lại (chấp nhận, đã ghi)
- **Hạ cấp / chen giữa**: Firefox không có HSTS cho địa chỉ IP; người dùng gõ tay `http://` thì kẻ chen giữa (sslstrip) có thể giữ ở HTTP. Giảm bằng dấu trang +
  trang chủ https, cổng TLS luôn trả 308, và đào tạo: **mọi** cảnh báo chứng chỉ ở địa chỉ Box là dấu hiệu bị tấn công. Không bật `DisableSecurityBypass`/HTTPS-Only
  (máy in, thiết bị LAN tự ký vẫn phải mở được) → người dùng bấm qua cảnh báo giả vẫn lộ mật khẩu.
- **Cookie dùng chung** giữa các cổng cùng IP (cùng "site"): cookie không tách theo cổng.
- **Ràng buộc tên chỉ giới hạn thiệt hại khi lộ khóa CA mà Box chưa bị chiếm.** Chiếm Box (root) thì cài được CA tùy ý lên máy trạm qua `dong-bo-may` — rủi ro F4, đã chấp nhận (ADR 0004).
- Windows/macOS có áp ràng buộc tên cho CA người dùng tự cài hay không: [Unverified]; Chromium `CACertificatesWithConstraints` và Firefox NSS: [Unverified] trên máy thật.
- Thời hạn: CA trung gian hết hạn mà không ai chạy bộ cài/sao lưu → HTTPS hỏng (đêm sao lưu gia hạn tự động, cảnh báo < 30 ngày trong email).
- Caddy 2.11.6 trở lên có timeout idle mặc định 1 phút: giữ 2.11.4@digest; chỉ nâng sau khi thử `hoi` không stream (~5 phút), tóm tắt PDF, restic tải lớn.

## Hệ quả
Mỗi Box cần `onebee_box_ma_don_vi` + IP tĩnh; đổi một trong hai = xoay CA. Khôi phục toàn bộ giữ nguyên CA (máy trạm không phải làm gì).
