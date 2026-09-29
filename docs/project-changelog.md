# Nhật ký thay đổi

## [0.3.0] — 29/9/2026 — Trợ lý AI Gemma + quy trình n8n qua email
### Thêm
- Trợ lý OneBee trên Box: model `gemma4:e2b-it-qat` (ADR 0003), lời dặn tiếng Việt (có mục soạn văn bản theo NĐ 30/2020),
  tài khoản quản trị tạo sẵn, tắt đăng ký tự do, khóa API riêng từng máy trạm chỉ gọi được hỏi đáp.
- Lệnh `hoi` trên máy trạm (role `ai-cli`, cấu hình `/etc/onebee-hoi.conf`).
- 5 quy trình n8n qua email: báo cáo sao lưu (+ máy trạm quá 3 ngày chưa sao lưu), nhắc hạn thuế/BHXH/báo cáo,
  tóm tắt PDF bằng AI nội bộ, nhập đơn hàng, tổng hợp đơn hàng 17:00; chủ n8n tạo sẵn; `onebee-box dat-mat-khau-email`, `email-thu`.
- Bộ chấm AI: 40 câu tiếng Việt, 5 nhóm, ngưỡng chặt; `tests/ai/cham-diem-model.py` (chấm lại được từ CSV); báo cáo `reports/ai/`.
### Kết quả chấm (máy thử 2 vCPU, không GPU)
- `gemma4:e2b-it-qat` ĐẠT (40 câu × 3 lần: 98% ý bắt buộc, 0 lần bịa); `gemma3:1b`, `gemma3:4b` không đạt.
### Sửa
- Máy trạm v0.1 tự đổi `sao-luu.env` → `may-tram.env`; `/etc/onebee` giữ 0700. Lịch nhắc hạn thêm BHXH (Luật BHXH 2024).
- Test tóm tắt PDF: hỏi trạng thái trước khi mở trang kết quả (mở sớm thì n8n giữ kết nối mãi).
- Lệnh `hoi` bị lỗi 400 "Model not found": Open WebUI v0.11 chặn tài khoản thường dùng Trợ lý khi model nền chưa có bản ghi
  + quyền đọc → bộ cài tạo bản ghi model nền (ẩn khỏi danh sách chọn, mở quyền đọc).
### Kiểm thử (29/9, container)
- Box: 59 mục ĐẠT (cài 2 lần, AI, 7 bước n8n + tóm tắt PDF, sao lưu, máy trạm `hoi`, chỉ-thêm, bản ngày tương lai, khởi động lại).
  Chưa chạy trên máy Box thật.

## [0.2.0] — 28/9/2026 — OneBee Box v0.1 + kiểm thử mở rộng Desktop
### Thêm
- **OneBee Box** (`box/`): bộ cài Ubuntu Server 24.04 + Ansible; Docker Compose gồm trang giới thiệu (Caddy),
  Ollama (không mở cổng ra LAN), Open WebUI (tiếng Việt, tắt AI đám mây, tắt thu thập dữ liệu), n8n, Uptime Kuma,
  rest-server (`--private-repos --append-only`); Samba thư mục chung (bắt buộc mật khẩu); khóa bí mật sinh ngẫu nhiên.
- Lệnh `onebee-box`: `trang-thai`, `them-may`, `sao-luu` (Box → ổ ngoài 23:00 hằng ngày, tạm dừng dịch vụ có CSDL lúc chụp),
  `khoi-phuc-thu`.
- Desktop role `backup-client`: sao lưu `/home` lên Box 12:00 hằng ngày (chạy bù khi máy bật lại).
- Kiểm thử: `tests/desktop/run-desktop-extended-tests.sh` (5 kịch bản, gõ Telex thật qua IBus), `tests/box/…` (Docker lồng + systemd).
- ADR 0002 (nền tảng Box), hướng dẫn cài Box, `tests/README.md`.
### Bảo mật / an toàn dữ liệu (sau code review)
- Sao lưu Box: bắt buộc ổ ngoài đã gắn (mountpoint); kho chỉ tạo bằng `onebee-box khoi-tao`; khóa lệnh chạy chồng (flock).
- Chống bản sao lưu giả mạo ngày tương lai; giữ mọi bản 30 ngày của máy trạm.
- `onebee-box in-khoa` để cất khóa ngoài Box; hướng dẫn khôi phục toàn bộ.
- Chỉ dừng dịch vụ trong lúc chụp dữ liệu CSDL; bẫy chạy lại dịch vụ đặt TRƯỚC khi tạm dừng.
- Mật khẩu rest-server không lộ trong danh sách tiến trình; Samba chỉ nhận dải mạng nội bộ; giới hạn nhật ký Docker;
  IP in cho máy trạm lấy từ cổng ra mạng chính (hoặc `onebee_box_address`); không cài đè khi đã có Docker CE.
### Sửa (phát hiện nhờ kiểm thử)
- Font: Caladea (thay Cambria) thiếu chữ tiếng Việt → chữ có dấu bị lẫn font. Nay thay Cambria bằng Noto Serif
  (fontconfig + bảng thay font của LibreOffice).
- Bộ cài thiếu `python3-debian` trên Ubuntu gốc → lỗi thêm kho PPA. Đã thêm.
- n8n không chạy trên máy tắt IPv6 (mặc định nghe `::`) → đặt `N8N_LISTEN_ADDRESS=0.0.0.0`.

## [0.1.0] — 28/9/2026 — OneBee OS Desktop v0.1
### Thêm
- `desktop/onebee-install.sh` + playbook Ansible: tiếng Việt (locale, gói ngôn ngữ, IBus + Bamboo), font tương thích
  Microsoft, LibreOffice tiếng Việt lưu mặc định .docx/.xlsx/.pptx, hình nền OneBee, tự động cập nhật mintupdate.
- Kiểm thử tự động trong container Linux Mint 22.3 (có mint-artwork như máy thật): cài 2 lần (idempotent), 31 mục kiểm tra + 4 mục LibreOffice kiểm qua UNO.
- Bảo mật: PPA ibus-bamboo bị giới hạn chỉ cấp gói `ibus-bamboo` (apt pin), khóa ký lưu sẵn trong repo.
- Chờ khóa dpkg tối đa 10 phút (máy mới cài thường đang tự cập nhật ngầm).
- CI GitHub Actions: shellcheck, yamllint, ansible-lint, cài thử trên Mint 22.3.
- ADR 0001 (chọn nền tảng), `LICENSES.md` (giấy phép thành phần), hướng dẫn cài đặt.
### Đổi
- Chuyển hồ sơ dự thi vào `docs/hoi-thi/`.
- Demo web: bỏ số "80.000.000đ" và "Giảm 80%" chưa có nguồn đo — thay bằng "Theo báo giá" / "Đo khi thí điểm".
