-- Kho tệp: thêm khóa đối tượng trong SeaweedFS, trạng thái kiểm dịch và kết quả quét vào bảng metadata có sẵn.
-- Dịch vụ kho tệp ghi/đọc bảng này qua cổng API bằng JWT của người dùng (RLS), không dùng quyền chủ CSDL.
ALTER TABLE onebee.tep_dinh_kem
  ADD COLUMN khoa_luu_tru text,
  ADD COLUMN trang_thai_quet text NOT NULL DEFAULT 'PENDING_SCAN'
    CHECK (trang_thai_quet IN ('PENDING_SCAN', 'CLEAN', 'INFECTED')),
  ADD COLUMN ket_qua_quet text;
-- Tệp nhiễm không có khóa đối tượng (nhiều NULL hợp lệ); tệp sạch có đúng một khóa
CREATE UNIQUE INDEX tep_dinh_kem_khoa_luu_tru ON onebee.tep_dinh_kem (khoa_luu_tru);

-- Nhân viên: ghi metadata tệp của chính mình (nguoi_tao lấy từ claim sub của JWT) và đọc tệp của mình.
-- Chỉ cấp INSERT theo cột: người gọi không tự đặt id, tao_luc hay nguoi_tao.
-- Kỹ thuật và quản lý đọc metadata mọi tệp để điều tra sự cố; không ai sửa, xóa.
GRANT INSERT (ten_tep, kich_thuoc, sha256, khoa_luu_tru, trang_thai_quet, ket_qua_quet) ON onebee.tep_dinh_kem TO nhan_vien;
GRANT SELECT ON onebee.tep_dinh_kem TO nhan_vien;
GRANT USAGE ON SEQUENCE onebee.tep_dinh_kem_id_seq TO nhan_vien;
CREATE POLICY nhan_vien_them ON onebee.tep_dinh_kem FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tao = onebee_noi_bo.nguoi_dung());
CREATE POLICY nhan_vien_doc ON onebee.tep_dinh_kem FOR SELECT TO nhan_vien
  USING (nguoi_tao = onebee_noi_bo.nguoi_dung());
GRANT SELECT ON onebee.tep_dinh_kem TO ky_thuat, quan_ly;
CREATE POLICY ky_thuat_doc ON onebee.tep_dinh_kem FOR SELECT TO ky_thuat USING (true);
CREATE POLICY quan_ly_doc ON onebee.tep_dinh_kem FOR SELECT TO quan_ly USING (true);
