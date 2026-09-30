# Bảng giá dịch vụ OneBee OS — cách tính

Trạng thái: **chưa có giá chính thức.** Giá tính từ chi phí thật đo trong đợt chạy thử (Phase 5, `reports/pilot/`).
Chưa có số đo thì các ô dưới để trống — không điền ước lượng.

## 1. Khung giá trong hồ sơ hội thi (chưa có cơ sở chi phí)
Hồ sơ M-02/M-03 (`docs/hoi-thi/`) ghi dải giá là **giả định nội bộ [Unverified]**: Starter 5–10 triệu (≤ 5 máy),
Business 20–40 triệu (5–20 máy), Enterprise 50–150 triệu, bảo trì 2–5 triệu/tháng. Chỉ dùng để so sánh sau khi có giá tính thật;
chênh lệch thì trình bày rõ lý do (theo rủi ro đã ghi trong plan Phase 6).

## 2. Gói theo phạm vi sản phẩm đã làm được
| Gói | Gồm | Không gồm |
|---|---|---|
| **Máy trạm** (theo máy) | Sao lưu nguyên ổ Windows (Clonezilla), cài Linux Mint + OneBee OS Desktop, chuyển file người dùng, cấu hình máy in | Mua bản quyền phần mềm khác, sửa phần cứng |
| **Box** (1 lần / đơn vị) | Cài OneBee Box: Trợ lý AI tại chỗ, n8n + các quy trình mẫu, thư mục chung, sao lưu 2 tầng, quản lý máy trạm, email báo cáo | Máy chủ + ổ sao lưu (khách mua, OneBee tư vấn cấu hình) |
| **Đào tạo** | 3 buổi theo `docs/huong-dan/dao-tao-buoi-1-3.md`, tờ phím tắt | Đào tạo nghiệp vụ kế toán, phần mềm riêng của khách |
| **Bảo trì** (theo tháng) | Theo dõi email báo cáo hằng ngày, cập nhật máy trạm từ Box, hỗ trợ qua biểu mẫu + từ xa (có đồng ý), nhật ký tuần/báo cáo tháng, diễn tập khôi phục | Thay thế phần cứng, khôi phục dữ liệu không nằm trong phạm vi sao lưu |

## 3. Công thức (điền số thật từ đợt chạy thử)
```
Giá gói = (Giờ công × Đơn giá giờ + Chi phí đi lại + Vật tư) × (1 + Dự phòng rủi ro) + Lợi nhuận
Giá bảo trì/tháng = (Giờ hỗ trợ trung bình/máy/tháng × Số máy + Giờ trực email/báo cáo) × Đơn giá giờ × (1 + Dự phòng) + Lợi nhuận
```
| Đầu vào | Giá trị | Nguồn |
|---|---|---|
| Giờ cài 1 máy trạm (gồm sao lưu Windows) | _chưa đo_ | `docs/huong-dan/cai-hang-loat.md` mục 5 |
| Giờ cài 1 Box + cấu hình email | _chưa đo_ | Ghi tay khi cài Box ở đợt chạy thử |
| Giờ đào tạo (3 buổi) + chuẩn bị | _chưa đo_ | Nhật ký tuần, phần ghi tay |
| Giờ hỗ trợ / máy / tháng | _chưa đo_ | `onebee-box bao-cao-tuan` (công xử lý) ÷ số máy |
| Đơn giá giờ công kỹ thuật | _anh chốt_ | |
| Chi phí đi lại / lần | _anh chốt_ | |
| Dự phòng rủi ro (%) | _anh chốt_ | |
| Lợi nhuận mong muốn (%) | _anh chốt_ | |
| Phần cứng phải thay (SSD, RAM) — tính riêng cho khách | _chưa đo_ | Nhật ký tuần |

## 4. So sánh chi phí với phần mềm bản quyền (cho khách tự quyết)
Chỉ so khi có **báo giá có nguồn** (đại lý/nhà cung cấp, ghi ngày báo giá). Bảng so gồm cả chi phí của OneBee (cài, đào tạo, bảo trì)
và chi phí chuyển đổi (thời gian người dùng làm quen, phần mềm phải giữ Windows). Không dùng câu "tiết kiệm X%" khi chưa có báo giá.
