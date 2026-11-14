---
title: "OLP 2026 — đưa OneBee OS thành DX-OS Open-Core"
description: "Vá điểm PoF, thêm 4 dịch vụ lõi bắt buộc (SSO, cổng API, dữ liệu cấu trúc và phi cấu trúc có API, workflow giấy phép OSI có phê duyệt), gỡ n8n và Open WebUI, một ứng dụng minh họa H-P-D-I và bản chạy thử công khai trước hạn nộp 17:00 ngày 06/12/2026."
status: pending
priority: P1
effort: "28d"
branch: main
tags: [feature, box, infra, docs, critical]
blockedBy: []
blocks: []
created: 2026-11-13
---

# OLP 2026 — đưa OneBee OS thành DX-OS Open-Core

## Tổng quan
Nguồn: phiên Antigravity `5350a6b2-0d39-4656-9eea-209b103f298e` (đối chiếu dự án với 3 file của cuộc thi) và việc em đọc lại
`Thể lệ` cùng `Đề thi` trong `~/Downloads`. Hạn gửi bài: **17:00 Chủ nhật 06/12/2026** (đề in nhầm năm 2025). Chấm kho mã 7–9/12, chung kết 10/12.
Mốc đóng băng mã của plan này: **03/12**.

Thang điểm: 50 điểm PoF chấm trên kho mã trước chung kết, 50 điểm sản phẩm chấm tại chung kết.
Đề bắt buộc: một **nền tảng lõi chạy ngầm, không giao diện** cung cấp Định danh/SSO, Cổng API, Quản trị dữ liệu cấu trúc/phi cấu trúc,
Động cơ luồng công việc; và **ít nhất một ứng dụng minh họa** trong không gian H-P-D-I.

## Điều em đã kiểm lại so với đánh giá của Antigravity
| Nhận định của Antigravity | Kết quả kiểm |
|---|---|
| 0 tệp mã có dòng giấy phép | Đúng: 0 trên 150 tệp mã được theo dõi. Thể lệ trừ 5 điểm. |
| Gói phát hành thiếu file `LICENSE` | Đúng: `scripts/dong-goi-ban-phat-hanh.sh:21-22` không đóng `LICENSE`. Thể lệ trừ 5 điểm. |
| n8n không phải giấy phép OSI | Đúng về giấy phép. Lưu ý: bảng công nghệ tham chiếu của Đề thi (Lớp 4) tự liệt kê n8n; anh vẫn chọn thay để chắc chắn. |
| Thiếu SSO, thiếu CSDL tập trung có API tự sinh | Đúng: mỗi dịch vụ tự giữ mật khẩu; đơn hàng, sổ hỗ trợ, khảo sát đang ghi CSV. |
| "Đáp ứng 65–70%" | Là ước lượng của Antigravity, không phải số đo. |
| Bảng BI, tác tử AI, P.A.R.A, MinIO là bắt buộc | Không bắt buộc theo mục 3 của Đề thi; để ngoài phạm vi (anh chọn "đủ yêu cầu bắt buộc"). |

## Rà soát lần 2 (13/11, đối chiếu lại 3 file chấm điểm) và quyết định của anh Thiện
| Lỗ hổng phát hiện | Quyết định | Nằm ở |
|---|---|---|
| Open WebUI dùng "BSD-3 + điều khoản thương hiệu" (từ v0.6.6), **không thuộc OSI**; plan cũ chỉ thay n8n nên Kết quả #2 không thể đạt | **Bỏ Open WebUI.** Trợ lý AI chuyển vào ứng dụng minh họa, gọi thẳng Ollama qua cổng API; RAG làm lại trên PostgreSQL + pgvector; `hoi` đổi sang địa chỉ mới | Giai đoạn 8 (mới); 2, 4 sửa |
| Dữ liệu phi cấu trúc chỉ có Samba, **không có API** cho ứng dụng tầng trên — sai yêu cầu bắt buộc mục 3 | **Thêm** kho tệp chuẩn đối tượng sau cổng API, kèm kiểm dịch mã độc (ClamAV) — đồng thời đáp ứng nguyên lý (iv) mục 4 | Giai đoạn 7 (mới) |
| Demo không có luồng phê duyệt chạy trên động cơ quy trình (trọng tâm không gian [P], BPMN) | **Thêm** quy trình phê duyệt: nhân viên gửi → quản lý duyệt/từ chối → thông báo | Giai đoạn 2 (tiêu chí chọn), 5, 6 |
| Không có bản chạy thử trên Internet (Đề khuyến khích; tiêu chí 11) | **Đưa lên host công khai** | Giai đoạn 9 (mới) |
| 4 nguyên lý mục 4 của Đề chưa được nhắc | Bảng ánh xạ trong tài liệu kiến trúc; làm thật phần kiểm dịch (gđ 7) và GitOps (bộ cài lần 2 `changed=0`) | Giai đoạn 10 |
| Dòng trừ điểm PoF chưa có bước kiểm: thông báo mục đích giấy phép, chạy ngoài thư mục mã nguồn, đính kèm gói dự án khác, bug tracker không dùng | Bổ sung bước kiểm | Giai đoạn 1, 10 |
| Thư mục `~/Downloads/OneBee-DX-OS` (bản Apache-2.0, lõi giả lập) | **Không dùng làm bài nộp.** Giấy phép: repo chính giữ **MIT** (OSI, có bản toàn văn là đủ). Chỉ tham khảo ý tưởng (BPMN mua sắm, vòng đời quét tệp, bảng ECharts) | — |

## Kết quả phải đạt
| # | Kết quả | Đo bằng |
|---|---|---|
| 1 | Mọi tệp mã có dòng `SPDX-License-Identifier: MIT`; gói phát hành có `LICENSE`; có `CHANGELOG.md` ở gốc; README có mục Giấy phép nêu mục đích | test trong CI; `tar tzf` gói phát hành |
| 2 | Không còn thành phần nào không thuộc giấy phép OSI trong bộ cài (n8n **và** Open WebUI đã gỡ) | `git grep -il "n8n\|open.webui"` chỉ còn trong `CHANGELOG.md` và `docs/adr`; `LICENSES.md` |
| 3 | Lõi chạy ngầm có đủ 4 dịch vụ: SSO, cổng API, dữ liệu cấu trúc (PostgreSQL có API tự sinh, phân quyền theo dòng) **và phi cấu trúc (kho tệp có API, kiểm dịch)**, động cơ quy trình | bài kiểm Box thật (CI `box=true`) |
| 4 | Một ứng dụng minh họa đi trọn vòng H → P → D → I, đăng nhập một lần, **có luồng phê duyệt chạy trên động cơ quy trình và đính kèm tệp** | bài kiểm Box thật + kịch bản trình diễn |
| 5 | Bộ cài chạy lần 2 `changed=0`; sao lưu và khôi phục gồm cả CSDL và kho tệp mới | runner Box hiện có |
| 6 | Bản phát hành có file tải trước 06/12; tài liệu kiến trúc 3 tầng dùng đúng thuật ngữ của Đề thi, có bảng 4 nguyên lý | `gh release view`; README |
| 7 | Bản chạy thử công khai truy cập được qua HTTPS bằng tài khoản demo, dữ liệu demo tự đặt lại hằng đêm | `curl -fsS https://<tên miền>/` từ ngoài mạng; bài kiểm khói của gđ 9 |

## Ràng buộc
- Giữ mọi chuẩn của repo (test trước, lần 2 `changed=0`, lint sạch, commit tiếng Việt, tác giả Dương Minh Thiện, không nhắc AI).
- Mọi thành phần mới phải có giấy phép OSI, kéo bằng image chính chủ ghim tag + digest, ghi vào `LICENSES.md`. Không đóng gói mã của dự án khác.
- Box mục tiêu vẫn là máy nhỏ (8–12 GB RAM) chạy cùng Ollama: tổng RAM thành phần mới không quá 1,5 GB lúc rảnh (đo ở giai đoạn 2).
- Lõi không có giao diện người dùng cuối; giao diện thuộc ứng dụng minh họa ở tầng trên.
- Không phá dữ liệu Box đã cài: có bước chuyển dữ liệu CSV sang CSDL và sao lưu trước khi chuyển.

- Bản chạy thử công khai (gđ 9) là bản **demo riêng**, dữ liệu giả lập rõ ràng; không mở Box của đơn vị thật ra Internet.

## Không làm
Bảng BI đầy đủ (Metabase/Superset), tác tử AI tự hành, cây thư mục P.A.R.A, MinIO (AGPL, nặng — dùng kho tệp nhẹ chọn ở ADR 0006), đa thuê ước, Lakehouse/IoT thật (nguyên lý (i), (ii) mục 4 chỉ ghi ở mức định hướng).

## Giai đoạn
| # | Giai đoạn | Người thực thi đề xuất | Cần xong trước | Công | Trạng thái |
|---|---|---|---|---|---|
| 1 | [Vá điểm PoF: giấy phép và đóng gói](./phase-01-va-diem-pof-giay-phep-va-dong-goi.md) | Sonnet hoặc Antigravity | — | 1,5 ngày | Chưa làm |
| 2 | [Thử nghiệm và chốt công nghệ lõi](./phase-02-thu-nghiem-va-chot-cong-nghe-loi.md) | Opus | — | 2 ngày | Chưa làm |
| 3 | [Dữ liệu cấu trúc: PostgreSQL và API tự sinh](./phase-03-du-lieu-cau-truc-postgresql-va-api-tu-sinh.md) | Opus | 2 | 3 ngày | Chưa làm |
| 4 | [Định danh SSO và cổng API](./phase-04-dinh-danh-sso-va-cong-api.md) | Opus | 2 | 3 ngày | Chưa làm |
| 5 | [Thay n8n bằng động cơ quy trình giấy phép OSI + quy trình phê duyệt](./phase-05-thay-n8n-bang-dong-co-quy-trinh-osi.md) | Antigravity + Sonnet | 3 | 5 ngày | Chưa làm |
| 6 | [Ứng dụng minh họa H-P-D-I](./phase-06-ung-dung-minh-hoa-h-p-d-i.md) | Opus | 3, 4, 5, 7, 8 | 3 ngày | Chưa làm |
| 7 | [Kho tệp đối tượng và kiểm dịch mã độc](./phase-07-kho-tep-doi-tuong-va-kiem-dich.md) | Opus | 2, 4 | 2,5 ngày | Chưa làm |
| 8 | [Gỡ Open WebUI: trợ lý AI và RAG trên lõi](./phase-08-go-open-webui-tro-ly-ai-va-rag-tren-loi.md) | Opus + Sonnet | 3, 4 | 3,5 ngày | Chưa làm |
| 9 | [Bản chạy thử công khai trên host](./phase-09-ban-chay-thu-cong-khai-tren-host.md) | Antigravity + anh Thiện | 4 (9.1); 6 (9.3) | 2 ngày | Chưa làm |
| 10 | [Tài liệu kiến trúc, phát hành và nộp bài](./phase-10-tai-lieu-kien-truc-phat-hanh-va-nop-bai.md) | Sonnet + anh Thiện | 1, 6, 9 | 2 ngày | Chưa làm |

Tổng công: khoảng 28 ngày công trong 21 ngày lịch (13/11 → 03/12) — **chỉ kịp khi chạy song song** theo lịch dưới (mỗi luồng một worktree, một agent):

| Ngày | Luồng A | Luồng B | Luồng C |
|---|---|---|---|
| 13–16/11 | 1 (vá PoF) | 2 (ADR, đo) | — |
| 17–21/11 | 3 (CSDL, API) | 4 (SSO, cổng API) | 9.1 (thuê host, tên miền, dựng nền) |
| 22–27/11 | 5 (thay n8n + phê duyệt) | 7 (kho tệp, kiểm dịch) | 8 (gỡ Open WebUI, RAG) |
| 28/11–01/12 | 6 (ứng dụng minh họa) | 9.2 (triển khai lõi lên host) | 10.1–10.2 (tài liệu) |
| 02–03/12 | 9.3 (đưa ứng dụng lên host, kiểm khói) | 10.3–10.4 | — |
| 04–05/12 | Dự phòng; 05/12 phát hành; **06/12 trước 17:00 gửi thư** | | |

Thứ tự cắt khi trễ (báo anh Thiện trước, không tự cắt): (1) RAG của gđ 8 xuống "hỏi đáp không tài liệu"; (2) phần [I] của gđ 6 xuống một nút mở trợ lý; (3) đặt lại dữ liệu demo hằng đêm của gđ 9 thành đặt lại thủ công. **Không cắt**: gỡ Open WebUI, gỡ n8n, kho tệp có API, quy trình phê duyệt — đây là phần chấm điểm.

## Quan hệ với plan trải nghiệm (`plans/261112-0720-toi-uu-trai-nghiem-nguoi-dung`)
Plan trải nghiệm đã gộp hết vào `main` và phát hành `v1.2.0` (14/11), kể cả PR #14 (Trợ lý AI trên Open WebUI) và PR #18 (trang chủ Box). Do đó:
- Các nhánh dở của plan này (`chore/giay-phep-tung-tep-va-dong-goi`, `docs/adr-0006-loi-dx-os`, `docs/adr-0007-thay-n8n`) phải rebase lên `origin/main` mới nhất trước khi làm tiếp.
- Nội dung của PR #14 (mẫu soạn văn bản, gợi ý tiếng Việt, dòng nhắc kiểm tra) đã có sẵn trên `main` — giai đoạn 8 kế thừa nguyên nội dung này và gỡ phần Open WebUI đi.
- Trang chủ Box (từ PR #18) và menu "Báo cần hỗ trợ" trên máy trạm sẽ được cập nhật địa chỉ mới ở giai đoạn 6.4.

## Quy ước cho người thực thi
Như plan trải nghiệm (mỗi giai đoạn một nhánh, một PR; không gộp, không gắn tag, không phát hành khi chưa có anh Thiện; kiểm chứng tại máy bằng
`~/.cache/onebee-kiem/bin/python`; cửa cuối là CI của PR, giai đoạn 3–8 thêm lần chạy `gh workflow run ci.yml --ref <nhánh> -f box=true`).
Các giai đoạn 3–9 chỉ được bắt đầu sau khi ADR của giai đoạn 2 đã gộp; tên công nghệ ghi trong các giai đoạn đó là **phương án đề xuất**, ADR là bản chốt.
Nhánh đã có sẵn (13/11): `chore/giay-phep-tung-tep-va-dong-goi` (gđ 1, PR #16 nháp), `docs/adr-0006-loi-dx-os` (gđ 2, bản nháp ADR chưa có số đo), `docs/adr-0007-thay-n8n` (gđ 5.1). Người thực thi tiếp tục trên các nhánh này, không tạo nhánh trùng.

## Việc của anh Thiện (không model nào làm thay được)
- Đăng ký đội qua trường (tối đa 3 sinh viên, có giảng viên hướng dẫn) theo Thể lệ; cho em biết tên đội để ghi vào hồ sơ.
- Quyết định dự án giữ song song tư cách dự thi Hội thi KNĐMST Tây Ninh hay không (ảnh hưởng dòng cuối README).
- Duyệt ADR chốt công nghệ (giai đoạn 2), gộp PR, cho phát hành, và gửi thư nộp bài.
- Giai đoạn 9: chọn và trả tiền host, tên miền; tạo khóa SSH cho bộ cài; tự đăng nhập bảng điều khiển nhà cung cấp (model không giữ thông tin thanh toán hay mật khẩu tài khoản host).

## Câu hỏi còn mở
1. Host cho bản chạy thử: nhà cung cấp và ngân sách? Yêu cầu tối thiểu ở gđ 9 (8 GB RAM, 4 vCPU, 80 GB SSD, Ubuntu 24.04). Đã có tên miền chưa?
2. Biểu mẫu đang dùng tài khoản chung `nhanvien`; khi có SSO, mỗi nhân viên một tài khoản — đơn vị thử nghiệm có chấp nhận không?
3. Box đơn vị đang dùng Open WebUI (lịch sử chat, kho tri thức đã nạp): khi nâng cấp có cần chuyển lịch sử chat không, hay chỉ chuyển tài liệu tri thức? (Mặc định của gđ 8: chỉ chuyển tài liệu, lịch sử chat giữ nguyên thư mục cũ và ghi rõ.)

## Quy tắc khi kiểm chứng không đạt
Nếu một bước Kiểm chứng không đạt đúng điều kiện đã ghi, DỪNG giai đoạn này.
Không tự nghĩ cách sửa khác, không thử lại mù, không lập luận để bỏ qua lỗi, không nới lỏng test.
Gọi subagent `kongming` để xin hướng xử lý và gửi kèm: số giai đoạn và số nhiệm vụ, những bước đã làm,
lệnh đã chạy và toàn bộ đầu ra của nó, điều kiện đạt mà nó không thỏa.
Làm theo hướng dẫn của kongming rồi chạy lại bước Kiểm chứng.
Nếu môi trường không gọi được `kongming` (ví dụ Antigravity), DỪNG và báo lại đúng các bằng chứng trên cho anh Thiện.
