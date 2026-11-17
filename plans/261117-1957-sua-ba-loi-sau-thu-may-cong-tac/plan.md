---
title: "Sửa ba lỗi tìm thấy khi thử máy công tác trên Box thật"
description: "Tải lên kho tệp treo trên Box thật, hoi không báo lỗi sớm khi mất đường tới Box, chan-doan báo giả chứng chỉ HTTPS còn 0 ngày."
status: in-progress
priority: P1
effort: 1d
branch: fix/ba-loi-sau-thu-may-cong-tac
tags: [fix, box, desktop, test]
blockedBy: []
blocks: []
created: 2026-11-17
---

# Sửa ba lỗi tìm thấy khi thử máy công tác trên Box thật

## Overview

Lần thử thật ngày 17/11/2026 (`plans/reports/261117-kiem-thu-may-di-cong-tac.md`) tìm ra ba lỗi nằm ngoài PR #49. Cả ba đều có trên `main` từ trước (bản 1.3.x) và chỉ lộ ra khi Box thật bật HTTPS. Kế hoạch này sửa cả ba trong một PR.

## Ba lỗi và bằng chứng

| # | Lỗi | Bằng chứng | Nguyên nhân |
|---|---|---|---|
| L1 | Tải lên kho tệp treo trên Box thật | `PUT /files/...` sau đăng nhập một lần: 0 byte trả về trong 60 đến 120 giây, **cả qua LAN ngay trên Box**; nhật ký `onebee-kho-tep` có `BrokenPipeError` khi ghi trả lời. CI `box=true` thì tải lên PDF đạt 201 | **Đã thu hẹp, chưa chứng minh** (đo 17/11 20:06, xem Giai đoạn 1). `clamscan` một lượt chỉ 13 giây; tải lên PDF bằng `application/pdf` lúc 20:06 trả 201 sau 12,3 giây. Ba lượt treo hồi chiều đều kết thúc **đúng lúc client bỏ cuộc** (chờ 20, 120, 60 giây thì kho tệp xử lý xong sau đúng 20, 120, 60 giây rồi `BrokenPipeError`): kho tệp đang chờ một thứ chỉ xong khi kết nối đóng. Các lời gọi phụ thuộc đều có giới hạn 15 hoặc 60 giây nên không giải thích được điều này. Còn lại hai điểm khác giữa lượt treo và lượt đạt: tệp `.txt` gửi kiểu `text/plain`, và cầu nối danh tính cũ (bị tạo lại lúc 17:03) |
| L2 | `hoi` không báo lỗi sớm khi mất đường tới Box | Sau khi thu hồi máy công tác, `hoi` im lặng hơn 60 giây | `goi_api(..., timeout=300)` trong `desktop/ansible/roles/ai-cli/files/hoi`: một thời gian chờ 300 giây dùng chung cho cả lúc nối lẫn lúc chờ trả lời. Gói bị DROP thì lúc nối chờ đủ 300 giây |
| L3 | `chan-doan` luôn báo "Chứng chỉ HTTPS (cổng 443): Còn 0 ngày" khi HTTPS bật | Box thật: chứng chỉ lá `notBefore 08:33`, `notAfter 20:33` (UTC) | Caddy (`tls internal`) cấp chứng chỉ lá sống 12 giờ và tự gia hạn; `kiem_chung_chi` so số ngày còn lại với `NGUONG_CHUNG_CHI_NGAY=15` nên luôn cảnh báo |

## Phases

| # | Phase | Ưu tiên | Công | Phụ thuộc | Status |
|---|-------|---------|------|-----------|--------|
| 1 | [Kho tệp: chẩn đoán trên Box thật rồi sửa](./phase-01-kho-tep-chan-doan-va-sua.md) | P1 | 4h | — | Completed |
| 2 | [hoi: tách thời gian chờ nối khỏi thời gian chờ trả lời](./phase-02-hoi-bao-loi-som-khi-mat-duong.md) | P2 | 1,5h | — | Completed |
| 3 | [chan-doan: ngưỡng chứng chỉ HTTPS theo thời hạn của chính nó](./phase-03-chan-doan-nguong-chung-chi.md) | P2 | 1,5h | — | Completed |
| 4 | [CI, nhật ký thay đổi, PR](./phase-04-ci-va-pr.md) | P1 | 1h | 1, 2, 3 | Pending |

Ba giai đoạn đầu không đụng chung tệp nên chạy song song được: Giai đoạn 1 chỉ sửa trong `box/ansible/roles/box-kho-tep/` và bài kiểm kho tệp; Giai đoạn 2 chỉ sửa `hoi` và `tests/desktop/test_onebee_hoi.py`; Giai đoạn 3 chỉ sửa `onebee-box-chan-doan.sh.j2` và `tests/box/check-diagnosis.sh`. `CHANGELOG.md` để riêng cho Giai đoạn 4.

## Cách làm chung

- Một nhánh `fix/ba-loi-sau-thu-may-cong-tac` từ `origin/main`, làm trong worktree riêng `.worktrees/ba-loi`.
- Viết bài kiểm tái hiện lỗi **trước**, chạy thấy trượt, rồi mới sửa. Không nới bài kiểm nào để cho đạt.
- Commit tiếng Việt, tác giả Dương Minh Thiện, không nhắc AI.
- **Box thật dùng chung với phiên khác (DeepSeek).** Trước mọi lệnh làm đổi trạng thái trên `192.168.100.127`, kiểm không có bộ cài nào đang chạy (`ps -eo args | grep onebee-box-install`) và báo anh Thiện trước. Đo đạc chỉ đọc thì không cần.

## Tiêu chí hoàn thành

1. L1: trên Box thật đang bật HTTPS, đăng nhập một lần rồi tải lên một PDF 1 MB trả 201 trong dưới 60 giây, tải lại đúng SHA-256. Nguyên nhân được chứng minh bằng số đo, ghi trong báo cáo. Có bài kiểm hồi quy tái hiện đúng nguyên nhân đó.
2. L2: Box không tới được (gói bị DROP) thì `hoi` báo "Không kết nối được OneBee Box" trong tối đa khoảng 10 giây. Câu trả lời dài (mô hình chạy CPU, tới 300 giây) vẫn nhận đủ.
3. L3: chứng chỉ lá 12 giờ do Caddy cấp, còn hơn một phần ba thời hạn, thì `chan-doan` báo OK và in số giờ còn lại. Chứng chỉ sắp hết mà không được gia hạn thì vẫn cảnh báo; hết hạn hoặc không có thì vẫn báo lỗi.
4. CI `box=true` đạt cả 4 job; PR gộp vào `main`.

## Ngoài phạm vi

- Thay đổi kiến trúc quét virus (ví dụ đổi sang `clamd` thường trú) chỉ làm khi Giai đoạn 1 chứng minh `clamscan` từng lượt là nguyên nhân **và** anh Thiện chốt phương án (QĐ5 của ADR kho tệp đang chọn không chạy `clamd` để giữ RAM).
- Quy ước giữ chỗ khi nhiều phiên dùng chung Box thật (phát hiện số 4 trong báo cáo thử máy công tác).

## Câu hỏi còn mở

0. Giai đoạn 1 cần anh cho phép tạo một tài khoản thử và tải vài tệp thử lên kho tệp của Box thật (xoá sau khi xong). Lần đo lúc 20:06 đã tạo tài khoản `chandoan-kho` và tệp `chan-doan/t.pdf` (mã 2) trên Box, chưa dọn vì lệnh xoá cần anh duyệt.
1. Nếu L1 do `clamscan` nạp chữ ký quá lâu (khả năng thấp: đo được 13 giây) thì có ba hướng, đều đổi hành vi: (a) chạy `clamd` thường trú, tốn thêm khoảng 1 GB RAM; (b) tải lên trả 202 ngay rồi quét nền, người dùng thấy trạng thái "đang quét"; (c) chỉ nới thời gian chờ ở Caddy và kho tệp. Giai đoạn 1 có số đo xong sẽ hỏi anh chọn.
