-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Phân quyền cho kho và kế toán: vai trò mới thu_kho, ke_toan; quyền bảng/khung nhìn/hàm.
-- Tệp 002 đã áp dụng nên danh sách vai trò mới nằm ở đây (thay đổi vai trò là tệp lược đồ mới).
-- Vai trò là của cả cụm PostgreSQL (không nằm trong bản kết xuất CSDL) → tạo có điều kiện như 002.
-- Nguyên tắc: chứng từ kho và bút toán CHỈ sinh qua hàm nội bộ/trigger, không cấp INSERT/SELECT bảng thô cho vai trò
-- ngoài phạm vi; khung nhìn chạy bằng quyền chủ CSDL nên chỉ cấp cho đúng vai trò được xem.

DO $$
DECLARE
  v text;
BEGIN
  FOREACH v IN ARRAY ARRAY['thu_kho', 'ke_toan'] LOOP
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = v) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', v);
    END IF;
  END LOOP;
END $$;

-- Thủ kho và kế toán cũng là nhân viên: vẫn gửi đơn, báo sự cố, gửi khảo sát như mọi người
GRANT nhan_vien TO thu_kho;
GRANT nhan_vien TO ke_toan;
GRANT thu_kho, ke_toan TO xac_thuc;

GRANT USAGE ON SCHEMA onebee, onebee_noi_bo TO thu_kho, ke_toan;
-- Hàm dùng chung cho mặc định cột (nguoi_tao, tao_luc) và RLS; hàm ghi bút toán KHÔNG cấp
GRANT EXECUTE ON FUNCTION onebee_noi_bo.nguoi_dung(), onebee_noi_bo.bay_gio() TO thu_kho, ke_toan;

-- Hàm nội bộ không cho vai trò nào gọi thẳng qua API (PostgreSQL cấp EXECUTE cho PUBLIC theo mặc định)
REVOKE ALL ON FUNCTION onebee_noi_bo.ghi_but_toan(date, text, text, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION onebee_noi_bo.phieu_kho_so() FROM PUBLIC;
REVOKE ALL ON FUNCTION onebee_noi_bo.kiem_ton_kho() FROM PUBLIC;
REVOKE ALL ON FUNCTION onebee_noi_bo.don_hang_hoan_tat() FROM PUBLIC;
REVOKE ALL ON FUNCTION onebee.them_nhap_kho(date, text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION onebee.them_nhap_kho(date, text, jsonb) TO thu_kho, quan_ly;

-- ---- Danh mục mặt hàng: mọi vai trò đọc (biểu mẫu đơn hàng cần danh sách); thủ kho và quản lý thêm/sửa ----
GRANT SELECT ON onebee.mat_hang TO nhan_vien, thu_kho, ke_toan, quan_ly;
GRANT INSERT, UPDATE ON onebee.mat_hang TO thu_kho, quan_ly;
GRANT USAGE ON SEQUENCE onebee.mat_hang_id_seq TO thu_kho, quan_ly;
CREATE POLICY moi_nguoi_doc ON onebee.mat_hang FOR SELECT TO nhan_vien, thu_kho, ke_toan, quan_ly USING (true);
CREATE POLICY thu_kho_them ON onebee.mat_hang FOR INSERT TO thu_kho WITH CHECK (true);
CREATE POLICY thu_kho_sua ON onebee.mat_hang FOR UPDATE TO thu_kho USING (true) WITH CHECK (true);
CREATE POLICY quan_ly_them ON onebee.mat_hang FOR INSERT TO quan_ly WITH CHECK (true);
CREATE POLICY quan_ly_sua ON onebee.mat_hang FOR UPDATE TO quan_ly USING (true) WITH CHECK (true);

-- ---- Phiếu kho: thủ kho, kế toán, quản lý đọc; chỉ ghi qua them_nhap_kho và trigger duyệt đơn ----
GRANT SELECT ON onebee.phieu_kho, onebee.phieu_kho_dong TO thu_kho, ke_toan, quan_ly;
CREATE POLICY thu_kho_doc ON onebee.phieu_kho FOR SELECT TO thu_kho USING (true);
CREATE POLICY ke_toan_doc ON onebee.phieu_kho FOR SELECT TO ke_toan USING (true);
CREATE POLICY quan_ly_doc ON onebee.phieu_kho FOR SELECT TO quan_ly USING (true);
CREATE POLICY thu_kho_doc ON onebee.phieu_kho_dong FOR SELECT TO thu_kho USING (true);
CREATE POLICY ke_toan_doc ON onebee.phieu_kho_dong FOR SELECT TO ke_toan USING (true);
CREATE POLICY quan_ly_doc ON onebee.phieu_kho_dong FOR SELECT TO quan_ly USING (true);

-- ---- Hệ thống tài khoản và nhật ký: chỉ kế toán và quản lý ----
GRANT SELECT ON onebee.tai_khoan, onebee.but_toan, onebee.but_toan_dong TO ke_toan, quan_ly;
CREATE POLICY ke_toan_doc ON onebee.tai_khoan FOR SELECT TO ke_toan USING (true);
CREATE POLICY quan_ly_doc ON onebee.tai_khoan FOR SELECT TO quan_ly USING (true);
CREATE POLICY ke_toan_doc ON onebee.but_toan FOR SELECT TO ke_toan USING (true);
CREATE POLICY quan_ly_doc ON onebee.but_toan FOR SELECT TO quan_ly USING (true);
CREATE POLICY ke_toan_doc ON onebee.but_toan_dong FOR SELECT TO ke_toan USING (true);
CREATE POLICY quan_ly_doc ON onebee.but_toan_dong FOR SELECT TO quan_ly USING (true);

-- ---- Khung nhìn ----
REVOKE ALL ON onebee.ton_kho, onebee.so_kho, onebee.so_nhat_ky, onebee.bang_can_doi FROM PUBLIC;
GRANT SELECT ON onebee.ton_kho, onebee.so_kho TO thu_kho, quan_ly;
GRANT SELECT ON onebee.ton_kho, onebee.so_kho, onebee.so_nhat_ky, onebee.bang_can_doi TO ke_toan, quan_ly;
