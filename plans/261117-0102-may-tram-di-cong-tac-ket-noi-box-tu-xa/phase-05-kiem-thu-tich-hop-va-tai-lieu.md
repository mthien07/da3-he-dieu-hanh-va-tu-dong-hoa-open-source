---
phase: 5
title: "Phase 5: Kiểm thử tích hợp và tài liệu"
status: in-progress
priority: P1
effort: "1,5 ngày"
dependencies: [2, 3, 4]
---

# Phase 5: Kiểm thử tích hợp và tài liệu

## Overview

Chứng minh toàn bộ luồng bằng tường lửa thật: trong container của CI (không cần tài khoản Tailscale) và trên hai máy ảo thật qua một tailnet thử. Viết hướng dẫn cho kỹ thuật và cập nhật các tài liệu đang nói khác đi.

## Files to Create / Modify

- Modify: `tests/box/run-box-test-in-systemd-container.sh` (kịch bản máy công tác)
- Modify: `tests/box/verify-box-install.sh`, `tests/README.md`
- Create: `docs/huong-dan/may-tram-di-cong-tac.md`
- Modify: `docs/huong-dan/cai-dat-onebee-box.md` (mục tường lửa dòng 28-37, bảng lệnh dòng 173)
- Modify: `docs/huong-dan/quan-ly-may-tram.md`, `docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md` (Phần 9 và Phụ lục lệnh)
- Modify: `docs/adr/0008-may-tram-di-cong-tac-qua-vpn.md` (trạng thái sau khi thử), `CHANGELOG.md`
- Create: `plans/reports/<ngày>-kiem-thu-may-di-cong-tac.md`

## Kịch bản trong container (chạy trong CI `box=true`)

Tailscale thật không chạy được trong CI. Thay bằng một cặp `veth` mà đầu phía Box tên đúng là `tailscale0`, đầu kia nằm trong không gian mạng `may-xa` với IP `100.64.0.7`, cùng một lệnh `tailscale` giả trả IP và danh sách thiết bị. Tường lửa, Docker, Caddy, Samba đều là thật.

| # | Bước | Mong đợi |
|---|---|---|
| C1 | Chưa duyệt: từ `may-xa` thử cổng 443, 445, 8000, 22, 3001 | Cả năm hết giờ |
| C2 | `onebee-box duyet-tu-xa may-thu --ip 100.64.0.7 --ngay 1 --dong-y` | Thoát 0; `tu-xa` liệt kê máy |
| C3 | Từ `may-xa`: `curl` tới `https://box.<mã>…/` (ép phân giải về IP phía Box), cổng 8000, `smbclient` tới 445 | Cả ba tới được |
| C4 | Từ `may-xa`: cổng 22, 3001, 80, 139 | Hết giờ |
| C5 | Thêm IP thứ hai `100.64.0.8` vào `may-xa`, thử 443 từ IP đó | Hết giờ |
| C6 | Mở một kết nối `curl` giữ lâu và một phiên `smbclient`, rồi `thu-hoi-tu-xa may-thu` | Cả hai đứt trong 5 giây; kết nối mới hết giờ |
| C7 | Duyệt lại, sửa `HET_HAN` về quá khứ, chạy `onebee-box tu-xa-ap-dung` | Lượt bị xoá; 443 hết giờ |
| C8 | Duyệt lại, `systemctl restart docker`, rồi khởi động lại dịch vụ tường lửa | Sau mỗi lần, C3 và C4 vẫn đúng |
| C9 | Duyệt lại, `thu-hoi-may may-thu --dong-y` | Quyền từ xa mất cùng lúc |
| C10 | Chạy lại bộ cài Box khi đang có một lượt duyệt | `changed=0 failed=0`; lượt duyệt còn nguyên |
| C11 | Duyệt không có `--ngay`, chạy `tu-xa-ap-dung`; rồi sửa `DUYET_LUC` lùi 31 ngày, chạy `chan-doan` | Lượt còn nguyên; `chan-doan` có CẢNH BÁO lượt không hạn quá 30 ngày |

## Kịch bản trên máy ảo thật

Box thật (`192.168.100.127`) và VM `onebee-mint-may-sach` trong một tailnet thử có ACL mẫu. Chụp snapshot cả hai trước khi bắt đầu. Box phải bật HTTPS trước (`onebee_box_https: true`).

| # | Bước | Mong đợi |
|---|---|---|
| T1 | Trên Mint: `sudo onebee-cong-tac bat` | Vào tailnet, tên thiết bị bằng `MAY_TRAM` |
| T2 | Trên Box: `sudo onebee-box duyet-tu-xa ketoan-01 --ngay 1` | Tự tìm đúng IP, hỏi xác nhận, tự `dong-bo-may`; `may-tram.env` trên Mint có `BOX_IP_TU_XA` |
| T3 | Mint còn trong LAN: `onebee-cong-tac xem` | "mạng văn phòng"; `/etc/hosts` trỏ IP LAN |
| T4 | Chuyển card mạng của VM Mint sang NAT (ra khỏi LAN của Box) | Trong 5 phút `/etc/hosts` trỏ IP Tailscale của Box; `xem` báo "từ xa qua VPN" |
| T5 | `hoi xin chào`; mở lối tắt thư mục chung, chép một tệp 50 MB; tải một tệp lên kho tệp; `sudo onebee-sao-luu`; chờ một lượt báo tình trạng | Tất cả đạt; `sudo onebee-box may-tram` thấy máy với IP `100.x` |
| T6 | Từ Mint: `nc -zv` tới cổng 22, 80, 3001 của IP Tailscale Box; mở `/quy-trinh/` bằng tài khoản nhóm `nhan_vien` | Ba cổng hết giờ; `/quy-trinh/` bị từ chối |
| T7 | Thêm một thiết bị thứ ba vào tailnet, chưa duyệt | Không tới được cổng nào của Box |
| T8 | Đang chép tệp lớn qua SMB, trên Box `thu-hoi-tu-xa ketoan-01` | Chép đứt trong 5 giây; `hoi` báo không kết nối được |
| T9 | Duyệt lại; chuyển card mạng Mint về LAN của Box | Trong 5 phút `/etc/hosts` trỏ lại IP LAN, không ai gõ lệnh nào |
| T10 | Dựng một máy giả ở IP LAN của Box trong mạng NAT, trình chứng chỉ tự ký | Mint **không** chọn IP đó, vẫn dùng IP VPN |
| T11 | Chạy lại bộ cài máy trạm và bộ cài Box | Cả hai `changed=0 failed=0` |
| T12 | `sudo onebee-box chan-doan` trên Box | Có dòng máy đang được duyệt từ xa; không lỗi mới so với trước |

Sau khi thử: thu hồi, `sudo onebee-cong-tac tat`, xoá ba thiết bị khỏi tailnet thử, trả card mạng về như cũ.

## Tài liệu

`docs/huong-dan/may-tram-di-cong-tac.md` (cho kỹ thuật, theo giọng các hướng dẫn hiện có):
1. Khi nào dùng và cần gì trước: Box đã bật HTTPS, Box đã vào tailnet của đơn vị, máy đã cấp bằng `them-may`.
2. Đặt ACL của tailnet một lần. Mẫu:
   ```json
   {
     "tagOwners": {"tag:box": ["autogroup:admin"], "tag:kythuat": ["autogroup:admin"], "tag:congtac": ["autogroup:admin"]},
     "acls": [
       {"action": "accept", "src": ["tag:kythuat"], "dst": ["tag:box:22,80,443,445,3001,8000"]},
       {"action": "accept", "src": ["tag:congtac"], "dst": ["tag:box:443,445,8000"]}
     ],
     "ssh": [
       {"action": "check", "src": ["tag:kythuat"], "dst": ["tag:box"], "users": ["autogroup:nonroot", "root"]}
     ]
   }
   ```
   Cú pháp ACL phải đối chiếu lại với tài liệu Tailscale lúc viết hướng dẫn và thử trên tailnet ở bước T1.
3. Trước chuyến đi, trong lúc đi, khi về, khi mất máy: đúng bốn luồng trong `plan.md`.
4. Máy đã đi mà chưa chuẩn bị.
5. Giới hạn: lượt duyệt mặc định không hạn nên phải nhớ thu hồi; không cập nhật và không hỗ trợ từ xa tới máy đang đi; sao lưu qua 4G tốn dung lượng; mật khẩu thư mục chung dùng chung; nên mã hóa ổ đĩa laptop.
6. Bảng sự cố: `hoi` báo không kết nối được, thư mục chung hỏi mật khẩu lại, lượt duyệt hết hạn giữa chuyến đi.

Sửa `cai-dat-onebee-box.md`: câu ở dòng 35 về máy kỹ thuật và thư mục chung cho đúng với kết quả U4; thêm bốn lệnh mới vào bảng lệnh. `CHANGELOG.md`: mục mới cho bản 1.4.0 và nâng `onebee_box_version`, `onebee_version` lên `1.4.0` (bài `tests/desktop/test_onebee_phien_ban.py` đòi hai số khớp nhau).

## Implementation Steps

1. Thêm C1 đến C11 vào `run-box-test-in-systemd-container.sh`, theo kiểu `PASS`/`FAIL` có sẵn.
2. Mở PR, chạy CI thường rồi `gh workflow run ci.yml --ref <nhánh> -f box=true`.
3. Chạy T1 đến T12 trên hai máy ảo, ghi lệnh và đầu ra thật vào báo cáo kiểm thử, kèm ảnh chụp bước T4, T5, T9.
4. Viết hướng dẫn mới, sửa bốn tài liệu, cập nhật ADR 0008 và `CHANGELOG.md`.
5. Kiểm mọi liên kết và mọi câu lệnh trong tài liệu khớp với lệnh thật (`onebee-box` in phần trợ giúp).

## Todo

- [ ] C1 đến C11 đạt trong CI `box=true`
- [x] T1 đến T12 chạy thật, có báo cáo (`plans/reports/261117-kiem-thu-may-di-cong-tac.md`)
- [x] Hướng dẫn `may-tram-di-cong-tac.md`
- [x] Bốn tài liệu cũ đã sửa, ADR 0008 cập nhật trạng thái
- [ ] `CHANGELOG.md` và số phiên bản 1.4.0
- [ ] Hai máy ảo và tailnet thử đã dọn

## Success Criteria

- CI của PR xanh, lượt `box=true` xanh.
- Báo cáo kiểm thử có đủ 12 dòng T, mỗi dòng Đạt hoặc Trượt kèm đầu ra thật; dòng nào chưa chạy được ghi rõ lý do.
- Bảy tiêu chí thành công trong `plan.md` đều có bằng chứng trỏ tới một dòng C hoặc T.

## Rủi ro

- Bài kiểm trong container dùng `veth` tên `tailscale0`, không có tailscaled thật chèn chuỗi `ts-input`. Phần tương tác với tailscaled chỉ được chứng minh ở T1 đến T12.
- Bật HTTPS trên Box thật là thay đổi lớn với Box đó: làm trên snapshot, và ghi rõ trong báo cáo Box đã ở trạng thái nào trước khi thử.
- Chưa kiểm trên máy vật lý và trên mạng 4G thật; báo cáo phải nói rõ.
