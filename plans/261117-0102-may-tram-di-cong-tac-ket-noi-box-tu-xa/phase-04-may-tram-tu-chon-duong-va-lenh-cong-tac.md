---
phase: 4
title: "Phase 4: Máy trạm — tự chọn đường và lệnh công tác"
status: todo
priority: P1
effort: "1,5 ngày"
dependencies: [1]
---

# Phase 4: Máy trạm — tự chọn đường và lệnh công tác

## Overview

Máy trạm tự quyết tên Box trỏ về IP LAN hay IP VPN mỗi khi mạng đổi, không cần người dùng gõ gì (nhân viên không có `sudo`). Kỹ thuật có một lệnh `onebee-cong-tac` để đưa máy vào và ra khỏi tailnet. Máy không có dòng `BOX_IP_TU_XA` hành xử y như 1.3.1.

Giai đoạn này chỉ sửa trong `desktop/` và `tests/desktop/`, làm song song được với Giai đoạn 2 và 3.

## Files to Create / Modify

- Create: `desktop/ansible/roles/ket-noi-box/files/onebee-chon-duong-box` (Python 3, chạy bằng root)
- Create: `desktop/ansible/roles/ket-noi-box/files/onebee-cong-tac` (bash)
- Modify: `desktop/ansible/roles/ket-noi-box/tasks/main.yml`
- Modify: `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-bao-tinh-trang` (dòng 163)
- Modify: `desktop/ansible/roles/quan-ly-tap-trung/files/onebee-chan-doan` (dòng 69)
- Create: `tests/desktop/test_onebee_chon_duong_box.py`, `tests/desktop/test_onebee_cong_tac.py`
- Modify: `tests/desktop/test_onebee_ket_noi_box.py` (lớp kiểm dòng `/etc/hosts`, khoảng dòng 313)

Role `ket-noi-box` được Box gọi lại trong `dong-bo-may-tram.yml`, nên mọi thứ đặt trong role này tự tới máy khi `dong-bo-may`.

## `onebee-chon-duong-box`

Đọc `MAY_TRAM`, `BOX_IP`, `BOX_TEN`, `BOX_IP_TU_XA` từ `/etc/onebee/may-tram.env` bằng cách tách dòng và kiểm dạng (không `source`; cùng biểu thức với các task hiện có). Quy tắc quyết định, theo thứ tự:

| Điều kiện | Dòng `/etc/hosts` có dấu `# onebee-box` |
|---|---|
| `BOX_TEN` hoặc `BOX_IP` thiếu hay sai dạng | Gỡ dòng (đúng hành vi task hiện có) |
| Không có `BOX_IP_TU_XA` hợp lệ | `<BOX_IP> <BOX_TEN>` (y như 1.3.1) |
| Có `BOX_IP_TU_XA`, và bắt tay TLS tới `BOX_IP:443` đạt | `<BOX_IP> <BOX_TEN>` |
| Có `BOX_IP_TU_XA`, bắt tay tới `BOX_IP` không đạt | `<BOX_IP_TU_XA> <BOX_TEN>` |

Bắt tay TLS: `ssl.create_default_context(cafile="/usr/local/share/ca-certificates/onebee-box-ca.crt")`, nối `(BOX_IP, 443)` hết giờ 3 giây, `server_hostname=BOX_TEN`. Đạt nghĩa là máy ở địa chỉ đó trình được chứng chỉ do CA của Box cấp cho đúng tên Box. Thiếu tệp CA thì coi là không đạt.

Nhánh cuối không cần thử IP VPN có tới được không: IP đó chỉ tồn tại trong tailnet, không giả được, nên là giá trị an toàn khi chưa xác thực được LAN.

Ghi tệp: chỉ ghi khi dòng khác dòng đang có; ghi qua tệp tạm rồi `os.replace`, lỗi "Device or resource busy" (trong container, `/etc/hosts` là tệp gắn vào) thì ghi thẳng. In `đã đổi: <cũ> -> <mới>` khi có đổi, không in gì khi giữ nguyên. `--xem` (không cần root) chỉ in đường đang dùng: "mạng văn phòng", "từ xa qua VPN", hoặc "chưa nối Box".

Ba chỗ gọi:
- Task Ansible trong `ket-noi-box` (thay hai task `lineinfile` ở dòng 132-153), `changed_when: "'đã đổi' in stdout"`.
- `/etc/NetworkManager/dispatcher.d/90-onebee-chon-duong-box` cho các sự kiện `up`, `down`, `connectivity-change`, `vpn-up`, `vpn-down`.
- `onebee-chon-duong-box.timer` mỗi 5 phút, phòng khi Tailscale nối xong sau sự kiện mạng.

## `onebee-cong-tac`

- `sudo onebee-cong-tac bat [--khoa <tskey-auth-…>] [--box-tu-xa <IPv4>]`
  1. Chưa có `tailscale`: cài từ kho của Tailscale (khoá và danh sách kho `noble`, cùng cách với `scripts/mo-truy-cap-tu-xa.sh:91-96`).
  2. `tailscale up --reset --hostname="${MAY_TRAM}" --accept-dns=false --accept-routes=false --shields-up --ssh=false`, thêm `--authkey` khi có `--khoa`; không có thì Tailscale in link đăng nhập cho kỹ thuật duyệt.
  3. Có `--box-tu-xa`: kiểm là IPv4 trong `100.64.0.0/10`, ghi hoặc thay dòng `BOX_IP_TU_XA=` trong `may-tram.env` (giữ quyền `0600`). Dùng khi máy đã ở xa và Box không đẩy cấu hình xuống được.
  4. Chạy `onebee-chon-duong-box`, in IP Tailscale của máy và đường đang dùng.
- `sudo onebee-cong-tac tat`: `tailscale logout`, chạy `onebee-chon-duong-box`. Không xoá `BOX_IP_TU_XA`: dòng đó do Box quản lý, `dong-bo-may` sau khi thu hồi sẽ gỡ.
- `onebee-cong-tac xem`: không cần root; in đường đang dùng và trạng thái Tailscale.

Khoá `--khoa` không được ghi vào tệp nào và không xuất hiện trong nhật ký.

## Sửa các chỗ có sẵn

- **Lối tắt thư mục chung** (`ket-noi-box/tasks/main.yml:106-122`): máy có `BOX_IP_TU_XA` hợp lệ thì `Exec=nemo smb://<BOX_TEN>/chung`; máy khác giữ `smb://<BOX_IP>/chung`. `onebee-loi-tat-chia-se` có sẵn tự làm mới lối tắt trên màn hình nền khi bản gốc đổi. Người dùng phải nhập lại mật khẩu thư mục chung một lần vì địa chỉ đổi.
- **`onebee-bao-tinh-trang:163`**: `ip_toi_box` nhận địa chỉ mà `BOX_TEN` đang phân giải ra, lùi về `BOX_IP` khi không phân giải được. Ở xa, máy sẽ báo IP Tailscale của nó. Node-RED chỉ kiểm trường `ip` là IPv4 (`onebee-quy-trinh.js:288`), không phải sửa phía Box.
- **`onebee-chan-doan:69`** (máy trạm): kiểm tới Box theo `BOX_TEN`, thêm một dòng "Đường tới Box".
- `authorized_keys` với `from="<BOX_IP>"` giữ nguyên (ngoài phạm vi).

## Implementation Steps

1. Viết `tests/desktop/test_onebee_chon_duong_box.py` trước. Dựng CA thử và một máy chủ TLS cục bộ (dùng lại cách dựng trong `tests/desktop/test_onebee_clients_https.py`), cho phép đổi đường dẫn `may-tram.env`, `/etc/hosts`, tệp CA và cổng qua biến môi trường. Các bài:
   - không có `BOX_IP_TU_XA`: dòng LAN, giống bản cũ;
   - có `BOX_IP_TU_XA`, máy chủ TLS trình chứng chỉ đúng: dòng LAN;
   - có `BOX_IP_TU_XA`, không ai nghe ở IP LAN: dòng VPN;
   - có `BOX_IP_TU_XA`, máy chủ trình chứng chỉ của CA khác: dòng VPN;
   - có `BOX_IP_TU_XA`, chứng chỉ đúng CA nhưng sai tên: dòng VPN;
   - chạy hai lần: lần hai không in `đã đổi`, thời điểm sửa tệp không đổi;
   - `BOX_TEN` sai dạng: gỡ dòng; các dòng khác trong `/etc/hosts` còn nguyên;
   - `BOX_IP_TU_XA="1.2.3.4"` (ngoài `100.64.0.0/10`) bị coi là không có.
2. Viết `tests/desktop/test_onebee_cong_tac.py` với `tailscale`, `apt-get`, `curl` giả: cờ của `tailscale up` đúng và đủ; `--khoa` không lọt vào tệp nào; `--box-tu-xa` ghi đúng một dòng và từ chối IP ngoài dải; `tat` không xoá `BOX_IP_TU_XA`; `xem` chạy được không cần root.
3. Viết hai tệp lệnh, sửa role `ket-noi-box`, cập nhật `test_onebee_ket_noi_box.py`.
4. Sửa `onebee-bao-tinh-trang` và `onebee-chan-doan`, bổ sung bài kiểm tương ứng trong `tests/desktop/`.
5. Chạy `python3 -m unittest discover -s tests/desktop -p 'test_*.py'`, `shellcheck`, `yamllint`, `ansible-lint`, `python3 scripts/chen-giay-phep.py --kiem`.

## Todo

- [ ] Hai tệp kiểm mới viết trước, đang trượt
- [ ] `onebee-chon-duong-box` đạt tám bài
- [ ] `onebee-cong-tac` đạt bài kiểm
- [ ] Role `ket-noi-box`: cài hai lệnh, dispatcher, bộ hẹn giờ; bỏ hai task `lineinfile`
- [ ] Lối tắt thư mục chung theo tên khi máy có `BOX_IP_TU_XA`
- [ ] `onebee-bao-tinh-trang` và `onebee-chan-doan` theo tên Box
- [ ] Toàn bộ `tests/desktop` đạt, lint sạch

## Success Criteria

- `python3 -m unittest discover -s tests/desktop -p 'test_*.py'` đạt, không bài cũ nào phải nới.
- Bộ cài máy trạm chạy lần hai đạt `changed=0 failed=0`, cả khi máy có lẫn không có `BOX_IP_TU_XA`.
- Máy không có `BOX_IP_TU_XA`: `/etc/hosts`, lối tắt và `RESTIC_REPOSITORY` sau khi cài giống hệt 1.3.1.

## Rủi ro

- Hai nơi cùng ghi dòng `/etc/hosts` sẽ làm bộ cài báo `changed` mãi (R9). Vì vậy bỏ hẳn hai task `lineinfile`, chỉ còn công cụ chọn đường ghi.
- Dispatcher chạy bằng root trên mọi sự kiện mạng: công cụ không nhận tham số từ sự kiện, không `source` tệp cấu hình, hết giờ 3 giây cho phép thử TLS.
- `--shields-up` chặn kết nối vào máy, kể cả hỗ trợ từ xa của kỹ thuật. Đã ghi ở Ngoài phạm vi.
- Mint 22 dùng kho `noble`; bản Mint khác tên mã thì bước cài Tailscale phải dừng với thông báo rõ, không đoán.
