# Lộ trình OneBee OS

Tài liệu này tách rõ **đã phát hành**, **đang hoàn thiện** và **định hướng**. Chỉ mục đầu có bằng chứng chạy được; hai mục sau là kế hoạch, chưa có cam kết về thời điểm.
Chi tiết thay đổi từng bản: [docs/project-changelog.md](docs/project-changelog.md). Kiến trúc: [docs/kien-truc-dx-os.md](docs/kien-truc-dx-os.md).

## Đã phát hành
| Bản | Ngày | Nội dung | File tải |
|---|---|---|---|
| 1.0.0 | 15/10/2026 | Bộ cài máy trạm (Linux Mint 22.x: gõ Telex, LibreOffice .docx/.xlsx, `hoi`, tự sao lưu) và OneBee Box (Ubuntu Server 24.04: Trợ lý AI chạy tại chỗ, sao lưu hai tầng, giám sát, thư mục chung, quản lý tập trung máy trạm, HTTPS nội bộ bằng CA riêng) | `.tar.gz` + `SHA256SUMS` |
| 1.1.0 | 22/10/2026 | Trang chủ Box tìm thấy bằng `onebee.local`, bộ tự chẩn đoán, trợ lý mở file Windows, kho mẫu soạn văn bản hành chính, cảnh báo sự cố qua Telegram, bộ cài USB offline | Không có (bản này chưa đính kèm file) |
| 1.2.0 | 14/11/2026 | Trung tâm OneBee, trang Kiểm tra máy, nhắc sao lưu trễ, mẫu soạn văn bản cho Trợ lý AI | `.tar.gz` + `SHA256SUMS` |

Nguồn: [Releases](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/releases).

## Đang hoàn thiện: lõi DX-OS Open-Core (dự thi OLP 2026)
Biến OneBee Box thành nền tảng lõi chạy ngầm theo Khung kiến trúc DX-OS của Đề thi. Chỉ ghi "đã chạy" khi bộ kiểm Box của bản đó đạt.
- Đăng nhập một lần (Authelia, TOTP hai lớp cho `ky_thuat` và `quan_ly`) và cổng API trên Caddy; cầu nối danh tính ký JWT 60 giây.
- Cơ sở dữ liệu PostgreSQL + pgvector, API tự sinh PostgREST, phân quyền tới cấp dòng (RLS) trên mọi bảng; lệnh chuyển sổ cũ vào CSDL.
- Động cơ quy trình Node-RED (luồng phê duyệt, thư báo cáo, nhắc hạn) thay thành phần fair-code trước đây.
- Kho tệp SeaweedFS và kiểm dịch ClamAV (bản bỏ `libclamunrar`); cập nhật chữ ký ClamAV khi Box không có Internet.
- Trợ lý AI và RAG chạy trên lõi (`onebee-ai-rag`, Ollama, Gemma 4), thay giao diện AI có điều khoản thương hiệu.
- Ứng dụng Sổ điều hành đi trọn bốn không gian H-P-D-I; chế độ bản chạy thử công khai với dữ liệu giả lập tự đặt lại lúc 03:00.
- Dòng giấy phép trong từng tệp mã, gói phát hành có `LICENSE`.

Việc còn mở trước khi nộp bài: chạy thử trên Box thật, dựng bản chạy thử công khai trên một host thật (cần nhà cung cấp, tên miền), phát hành bản có file tải.

## Định hướng (chưa làm, chưa có lịch)
Xếp theo thứ tự ưu tiên hiện tại.
1. **Dữ liệu lạnh phân tích (Lakehouse):** đẩy dữ liệu lịch sử từ PostgreSQL xuống kho đối tượng theo định dạng bảng mở (Apache Iceberg trên SeaweedFS) cho báo cáo nhiều kỳ. Chưa có.
2. **Kết nối thiết bị hiện trường (IoT / OT):** thu cảm biến nhà kho, vườn trồng theo chuẩn NGSI-LD vào cùng đường ống PostgreSQL và Node-RED. Chưa có; hiện chỉ hội tụ tình trạng máy trạm.
3. **Danh mục dữ liệu và phả hệ (OpenMetadata)** khi một đơn vị có nhiều cơ sở dữ liệu liên phòng ban.
4. **Chuỗi cung ứng bản phát hành:** ký gói phát hành và image (Cosign hoặc Minisign) trong quy trình phát hành.
5. **Tầng Nền tảng Kinh doanh số:** ứng dụng cắm-rút đầu tiên (hóa đơn điện tử, thanh toán QR) trên API đã có của Tầng 1.
6. **Nhiều Box chi nhánh:** đồng bộ giữa các Box qua WireGuard hoặc Tailscale, định danh liên kết.

## Đóng góp
- Hướng dẫn đóng góp và cách chạy kiểm thử: [CONTRIBUTING.md](CONTRIBUTING.md)
- Báo lỗi, đề xuất: [Issues](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/issues)
- Báo lỗ hổng bảo mật (riêng tư): [SECURITY.md](SECURITY.md)
