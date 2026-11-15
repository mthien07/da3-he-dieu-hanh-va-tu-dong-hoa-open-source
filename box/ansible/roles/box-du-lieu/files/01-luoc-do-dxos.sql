-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Lược đồ dữ liệu lõi DX-OS Open-Core (PostgreSQL 18 + pgvector + PostgREST)
-- Đảm bảo lũy đẳng (idempotent): chạy lại nhiều lần không lỗi, không mất dữ liệu.

CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
    CREATE ROLE authenticator LOGIN NOINHERIT NOCREATEDB NOCREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nhan_vien') THEN
    CREATE ROLE nhan_vien NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ky_thuat') THEN
    CREATE ROLE ky_thuat NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'quan_ly') THEN
    CREATE ROLE quan_ly NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dich_vu') THEN
    CREATE ROLE dich_vu NOLOGIN;
  END IF;
END
$$;

GRANT nhan_vien, ky_thuat, quan_ly, dich_vu TO authenticator;

CREATE SCHEMA IF NOT EXISTS api;
GRANT USAGE ON SCHEMA api TO nhan_vien, ky_thuat, quan_ly, dich_vu;

-- Hàm tiện ích lấy tên đăng nhập và vai trò từ JWT của PostgREST
CREATE OR REPLACE FUNCTION api.nguoi_dung_hien_tai() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::json->>'sub',
    current_user
  );
$$;

CREATE OR REPLACE FUNCTION api.vai_tro_hien_tai() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::json->>'role',
    current_user
  );
$$;

-- 1. Bảng đơn hàng (có bước phê duyệt quản lý + Poka-yoke cấm tự duyệt)
CREATE TABLE IF NOT EXISTS api.don_hang (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_don text UNIQUE NOT NULL,
  ngay_tao timestamptz NOT NULL DEFAULT now(),
  nguoi_tao text NOT NULL DEFAULT api.nguoi_dung_hien_tai(),
  khach_hang text NOT NULL,
  mat_hang text NOT NULL,
  so_luong numeric(12,2) NOT NULL CHECK (so_luong > 0),
  don_gia numeric(14,2) NOT NULL CHECK (don_gia >= 0),
  thanh_tien numeric(16,2) GENERATED ALWAYS AS (so_luong * don_gia) STORED,
  ghi_chu text NOT NULL DEFAULT '',
  trang_thai_duyet text NOT NULL DEFAULT 'CHO_DUYET'
    CHECK (trang_thai_duyet IN ('CHO_DUYET', 'DA_DUYET', 'TU_CHOI')),
  nguoi_duyet text,
  ly_do_duyet text,
  thoi_gian_duyet timestamptz,
  CONSTRAINT khong_tu_duyet_don CHECK (nguoi_duyet IS NULL OR nguoi_duyet <> nguoi_tao),
  CONSTRAINT tu_choi_don_phai_co_ly_do CHECK (
    trang_thai_duyet <> 'TU_CHOI'
    OR (ly_do_duyet IS NOT NULL AND length(btrim(ly_do_duyet)) > 0)
  )
);

-- 2. Bảng yêu cầu hỗ trợ kỹ thuật (có bước phê duyệt cho yêu cầu mua sắm/thay phần cứng)
CREATE TABLE IF NOT EXISTS api.yeu_cau_ho_tro (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma text UNIQUE NOT NULL,
  thoi_gian timestamptz NOT NULL DEFAULT now(),
  may_tram text NOT NULL,
  loai text NOT NULL,
  muc_do text NOT NULL DEFAULT 'thuong' CHECK (muc_do IN ('thuong', 'gap')),
  nguoi_bao text NOT NULL DEFAULT api.nguoi_dung_hien_tai(),
  mo_ta text NOT NULL,
  trang_thai_duyet text NOT NULL DEFAULT 'CHO_DUYET'
    CHECK (trang_thai_duyet IN ('CHO_DUYET', 'DA_DUYET', 'TU_CHOI')),
  nguoi_duyet text,
  ly_do_duyet text,
  thoi_gian_duyet timestamptz,
  CONSTRAINT khong_tu_duyet_ho_tro CHECK (nguoi_duyet IS NULL OR nguoi_duyet <> nguoi_bao),
  CONSTRAINT tu_choi_ho_tro_phai_co_ly_do CHECK (
    trang_thai_duyet <> 'TU_CHOI'
    OR (ly_do_duyet IS NOT NULL AND length(btrim(ly_do_duyet)) > 0)
  )
);

-- 3. Bảng nhật ký xử lý yêu cầu hỗ trợ
CREATE TABLE IF NOT EXISTS api.xu_ly_ho_tro (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_yeu_cau text NOT NULL REFERENCES api.yeu_cau_ho_tro(ma) ON DELETE CASCADE,
  thoi_gian timestamptz NOT NULL DEFAULT now(),
  nguoi_xu_ly text NOT NULL DEFAULT api.nguoi_dung_hien_tai(),
  cach_xu_ly text NOT NULL,
  so_phut integer NOT NULL DEFAULT 0 CHECK (so_phut >= 0),
  ghi_chu text NOT NULL DEFAULT ''
);

-- 4. Bảng khảo sát hài lòng (ẩn danh: không lưu tên người gửi)
CREATE TABLE IF NOT EXISTS api.khao_sat (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  thoi_gian timestamptz NOT NULL DEFAULT now(),
  diem_on_dinh smallint NOT NULL CHECK (diem_on_dinh BETWEEN 1 AND 5),
  diem_van_ban smallint NOT NULL CHECK (diem_van_ban BETWEEN 1 AND 5),
  diem_tieng_viet smallint NOT NULL CHECK (diem_tieng_viet BETWEEN 1 AND 5),
  diem_ho_tro smallint NOT NULL CHECK (diem_ho_tro BETWEEN 1 AND 5),
  diem_tiep_tuc smallint NOT NULL CHECK (diem_tiep_tuc BETWEEN 1 AND 5),
  gop_y text NOT NULL DEFAULT ''
);

-- 5. Bảng tình trạng máy trạm
CREATE TABLE IF NOT EXISTS api.tinh_trang_may (
  ten_may text PRIMARY KEY,
  ip text,
  phien_ban text,
  goi_cho integer,
  goi_bao_mat integer,
  can_khoi_dong_lai boolean NOT NULL DEFAULT false,
  o_dia_trong_gb numeric(10,2),
  gio_da_bat numeric(10,2),
  lan_sao_luu_cuoi text,
  so_tai_khoan_sudo integer,
  hop_le_chu_ky boolean NOT NULL DEFAULT false,
  du_lieu_goc jsonb NOT NULL DEFAULT '{}'::jsonb,
  cap_nhat_luc timestamptz NOT NULL DEFAULT now()
);

-- 6. Bảng tệp đính kèm và trạng thái kiểm dịch ClamAV (Giai đoạn 7)
CREATE TABLE IF NOT EXISTS api.tep_dinh_kem (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_tep text UNIQUE NOT NULL,
  ten_goc text NOT NULL,
  duong_dan_kho text NOT NULL,
  kich_thuoc bigint NOT NULL CHECK (kich_thuoc >= 0),
  sha256 text NOT NULL,
  nguoi_tai text NOT NULL DEFAULT api.nguoi_dung_hien_tai(),
  loai_nghiep_vu text NOT NULL DEFAULT 'chung',
  ma_nghiep_vu text NOT NULL DEFAULT '',
  trang_thai_quet text NOT NULL DEFAULT 'PENDING_SCAN'
    CHECK (trang_thai_quet IN ('PENDING_SCAN', 'CLEAN', 'INFECTED')),
  chi_tiet_quet text NOT NULL DEFAULT '',
  tao_luc timestamptz NOT NULL DEFAULT now(),
  quet_luc timestamptz
);

-- 7. Bảng tài liệu tri thức RAG kèm vector nhúng (Giai đoạn 8)
CREATE TABLE IF NOT EXISTS api.tai_lieu_tri_thuc (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_tai_lieu text NOT NULL,
  tieu_de text NOT NULL,
  doan_so integer NOT NULL DEFAULT 0,
  noi_dung text NOT NULL,
  nhung vector(384),
  cap_nhat_luc timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ma_tai_lieu, doan_so)
);

-- 8. Bảng lịch sử gọi Trợ lý AI (không lưu nội dung nhạy cảm)
CREATE TABLE IF NOT EXISTS api.lich_su_hoi_ai (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nguoi_hoi text NOT NULL DEFAULT api.nguoi_dung_hien_tai(),
  loai text NOT NULL DEFAULT 'hoi',
  ma_mau text NOT NULL DEFAULT '',
  do_dai_cau_hoi integer NOT NULL DEFAULT 0,
  so_doan_rag integer NOT NULL DEFAULT 0,
  thoi_gian_ms integer NOT NULL DEFAULT 0,
  tao_luc timestamptz NOT NULL DEFAULT now()
);

-- Phân quyền bảng và chuỗi tự tăng
GRANT SELECT, INSERT ON api.don_hang, api.yeu_cau_ho_tro, api.tep_dinh_kem, api.lich_su_hoi_ai TO nhan_vien;
GRANT INSERT ON api.khao_sat TO nhan_vien;
GRANT SELECT ON api.tai_lieu_tri_thuc TO nhan_vien, ky_thuat, quan_ly;

GRANT SELECT, INSERT, UPDATE ON api.yeu_cau_ho_tro, api.xu_ly_ho_tro, api.tinh_trang_may, api.tep_dinh_kem TO ky_thuat;
GRANT SELECT ON api.don_hang, api.khao_sat TO ky_thuat;

GRANT SELECT, INSERT, UPDATE ON api.don_hang, api.yeu_cau_ho_tro, api.xu_ly_ho_tro, api.tinh_trang_may, api.tep_dinh_kem TO quan_ly;
GRANT SELECT, INSERT ON api.khao_sat, api.lich_su_hoi_ai TO quan_ly;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA api TO dich_vu;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA api TO nhan_vien, ky_thuat, quan_ly, dich_vu;

-- Bật Row-Level Security (RLS)
ALTER TABLE api.don_hang ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.don_hang FORCE ROW LEVEL SECURITY;

ALTER TABLE api.yeu_cau_ho_tro ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.yeu_cau_ho_tro FORCE ROW LEVEL SECURITY;

ALTER TABLE api.tep_dinh_kem ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.tep_dinh_kem FORCE ROW LEVEL SECURITY;

ALTER TABLE api.lich_su_hoi_ai ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.lich_su_hoi_ai FORCE ROW LEVEL SECURITY;

-- Chính sách RLS cho api.don_hang
DROP POLICY IF EXISTS don_hang_nhan_vien_xem ON api.don_hang;
CREATE POLICY don_hang_nhan_vien_xem ON api.don_hang
  FOR SELECT TO nhan_vien
  USING (nguoi_tao = api.nguoi_dung_hien_tai());

DROP POLICY IF EXISTS don_hang_nhan_vien_tao ON api.don_hang;
CREATE POLICY don_hang_nhan_vien_tao ON api.don_hang
  FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tao = api.nguoi_dung_hien_tai() AND trang_thai_duyet = 'CHO_DUYET' AND nguoi_duyet IS NULL);

DROP POLICY IF EXISTS don_hang_ky_thuat_xem ON api.don_hang;
CREATE POLICY don_hang_ky_thuat_xem ON api.don_hang
  FOR SELECT TO ky_thuat
  USING (true);

DROP POLICY IF EXISTS don_hang_quan_ly_toan_quyen ON api.don_hang;
CREATE POLICY don_hang_quan_ly_toan_quyen ON api.don_hang
  FOR ALL TO quan_ly
  USING (true)
  WITH CHECK (nguoi_duyet IS NULL OR (nguoi_duyet = api.nguoi_dung_hien_tai() AND nguoi_duyet <> nguoi_tao));

DROP POLICY IF EXISTS don_hang_dich_vu ON api.don_hang;
CREATE POLICY don_hang_dich_vu ON api.don_hang
  FOR ALL TO dich_vu
  USING (true)
  WITH CHECK (true);

-- Chính sách RLS cho api.yeu_cau_ho_tro
DROP POLICY IF EXISTS ho_tro_nhan_vien_xem ON api.yeu_cau_ho_tro;
CREATE POLICY ho_tro_nhan_vien_xem ON api.yeu_cau_ho_tro
  FOR SELECT TO nhan_vien
  USING (nguoi_bao = api.nguoi_dung_hien_tai());

DROP POLICY IF EXISTS ho_tro_nhan_vien_tao ON api.yeu_cau_ho_tro;
CREATE POLICY ho_tro_nhan_vien_tao ON api.yeu_cau_ho_tro
  FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_bao = api.nguoi_dung_hien_tai() AND trang_thai_duyet = 'CHO_DUYET' AND nguoi_duyet IS NULL);

DROP POLICY IF EXISTS ho_tro_ky_thuat ON api.yeu_cau_ho_tro;
CREATE POLICY ho_tro_ky_thuat ON api.yeu_cau_ho_tro
  FOR ALL TO ky_thuat
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS ho_tro_quan_ly ON api.yeu_cau_ho_tro;
CREATE POLICY ho_tro_quan_ly ON api.yeu_cau_ho_tro
  FOR ALL TO quan_ly
  USING (true)
  WITH CHECK (nguoi_duyet IS NULL OR (nguoi_duyet = api.nguoi_dung_hien_tai() AND nguoi_duyet <> nguoi_bao));

DROP POLICY IF EXISTS ho_tro_dich_vu ON api.yeu_cau_ho_tro;
CREATE POLICY ho_tro_dich_vu ON api.yeu_cau_ho_tro
  FOR ALL TO dich_vu
  USING (true)
  WITH CHECK (true);

-- Chính sách RLS cho api.tep_dinh_kem (không trả tệp INFECTED cho người dùng thường)
DROP POLICY IF EXISTS tep_nhan_vien_xem ON api.tep_dinh_kem;
CREATE POLICY tep_nhan_vien_xem ON api.tep_dinh_kem
  FOR SELECT TO nhan_vien
  USING (nguoi_tai = api.nguoi_dung_hien_tai() AND trang_thai_quet <> 'INFECTED');

DROP POLICY IF EXISTS tep_nhan_vien_tao ON api.tep_dinh_kem;
CREATE POLICY tep_nhan_vien_tao ON api.tep_dinh_kem
  FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tai = api.nguoi_dung_hien_tai() AND trang_thai_quet = 'PENDING_SCAN');

DROP POLICY IF EXISTS tep_ky_thuat_quan_ly ON api.tep_dinh_kem;
CREATE POLICY tep_ky_thuat_quan_ly ON api.tep_dinh_kem
  FOR ALL TO ky_thuat, quan_ly, dich_vu
  USING (true)
  WITH CHECK (true);

-- Chính sách RLS cho api.lich_su_hoi_ai
DROP POLICY IF EXISTS lich_su_ai_xem ON api.lich_su_hoi_ai;
CREATE POLICY lich_su_ai_xem ON api.lich_su_hoi_ai
  FOR SELECT TO nhan_vien
  USING (nguoi_hoi = api.nguoi_dung_hien_tai());

DROP POLICY IF EXISTS lich_su_ai_tao ON api.lich_su_hoi_ai;
CREATE POLICY lich_su_ai_tao ON api.lich_su_hoi_ai
  FOR INSERT TO nhan_vien, ky_thuat, quan_ly, dich_vu
  WITH CHECK (true);

DROP POLICY IF EXISTS lich_su_ai_quan_ly ON api.lich_su_hoi_ai;
CREATE POLICY lich_su_ai_quan_ly ON api.lich_su_hoi_ai
  FOR SELECT TO quan_ly, dich_vu
  USING (true);
