---
phase: 1
title: "Ngôn ngữ thiết kế và bản mẫu để anh duyệt"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Giai đoạn 1: Ngôn ngữ thiết kế và bản mẫu để anh duyệt

## Mục tiêu
Chốt một ngôn ngữ thiết kế tối giản dùng chung cho trang chủ Box và hình nền máy trạm, có bản mẫu xem được để anh Thiện duyệt trước khi sửa mã sản phẩm.

## Nguyên tắc thiết kế (bản đề xuất, chốt sau khi anh duyệt)
| Bỏ (dấu hiệu "AI làm") | Thay bằng |
|---|---|
| Nền xanh than + chữ ngọc phát sáng | Nền sáng `#F5F5F7`, thẻ trắng; chế độ tối `#000`/`#1C1C1E` theo `prefers-color-scheme` |
| Emoji làm biểu tượng | Không biểu tượng, hoặc SVG nét mảnh một màu (≤ 4 cái, nội tuyến) |
| Viền trái màu trên mọi thẻ | Thẻ bo 18px, không viền, bóng rất nhẹ hoặc không bóng |
| Tiêu đề nhóm IN HOA nhỏ, nhiều mục ngang hàng | Tiêu đề câu thường, cỡ lớn; ít mục, khoảng trắng rộng |
| Nhiều màu trạng thái, thẻ "pill" | Một màu nhấn; trạng thái bằng chấm nhỏ + chữ, chỉ đổi màu khi có vấn đề |
| Câu dài giải thích kỹ thuật trên thẻ | Một dòng tiêu đề + một dòng mô tả; chi tiết kỹ thuật đưa vào phần mở rộng |

Cấu trúc trang đề xuất (từ trên xuống): tên Box + tên đơn vị (chữ lớn) → một dòng tình trạng ("Mọi thứ đang chạy bình thường" hoặc điều cần chú ý) → 3 lối vào chính (Sổ điều hành, Thư mục dùng chung, Trợ lý AI) → Tình trạng chi tiết (CPU, RAM, ổ đĩa — số lớn, thanh mảnh) → Cẩm nang (mục gập) → Quản trị (liên kết chữ nhỏ cuối trang) → chân trang.

Hình nền máy trạm: nền chuyển sắc rất nhẹ một tông (không hoa văn tổ ong), logo OneBee nhỏ ở giữa hoặc góc; chữ tùy câu hỏi mở 3 của plan. Xuất PNG 1920×1080 và 2560×1440 từ một tệp SVG nguồn.

## Tệp tạo / sửa
- Tạo (ngoài repo, chỉ để duyệt): `plans/261116-2242-giao-dien-toi-gian-box-va-may-tram/ban-mau/trang-chu.html` (dựng từ dữ liệu mẫu, không Jinja) và `ban-mau/hinh-nen.svg`.
- Không sửa tệp sản phẩm ở giai đoạn này.

## Các bước
1. Đọc skill `ak:frontend-design` và `ak:ui-ux-pro-max` (phần tối giản), rồi viết bản mẫu trang chủ với nội dung thật của trang hiện tại (đủ mọi khối, số liệu mẫu).
2. Vẽ hình nền mới dạng SVG cùng bảng màu.
3. Chụp 6 ảnh: trang chủ sáng/tối × máy tính 1440px/điện thoại 390px, hình nền 1920×1080 — bằng trình duyệt Playwright riêng (`--user-data-dir` tạm, đóng trong `finally`), không dùng Chrome của anh.
4. Gửi ảnh + đường dẫn bản mẫu cho anh; ghi lựa chọn của anh cho 3 câu hỏi mở vào `plan.md`.

## Kiểm chứng
- Anh Thiện trả lời "duyệt" (hoặc sửa đến khi duyệt). Chưa duyệt thì DỪNG, không sang giai đoạn 2, 3.

## Todo
- [ ] Bản mẫu trang chủ (sáng, tối, điện thoại)
- [ ] Bản mẫu hình nền SVG
- [ ] 6 ảnh chụp gửi anh
- [ ] Ghi quyết định của anh vào plan
