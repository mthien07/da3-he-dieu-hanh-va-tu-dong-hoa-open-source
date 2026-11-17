-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Siết toàn vẹn số liệu sau lượt rà soát kho/kế toán:
--   1. Thẻ kho: chỉ được sửa cột mô tả; giá vốn chỉ do hàm nhập kho ghi. Nhân viên chỉ đọc cột cần cho biểu mẫu đơn.
--   2. Duyệt đơn: doanh thu tính từ số lượng × đơn giá (không tin thành tiền do trình duyệt gửi), chặn lệch số,
--      chặn đơn ghi tên mặt hàng khác với thẻ kho được chọn.
--   3. Nhập kho: khoá thẻ kho TRƯỚC khi đọc tồn, cộng dồn theo từng mặt hàng trong cùng phiếu (bình quân đúng,
--      thứ tự khoá theo id để tránh deadlock khi hai người nhập cùng lúc).
--   4. Bảng dấu chế độ demo để script đặt lại dữ liệu mẫu chỉ chạy khi chế độ demo đang bật.

-- ---------------------------------------------------------------------------------------------------
-- 1. Quyền theo cột của thẻ kho
-- ---------------------------------------------------------------------------------------------------
REVOKE INSERT, UPDATE ON onebee.mat_hang FROM thu_kho, quan_ly;
GRANT INSERT (ma, ten, don_vi, gia_ban, ton_toi_thieu, hoat_dong) ON onebee.mat_hang TO thu_kho, quan_ly;
GRANT UPDATE (ten, don_vi, gia_ban, ton_toi_thieu, hoat_dong) ON onebee.mat_hang TO thu_kho, quan_ly;
-- Nhân viên chỉ cần id/tên/đơn vị/trạng thái cho danh sách chọn ở biểu mẫu đơn; giá vốn là dữ liệu biên lợi nhuận
REVOKE SELECT ON onebee.mat_hang FROM nhan_vien;
GRANT SELECT (id, ma, ten, don_vi, hoat_dong) ON onebee.mat_hang TO nhan_vien;

-- ---------------------------------------------------------------------------------------------------
-- 2. Duyệt đơn: doanh thu theo số lượng × đơn giá; tên mặt hàng phải khớp thẻ kho
-- ---------------------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION onebee_noi_bo.don_hang_hoan_tat() RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
DECLARE
  v_mh onebee.mat_hang%ROWTYPE;
  v_phieu_id bigint;
  v_gia_von numeric;
  v_doanh_thu numeric;
  v_ngay date := onebee_noi_bo.bay_gio()::date;
BEGIN
  IF NEW.trang_thai_duyet IS DISTINCT FROM 'DA_DUYET' OR OLD.trang_thai_duyet = 'DA_DUYET' THEN
    RETURN NEW;
  END IF;
  IF NEW.nguon IS NOT NULL THEN
    RETURN NEW;   -- dòng sổ cũ, không có chứng từ kho
  END IF;
  IF EXISTS (SELECT 1 FROM onebee.phieu_kho WHERE don_hang_id = NEW.id) THEN
    RETURN NEW;   -- đã có phiếu xuất (duyệt lại không nhân đôi chứng từ)
  END IF;

  SELECT * INTO v_mh
    FROM onebee.mat_hang
   WHERE (NEW.mat_hang_id IS NOT NULL AND id = NEW.mat_hang_id)
      OR (NEW.mat_hang_id IS NULL AND lower(ten) = lower(btrim(NEW.mat_hang)))
   LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'mat_hang_chua_co: mặt hàng "%" chưa có trong danh mục kho — vào khu Kho thêm mặt hàng rồi duyệt lại',
      NEW.mat_hang USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.mat_hang_id IS NOT NULL AND lower(btrim(NEW.mat_hang)) <> lower(v_mh.ten) THEN
    RAISE EXCEPTION 'mat_hang_khong_khop: đơn ghi "%" nhưng thẻ kho được chọn là "%" — sửa lại đơn trước khi duyệt',
      NEW.mat_hang, v_mh.ten USING ERRCODE = 'check_violation';
  END IF;

  -- Doanh thu do CSDL tính, không tin số thành tiền do trình duyệt gửi
  v_doanh_thu := round(NEW.so_luong_kg * NEW.don_gia, 2);
  IF NEW.thanh_tien IS DISTINCT FROM v_doanh_thu THEN
    RAISE EXCEPTION 'thanh_tien_khong_khop: thành tiền % không khớp số lượng × đơn giá (%) — sửa lại đơn trước khi duyệt',
      NEW.thanh_tien, v_doanh_thu USING ERRCODE = 'check_violation';
  END IF;

  INSERT INTO onebee.phieu_kho (loai, ngay, dien_gia, don_hang_id)
  VALUES ('XUAT', v_ngay, 'Xuất bán cho ' || NEW.khach_hang, NEW.id)
  RETURNING id INTO v_phieu_id;

  INSERT INTO onebee.phieu_kho_dong (phieu_id, mat_hang_id, so_luong, don_gia)
  VALUES (v_phieu_id, v_mh.id, NEW.so_luong_kg, NEW.don_gia);

  IF v_doanh_thu > 0 THEN
    PERFORM onebee_noi_bo.ghi_but_toan(
      v_ngay,
      'Bán hàng cho ' || NEW.khach_hang || ' — đơn #' || NEW.id,
      'don_hang:' || NEW.id,
      jsonb_build_array(
        jsonb_build_object('tai_khoan', '131', 'no', v_doanh_thu),
        jsonb_build_object('tai_khoan', '511', 'co', v_doanh_thu)));
  END IF;

  v_gia_von := round(NEW.so_luong_kg * v_mh.gia_von, 2);
  IF v_gia_von > 0 THEN
    PERFORM onebee_noi_bo.ghi_but_toan(
      v_ngay,
      'Giá vốn đơn #' || NEW.id || ' — ' || v_mh.ten,
      'don_hang:' || NEW.id,
      jsonb_build_array(
        jsonb_build_object('tai_khoan', '632', 'no', v_gia_von),
        jsonb_build_object('tai_khoan', '156', 'co', v_gia_von)));
  END IF;

  RETURN NEW;
END $$;

-- ---------------------------------------------------------------------------------------------------
-- 3. Nhập kho: khoá thẻ kho trước khi đọc tồn, cộng dồn theo mặt hàng trong cùng phiếu
-- ---------------------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION onebee.them_nhap_kho(
    p_ngay date DEFAULT NULL,
    p_dien_gia text DEFAULT '',
    p_dong jsonb DEFAULT '[]'::jsonb)
  RETURNS onebee.phieu_kho
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
DECLARE
  v_phieu onebee.phieu_kho;
  v_dong jsonb;
  v_mh bigint;
  v_sl numeric;
  v_dg numeric;
  v_ton numeric;
  v_gv numeric;
  v_tong numeric := 0;
  v_nh record;
BEGIN
  IF onebee_noi_bo.nguoi_dung() IS NULL THEN
    RAISE EXCEPTION 'Chưa đăng nhập — không ghi được phiếu nhập';
  END IF;
  IF jsonb_typeof(p_dong) IS DISTINCT FROM 'array' OR jsonb_array_length(p_dong) = 0 THEN
    RAISE EXCEPTION 'Phiếu nhập phải có ít nhất một dòng';
  END IF;

  INSERT INTO onebee.phieu_kho (loai, ngay, dien_gia)
  VALUES ('NHAP', COALESCE(p_ngay, onebee_noi_bo.bay_gio()::date), COALESCE(nullif(btrim(p_dien_gia), ''), 'Nhập kho'))
  RETURNING * INTO v_phieu;

  FOR v_dong IN SELECT * FROM jsonb_array_elements(p_dong) LOOP
    v_mh := (v_dong->>'mat_hang_id')::bigint;
    v_sl := (v_dong->>'so_luong')::numeric;
    v_dg := (v_dong->>'don_gia')::numeric;
    IF v_mh IS NULL THEN
      RAISE EXCEPTION 'Dòng nhập thiếu mặt hàng';
    END IF;
    IF v_sl IS NULL OR v_sl <= 0 THEN
      RAISE EXCEPTION 'Số lượng nhập phải là số lớn hơn 0';
    END IF;
    IF v_dg IS NULL OR v_dg < 0 THEN
      RAISE EXCEPTION 'Đơn giá nhập không được âm';
    END IF;
    INSERT INTO onebee.phieu_kho_dong (phieu_id, mat_hang_id, so_luong, don_gia)
    VALUES (v_phieu.id, v_mh, v_sl, v_dg);
  END LOOP;

  -- Cộng dồn theo mặt hàng (một phiếu có thể có nhiều dòng cùng mặt hàng), khoá theo thứ tự id để tránh deadlock
  FOR v_nh IN
    SELECT mat_hang_id, sum(so_luong) AS sl, sum(round(so_luong * don_gia, 2)) AS gt
      FROM jsonb_to_recordset(p_dong) AS x(mat_hang_id bigint, so_luong numeric, don_gia numeric)
     GROUP BY mat_hang_id
     ORDER BY mat_hang_id
  LOOP
    -- Khoá thẻ kho TRƯỚC khi đọc tồn: hai người nhập cùng mặt hàng xếp hàng, không ghi đè giá vốn của nhau
    SELECT gia_von INTO v_gv FROM onebee.mat_hang WHERE id = v_nh.mat_hang_id FOR UPDATE;
    IF v_gv IS NULL THEN
      RAISE EXCEPTION 'Không có mặt hàng id % trong danh mục', v_nh.mat_hang_id;
    END IF;
    SELECT COALESCE(sum(CASE WHEN p.loai = 'NHAP' THEN d.so_luong ELSE -d.so_luong END), 0)
      INTO v_ton
      FROM onebee.phieu_kho_dong d
      JOIN onebee.phieu_kho p ON p.id = d.phieu_id
     WHERE d.mat_hang_id = v_nh.mat_hang_id AND p.id <> v_phieu.id;
    IF v_ton > 0 THEN
      UPDATE onebee.mat_hang
         SET gia_von = round((v_ton * v_gv + v_nh.gt) / (v_ton + v_nh.sl), 2)
       WHERE id = v_nh.mat_hang_id;
    ELSE
      UPDATE onebee.mat_hang SET gia_von = round(v_nh.gt / v_nh.sl, 2) WHERE id = v_nh.mat_hang_id;
    END IF;
    v_tong := v_tong + v_nh.gt;
  END LOOP;

  IF v_tong > 0 THEN
    PERFORM onebee_noi_bo.ghi_but_toan(
      v_phieu.ngay,
      'Nhập kho ' || v_phieu.so_phieu || COALESCE(' — ' || nullif(btrim(p_dien_gia), ''), ''),
      'phieu_kho:' || v_phieu.id,
      jsonb_build_array(
        jsonb_build_object('tai_khoan', '156', 'no', v_tong),
        jsonb_build_object('tai_khoan', '111', 'co', v_tong)));
  END IF;

  RETURN v_phieu;
END $$;

-- ---------------------------------------------------------------------------------------------------
-- 4. Dấu chế độ demo: script đặt lại dữ liệu mẫu chỉ được xoá dữ liệu khi dấu này bật
-- ---------------------------------------------------------------------------------------------------
CREATE TABLE onebee.che_do_demo (
  bat boolean NOT NULL DEFAULT false
);
INSERT INTO onebee.che_do_demo (bat) VALUES (false);
ALTER TABLE onebee.che_do_demo ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.che_do_demo FORCE ROW LEVEL SECURITY;
