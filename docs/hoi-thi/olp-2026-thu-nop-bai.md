# Thư Nộp Bài & Hồ sơ Bàn giao — Khối Phần mềm Nguồn mở OLP 2026

**Kính gửi:** Hội đồng Giám khảo Khối Phần mềm Nguồn mở — Cuộc thi Olympic Tin học Sinh viên Việt Nam (OLP 2026)  
**Tên dự án:** **OneBee OS v1.3.0 — Khung Nền tảng Chuyển đổi số Lõi Mở (DX-OS Open-Core) cho Doanh nghiệp Siêu nhỏ và Hợp tác xã (MSME/HTX)**  
**Giấy phép phát hành:** MIT License (`SPDX-License-Identifier: MIT`) — 100% thành phần thực thi tuân thủ chuẩn OSI.

---

## 1. Tóm tắt Giải pháp (Executive Summary)

**OneBee OS v1.3.0** giải quyết bài toán chuyển đổi số thực chiến cho các Hợp tác xã và Doanh nghiệp siêu nhỏ tại Việt Nam: chi phí phần cứng thấp (chạy trọn vẹn trên 1 Mini PC 8–16 GB RAM và các máy trạm Ubuntu cũ), hoạt động bền bỉ ngay cả khi mất kết nối Internet (Offline-First), và loại bỏ hoàn toàn rủi ro khóa chặt nhà cung cấp (Anti-Vendor Lock-in).

Phiên bản `v1.3.0` hoàn thiện kiến trúc **DX-OS Open-Core 3 tầng** xoay quanh 4 trụ cột **`[H]` Con người & Định danh — `[P]` Quy trình & Poka-yoke — `[D]` Dữ liệu & Kho tệp an toàn — `[I]` Trí tuệ nhân tạo & Văn bản Nghị định 30**:

1. **100% Chuẩn OSI (Proof of Freedom)**:
   - Thay thế triệt để công cụ fair-code cũ (Sustainable Use License) bằng **Node-RED (`Apache-2.0`)** kèm 11 luồng nghiệp vụ và phê duyệt tự động.
   - Thay thế `giao diện AI bên thứ ba` (giấy phép sửa đổi kèm điều khoản bảo hộ thương hiệu từ v0.6.6+) bằng dịch vụ **`onebee-ai-rag.py` (`MIT`)** tích hợp tìm kiếm toàn văn SQLite FTS5, ẩn danh hóa PII và sinh văn bản hành chính theo **Nghị định 30/2020/NĐ-CP**.
2. **Bảo mật Mặc định theo Vai trò (Zero-Trust RBAC & RLS)**:
   - Xác thực tập trung qua **Authelia (`Apache-2.0`)** + **Caddy ForwardAuth** kết hợp **Cầu nối JWT (`onebee-cau-noi.py`)** cấp JWT ngắn hạn (60 giây) xuống **PostgreSQL 16 + `pgvector` + PostgREST** với chính sách **Row-Level Security (RLS)** cho 3 vai trò `nhan_vien`, `ky_thuat`, `quan_ly`.
3. **Chống sai sót Poka-yoke & Kiểm dịch Mã độc Tự động**:
   - Giao diện hợp nhất **Sổ điều hành HTX (`/so-dieu-hanh/`)** kết hợp ràng buộc Poka-yoke 3 lớp (UI + Node-RED + PostgreSQL `CHECK` constraint) ngăn người tạo tự duyệt phiếu của chính mình và bắt buộc ghi lý do khi từ chối.
   - Cổng tệp **`onebee-kho-tep.py`** quét mọi tệp đính kèm bằng **ClamAV (`GPL-2.0`)** trước khi lưu vào **SeaweedFS (`Apache-2.0`)**, tự động cách ly tức thời tệp chứa mã độc (`INFECTED`).

---

## 2. Danh mục Hồ sơ & Đường dẫn Nhanh cho Ban Giám khảo

| Hạng mục Đánh giá | Đường dẫn Tài liệu / Mã nguồn trong Kho lưu trữ |
|---|---|
| **1. Kiến trúc 3 Tầng & 4 Nguyên tắc Thiết kế** | `docs/kien-truc-dx-os.md` |
| **2. Báo cáo Khảo sát & Chấm điểm Lõi Mở (ADR 0006 & 0007)** | `docs/adr/0006-loi-dx-os-open-core.md` & `docs/adr/0007-thay-công cụ fair-code cũ.md` |
| **3. Bảng Tự Chấm 40 Tiêu chí Proof of Freedom (PoF)** | `docs/olp-2026-tu-cham-pof.md` |
| **4. Đặc tả OpenAPI / REST của các Dịch vụ DX-OS** | `docs/api/openapi-dxos.md` |
| **5. Kịch bản Trình diễn Trực tiếp 10 Phút** | `docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md` |
| **6. Hồ sơ Pháp lý, Đóng góp, Bảo mật & Lộ trình** | `LICENSE`, `LICENSES.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `ROADMAP.md` |
| **7. Lược đồ PostgreSQL RLS & Ràng buộc Poka-yoke** | `box/ansible/roles/box-du-lieu/files/01-luoc-do-dxos.sql` |
| **8. Cầu nối Định danh SSO -> JWT & Giải mã UTF-8** | `box/ansible/roles/box-dinh-danh/files/onebee-cau-noi.py` |
| **9. 11 Luồng Nghiệp vụ Node-RED & Sổ điều hành HTX** | `box/ansible/roles/box-quy-trinh/templates/flows.json.j2` & `box/ansible/roles/box-stack/templates/so-dieu-hanh.html.j2` |
| **10. Dịch vụ Kho tệp ClamAV + SeaweedFS & AI RAG** | `box/ansible/roles/box-kho-tep/files/onebee-kho-tep.py` & `box/ansible/roles/box-ai/files/onebee-ai-rag.py` |

---

## 3. Lệnh Kiểm chứng Nhanh (Quick Verification Commands)

Ban Giám khảo có thể kiểm chứng ngay tính toàn vẹn của kho mã nguồn mà không cần máy ảo phụ trợ bằng 3 lệnh chuẩn sau:

```bash
# 1. Kiểm tra 100% tệp mã nguồn mang định danh SPDX-License-Identifier: MIT
python3 scripts/chen-giay-phep.py --kiem

# 2. Kiểm tra kết xuất toàn bộ mẫu cấu hình Ansible Jinja2 của hệ thống
python3 tests/kiem-tra-mau-jinja.py

# 3. Chạy toàn bộ bộ kiểm thử đơn vị (Box + Desktop + AI + DX-OS Core)
python3 -m unittest discover -s tests/box -p "test_*.py"
python3 -m unittest discover -s tests/desktop -p "test_*.py"
python3 -m unittest discover -s tests/ai -p "test_*.py"
```

---

## 4. Thông tin Tài khoản Trình diễn Mặc định (Chế độ Demo)

Khi triển khai với `onebee_box_che_do_demo=true` (xem `box/ansible/inventory.demo.ini.example`), hệ thống tạo sẵn 3 tài khoản SSO đại diện cho 3 nhóm quyền RBAC:

- **Nhân viên nghiệp vụ (`nhan_vien`)**: `nhanvien1` / `OneBee@2026`
- **Kỹ thuật viên đơn vị (`ky_thuat`)**: `kythuat1` / `OneBee@2026`
- **Ban Giám đốc phê duyệt (`quan_ly`)**: `quanly1` / `OneBee@2026`

Trân trọng cảm ơn Hội đồng Giám khảo!
