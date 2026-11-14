---
phase: 3
title: "Giai đoạn 3: Dữ liệu cấu trúc — PostgreSQL và API tự sinh"
status: todo
priority: P1
effort: "3d"
dependencies: [2]
---

# Giai đoạn 3: Dữ liệu cấu trúc — PostgreSQL và API tự sinh

Nhánh: `feat/box-co-so-du-lieu-va-api`. Bắt đầu sau khi ADR 0006 đã gộp; công nghệ theo ADR.

## Mục tiêu
Một nguồn dữ liệu duy nhất thay các tệp CSV rời: đơn hàng, yêu cầu hỗ trợ, khảo sát, tình trạng máy trạm; có API sinh tự động và phân quyền tới cấp dòng.

## Điều cần biết
- Dữ liệu hiện ghi CSV dưới `/srv/onebee/` bởi các quy trình n8n 04, 05, 06, 07, 08, 09; `onebee-bao-cao-tuan.py` và `onebee-may-tram.py` đọc các tệp đó.
- Sao lưu Box (`onebee-box-sao-luu.sh.j2`) tạm dừng container rồi chụp `/srv/onebee`; CSDL phải được kết xuất (`pg_dump`) trước khi chụp để bản sao lưu nhất quán.
- Quy tắc của dự án: sao lưu trước mọi thay đổi lược đồ hay dữ liệu.

## Nhiệm vụ

### Nhiệm vụ 3.1 — Role `box-du-lieu`: PostgreSQL (`pgvector`) và PostgREST
- Các bước: thêm 2 dịch vụ vào `docker-compose.yml.j2` (image PostgreSQL kèm mở rộng `pgvector` ghim tag + digest trong `group_vars/all.yml`, `no-new-privileges`, không công bố cổng ra LAN); mật khẩu sinh vào `/etc/onebee-box/secrets`; lược đồ khởi tạo bằng tệp SQL có đánh số trong role.
- Lược đồ tối thiểu:
  - Các bảng tác nghiệp hiện có: `don_hang`, `yeu_cau_ho_tro`, `xu_ly_ho_tro`, `khao_sat`, `tinh_trang_may` (cột lấy đúng theo cột CSV hiện có), kèm cột `trang_thai_duyet`, `nguoi_duyet`, `ly_do_duyet`, `thoi_gian_duyet` và ràng buộc `CHECK` cho các danh mục (loại sự cố, mức độ, trạng thái phê duyệt — quy tắc Poka-yoke không cho tự duyệt đơn của chính mình) — đây là rào chắn dữ liệu sai ở tầng lõi.
  - Bảng `tep_dinh_kem`: lưu metadata tệp phi cấu trúc gắn với đơn/yêu cầu và trạng thái kiểm dịch (`PENDING_SCAN`, `CLEAN`, `INFECTED`) cho giai đoạn 7.
  - Bảng `tai_lieu_tri_thuc` (dùng mở rộng `vector`) và `lich_su_hoi_ai`: phục vụ RAG nội bộ ở giai đoạn 8.
- Phân quyền: vai trò `nhan_vien` (thêm và đọc dòng của mình, không được sửa đơn đã gửi duyệt), `ky_thuat`, `quan_ly` (đọc tổng hợp và duyệt/từ chối đơn không phải của mình); bật RLS trên mọi bảng.
- Kiểm chứng: test đơn vị đọc compose và SQL (có RLS trên mọi bảng, không cổng nào công bố, có ràng buộc không tự duyệt); `tests/kiem-tra-mau-jinja.py` 0 lỗi.

### Nhiệm vụ 3.2 — Chuyển dữ liệu CSV sang CSDL
- Các bước: lệnh `onebee-box chuyen-du-lieu` đọc các CSV hiện có, sao lưu chúng sang `*.truoc-chuyen`, nạp vào bảng, in số dòng từng bảng; chạy lại không nạp trùng.
- Kiểm chứng: test với CSV mẫu trong `tests/box/fixtures/`: số dòng trong bảng bằng số dòng CSV; chạy lần hai số dòng không đổi.

### Nhiệm vụ 3.3 — Báo cáo tuần và tình trạng máy trạm đọc từ CSDL
- Các bước: `onebee-bao-cao-tuan.py` đọc qua một lớp truy cập dữ liệu duy nhất (có test với CSDL giả lập bằng tệp SQL mẫu); giữ nguyên định dạng báo cáo.
- Kiểm chứng: các test hiện có của `test_onebee_bao_cao_tuan.py` vẫn đạt, không sửa kết quả mong đợi.

### Nhiệm vụ 3.4 — Sao lưu, khôi phục, chẩn đoán
- Các bước: `cmd_sao_luu` kết xuất CSDL trước khi chụp; `khoi-phuc-toan-bo` nạp lại; `onebee-box chan-doan` thêm mục CSDL và API.
- Kiểm chứng: bài kiểm Box thật (`check-khoi-phuc-toan-bo.sh` bổ sung bước: tạo 1 đơn hàng trước khi hỏng ổ, sau khôi phục còn đúng đơn đó); `gh run watch <mã> --exit-status` thoát mã 0 và lần cài hai `changed=0`.

## Todo
- [ ] 3.1 PostgreSQL và PostgREST
- [ ] 3.2 Chuyển dữ liệu CSV
- [ ] 3.3 Báo cáo đọc từ CSDL
- [ ] 3.4 Sao lưu, khôi phục, chẩn đoán

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Mất dữ liệu khi chuyển | Số dòng lệch | Lệnh chuyển dừng, giữ nguyên CSV và bản `*.truoc-chuyen`; không xóa CSV trong plan này. |
| Sao lưu không nhất quán | Khôi phục thiếu dòng mới nhất | Kết xuất CSDL phải nằm trong cùng lần tạm dừng dịch vụ của `cmd_sao_luu`. |

## Bảo mật
API không công bố ra LAN, chỉ đi qua cổng API ở giai đoạn 4. Mật khẩu CSDL sinh ngẫu nhiên, chỉ root đọc, có trong `onebee-box xoay-khoa --box`.

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
