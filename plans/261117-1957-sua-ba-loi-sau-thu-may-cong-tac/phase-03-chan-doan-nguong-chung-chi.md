---
phase: 3
title: "chan-doan: ngưỡng chứng chỉ HTTPS theo thời hạn của chính nó"
status: completed
priority: P2
effort: "1,5h"
dependencies: []
---

# Phase 3: chan-doan: ngưỡng chứng chỉ HTTPS theo thời hạn của chính nó

## Goal
`chan-doan` không còn báo giả "còn 0 ngày" cho chứng chỉ lá 12 giờ của Caddy, nhưng vẫn bắt được trường hợp gia hạn tự động bị hỏng.

## Files to Create / Modify
- Modify: `box/ansible/roles/box-stack/templates/onebee-box-chan-doan.sh.j2` (hàm `kiem_chung_chi`, dòng 350-373)
- Modify: `tests/box/check-diagnosis.sh` (khối "HTTPS đang bật", dòng 322-334)

## Mã liên quan (đã đọc)
- Dòng 364-370: lấy `notAfter` của chứng chỉ ở cổng 443 bằng `openssl s_client`, đổi ra số **ngày** còn lại, gọi `kiem_ngay_het` với ngưỡng `NGUONG_CHUNG_CHI_NGAY=15`.
- `kiem_ngay_het` dùng chung cho CA gốc và CA trung gian. Hai CA này sống dài nên ngưỡng 15 ngày vẫn đúng; giữ nguyên.

## Quy tắc mới (chỉ cho chứng chỉ lá ở cổng 443)
- Đọc cả `notBefore` và `notAfter`, tính bằng **giây**: thời hạn `T = notAfter − notBefore`, còn lại `C = notAfter − bây giờ`.
- `C ≤ 0` hoặc không đọc được: **LỖI** (giữ như cũ).
- `C < min(15 ngày, T/3)`: **CẢNH BÁO**. Caddy tự gia hạn khi còn khoảng một phần ba thời hạn; còn ít hơn nghĩa là gia hạn đang hỏng.
- Ngược lại: **OK**. In "Còn N ngày" khi `C ≥ 1 ngày`, "Còn N giờ (Caddy tự gia hạn)" khi dưới 1 ngày.

## Tasks & Steps
1. **Bài kiểm trước** trong `check-diagnosis.sh`, thay kịch bản "còn 7 ngày → CẢNH BÁO" bằng ba kịch bản. Dùng `openssl ca` với `-startdate`/`-enddate` để tạo chứng chỉ có thời điểm bắt đầu trong quá khứ (Ubuntu 24.04 có OpenSSL 3.0, `req -x509` chưa có `-not_before`):
   - Lá 12 giờ, cấp cách đây 1 giờ (còn 11 giờ): `ssl/https=ok`, dòng có "giờ".
   - Lá 12 giờ, cấp cách đây 10 giờ (còn 2 giờ, dưới T/3 = 4 giờ): `ssl/https=canh_bao`.
   - Lá 90 ngày, còn 7 ngày (dưới 15 ngày): `ssl/https=canh_bao`, để giữ đúng ý của kịch bản cũ cho chứng chỉ sống dài.
   - Giữ kịch bản "cổng 443 không trả chứng chỉ → LỖI".
   Chạy trên mã cũ: kịch bản đầu phải trượt.
2. **Sửa `kiem_chung_chi`** theo quy tắc trên. Tách một hàm nhỏ cho chứng chỉ lá, không đổi `kiem_ngay_het` của CA.
3. Giữ câu gợi ý cũ ("Khởi động lại cổng web để Caddy cấp lại…") cho mức CẢNH BÁO và LỖI.

## Verification
- `tests/box/check-diagnosis.sh` chạy bằng root trong container Ubuntu 24.04 (đúng như CI): "0 mục không đạt".
- Kết xuất `--json` vẫn đúng dạng (bài `check-diagnosis.sh` có kiểm).

## Risk & Rollback
- Nếu Caddy được cấu hình chứng chỉ lá sống dài hơn trong tương lai, quy tắc `min(15 ngày, T/3)` vẫn đúng.
- Hoàn tác: `git revert`.
