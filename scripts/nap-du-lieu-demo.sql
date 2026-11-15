-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Dữ liệu mẫu và khôi phục hằng đêm (03:00) cho máy chủ Demo công khai OLP 2026

BEGIN;

TRUNCATE TABLE nhat_ky_ai, tep_dinh_kem, phieu_nghiep_vu, may_tram RESTART IDENTITY CASCADE;

INSERT INTO may_tram (don_vi, hostname, nguoi_dung, ip_lan, phien_ban_onebee, uptime_phut, ram_dung_phan_tram, dia_dung_phan_tram, sao_luu_gan_nhat, trang_thai_sao_luu, cap_nhat_luc)
VALUES
  ('htx-onebee', 'tram-ke-toan-01', 'nhanvien1', '192.168.1.21', '1.3.0', 480, 42, 38, '2026-11-15T02:00:00Z', 'THANH_CONG', NOW()),
  ('htx-onebee', 'tram-kho-van-02', 'kythuat1', '192.168.1.22', '1.3.0', 1420, 55, 61, '2026-11-15T02:05:00Z', 'THANH_CONG', NOW()),
  ('htx-onebee', 'tram-ban-hang-03', 'nhanvien1', '192.168.1.23', '1.3.0', 210, 36, 29, '2026-11-15T02:10:00Z', 'THANH_CONG', NOW());

INSERT INTO phieu_nghiep_vu (ma_phieu, don_vi, loai_phieu, tieu_de, noi_dung, so_tien_vnd, muc_do, nguoi_tao, vai_tro_tao, trang_thai, nguoi_duyet, ly_do_quyet_dinh, duyet_luc)
VALUES
  ('DH-20261115-001', 'htx-onebee', 'DON_HANG', 'Đơn xuất 120 chai mật ong hoa nhãn đi Đà Lạt', 'Khách hàng đại lý Lâm Đồng đặt 120 chai 500ml, thanh toán chuyển khoản khi nhận.', 18000000, 'trung_binh', 'nhanvien1', 'nhan_vien', 'CHO_DUYET', NULL, NULL, NULL),
  ('HT-20261115-002', 'htx-onebee', 'HO_TRO', 'Máy in tem nhãn kho số 2 bị lệch khổ giấy', 'Cần kỹ thuật căn chỉnh lại cảm biến khổ giấy nhiệt 50x30mm.', 0, 'cao', 'nhanvien1', 'nhan_vien', 'CHO_DUYET', NULL, NULL, NULL),
  ('KS-20261114-003', 'htx-onebee', 'KHAO_SAT', 'Khảo sát sản lượng mật vụ thu đông trại ong số 4', 'Sản lượng ước tính đạt 450 lít, độ ẩm 18.5%, đạt chuẩn đóng chai xuất khẩu.', 0, 'thap', 'kythuat1', 'ky_thuat', 'DA_DUYET', 'quanly1', 'Đạt tiêu chuẩn nhập kho đợt 2.', NOW() - INTERVAL '6 hours');

INSERT INTO tep_dinh_kem (ma_tep, phieu_id, don_vi, ten_tep_goc, kich_thuoc_byte, sha256, duong_dan_luu_tru, trang_thai_quet, chi_tiet_quet, nguoi_tai_len)
VALUES
  ('TEP-DEMO-001', 1, 'htx-onebee', 'bien-ban-kiem-ke-lo-2026-11.pdf', 84320, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'seaweed://onebee-bucket/TEP-DEMO-001', 'CLEAN', 'ClamAV: OK (0 mối đe dọa)', 'nhanvien1');

COMMIT;
