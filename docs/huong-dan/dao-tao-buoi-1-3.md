# Giáo án đào tạo người dùng OneBee OS (3 buổi)

Mỗi buổi 60–75 phút, tối đa 5 người/buổi, mỗi người ngồi đúng máy của mình. Nguyên tắc: **người dùng tự làm trên máy**,
kỹ thuật chỉ hướng dẫn; dùng file công việc thật của đơn vị (đã xin phép), không dùng file mẫu chung chung.
Sau mỗi buổi: ghi số người, thắc mắc chưa giải quyết (đưa vào nhật ký tuần, phần ghi tay).

## Buổi 1 — Làm quen (ngày cài máy)
Mục tiêu: người dùng tự mở máy, tìm ứng dụng, gõ tiếng Việt, tìm lại file cũ.
1. (10') Vì sao đổi: máy nhanh hơn/ổn định (nói số đo "trước" của chính máy đó nếu đã đo), không bản quyền lậu, có sao lưu.
2. (15') Màn hình: nút menu góc trái (hoặc phím Windows), thanh tác vụ, khay đồng hồ, tắt/khởi động lại máy.
   Thực hành: mở Firefox, LibreOffice Writer, thư mục cá nhân; ghim ứng dụng hay dùng ra thanh tác vụ.
3. (15') Gõ tiếng Việt: Telex như Unikey. Đổi Việt/Anh bằng phím tắt ghi trên [tờ phím tắt](to-phim-tat.md).
   Thực hành: gõ tên đơn vị, một câu có đủ dấu.
4. (15') File: thư mục Tài liệu, Tải xuống; file cũ từ Windows đã chép ở đâu; thư mục chung trên Box (`smb://<ip-box>/chung`).
5. (5') Khi gặp khó: menu **"Báo cần hỗ trợ (OneBee)"** — chọn loại sự cố, mô tả, gửi. Gấp thì gọi điện thêm.
Kiểm tra cuối buổi: mỗi người tự mở 1 file Word cũ của mình và sửa 1 dòng tiếng Việt.

## Buổi 2 — Văn phòng (2–3 ngày sau)
Mục tiêu: làm được việc hằng ngày với file Word/Excel, gửi đi bên ngoài không lỗi.
1. (20') LibreOffice Writer: mở .docx, sửa, lưu (mặc định vẫn là .docx), **xuất PDF** (nút PDF trên thanh công cụ), in.
2. (20') LibreOffice Calc: mở .xlsx, công thức SUM, lọc, định dạng số tiền; lưu .xlsx.
3. (10') Gửi file ra ngoài: gửi .docx/.xlsx như cũ; văn bản chính thức gửi PDF để bên nhận thấy đúng bố cục.
4. (10') Máy in, máy quét của đơn vị. Chụp màn hình (phím Print Screen).
5. (5') Những file không mở đúng → báo hỗ trợ, loại "File không mở được", ghi tên file (kỹ thuật tự lấy file).
Kiểm tra cuối buổi: mỗi người làm 1 văn bản thật của mình, xuất PDF, in 1 trang.

## Buổi 3 — Box, Trợ lý AI, tự động (tuần 2)
Mục tiêu: dùng được các tiện ích trên OneBee Box, biết dữ liệu được sao lưu thế nào.
1. (15') Trợ lý AI `http://<ip-box>:3000` → chọn "Trợ lý OneBee": soạn công văn nháp, tóm tắt văn bản.
   **AI có thể sai** — luôn đọc lại số liệu, tên, ngày tháng. Không dán mật khẩu, số tài khoản vào ô hỏi.
   Lệnh `hoi` trên máy (cho người quen dòng lệnh).
2. (15') Biểu mẫu: tóm tắt PDF (`/form/onebee-tom-tat`), nhập đơn hàng (`/form/onebee-don-hang`) — tài khoản `nhanvien`.
3. (10') Sao lưu: máy tự sao lưu 12:00 hằng ngày lên Box; lỡ xóa file thì báo hỗ trợ để lấy lại (loại "Sao lưu / mất file").
4. (10') Hỗ trợ từ xa: menu "Cho phép hỗ trợ từ xa" → đọc mã cho kỹ thuật → khi máy hỏi thì bấm "Cho phép".
   **Chỉ bấm khi chính mình vừa gọi kỹ thuật OneBee.**
5. (10') Hỏi đáp, ghi lại việc người dùng muốn tự động hóa thêm (đầu vào cho giai đoạn sau).
Kiểm tra cuối buổi: mỗi người hỏi Trợ lý 1 việc của mình và tự đánh giá câu trả lời đúng/sai.
