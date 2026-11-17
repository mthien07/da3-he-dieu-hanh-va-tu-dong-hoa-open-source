# Thử thực địa: máy trạm đi công tác kết nối Box từ xa (17/11/2026)

Kết quả ngắn: trên Box thật, máy Mint thật và tailnet Tailscale thật, **T1 đến T12 đều đạt** sau khi sửa một lỗ hổng thật ở phía máy trạm (sao lưu của máy đã đi mà chưa chuẩn bị). Lần thử cũng chỉ ra rằng luật `DOCKER-USER` cho máy công tác không bao giờ được xét khi có `tailscaled` thật. Lớp lọc thật là mangle, đúng như thiết kế, và vẫn chặn đúng.

Mọi số liệu dưới đây lấy từ đầu ra thật trong lượt thử, không ước lượng.

## Môi trường

| Vai trò | Máy | Ghi chú |
|---|---|---|
| Box | VM Ubuntu Server 24.04.5 `192.168.100.127` (`may-chu`), bridged vào LAN | Nhánh `feat/may-tram-di-cong-tac`, HTTPS bật, Tailscale 1.104.7, tên `onebee-box` (100.103.80.31), gắn `tag:box` |
| Máy công tác | VM `onebee-mint-may-sach` (Mint 22.3), NAT | Cấp `ketoan-01` bằng `them-may`, cài máy trạm từ nhánh PR, `tag:congtac` (100.91.229.106) |
| Máy lạ trong tailnet | VM `onebee-mint-22-3-kiem`, NAT | Chỉ cài Tailscale, tên `may-la` (100.126.185.115), `tag:congtac`, không duyệt |
| Tailnet | Tailnet thử riêng của anh Thiện | ACL mẫu trong `docs/huong-dan/may-tram-di-cong-tac.md` (đã bỏ mục `ssh`, xem mục Lỗi) |

**Cách giả lập "máy rời văn phòng":** VM Mint chạy NAT nên vẫn tới được IP LAN của Box qua máy Mac. Em chặn mọi gói từ Mint tới `192.168.100.127` (`iptables -I OUTPUT -d 192.168.100.127 -j DROP`), giống hệt khi máy ở mạng khác. Khi đó Tailscale không nối thẳng được và đi qua máy chuyển tiếp DERP ở Singapore (ping 85 ms, khoảng 450 KB/s). Đây là đường chậm nhất có thể có; ngoài thực tế Tailscale thường nối thẳng được.

**Box dùng chung:** trong lúc thử, một phiên khác (DeepSeek, nhánh `feat/box-kho-ke-toan`) chạy bộ cài từ `/root/onebee-test` chồng lên hai lần (15:52 và 16:15), ghi đè lệnh `onebee-box` và `onebee-tuong-lua` bằng bản không có tính năng này. Kết quả trước 16:20 vì vậy bị bỏ; mọi dòng dưới đây đo sau lần cài lại lúc 16:20. Sau khi thử xong, Box đã được cài lại bản sổ kho và kế toán từ `/root/onebee-test` như trước.

## Kịch bản trên máy thật (T1 đến T12)

| # | Bước | Kết quả |
|---|---|---|
| T1 | `sudo onebee-cong-tac bat --khoa file:<tệp>` trên Mint | **Đạt.** Tự cài Tailscale, vào tailnet với tên `ketoan-01` |
| T2 | `duyet-tu-xa ketoan-01 --ngay 1` trên Box | **Đạt.** Tự tìm đúng IP 100.91.229.106 theo tên, hỏi xác nhận, ghi lượt, sinh luật mangle và `samba-tu-xa.conf`. Box không SSH được tới Mint (Mint sau NAT) nên in hướng dẫn `onebee-cong-tac bat --box-tu-xa 100.103.80.31`; đã chạy theo |
| T3 | Mint còn trong LAN: `onebee-cong-tac xem` | **Đạt.** "mạng văn phòng", `/etc/hosts` trỏ 192.168.100.127 |
| T4 | Chặn LAN (giả lập rời văn phòng) | **Đạt.** Bộ hẹn giờ tự đổi `/etc/hosts` sang 100.103.80.31 sau khoảng 2 phút 30 giây (yêu cầu dưới 5 phút), không ai gõ lệnh |
| T5 | Dịch vụ qua VPN | **Đạt** (sau khi sửa lỗi sao lưu). Trang chủ 443: 200. `hoi`: trả lời đúng (265 giây, Box chạy mô hình bằng CPU). Chép 50 MB qua SMB: 114 giây. Sao lưu: snapshot `19c4b36d`, 20 giây. Báo tình trạng: Box ghi "sao lưu vừa xong · báo tình trạng vừa xong". Tải lên kho tệp: **lỗi riêng của Box**, xem mục Phát hiện ngoài phạm vi |
| T6 | Cổng cấm; `/quy-trinh/` bằng tài khoản `nhan_vien` | **Đạt.** 22, 80, 3001 hết giờ. Đăng nhập một lần 200; `/quy-trinh/` 403; chưa đăng nhập 302 |
| T7 | Thiết bị thứ ba chưa duyệt | **Đạt.** `may-la` thử 443, 445, 8000, 22, 80, 3001: đều bị chặn |
| T8 | Đang chép SMB thì `thu-hoi-tu-xa` | **Đạt.** Lệnh thu hồi 2,2 giây; phiên SMB chết khoảng 4 giây sau (`NT_STATUS_IO_TIMEOUT`); tệp trên Box không tăng thêm byte nào trong 10 giây; `ESTABLISHED` trong conntrack từ 1 về 0. `hoi` sau thu hồi không trả lời trong 60 giây (không báo lỗi sớm, xem dưới) |
| T9 | Duyệt lại, gỡ chặn LAN (về văn phòng) | **Đạt.** Quay lại IP LAN sau 40 giây, không ai gõ lệnh |
| T10 | Máy giả chiếm IP LAN của Box, chứng chỉ tự ký | **Đạt.** Máy giả trả lời ở 192.168.100.127 nhưng không qua được CA đã ghim (`curl` lỗi 60); Mint chọn VPN và vẫn tới Box thật (200) |
| T11 | Chạy lại bộ cài Box và máy trạm | **Đạt.** Lần hai: Box `ok=163 changed=0 failed=0`, Mint `ok=147 changed=0 failed=0` |
| T12 | `chan-doan` trên Box | **Đạt.** Có dòng "Máy công tác đang được duyệt: 1 máy — sắp hết hạn trong 24 giờ: ketoan-01"; không lỗi mới so với lúc trước khi thử |

## Giả định U1 đến U8

| # | Giả định | Kết quả |
|---|---|---|
| U1 | Ở mangle, cổng còn là cổng trước DNAT | **Đúng.** Luật mangle `--dports 443,445,8000` cho qua (bộ đếm 8 gói), 443 và 8000 tới được, 22 và 3001 bị chặn |
| U2 | `--ctorigdstport` trong `DOCKER-USER` khớp sau DNAT | **Không áp dụng được khi có `tailscaled` thật.** `tailscaled` chèn `-A FORWARD -j ts-forward` lên đầu, chuỗi này ACCEPT mọi gói từ `tailscale0` (6543 gói) trước khi tới `DOCKER-USER`; bộ đếm ba luật `--ctorigdstport` đứng ở 0 dù 443 và 8000 tới được. An toàn không đổi vì lớp mangle chặn trước (T6, T7). Luật `DOCKER-USER` chỉ còn là lớp dự phòng khi `tailscaled` chạy `--netfilter-mode=off`, và vẫn được bài CI (không có `tailscaled`) kiểm |
| U3 | `include` trong khối thư mục chung đè `hosts allow` | **Đúng.** `testparm` thấy dòng `include`; Mint qua IP Tailscale chép được |
| U4 | Samba trước khi sửa từ chối nguồn 100.x | **Chưa thử.** Tailnet thử không có thiết bị `tag:kythuat` |
| U5 | `conntrack -D` cắt kết nối TCP đang mở | **Đúng** (T8) |
| U6 | `tailscale status --json` trên Box thấy `HostName` và IP của máy công tác dưới ACL hẹp | **Đúng.** Thấy `ketoan-01` với 100.91.229.106 |
| U7 | `--shields-up --accept-dns=false` vẫn gọi ra được; `resolv.conf` không đổi | **Đúng.** `resolv.conf` vẫn `127.0.0.53`; từ Box gọi cổng 22 của Mint qua Tailscale hết giờ |
| U8 | Mở thư mục chung theo tên Box; đọc được trạng thái Tailscale SSH | **Đạt một phần.** `smbclient //box.test.onebee.internal/chung` qua dòng `/etc/hosts` chạy; chưa mở bằng giao diện Nemo. `chan-doan` đọc được `RunSSH` (không cảnh báo vì Box tắt Tailscale SSH) |

## Lỗi tìm thấy và đã sửa trong PR #49

| Lỗi | Bằng chứng | Sửa |
|---|---|---|
| Máy đã đi mà chưa chuẩn bị không sao lưu được: `--box-tu-xa` chỉ ghi `BOX_IP_TU_XA`, kho sao lưu vẫn theo IP LAN | `dial tcp 192.168.100.127:8000: i/o timeout` | `onebee-cong-tac` đổi máy chủ trong `RESTIC_REPOSITORY` (https, đang theo `BOX_IP`) sang `BOX_TEN`; hai bài kiểm mới; thử lại trên máy thật đạt |
| ACL mẫu trong hướng dẫn không lưu được | Tailscale: `"check" action does not support tags in src` | Bỏ mục `ssh` khỏi ACL mẫu; sửa câu gợi ý trong `chan-doan` (tên tag sai `tag:ky-thuat`) |
| C3 của CI trượt hay đạt tùy thời điểm | `curl | grep -q` dưới `pipefail`: tái hiện 20/20 lần trượt với trang lớn (curl thoát 23) | Dùng `grep >/dev/null` trong khối máy công tác |
| C6 mới không thấy phiên Samba | `smbclient` đệm stdout khi ghi ra tệp: tái hiện với smbd thật, không `stdbuf` 0 dòng sau 3 giây | `stdbuf -oL -eL` |

## Phát hiện ngoài phạm vi PR (chưa sửa)

1. **Tải lên kho tệp treo trên Box này, cả qua LAN.** `PUT /files/...` sau đăng nhập không trả byte nào trong 60 đến 120 giây; nhật ký `onebee-kho-tep` có `BrokenPipeError`. Kho tệp quét ClamAV ngay trong container cho mỗi lượt tải; nghi chậm hoặc treo trên VM này. Không liên quan đường VPN.
2. **`hoi` không báo lỗi sớm khi mất đường tới Box.** Sau thu hồi, lệnh chờ hơn 60 giây mà không nói gì, vì thời gian chờ của nó phải đủ dài cho mô hình chạy bằng CPU (lần đạt mất 265 giây). Nên tách thời gian chờ nối mạng (vài giây) khỏi thời gian chờ trả lời.
3. **`chan-doan` cảnh báo "Chứng chỉ HTTPS còn 0 ngày" khi HTTPS bật.** Chứng chỉ lá do Caddy cấp từ CA nội bộ chỉ sống 12 giờ và tự gia hạn (`notBefore 08:33`, `notAfter 20:33` UTC), nên ngưỡng 15 ngày luôn báo. Cảnh báo giả, có từ trước PR này.
4. **`duyet-tu-xa` in "lần thấy cuối" là `0001-01-01T00:00:00Z`** khi máy đang trực tuyến (Tailscale để trống trường này cho máy đang nối). Chỉ là hiển thị.
5. **Box thật bị hai phiên dùng cùng lúc** mà không có cơ chế giữ chỗ. Nên quy ước: phiên nào dùng Box thật thì ghi một tệp khóa (ví dụ `/root/dang-dung-boi`) và phiên khác kiểm trước khi cài.

## Dọn dẹp

- Box: đã thu hồi lượt duyệt và máy `ketoan-01`, xoá tài khoản thử `nvthu`, xoá tệp thử trong thư mục chung, đăng xuất và gỡ Tailscale. Cài lại bản sổ kho và kế toán từ `/root/onebee-test`; **giữ HTTPS bật** theo lựa chọn của anh. `~/onebee` về `main` như cũ, chỉ thêm `onebee_box_https: true`.
- Hai VM Mint: quay về snapshot `truoc-thu-may-cong-tac` (tắt).
- Tailnet thử: ba thiết bị đã đăng xuất; **còn phải xoá trên bảng điều khiển** (xem Câu hỏi).
- Khóa Tailscale và mật khẩu chỉ nằm trong thư mục tạm của phiên, không vào repo hay commit.

## Câu hỏi còn mở

1. Anh xoá giúp ba thiết bị `onebee-box`, `ketoan-01`, `may-la` trên bảng điều khiển tailnet thử, hoặc xoá luôn tailnet thử, và thu hồi hai khóa (hạn 3 ngày).
2. Các phát hiện 1 đến 3 ở trên: anh muốn em mở việc riêng để sửa không?
