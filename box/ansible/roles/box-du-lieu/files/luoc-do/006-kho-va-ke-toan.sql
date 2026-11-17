-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Kho và kế toán của OneBee Box: danh mục mặt hàng, phiếu nhập/xuất kho, nhật ký kế toán kép.
-- Luồng chính: quản lý duyệt đơn (don_hang.trang_thai_duyet → DA_DUYET) thì CSDL tự sinh phiếu xuất kho và bút toán
-- doanh thu + giá vốn TRONG CÙNG giao dịch; tồn không đủ thì chặn duyệt. Thủ kho nhập kho qua hàm them_nhap_kho
-- (một giao dịch: phiếu nhập + giá vốn bình quân + bút toán Nợ 156 / Có 111).
-- Thời gian: timestamp không múi giờ theo giờ Việt Nam như các bảng trước; ngày hạch toán dùng kiểu date.
-- Mọi quyền kiểm ở CSDL: bảng bật và ép RLS; hàm nội bộ không cấp cho vai trò nào (REVOKE … FROM PUBLIC).

-- ---------------------------------------------------------------------------------------------------
-- Danh mục mặt hàng (thẻ kho)
-- ---------------------------------------------------------------------------------------------------
CREATE TABLE onebee.mat_hang (
  id bigserial PRIMARY KEY,
  ma text NOT NULL UNIQUE CHECK (ma ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'),
  ten text NOT NULL CHECK (btrim(ten) <> '' AND length(ten) <= 200),
  don_vi text NOT NULL DEFAULT 'kg' CHECK (btrim(don_vi) <> '' AND length(don_vi) <= 16),
  -- Giá vốn bình quân gia quyền, cập nhật mỗi lần nhập kho
  gia_von numeric NOT NULL DEFAULT 0 CHECK (gia_von >= 0),
  gia_ban numeric NOT NULL DEFAULT 0 CHECK (gia_ban >= 0),
  ton_toi_thieu numeric NOT NULL DEFAULT 0 CHECK (ton_toi_thieu >= 0),
  hoat_dong boolean NOT NULL DEFAULT true,
  tao_luc timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung()
);
-- Tên mặt hàng không phân biệt hoa thường khi khớp với đơn hàng
CREATE UNIQUE INDEX mat_hang_ten_key ON onebee.mat_hang (lower(ten));
ALTER TABLE onebee.mat_hang ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.mat_hang FORCE ROW LEVEL SECURITY;

-- Đơn hàng trỏ tới thẻ kho khi gửi từ danh mục; đơn cũ (không có mat_hang_id) khớp theo tên lúc duyệt
ALTER TABLE onebee.don_hang ADD COLUMN mat_hang_id bigint REFERENCES onebee.mat_hang(id);
CREATE INDEX don_hang_mat_hang_id_idx ON onebee.don_hang (mat_hang_id);

-- ---------------------------------------------------------------------------------------------------
-- Phiếu kho
-- ---------------------------------------------------------------------------------------------------
CREATE SEQUENCE onebee.phieu_kho_so_seq;

CREATE TABLE onebee.phieu_kho (
  id bigserial PRIMARY KEY,
  so_phieu text NOT NULL UNIQUE,
  loai text NOT NULL CHECK (loai IN ('NHAP', 'XUAT')),
  ngay date NOT NULL DEFAULT (onebee_noi_bo.bay_gio()::date),
  dien_gia text NOT NULL DEFAULT '',
  -- Phiếu xuất tự sinh khi duyệt đơn: mỗi đơn tối đa một phiếu xuất
  don_hang_id bigint UNIQUE REFERENCES onebee.don_hang(id),
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  tao_luc timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  CONSTRAINT chi_phieu_xuat_co_don CHECK (loai = 'XUAT' OR don_hang_id IS NULL)
);
ALTER TABLE onebee.phieu_kho ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.phieu_kho FORCE ROW LEVEL SECURITY;

CREATE TABLE onebee.phieu_kho_dong (
  id bigserial PRIMARY KEY,
  phieu_id bigint NOT NULL REFERENCES onebee.phieu_kho(id) ON DELETE CASCADE,
  mat_hang_id bigint NOT NULL REFERENCES onebee.mat_hang(id),
  so_luong numeric NOT NULL CHECK (so_luong > 0),
  don_gia numeric NOT NULL CHECK (don_gia >= 0),
  thanh_tien numeric GENERATED ALWAYS AS (round(so_luong * don_gia, 2)) STORED
);
CREATE INDEX phieu_kho_dong_mat_hang_idx ON onebee.phieu_kho_dong (mat_hang_id);
ALTER TABLE onebee.phieu_kho_dong ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.phieu_kho_dong FORCE ROW LEVEL SECURITY;

-- Số phiếu tự sinh theo loại và ngày: PN-20261117-0001 / PX-20261117-0001
CREATE FUNCTION onebee_noi_bo.phieu_kho_so() RETURNS trigger
  LANGUAGE plpgsql
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
BEGIN
  IF NEW.so_phieu IS NULL OR btrim(NEW.so_phieu) = '' THEN
    NEW.so_phieu := (CASE NEW.loai WHEN 'NHAP' THEN 'PN-' ELSE 'PX-' END)
      || to_char(COALESCE(NEW.ngay, onebee_noi_bo.bay_gio()::date), 'YYYYMMDD')
      || '-' || lpad(nextval('onebee.phieu_kho_so_seq')::text, 4, '0');
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER phieu_kho_so BEFORE INSERT ON onebee.phieu_kho FOR EACH ROW EXECUTE FUNCTION onebee_noi_bo.phieu_kho_so();

-- Chặn xuất quá tồn: khoá dòng thẻ kho (hai người xuất cùng lúc vẫn tuần tự), so tồn thực rồi mới cho ghi.
-- Tồn = tổng nhập − tổng xuất của mọi phiếu đã ghi (dòng mới chưa nằm trong bảng nên không cần trừ).
CREATE FUNCTION onebee_noi_bo.kiem_ton_kho() RETURNS trigger
  LANGUAGE plpgsql
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
DECLARE
  v_loai text;
  v_ten text;
  v_ton numeric;
BEGIN
  SELECT loai INTO v_loai FROM onebee.phieu_kho WHERE id = NEW.phieu_id;
  IF v_loai IS DISTINCT FROM 'XUAT' THEN
    RETURN NEW;
  END IF;

  SELECT ten INTO v_ten FROM onebee.mat_hang WHERE id = NEW.mat_hang_id FOR UPDATE;
  SELECT COALESCE(sum(CASE WHEN p.loai = 'NHAP' THEN d.so_luong ELSE -d.so_luong END), 0)
    INTO v_ton
    FROM onebee.phieu_kho_dong d
    JOIN onebee.phieu_kho p ON p.id = d.phieu_id
   WHERE d.mat_hang_id = NEW.mat_hang_id;

  IF v_ton < NEW.so_luong THEN
    RAISE EXCEPTION 'Không đủ tồn kho: mặt hàng "%" còn % , cần %',
      v_ten, v_ton, NEW.so_luong
      USING ERRCODE = 'check_violation',
            HINT = 'Nhập kho thêm mặt hàng này rồi duyệt lại đơn.';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER kiem_ton_kho BEFORE INSERT ON onebee.phieu_kho_dong FOR EACH ROW EXECUTE FUNCTION onebee_noi_bo.kiem_ton_kho();

-- ---------------------------------------------------------------------------------------------------
-- Kế toán: hệ thống tài khoản và nhật ký kép
-- ---------------------------------------------------------------------------------------------------
CREATE TABLE onebee.tai_khoan (
  ma text PRIMARY KEY CHECK (ma ~ '^[0-9]{3,4}$'),
  ten text NOT NULL,
  -- tai_san / chi_phi: số dư bình thường bên Nợ; no_phai_tra / von / doanh_thu: bên Có
  loai text NOT NULL CHECK (loai IN ('tai_san', 'no_phai_tra', 'von', 'doanh_thu', 'chi_phi'))
);
ALTER TABLE onebee.tai_khoan ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.tai_khoan FORCE ROW LEVEL SECURITY;

-- Hệ thống tài khoản tối thiểu cho HTX/hộ kinh doanh (Thông tư 133); bổ sung tài khoản là tệp lược đồ mới
INSERT INTO onebee.tai_khoan (ma, ten, loai) VALUES
  ('111', 'Tiền mặt', 'tai_san'),
  ('112', 'Tiền gửi ngân hàng', 'tai_san'),
  ('131', 'Phải thu khách hàng', 'tai_san'),
  ('152', 'Nguyên liệu, vật liệu', 'tai_san'),
  ('156', 'Hàng hóa', 'tai_san'),
  ('331', 'Phải trả người bán', 'no_phai_tra'),
  ('411', 'Vốn đầu tư của chủ sở hữu', 'von'),
  ('511', 'Doanh thu bán hàng và cung cấp dịch vụ', 'doanh_thu'),
  ('632', 'Giá vốn hàng bán', 'chi_phi'),
  ('642', 'Chi phí quản lý', 'chi_phi');

CREATE SEQUENCE onebee.but_toan_so_seq;

CREATE TABLE onebee.but_toan (
  id bigserial PRIMARY KEY,
  so_hieu text NOT NULL UNIQUE DEFAULT ('BT-' || lpad(nextval('onebee.but_toan_so_seq')::text, 6, '0')),
  ngay date NOT NULL DEFAULT (onebee_noi_bo.bay_gio()::date),
  dien_gia text NOT NULL CHECK (btrim(dien_gia) <> ''),
  -- Chứng từ gốc: 'don_hang:<id>' hoặc 'phieu_kho:<id>'
  chung_tu text,
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  tao_luc timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio()
);
ALTER TABLE onebee.but_toan ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.but_toan FORCE ROW LEVEL SECURITY;

CREATE TABLE onebee.but_toan_dong (
  id bigserial PRIMARY KEY,
  but_toan_id bigint NOT NULL REFERENCES onebee.but_toan(id) ON DELETE CASCADE,
  tai_khoan text NOT NULL REFERENCES onebee.tai_khoan(ma),
  no numeric NOT NULL DEFAULT 0 CHECK (no >= 0),
  co numeric NOT NULL DEFAULT 0 CHECK (co >= 0),
  -- Mỗi dòng ghi đúng một bên Nợ hoặc Có
  CONSTRAINT mot_ben CHECK ((no > 0) <> (co > 0))
);
CREATE INDEX but_toan_dong_but_toan_idx ON onebee.but_toan_dong (but_toan_id);
ALTER TABLE onebee.but_toan_dong ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.but_toan_dong FORCE ROW LEVEL SECURITY;

-- Ghi một bút toán cân Nợ = Có. Chỉ dùng nội bộ (trigger/hàm khác gọi), không cấp quyền cho vai trò nào.
CREATE FUNCTION onebee_noi_bo.ghi_but_toan(p_ngay date, p_dien_gia text, p_chung_tu text, p_dong jsonb)
  RETURNS bigint
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
DECLARE
  v_id bigint;
  v_dong jsonb;
  v_no numeric;
  v_co numeric;
  v_tong_no numeric := 0;
  v_tong_co numeric := 0;
BEGIN
  IF jsonb_typeof(p_dong) IS DISTINCT FROM 'array' OR jsonb_array_length(p_dong) < 2 THEN
    RAISE EXCEPTION 'Bút toán phải có ít nhất hai dòng';
  END IF;

  INSERT INTO onebee.but_toan (ngay, dien_gia, chung_tu)
  VALUES (COALESCE(p_ngay, onebee_noi_bo.bay_gio()::date), p_dien_gia, p_chung_tu)
  RETURNING id INTO v_id;

  FOR v_dong IN SELECT * FROM jsonb_array_elements(p_dong) LOOP
    v_no := COALESCE((v_dong->>'no')::numeric, 0);
    v_co := COALESCE((v_dong->>'co')::numeric, 0);
    IF (v_no > 0) = (v_co > 0) THEN
      RAISE EXCEPTION 'Mỗi dòng bút toán phải có đúng một bên Nợ hoặc Có (tài khoản %)', v_dong->>'tai_khoan';
    END IF;
    INSERT INTO onebee.but_toan_dong (but_toan_id, tai_khoan, no, co)
    VALUES (v_id, v_dong->>'tai_khoan', v_no, v_co);
    v_tong_no := v_tong_no + v_no;
    v_tong_co := v_tong_co + v_co;
  END LOOP;

  IF v_tong_no <> v_tong_co THEN
    RAISE EXCEPTION 'Bút toán không cân: tổng Nợ % khác tổng Có %', v_tong_no, v_tong_co;
  END IF;
  RETURN v_id;
END $$;

-- ---------------------------------------------------------------------------------------------------
-- Nhập kho (thủ kho/quản lý gọi qua API): một giao dịch gồm phiếu, dòng, giá vốn bình quân, bút toán
-- p_dong: [{"mat_hang_id": 1, "so_luong": 100, "don_gia": 70000}, …]
-- ---------------------------------------------------------------------------------------------------
CREATE FUNCTION onebee.them_nhap_kho(p_ngay date, p_dien_gia text, p_dong jsonb)
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

-- ---------------------------------------------------------------------------------------------------
-- Duyệt đơn bán hàng → phiếu xuất kho + bút toán doanh thu và giá vốn, cùng giao dịch với thao tác duyệt.
-- Tồn thiếu thì trigger kiem_ton_kho ném lỗi, cả thao tác duyệt bị hoàn tác (đơn vẫn CHO_DUYET).
-- Đơn cũ (nguon khác NULL) không phát sinh chứng từ.
-- ---------------------------------------------------------------------------------------------------
CREATE FUNCTION onebee_noi_bo.don_hang_hoan_tat() RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = pg_catalog, onebee, onebee_noi_bo
  AS $$
DECLARE
  v_mh onebee.mat_hang%ROWTYPE;
  v_phieu_id bigint;
  v_gia_von numeric;
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

  INSERT INTO onebee.phieu_kho (loai, ngay, dien_gia, don_hang_id)
  VALUES ('XUAT', v_ngay, 'Xuất bán cho ' || NEW.khach_hang, NEW.id)
  RETURNING id INTO v_phieu_id;

  INSERT INTO onebee.phieu_kho_dong (phieu_id, mat_hang_id, so_luong, don_gia)
  VALUES (v_phieu_id, v_mh.id, NEW.so_luong_kg, NEW.don_gia);

  IF NEW.thanh_tien > 0 THEN
    PERFORM onebee_noi_bo.ghi_but_toan(
      v_ngay,
      'Bán hàng cho ' || NEW.khach_hang || ' — đơn #' || NEW.id,
      'don_hang:' || NEW.id,
      jsonb_build_array(
        jsonb_build_object('tai_khoan', '131', 'no', NEW.thanh_tien),
        jsonb_build_object('tai_khoan', '511', 'co', NEW.thanh_tien)));
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
CREATE TRIGGER don_hang_hoan_tat AFTER UPDATE ON onebee.don_hang FOR EACH ROW EXECUTE FUNCTION onebee_noi_bo.don_hang_hoan_tat();

-- ---------------------------------------------------------------------------------------------------
-- Khung nhìn cho trang Sổ điều hành. Chạy bằng quyền chủ CSDL (như khao_sat_tong_hop) nên chỉ cấp cho
-- đúng vai trò được xem; RLS của bảng gốc không áp cho khung nhìn.
-- ---------------------------------------------------------------------------------------------------
CREATE VIEW onebee.ton_kho AS
  SELECT m.id AS mat_hang_id, m.ma, m.ten, m.don_vi, m.gia_von, m.gia_ban, m.ton_toi_thieu, m.hoat_dong,
         COALESCE(sum(CASE WHEN p.loai = 'NHAP' THEN d.so_luong ELSE -d.so_luong END), 0) AS ton
    FROM onebee.mat_hang m
    LEFT JOIN onebee.phieu_kho_dong d ON d.mat_hang_id = m.id
    LEFT JOIN onebee.phieu_kho p ON p.id = d.phieu_id
   GROUP BY m.id, m.ma, m.ten, m.don_vi, m.gia_von, m.gia_ban, m.ton_toi_thieu, m.hoat_dong;

CREATE VIEW onebee.so_kho AS
  SELECT p.id AS phieu_id, p.so_phieu, p.loai, p.ngay, p.dien_gia, p.don_hang_id, p.nguoi_tao,
         d.id AS dong_id, d.mat_hang_id, m.ma AS ma_hang, m.ten AS ten_hang, m.don_vi,
         d.so_luong, d.don_gia, d.thanh_tien
    FROM onebee.phieu_kho p
    JOIN onebee.phieu_kho_dong d ON d.phieu_id = p.id
    JOIN onebee.mat_hang m ON m.id = d.mat_hang_id
   ORDER BY p.ngay DESC, p.id DESC, d.id;

CREATE VIEW onebee.so_nhat_ky AS
  SELECT b.id AS but_toan_id, b.so_hieu, b.ngay, b.dien_gia, b.chung_tu, b.nguoi_tao,
         d.id AS dong_id, d.tai_khoan, t.ten AS ten_tai_khoan, d.no, d.co
    FROM onebee.but_toan b
    JOIN onebee.but_toan_dong d ON d.but_toan_id = b.id
    JOIN onebee.tai_khoan t ON t.ma = d.tai_khoan
   ORDER BY b.ngay DESC, b.id DESC, d.id;

CREATE VIEW onebee.bang_can_doi AS
  SELECT t.ma AS tai_khoan, t.ten, t.loai,
         COALESCE(sum(d.no), 0) AS tong_no,
         COALESCE(sum(d.co), 0) AS tong_co,
         COALESCE(sum(d.no - d.co), 0) AS du
    FROM onebee.tai_khoan t
    LEFT JOIN onebee.but_toan_dong d ON d.tai_khoan = t.ma
   GROUP BY t.ma, t.ten, t.loai;
