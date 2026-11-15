-- Khung nhìn tổng hợp khảo sát cho quản lý: số phiếu và điểm trung bình theo tuần (thứ Hai đầu tuần).
-- Không có góp ý, không có dòng lẻ: quản lý không đọc được bảng khao_sat (khảo sát ẩn danh).
-- Khung nhìn chạy bằng quyền chủ CSDL (không security_invoker) nên đọc được bảng mà người xem không có quyền.
CREATE VIEW onebee.khao_sat_tong_hop AS
  SELECT date_trunc('week', thoi_gian)::date AS tuan,
         count(*) AS so_phieu,
         round(avg(diem_1), 2) AS diem_1,
         round(avg(diem_2), 2) AS diem_2,
         round(avg(diem_3), 2) AS diem_3,
         round(avg(diem_4), 2) AS diem_4,
         round(avg(diem_5), 2) AS diem_5
    FROM onebee.khao_sat
   GROUP BY 1;

REVOKE ALL ON onebee.khao_sat_tong_hop FROM PUBLIC;
GRANT SELECT ON onebee.khao_sat_tong_hop TO quan_ly;
