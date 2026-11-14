---
phase: 8
title: "Giai đoạn 8: Gỡ Open WebUI — trợ lý AI và RAG trên lõi"
status: todo
priority: P1
effort: "3.5d"
dependencies: [3, 4]
---

# Giai đoạn 8: Gỡ Open WebUI — trợ lý AI và RAG trên lõi

Nhánh: `feat/go-open-webui-rag-tren-loi`. Bắt đầu sau khi giai đoạn 3 và 4 có nền CSDL + cổng API.

## Mục tiêu
Gỡ bỏ hoàn toàn Open WebUI (giấy phép có điều khoản thương hiệu ngoài OSI) khỏi bộ cài, thay bằng dịch vụ hỏi đáp & RAG giấy phép MIT/Apache-2.0 đặt trên lõi (PostgreSQL `pgvector` + Ollama), giữ đủ tính năng trợ lý cho ứng dụng minh họa ở tầng 2 và lệnh `hoi` trên máy trạm.

## Điều cần biết
- Open WebUI đang xuất hiện ở khoảng 33 tệp trong repo (`box-ai`, `box-stack`, `Caddyfile.j2`, `docker-compose.yml.j2`, `hoi`, `LICENSES.md`, các bài test `check-ai-chat-inside.sh`, `check-rag-prompts.sh`, `test_onebee_webui.py`, `test_onebee_rag_prompts.py`, `test_onebee_hoi.py`...).
- Kho tri thức mẫu văn bản hành chính NĐ 30/2020 và prompt tiếng Việt đã có sẵn trên `main` trong `box/ansible/roles/box-ai/files/knowledge/`, `prompts/` (gồm cả phần mẫu soạn thảo văn bản, gợi ý tiếng Việt và dòng nhắc kiểm tra từ PR #14 đã gộp vào `main`).
- Lệnh `hoi` trên máy trạm đang gọi API của Open WebUI.
- Quy định: không xóa lịch sử chat cũ trên Box đang vận hành — chuyển sang thư mục `open-webui.da-thay-<ngày>` và chỉ di chuyển tài liệu tri thức sang kho mới.

## Nhiệm vụ

### Nhiệm vụ 8.1 — Kiểm kê điểm đụng và thiết kế dịch vụ AI + RAG nhẹ trên lõi
- Các bước: tạo danh sách đầy đủ các tệp nhắc tới Open WebUI bằng `git grep -il "open.webui\|open_webui\|openwebui" -- . ':!plans'`; thiết kế dịch vụ Python nhẹ (`onebee-ai-rag`, giấy phép MIT trong repo) gọi Ollama trực tiếp (`http://ollama:11434`) kết hợp truy xuất vector trên bảng `tai_lieu_tri_thuc` (`pgvector`) trong PostgreSQL.
- Kiểm chứng: test đơn vị hàm phân đoạn văn bản, tìm kiếm ngữ nghĩa giả lập, tạo prompt kèm trích dẫn nguồn và dòng nhắc kiểm tra; kiểm `chen-giay-phep.py --kiem` đạt.

### Nhiệm vụ 8.2 — Nạp kho tri thức và nối với cổng `/ai/`
- Các bước: đưa kho tri thức NĐ 30 và mẫu soạn thảo (kế thừa từ `box-ai/files/` trên `main`) thành tập nạp tự động vào `tai_lieu_tri_thuc`; mở điểm cuối `/ai/hoi`, `/ai/tom-tat`, `/ai/mau` qua cổng Caddy (`forward_auth` hoặc bearer token theo người dùng); không lưu PII vào prompt gửi Ollama khi tóm tắt số liệu.
- Kiểm chứng: bài kiểm Box: gọi `/ai/hoi` không phiên nhận 401; gọi với phiên hợp lệ trả về câu trả lời tiếng Việt có trích nguồn tài liệu nội bộ; bộ kiểm 40 câu tiếng Việt / `check-rag-prompts.sh` (cập nhật sang điểm cuối mới) đạt.

### Nhiệm vụ 8.3 — Cập nhật lệnh `hoi` trên máy trạm
- Các bước: sửa `desktop/ansible/roles/ai-cli/files/hoi` (và hướng dẫn liên quan) để gọi thẳng `/ai/hoi` qua cổng Caddy có ghim CA nội bộ như cũ, sử dụng khóa API/token người dùng do `onebee-box` cấp (tương thích `onebee-box xoay-khoa`).
- Kiểm chứng: `test_onebee_hoi.py` đạt; `check-ai-chat-inside.sh` (chuyển sang kiểm tra `/ai/hoi` và `hoi`) đạt.

### Nhiệm vụ 8.4 — Gỡ hoàn toàn Open WebUI khỏi bộ cài và tài liệu
- Các bước: xóa container `open-webui`, `box/ansible/roles/box-ai/files/onebee-webui.py`, biến `open_webui` trong `all.yml`, cổng `3000` (nếu không còn dịch vụ nào dùng), test `test_onebee_webui.py`; bộ cài dừng và gỡ container Open WebUI cũ (giữ dữ liệu dưới tên `open-webui.da-thay-<ngày>`); cập nhật `LICENSES.md`, `onebee-box` (`in-khoa`, `xoay-khoa`, `chan-doan`).
- Kiểm chứng (đủ 3): `git grep -il "open.webui\|open_webui\|openwebui" -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr'` không in gì; CI của PR xanh; lần chạy `box=true` xanh với lần cài hai `changed=0`.

## Todo
- [ ] 8.1 Kiểm kê và viết dịch vụ `onebee-ai-rag` (MIT)
- [ ] 8.2 Nạp tri thức NĐ 30 + mẫu trên `main` và nối cổng `/ai/`
- [ ] 8.3 Cập nhật lệnh `hoi` trên máy trạm
- [ ] 8.4 Gỡ sạch Open WebUI, CI `box=true` xanh

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Sinh vector embedding trên CPU quá chậm khi nạp hàng loạt | Quá trình cài Box treo lâu ở bước nạp tri thức | Chạy trước vector cho bộ tài liệu tĩnh hoặc dùng model embedding nhẹ (`nomic-embed-text` / `all-minilm`) hay truy vấn toàn văn `tsvector` của PostgreSQL làm dự phòng nếu CPU yếu. |
| Không kịp xong toàn bộ RAG trước hạn | Đến 27/11 chưa xong 8.2 | Báo anh Thiện để dùng phương án cắt đã định: bỏ phần tìm kiếm vector, chỉ giữ gọi thẳng Ollama kèm prompt hệ thống + mẫu văn bản. Không giữ Open WebUI trong bộ cài mặc định. |

## Bảo mật
Không mở cổng `11434` của Ollama ra LAN. Toàn bộ gọi AI phải đi qua `/ai/` trên Caddy có xác thực danh tính và giới hạn tốc độ (rate limit).

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.

