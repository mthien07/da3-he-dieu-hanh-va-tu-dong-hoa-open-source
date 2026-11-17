---
title: "Sửa PR #49 máy trạm đi công tác trước khi gộp"
description: "Sửa lỗi thứ tự cắt kết nối khi lượt duyệt hết hạn, viết lại bài kiểm C6 đang kiểm sai, rồi chạy CI Box tới khi C1 đến C11 đều đạt."
status: in-progress
priority: P1
effort: 5,5h
issue: 49
branch: feat/may-tram-di-cong-tac
tags: [fix, test, infra, critical]
blockedBy: []
blocks: []
created: 2026-11-17
---

# Sửa PR #49 máy trạm đi công tác trước khi gộp

## Overview

PR #49 (`feat/may-tram-di-cong-tac` vào `main`, commit `754cae6`) làm đủ 5 giai đoạn của kế hoạch `plans/261117-0102-may-tram-di-cong-tac-ket-noi-box-tu-xa/`. Lượt CI chạy tay có bài Box (run `44022483141`) trượt ở C6, nên C7 đến C11 chưa chạy lần nào. Kế hoạch này sửa đúng những gì đã tìm thấy khi đọc mã, rồi chạy lại CI Box cho tới khi đạt hết.

## Lỗi đã tìm thấy (bằng chứng)

| # | Lỗi | Bằng chứng | Mức |
|---|---|---|---|
| L1 | Bài kiểm C6 không mở kết nối nào. `curl --config -` đọc hết cấu hình rồi mới tải, mà cấu hình đến từ một vòng lặp chạy mãi, nên `curl` chờ mãi, không gửi yêu cầu nào và không bao giờ thoát. C6 báo "kết nối không đứt (5s)" dù chưa từng có kết nối | `tests/box/run-box-test-in-systemd-container.sh:363-390`. Đã thử trên máy Mac: sau 3 giây `curl` vẫn sống, không ghi dòng `Trying` nào. Log CI: `FAIL  C6: kết nối đang mở không đứt trong 5 giây (5s)` | Cao: chặn CI, che C7 đến C11 |
| L2 | Lượt duyệt hết hạn: `tu_xa_ap_dung` chạy `conntrack -D` **trước** khi dựng lại tường lửa. Trong khoảng giữa, gói kế tiếp của kết nối cũ tạo lại mục conntrack mới mà luật cũ vẫn cho qua (IP vẫn còn trong danh sách), nên kết nối đang mở **không đứt** khi hết hạn. Rủi ro R1 của kế hoạch gốc chỉ được xử lý đúng ở nhánh thu hồi tay | `onebee-box-tu-xa.sh.j2`, hàm `tu_xa_ap_dung`: `conntrack -D` nằm trong vòng lặp, `onebee-tuong-lua bat` nằm ở cuối hàm. Nhánh thu hồi tay `thu_hoi_tu_xa_thuc` làm đúng thứ tự (dựng tường lửa rồi mới `conntrack -D`) | Cao: lỗi bảo mật thật |
| L3 | C7 chỉ kiểm kết nối **mới** bị chặn sau khi hết hạn, không kiểm kết nối **đang mở**, nên không bắt được L2. Bài kiểm đơn vị cũng không kiểm thứ tự gọi | `run-box-test-in-systemd-container.sh:392-400`; `tests/box/test_onebee_tu_xa.py` chỉ kiểm `conntrack.log` có `-D -s`, không kiểm thứ tự so với `tuong-lua.log` | Trung bình |
| L4 | `conntrack -D -s <IP>` có thể trả mã khác 0 khi không có mục nào để xoá, làm lệnh thu hồi in cảnh báo "Không chạy được conntrack" sai | Chưa xác minh, cần đọc mã thoát thật trong container CI (Ubuntu 24.04, conntrack 1.4.x) | Thấp |
| L6 | `onebee-tuong-lua bat` chạy `tat` (gỡ hết) rồi mới `dung`: trong khoảng đó kết nối mới qua mọi cổng mạng không bị lọc. Có từ trước PR này, nhưng giờ chạy mỗi lần duyệt hoặc thu hồi | `onebee-tuong-lua`, hàm `bat` | Trung bình |
| L5 | Mô tả PR #49 hỏng ký tự: `\t` bị hiểu thành tab (`tu-xa-duoc-duyet` thành "	u-xa-duoc-duyet") | `gh pr view 49` | Thấp, chỉ hiển thị |

Phía máy trạm (`onebee-chon-duong-box`, `onebee-cong-tac`, dispatcher NetworkManager, bộ hẹn giờ 5 phút): đã đọc, chưa thấy lỗi, nên ngoài phạm vi sửa.

## Phases

| # | Phase | Ưu tiên | Công | Phụ thuộc | Status |
|---|-------|---------|------|-----------|--------|
| 1 | [Box: cắt kết nối sau khi dựng lại tường lửa khi hết hạn](./phase-01-box-cat-ket-noi-sau-khi-dung-tuong-lua.md) | P1 | 1h | — | Completed |
| 2 | [Viết lại C6 và mở rộng C7 giữ kết nối thật](./phase-02-viet-lai-c6-va-mo-rong-c7.md) | P1 | 2h | — (song song được với 1) | Completed |
| 3 | [Chạy CI Box, xử lý C7 đến C11, sửa mô tả PR](./phase-03-chay-ci-box-va-cap-nhat-pr.md) | P1 | 1,5h | 1, 2, 4 | Pending |
| 4 | [Tường lửa: dựng lại không có khoảng hở](./phase-04-tuong-lua-dung-lai-khong-khoang-ho.md) | P1 | 1h | — | Completed |

Giai đoạn 1 chỉ sửa `onebee-box-tu-xa.sh.j2` và `test_onebee_tu_xa.py`; Giai đoạn 2 chỉ sửa `run-box-test-in-systemd-container.sh` và `tests/README.md`. Hai giai đoạn không đụng chung tệp nên giao hai máy làm song song được.

## Cách làm chung

- Làm trên chính nhánh PR: `git worktree add .worktrees/sua-cong-tac origin/feat/may-tram-di-cong-tac -B feat/may-tram-di-cong-tac`. Không mở PR mới.
- Commit tiếng Việt, kiểu `fix(box): ...`, `test(box): ...`, tác giả `Dương Minh Thiện`, không nhắc AI.
- Không gỡ hay nới bài kiểm nào để cho đạt. C6 phải vẫn chứng minh được "kết nối đang mở đứt trong 5 giây".

## Tiêu chí hoàn thành

1. Bài kiểm đơn vị chứng minh cả thu hồi tay lẫn hết hạn đều dựng lại tường lửa **trước** khi `conntrack -D`.
2. C6 chỉ đạt khi trước lúc thu hồi đã có kết nối HTTPS 443 và phiên Samba 445 chạy được một lượt, và sau thu hồi lượt kế tiếp trên chính kết nối đó không có phản hồi trong 5 giây.
3. C7 kiểm thêm một kết nối HTTPS đang mở bị đứt khi lượt hết hạn. Chạy bản C7 mới trên mã chưa sửa L2 thì phải trượt (chứng minh bài kiểm bắt được lỗi).
4. CI chạy tay với `box=true` trên nhánh PR đạt cả 4 job, log có đủ `PASS  C1` đến `PASS  C11` và `TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT`.
5. Mô tả PR #49 hiển thị đúng tên lệnh, có thêm dòng kết quả CI Box.

## Ngoài phạm vi

- Kiểm thử thực địa trên Box thật và máy Mint thật (U1 đến U8, T1 đến T12 của kế hoạch gốc).
- Gộp PR #49: anh quyết sau khi xem kết quả.

## Quyết định

- 17/11/2026, anh Thiện chốt vá luôn khoảng hở của `onebee-tuong-lua bat` trong PR #49 (thêm Giai đoạn 4).
