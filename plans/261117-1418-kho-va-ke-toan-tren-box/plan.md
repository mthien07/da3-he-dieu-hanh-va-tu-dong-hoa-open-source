---
plan: kho-va-ke-toan-tren-box
created: 2026-11-17
status: in_progress
branch: feat/box-kho-ke-toan
base: feat/dx-os-tich-hop
owner: Dương Minh Thiện
---

# Kho và kế toán trên OneBee Box

## Kết quả mong đợi

Trên Box test (192.168.100.127) chạy trọn một luồng bán hàng thật:

1. Thủ kho tạo mặt hàng và nhập kho (có phiếu nhập, tồn tăng, giá vốn bình quân cập nhật).
2. Nhân viên gửi đơn bán hàng chọn mặt hàng từ danh mục.
3. Quản lý duyệt đơn: CSDL tự sinh **phiếu xuất kho** và **bút toán kế toán** trong cùng giao dịch; tồn không đủ thì **chặn duyệt** kèm lời báo tiếng Việt rõ ràng.
4. Kế toán xem **sổ nhật ký kép** (Nợ/Có theo tài khoản) và **bảng cân đối tài khoản**; mọi sổ tải được **CSV** mở bằng LibreOffice/Excel, lọc theo khoảng ngày.

## Ràng buộc

- Giữ nguyên kiến trúc: PostgreSQL + PostgREST + cầu nối danh tính + RLS, trang tĩnh Sổ điều hành không thư viện ngoài.
- Lược đồ mới luôn là tệp mới trong `box/ansible/roles/box-du-lieu/files/luoc-do/` (001–005 đã áp dụng, không sửa).
- Mọi quyền kiểm ở CSDL (RLS + GRANT), không tin kiểm tra phía trình duyệt.
- Thời gian theo giờ Việt Nam, dữ liệu người dùng chỉ vào trang bằng `textContent`.
- Bộ cài chạy lại phải đạt `changed=0 failed=0`.
- Tiếng Việt toàn bộ: giao diện, thông báo lỗi, tài liệu, commit.

## Quyết định của anh Thiện (17/11/2026)

| Vấn đề | Quyết định |
|---|---|
| Mức kế toán | **Nhật ký kép đủ tài khoản** (131, 511, 156, 632, 111…), có sổ nhật ký chung và bảng cân đối tài khoản |
| Kho khi duyệt đơn | **Tự trừ tồn, chặn khi thiếu**; có phiếu nhập kho để tăng tồn |
| Xuất dữ liệu | **Nút tải CSV trên trang Sổ điều hành**, lọc theo khoảng ngày |
| Phân quyền | **Thêm vai trò `thu_kho` và `ke_toan`** bên cạnh `nhan_vien`, `ky_thuat`, `quan_ly` |

## Kiến trúc đã chốt

```
Nhân viên ── gửi đơn ──▶ onebee.don_hang (CHO_DUYET)
                              │ quản lý duyệt (PUT trang_thai_duyet)
                              ▼
              trigger AFTER UPDATE (cùng giao dịch)
              ├─ phiếu xuất kho  onebee.phieu_kho (XUAT) + dòng
              │    └─ trigger chặn tồn âm: khoá dòng mat_hang, so tồn thực
              ├─ bút toán doanh thu  Nợ 131 / Có 511 = thành tiền
              └─ bút toán giá vốn    Nợ 632 / Có 156 = số lượng × giá vốn bình quân

Thủ kho ── nhập kho (RPC them_nhap_kho, một giao dịch) ──▶ phiếu nhập + dòng
              ├─ cập nhật giá vốn bình quân gia quyền của mặt hàng
              └─ bút toán nhập kho  Nợ 156 / Có 111

Kế toán ── đọc so_nhat_ky, bang_can_doi (RLS: chỉ ke_toan + quan_ly)
```

## Trạng thái (17/11/2026)

| Giai đoạn | Trạng thái |
|---|---|
| 1. Lược đồ kho + kế toán | Xong, đã kiểm trên PostgreSQL tạm (nhập 100 kg, duyệt 30 kg, chặn 500 kg, quyền bốn vai trò) |
| 2. Vai trò thu_kho, ke_toan | Xong mã; chờ kiểm trên Box |
| 3. Giao diện khu Kho, kế toán, CSV | Xong mã; chờ kiểm trên Box |
| 4. Dữ liệu mẫu + bài kiểm cũ | Xong; nạp thử trên PostgreSQL tạm, bút toán mở kho cân |
| 5. Kiểm thử Box | Xong: bài kiểm đầu-cuối đạt toàn bộ trên Box test; cài lại `changed=0` |
| 6. Tài liệu | Xong: hướng dẫn sử dụng, README, changelog, báo cáo kiểm thử |

## Các giai đoạn

| # | Giai đoạn | Tệp chính | Phụ thuộc |
|---|---|---|---|
| 1 | Lược đồ kho + kế toán, RPC nhập kho, trigger duyệt đơn | `luoc-do/006-kho-va-ke-toan.sql`, `luoc-do/007-phan-quyen-kho-ke-toan.sql` | — |
| 2 | Vai trò mới xuyên suốt: Authelia, cầu nối danh tính, PG, `onebee-box them-nguoi` | `box-dinh-danh`, `box-stack`, `group_vars/all.yml` | 1 |
| 3 | Giao diện Sổ điều hành: khu Kho, khu Kế toán, chọn mặt hàng khi tạo đơn, xuất CSV | `box-stack/templates/so-dieu-hanh.html.j2`, `box-stack/files/so-dieu-hanh.js`, `.css` | 1, 2 |
| 4 | Dữ liệu mẫu + cập nhật bài kiểm cũ (đơn cũ phải có mặt hàng và tồn trước khi duyệt) | `scripts/nap-du-lieu-demo.sql`, `tests/box/check-so-dieu-hanh.sh` | 1 |
| 5 | Kiểm thử tự động: unit + bài kiểm Box mới `check-kho-ke-toan.sh`, chạy cài trên Box test | `tests/box/` | 1–4 |
| 6 | Tài liệu: hướng dẫn dùng sổ kho/kế toán, README, changelog | `docs/huong-dan/`, `README.md`, `docs/project-changelog.md` | 5 |

## Tiêu chí nghiệm thu

1. Tạo mặt hàng "Mật ong" (kg, giá vốn 70.000) và nhập 100 kg giá 70.000 → tồn 100, bút toán Nợ 156 / Có 111 = 7.000.000.
2. Nhân viên gửi đơn 30 kg × 100.000 → quản lý duyệt → phiếu xuất 30 kg, tồn 70; bút toán Nợ 131 / Có 511 = 3.000.000 và Nợ 632 / Có 156 = 2.100.000; mọi bút toán cân Nợ = Có.
3. Gửi đơn 500 kg → duyệt bị **chặn**, thông báo nêu đúng mặt hàng, tồn còn, số cần; đơn vẫn `CHO_DUYET`.
4. Không nhập được số lượng âm hoặc xuất quá tồn qua API (CSDL từ chối, mã lỗi rõ).
5. `nhan_vien` gọi sổ kế toán nhận 403; `ke_toan` đọc được sổ nhưng không duyệt đơn; `thu_kho` nhập kho được nhưng không đọc sổ kế toán.
6. Trang Sổ điều hành có khu Kho (tồn, phiếu, form nhập) và khu Kế toán (nhật ký, cân đối), mỗi sổ có nút **Xuất CSV** lọc theo ngày, tải về mở đúng tiếng Việt trong LibreOffice.
7. Chạy lại bộ cài trên Box test: `changed=0 failed=0`; 12 dịch vụ vẫn khỏe; `sudo onebee-box chan-doan` không thêm lỗi mới.
8. `python3 -m unittest` của bộ kiểm tĩnh và `check-kho-ke-toan.sh` trên Box đều đạt; CI xanh.

## Không nằm trong phạm vi (non-goals)

- Không làm quản lý nhiều kho/địa điểm, không theo lô–hạn dùng, không giá vốn từng lô (FIFO).
- Không làm báo cáo thuế, tờ khai, kết chuyển cuối kỳ, khoá sổ.
- Không sửa động cơ quy trình Node-RED cho nghiệp vụ kho (dùng trigger CSDL + RPC).
- Không nhập dữ liệu sổ cũ của kho/kế toán (chưa có nguồn).

## Rủi ro

| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Trigger duyệt đơn làm hỏng bài kiểm cũ | `check-so-dieu-hanh.sh` đỏ vì mặt hàng "Mật ong" chưa có tồn | Cập nhật bài kiểm: tạo mặt hàng + nhập tồn trước khi duyệt (giai đoạn 4) |
| Duyệt đơn làm nghẽn vì khoá dòng khi nhiều người duyệt cùng lúc | Hai quản lý duyệt cùng mặt hàng | `SELECT … FOR UPDATE` trên `mat_hang`, giao dịch ngắn; sai hiếm gặp vẫn an toàn |
| Vai trò mới làm hỏng đường đăng nhập | Người dùng `thu_kho` đăng nhập bị 403 | Kiểm bằng bài Box: đăng nhập, `/api/toi` trả đúng vai trò; thiếu thì cầu nối chưa nạp lại |
| Giao diện phình to, khó bảo trì | Tệp JS quá lớn | Giữ một tệp, chia hàm theo khu; không thêm thư viện |

## Quy tắc khi kiểm chứng không đạt

Nếu một bước kiểm chứng không đạt đúng điều kiện đã ghi: DỪNG, không nới lỏng test, không thử mù.
Ghi lại lệnh đã chạy và đầu ra, rồi báo anh Thiện (hoặc gọi `kongming` xin hướng nếu cần).
