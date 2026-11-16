-- SPDX-License-Identifier: MIT
-- Dữ liệu giả lập cho bản chạy thử công khai: nạp idempotent, tự đặt lại lúc 03:00 mỗi ngày.
-- Chạy bằng tài khoản chủ CSDL trong container (bộ cài và bộ hẹn giờ gọi):
--   docker exec -i onebee-postgres psql -X -q -U postgres -d onebee -v ON_ERROR_STOP=1 < nap-du-lieu-demo.sql
-- Dòng mẫu mang nguon = 'nap-du-lieu-demo' và dong, nên chạy lại không sinh thêm dòng.
-- Dòng do người dùng tạo qua API (nguon IS NULL) bị xóa để mỗi ngày trở về trạng thái mẫu;
-- dòng chuyển từ sổ cũ (nguon là tên tệp) được giữ nguyên. Máy trạng thái mẫu mang tên demo-*.

BEGIN;

-- Không để trigger duyệt ghi đè người duyệt/giờ duyệt của dữ liệu mẫu (chỉ trong giao dịch này).
-- Bản ghi mẫu có nguon khác NULL nên trigger "đơn mới" cũng không can thiệp.
SET LOCAL session_replication_role = replica;

-- Bỏ dòng phát sinh (API: nguon NULL) và dòng mẫu thừa trước khi nạp lại
DELETE FROM onebee.xu_ly_ho_tro WHERE nguon IS NULL OR (nguon = 'nap-du-lieu-demo' AND dong > 1);
DELETE FROM onebee.yeu_cau_ho_tro WHERE nguon IS NULL OR (nguon = 'nap-du-lieu-demo' AND dong > 3);
DELETE FROM onebee.don_hang WHERE nguon IS NULL OR (nguon = 'nap-du-lieu-demo' AND dong > 5);
DELETE FROM onebee.khao_sat WHERE nguon IS NULL OR (nguon = 'nap-du-lieu-demo' AND dong > 3);
DELETE FROM onebee.tinh_trang_may WHERE ten LIKE 'demo-%';

-- Đơn hàng mẫu: đủ ba trạng thái duyệt để trình diễn hàng đợi và lịch sử
INSERT INTO onebee.don_hang
  (thoi_gian, khach_hang, mat_hang, so_luong_kg, don_gia, thanh_tien, ngay_giao, ghi_chu,
   nguoi_tao, nguon, dong, trang_thai_duyet, nguoi_duyet, ly_do_duyet, thoi_gian_duyet)
VALUES
  (onebee_noi_bo.bay_gio() - interval '2 days', 'Cửa hàng Xanh Tây Ninh', 'Gạo ST25 vụ Đông Xuân', 500, 37000, 18500000,
   '2026-11-20', 'Đơn mẫu đã phê duyệt', 'nhanvien1', 'nap-du-lieu-demo', 1, 'DA_DUYET', 'quanly1',
   'Đủ hàng, đã đối chiếu tồn kho', onebee_noi_bo.bay_gio() - interval '1 day'),
  (onebee_noi_bo.bay_gio() - interval '1 day', 'Siêu thị Miền Đông', 'Hạt điều rang muối đóng hộp 500g', 200, 62000, 12400000,
   '2026-11-22', 'Chờ quản lý phê duyệt hai bước', 'nhanvien1', 'nap-du-lieu-demo', 2, 'CHO_DUYET', NULL, NULL, NULL),
  (onebee_noi_bo.bay_gio() - interval '7 hours', 'Nhà phân phối Hòa Thành', 'Mật ong hoa nhãn đóng chai 500ml', 100, 79000, 7900000,
   '2026-11-21', 'Đính kèm hợp đồng PDF đã kiểm dịch', 'nhanvien1', 'nap-du-lieu-demo', 3, 'CHO_DUYET', NULL, NULL, NULL),
  (onebee_noi_bo.bay_gio() - interval '3 hours', 'Bếp ăn Khu công nghiệp', 'Xoài cát chu đóng thùng 10kg', 400, 23000, 9200000,
   '2026-11-25', 'Bản nháp chờ kiểm tra tồn kho', 'nhanvien1', 'nap-du-lieu-demo', 4, 'CHO_DUYET', NULL, NULL, NULL),
  (onebee_noi_bo.bay_gio() - interval '3 days', 'Tổ hợp tác số 3', 'Phân bón hữu cơ vi sinh bao 25kg', 200, 30500, 6100000,
   '2026-11-19', 'Thiếu phụ lục giao hàng', 'nhanvien1', 'nap-du-lieu-demo', 5, 'TU_CHOI', 'quanly1',
   'Thiếu phụ lục giao hàng', onebee_noi_bo.bay_gio() - interval '2 days')
ON CONFLICT (nguon, dong) DO UPDATE SET
  thoi_gian = EXCLUDED.thoi_gian,
  khach_hang = EXCLUDED.khach_hang,
  mat_hang = EXCLUDED.mat_hang,
  so_luong_kg = EXCLUDED.so_luong_kg,
  don_gia = EXCLUDED.don_gia,
  thanh_tien = EXCLUDED.thanh_tien,
  ngay_giao = EXCLUDED.ngay_giao,
  ghi_chu = EXCLUDED.ghi_chu,
  nguoi_tao = EXCLUDED.nguoi_tao,
  trang_thai_duyet = EXCLUDED.trang_thai_duyet,
  nguoi_duyet = EXCLUDED.nguoi_duyet,
  ly_do_duyet = EXCLUDED.ly_do_duyet,
  thoi_gian_duyet = EXCLUDED.thoi_gian_duyet;

-- Yêu cầu hỗ trợ mẫu: loại và mức độ đúng danh mục biểu mẫu
INSERT INTO onebee.yeu_cau_ho_tro
  (ma, thoi_gian, may, loai, muc_do, nguoi_bao, mo_ta, nguoi_tao, nguon, dong)
VALUES
  ('DEMO-HT-001', onebee_noi_bo.bay_gio() - interval '3 hours', 'demo-ketoan-01', 'Máy in / máy quét', 'gap',
   'nhanvien1', 'Máy in hóa đơn USB không nhận lệnh in', 'nhanvien1', 'nap-du-lieu-demo', 1),
  ('DEMO-HT-002', onebee_noi_bo.bay_gio() - interval '2 days', 'demo-ketoan-01', 'Gõ tiếng Việt', 'binh-thuong',
   'nhanvien1', 'Gõ Telex trong LibreOffice Writer bị mất dấu', 'nhanvien1', 'nap-du-lieu-demo', 2),
  ('DEMO-HT-003', onebee_noi_bo.bay_gio() - interval '5 hours', 'demo-kho-01', 'Mạng / Internet', 'binh-thuong',
   'nhanvien1', 'Máy kho chập chờn khi mở trang quản trị Box', 'nhanvien1', 'nap-du-lieu-demo', 3)
ON CONFLICT (nguon, dong) DO UPDATE SET
  ma = EXCLUDED.ma,
  thoi_gian = EXCLUDED.thoi_gian,
  may = EXCLUDED.may,
  loai = EXCLUDED.loai,
  muc_do = EXCLUDED.muc_do,
  nguoi_bao = EXCLUDED.nguoi_bao,
  mo_ta = EXCLUDED.mo_ta,
  nguoi_tao = EXCLUDED.nguoi_tao;

-- Cách xử lý mẫu cho yêu cầu hỗ trợ đầu tiên
INSERT INTO onebee.xu_ly_ho_tro
  (ma, thoi_gian, cach_xu_ly, so_phut, ghi_chu, nguoi_tao, nguon, dong)
VALUES
  ('DEMO-HT-001', onebee_noi_bo.bay_gio() - interval '2 hours', 'Sửa cấu hình', 25,
   'Cài lại driver CUPS và chọn đúng khổ giấy A5', 'kythuat1', 'nap-du-lieu-demo', 1)
ON CONFLICT (nguon, dong) DO UPDATE SET
  ma = EXCLUDED.ma,
  thoi_gian = EXCLUDED.thoi_gian,
  cach_xu_ly = EXCLUDED.cach_xu_ly,
  so_phut = EXCLUDED.so_phut,
  ghi_chu = EXCLUDED.ghi_chu,
  nguoi_tao = EXCLUDED.nguoi_tao;

-- Khảo sát ẩn danh: đủ ba phiếu để bảng điều hành hiện điểm trung bình
INSERT INTO onebee.khao_sat (thoi_gian, diem_1, diem_2, diem_3, diem_4, diem_5, gop_y, nguon, dong)
VALUES
  (onebee_noi_bo.bay_gio() - interval '6 hours', 5, 5, 4, 5, 5, 'Bộ gõ tiếng Việt và Ribbon LibreOffice dễ chuyển từ Windows', 'nap-du-lieu-demo', 1),
  (onebee_noi_bo.bay_gio() - interval '1 day', 4, 5, 5, 4, 4, 'Sao lưu tự động chạy ổn định, không lo quên sao lưu', 'nap-du-lieu-demo', 2),
  (onebee_noi_bo.bay_gio() - interval '2 days', 5, 4, 5, 5, 4, 'Trợ lý AI trả lời tiếng Việt sát với công việc văn phòng', 'nap-du-lieu-demo', 3)
ON CONFLICT (nguon, dong) DO UPDATE SET
  thoi_gian = EXCLUDED.thoi_gian,
  diem_1 = EXCLUDED.diem_1,
  diem_2 = EXCLUDED.diem_2,
  diem_3 = EXCLUDED.diem_3,
  diem_4 = EXCLUDED.diem_4,
  diem_5 = EXCLUDED.diem_5,
  gop_y = EXCLUDED.gop_y;

-- Tình trạng máy trạm mẫu (bao bì JSON như máy trạm gửi; bản chạy thử không có máy thật)
INSERT INTO onebee.tinh_trang_may (ten, bao_bi, nhan_luc)
VALUES
  ('demo-ketoan-01',
   '{"ten": "demo-ketoan-01", "he_dieu_hanh": "Linux Mint 22.3 + OneBee OS 1.3.0", "trang_thai": "TOT", "lan_sao_luu_cuoi": "2026-11-16 12:00:00", "ghi_chu": "Sao lưu restic thành công"}'::jsonb,
   (extract(epoch FROM now()))::bigint),
  ('demo-kho-01',
   '{"ten": "demo-kho-01", "he_dieu_hanh": "Linux Mint 22.3 + OneBee OS 1.3.0", "trang_thai": "TOT", "lan_sao_luu_cuoi": "2026-11-16 12:00:00", "ghi_chu": "Khóa hoi hoạt động bình thường"}'::jsonb,
   (extract(epoch FROM now()))::bigint),
  ('demo-banhang-01',
   '{"ten": "demo-banhang-01", "he_dieu_hanh": "Linux Mint 22.3 + OneBee OS 1.3.0", "trang_thai": "CANH_BAO", "lan_sao_luu_cuoi": "2026-11-13 12:00:00", "ghi_chu": "Quá hai ngày chưa sao lưu (dữ liệu mẫu)"}'::jsonb,
   (extract(epoch FROM now()))::bigint)
ON CONFLICT (ten) DO UPDATE SET
  bao_bi = EXCLUDED.bao_bi,
  nhan_luc = EXCLUDED.nhan_luc;

COMMIT;
