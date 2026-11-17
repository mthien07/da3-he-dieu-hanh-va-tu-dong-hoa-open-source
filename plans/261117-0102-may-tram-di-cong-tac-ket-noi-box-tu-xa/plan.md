---
title: "Máy trạm đi công tác kết nối OneBee Box từ xa (duyệt và thu hồi theo từng máy)"
description: "Cho một máy trạm ngoài LAN dùng thư mục chung, kho tệp, Trợ lý AI và sao lưu của Box qua VPN, Box duyệt theo từng máy, có hạn, thu hồi ngay."
status: pending
priority: P1
effort: 6d
branch: feat/may-tram-di-cong-tac
tags: [feature, infra, auth, critical]
blockedBy: []
blocks: []
created: 2026-11-17
---

# Máy trạm đi công tác kết nối OneBee Box từ xa

## Overview

Một máy trạm OneBee mang ra ngoài văn phòng vẫn dùng được thư mục chung (Samba), kho tệp (`/files/`), Sổ điều hành, Trợ lý AI (lệnh `hoi`), sao lưu và báo tình trạng, qua VPN Tailscale, không mở cổng nào trên router. Box duyệt **từng máy, từng cổng**, có thể đặt hạn, và thu hồi có hiệu lực ngay cả với kết nối đang mở. Người dùng cuối không phải làm gì khi đổi mạng: máy tự chọn đường tới Box.

Kế hoạch viết trên `origin/main` tại `f961bf1` (bản 1.3.1). Đề bài nhắc ba thứ **không còn trên main**, kế hoạch xử lý theo hiện trạng thật:

| Đề bài nhắc | Hiện trạng trên main 1.3.1 | Kế hoạch làm gì |
|---|---|---|
| Open WebUI | Đã gỡ. Trợ lý AI chỉ còn `hoi` và tuyến `/ai/hoi`, `/ai/tom-tat` trên tên Box (`Caddyfile.j2:136-172`) | Chỉ lo `hoi`; không có lối tắt web AI để trỏ lại |
| n8n | Đã thay bằng Node-RED tại `/quy-trinh/` (ADR 0007) | Máy nhân viên không vào được nhờ nhóm SSO, xem mục Phân quyền |
| `onebee_box_cors_them` | Là biến của Open WebUI ở bản 1.2.0 (`group_vars/all.yml:76` tại tag `v1.2.0`), đã gỡ cùng Open WebUI. Trên main chỉ còn được nhắc trong `CHANGELOG.md:177` và tài liệu kế hoạch cũ; không còn trong `box/` hay `desktop/` | Không cần CORS: `hoi` không phải trình duyệt, Sổ điều hành cùng gốc với API |

## Hiện trạng đã khảo sát (bằng chứng)

- **Tường lửa** (`box/ansible/roles/box-firewall/files/onebee-tuong-lua`): kết nối mới qua `tailscale0` bị lọc ở `mangle/PREROUTING` (chuỗi `ONEBEE-TAILSCALE`), chỉ nguồn trong `TAILSCALE_CHO_PHEP` được qua, và được qua **mọi cổng**. Chưa có khái niệm "nguồn này chỉ được vài cổng". Quy tắc chỉ xét trạng thái `NEW`, nên gỡ một IP khỏi danh sách không cắt kết nối đang mở.
- **Tên và chứng chỉ**: CA của Box chỉ cấp cho IP LAN của Box (/32) và `<mã>.onebee.internal` (ADR 0005). Khi HTTPS bật, mọi tuyến lõi chỉ phục vụ trên `https://box.<mã>.onebee.internal` (`Caddyfile.j2:92-102`); kho sao lưu nghe trên cả IP lẫn tên (`Caddyfile.j2:233`). Vậy đi qua VPN bằng **tên Box** thì chứng chỉ hợp lệ sẵn, không phải xoay CA, không cần chứng chỉ cho IP VPN.
- **Cấu hình máy trạm** (`onebee-box.sh.j2:79-124`, hàm `in_cau_hinh_may`): `HOI_URL` và `TINH_TRANG_URL` đã theo tên; `RESTIC_REPOSITORY` còn theo IP LAN (dòng 108); lối tắt thư mục chung theo IP LAN (`ket-noi-box/tasks/main.yml:114`); dòng `/etc/hosts` `<BOX_IP> <BOX_TEN> # onebee-box` do Ansible ghi (`ket-noi-box/tasks/main.yml:136`).
- **Samba** (`box/ansible/roles/samba/tasks/main.yml`): `hosts allow = 127. 10. 172.16.0.0/12 192.168.` ở mức thư mục chung. Dải Tailscale `100.64.0.0/10` không nằm trong đó, nên hiện tại cả máy kỹ thuật qua Tailscale cũng bị Samba từ chối, trái với câu "vào được web/SSH/thư mục chung" trong `docs/huong-dan/cai-dat-onebee-box.md:35`. [Chưa kiểm trên máy thật, xác minh ở Giai đoạn 1.] Samba dùng **một** tài khoản chung `onebee`; `xoay-khoa` không đổi mật khẩu này.
- **Thu hồi máy** (`onebee-box.sh.j2:160-178`, `cmd_thu_hoi_may`): gỡ kho HTTP, khóa AI, ghim SSH, chỗ báo tình trạng. Chưa đụng tường lửa.
- **Quản lý từ Box qua SSH**: `authorized_keys` trên máy trạm có `from="<BOX_IP>"` (`quan-ly-tap-trung/tasks/main.yml:138`), nên `cap-nhat-may`, `dong-bo-may` không chạy được qua VPN.
- **Sao lưu Box** chỉ gồm `${SECRETS}` và `${BOX_DIR}` trong `/etc/onebee-box` (`onebee-box-sao-luu.sh.j2:71`); thư mục khác dưới `/etc/onebee-box` không được khôi phục.
- **Nhân viên không có `sudo`** trên máy trạm (`desktop/ansible/group_vars/all.yml`), nên việc chuyển chế độ không thể là một lệnh `sudo` do người dùng gõ.

## Kiến trúc

```
Máy trạm (ngoài LAN)                              OneBee Box (trong LAN văn phòng)
┌─────────────────────────────┐                   ┌──────────────────────────────────────┐
│ /etc/hosts:                 │  Tailscale        │ tailscale0 100.x.B                   │
│  <IP đang chọn> box.<mã>... │  (WireGuard,      │  mangle ONEBEE-TAILSCALE:            │
│ onebee-chon-duong-box       │   không mở cổng   │   máy kỹ thuật  → mọi cổng (như cũ)  │
│  (tự chạy khi đổi mạng)     │   router)         │   máy công tác  → tcp 443,445,8000   │
│ hoi → https://box.<mã>/ai   │ ────────────────► │   còn lại       → DROP               │
│ smb://box.<mã>/chung        │                   │ Caddy 443 (tên Box, CA riêng, SSO)   │
│ restic → https://box.<mã>:8000                  │ Samba 445 (hosts allow theo máy)     │
└─────────────────────────────┘                   │ /etc/onebee-box/tu-xa/<máy> (lượt    │
                                                  │  duyệt: IP, hạn) ← onebee-box        │
                                                  └──────────────────────────────────────┘
Lớp 2 (ngoài Box): ACL của tailnet — tag:congtac → tag:box chỉ tcp 443,445,8000; không có mục ssh.
```

Sáu quyết định (ghi thành ADR 0008 ở Giai đoạn 1):

1. **VPN là Tailscale trên tailnet của đơn vị** (nối tiếp ADR 0004). Không mở cổng router. WireGuard thuần và Headscale tự dựng đều cần một cổng công khai, trái yêu cầu.
2. **Tường lửa của Box là lớp quyết định**, theo từng IP và từng cổng. ACL của Tailscale là lớp thứ hai. Tài khoản quản trị tailnet bị chiếm thì thêm được thiết bị, nhưng thiết bị đó vẫn không qua được tường lửa Box.
3. **Mọi dịch vụ đi theo tên Box**, chỉ một dòng `/etc/hosts` đổi giữa IP LAN và IP VPN. Không URL nào chứa IP VPN, nên không đụng tới CA.
4. **Máy tự chọn đường**: thấy Box thật trong LAN (bắt tay TLS với CA đã ghim) thì dùng IP LAN; không thì dùng IP VPN. IP VPN chỉ tới được trong tailnet nên không giả được.
5. **Cần HTTPS đã bật** (`onebee_box_https: true`). Không có HTTPS thì Trợ lý AI vốn không chạy và máy không có cách xác thực Box trong mạng lạ.
6. **Lượt duyệt mặc định không hạn**, giữ tới khi kỹ thuật thu hồi. Thêm `--ngay N` (1 đến 365) thì hết hạn tự thu hồi. `chan-doan` cảnh báo lượt không hạn đã mở quá 30 ngày để không ai quên.

Phương án đã cân nhắc và không chọn: quảng bá IP LAN của Box (/32) qua Tailscale subnet route. Máy trạm không phải đổi gì, nhưng phụ thuộc bước duyệt tuyến trên bảng điều khiển Tailscale, không kiểm được trong CI, và không xác thực được Box khi mạng lạ trùng dải với văn phòng.

## Phân quyền: máy công tác so với máy kỹ thuật

| Thứ | Máy công tác (`duyet-tu-xa`) | Máy kỹ thuật (`onebee_box_tailscale_cho_phep`) |
|---|---|---|
| 443: trang chủ, `/dangnhap/`, `/ai/`, `/files/`, `/api/`, Sổ điều hành, `/webhook/` | Có | Có |
| 445: thư mục chung (SMB 3.1.1, bắt buộc mã hóa) | Có | Có (sau khi sửa `hosts allow`) |
| 8000: kho sao lưu của chính máy đó | Có | Có |
| 22 SSH, 3001 Giám sát, 80, 139, UDP 137/138 | **Chặn ở tường lửa** | Có |
| `/quy-trinh/` (Node-RED), trang giám sát | Tới được cổng 443 nhưng **bị SSO chặn**: chỉ nhóm `ky_thuat`/`quan_ly`, hai lớp | Có, sau SSO hai lớp |
| Hạn dùng | Không hạn theo mặc định; có `--ngay N` thì tự thu hồi | Không hạn, khai trong `group_vars` |

Giới hạn cần biết: Caddy chạy trong Docker không thấy IP nguồn thật, nên không tách được `/quy-trinh/` theo nguồn ở tầng mạng. Lớp chặn ở đó là nhóm SSO, giống hệt một máy nhân viên trong LAN hôm nay.

## Luồng duyệt và thu hồi

**Trước chuyến đi, tại văn phòng (kỹ thuật, khoảng 10 phút):**
1. Trên máy trạm: `sudo onebee-cong-tac bat` (cài Tailscale nếu chưa có, hiện link đăng nhập; hoặc `--khoa tskey-auth-…` dùng một lần, gắn `tag:congtac`). Máy vào tailnet với tên máy đúng bằng `MAY_TRAM`.
2. Trên Box: `sudo onebee-box duyet-tu-xa ketoan-01` (thêm `--ngay 14` nếu muốn tự hết hạn). Box tìm IP Tailscale theo tên máy, hỏi xác nhận, ghi lượt duyệt, mở đúng ba cổng cho đúng IP đó, rồi tự `dong-bo-may` để đẩy `BOX_IP_TU_XA` xuống máy.
3. Thử: tắt Wi-Fi văn phòng, bật 4G. `onebee-cong-tac xem` báo "từ xa qua VPN"; `hoi xin chào` trả lời; mở được thư mục chung.

**Đang đi:** người dùng không làm gì. Đổi mạng thì `onebee-chon-duong-box` tự chạy.

**Về văn phòng:** không làm gì; máy thấy Box thật trong LAN và quay lại IP LAN. Kỹ thuật chạy `sudo onebee-box thu-hoi-tu-xa ketoan-01`; lượt có `--ngay N` thì tự hết hạn.

**Mất máy:** `sudo onebee-box thu-hoi-may ketoan-01` (đã gồm thu hồi từ xa và cắt kết nối đang mở), xoá thiết bị khỏi tailnet, `xoa-nguoi`/`go-khoa-hoi` cho người dùng máy đó, đổi mật khẩu Samba chung.

**Máy đã đi mà chưa chuẩn bị:** cần người có mật khẩu tài khoản quản trị của máy. Kỹ thuật vào bằng `scripts/mo-truy-cap-tu-xa.sh` có sẵn, chạy `sudo onebee-cong-tac bat --box-tu-xa <IP Tailscale của Box>`, rồi `duyet-tu-xa … --ip <IP>` trên Box.

## Phases

| # | Phase | Ưu tiên | Công | Phụ thuộc | Status |
|---|-------|---------|------|-----------|--------|
| 1 | [Quyết định kiến trúc và xác minh giả định](./phase-01-quyet-dinh-kien-truc-va-xac-minh-gia-dinh.md) | P1 | 0,5 ngày | — | Pending |
| 2 | [Box: tường lửa theo cổng và Samba cho máy từ xa](./phase-02-box-tuong-lua-va-samba-cho-may-tu-xa.md) | P1 | 1 ngày | 1 | Pending |
| 3 | [Box: lệnh duyệt, thu hồi, hết hạn](./phase-03-box-lenh-duyet-thu-hoi-het-han.md) | P1 | 1,5 ngày | 2 | Pending |
| 4 | [Máy trạm: tự chọn đường và lệnh công tác](./phase-04-may-tram-tu-chon-duong-va-lenh-cong-tac.md) | P1 | 1,5 ngày | 1 (song song được với 2, 3) | Pending |
| 5 | [Kiểm thử tích hợp và tài liệu](./phase-05-kiem-thu-tich-hop-va-tai-lieu.md) | P1 | 1,5 ngày | 2, 3, 4 | Pending |

Giai đoạn 4 chỉ sửa trong `desktop/` và `tests/desktop/`; Giai đoạn 2 và 3 chỉ sửa trong `box/` và `tests/box/`. Hai nhánh này không đụng chung tệp nào.

## Ngoài phạm vi

- `cap-nhat-may`, `dong-bo-may`, `xoay-khoa` tới máy **đang ở xa**. Máy ở xa giữ cấu hình cũ tới khi về LAN. Hệ quả: xoay khóa trong lúc máy đi công tác làm máy đó mất sao lưu và `hoi` theo máy cho tới khi về.
- Hỗ trợ từ xa (`onebee-ho-tro`, x11vnc) tới máy đang đi công tác. Máy chạy Tailscale ở chế độ `--shields-up` nên không nhận kết nối vào.
- VPN khác Tailscale; điện thoại và máy không do OneBee quản lý.
- Tự đổi mật khẩu Samba chung khi thu hồi (xem Câu hỏi còn mở).
- Mã hóa ổ đĩa máy trạm (LUKS). Tài liệu chỉ khuyến nghị.

## Rủi ro bảo mật

| # | Rủi ro | Mức | Cách xử lý trong kế hoạch |
|---|---|---|---|
| R1 | Thu hồi xong nhưng kết nối đang mở vẫn sống (quy tắc chỉ xét `NEW`) | Cao | Thu hồi và hết hạn đều chạy `conntrack -D -s <IP>`; kiểm bằng kịch bản thật ở Giai đoạn 5 |
| R2 | Tailscale SSH đi vòng tường lửa Box (tailscaled nhận cổng 22 trước iptables) | Cao | ACL không có mục `ssh` cho `tag:congtac`; `chan-doan` cảnh báo khi Box bật Tailscale SSH mà đang có lượt duyệt |
| R3 | Samba một mật khẩu chung: không thu hồi được theo máy ở tầng ứng dụng | Trung bình | Thu hồi ở tầng mạng (tường lửa + `hosts allow`); mất máy thì đổi mật khẩu Samba theo hướng dẫn |
| R4 | Thiết bị lạ ở mạng khách sạn trùng IP LAN của Box, giả làm Box | Trung bình | Chỉ dùng IP LAN sau khi bắt tay TLS với CA đã ghim; không xác thực được thì dùng IP VPN |
| R5 | Thiết bị khác trong tailnet tự đặt tên `ketoan-01` để được duyệt nhầm | Trung bình | `duyet-tu-xa` chỉ nhận khi đúng một thiết bị khớp tên, in chi tiết và bắt gõ xác nhận; có `--ip` lấy từ bảng điều khiển |
| R6 | Tài khoản quản trị tailnet bị chiếm, gán IP đã duyệt cho thiết bị khác | Thấp | Vẫn cần mật khẩu Samba, tài khoản SSO hoặc khóa `obk-` |
| R11 | Lượt duyệt không hạn bị quên, quyền mở mãi | Trung bình | `chan-doan` cảnh báo lượt không hạn quá 30 ngày; `onebee-box tu-xa` liệt kê ngày duyệt và người duyệt |
| R7 | Khôi phục toàn bộ Box làm sống lại lượt duyệt cũ | Thấp | Lượt duyệt nằm ngoài vùng sao lưu: sau khôi phục phải duyệt lại (đóng mặc định) |
| R8 | Máy công tác bị chiếm là một chỗ đứng vào Box | Trung bình | Chỉ ba cổng; SSO và khóa riêng vẫn áp dụng; nhân viên không có `sudo` |
| R9 | Dòng `/etc/hosts` nhảy qua lại, hoặc Ansible và công cụ chọn đường giành nhau ghi | Trung bình | Một chủ duy nhất cho dòng đó (công cụ chọn đường); Ansible chỉ gọi công cụ; chỉ ghi khi nội dung đổi |
| R10 | Sao lưu qua 4G tốn dung lượng, SMB qua mạng xa chậm | Thấp | Ghi rõ trong hướng dẫn; anh đã chọn vẫn mở cổng 8000 |

## Success Criteria

- [ ] Máy đã duyệt, ở ngoài LAN: `hoi`, thư mục chung, kho tệp, sao lưu và báo tình trạng đều chạy; cổng 22, 80, 3001 của Box không tới được.
- [ ] Máy chưa duyệt trong cùng tailnet không tới được cổng nào của Box.
- [ ] Sau `thu-hoi-tu-xa`, kết nối SMB và HTTPS đang mở của máy đó đứt trong 5 giây; kết nối mới bị chặn.
- [ ] Lượt duyệt có `--ngay N` hết hạn thì tự thu hồi trong 15 phút; lượt không hạn giữ nguyên tới khi thu hồi tay.
- [ ] Máy về LAN tự dùng lại IP LAN trong 5 phút, người dùng không gõ lệnh nào.
- [ ] Máy không được duyệt từ xa hành xử y như 1.3.1 (không đổi URL, không đổi lối tắt).
- [ ] Bộ cài Box và máy trạm chạy lần hai đạt `changed=0 failed=0`; `shellcheck`, `yamllint`, `ansible-lint` sạch; CI `box=true` xanh.

## Validation Log

### Phiên 1 — 17/11/2026

| # | Câu hỏi | Anh chọn | Tác động |
|---|---|---|---|
| 1 | Hạn mặc định của lượt duyệt | **Không hạn mặc định** (em đề xuất 14 ngày) | Quyết định 6 đổi: mặc định không hạn, `--ngay N` là tuỳ chọn; thêm cảnh báo quá 30 ngày trong `chan-doan` (R11) |
| 2 | Sao lưu qua VPN | Có, mở cổng 8000 | Giữ `CONG_TU_XA="443,445,8000"` |
| 3 | Mật khẩu Samba chung khi mất máy | Chặn tầng mạng, đổi tay | Không thêm lệnh xoay mật khẩu Samba; hướng dẫn ghi cách đổi tay |
| 4 | Cập nhật và đồng bộ tới máy đang ở xa | Không, chờ máy về LAN | Giữ nguyên `from="<BOX_IP>"`; nằm ở Ngoài phạm vi |

### Kết quả đối chiếu với mã nguồn

- Đã đối chiếu 22 chỗ trích dẫn (đường dẫn, số dòng, tên hàm) với `origin/main` tại `f961bf1`: 22 khớp, 0 sai.
- 8 giả định chưa chạy thật, đánh số U1 đến U8, là việc của Giai đoạn 1. Không giả định nào được coi là đúng trước khi thử.
- `onebee_box_cors_them`, Open WebUI, n8n: có ở tag `v1.2.0`, không còn trong mã `box/` và `desktop/` trên main (biến CORS chỉ còn được nhắc trong `CHANGELOG.md:177`).

### Rà chéo toàn kế hoạch

Sau khi áp bốn câu trả lời: đã tìm lại "14 ngày", "khong-han", "có hạn", "Câu hỏi còn mở" trong `plan.md` và năm tệp giai đoạn; mọi chỗ đã theo quyết định mới. Không còn mâu thuẫn.

## Red Team Review

Em tự rà theo ba góc (kẻ tấn công, giả định sai, chế độ hỏng). Chín điểm dưới đây đã được đưa vào kế hoạch; không điểm nào bị bỏ.

| # | Phát hiện | Bằng chứng | Đã xử lý ở |
|---|---|---|---|
| 1 | Thu hồi không cắt kết nối đang mở | `onebee-tuong-lua` chỉ lọc `--ctstate NEW` | GĐ3 `conntrack -D`; U5; C6; T8 |
| 2 | Tailscale SSH đi vòng tường lửa | `docs/huong-dan/truy-cap-tu-xa-khi-cai-may.md` mục "Lưu ý khi máy này thành OneBee Box" | ACL mẫu không có `ssh` cho máy công tác; cảnh báo trong `chan-doan` |
| 3 | Ansible và công cụ chọn đường cùng ghi `/etc/hosts`, phá `changed=0` | `ket-noi-box/tasks/main.yml:136` | GĐ4 bỏ hai task `lineinfile` |
| 4 | Samba từ chối cả máy kỹ thuật qua Tailscale | `samba/tasks/main.yml` (`hosts allow`), `group_vars/all.yml` | U4; GĐ2 mục Samba |
| 5 | Tìm IP theo tên máy có thể bị đặt trùng tên | thiết kế mới | Bắt xác nhận, đòi đúng một thiết bị, có `--ip` |
| 6 | Khôi phục Box làm sống lại lượt duyệt | `onebee-box-sao-luu.sh.j2:71` | Trạng thái đặt ngoài vùng sao lưu |
| 7 | `/quy-trinh/` nằm trên cổng 443 mà máy công tác tới được | `Caddyfile.j2:205` | Ghi rõ lớp chặn là nhóm SSO hai lớp; T6 kiểm |
| 8 | Thiết bị lạ trùng IP LAN của Box ở mạng ngoài | thiết kế mới | Bắt tay TLS với CA ghim; T10 kiểm |
| 9 | Đổi URL kho sao lưu và lối tắt cho mọi máy là thay đổi quá rộng | `onebee-box.sh.j2:108` | Chỉ đổi cho máy có lượt duyệt; máy khác y như 1.3.1 |

## Câu hỏi còn mở

Không còn câu nào chặn việc bắt đầu. Hai điều chỉ biết được sau khi thử thật:

1. Nếu U2, U3 hoặc U5 trượt ở Giai đoạn 1, Giai đoạn 2 và 3 dùng phương án thay đã ghi sẵn trong từng tệp.
2. Box thật hiện chưa bật HTTPS. Giai đoạn 1 và 5 cần bật trên snapshot; anh có muốn giữ HTTPS bật trên Box đó sau khi thử không?

<!-- slug: may-tram-di-cong-tac-ket-noi-box-tu-xa -->
