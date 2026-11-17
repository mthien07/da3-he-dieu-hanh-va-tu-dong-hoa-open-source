---
phase: 1
title: "Phase 1: Quyết định kiến trúc và xác minh giả định"
status: completed
priority: P1
effort: "0,5 ngày"
dependencies: []
---

# Phase 1: Quyết định kiến trúc và xác minh giả định

## Overview

Ghi sáu quyết định thành ADR 0008 và thử tay tám giả định kỹ thuật mà kế hoạch dựa vào nhưng chưa ai chạy thật. Giai đoạn này không sửa mã sản phẩm. Kết quả của nó quyết định Giai đoạn 2 đến 4 làm đúng như viết hay phải đổi.

## Requirements

- [ ] ADR `docs/adr/0008-may-tram-di-cong-tac-qua-vpn.md` theo đúng khuôn các ADR 0004, 0005: Bối cảnh, Quyết định (6 mục trong `plan.md`, mục 6 theo lựa chọn của anh: mặc định không hạn), Phương án đã cân nhắc (subnet route /32, WireGuard thuần, Headscale), Rủi ro còn lại, Hệ quả. Trạng thái "Đề xuất, chưa thử trên máy thật".
- [ ] Bảng kết quả tám phép thử dưới đây, ghi vào `plans/reports/261117-xac-minh-gia-dinh-may-di-cong-tac.md`, mỗi dòng có lệnh đã chạy và đầu ra thật.

## Tám giả định phải thử

Môi trường: Box thật (VM `192.168.100.127`, đã ở 1.3.1) và VM `onebee-mint-may-sach`, cả hai vào một tailnet thử. Chụp snapshot VM trước khi thử. Mọi thay đổi tay trên Box phải gỡ lại sau khi thử.

| # | Giả định | Cách thử | Đạt khi |
|---|---|---|---|
| U1 | Ở `mangle/PREROUTING`, cổng đích của gói tới container vẫn là cổng **trước DNAT** (443, 8000) | Thêm tay quy tắc `-s <IP máy thử> -p tcp -m multiport --dports 443,445,8000 -j RETURN` vào `ONEBEE-TAILSCALE`, bỏ IP đó khỏi danh sách mọi cổng | `curl https://box.<mã>…/` và cổng 8000 tới được; cổng 3001 và 22 hết giờ |
| U2 | `-m conntrack --ctorigdstport 443` khớp được trong `DOCKER-USER` (sau DNAT) | Thêm quy tắc đó vào `ONEBEE-LAN-DOCKER`, xem bộ đếm `iptables -vnL` | Bộ đếm tăng khi máy thử mở cổng 443 |
| U3 | Samba nhận `include =` đặt **trong khối thư mục chung** và `hosts allow` trong tệp include đè giá trị phía trên | Tạo tệp include tay, `testparm -s`, `smbcontrol all reload-config` | `testparm` in `hosts allow` mới; máy thử nối được 445, máy khác trong tailnet bị từ chối |
| U4 | Hiện tại Samba từ chối nguồn `100.x` (kể cả máy kỹ thuật đã khai) | Từ máy kỹ thuật qua Tailscale: `smbclient -L //<IP Tailscale Box> -U onebee` | Bị từ chối trước khi sửa. Nếu **không** bị từ chối thì bỏ hạng mục "sửa `hosts allow` cho máy kỹ thuật" ở Giai đoạn 2 |
| U5 | `conntrack -D -s <IP>` làm đứt kết nối TCP đang mở (gói giữa chừng bị coi là `NEW` rồi bị DROP) | Mở phiên SMB đang chép tệp lớn và một `curl` tải chậm, gỡ IP khỏi danh sách, chạy `conntrack -D` | Cả hai đứt trong 5 giây. Nếu không: đổi thiết kế sang quy tắc DROP mọi trạng thái cho IP bị thu hồi |
| U6 | `tailscale status --json` trên Box có `Peer[].HostName` và `Peer[].TailscaleIPs` của máy trạm khi ACL chỉ cho `tag:congtac → tag:box` | Chạy lệnh, đọc JSON | Thấy đúng một mục có `HostName` bằng tên máy và một IPv4 `100.x` |
| U7 | `tailscale up --shields-up --accept-dns=false --accept-routes=false` trên máy trạm vẫn gọi ra Box được; `resolv.conf` không đổi | Chạy trên VM Mint | `hoi` và SMB chạy; `resolv.conf` y nguyên; từ Box `nc -zv <IP máy> 22` hết giờ |
| U8 | Nemo mở `smb://box.<mã>.onebee.internal/chung` qua dòng `/etc/hosts`; đọc được trạng thái Tailscale SSH của Box | Mở trong Nemo; trên Box `tailscale debug prefs` | Nemo hỏi mật khẩu rồi mở được; đầu ra có trường `RunSSH` |

## Implementation Steps

1. Viết ADR 0008 từ mục Kiến trúc của `plan.md`.
2. Dựng tailnet thử, đưa Box thật và VM Mint vào. Chụp snapshot hai VM.
3. Chạy U1 đến U8 theo thứ tự, ghi lệnh và đầu ra thật vào báo cáo. Giả định nào trượt thì ghi rõ và đề xuất thay thế ngay trong báo cáo.
4. Gỡ mọi quy tắc và tệp thử tay trên Box (`sudo onebee-tuong-lua bat` dựng lại từ đầu; xoá tệp include thử; `systemctl reload smbd`).
5. Cập nhật `plan.md` và các tệp giai đoạn nếu có giả định trượt, trước khi sang Giai đoạn 2.

## Todo

- [ ] ADR 0008 viết xong
- [ ] U1, U2 (tường lửa theo cổng)
- [ ] U3, U4 (Samba)
- [ ] U5 (cắt kết nối đang mở)
- [ ] U6, U7, U8 (Tailscale và Nemo)
- [ ] Box thật trả về trạng thái trước khi thử, `sudo onebee-box chan-doan` không thêm lỗi mới
- [ ] Báo cáo xác minh có đủ tám dòng

## Success Criteria

- Tám giả định đều có kết luận Đạt hoặc Trượt kèm đầu ra lệnh thật; không dòng nào để trống.
- Giả định trượt đã có phương án thay và kế hoạch đã sửa theo.
- `sudo onebee-tuong-lua xem` trên Box sau khi dọn giống hệt trước khi thử.

## Rủi ro

- Thử trên Box thật có thể khoá mất đường SSH qua Tailscale. Giữ một phiên SSH qua LAN mở suốt lúc thử và có snapshot để quay lại.
- Tailnet thử dùng tài khoản cá nhân: xoá hai thiết bị khỏi tailnet sau khi thử.
