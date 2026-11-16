-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Trợ lý AI tra cứu tri thức (pgvector) và nhật ký hỏi đáp. Bộ cài áp dụng MỘT lần; đã áp dụng thì không sửa tệp này — thay đổi tiếp là tệp mới.
-- Bảng tai_lieu_tri_thuc và lich_su_hoi_ai đã có (RLS bật và ép) từ tệp 001, chưa cấp quyền cho vai trò nào.
-- Đọc tri thức: mọi nhân viên (kỹ thuật và quản lý thừa hưởng nhan_vien). Ghi tri thức: chỉ chủ CSDL, qua `onebee-box nap-tri-thuc`.
-- Nhật ký hỏi đáp: mỗi người chỉ thêm và đọc dòng của chính mình; không ai sửa, không ai xóa.

-- Mỗi đoạn tri thức nhận diện bằng (nguon, doan): nạp lại cùng nguồn thì cập nhật đúng dòng, không tạo trùng.
-- sha256: băm tiêu đề + nội dung đoạn (đổi mới nhúng lại); mo_hinh_nhung: mô hình đã tạo vector (đổi mô hình thì nhúng lại hết).
ALTER TABLE onebee.tai_lieu_tri_thuc
  ADD COLUMN nguon text NOT NULL,
  ADD COLUMN doan integer NOT NULL CHECK (doan >= 0),
  ADD COLUMN sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  ADD COLUMN mo_hinh_nhung text NOT NULL,
  ADD CONSTRAINT tri_thuc_nguon_doan UNIQUE (nguon, doan);

GRANT SELECT ON onebee.tai_lieu_tri_thuc TO nhan_vien;
CREATE POLICY nhan_vien_doc ON onebee.tai_lieu_tri_thuc FOR SELECT TO nhan_vien USING (true);

GRANT SELECT ON onebee.lich_su_hoi_ai TO nhan_vien;
GRANT INSERT (cau_hoi, tra_loi) ON onebee.lich_su_hoi_ai TO nhan_vien;
GRANT USAGE ON SEQUENCE onebee.lich_su_hoi_ai_id_seq TO nhan_vien;
CREATE POLICY nhan_vien_them ON onebee.lich_su_hoi_ai FOR INSERT TO nhan_vien
  WITH CHECK (nguoi_tao = onebee_noi_bo.nguoi_dung());
CREATE POLICY nhan_vien_doc ON onebee.lich_su_hoi_ai FOR SELECT TO nhan_vien
  USING (nguoi_tao = onebee_noi_bo.nguoi_dung());

-- Tìm các đoạn tri thức gần câu hỏi nhất (khoảng cách cosine, nhỏ hơn là gần hơn). Chạy bằng quyền người gọi nên RLS vẫn áp dụng.
-- truy_van: vector nhúng của câu hỏi dạng '[0.1,0.2,...]'. Chỉ so với đoạn cùng số chiều (đổi mô hình nhúng giữa chừng không gây lỗi).
CREATE FUNCTION onebee.tim_tri_thuc(truy_van text, so_luong integer DEFAULT 3)
  RETURNS TABLE (nguon text, tieu_de text, noi_dung text, khoang_cach double precision)
  LANGUAGE sql STABLE
  SET search_path = public, pg_catalog
  AS $$
    WITH q AS (SELECT truy_van::vector AS v)
    SELECT t.nguon, t.tieu_de, t.noi_dung, (t.nhung <=> q.v)::double precision
      FROM onebee.tai_lieu_tri_thuc t, q
     WHERE vector_dims(t.nhung) = vector_dims(q.v)
     ORDER BY t.nhung <=> q.v, t.nguon, t.doan
     LIMIT least(greatest(so_luong, 1), 10)
  $$;
REVOKE ALL ON FUNCTION onebee.tim_tri_thuc(text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION onebee.tim_tri_thuc(text, integer) TO nhan_vien;
