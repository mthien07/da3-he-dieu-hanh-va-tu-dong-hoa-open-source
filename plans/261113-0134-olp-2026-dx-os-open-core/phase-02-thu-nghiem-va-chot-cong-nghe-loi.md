---
phase: 2
title: "Giai đoạn 2: Thử nghiệm và chốt công nghệ lõi"
status: todo
priority: P1
effort: "2d"
dependencies: []
---

# Giai đoạn 2: Thử nghiệm và chốt công nghệ lõi

Nhánh: `docs/adr-0006-loi-dx-os`. Sản phẩm là một ADR có số đo, không sửa bộ cài.

## Mục tiêu
Chốt bằng số đo thật 5 thành phần lõi (thêm kho tệp đối tượng có API, kiểm dịch mã độc, và gỡ Open WebUI) trước khi viết mã, vì chọn sai sẽ mất nhiều ngày trong thời gian còn lại.

## Phương án đề xuất (phải kiểm, chưa phải bản chốt)
| Dịch vụ lõi của Đề thi | Đề xuất | Giấy phép | Lý do | Phương án lùi |
|---|---|---|---|---|
| Định danh, SSO, MFA | Authelia | Apache-2.0 | Nhẹ, là nhà cung cấp OIDC, làm `forward_auth` với Caddy, có TOTP | Keycloak (Apache-2.0, nặng hơn nhiều) |
| Cổng API, biên mạng | Caddy (đang dùng) | Apache-2.0 | Đã có CA nội bộ, chỉ thêm tuyến `/api/`, `/files/`, `/ai/` và xác thực chuyển tiếp | Apache APISIX |
| Dữ liệu cấu trúc + API tự sinh + Vector | PostgreSQL (+ `pgvector`) + PostgREST | PostgreSQL License, MIT | API sinh từ lược đồ, phân quyền tới cấp dòng bằng RLS; `pgvector` làm RAG thay kho của Open WebUI | Directus (kiểm lại giấy phép trước khi dùng) |
| Dữ liệu phi cấu trúc có API + Kiểm dịch | SeaweedFS (S3/HTTP API) + ClamAV + Samba/restic | Apache-2.0, GPL-2.0, GPL-3.0, BSD-2 | Đáp ứng kho đối tượng có API (mục 3 Đề) và kiểm dịch mã độc biên mạng (nguyên lý iv mục 4) | Garage (AGPL — tránh), hoặc FastAPI + ổ đĩa cục bộ nếu RAM vượt ngưỡng |
| Động cơ quy trình (có phê duyệt) | Flowable OSS (BPMN 2.0) hoặc Node-RED / Kestra | Apache-2.0 | Cần có tác vụ chờ người duyệt (Human Task / Approval) cho không gian [P] | Node-RED (Apache-2.0) kết hợp bảng trạng thái phê duyệt trên PostgreSQL nếu Flowable quá nặng RAM |
| Trí tuệ AI (thay Open WebUI) | Ollama (đang dùng) + API/UI nội bộ trong ứng dụng | MIT | Bỏ Open WebUI (không thuộc OSI); ứng dụng tầng 2 và lệnh `hoi` gọi qua cổng API | — |

## Nhiệm vụ

### Nhiệm vụ 2.1 — Xác minh giấy phép từ nguồn chính thức
- Các bước: với mỗi thành phần trong bảng (bao gồm SeaweedFS, ClamAV, `pgvector`, Flowable, và bản chính thức của model Gemma 4), mở tệp `LICENSE` ở kho mã chính thức đúng phiên bản định ghim; ghi tên giấy phép SPDX, URL, và việc nó có trong danh sách OSI không. Ghi rõ phần nào của sản phẩm (nếu có) thuộc giấy phép khác (ví dụ Open WebUI bị loại khỏi bộ cài vì điều khoản thương hiệu ngoài OSI).
- Kiểm chứng: bảng trong ADR có đủ các dòng thành phần lõi (kể cả kho tệp, kiểm dịch, AI model), mỗi dòng có URL tới tệp giấy phép chính thức.

### Nhiệm vụ 2.2 — Dựng thử trên Box thử và đo
- Các bước: dùng container Box giữ lại của `tests/box/run-box-test-in-systemd-container.sh` (`ONEBEE_TEST_KEEP=1`) hoặc một tệp compose thử trong thư mục tạm ngoài repo. Dựng PostgreSQL (`pgvector`) + PostgREST + Authelia + SeaweedFS + ClamAV + động cơ quy trình cạnh Ollama. Đo: RAM lúc rảnh của từng container (`docker stats --no-stream`), thời gian khởi động, kích thước image.
- Tiêu chí chọn động cơ quy trình: tổng RAM các thành phần mới (chưa tính Ollama) không vượt quá **1,5 GB** (nếu tính cả ClamAV thì đo riêng con số có/không có ClamAV để chốt cấu hình bật/tắt `freshclam` tối ưu RAM) **và** động cơ quy trình làm được 5 việc mẫu: chạy theo lịch, nhận webhook, gửi thư qua SMTP, gọi Ollama, và **tạm dừng chờ người quản lý duyệt/từ chối rồi đi tiếp**. Nếu Flowable vượt quá RAM ngân sách, chọn Node-RED (`Apache-2.0`) hoặc Kestra quản lý trạng thái tác vụ người duyệt qua PostgreSQL.
- Kiểm chứng: ADR có bảng số đo kèm lệnh đã chạy; nêu rõ phương án tối ưu RAM nếu tổng vượt 1,5 GB.

### Nhiệm vụ 2.3 — Thử ba điểm ghép nối rủi ro nhất
- Các bước: (a) Caddy `forward_auth` với Authelia bảo vệ một trang tĩnh và chuyển tiếp tới Ollama (`/ai/`); (b) PostgREST nhận JWT và RLS chỉ cho người dùng thấy dòng của mình; (c) Tải lên một tệp qua API tới SeaweedFS và kích hoạt kiểm tra virus bằng ClamAV (`clamdscan` / EICAR test string).
- Kiểm chứng: ADR ghi kết quả từng điểm (đạt hoặc không, kèm lệnh `curl` và mã trả về). Điểm nào không đạt thì ADR nêu cách thay.

### Nhiệm vụ 2.4 — Viết ADR và PR
- File: cập nhật `docs/adr/0006-loi-dx-os-open-core.md` (bối cảnh, quyết định, số đo, hệ quả, phương án bị loại — nêu rõ lý do loại Open WebUI và n8n), cập nhật `README.md` bảng tài liệu.
- Kiểm chứng: `gh pr checks --watch` thoát mã 0. Dừng: anh Thiện duyệt ADR rồi mới làm giai đoạn 3–9.

## Todo
- [ ] 2.1 Xác minh giấy phép (gồm SeaweedFS, ClamAV, pgvector, Flowable, Gemma 4)
- [ ] 2.2 Dựng thử và đo (gồm tiêu chí luồng phê duyệt và ngân sách RAM)
- [ ] 2.3 Thử ba điểm ghép nối
- [ ] 2.4 ADR và PR

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Không có Docker tại máy | Không dựng được Box thử | Chạy phần đo trên CI (`box=true`) bằng một nhánh thử, ghi số từ nhật ký CI. |
| ClamAV và Flowable cùng lúc ngốn > 1,5 GB RAM | Tổng RAM vượt mức trên máy 8 GB | Dùng Node-RED thay Flowable (tiết kiệm ~500 MB) hoặc chạy ClamAV theo cơ chế `clamscan` theo đợt / giới hạn DB chữ ký thay vì daemon thường trú; ghi rõ trong ADR. |

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
