-- Lược đồ dữ liệu tác nghiệp của OneBee Box (PostgreSQL + pgvector). Bộ cài áp dụng MỘT lần, ghi vào onebee.lich_su_luoc_do;
-- đã áp dụng thì không sửa tệp này nữa — thay đổi lược đồ luôn là tệp mới có số tiếp theo.
-- Thời gian: timestamp without time zone theo giờ Việt Nam, khớp dạng yyyy-MM-dd HH:mm của sổ cũ (CSV do n8n ghi).
-- Thứ tự cột dữ liệu = thứ tự cột của sổ cũ = thứ tự khi xuất cho báo cáo tuần; sau đó mới tới các cột thêm.
-- nguon/dong: tên tệp sổ cũ (tính từ thư mục dữ liệu) và số dòng trong tệp, bắt đầu từ 1 — lệnh chuyển dữ liệu khử trùng theo cặp này;
-- dòng tạo qua API có nguon, dong là NULL. Danh mục (loại, mức độ, cách xử lý) chỉ chặn dòng mới: sổ cũ mang nhãn lạ vẫn nạp được.

CREATE EXTENSION IF NOT EXISTS vector;

-- Hàm dùng chung nằm ngoài lược đồ onebee (lược đồ onebee là thứ dịch vụ dữ liệu công bố ra API)
CREATE SCHEMA onebee_noi_bo;

-- Tên đăng nhập của người gọi: claim sub trong JWT do cầu nối danh tính ký (NULL khi không đi qua API)
CREATE FUNCTION onebee_noi_bo.nguoi_dung() RETURNS text
  LANGUAGE sql STABLE
  AS $$ SELECT nullif(current_setting('request.jwt.claims', true), '')::json->>'sub' $$;

-- Giờ Việt Nam hiện tại, làm tròn tới phút như sổ cũ
CREATE FUNCTION onebee_noi_bo.bay_gio() RETURNS timestamp without time zone
  LANGUAGE sql STABLE
  AS $$ SELECT date_trunc('minute', now() AT TIME ZONE 'Asia/Ho_Chi_Minh') $$;

CREATE TABLE onebee.don_hang (
  thoi_gian timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  khach_hang text NOT NULL,
  mat_hang text NOT NULL,
  so_luong_kg numeric NOT NULL,
  don_gia numeric NOT NULL,
  thanh_tien numeric NOT NULL,
  ngay_giao text,
  ghi_chu text,
  id bigserial PRIMARY KEY,
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  nguon text,
  dong integer,
  trang_thai_duyet text,
  nguoi_duyet text,
  ly_do_duyet text,
  thoi_gian_duyet timestamp without time zone,
  UNIQUE (nguon, dong),
  CHECK ((nguon IS NULL) = (dong IS NULL)),
  CHECK (so_luong_kg > 0 AND don_gia >= 0),
  CHECK (thanh_tien >= 0),
  -- NULL: dòng sổ cũ, không qua quy trình duyệt; dòng mới luôn có trạng thái
  CHECK (trang_thai_duyet IN ('CHO_DUYET', 'DA_DUYET', 'TU_CHOI')),
  CHECK (nguon IS NOT NULL OR trang_thai_duyet IS NOT NULL),
  -- Không ai tự duyệt đơn của mình
  CHECK (nguoi_duyet IS NULL OR nguoi_duyet <> nguoi_tao)
);
ALTER TABLE onebee.don_hang ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.don_hang FORCE ROW LEVEL SECURITY;

CREATE TABLE onebee.yeu_cau_ho_tro (
  -- Mã như biểu mẫu n8n đang cấp: yyMMdd-HHmmss-<2 số ngẫu nhiên>
  ma text NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYMMDD-HH24MISS') || '-' || (10 + floor(random() * 90))::int),
  thoi_gian timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  may text,
  loai text NOT NULL,
  muc_do text NOT NULL,
  nguoi_bao text,
  mo_ta text,
  id bigserial PRIMARY KEY,
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  nguon text,
  dong integer,
  UNIQUE (ma),
  UNIQUE (nguon, dong),
  CHECK ((nguon IS NULL) = (dong IS NULL)),
  -- Danh mục loại sự cố: box/ansible/roles/box-n8n/vars/main.yml (onebee_ho_tro_loai)
  CHECK (nguon IS NOT NULL OR loai IN ('File không mở được / sai định dạng', 'Phần mềm chỉ chạy trên Windows', 'Máy in / máy quét',
                                       'Mạng / Internet', 'Gõ tiếng Việt', 'Máy chậm / treo', 'Sao lưu / mất file', 'Khác')),
  -- Mức độ: đúng giá trị sổ cũ ghi (biểu mẫu 07-yeu-cau-ho-tro: "Gấp (đang dừng việc)" → gap, "Bình thường" → binh-thuong)
  CHECK (nguon IS NOT NULL OR muc_do IN ('gap', 'binh-thuong'))
);
ALTER TABLE onebee.yeu_cau_ho_tro ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.yeu_cau_ho_tro FORCE ROW LEVEL SECURITY;

CREATE TABLE onebee.xu_ly_ho_tro (
  ma text NOT NULL,
  thoi_gian timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  cach_xu_ly text NOT NULL,
  so_phut integer NOT NULL,
  ghi_chu text,
  id bigserial PRIMARY KEY,
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  nguon text,
  dong integer,
  UNIQUE (nguon, dong),
  CHECK ((nguon IS NULL) = (dong IS NULL)),
  CHECK (so_phut >= 0),
  -- Danh mục cách xử lý: box/ansible/roles/box-n8n/vars/main.yml (onebee_ho_tro_cach_xu_ly)
  CHECK (nguon IS NOT NULL OR cach_xu_ly IN ('Hướng dẫn người dùng', 'Sửa cấu hình', 'Cài thêm phần mềm', 'Thay phần cứng',
                                             'Quay về Windows (máy/phần mềm)', 'Chưa xử lý được'))
);
ALTER TABLE onebee.xu_ly_ho_tro ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.xu_ly_ho_tro FORCE ROW LEVEL SECURITY;

-- Khảo sát ẩn danh: không có cột người tạo
CREATE TABLE onebee.khao_sat (
  thoi_gian timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio(),
  diem_1 smallint NOT NULL CHECK (diem_1 BETWEEN 1 AND 5),
  diem_2 smallint NOT NULL CHECK (diem_2 BETWEEN 1 AND 5),
  diem_3 smallint NOT NULL CHECK (diem_3 BETWEEN 1 AND 5),
  diem_4 smallint NOT NULL CHECK (diem_4 BETWEEN 1 AND 5),
  diem_5 smallint NOT NULL CHECK (diem_5 BETWEEN 1 AND 5),
  gop_y text,
  id bigserial PRIMARY KEY,
  nguon text,
  dong integer,
  UNIQUE (nguon, dong),
  CHECK ((nguon IS NULL) = (dong IS NULL))
);
ALTER TABLE onebee.khao_sat ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.khao_sat FORCE ROW LEVEL SECURITY;

-- Tình trạng máy trạm: nguyên văn bao bì có chữ ký (<tên>.json); việc kiểm chữ ký vẫn do onebee-may-tram.py làm
CREATE TABLE onebee.tinh_trang_may (
  ten text PRIMARY KEY CHECK (ten ~ '^[a-z0-9][a-z0-9-]{0,31}$'),
  bao_bi jsonb NOT NULL,
  nhan_luc bigint NOT NULL
);
ALTER TABLE onebee.tinh_trang_may ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.tinh_trang_may FORCE ROW LEVEL SECURITY;

-- Chuẩn bị cho kho tệp (tệp đã qua kiểm dịch); chưa cấp quyền cho vai trò nào
CREATE TABLE onebee.tep_dinh_kem (
  id bigserial PRIMARY KEY,
  ten_tep text NOT NULL,
  kich_thuoc bigint NOT NULL CHECK (kich_thuoc >= 0),
  sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  tao_luc timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio()
);
ALTER TABLE onebee.tep_dinh_kem ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.tep_dinh_kem FORCE ROW LEVEL SECURITY;

-- Chuẩn bị cho Trợ lý tra cứu tri thức (vector nhúng, số chiều chốt khi chọn mô hình nhúng); chưa cấp quyền cho vai trò nào
CREATE TABLE onebee.tai_lieu_tri_thuc (
  id bigserial PRIMARY KEY,
  tieu_de text NOT NULL,
  noi_dung text NOT NULL,
  nhung vector,
  tao_luc timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio()
);
ALTER TABLE onebee.tai_lieu_tri_thuc ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.tai_lieu_tri_thuc FORCE ROW LEVEL SECURITY;

CREATE TABLE onebee.lich_su_hoi_ai (
  id bigserial PRIMARY KEY,
  nguoi_tao text NOT NULL DEFAULT onebee_noi_bo.nguoi_dung(),
  cau_hoi text NOT NULL,
  tra_loi text,
  thoi_gian timestamp without time zone NOT NULL DEFAULT onebee_noi_bo.bay_gio()
);
ALTER TABLE onebee.lich_su_hoi_ai ENABLE ROW LEVEL SECURITY;
ALTER TABLE onebee.lich_su_hoi_ai FORCE ROW LEVEL SECURITY;

-- Đơn hàng mới (tạo qua API, nguon NULL) luôn bắt đầu ở CHO_DUYET, chưa có người duyệt — người tạo không tự đặt được
CREATE FUNCTION onebee_noi_bo.don_hang_moi() RETURNS trigger
  LANGUAGE plpgsql
  AS $$
BEGIN
  IF NEW.nguon IS NULL THEN
    NEW.trang_thai_duyet := 'CHO_DUYET';
    NEW.nguoi_duyet := NULL;
    NEW.ly_do_duyet := NULL;
    NEW.thoi_gian_duyet := NULL;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER don_hang_moi BEFORE INSERT ON onebee.don_hang FOR EACH ROW EXECUTE FUNCTION onebee_noi_bo.don_hang_moi();

-- Duyệt đơn: người duyệt (claim sub) và giờ duyệt do CSDL ghi, người dùng không tự đặt được
CREATE FUNCTION onebee_noi_bo.don_hang_duyet() RETURNS trigger
  LANGUAGE plpgsql
  AS $$
BEGIN
  IF NEW.trang_thai_duyet IS DISTINCT FROM OLD.trang_thai_duyet OR NEW.ly_do_duyet IS DISTINCT FROM OLD.ly_do_duyet THEN
    NEW.nguoi_duyet := onebee_noi_bo.nguoi_dung();
    NEW.thoi_gian_duyet := onebee_noi_bo.bay_gio();
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER don_hang_duyet BEFORE UPDATE ON onebee.don_hang FOR EACH ROW EXECUTE FUNCTION onebee_noi_bo.don_hang_duyet();
