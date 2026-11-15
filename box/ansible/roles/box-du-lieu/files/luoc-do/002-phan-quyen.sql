-- Vai trò và phân quyền tới cấp dòng (RLS). Mọi quyền được kiểm ở CSDL, không dựa vào kiểm tra phía ứng dụng.
-- xac_thuc: dịch vụ dữ liệu (PostgREST) đăng nhập bằng vai trò này, không có quyền trên bảng nào; với mỗi yêu cầu nó chuyển sang
-- vai trò ghi trong JWT (claim role) do cầu nối danh tính ký. Không có vai trò ẩn danh: yêu cầu không có JWT bị từ chối (401).
-- Mật khẩu của xac_thuc do bộ cài đặt (ALTER ROLE), không nằm trong tệp này.
-- Vai trò là của cả cụm PostgreSQL (không nằm trong bản kết xuất CSDL) → tạo có điều kiện để khôi phục vào cụm mới vẫn chạy.

DO $$
DECLARE
  v text;
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'xac_thuc') THEN
    CREATE ROLE xac_thuc LOGIN NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;
  END IF;
  FOREACH v IN ARRAY ARRAY['nhan_vien', 'ky_thuat', 'quan_ly'] LOOP
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = v) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', v);
    END IF;
  END LOOP;
END $$;

-- Kỹ thuật và quản lý cũng là nhân viên: được báo sự cố, tạo đơn, gửi khảo sát như mọi người (thừa hưởng quyền của nhan_vien)
GRANT nhan_vien TO ky_thuat;
GRANT nhan_vien TO quan_ly;
GRANT nhan_vien, ky_thuat, quan_ly TO xac_thuc;

REVOKE ALL ON SCHEMA onebee FROM PUBLIC;
REVOKE ALL ON SCHEMA onebee_noi_bo FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA onebee FROM PUBLIC;
GRANT USAGE ON SCHEMA onebee, onebee_noi_bo TO nhan_vien;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA onebee_noi_bo TO nhan_vien;

-- ---- Đơn hàng ----
-- Nhân viên: thêm đơn của chính mình, đọc đơn do mình tạo; không sửa, không xóa
GRANT SELECT, INSERT ON onebee.don_hang TO nhan_vien;
GRANT USAGE ON SEQUENCE onebee.don_hang_id_seq TO nhan_vien;
CREATE POLICY nhan_vien_them ON onebee.don_hang FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tao = onebee_noi_bo.nguoi_dung() AND nguon IS NULL);
CREATE POLICY nhan_vien_doc ON onebee.don_hang FOR SELECT TO nhan_vien
  USING (nguoi_tao = onebee_noi_bo.nguoi_dung());
-- Quản lý: đọc mọi đơn; chỉ sửa được trạng thái duyệt và lý do (quyền theo cột). Đơn của chính mình bị ràng buộc
-- nguoi_duyet <> nguoi_tao chặn (báo lỗi rõ, không lặng lẽ bỏ qua); người duyệt, giờ duyệt do trigger ghi
GRANT UPDATE (trang_thai_duyet, ly_do_duyet) ON onebee.don_hang TO quan_ly;
CREATE POLICY quan_ly_doc ON onebee.don_hang FOR SELECT TO quan_ly USING (true);
CREATE POLICY quan_ly_duyet ON onebee.don_hang FOR UPDATE TO quan_ly
  USING (nguon IS NULL) WITH CHECK (nguon IS NULL AND trang_thai_duyet IS NOT NULL);

-- ---- Yêu cầu hỗ trợ ----
GRANT SELECT, INSERT ON onebee.yeu_cau_ho_tro TO nhan_vien;
GRANT USAGE ON SEQUENCE onebee.yeu_cau_ho_tro_id_seq TO nhan_vien;
CREATE POLICY nhan_vien_them ON onebee.yeu_cau_ho_tro FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tao = onebee_noi_bo.nguoi_dung() AND nguon IS NULL);
CREATE POLICY nhan_vien_doc ON onebee.yeu_cau_ho_tro FOR SELECT TO nhan_vien
  USING (nguoi_tao = onebee_noi_bo.nguoi_dung());
CREATE POLICY ky_thuat_doc ON onebee.yeu_cau_ho_tro FOR SELECT TO ky_thuat USING (true);
CREATE POLICY quan_ly_doc ON onebee.yeu_cau_ho_tro FOR SELECT TO quan_ly USING (true);

-- ---- Xử lý hỗ trợ: kỹ thuật thêm dòng và đọc; quản lý đọc ----
GRANT SELECT, INSERT ON onebee.xu_ly_ho_tro TO ky_thuat;
GRANT SELECT ON onebee.xu_ly_ho_tro TO quan_ly;
GRANT USAGE ON SEQUENCE onebee.xu_ly_ho_tro_id_seq TO ky_thuat;
CREATE POLICY ky_thuat_them ON onebee.xu_ly_ho_tro FOR INSERT TO ky_thuat
  WITH CHECK (nguoi_tao = onebee_noi_bo.nguoi_dung() AND nguon IS NULL);
CREATE POLICY ky_thuat_doc ON onebee.xu_ly_ho_tro FOR SELECT TO ky_thuat USING (true);
CREATE POLICY quan_ly_doc ON onebee.xu_ly_ho_tro FOR SELECT TO quan_ly USING (true);

-- ---- Khảo sát: ai cũng gửi được (ẩn danh), không ai đọc thẳng bảng — quản lý chỉ xem khung nhìn tổng hợp ----
GRANT INSERT (thoi_gian, diem_1, diem_2, diem_3, diem_4, diem_5, gop_y) ON onebee.khao_sat TO nhan_vien;
GRANT USAGE ON SEQUENCE onebee.khao_sat_id_seq TO nhan_vien;
CREATE POLICY nhan_vien_them ON onebee.khao_sat FOR INSERT TO nhan_vien WITH CHECK (nguon IS NULL);

-- ---- Tình trạng máy trạm: kỹ thuật và quản lý đọc; chỉ Box (chủ CSDL) ghi ----
GRANT SELECT ON onebee.tinh_trang_may TO ky_thuat, quan_ly;
CREATE POLICY ky_thuat_doc ON onebee.tinh_trang_may FOR SELECT TO ky_thuat USING (true);
CREATE POLICY quan_ly_doc ON onebee.tinh_trang_may FOR SELECT TO quan_ly USING (true);

-- tep_dinh_kem, tai_lieu_tri_thuc, lich_su_hoi_ai: RLS đã bật, chưa cấp quyền cho vai trò nào (giai đoạn kho tệp, Trợ lý)
