---
phase: 2
title: "Phase 2: Box — tường lửa theo cổng và Samba cho máy từ xa"
status: completed
priority: P1
effort: "1 ngày"
dependencies: [1]
---

# Phase 2: Box — tường lửa theo cổng và Samba cho máy từ xa

## Overview

Dạy tường lửa Box một loại nguồn mới: "máy công tác", chỉ được ba cổng TCP. Cho Samba nhận đúng các IP đó. Giai đoạn này chưa có lệnh quản trị; danh sách IP đọc từ một tệp mà Giai đoạn 3 sẽ sinh ra. Tệp trống hoặc không có thì Box hành xử y như 1.3.1.

## Files to Create / Modify

- Modify: `box/ansible/roles/box-firewall/files/onebee-tuong-lua`
- Modify: `box/ansible/roles/box-firewall/templates/tuong-lua.conf.j2`
- Modify: `box/ansible/roles/box-firewall/tasks/main.yml` (cài gói `conntrack`)
- Modify: `box/ansible/roles/samba/tasks/main.yml`
- Modify: `tests/box/test_onebee_tuong_lua.py`
- Modify: `tests/box/verify-box-install.sh` (kiểm Samba có dòng include)

## Requirements

- [ ] Biến mới trong `onebee-tuong-lua`: `TU_XA_CHO_PHEP=""` (IPv4 đơn, cách nhau dấu phẩy) và `CONG_TU_XA="443,445,8000"`.
- [ ] `tuong-lua.conf.j2` thêm `CONG_TU_XA="443,445,{{ onebee_box_ports.rest_server }}"`. Không đưa `TU_XA_CHO_PHEP` vào đây: nó là trạng thái vận hành, không phải cấu hình trong `group_vars`.
- [ ] Sau khi nạp `CONF`, nạp thêm `${ONEBEE_TU_XA_CONF:-/etc/onebee-box/tuong-lua-tu-xa.conf}` nếu có. Trước khi dùng, lọc `TU_XA_CHO_PHEP` bằng biểu thức IPv4 đơn; mục sai dạng bị bỏ và in cảnh báo ra stderr, không dừng dựng tường lửa.
- [ ] Ba chỗ thêm quy tắc, chỉ cho `iptables` (IPv4). `ip6tables` không nhận máy công tác.
- [ ] IP nằm trong cả `TAILSCALE_CHO_PHEP` lẫn `TU_XA_CHO_PHEP` thì quyền máy kỹ thuật thắng (quy tắc mọi cổng đứng trước).
- [ ] Samba đọc `hosts allow` cuối cùng từ `/etc/onebee-box/samba-tu-xa.conf`.

## Quy tắc tường lửa thêm vào

Với mỗi `<ip>` trong `TU_XA_CHO_PHEP`, trong hàm `dung()`:

```
# mangle/ONEBEE-TAILSCALE — lớp quyết định, cổng còn là cổng trước DNAT. Đặt SAU các dòng máy kỹ thuật, TRƯỚC dòng DROP cuối
-t mangle -A ONEBEE-TAILSCALE -s <ip> -p tcp -m multiport --dports ${CONG_TU_XA} -j RETURN

# filter/ONEBEE-LAN-BOX (INPUT, chỉ tới đây với cổng 22,139,445) — chỉ 445 khớp
-A ONEBEE-LAN-BOX -i tailscale0 -s <ip> -p tcp -m multiport --dports ${CONG_TU_XA} -j RETURN

# filter/ONEBEE-LAN-DOCKER (DOCKER-USER, sau DNAT) — một dòng cho mỗi cổng, khớp theo cổng gốc
-A ONEBEE-LAN-DOCKER -i tailscale0 -s <ip> -p tcp -m conntrack --ctorigdstport <cổng> -j RETURN
```

Thứ tự dựng giữ nguyên nguyên tắc hiện có: chuỗi `filter` dựng trước, `mangle` dựng sau, để `mangle` lỗi thì LAN vẫn được lọc. Nếu U2 ở Giai đoạn 1 trượt, dòng `ONEBEE-LAN-DOCKER` đổi thành `-i tailscale0 -s <ip> -p tcp -j RETURN` và ghi chú rằng `mangle` là lớp duy nhất lọc theo cổng.

## Samba

1. Trong khối thư mục chung (`blockinfile` có sẵn), thêm dòng cuối: `include = /etc/onebee-box/samba-tu-xa.conf`.
2. Thêm task tạo tệp đó nếu chưa có (`copy` với `force: false`), nội dung một dòng: `hosts allow = {{ onebee_box_samba_hosts_allow }}`. `force: false` để chạy lại bộ cài không xoá danh sách đang có. Giai đoạn 3 thêm lệnh sinh lại tệp này.
3. Nếu U4 ở Giai đoạn 1 xác nhận Samba đang từ chối máy kỹ thuật: nội dung sinh ra gồm cả các IPv4 trong `onebee_box_tailscale_cho_phep`. Việc này sửa đúng điều tài liệu đã hứa, không mở thêm ai.
4. `validate: testparm -s %s` giữ nguyên cho `smb.conf`.

## Implementation Steps

1. Viết bài kiểm trước, trong `tests/box/test_onebee_tuong_lua.py` (dùng `iptables` giả có sẵn trong tệp):
   - `test_may_cong_tac_chi_duoc_ba_cong_o_mangle`: có đúng một dòng `-s 100.64.0.7 -p tcp -m multiport --dports 443,445,8000 -j RETURN` trong `mangle/ONEBEE-TAILSCALE`, và **không** có dòng `-s 100.64.0.7 -j RETURN` trần.
   - `test_may_cong_tac_dung_sau_may_ky_thuat_va_truoc_drop`: thứ tự dòng trong chuỗi.
   - `test_may_cong_tac_khong_co_trong_ip6tables`.
   - `test_filter_box_va_docker_co_quy_tac_theo_cong`: `ONEBEE-LAN-BOX` có dòng multiport; `ONEBEE-LAN-DOCKER` có một dòng `--ctorigdstport` cho mỗi cổng.
   - `test_khong_co_tep_tu_xa_thi_giong_ban_cu`: so toàn bộ quy tắc với lúc chưa có tính năng.
   - `test_muc_sai_dang_bi_bo_khong_dung_tuong_lua`: `TU_XA_CHO_PHEP="100.64.0.7,; rm -rf /,10.0.0.0/8"` chỉ còn `100.64.0.7`.
   - `test_chay_lai_khong_nhan_doi_quy_tac_tu_xa`.
2. Sửa `onebee-tuong-lua`: thêm tham số thứ năm cho `dung()`, hàm lọc IPv4, ba chỗ thêm quy tắc, dòng thông báo cuối của `bat` in thêm danh sách máy công tác.
3. Sửa `tuong-lua.conf.j2`, thêm gói `conntrack` vào `box-firewall/tasks/main.yml`.
4. Sửa role `samba` theo mục Samba ở trên.
5. Chạy `python3 -m unittest tests/box/test_onebee_tuong_lua.py`, `shellcheck`, `yamllint`, `ansible-lint`, `python3 tests/kiem-tra-mau-jinja.py`.

## Todo

- [ ] Bảy bài kiểm mới viết xong và đang trượt (chưa có mã)
- [ ] `onebee-tuong-lua` nhận `TU_XA_CHO_PHEP`, bảy bài kiểm đạt, chín bài cũ vẫn đạt
- [ ] `tuong-lua.conf.j2` có `CONG_TU_XA`
- [ ] Gói `conntrack` được cài
- [ ] Samba có `include` và tệp mặc định
- [ ] Lint sạch

## Success Criteria

- `python3 -m unittest tests/box/test_onebee_tuong_lua.py` đạt toàn bộ (16 bài).
- Không có tệp `tuong-lua-tu-xa.conf`: đầu ra `onebee-tuong-lua xem` giống hệt bản 1.3.1.
- `testparm -s` không báo lỗi; chạy bộ cài Box lần hai đạt `changed=0`.

## Rủi ro

- Sửa tường lửa sai có thể khoá mất SSH. Nguyên tắc "dựng `filter` trước, `mangle` sau" và bài `test_mangle_loi_thi_van_chan_lan_khong_mo_toang` có sẵn phải tiếp tục đạt.
- `include` trong khối thư mục chung là hành vi cần U3 xác nhận. Nếu trượt, thay bằng cách cho lệnh ở Giai đoạn 3 sửa thẳng dòng `hosts allow` trong `smb.conf` giữa hai dấu mốc riêng.
