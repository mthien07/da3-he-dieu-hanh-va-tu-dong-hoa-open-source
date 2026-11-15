# Bảng Tự Chấm 40 Tiêu chí Proof of Freedom (PoF) — OLP 2026

Tài liệu này đối chiếu trực tiếp **40 tiêu chí đánh giá Proof of Freedom (PoF) & Kiến trúc DX-OS Open-Core** của Khối Phần mềm nguồn mở OLP 2026 với bằng chứng mã nguồn, kịch bản kiểm thử và tài liệu trong kho lưu trữ **OneBee OS v1.3.0**.

---

## Nhóm A — Pháp lý Nguồn mở & Chống Khóa chặt (10/10 tiêu chí)

| # | Tiêu chí PoF | Trạng thái | Bằng chứng trong kho mã nguồn |
|---|---|---|---|
| A1 | Kho mã nguồn có giấy phép chuẩn OSI tại thư mục gốc | ĐẠT | `LICENSE` (MIT License) |
| A2 | 100% tệp mã nguồn có dòng định danh `SPDX-License-Identifier: MIT` | ĐẠT | `scripts/chen-giay-phep.py --kiem` & `tests/desktop/test_onebee_giay_phep.py` |
| A3 | Kiểm tra tự động header giấy phép trên CI/CD | ĐẠT | `.github/workflows/ci.yml` (bước `python3 scripts/chen-giay-phep.py --kiem`) |
| A4 | Không sử dụng thành phần Source-Available / Sustainable Use License (công cụ fair-code cũ) | ĐẠT | Đã thay hoàn toàn bằng Node-RED (`Apache-2.0`) — xem `docs/adr/0007-thay-công cụ fair-code cũ.md` |
| A5 | Không sử dụng thành phần giới hạn thương hiệu (`giao diện AI bên thứ ba >= 0.6.6`) | ĐẠT | Đã thay bằng dịch vụ `onebee-ai-rag.py` (`MIT`) — xem `docs/adr/0006-loi-dx-os-open-core.md` |
| A6 | Danh mục đầy đủ giấy phép của toàn bộ container và gói phụ thuộc | ĐẠT | `LICENSES.md` (100% giấy phép chuẩn OSI: MIT, Apache-2.0, PostgreSQL, BSD, GPL-2.0) |
| A7 | Có tài liệu hướng dẫn đóng góp cộng đồng | ĐẠT | `CONTRIBUTING.md` |
| A8 | Có chính sách công bố lỗ hổng bảo mật và kiểm toán | ĐẠT | `SECURITY.md` & `docs/security-audit.md` |
| A9 | Có lịch sử phiên bản chuẩn Keep a Changelog và lộ trình phát triển | ĐẠT | `CHANGELOG.md` (`[1.3.0]`) & `ROADMAP.md` |
| A10 | Kịch bản đóng gói bản phát hành kèm đầy đủ hồ sơ pháp lý | ĐẠT | `scripts/dong-goi-ban-phat-hanh.sh` & `tests/desktop/test_onebee_phien_ban.py` |

---

## Nhóm B — Kiến trúc 3 Tầng & 4 Trụ cột H-P-D-I (10/10 tiêu chí)

| # | Tiêu chí PoF | Trạng thái | Bằng chứng trong kho mã nguồn |
|---|---|---|---|
| B1 | Có tài liệu khảo sát, chấm điểm định lượng và chọn thành phần lõi | ĐẠT | `docs/adr/0006-loi-dx-os-open-core.md` (QĐ1–QĐ7) |
| B2 | Tách biệt rõ 3 tầng kiến trúc (Giao tiếp, Điều phối, Lưu trữ) | ĐẠT | `docs/kien-truc-dx-os.md` & `box/ansible/roles/box-stack/templates/docker-compose.yml.j2` |
| B3 | Trụ cột `[H]` (Con người & Định danh): SSO tập trung 1 lần đăng nhập | ĐẠT | `box/ansible/roles/box-dinh-danh/templates/authelia-configuration.yml.j2` |
| B4 | Trụ cột `[P]` (Quy trình & Phê duyệt): Luồng tạo phiếu và duyệt phiếu tự động | ĐẠT | `box/ansible/roles/box-quy-trinh/templates/flows.json.j2` |
| B5 | Trụ cột `[D]` (Dữ liệu): CSDL quan hệ + tìm kiếm ngữ nghĩa Vector + kho tệp S3 | ĐẠT | `box/ansible/roles/box-du-lieu/files/01-luoc-do-dxos.sql` + `SeaweedFS` |
| B6 | Trụ cột `[I]` (Trí tuệ Nhân tạo): RAG nội bộ + mẫu văn bản Nghị định 30 | ĐẠT | `box/ansible/roles/box-ai/files/onebee-ai-rag.py` |
| B7 | Giao diện hợp nhất "Sổ điều hành HTX" gom đủ `[H]-[P]-[D]-[I]` trên 1 trang | ĐẠT | `box/ansible/roles/box-stack/templates/so-dieu-hanh.html.j2` |
| B8 | Đặc tả OpenAPI / REST chuẩn cho toàn bộ dịch vụ nội bộ | ĐẠT | `docs/api/openapi-dxos.md` |
| B9 | Công cụ di trú dữ liệu lịch sử từ CSV sang PostgreSQL không mất dữ liệu | ĐẠT | `box/ansible/roles/box-du-lieu/files/onebee-chuyen-du-lieu.py` |
| B10 | Tương thích ngược với công cụ CLI `hoi` trên máy trạm thông qua chuẩn OpenAI `/v1` | ĐẠT | `box/ansible/roles/box-ai/files/onebee-ai-rag.py` & `desktop/ansible/roles/ai-cli/files/hoi` |

---

## Nhóm C — An toàn Bảo mật, Phân quyền RLS & Poka-yoke (10/10 tiêu chí)

| # | Tiêu chí PoF | Trạng thái | Bằng chứng trong kho mã nguồn |
|---|---|---|---|
| C1 | Mọi đường dẫn nhạy cảm (`/api/`, `/files/`, `/ai/`, `/so-dieu-hanh/`) bắt buộc qua ForwardAuth | ĐẠT | `box/ansible/roles/box-stack/templates/Caddyfile.j2` |
| C2 | Cầu nối đúc JWT HS256 ngắn hạn (60 giây) từ header định danh Authelia | ĐẠT | `box/ansible/roles/box-dinh-danh/files/onebee-cau-noi.py` |
| C3 | Giải mã an toàn tên hiển thị tiếng Việt UTF-8 (RFC 2047 / URL-encoded) trong header SSO | ĐẠT | `giai_ma_header_utf8` trong `onebee-cau-noi.py` |
| C4 | Phân quyền Row-Level Security (RLS) tại tầng PostgreSQL cho `nhan_vien`, `ky_thuat`, `quan_ly` | ĐẠT | `01-luoc-do-dxos.sql` (`ENABLE ROW LEVEL SECURITY` + `CREATE POLICY`) |
| C5 | Ràng buộc Poka-yoke cấm người tạo tự duyệt phiếu của chính mình (`nguoi_duyet <> nguoi_tao`) | ĐẠT | `chk_poka_yoke_khong_tu_duyet` trong `01-luoc-do-dxos.sql` + luồng 11 Node-RED + UI |
| C6 | Ràng buộc Poka-yoke bắt buộc nhập lý do tối thiểu 3 ký tự khi từ chối phiếu (`TU_CHOI`) | ĐẠT | `chk_poka_yoke_ly_do_tu_choi` trong `01-luoc-do-dxos.sql` + luồng 11 Node-RED + UI |
| C7 | Quét mã độc tự động bằng ClamAV cho mọi tệp tải lên trước khi đưa vào SeaweedFS | ĐẠT | `box/ansible/roles/box-kho-tep/files/onebee-kho-tep.py` (`quet_clamav`) |
| C8 | Cách ly tức thời tệp nhiễm mã độc / chuỗi thử EICAR vào vùng Quarantine với trạng thái `INFECTED` | ĐẠT | `onebee-kho-tep.py` & `tests/box/test_onebee_dxos_core.py` |
| C9 | Khử mã độc công thức bảng tính (CSV Injection Sanitization) khi xuất báo cáo CSV | ĐẠT | `box/ansible/roles/box-quy-trinh/templates/_csv-js.j2` |
| C10 | Chế độ khẩn cấp tắt SSO tạm thời có thời hạn tự đóng (`15m`/`1h`) và ghi nhật ký kiểm toán | ĐẠT | `cmd_tat_sso_tam` trong `onebee-cau-noi.py` (`audit-sso.log`) |

---

## Nhóm D — Vận hành Ngoại tuyến, Tự phục hồi & Kiểm thử Tự động (10/10 tiêu chí)

| # | Tiêu chí PoF | Trạng thái | Bằng chứng trong kho mã nguồn |
|---|---|---|---|
| D1 | Hoạt động 100% ngoại tuyến (Air-gapped LAN) không phụ thuộc đám mây bên ngoài | ĐẠT | `scripts/dong-goi-usb-ngoai-tuyen.sh` & `docs/usb-cai-dat-ngoai-tuyen.md` |
| D2 | Cầu nối sinh mã TOTP 6 số tại chỗ khi máy người dùng lệch giờ hoặc không có điện thoại | ĐẠT | `sudo onebee-box ma-xac-minh <user>` (`onebee-cau-noi.py`) |
| D3 | Cập nhật cơ sở dữ liệu chữ ký ClamAV ngoại tuyến qua USB | ĐẠT | `sudo onebee-box cap-nhat-chu-ky-clamav <tep>` (`onebee-kho-tep.py`) |
| D4 | Sao lưu mã hóa tự động hằng đêm bằng Restic kèm kết xuất `pg_dump` PostgreSQL | ĐẠT | `box/ansible/roles/box-stack/templates/onebee-box-sao-luu.sh.j2` |
| D5 | Công cụ chẩn đoán 1 lệnh kiểm tra phần cứng, 11 container, kho Restic và nhật ký cảnh báo | ĐẠT | `box/ansible/roles/box-stack/templates/onebee-box-chan-doan.sh.j2` |
| D6 | Báo cáo tổng hợp tuần tự động và ẩn danh hóa PII trước khi nhờ AI tóm tắt | ĐẠT | `box/ansible/roles/box-fleet/files/onebee-bao-cao-tuan.py` & `/ai/tom-tat` |
| D7 | Hỗ trợ chế độ máy chủ Demo công khai kèm banner tài khoản mẫu và timer khôi phục dữ liệu 03:00 | ĐẠT | `box/ansible/inventory.demo.ini.example` & `scripts/nap-du-lieu-demo.sql` |
| D8 | Kiểm thử tự động kết xuất toàn bộ mẫu Jinja2 của Ansible | ĐẠT | `python3 tests/kiem-tra-mau-jinja.py` |
| D9 | Kiểm thử đơn vị (Unit Tests) cho Box, Desktop, AI và các mô-đun lõi DX-OS | ĐẠT | `tests/box/test_onebee_dxos_core.py` cùng toàn bộ suite trong `tests/` |
| D10 | Kịch bản trình diễn 10 phút và thư nộp bài hoàn chỉnh cho Ban Giám khảo | ĐẠT | `docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md` & `docs/hoi-thi/olp-2026-thu-nop-bai.md` |
