-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
-- Nạp dữ liệu giả lập idempotent cho bản chạy thử công khai OLP 2026 (tự đặt lại lúc 03:00 mỗi ngày).
-- Chạy an toàn nhiều lần: psql -U onebee -d onebee_dxos -v ON_ERROR_STOP=1 -f scripts/nap-du-lieu-demo.sql

BEGIN;

CREATE TABLE IF NOT EXISTS don_hang (
    ma_don TEXT PRIMARY KEY,
    tieu_de TEXT NOT NULL,
    khach_hang TEXT NOT NULL,
    tong_tien BIGINT NOT NULL CHECK (tong_tien >= 0),
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('NHAP', 'CHO_DUYET', 'DA_DUYET', 'TU_CHOI')),
    nguoi_tao TEXT NOT NULL,
    ghi_chu TEXT DEFAULT '',
    cap_nhat_luc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yeu_cau_ho_tro (
    ma_yeu_cau TEXT PRIMARY KEY,
    tieu_de TEXT NOT NULL,
    muc_do TEXT NOT NULL CHECK (muc_do IN ('BINH_THUONG', 'KHAN')),
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('MOI', 'DANG_XU_LY', 'DA_XONG')),
    nguoi_tao TEXT NOT NULL,
    mo_ta TEXT DEFAULT '',
    cap_nhat_luc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS khao_sat (
    ma_khao_sat TEXT PRIMARY KEY,
    diem_hai_long INTEGER NOT NULL CHECK (diem_hai_long BETWEEN 1 AND 5),
    gop_y TEXT NOT NULL,
    nguoi_tao TEXT NOT NULL,
    cap_nhat_luc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tinh_trang_may (
    ten_may TEXT PRIMARY KEY,
    he_dieu_hanh TEXT NOT NULL,
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('TOT', 'CANH_BAO', 'LOI')),
    lan_sao_luu_cuoi TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ghi_chu TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tep_dinh_kem (
    ma_tep TEXT PRIMARY KEY,
    ten_tep TEXT NOT NULL,
    loai_mime TEXT NOT NULL,
    kich_thuoc_bytes INTEGER NOT NULL CHECK (kich_thuoc_bytes > 0 AND kich_thuoc_bytes <= 5242880),
    trang_thai_quet TEXT NOT NULL CHECK (trang_thai_quet IN ('DANG_QUET', 'CLEAN', 'INFECTED')),
    ma_don TEXT REFERENCES don_hang(ma_don) ON DELETE SET NULL,
    nguoi_tai TEXT NOT NULL,
    cap_nhat_luc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Xóa dữ liệu phát sinh ngoài bộ mẫu để đảm bảo trạng thái sau mỗi lần đặt lại 03:00 đồng nhất
DELETE FROM tep_dinh_kem WHERE ma_tep NOT LIKE 'DEMO-TEP-%';
DELETE FROM don_hang WHERE ma_don NOT LIKE 'DEMO-DH-%';
DELETE FROM yeu_cau_ho_tro WHERE ma_yeu_cau NOT LIKE 'DEMO-HT-%';
DELETE FROM khao_sat WHERE ma_khao_sat NOT LIKE 'DEMO-KS-%';
DELETE FROM tinh_trang_may WHERE ten_may NOT LIKE 'demo-%';

INSERT INTO don_hang (ma_don, tieu_de, khach_hang, tong_tien, trang_thai, nguoi_tao, ghi_chu) VALUES
    ('DEMO-DH-001', 'Cung ứng gạo ST25 vụ Đông Xuân (mẫu)', 'Cửa hàng Xanh Tây Ninh', 18500000, 'DA_DUYET', 'nhanvien1', 'Đơn mẫu đã phê duyệt'),
    ('DEMO-DH-002', 'Hạt điều rang muối đóng hộp 500g (mẫu)', 'Siêu thị Miền Đông', 12400000, 'CHO_DUYET', 'nhanvien1', 'Chờ quản lý phê duyệt 2 bước'),
    ('DEMO-DH-003', 'Mật ong hoa nhãn đóng chai 500ml (mẫu)', 'Nhà phân phối Hòa Thành', 7900000, 'CHO_DUYET', 'nhanvien1', 'Đính kèm hợp đồng PDF sạch'),
    ('DEMO-DH-004', 'Xoài cát chu đóng thùng 10kg (mẫu)', 'Bếp ăn Khu công nghiệp', 9200000, 'NHAP', 'nhanvien1', 'Bản nháp chờ kiểm tra tồn kho'),
    ('DEMO-DH-005', 'Phân bón hữu cơ vi sinh bao 25kg (mẫu)', 'Tổ hợp tác số 3', 6100000, 'TU_CHOI', 'nhanvien1', 'Thiếu phụ lục giao hàng')
ON CONFLICT (ma_don) DO UPDATE SET
    tieu_de = EXCLUDED.tieu_de,
    khach_hang = EXCLUDED.khach_hang,
    tong_tien = EXCLUDED.tong_tien,
    trang_thai = EXCLUDED.trang_thai,
    nguoi_tao = EXCLUDED.nguoi_tao,
    ghi_chu = EXCLUDED.ghi_chu,
    cap_nhat_luc = NOW();

INSERT INTO yeu_cau_ho_tro (ma_yeu_cau, tieu_de, muc_do, trang_thai, nguoi_tao, mo_ta) VALUES
    ('DEMO-HT-001', 'Cài đặt máy in hóa đơn USB trên quầy kho (mẫu)', 'KHAN', 'DANG_XU_LY', 'nhanvien1', 'Đã kiểm tra kết nối LAN và driver CUPS'),
    ('DEMO-HT-002', 'Hướng dẫn xuất trực tiếp PDF trong LibreOffice Calc (mẫu)', 'BINH_THUONG', 'DA_XONG', 'nhanvien1', 'Dùng thẻ File -> Export Directly as PDF'),
    ('DEMO-HT-003', 'Kiểm tra chứng chỉ CA trên laptop kế toán mới (mẫu)', 'BINH_THUONG', 'MOI', 'nhanvien1', 'Chờ kỹ thuật viên đối chiếu in-ca')
ON CONFLICT (ma_yeu_cau) DO UPDATE SET
    tieu_de = EXCLUDED.tieu_de,
    muc_do = EXCLUDED.muc_do,
    trang_thai = EXCLUDED.trang_thai,
    nguoi_tao = EXCLUDED.nguoi_tao,
    mo_ta = EXCLUDED.mo_ta,
    cap_nhat_luc = NOW();

INSERT INTO khao_sat (ma_khao_sat, diem_hai_long, gop_y, nguoi_tao) VALUES
    ('DEMO-KS-001', 5, 'Bộ gõ tiếng Việt Bamboo và Ribbon LibreOffice dễ chuyển từ Windows (mẫu).', 'nhanvien1'),
    ('DEMO-KS-002', 5, 'Lệnh hoi và sao lưu tự động chạy ổn định, không lo quên sao lưu (mẫu).', 'kythuat1')
ON CONFLICT (ma_khao_sat) DO UPDATE SET
    diem_hai_long = EXCLUDED.diem_hai_long,
    gop_y = EXCLUDED.gop_y,
    nguoi_tao = EXCLUDED.nguoi_tao,
    cap_nhat_luc = NOW();

INSERT INTO tinh_trang_may (ten_may, he_dieu_hanh, trang_thai, ghi_chu) VALUES
    ('demo-ketoan-01', 'Linux Mint 22.3 + OneBee OS 1.3.0', 'TOT', 'Sao lưu restic thành công 12:00'),
    ('demo-kho-01', 'Linux Mint 22.3 + OneBee OS 1.3.0', 'TOT', 'Khóa hoi hoạt động bình thường'),
    ('demo-banhang-01', 'Linux Mint 22.3 + OneBee OS 1.3.0', 'CANH_BAO', 'Quá 2 ngày chưa sao lưu (dữ liệu mẫu)')
ON CONFLICT (ten_may) DO UPDATE SET
    he_dieu_hanh = EXCLUDED.he_dieu_hanh,
    trang_thai = EXCLUDED.trang_thai,
    ghi_chu = EXCLUDED.ghi_chu,
    lan_sao_luu_cuoi = NOW();

INSERT INTO tep_dinh_kem (ma_tep, ten_tep, loai_mime, kich_thuoc_bytes, trang_thai_quet, ma_don, nguoi_tai) VALUES
    ('DEMO-TEP-001', 'hop-dong-cung-ung-gao-st25.pdf', 'application/pdf', 245760, 'CLEAN', 'DEMO-DH-001', 'nhanvien1'),
    ('DEMO-TEP-002', 'phieu-chao-gia-hat-dieu.pdf', 'application/pdf', 184320, 'CLEAN', 'DEMO-DH-002', 'nhanvien1')
ON CONFLICT (ma_tep) DO UPDATE SET
    ten_tep = EXCLUDED.ten_tep,
    loai_mime = EXCLUDED.loai_mime,
    kich_thuoc_bytes = EXCLUDED.kich_thuoc_bytes,
    trang_thai_quet = EXCLUDED.trang_thai_quet,
    ma_don = EXCLUDED.ma_don,
    nguoi_tai = EXCLUDED.nguoi_tai,
    cap_nhat_luc = NOW();

COMMIT;
