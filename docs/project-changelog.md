# Nhật ký thay đổi

## [Chưa phát hành]
### Thêm
- SSH vào Box chỉ bằng khóa, không cho root, tối đa 3 lần thử (`onebee_box_ssh_chi_khoa`) — tự bật khi đã có khóa SSH của
  tài khoản quản trị; chưa có khóa thì giữ mật khẩu + cảnh báo (không tự khóa mình ở ngoài). Test Box thêm bước kiểm cả 2 trường hợp.
- Uptime Kuma lần cài đầu chỉ mở cổng trong Box (127.0.0.1) tới khi đã tạo tài khoản quản trị, rồi mới mở ra LAN — hết khoảng
  vài giây người trong LAN có thể giành trang "tạo tài khoản đầu tiên".
- Tường lửa Box (`roles/box-firewall`, lệnh `onebee-tuong-lua bat|tat|xem`): chỉ mạng LAN cho phép (mặc định: mạng của cổng mạng
  chính; khai báo thêm bằng `onebee_box_lan_cho_phep`) vào được dịch vụ Docker (trang giới thiệu, AI, n8n, giám sát, kho sao lưu)
  và Samba/SSH. Chặn ở `DOCKER-USER` + `INPUT` vì Docker đi vòng ufw. Cổng dịch vụ chỉ mở IPv4 (cổng IPv6 của Docker đi vòng
  tường lửa); cổng UDP NetBIOS của Samba (137/138) cũng chỉ mở cho LAN; tường lửa bật TRƯỚC khi mở dịch vụ (lần cài đầu
  không có lúc dịch vụ mở cho mọi mạng). Test Box thêm bước: máy ngoài mạng cho phép bị chặn hết, Box tự gọi dịch vụ không bị chặn.
- Khóa chặt thêm (rà soát bảo mật 8/10): n8n ghi rõ không có nút chạy lệnh hệ thống/SSH/theo dõi file, nút Code không đọc
  biến môi trường, chỉ đọc/ghi trong `~/.n8n-files`; trang giới thiệu có tiêu đề bảo mật (chống nhúng khung, ẩn tên máy chủ web);
  máy trạm chỉ cho tài khoản quản trị của Box SSH vào (`AllowUsers`), tối đa 3 lần thử khóa.
- Ngưỡng đạt chạy thử v2 (`reports/pilot/nguong-dat.md`, chờ chốt): 9 tiêu chí, 3 bắt buộc, cách kết luận; nhật ký tuần tự tính
  yêu cầu gấp có phản hồi trong 4 giờ làm việc, số máy từng phải quay về Windows (tính dồn, kể cả đã sửa), số phiếu khảo sát ≤ 2 điểm,
  tuổi bản sao lưu của mọi máy; điểm khảo sát in 2 số lẻ.
### Sửa
- Bộ cài Box tự thử lại (5 lần, cách 30 giây) khi tải image Docker và model AI — mạng chập chờn làm hỏng lần cài đầu
  (gặp thật khi thử 8/10: EOF từ Docker Hub, DNS lỗi, TLS quá giờ).
- Script test chạy được trên macOS (bash 3.2: mảng rỗng với `set -u`); test AI tự thử lại khi tải model và in lỗi thật thay vì giấu.
### Kiểm thử (8/10, Docker Desktop trên MacBook, container)
- Desktop cơ bản 40/40 ĐẠT; Desktop mở rộng 5/5 kịch bản ĐẠT; Box 81/81 ĐẠT (bản 1.0.0-rc.1, trước khi thêm tường lửa).
  Lần chạy đầu hỏng vì mạng (không phải lỗi code) → chạy lại các bước Box trên container đã giữ lại.

## [1.0.0-rc.1] — 30/9/2026 — Bản thử trước v1.0 (để thử trên máy ảo/máy thật)
Bản đủ tính năng; mọi mục đã kiểm tự động trong container (không có máy ảo/máy thật). Thử trên máy thật đạt thì phát hành 1.0.0.
### Thêm
- Giám sát: tài khoản quản trị Uptime Kuma tạo sẵn (hết "ai mở trước thành quản trị" ở mọi trang của Box), 5 mục theo dõi dịch vụ,
  email báo khi dịch vụ ngừng; bỏ trang chọn cơ sở dữ liệu lúc mở lần đầu.
- `onebee-box khoi-phuc-toan-bo [file-khóa]`: hỏng ổ Box → cài lại → lấy lại toàn bộ dữ liệu, khóa bí mật, khóa SSH bằng khóa in ra giấy;
  máy trạm chạy tiếp không phải cấu hình lại.
- Trang giới thiệu Box có lối vào 3 biểu mẫu (báo cần hỗ trợ, nhập đơn hàng, tóm tắt PDF).
- Tự phát hành: đẩy tag `v*` (hoặc nhánh `phat-hanh/v*`) → GitHub Actions đóng gói + SHA256SUMS + tạo bản phát hành (tag có `-rc` = bản thử).
- Hướng dẫn tự thử trên máy ảo có danh sách kiểm tra (`docs/huong-dan/thu-nghiem-tren-may-ao.md`); ảnh chụp màn hình thật trong tài liệu.
### Sửa
- Trợ lý OneBee biết ngày hôm nay (biến ngày của Open WebUI, múi giờ Việt Nam) và soạn ngay văn bản khi được nhờ, chỗ thiếu để [ngoặc vuông]
  — trước đó hỏi lại ngày và lấy ví dụ năm sai (phát hiện khi chụp màn hình). Bộ chấm AI thay biến ngày giống Open WebUI.
- Trên giao diện web, Open WebUI v0.11 cho model gọi "công cụ có sẵn" (lịch, ghi chú…) → Gemma gọi nhầm "tạo lịch" thay vì soạn thông báo
  và trả lời tiếng Anh. Tắt công cụ có sẵn cho "Trợ lý OneBee" → web trả lời giống lệnh `hoi` và bộ chấm. (Bộ chấm gọi thẳng Ollama nên
  không bắt được lỗi này — chỉ thấy khi thử trên giao diện; có kiểm tự động cấu hình này.)
- Lời dặn: mở thư mục chung bằng trình quản lý tệp (không phải trình duyệt), ghi đúng chuỗi phím Telex khi được hỏi cách gõ.
- Chấm lại 40 câu × 1 lần với lời dặn mới: ĐẠT 98% (N1 94%, N2 94%, N3–N5 100%, 0 bịa, 0 ý cấm) — `reports/ai/260930-luot3-*`.
### Kiểm thử (30/9, container)
- Box (Docker-in-Docker, systemd): **81/81 bước ĐẠT** — cài 2 lần, dịch vụ, AI hỏi đáp thật, quy trình n8n + email, sổ hỗ trợ,
  Uptime Kuma báo email, quản lý máy trạm qua SSH, sao lưu/khôi phục, diễn tập hỏng ổ Box → khôi phục toàn bộ, khởi động lại.
- Desktop: 5 kịch bản mở rộng (chặn sai máy, Mint, bộ gõ, systemd + SSH quản trị, Ubuntu) ĐẠT; 14 unit test Python ĐẠT; mẫu Jinja đọc được.
- Trợ lý AI: bộ chấm 40 câu ĐẠT 98%.
- Chưa thử: máy ảo/máy thật (phiên Cinnamon thật, phần cứng, LAN thật, email qua máy chủ thư thật, tốc độ AI).

## [0.6.0] — 30/9/2026 — Chuẩn bị đóng gói dịch vụ (trước v1.0)
### Thêm
- `scripts/dong-goi-ban-phat-hanh.sh <phiên-bản>`: gói `dist/onebee-os-<phiên-bản>.tar.gz` + `SHA256SUMS` + ghi chú phát hành
  (chỉ file đã commit; kiểm phiên bản khớp; chặn file giống khóa bí mật).
- Kinh doanh: cách tính giá từ chi phí thật (`docs/kinh-doanh/bang-gia.md`), mẫu hợp đồng triển khai + bảo trì có SLA (**bản nháp,
  cần luật sư xem**), biên bản khảo sát khách hàng. Kịch bản 5 video hướng dẫn.
- CI: chạy unit test Python và kiểm mọi mẫu Jinja đọc được; shellcheck thêm `onebee-ho-tro`.
### Sửa
- CI đỏ từ 0.4.0 (shellcheck SC2015 trong test, ansible-lint `command-instead-of-module`) → xanh lại.
- README viết lại theo sản phẩm thật: bỏ số liệu không có nguồn ("hàng trăm triệu"), bỏ công nghệ không dùng (vLLM, Grafana,
  Rocky, Preseed); trạng thái nói rõ chưa thử máy thật; bảng giấy phép OSI / fair-code.
- Demo web: model mô phỏng đổi sang Gemma 4 (đúng sản phẩm), bỏ câu "tiết kiệm hàng triệu đồng" chưa có nguồn.
### Kiểm thử (30/9)
- Gói `onebee-os-0.6.0.tar.gz`: `sha256sum -c` đạt; giải nén ra thư mục riêng rồi chạy test cài Desktop trên Mint 22.3 (container): đạt.
- CI: lint + unit test xanh.

## [0.5.0] — 30/9/2026 — Chuẩn bị chạy thử tại đơn vị (mô hình điểm)
### Thêm
- Biểu mẫu "Báo cần hỗ trợ" (n8n quy trình 07): ghi sổ `/srv/onebee/ho-tro/yeu-cau.csv`, email cho kỹ thuật (GẤP ghi ở tiêu đề;
  email lỗi không làm mất yêu cầu). Mục menu "Báo cần hỗ trợ (OneBee)" trên máy trạm.
- Biểu mẫu kỹ thuật ghi xử lý (quy trình 08, tài khoản `kythuat` riêng) và khảo sát hài lòng 5 câu ẩn danh (quy trình 09).
- `onebee-box bao-cao-tuan [ngày]`: nhật ký tuần Markdown (yêu cầu theo loại, còn mở, công xử lý, thời gian từ báo đến xong,
  số lần quay về Windows, khảo sát khi ≥ 3 phiếu, tình trạng máy) — không in tên người báo, mô tả, góp ý.
- Tài liệu: quy trình chạy thử 4 tuần, giáo án đào tạo 3 buổi, tờ phím tắt; `reports/pilot/` (ngưỡng đạt đề xuất, mẫu báo cáo).
### Sửa
- Sổ hỗ trợ `/srv/onebee/ho-tro` có trong bản sao lưu Box.
### Kiểm thử (30/9, container)
- Box: 73 mục ĐẠT (thêm 6 mục: báo cần hỗ trợ + email GẤP, kỹ thuật ghi xử lý bằng tài khoản riêng, khảo sát ẩn danh,
  nhật ký tuần không lộ tên/nội dung, chỉ nhận loại sự cố có sẵn, máy chủ email hỏng vẫn ghi sổ + dặn gọi điện; menu máy trạm).
- Unit test: 14 mục ĐẠT (báo cáo máy trạm + nhật ký tuần: không lộ tên/nội dung, mã gõ nhầm, nhiều lần xử lý, nhãn khớp biểu mẫu).

## [0.4.0] — 29/9/2026 — Quản lý tập trung máy trạm, hỗ trợ từ xa, bộ đo trước/sau
### Thêm
- Máy trạm báo tình trạng về Box mỗi giờ (IP, gói chờ cập nhật, bản vá bảo mật, cần khởi động lại, ổ trống, sao lưu cuối)
  qua n8n (quy trình 06, khóa riêng cho máy trạm).
- `onebee-box may-tram`: bảng tình trạng + cảnh báo (quá 3 ngày chưa sao lưu, 2 ngày mất liên lạc, ổ < 10%, bản vá bảo mật
  chưa cài, cần khởi động lại); email báo cáo 23:00 nêu từng máy.
- `onebee-box cap-nhat-may <tên>|--tat-ca`: cập nhật máy trạm qua SSH (Ansible trên Box, khóa riêng từng Box,
  tài khoản `onebee-quantri` chỉ nhận khóa từ IP của Box; SSH máy trạm tắt mật khẩu và root).
- `them-may` in 9 dòng cấu hình (thêm tên máy, IP Box, khóa báo tình trạng, khóa SSH quản trị).
- Hỗ trợ từ xa có đồng ý (`onebee-ho-tro`, x11vnc): mã 1 lần, người dùng bấm "Cho phép" mỗi kết nối, tự đóng (ADR 0004).
- `tests/do-dac/do-may.py` + hướng dẫn đo trước/sau; hướng dẫn cài hàng loạt và đường lui bằng Clonezilla.
### Sửa
- Lệnh sao lưu máy trạm chỉ nạp dòng `RESTIC_` (dán cấu hình có ký tự xuống dòng Windows vẫn chạy).
- Phiên bản ghi trong `/etc/onebee-release` và Box: 0.4.0 (trước đó vẫn ghi 0.1.0).
- Hướng dẫn cài Box: bỏ mục "ai mở trước thành quản trị" cho Trợ lý AI/n8n (đã tạo sẵn từ 0.3.0).
### Kiểm thử (29/9, container)
- Box: 67 mục ĐẠT (thêm 8 mục quản lý tập trung: SSH chỉ nhận khóa Box từ IP Box, báo tình trạng, chặn khóa sai/tên bậy,
  `may-tram` nêu máy cần xử lý, cảnh báo cần khởi động lại, cập nhật qua SSH 30 giây, email nêu máy cần xử lý).
- Desktop mở rộng: 5 kịch bản, 79 mục ĐẠT (có hỗ trợ từ xa 6 mục, bộ đo trước/sau).
- Chưa thử trên máy thật (cài 3 máy, SSH bật kiểu socket, Tailscale, đo trước/sau).

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
