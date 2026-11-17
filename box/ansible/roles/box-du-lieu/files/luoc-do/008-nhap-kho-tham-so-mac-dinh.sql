-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Cho ba tham số của hàm nhập kho giá trị mặc định để dịch vụ dữ liệu (PostgREST) khớp được lời gọi
-- chỉ gửi một phần tham số (vd chỉ p_dong) mà không phải gửi p_ngay = null.
-- Không đổi thân hàm: 006 đã áp dụng nên giữ nguyên, chỉ tạo lại với DEFAULT.
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

    -- Tồn và giá vốn TRƯỚC phiếu này (bỏ toàn bộ phiếu hiện tại): bình quân gia quyền
    SELECT COALESCE(sum(CASE WHEN p.loai = 'NHAP' THEN d.so_luong ELSE -d.so_luong END), 0)
      INTO v_ton
      FROM onebee.phieu_kho_dong d
      JOIN onebee.phieu_kho p ON p.id = d.phieu_id
     WHERE d.mat_hang_id = v_mh AND p.id <> v_phieu.id;
    SELECT gia_von INTO v_gv FROM onebee.mat_hang WHERE id = v_mh FOR UPDATE;
    IF v_gv IS NULL THEN
      RAISE EXCEPTION 'Không có mặt hàng id % trong danh mục', v_mh;
    END IF;
    IF v_ton > 0 THEN
      UPDATE onebee.mat_hang
         SET gia_von = round((v_ton * v_gv + v_sl * v_dg) / (v_ton + v_sl), 2)
       WHERE id = v_mh;
    ELSE
      UPDATE onebee.mat_hang SET gia_von = v_dg WHERE id = v_mh;
    END IF;
    v_tong := v_tong + round(v_sl * v_dg, 2);
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
