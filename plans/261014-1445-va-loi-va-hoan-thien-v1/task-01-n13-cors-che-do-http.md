# Task 01 — Vá lỗi N13: CORS ở chế độ HTTP & Siết chặt kiểm thử check-https

**Ưu tiên:** Cao  
**Trạng thái:** Sẵn sàng thực hiện  
**Mã lỗi gốc:** N13 trong `docs/kiem-thu-tren-may-that.md`

---

## 1. Hiện tượng & Nguyên nhân gốc

- **Hiện tượng:** Ở chế độ HTTP (mặc định ban đầu của Box), khi gọi API Open WebUI với một `Origin` bất kỳ (ví dụ: `https://ke-la.example`), máy chủ Open WebUI phản chiếu lại đúng origin đó trong header `Access-Control-Allow-Origin` kèm `Access-Control-Allow-Credentials: true`.
- **Nguyên nhân:** Trong `box/ansible/roles/box-stack/templates/docker-compose.yml.j2` (khoảng dòng 93–98), biến môi trường `CORS_ALLOW_ORIGIN` chỉ được cấu hình trong khối `{% if https %}`. Khi `https` là `false`, biến này không được khai báo, khiến Open WebUI áp dụng cấu hình mặc định là cho phép mọi origin kèm credentials.
- **Rủi ro:** Một trang web lạ người dùng vô tình mở trên trình duyệt của máy trạm có thể gửi yêu cầu cross-origin tới API Open WebUI (cổng 3000) và đọc được dữ liệu nếu cookie xác thực được trình duyệt gửi kèm.
- **Khiếm khuyết kiểm thử:** Trong `tests/box/check-https.sh:53`, câu lệnh kiểm tra:
  ```bash
  ! curl -si -m 10 https://${IP}:3000/api/config -H 'Origin: https://ke-la.example' | grep -qi 'access-control-allow-origin: https://ke-la.example'
  ```
  Nếu lệnh `curl` gặp sự cố (timeout, lỗi mạng, lỗi TLS), lệnh grep trả về khác 0 (không tìm thấy), phủ định `!` biến thành 0 (thành công). Điều này gây ra **kết quả đạt giả**.

---

## 2. Hướng dẫn sửa đổi kỹ thuật

### Bước 1: Sửa template `docker-compose.yml.j2`
**Tệp:** `box/ansible/roles/box-stack/templates/docker-compose.yml.j2`

Thay đổi khối cấu hình môi trường Open WebUI (quanh dòng 93–98):
```jinja2
{% if https %}
      # HTTPS qua Caddy: cookie chỉ gửi qua HTTPS; CORS đúng địa chỉ thật (lệch thì WebSocket chat hỏng mà không báo lỗi)
      WEBUI_SESSION_COOKIE_SECURE: "true"
      WEBUI_AUTH_COOKIE_SECURE: "true"
      CORS_ALLOW_ORIGIN: "https://{{ onebee_box_ip }}:{{ onebee_box_ports.open_webui }};https://box.{{ onebee_box_ma_don_vi }}.onebee.internal:{{ onebee_box_ports.open_webui }}"
{% else %}
      # HTTP nội bộ: chỉ cho phép WebUI tự gọi chính nó, chặn trang web lạ gửi request kèm cookie/credentials
      CORS_ALLOW_ORIGIN: "http://{{ onebee_box_ip }}:{{ onebee_box_ports.open_webui }}"
{% endif %}
```

### Bước 2: Sửa assertion trong `tests/box/check-https.sh`
**Tệp:** `tests/box/check-https.sh`

Tại dòng 53–54, tách thành 2 bước kiểm tra:
1. Xác nhận gọi API thành công (HTTP 200).
2. Xác nhận header `Access-Control-Allow-Origin` KHÔNG chứa origin kẻ lạ.

```bash
  # Trước: ! curl ... | grep -qi ...
  # Sửa thành:
  res=$(curl -si -m 10 https://${IP}:3000/api/config -H 'Origin: https://ke-la.example')
  grep -q "HTTP/.* 200" <<< "$res" || { echo 'FAIL  Không gọi được /api/config qua HTTPS'; exit 1; }
  grep -qi 'access-control-allow-origin: https://ke-la.example' <<< "$res" && { echo 'FAIL  Origin lạ được CORS cho phép'; exit 1; }
```

Đồng thời, thêm bước kiểm tra tương tự cho trường hợp gọi HTTP cổng 3000 (nếu có bài test ở chế độ HTTP).

---

## 3. Kiểm thử hồi quy (Regression Test)

**Tệp:** `tests/box/test_onebee_compose_https.py`

Thêm các ca kiểm thử:
1. `test_cors_o_che_do_http_duoc_gioi_han`:
   - Sinh template với `https: false`.
   - Kiểm tra `CORS_ALLOW_ORIGIN` tồn tại trong output.
   - Giá trị phải khớp định dạng `http://<IP>:3000`.
2. `test_cors_o_che_do_https_van_dung_nhu_cu`:
   - Sinh template với `https: true`.
   - Kiểm tra `CORS_ALLOW_ORIGIN` chứa `https://...` và tên miền `.onebee.internal`.

---

## 4. Lệnh chạy xác minh

```bash
# Chạy unit test kiểm tra template compose
python3 -m unittest tests.box.test_onebee_compose_https

# Chạy kiểm tra mẫu jinja
python3 tests/kiem-tra-mau-jinja.py

# Kiểm tra cú pháp YAML
yamllint box/ansible/roles/box-stack/templates/docker-compose.yml.j2
```

---

## 5. Tiêu chuẩn hoàn thành (Definition of Done)
- [ ] `docker-compose.yml.j2` sinh ra `CORS_ALLOW_ORIGIN` ở cả 2 chế độ `https: true` và `https: false`.
- [ ] Unit test mới viết trong `test_onebee_compose_https.py` vượt qua (`OK`).
- [ ] `tests/box/check-https.sh` kiểm tra mã phản hồi HTTP trước khi grep loại trừ.
- [ ] Không làm gãy bất kỳ bài unit test nào hiện có.
- [ ] Commit theo mẫu: `fix(security): đặt CORS_ALLOW_ORIGIN ở chế độ HTTP và siết kiểm tra test (N13)`.
