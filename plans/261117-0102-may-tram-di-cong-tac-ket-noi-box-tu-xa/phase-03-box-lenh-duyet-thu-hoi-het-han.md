---
phase: 3
title: "Phase 3: Box — lệnh duyệt, thu hồi, hết hạn"
status: completed
priority: P1
effort: "1,5 ngày"
dependencies: [2]
---

# Phase 3: Box — lệnh duyệt, thu hồi, hết hạn

## Overview

Thêm vào `onebee-box` ba lệnh cho quản trị (`duyet-tu-xa`, `thu-hoi-tu-xa`, `tu-xa`) và một lệnh nội bộ (`tu-xa-ap-dung`) biến danh sách lượt duyệt thành quy tắc tường lửa và `hosts allow` của Samba. Một bộ hẹn giờ tự thu hồi lượt hết hạn. `thu-hoi-may` thu hồi luôn quyền từ xa. Cấu hình in cho máy trạm có thêm địa chỉ từ xa.

## Files to Create / Modify

- Create: `box/ansible/roles/box-stack/templates/onebee-box-tu-xa.sh.j2` (thư viện, nạp như `sao-luu.sh`, `chan-doan.sh`; `onebee-box.sh.j2` đã 678 dòng)
- Create: `box/ansible/roles/box-stack/templates/onebee-tu-xa-het-han.service.j2`, `onebee-tu-xa-het-han.timer.j2`
- Modify: `box/ansible/roles/box-stack/templates/onebee-box.sh.j2` (nạp thư viện, bảng lệnh, phần trợ giúp đầu tệp, `cmd_thu_hoi_may`, `in_cau_hinh_may`)
- Modify: `box/ansible/roles/box-stack/templates/onebee-box-common.sh.j2` (`TU_XA_DIR`, `SAMBA_HOSTS_ALLOW`, `TAILSCALE_KY_THUAT`, `box_ip_tu_xa`)
- Modify: `box/ansible/roles/box-stack/templates/onebee-box-chan-doan.sh.j2`
- Modify: `box/ansible/roles/box-stack/tasks/main.yml` (cài thư viện, bộ hẹn giờ, bước áp dụng cuối bộ cài)
- Create: `tests/box/test_onebee_tu_xa.py`
- Modify: `tests/box/check-diagnosis.sh`

## Trạng thái

Mỗi lượt duyệt là một tệp `/etc/onebee-box/tu-xa/<tên-máy>` (thư mục `0700`, tệp `0600`, chủ `root`), bốn dòng `KHÓA=giá trị`:

```
IP=100.64.0.7
HET_HAN=1794873600        # giây epoch; 0 = không hạn
DUYET_LUC=1793664000
NGUOI_DUYET=box-1         # từ SUDO_USER
```

Đọc bằng `grep` từng khóa và kiểm dạng, không `source`. Thư mục nằm ngoài `${SECRETS}` nên **không** vào bản sao lưu Box: sau `khoi-phuc-toan-bo` mọi máy phải được duyệt lại.

## Lệnh

**`onebee-box duyet-tu-xa <tên-máy> [--ip <IPv4>] [--ngay N] [--dong-y]`**

Dừng với thông báo rõ khi: tên máy sai dạng hoặc chưa cấp (`la_may_da_cap`); HTTPS chưa bật (`https_bat`); Box chưa cài hoặc chưa nối Tailscale (`box_ip_tu_xa` rỗng); `N` ngoài 1 đến 365.

Xác định IP: có `--ip` thì dùng. Không có thì đọc `tailscale status --json` bằng `python3`, lấy các thiết bị có `HostName` bằng tên máy. Không thấy hoặc thấy hơn một thì dừng và yêu cầu `--ip`.

IP phải là IPv4 trong `100.64.0.0/10`, khác IP của Box, không nằm trong `onebee_box_tailscale_cho_phep`, chưa được duyệt cho máy khác.

In tên máy, IP, hệ điều hành và lần thấy cuối của thiết bị, hạn dùng, rồi bắt gõ `duyet` (bỏ qua khi có `--dong-y`, cùng kiểu với `thu-hoi-may`). Ghi tệp trạng thái, gọi `tu_xa_ap_dung`, ghi `logger -t onebee-tu-xa`. Sau đó thử `dong-bo-may <tên-máy>`; nếu máy không ở LAN thì in câu lệnh một dòng để chạy trên máy trạm: `sudo onebee-cong-tac bat --box-tu-xa <IP Tailscale của Box>`.

Chạy lại cho máy đã duyệt nghĩa là đổi hạn hoặc đổi IP. Không có `--ngay` thì lượt duyệt không hạn (`HET_HAN=0`), giữ tới khi thu hồi. <!-- Updated: Validation Session 1 - mặc định không hạn -->

**`onebee-box thu-hoi-tu-xa <tên-máy>`**: xoá tệp trạng thái, `tu_xa_ap_dung`, `conntrack -D -s <IP>` (coi "0 flow entries" là thành công), ghi `logger`. In hai việc còn lại: xoá thiết bị khỏi tailnet trên bảng điều khiển, và `dong-bo-may` khi máy về LAN. Máy không có lượt duyệt thì báo "không có gì để thu hồi" và thoát 0.

**`onebee-box tu-xa`**: bảng tên máy, IP, người duyệt, hạn, còn bao lâu. Không có lượt nào thì in một dòng.

**`onebee-box tu-xa-ap-dung`** (bộ hẹn giờ và bộ cài gọi): dưới khoá `flock /run/onebee-box-tu-xa.lock`:
1. Với mỗi lượt có `HET_HAN` khác 0 và đã qua: xoá tệp, `conntrack -D -s <IP>`, ghi `logger`.
2. Sinh `tuong-lua-tu-xa.conf` (`TU_XA_CHO_PHEP="…"`) và `samba-tu-xa.conf` (`hosts allow = <gốc> <IP máy kỹ thuật> <IP máy công tác>`) vào tệp tạm, so `cmp` với bản đang có.
3. Chỉ khi có tệp đổi: thay tệp, `onebee-tuong-lua bat` (nếu dịch vụ tường lửa đang bật), `smbcontrol all reload-config`, in `đã đổi`.

## Sửa các chỗ có sẵn

- `cmd_thu_hoi_may`: ngay sau dòng đánh dấu thu hồi, gọi phần thân của `thu-hoi-tu-xa` (không hỏi lại).
- `in_cau_hinh_may`: khi máy có lượt duyệt còn hạn **và** HTTPS bật, in thêm `BOX_IP_TU_XA=<box_ip_tu_xa>` và đổi `RESTIC_REPOSITORY` sang `rest:https://<tên>:<mk>@box.<mã>.onebee.internal:<cổng>/<tên>/`. Máy không có lượt duyệt: đầu ra giống hệt hôm nay.
- `dong-bo-may-tram.yml` (dòng 29) đã chấp nhận máy chủ bất kỳ trong URL kho; không phải sửa.
- `onebee-box-chan-doan.sh.j2`, hạng mục mạng, thêm bốn dòng: số máy đang được duyệt từ xa và lượt sắp hết hạn trong 24 giờ; CẢNH BÁO khi có lượt không hạn đã mở quá 30 ngày (kèm tên máy và lệnh thu hồi); CẢNH BÁO khi có lượt duyệt mà Tailscale chưa nối; CẢNH BÁO khi `tailscale debug prefs` báo `RunSSH: true` mà đang có lượt duyệt (kèm gợi ý giới hạn bằng ACL).
- Bộ cài: cuối `box-stack/tasks/main.yml` chạy `onebee-box tu-xa-ap-dung` với `changed_when: "'đã đổi' in stdout"`; bật `onebee-tu-xa-het-han.timer` (`OnCalendar=*:0/15`, `Persistent=true`).

## Implementation Steps

1. Viết `tests/box/test_onebee_tu_xa.py` trước. Dựng lệnh từ mẫu `.j2` vào thư mục tạm như `tests/box/check-diagnosis.sh` đang làm, thay `tailscale`, `conntrack`, `smbcontrol`, `onebee-tuong-lua`, `logger` bằng lệnh giả ghi lại lời gọi. Các bài:
   - duyệt bằng `--ip` ghi đúng bốn dòng trạng thái và sinh đúng hai tệp;
   - duyệt bằng tên máy: đúng một thiết bị khớp thì lấy IP; không khớp hoặc khớp hai thì dừng, không ghi gì;
   - từ chối: máy chưa cấp, HTTPS tắt, IP ngoài `100.64.0.0/10`, IP của máy kỹ thuật, IP đã duyệt cho máy khác, `--ngay 0`, `--ngay 366`;
   - không có `--ngay` thì `HET_HAN=0` và `tu-xa-ap-dung` không bao giờ xoá lượt đó;
   - thu hồi: xoá trạng thái, gọi `conntrack -D -s`, gọi dựng lại tường lửa đúng một lần;
   - `thu-hoi-may` thu hồi luôn quyền từ xa;
   - hết hạn: đặt `HET_HAN` trong quá khứ, `tu-xa-ap-dung` xoá lượt và gọi `conntrack`;
   - chạy `tu-xa-ap-dung` hai lần liền: lần hai không in `đã đổi`, không gọi `onebee-tuong-lua`;
   - `in_cau_hinh_may`: có lượt duyệt thì có `BOX_IP_TU_XA` và URL kho theo tên; không có thì đầu ra y như cũ.
2. Viết `onebee-box-tu-xa.sh.j2`, sửa `common.sh.j2`, `onebee-box.sh.j2`.
3. Thêm hai mẫu đơn vị systemd và các task trong `box-stack/tasks/main.yml`.
4. Sửa `chan-doan` và thêm bốn kịch bản vào `tests/box/check-diagnosis.sh`.
5. Chạy unit test Box, `shellcheck` (kể cả mẫu `.j2` đã dựng), `yamllint`, `ansible-lint`, `python3 tests/kiem-tra-mau-jinja.py`, `python3 scripts/chen-giay-phep.py --kiem`.

## Todo

- [ ] Bài kiểm viết trước, đang trượt
- [ ] Thư viện `onebee-box-tu-xa.sh.j2` và bốn lệnh
- [ ] `thu-hoi-may` gọi thu hồi từ xa
- [ ] `in_cau_hinh_may` in địa chỉ từ xa cho máy đã duyệt
- [ ] Bộ hẹn giờ hết hạn và bước áp dụng cuối bộ cài
- [ ] Bốn dòng mới trong `chan-doan` kèm kịch bản kiểm
- [ ] Phần trợ giúp đầu `onebee-box` có bốn lệnh mới
- [ ] Lint và kiểm dòng giấy phép sạch

## Success Criteria

- `python3 -m unittest tests/box/test_onebee_tu_xa.py` và `tests/box/check-diagnosis.sh` đạt.
- Bộ cài Box chạy lần hai, khi đang có một lượt duyệt, đạt `changed=0 failed=0`.
- `sudo onebee-box tu-xa` trên Box chưa duyệt máy nào in một dòng và thoát 0.

## Rủi ro

- Tìm IP theo tên máy có thể bị thiết bị khác trong tailnet đặt trùng tên lợi dụng (R5). Bước xác nhận in đủ chi tiết thiết bị; tài liệu khuyên dùng `--ip` lấy từ bảng điều khiển khi tailnet có nhiều người quản lý.
- Hạn dùng chính xác tới 15 phút (chu kỳ bộ hẹn giờ). Chấp nhận.
- Mặc định không hạn nên lượt duyệt dễ bị quên (R11): cảnh báo quá 30 ngày trong `chan-doan` là lưới an toàn duy nhất.
- Đồng hồ Box sai làm hạn sai. Box đã đồng bộ giờ qua `systemd-timesyncd`; không thêm gì.
