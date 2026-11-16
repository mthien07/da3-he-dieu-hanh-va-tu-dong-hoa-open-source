---
title: "Giao diện tối giản: trang chủ Box và màn hình máy trạm OneBee"
description: "Làm lại trang chủ Box theo phong cách tối giản (kiểu Apple), bỏ dấu vết 'trang do AI làm'; máy trạm Linux cài bằng terminal xong phải thấy ngay màn hình nền và nhận diện OneBee."
status: in-progress
priority: P1
effort: "3d"
branch: feat/giao-dien-toi-gian
tags: [feature, box, desktop, ui]
blockedBy: []
blocks: []
created: 2026-11-16
---

# Giao diện tối giản: trang chủ Box và màn hình máy trạm OneBee

## Bối cảnh
Anh Thiện yêu cầu (16/11):
1. Làm lại UI/UX trang chủ Box "cho không giống sản phẩm của AI, mà đơn giản, tối giản hơn, giống Apple".
2. Máy trạm Linux: "cài trên terminal xong là phải có hình ảnh desktop của OneBee".

Hiện trạng đã đọc (nhánh `feat/dx-os-tich-hop`, đỉnh `9cf26c4`):
- Trang chủ: `box/ansible/roles/box-stack/templates/index.html.j2` (14 KB, một tệp, không tải gì từ Internet). Nền xanh than + viền thẻ màu mật ong/ngọc, biểu tượng emoji (🤖📁📒📖), tiêu đề nhóm chữ IN HOA nhỏ, thẻ "pill" trạng thái — đúng những dấu hiệu làm trang trông như AI sinh ra. Trang HTTP phụ: `huong-dan-ca.html.j2`.
- Máy trạm: role `desktop/ansible/roles/theme` đã có hình nền `onebee-wallpaper.png` (1920×1080, nền tổ ong xanh than, logo `>_`, khẩu hiệu), đặt làm **mặc định hệ thống** qua `zz_onebee-theme.gschema.override`, màn hình đăng nhập qua `slick-greeter.conf` (`force: false`), nút Bắt đầu chỉ áp cho **người dùng chưa từng đăng nhập**.
- Bộ cài `desktop/onebee-install.sh` kết thúc bằng "Hãy khởi động lại máy để áp dụng... giao diện". Người đang ngồi ở phiên Cinnamon chạy lệnh cài **không thấy gì đổi**: mặc định gschema không đè giá trị người dùng đã có, và phiên đang chạy chưa đọc lại schema. Đây là giả thuyết, phải chứng minh trên máy Mint thật ở giai đoạn 3 trước khi sửa.

## Kết quả phải đạt
| # | Kết quả | Đo bằng |
|---|---|---|
| 1 | Trang chủ Box mới được anh Thiện duyệt bản mẫu (sáng + tối, máy tính + điện thoại) trước khi viết vào template | Ảnh chụp bản mẫu, anh trả lời "duyệt" |
| 2 | Trang chủ không còn dấu hiệu "AI": không emoji, không viền trái màu, không tiêu đề IN HOA nhỏ, một màu nhấn, nền sáng mặc định, tự theo chế độ tối của máy | `test_onebee_mdns_dashboard.py` có mục kiểm mới; ảnh chụp |
| 3 | Mọi chức năng cũ giữ nguyên: số liệu `/trang-thai.json`, thẻ Sổ điều hành theo HTTPS, thư mục chung theo tên máy, cẩm nang từ `onebee-cam-nang.json`, chứng chỉ, tài khoản SSO; thoát HTML tên đơn vị | Toàn bộ test hiện có của trang chủ đạt, không xóa mục kiểm nào |
| 4 | Trang vẫn một tệp, không nguồn ngoài, ≤ 20 KB sau khi dựng | test |
| 5 | Chạy `sudo ./onebee-install.sh` trong phiên Cinnamon xong: màn hình nền đổi sang OneBee **ngay**, không cần đăng xuất | Máy ảo Mint 22 có giao diện, ảnh chụp trước/sau |
| 6 | Tài khoản khác trên máy (chưa đăng nhập lúc cài) thấy hình nền OneBee ở lần đăng nhập kế tiếp; người dùng tự đổi hình nền sau đó thì OneBee không đè lại | test đơn vị + máy ảo |
| 7 | Màn hình đăng nhập, màn hình khóa dùng cùng hình nền mới | Máy ảo, ảnh chụp |
| 8 | Bộ cài lần 2 `changed=0`; shellcheck, yamllint, ansible-lint sạch | CI (job lint + Desktop), runner máy trạm |

## Ràng buộc
- Chuẩn repo: test trước, lần 2 `changed=0`, lint sạch, commit tiếng Việt, tác giả `Dương Minh Thiện <thien20071005@gmail.com>`, không nhắc AI, không ghi số plan/giai đoạn vào mã, test, commit.
- Box trong LAN có thể không ra Internet: không phông web, không CDN; chỉ phông hệ thống (`-apple-system, "SF Pro Text", "Segoe UI", "Noto Sans", system-ui, sans-serif`) và SVG nội tuyến.
- Giữ nguyên các `id`, `data-port`, `data-path`, chuỗi `fetch("/trang-thai.json"` mà test và JavaScript đang dựa vào (liệt kê ở giai đoạn 2).
- Không đổi đường dẫn hình nền `/usr/share/backgrounds/onebee/onebee-wallpaper.png` — màn hình đăng nhập của máy đã cài trỏ vào đó (`force: false`), thay tệp là các máy cũ tự nhận hình mới.
- Không làm việc trên worktree `.worktrees/tich-hop` khi phiên khác còn chạy CI/máy ảo ở đó.

## Không làm
Giao diện Sổ điều hành (`so-dieu-hanh.html.j2`, `so-dieu-hanh.css`), đổi logo OneBee, màn hình khởi động Plymouth/GRUB (chờ anh quyết — câu hỏi mở 2), giao diện quản trị Node-RED/Uptime Kuma, đổi bố cục thanh tác vụ kiểu Windows đã có.

## Giai đoạn
| # | Giai đoạn | Người thực thi đề xuất | Cần xong trước | Công | Trạng thái |
|---|---|---|---|---|---|
| 1 | [Ngôn ngữ thiết kế và bản mẫu để anh duyệt](./phase-01-ngon-ngu-thiet-ke-va-ban-mau.md) | Opus | — | 0,5 ngày | Xong (bản mẫu thay bằng chính trang dựng thật; anh duyệt ảnh chụp ở PR) |
| 2 | [Trang chủ Box tối giản](./phase-02-trang-chu-box-toi-gian.md) | Sonnet | 1 (anh duyệt) | 1 ngày | Xong mã + test, chờ CI `box=true` |
| 3 | [Máy trạm: hình nền OneBee hiện ngay sau khi cài](./phase-03-may-tram-hinh-nen-hien-ngay.md) | Opus | 1 (hình nền mới) | 1 ngày | Xong mã + test; kiểm Mint container đạt |
| 4 | [Màn hình khởi động Plymouth](./phase-04-man-hinh-khoi-dong.md) | Sonnet | 1 | 0,5 ngày | Xong mã + test; chưa xem được trên màn hình thật |
| 5 | [Kiểm trên máy ảo và gộp](./phase-05-kiem-may-ao-va-gop.md) | Opus + anh Thiện | 2, 3, 4 | 0,5 ngày | Còn: CI `box=true`, máy ảo Mint có giao diện, anh duyệt |

Giai đoạn 2, 3, 4 sửa các vùng tệp tách rời (`box/…/box-stack/templates`, `tests/box` ↔ `desktop/…`, `tests/desktop`) nên chạy **song song** được, mỗi giai đoạn một worktree, cùng tách từ `feat/giao-dien-toi-gian`.

## Nhánh và worktree
- Phiên đang kiểm `feat/dx-os-tich-hop` báo CI xanh. Sau đó tạo `feat/giao-dien-toi-gian` từ đỉnh `origin/feat/dx-os-tich-hop`, worktree `.worktrees/giao-dien`.
- Giai đoạn 2: `feat/giao-dien-trang-chu-box` (worktree `.worktrees/giao-dien-box`); giai đoạn 3: `feat/giao-dien-may-tram` (worktree `.worktrees/giao-dien-may-tram`). PR nháp nền `feat/giao-dien-toi-gian`; người điều phối gộp.
- Cửa cuối mỗi giai đoạn: test đơn vị liên quan đạt bằng `~/.cache/onebee-kiem/bin/python`; lint sạch; CI của PR xanh.

## Việc của anh Thiện
- Duyệt bản mẫu ở giai đoạn 1 (trang chủ + hình nền) — không duyệt thì không sang giai đoạn 2, 3.
- Bật máy ảo Mint 22 có giao diện (VMware) cho giai đoạn 3–4; chạy lệnh cài trong cửa sổ terminal của phiên đã đăng nhập.

## Quyết định của anh Thiện (16/11)
1. Màu nhấn: giữ màu mật ong của logo (`#F5A524`), dùng tiết chế.
2. Có làm màn hình khởi động (Plymouth) logo OneBee; máy đã cài chỉ cần chạy lại bộ cài là cập nhật.
3. Bỏ khẩu hiệu trên hình nền; chỉ còn logo.
4. "Làm đi": làm liền, bản mẫu xem cùng PR thay vì chờ duyệt riêng; anh xem ảnh chụp ở PR rồi quyết gộp.

## Còn thiếu khi chuyển giao (16/11)
- Chưa chứng minh nguyên nhân "cài xong không đổi hình" trên máy Mint có giao diện (bước 3.1 của giai đoạn 3). Bản sửa không phụ thuộc nguyên nhân: bộ cài chủ động đặt hình nền cho phiên đang mở.
- Màn hình khởi động chưa được nạp trên Plymouth thật: `plymouthd` không chạy được trong container (không có tty/DRM). Script chỉ gồm lệnh thông dụng của module script và thuần ASCII. Xem thử trên máy ảo, không cần khởi động lại: `sudo plymouthd --mode=boot; sudo plymouth show-splash; sleep 8; sudo plymouth quit`.
- CI `box=true` trên nhánh này chưa chạy; bài kiểm Box chạy cục bộ có 46 mục trượt vì môi trường (cùng 46 mục trên bản gốc `9cf26c4`).
- Bài kiểm Mint container chạy trước lần sửa cuối của script Plymouth (chỉ đổi lời chú thích và một ký tự); đã chạy lại test đơn vị sau đó.
