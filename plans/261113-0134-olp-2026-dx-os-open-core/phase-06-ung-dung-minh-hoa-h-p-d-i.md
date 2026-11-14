---
phase: 6
title: "Giai đoạn 6: Ứng dụng minh họa H-P-D-I"
status: todo
priority: P1
effort: "3d"
dependencies: [3, 4, 5, 7, 8]
---

# Giai đoạn 6: Ứng dụng minh họa H-P-D-I

Nhánh: `feat/ung-dung-so-dieu-hanh-htx`.

## Mục tiêu
Một ứng dụng web nhỏ "Sổ điều hành HTX" chạy **trên** lõi (gọi qua cổng API, dùng đầy đủ SSO, CSDL, kho tệp có kiểm dịch, động cơ phê duyệt, AI nội bộ), đi trọn vòng H → P → D → I, dùng được trong 15 phút trình diễn.

## Thiết kế
- Trang tĩnh (HTML, CSS, JavaScript thuần, không tải gì từ Internet, cùng phong cách trang chủ Box; có thể tham khảo cách chia bảng và biểu đồ trực quan nhưng không giữ dữ liệu cứng), do Caddy phục vụ sau SSO; mọi dữ liệu đi qua `/api/`, `/files/`, `/ai/`.
- **[H]** đăng nhập một lần, thấy tên và vai trò của mình (`nhan_vien`, `ky_thuat`, `quan_ly`), lối vào thư mục chung, kho tệp và Trợ lý AI.
- **[P]**
  - Ba biểu mẫu thay biểu mẫu n8n: nhập đơn hàng (có nút đính kèm tệp báo giá/hợp đồng tải lên kho tệp ở giai đoạn 7), báo cần hỗ trợ, khảo sát. Kiểm dữ liệu ở trình duyệt và ở CSDL (ràng buộc của giai đoạn 3); dữ liệu sai bị từ chối kèm lời giải thích tiếng Việt.
  - Hàng đợi phê duyệt cho nhóm `quan_ly`: xem đơn đang `CHO_DUYET`, tệp đính kèm đã qua kiểm dịch (`CLEAN`), bấm Duyệt hoặc Từ chối (gọi tới động cơ quy trình ở giai đoạn 5); Poka-yoke chặn tự duyệt đơn của chính mình.
- **[D]** trang điều hành cho nhóm `quan_ly`: số đơn hàng theo tuần, tỷ lệ đơn đã duyệt/từ chối, yêu cầu hỗ trợ đang mở và thời gian phản hồi, số máy trạm đã sao lưu, trạng thái tệp kiểm dịch — đọc trực tiếp từ API, cập nhật khi tải lại.
- **[I]** tích hợp khung hỏi đáp Trợ lý AI & RAG (xây ở giai đoạn 8) và nút "Nhờ Trợ lý tóm tắt tuần này": gửi số liệu tổng hợp (không có tên người) tới Ollama qua `/ai/`, hiện bản nháp kèm dòng nhắc AI có thể sai; người quản lý đọc và quyết định.

## Nhiệm vụ

### Nhiệm vụ 6.1 — Khung ứng dụng và trang [H]
- Kiểm chứng: test đơn vị trên mẫu trang (không tài nguyên ngoài, không `innerHTML` với dữ liệu, dưới 40 KB mỗi trang); bài kiểm Box: chưa đăng nhập bị chuyển tới trang đăng nhập.

### Nhiệm vụ 6.2 — Biểu mẫu, đính kèm tệp và hàng đợi phê duyệt [P]
- Kiểm chứng: bài kiểm Box:
  1. Gửi đơn hàng hợp lệ kèm 1 tệp PDF hợp lệ nhận 201, có dòng trong CSDL, tệp trên kho tệp đạt `CLEAN`, sinh tác vụ chờ duyệt trong động cơ quy trình.
  2. Gửi tệp chứa chuỗi thử EICAR bị từ chối/cách ly (`INFECTED`), không gắn được vào đơn.
  3. Gửi mức độ không có trong danh mục nhận 400.
  4. Nhân viên A không đọc được yêu cầu của nhân viên B; nhân viên tự duyệt đơn của mình bị từ chối; quản lý duyệt đơn chuyển trạng thái sang `DA_DUYET`.

### Nhiệm vụ 6.3 — Trang điều hành [D] và tích hợp Trợ lý [I]
- Kiểm chứng: bài kiểm Box: phiên `nhan_vien` vào trang điều hành nhận 403; phiên `quan_ly` nhận số liệu khớp dữ liệu vừa nạp; lời gọi tóm tắt trả về chữ tiếng Việt và thân yêu cầu gửi tới Ollama không chứa tên người.

### Nhiệm vụ 6.4 — Nối với trang chủ Box và máy trạm
- Các bước: trang chủ Box trỏ tới ứng dụng thay các thẻ biểu mẫu n8n và liên kết Open WebUI cũ; mục menu "Báo cần hỗ trợ" của máy trạm mở biểu mẫu mới (thông báo cho plan trải nghiệm: giai đoạn 3 và 6 của plan đó làm sau bước này).
- Kiểm chứng: `test_onebee_mdns_dashboard.py` đạt sau khi sửa kỳ vọng địa chỉ; `check-quan-ly-tap-trung.sh` đạt; CI `box=true` xanh.

## Todo
- [ ] 6.1 Khung ứng dụng và trang [H]
- [ ] 6.2 Biểu mẫu, đính kèm tệp và hàng đợi phê duyệt [P]
- [ ] 6.3 Trang điều hành [D] và tích hợp Trợ lý [I]
- [ ] 6.4 Nối với trang chủ Box và máy trạm

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Tóm tắt AI chậm trên máy yếu lúc trình diễn | Chờ quá 60 giây | Kịch bản trình diễn chạy sẵn một lần trước; trang hiện tiến trình. |
| Phạm vi phình ra | Đến 30/11 chưa xong 6.3 | Cắt phần [I] xuống một nút mở Trợ lý AI với câu hỏi điền sẵn; phải báo anh Thiện trước khi cắt. |

## Bảo mật
Dữ liệu người dùng chỉ hiện bằng `textContent`. Số liệu gửi cho AI là tổng hợp, không có tên, số điện thoại. Mọi quyền kiểm ở CSDL (RLS), không tin kiểm tra phía trình duyệt.

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
