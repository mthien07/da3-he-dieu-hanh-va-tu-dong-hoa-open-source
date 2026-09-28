# ADR 0001 — Nền tảng cho OneBee OS Desktop

- Ngày: 28/9/2026 · Trạng thái: Đã chốt cho v0.1

## Bối cảnh
Khách hàng mục tiêu (HTX, hộ kinh doanh, trường học, SME) dùng máy cũ, người dùng không rành kỹ thuật.
Cần: giao diện quen kiểu Windows, gõ tiếng Việt, mở file Office, tự cập nhật, cài lặp lại được trên nhiều máy.

## Quyết định
1. **Nền: Linux Mint 22.x Cinnamon** (22.3 "Zena", nền Ubuntu 24.04, chỉ amd64, hỗ trợ đến 4/2029).
   Cinnamon mặc định đã có bố cục thanh tác vụ + menu giống Windows → không cần tự làm giao diện.
2. **Không tự build ISO/distro ở v0.x.** Cài Mint chuẩn rồi chạy `desktop/onebee-install.sh`.
   Lý do: ít việc bảo trì, nhận bản vá bảo mật trực tiếp từ Mint/Ubuntu. Xét lại sau pilot.
3. **Cấu hình bằng Ansible (ansible-core từ kho Ubuntu), chạy tại chỗ.** Chạy lặp an toàn (idempotent),
   dùng lại được để quản lý nhiều máy ở Phase 4. Chỉ dùng module `ansible.builtin` (không phụ thuộc collection ngoài).
4. **Bộ gõ: ibus-bamboo** từ PPA chính thức của dự án BambooEngine; khóa ký lưu sẵn trong repo
   (vân tay `5AD2 E0B6 8A04 09AD 907D 462D 36ED 424E 9659 D014`). Dự phòng: `ibus-unikey` từ kho Ubuntu
   (đổi `onebee_input_method: unikey` trong `desktop/ansible/group_vars/all.yml`).
5. **Font: không cài font Microsoft gốc** (giấy phép riêng). Dùng font tương thích số đo
   (Liberation, Carlito, Caladea) — fontconfig tự thay tên font Microsoft.
6. **LibreOffice lưu mặc định .docx/.xlsx/.pptx** qua file cấu hình hệ thống `.xcd`
   (phải khai báo phụ thuộc writer/calc/impress, nếu không bị đè — đã kiểm bằng UNO).
7. **Cập nhật tự động: dùng tự động hóa có sẵn của mintupdate** (nâng cấp + dọn gói thừa).

## Hệ quả
- Kiểm thử tự động chạy trong container `linuxmintd/mint22.3-amd64` (có kho Mint nhưng không có giao diện
  đồ họa/systemd). Phần gõ phím, hiển thị, máy in phải kiểm trên máy ảo hoặc máy thật.
- Bản Xfce/MATE: các role dùng được, riêng hình nền mặc định chỉ áp dụng cho Cinnamon ở v0.1.
