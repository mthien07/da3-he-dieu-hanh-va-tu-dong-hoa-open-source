<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Bảng tự chấm điểm Vòng Sơ khảo / PoF — OLP 2026 (50/50 điểm)

Tài liệu đối chiếu từng tiêu chí chấm điểm Proof-of-Foundation (PoF) và toàn bộ quy định trừ điểm trong Thể lệ OLP 2026 với **đường dẫn tệp thực tế** và **lệnh kiểm chứng chạy được** trong kho mã nguồn OneBee DX-OS.

---

## 1. Bảng tự đánh giá 6 tiêu chí PoF (50 điểm)

| TT | Tiêu chí PoF (Thể lệ OLP 2026) | Điểm tối đa | Tự chấm | Bằng chứng cụ thể trong kho mã & Lệnh kiểm chứng |
|---|---|---|---|---|
| **1** | **Kho mã nguồn công khai & công cụ quản lý mã nguồn** (web viewer, lịch sử commit rõ ràng, Bug/Issue tracker hoạt động) | **5** | **5/5** | Kho GitHub công khai tại `github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source`, cấu hình `.github/ISSUE_TEMPLATE/`, lịch sử commit mạch lạc theo Conventional Commits (`git log --oneline -20`). |
| **2** | **Giấy phép nguồn mở chuẩn OSI** (gắn `SPDX-License-Identifier: MIT` ở tệp mã, nêu mục đích chọn giấy phép ở `README.md`, có `LICENSE`, 100% thành phần phụ thuộc dùng giấy phép OSI) | **10** | **10/10** | Toàn văn giấy phép MIT tại [LICENSE](../LICENSE); bảng kê đầy đủ thành phần OSI tại [LICENSES.md](../LICENSES.md) & [ADR 0006](adr/0006-loi-dx-os-open-core.md); mục đích giấy phép nêu rõ trong [README.md](../README.md). Kiểm tra tự động: `python3 scripts/chen-giay-phep.py --kiem` (khi gộp GĐ 1) và kiểm thử quét loại trừ sạch thành phần ngoài OSI trong [test_olp_2026_ho_so.py](../tests/box/test_olp_2026_ho_so.py). |
| **3** | **Phát hành theo phiên bản trên định dạng mở** (GitHub Release gắn tag, tệp nén chuẩn `.tar.gz` kèm mã kiểm `SHA256SUMS`) | **5** | **5/5** | Workflow phát hành tự động [.github/workflows/phat-hanh.yml](../.github/workflows/phat-hanh.yml) và script [scripts/dong-goi-ban-phat-hanh.sh](../scripts/dong-goi-ban-phat-hanh.sh) xuất `dist/onebee-os-<ver>.tar.gz` + `SHA256SUMS` + `ghi-chu-phat-hanh.md`. Kiểm tra: `bash scripts/dong-goi-ban-phat-hanh.sh 1.3.0`. |
| **4** | **Hướng dẫn cài đặt từ mã nguồn, cấu hình chuẩn, hoạt động độc lập ngoài thư mục mã nguồn** | **10** | **10/10** | Hướng dẫn từng bước tại [docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md](huong-dan/huong-dan-cai-dat-tu-a-den-z.md) và [docs/api/openapi-dxos.md](api/openapi-dxos.md); tách toàn bộ cấu hình sang [box/ansible/group_vars/all.yml](../box/ansible/group_vars/all.yml) và [desktop/ansible/group_vars/all.yml](../desktop/ansible/group_vars/all.yml). Kiểm chứng giải nén ngoài cây Git tại `/tmp/kiem-ngoai`: toàn bộ test Jinja và unittest chạy bình thường không phụ thuộc đường dẫn tuyệt đối hay repo Git. |
| **5** | **Khai báo đầy đủ thư viện phụ thuộc & không phát hành lẫn mã/nhị phân dự án khác** | **10** | **10/10** | Liệt kê 100% phụ thuộc tại [LICENSES.md](../LICENSES.md) và [requirements-dev.txt](../requirements-dev.txt). Script [scripts/dong-goi-ban-phat-hanh.sh](../scripts/dong-goi-ban-phat-hanh.sh) dùng `git archive HEAD` chỉ đóng gói mã nguồn, hướng dẫn, script, kiểm thử của dự án — **không** đính kèm gói USB offline chứa Docker image hay gói `.deb` bên thứ ba trong GitHub Release `v1.3.0`. |
| **6** | **Bug tracker & Tài liệu đồng bộ thực tế** (`CHANGELOG.md`, `README.md`, kiến trúc, lộ trình khớp mã nguồn 100%) | **10** | **10/10** | Nhật ký phiên bản tại [CHANGELOG.md](../CHANGELOG.md) & [docs/project-changelog.md](project-changelog.md); tài liệu kiến trúc [docs/kien-truc-dx-os.md](kien-truc-dx-os.md); lộ trình [ROADMAP.md](../ROADMAP.md); kiểm chứng tự động bằng [tests/box/test_olp_2026_ho_so.py](../tests/box/test_olp_2026_ho_so.py) và `tests/desktop/test_onebee_phien_ban.py`. |

**Tổng điểm tự chấm PoF:** **50 / 50 điểm**.

---

## 2. Kiểm soát các điểm có nguy cơ bị trừ điểm theo Thể lệ

| Hạng mục kiểm soát trừ điểm | Trạng thái | Cách xác minh cụ thể |
|---|---|---|
| Chứa thành phần không thuộc danh sách giấy phép OSI (mục fair-code SUL, mục có điều khoản thương hiệu > 50 người dùng, `libclamunrar`) | **Đã loại bỏ / ngăn chặn** | Đã thay thế sạch ở GĐ 5, GĐ 8 và loại `libclamunrar` khỏi ClamAV (ADR 0006 QĐ5); chuyển trọn sang Node-RED (`Apache-2.0`), `onebee-ai-rag.py` (`MIT`) và `clamscan` (`GPL-2.0-only`). Kiểm chứng tại [test_olp_2026_ho_so.py](../tests/box/test_olp_2026_ho_so.md) -> 0 vi phạm. |
| Thiếu tệp `LICENSE` toàn văn hoặc thiếu thông báo mục đích cấp phép | **Đạt** | Có [LICENSE](../LICENSE) tại gốc kho và trong `.tar.gz`; [README.md](../README.md) có đoạn giải thích lý do chọn MIT cho nền tảng và tương thích thương mại cho HTX/SME. |
| Không chạy/kiểm thử được khi giải nén ra ngoài thư mục Git nguồn | **Đã kiểm** | Giải nén `dist/onebee-os-<ver>.tar.gz` vào `/tmp/kiem-ngoai`: không phụ thuộc thư mục `.git`, chạy `python3 tests/kiem-tra-mau-jinja.py` và unit test thành công. |
| Bản phát hành đính kèm Docker image hoặc file `.deb` bên thứ ba | **Không vi phạm** | Chỉ xuất file mã nguồn `.tar.gz`, `SHA256SUMS`, `ghi-chu-phat-hanh.md` lên GitHub Release. |
| Thông tin tài liệu "nói quá" tính năng chưa kiểm chứng thực tế | **Đã rà soát** | Cả [README.md](../README.md) và [docs/kien-truc-dx-os.md](kien-truc-dx-os.md) đều ghi rạch ròi hạng mục đã nghiệm thu trong container/VM vs hạng mục định hướng tương lai. |
