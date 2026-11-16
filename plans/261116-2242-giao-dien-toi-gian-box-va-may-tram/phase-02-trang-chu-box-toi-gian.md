---
phase: 2
title: "Trang chủ Box tối giản"
status: completed
priority: P1
effort: "1d"
dependencies: [1]
---

# Giai đoạn 2: Trang chủ Box tối giản

## Mục tiêu
Viết lại phần trình bày (HTML, CSS) của `index.html.j2` theo bản mẫu đã duyệt, giữ nguyên mọi chức năng và giao kèo với test.

## Tệp được sửa
- Sửa: `box/ansible/roles/box-stack/templates/index.html.j2`, `box/ansible/roles/box-stack/templates/huong-dan-ca.html.j2` (cùng phong cách, trang HTTP hướng dẫn cài chứng chỉ).
- Sửa: `tests/box/test_onebee_mdns_dashboard.py` (chỉ **thêm** mục kiểm; sửa kỳ vọng khi đổi chữ hiển thị thì ghi rõ lý do trong commit).
- Không sửa: `so-dieu-hanh.*`, `tasks/main.yml` của `box-stack`, tệp ngoài `box/` và `tests/box/`.

## Giao kèo phải giữ (test và JavaScript đang dựa vào)
- `id`: `ten-box`, `smb-win`, `smb`, `trang-thai`, `tt-cpu`, `tt-ram`, `tt-o-dia` (+ `-o`), `tt-cap-nhat`, `dv-tro_ly_ai`, `dv-thu_muc_chung`, `dv-sao_luu`, `dv-may_tram`, `dv-may_tram-o`, `cam-nang`; liên kết `href="#cam-nang"`.
- `a.card[data-port]` với `data-port="443" data-path="quy-trinh/"` và cổng Uptime Kuma; không có `data-port="3000"`.
- Thẻ Sổ điều hành là liên kết `/so-dieu-hanh/` khi `onebee_https_hieu_luc`, là khối không bấm được khi tắt HTTPS.
- `fetch("/trang-thai.json"`, cập nhật mỗi 60 giây, báo số liệu cũ quá 5 phút, ô máy trạm ẩn khi không có số liệu.
- Cẩm nang dựng từ `onebee_cam_nang_nhom` / `onebee_cam_nang.phim_tat` (test `tests/desktop/test_onebee_cam_nang.py` đọc template này).
- Tên đơn vị luôn qua `| e`; JavaScript chỉ dùng `textContent`.
- Nếu đổi class `.card` hay cấu trúc thẻ, cập nhật bộ chọn trong `<script>` tương ứng.

## Các bước (test trước)
1. Thêm mục kiểm vào `test_onebee_mdns_dashboard.py`, chạy thấy **trượt** trên template cũ:
   - không có ký tự emoji (dải Unicode `\U0001F300-\U0001FAFF`, `☀-➿`);
   - CSS không có `border-left`, không `text-transform:uppercase`;
   - có `@media (prefers-color-scheme: dark)`;
   - trang dựng ra ≤ 20 KB, không `http://`/`https://` trong `src=`/`href=`/`url(` trừ liên kết `box.<mã>.onebee.internal`;
   - có `<meta name="color-scheme" content="light dark">`.
2. Viết lại CSS và khung HTML theo bản mẫu; giữ nguyên khối `<script>` trừ chỗ bắt buộc đổi bộ chọn.
3. Áp cùng phong cách cho `huong-dan-ca.html.j2`.
4. Chạy: `~/.cache/onebee-kiem/bin/python -m pytest tests/box/test_onebee_mdns_dashboard.py tests/box/test_onebee_so_dieu_hanh.py tests/desktop/test_onebee_cam_nang.py tests/box/test_onebee_caddy_https.py -q` và `python3 tests/kiem-tra-mau-jinja.py` → đạt hết.
5. Dựng trang bằng dữ liệu mẫu, chụp lại 4 ảnh (sáng/tối × máy tính/điện thoại) so với bản mẫu đã duyệt.

## Kiểm chứng
- Lệnh ở bước 4 thoát 0; số mục kiểm cũ không giảm.
- Ảnh chụp khớp bản mẫu đã duyệt; không thanh cuộn ngang ở 390px.
- CI của PR (job lint) xanh.

## Rủi ro
- Đổi cấu trúc thẻ làm `querySelectorAll("a.card[data-port]")` không bắt được → lối tắt quản trị mất href. Test `data-port` + đọc script phát hiện.

## Todo
- [ ] Mục kiểm mới (trượt trên bản cũ)
- [ ] Viết lại `index.html.j2`
- [ ] Viết lại `huong-dan-ca.html.j2`
- [ ] Test đạt, ảnh chụp khớp bản mẫu
