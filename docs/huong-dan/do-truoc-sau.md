# Đo máy trước/sau khi cài OneBee OS

Mục đích: có số liệu thật "trước (Windows) — sau (OneBee OS)" trên **cùng một máy**. File CSV trong `reports/do-dac/` là
**nguồn duy nhất** cho mọi con số về tốc độ trên slide, tài liệu giới thiệu. Chưa đo thì ghi "chưa đo", không ước lượng.

## Quy tắc đo
- Cùng một máy, cùng người đo, cắm điện (không chạy pin), không cắm thêm thiết bị lạ.
- Đo ngay sau khi bật máy và đăng nhập, **chưa mở ứng dụng nào**; mỗi ứng dụng đo lần mở đầu tiên sau khi bật máy.
- Các cột `bam_gio_*` đo bằng **đồng hồ bấm giờ trên điện thoại**, cùng một cách ở Windows và OneBee OS — **chỉ so sánh các cột này**
  giữa trước và sau. Cột `tu_do_*` do máy tự đo (chỉ có trên Linux), dùng để so các lần đo trên OneBee OS với nhau.
- Mỗi số đo 3 lần (tắt/bật máy giữa các lần đo khởi động), ghi số giữa (trung vị).

| Cột | Cách bấm giờ |
|---|---|
| `bam_gio_khoi_dong_giay` | Từ lúc bấm nút nguồn → màn hình đăng nhập hiện ra |
| `bam_gio_mo_van_ban_giay` | Từ lúc bấm mở trình soạn văn bản (Word / LibreOffice Writer) → gõ được chữ |
| `bam_gio_mo_trinh_duyet_giay` | Từ lúc bấm mở trình duyệt (Chrome/Edge / Firefox) → trang trống hiện ra |

## Trước: máy Windows (ghi tay vào CSV)
1. Bấm giờ 3 cột trên.
2. `ram_trong_mb`: Task Manager → Performance → Memory → **Available** (đổi GB ra MB) — xem ngay sau khi đăng nhập.
3. `o_trong_gb`: This PC → ổ C: → dung lượng còn trống. `loai_o`: Task Manager → Performance → Disk (SSD/HDD).
4. `he_dieu_hanh`, `cpu`, `ram_tong_mb`: Settings → System → About.
5. Mở `reports/do-dac/<đơn-vị>.csv` bằng LibreOffice Calc/Excel, thêm 1 dòng, `giai_doan` = `truoc`, bỏ trống cột `tu_do_*`.

## Sau: máy đã cài OneBee OS
```bash
sudo apt install -y xdotool
python3 tests/do-dac/do-may.py --don-vi htx-onebee --may ketoan-01 --giai-doan sau \
  --bam-gio-khoi-dong 48 --bam-gio-van-ban 6.5 --bam-gio-trinh-duyet 4 -o reports/do-dac/htx-onebee.csv
```
Script tự lấy cấu hình máy, RAM trống, ổ trống, thời gian khởi động (systemd-analyze), tự mở LibreOffice Writer và Firefox
để đo, rồi thêm 1 dòng vào CSV (các số bấm giờ nhập bằng tham số). Script ghi chú nếu máy đã bật quá 15 phút.

## Báo cáo
Khi có đủ dòng `truoc` và `sau` của một máy: so từng cột `bam_gio_*`, `ram_trong_mb`, `o_trong_gb`. Nêu kèm cấu hình máy,
số lần đo, ngày đo. Không cộng/trung bình số của các máy khác cấu hình với nhau.
