---
phase: 10
title: "Giai đoạn 10: Tài liệu kiến trúc, phát hành và nộp bài"
status: todo
priority: P1
effort: "2d"
dependencies: [1, 6, 9]
---

# Giai đoạn 10: Tài liệu kiến trúc, phát hành và nộp bài

Nhánh: `docs/ho-so-olp-2026`. Phải xong trước 03/12.

## Mục tiêu
Ban giám khảo mở kho mã là thấy ngay kiến trúc 3 tầng, 4 nguyên lý thiết kế, cách cài từ mã nguồn, bản phát hành chuẩn PoF và bản chạy thử công khai; anh Thiện có đủ thứ để gửi thư nộp bài và trình diễn 15 phút.

## Nhiệm vụ

### Nhiệm vụ 10.1 — Tài liệu kiến trúc DX-OS và 4 nguyên lý
- File: tạo `docs/kien-truc-dx-os.md`, `ROADMAP.md`; sửa `README.md`, `LICENSES.md`.
- Các bước:
  1. Sơ đồ 3 tầng dùng đúng tên trong Đề thi (`Tầng Nền tảng Dịch vụ Lõi số`, `Tầng Không gian Năng lực số` H-P-D-I, `Tầng Nền tảng Kinh doanh số`).
  2. Bảng ánh xạ từng dịch vụ lõi bắt buộc của Đề thi sang thành phần của dự án kèm giấy phép OSI (xác nhận lại không còn n8n và Open WebUI).
  3. **Bảng đối chiếu 4 nguyên lý thiết kế (mục 4 Đề thi)**:
     - (i) Tách dữ liệu nóng/lạnh: nêu phần đã có (PostgreSQL OLTP nóng vs restic đóng băng bất biến) và phần định hướng (Lakehouse/Iceberg).
     - (ii) Hội tụ IT/OT: nêu phần đã có (tình trạng máy trạm `onebee-bao-tinh-trang` gộp vào cùng CSDL tác nghiệp) và phần định hướng (IoT/NGSI-LD).
     - (iii) Quản trị dữ liệu & chất lượng: nêu ràng buộc `CHECK`, RLS, bảng kiểm toán/lịch sử, OpenAPI tự sinh từ PostgREST (chỉ xuất tài liệu tham khảo hoặc qua cổng).
     - (iv) Zero-Trust + GitOps + kiểm dịch mã độc biên mạng: nêu Caddy `forward_auth` + Authelia + kiểm dịch ClamAV tại `/files/` + Ansible idempotent `changed=0` (chạy định kỳ/tự phục hồi).
     - Ghi rạch ròi phần **đã chạy thật** và phần **định hướng**, tuyệt đối không tô vẽ.
  4. `README.md`: đoạn mở đầu nêu DX-OS Open-Core, liên kết tới bản chạy thử công khai (từ giai đoạn 9) và `ROADMAP.md`; mục Giấy phép có câu nêu mục đích cấp phép MIT; giữ hay bỏ dòng Hội thi Tây Ninh theo quyết định của anh Thiện.
- Kiểm chứng: `grep -c "Tầng Nền tảng Dịch vụ Lõi số\|Tầng Không gian Năng lực số" docs/kien-truc-dx-os.md` in số lớn hơn hoặc bằng `2`; `grep -c "Zero-Trust\|hội tụ\|nóng" docs/kien-truc-dx-os.md` >= `2`; mọi thành phần trong bảng có trong `LICENSES.md`.

### Nhiệm vụ 10.2 — Hướng dẫn cài từ mã nguồn, tài liệu API và danh sách tự chấm PoF
- File: tạo `docs/olp-2026-tu-cham-pof.md` (đầy đủ 6 tiêu chí, **tất cả các dòng trừ điểm của Thể lệ** kèm bằng chứng là đường dẫn tệp hoặc lệnh kiểm); tạo `docs/api/openapi-dxos.md` (mô tả `/api/`, `/files/`, `/ai/`); rà `docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md` cho khớp các dịch vụ mới (Authelia, PostgreSQL, kho tệp, động cơ quy trình, AI mới; bỏ n8n và Open WebUI).
- Kiểm chứng:
  1. `docs/olp-2026-tu-cham-pof.md` có đủ 6 tiêu chí và kiểm đủ cả: mục đích giấy phép, `LICENSE` trong gói phát hành, hoạt động khi giải nén ngoài thư mục mã nguồn (test giải nén gói phát hành ra `/tmp/kiem-ngoai` và chạy kiểm thử cấu hình/đơn vị từ đó thành công), không đóng gói dự án khác vào bản phát hành, và bug tracker có issue đang hoạt động.
  2. Mọi lệnh kiểm trong đó chạy được và cho kết quả như ghi.

### Nhiệm vụ 10.3 — Kịch bản trình diễn 15 phút và video dự phòng
- File: tạo `docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md` theo 4 nội dung Đề thi yêu cầu (thiết kế và lựa chọn công nghệ, tính năng nền tảng và bài toán minh họa, kết quả và demo trực tiếp trên bản host công khai + Box, định hướng).
- Các bước thêm: soạn đề cương slide trình bày và quay 1 video dự phòng 3–5 phút luồng demo phòng mất mạng ở hội trường.
- Kiểm chứng: có đủ 4 mục và thời lượng từng mục cộng lại không quá 15 phút.

### Nhiệm vụ 10.4 — Phát hành và nộp bài (việc của anh Thiện, model chỉ chuẩn bị)
- Các bước: đổi tiêu đề mục `[Unreleased]` thành `[1.3.0]` (hoặc số mới sau `v1.2.0`) trong `CHANGELOG.md`; chạy thử `scripts/dong-goi-ban-phat-hanh.sh`; kiểm tra lại **không** đính kèm gói USB offline (chứa Docker image/package bên thứ ba) vào GitHub Release dự thi; soạn sẵn nội dung thư nộp bài theo mẫu ở mục 5 của Đề thi vào `docs/hoi-thi/olp-2026-thu-nop-bai.md` (có link kho mã nguồn + link bản chạy thử công khai, để trống tên đội, thành viên, giảng viên).
- Kiểm chứng: script đóng gói in `Đã tạo:`; gói có `LICENSE` và có thể giải nén sang thư mục khác để kiểm thử; `git grep -il "n8n\|open.webui\|openwebui" -- . ':!plans' ':!CHANGELOG.md' ':!docs/adr'` không in gì. Dừng: gộp, tạo Release trên GitHub (chỉ kèm mã nguồn `.tar.gz`/`.tar.xz` và checksum) và **gửi thư tới `olpvietnam@vaip.vn`, `thuky@vfossa.vn` trước 17:00 ngày 06/12** là việc của anh Thiện.

## Todo
- [ ] 10.1 Tài liệu kiến trúc DX-OS, 4 nguyên lý, ROADMAP
- [ ] 10.2 Cài từ mã nguồn, tài liệu API và tự chấm PoF (kể cả kiểm ngoài thư mục nguồn)
- [ ] 10.3 Kịch bản trình diễn 15 phút + slide + video dự phòng
- [ ] 10.4 Chuẩn bị phát hành (không kèm gói bên thứ ba) và thư nộp bài

## Rủi ro
| Rủi ro | Dấu hiệu | Xử lý đã định |
|---|---|---|
| Giai đoạn 5, 6, 7, 8 hoặc 9 trễ | 01/12 chưa gộp | Viết tài liệu đúng theo cái đã gộp; phần chưa xong ghi là định hướng. Không ghi tính năng chưa có như đã có. |

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
