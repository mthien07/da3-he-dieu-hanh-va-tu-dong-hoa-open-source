# MẪU HỢP ĐỒNG TRIỂN KHAI VÀ BẢO TRÌ ONEBEE OS (BẢN NHÁP)

> **Bản nháp kỹ thuật — chưa được người có chuyên môn pháp lý xem.** Phải nhờ luật sư/chuyên viên pháp chế kiểm tra
> căn cứ pháp lý, hiệu lực văn bản và điều khoản trách nhiệm trước khi ký với khách hàng. Các phần trong [ngoặc vuông] điền theo
> từng hợp đồng.

**Căn cứ (luật sư kiểm lại hiệu lực và văn bản thay thế):** Bộ luật Dân sự số 91/2015/QH13; Luật Thương mại số 36/2005/QH11;
quy định hiện hành về bảo vệ dữ liệu cá nhân; nhu cầu và khả năng của hai bên.

**Bên A (khách hàng):** [tên, địa chỉ, MST, người đại diện]
**Bên B (bên cung cấp dịch vụ):** Hợp tác xã OneBee — MST 1102128064 — [địa chỉ, người đại diện theo giấy chứng nhận đăng ký HTX]

## Điều 1. Phạm vi dịch vụ
1. Triển khai: sao lưu nguyên ổ đĩa hiện có (trước khi cài), cài đặt OneBee OS Desktop trên [số] máy trạm, cài đặt OneBee Box
   trên máy chủ của Bên A, đào tạo [3] buổi. Danh sách máy và phần mềm cần giữ lại theo **Phụ lục 1 (biên bản khảo sát)**.
2. Bảo trì [hằng tháng]: theo dõi báo cáo sao lưu và tình trạng máy hằng ngày; cập nhật phần mềm máy trạm; tiếp nhận và xử lý
   yêu cầu hỗ trợ theo Điều 3; gửi báo cáo tháng (tổng hợp từ nhật ký tuần); diễn tập khôi phục dữ liệu [mỗi quý].
3. Không thuộc phạm vi (trừ khi có phụ lục riêng): sửa chữa, thay thế phần cứng; phần mềm của bên thứ ba; khôi phục dữ liệu nằm
   ngoài phạm vi sao lưu (Điều 5); đào tạo nghiệp vụ.

## Điều 2. Phần mềm và giấy phép
Phần mềm cài đặt là phần mềm nguồn mở và nguồn công bố, giữ nguyên giấy phép của tác giả (danh sách tại `LICENSES.md`).
Bên B **không bán giấy phép phần mềm**; phí hợp đồng là phí dịch vụ triển khai, đào tạo, bảo trì. n8n dùng theo Sustainable Use
License — chỉ cài cho nhu cầu nội bộ của Bên A.

## Điều 3. Mức dịch vụ (SLA) — đo bằng sổ yêu cầu hỗ trợ trên OneBee Box
| Mức độ (người báo chọn trên biểu mẫu) | Phản hồi | Xử lý hoặc có phương án tạm |
|---|---|---|
| Gấp (đang dừng việc) | [2] giờ làm việc | Trong [1] ngày làm việc (phương án tạm: máy dự phòng / khôi phục bản sao lưu) |
| Bình thường | [1] ngày làm việc | Trong [3] ngày làm việc |
Giờ làm việc: [7h30–17h00, thứ Hai–thứ Sáu, trừ ngày nghỉ lễ]. Thời điểm tính: giờ ghi trên sổ yêu cầu hỗ trợ của OneBee Box.
Báo qua điện thoại được Bên B nhập vào sổ ngay khi nhận.

## Điều 4. Trách nhiệm của Bên A
Cung cấp máy chủ, ổ sao lưu ngoài theo tư vấn của Bên B; **luôn cắm ổ sao lưu**; giữ điện, mạng cho máy chủ; thông báo cho người
dùng về việc Box sao lưu dữ liệu `/home` và có quyền quản trị máy trạm (Điều 5); cử đầu mối liên hệ; không tự ý thay đổi cấu hình
do Bên B quản lý.

## Điều 5. Dữ liệu và bảo mật
1. Sao lưu: thư mục người dùng (`/home`) của máy trạm → OneBee Box hằng ngày; dữ liệu Box → ổ ngoài hằng ngày. Dữ liệu lưu ngoài
   các vị trí này không được sao lưu.
2. Người quản trị OneBee Box (Bên B khi bảo trì) **đọc được bản sao lưu** và **có quyền quản trị máy trạm** để cập nhật. Bên B chỉ
   dùng quyền này để thực hiện hợp đồng, không sao chép, tiết lộ dữ liệu của Bên A; nhân sự của Bên B ký cam kết bảo mật.
3. Hỗ trợ từ xa chỉ thực hiện khi người dùng tự bấm cho phép trên máy.
4. Khóa bí mật (in từ `onebee-box in-khoa`) giao Bên A cất giữ ngay khi nghiệm thu.
5. Trợ lý AI chạy tại máy chủ của Bên A, không gửi câu hỏi ra ngoài. Email báo cáo đi qua máy chủ thư Bên A chọn và có chứa dữ liệu
   kinh doanh (theo `docs/huong-dan/dung-tro-ly-ai-va-quy-trinh-tu-dong.md`).

## Điều 6. Nghiệm thu
Theo **Phụ lục 2**: máy trạm cài đủ, gõ tiếng Việt, mở file mẫu của Bên A, sao lưu chạy (có bản trên Box), khôi phục thử 1 file đạt,
email báo cáo tới đúng người nhận, bàn giao khóa bí mật và tài liệu.

## Điều 7. Giá, thanh toán
[Giá triển khai, giá bảo trì/tháng theo `docs/kinh-doanh/bang-gia.md`; lịch thanh toán; hóa đơn.]

## Điều 8. Chấm dứt hợp đồng và bàn giao
Khi chấm dứt: Bên B bàn giao toàn bộ khóa bí mật, mật khẩu quản trị, hướng dẫn vận hành; gỡ khóa SSH của Bên B khỏi máy trạm nếu
Bên A yêu cầu; hỗ trợ xuất dữ liệu trong [30] ngày. Hệ thống vẫn chạy được mà không cần Bên B (phần mềm nguồn mở, cấu hình tại chỗ).

## Điều 9. Giới hạn trách nhiệm, bất khả kháng, giải quyết tranh chấp
[Luật sư soạn: mức bồi thường tối đa, trường hợp miễn trách, thương lượng → hòa giải → tòa án có thẩm quyền.]

**Phụ lục 1:** Biên bản khảo sát (theo `docs/kinh-doanh/khao-sat-khach-hang.md`) · **Phụ lục 2:** Biên bản nghiệm thu
