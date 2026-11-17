# ADR 0008 — Máy trạm đi công tác kết nối Box từ xa

- Ngày: 17/11/2026 · Trạng thái: Chấp nhận cho 2.0.0 — đã thử trên Box thật, máy Mint thật và tailnet thật ngày 17/11/2026 (`plans/reports/261117-kiem-thu-may-di-cong-tac.md`)

## Bối cảnh
Một máy trạm OneBee đem ra ngoài văn phòng vẫn cần dùng thư mục chung (Samba), kho tệp (`/files/`), Trợ lý AI (`hoi`), sao lưu (restic) và báo tình trạng. Ràng buộc: **không mở cổng nào trên router**; Box duyệt **từng máy, từng cổng**; thu hồi phải cắt cả kết nối đang mở; người dùng cuối (không có `sudo`) không phải làm gì khi đổi mạng. Cơ chế hỗ trợ từ xa hiện có (ADR 0004) là người dùng chủ động mở từng lần, không dùng được cho hằng ngày.

## Quyết định
1. **VPN là Tailscale trên tailnet của đơn vị** (nối tiếp ADR 0004). WireGuard thuần và Headscale tự dựng đều cần một cổng công khai — trái yêu cầu.
2. **Tường lửa của Box là lớp quyết định**, theo từng IP và từng cổng; ACL của tailnet là lớp thứ hai. Tài khoản quản trị tailnet bị chiếm thì thêm được thiết bị, nhưng thiết bị đó vẫn không qua được tường lửa Box. Máy công tác chỉ được TCP 443, 445, 8000; máy kỹ thuật giữ quyền như cũ.
3. **Mọi dịch vụ đi theo tên Box** (`box.<mã>.onebee.internal`), chỉ một dòng `/etc/hosts` đổi giữa IP LAN và IP VPN. Không URL nào chứa IP VPN, nên không đụng tới CA (ADR 0005) — chứng chỉ hợp lệ sẵn qua VPN.
4. **Máy tự chọn đường**: thấy Box thật trong LAN (bắt tay TLS với CA đã ghim tới `BOX_IP:443`) thì dùng IP LAN; không thì dùng IP VPN. IP VPN chỉ tới được trong tailnet nên không giả được.
5. **Cần HTTPS đã bật** (`onebee_box_https: true`, ADR 0005). Không có HTTPS thì Trợ lý AI vốn không chạy và máy không có cách xác thực Box trong mạng lạ.
6. **Lượt duyệt mặc định không hạn**, giữ tới khi kỹ thuật thu hồi; thêm `--ngay N` (1 đến 365) thì hết hạn tự thu hồi. `chan-doan` cảnh báo lượt không hạn đã mở quá 30 ngày. Trạng thái lượt duyệt nằm ngoài vùng sao lưu Box: sau khôi phục toàn bộ phải duyệt lại (đóng mặc định).

Phân quyền (tường lửa + SSO):

| Cổng / tuyến | Máy công tác | Máy kỹ thuật |
|---|---|---|
| 443: trang chủ, `/ai/`, `/files/`, `/api/`, Sổ điều hành, `/webhook/` | Có | Có |
| 445: thư mục chung (SMB 3.1.1, bắt buộc mã hóa) | Có | Có (sau khi sửa `hosts allow`) |
| 8000: kho sao lưu | Có | Có |
| 22 SSH, 3001 Giám sát, 80, 139, UDP 137/138 | **Chặn ở tường lửa** | Có |
| `/quy-trinh/` (Node-RED), trang giám sát | Tới được cổng 443 nhưng **bị SSO hai lớp chặn**: chỉ nhóm `ky_thuat`/`quan_ly` | Có, sau SSO hai lớp |

## Phương án đã cân nhắc
| Phương án | Vì sao chưa chọn |
|---|---|
| Quảng bá IP LAN của Box (/32) qua Tailscale subnet route | Máy trạm không phải đổi gì, nhưng phụ thuộc bước duyệt tuyến trên bảng điều khiển Tailscale, không kiểm được trong CI, và không xác thực được Box khi mạng lạ trùng dải với văn phòng |
| WireGuard thuần | Cần một cổng công khai trên router — trái yêu cầu |
| Headscale tự dựng | Cũng cần cổng công khai; thêm một dịch vụ tự vận hành |

## Rủi ro còn lại (chấp nhận, đã ghi)
- **Kết nối đang mở sống sót sau thu hồi**: quy tắc tường lửa hiện chỉ lọc `--ctstate NEW` → thu hồi và hết hạn chạy `conntrack -D -s <IP>` **sau khi** tường lửa đã dựng lại không còn IP đó (làm ngược thì gói kế tiếp tạo lại mục conntrack khi luật cũ còn cho qua). Đã thử thật: phiên SMB đang chép đứt khoảng 4 giây sau lệnh thu hồi.
- **Tailscale SSH đi vòng tường lửa Box** (tailscaled nhận cổng 22 trước iptables): ACL mẫu không có mục `ssh` cho `tag:congtac`; `chan-doan` cảnh báo khi Box bật Tailscale SSH mà còn lượt duyệt.
- **Samba một mật khẩu chung** (ADR 0004): thu hồi ở tầng mạng (tường lửa + `hosts allow`); mất máy thì đổi mật khẩu theo hướng dẫn.
- **Mạng lạ trùng dải LAN văn phòng, thiết bị giả làm Box**: chỉ dùng IP LAN sau khi bắt tay TLS với CA đã ghim; không xác thực được thì dùng IP VPN.
- **Thiết bị khác trong tailnet đặt trùng tên máy** để được duyệt nhầm: `duyet-tu-xa` chỉ nhận khi đúng một thiết bị khớp tên, in chi tiết và bắt gõ xác nhận; có `--ip` lấy từ bảng điều khiển.
- **Lượt duyệt không hạn bị quên**: `chan-doan` cảnh báo quá 30 ngày; `onebee-box tu-xa` liệt kê ngày duyệt và người duyệt.
- **Caddy chạy trong Docker không thấy IP nguồn thật**: không tách được `/quy-trinh/` theo nguồn ở tầng mạng; lớp chặn là nhóm SSO — giống hệt một máy nhân viên trong LAN hôm nay.

## Hệ quả
- Trước chuyến đi, kỹ thuật cần khoảng 10 phút: `onebee-cong-tac bat` trên máy trạm, `duyet-tu-xa` trên Box. Đang đi và khi về, người dùng không làm gì — máy tự chọn đường.
- Máy **đang ở xa** không nhận `cap-nhat-may`, `dong-bo-may`, `xoay-khoa` (`authorized_keys` có `from="<IP LAN Box>"`): máy giữ cấu hình cũ tới khi về LAN. Xoay khóa trong lúc máy đi công tác làm máy đó mất sao lưu và `hoi` cho tới khi về.
- Hỗ trợ từ xa (x11vnc) tới máy đang đi công tác không có — máy chạy Tailscale `--shields-up`, không nhận kết nối vào.
- Sao lưu qua VPN đi qua 4G tốn dung lượng; đã chọn vẫn mở cổng 8000.
- Kết quả thử thật các giả định: U1, U3, U5, U6, U7 đúng; U8 đúng một phần (chưa mở bằng Nemo); U4 chưa thử. **U2 không áp dụng khi có `tailscaled` thật**: `tailscaled` chèn `ts-forward` lên đầu FORWARD và ACCEPT mọi gói từ `tailscale0` trước `DOCKER-USER`, nên luật `--ctorigdstport` cho máy công tác không được xét. Lớp quyết định là mangle `ONEBEE-TAILSCALE` (chạy trước mọi chuỗi filter), đã chặn đúng máy chưa duyệt và cổng cấm. Luật `DOCKER-USER` giữ làm lớp dự phòng khi `tailscaled` chạy `--netfilter-mode=off`.
- Máy đã đi mà chưa chuẩn bị (Box không SSH tới được): `onebee-cong-tac bat --box-tu-xa` ghi `BOX_IP_TU_XA` và đổi kho sao lưu https sang tên Box, nên sao lưu chạy được qua VPN mà không cần Box đẩy cấu hình.
- Áp dụng cần: Box bật HTTPS, Box và máy trạm vào tailnet của đơn vị, đặt ACL một lần theo mẫu trong `docs/huong-dan/may-tram-di-cong-tac.md`.
