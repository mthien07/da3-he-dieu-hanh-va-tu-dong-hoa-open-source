# Nhật ký thay đổi

## [Chưa phát hành]
### Bảo mật (rà soát 10/10/2026 — Pha 1, xem `docs/security-audit.md`)
- **n8n 2.40.7 → 2.42.6** (dòng 2.40 đã ngừng nhận bản vá; bản mới vá cả 14 advisory ngày 30/9). Mọi image dịch vụ ghim **tag + digest**
  (`@sha256`, bản đa kiến trúc). Mỗi lần đổi image n8n, bộ cài tự dừng n8n và chép dữ liệu sang `/srv/onebee/n8n.truoc-<phiên bản cũ>`
  (migration CSDL không quay lui được): kiểm chỗ trống trước, chép vào thư mục tạm rồi đổi tên, lỗi giữa chừng thì bật lại n8n và dừng bộ cài.
  Chờ dịch vụ sẵn sàng lâu hơn (migration). Nhập quy trình/thông tin đăng nhập báo lỗi nếu n8n bỏ qua mục vì chính sách.
- n8n: tắt mô-đun Agents (bật sẵn từ 2.41.1) và MCP, chặn nút Git; `WEBHOOK_URL` → `N8N_WEBHOOK_URL`.
- Quy trình "Tóm tắt PDF": trang kết quả dùng chế độ chữ (n8n lọc HTML) và thoát `& < >` — câu trả lời của AI, vốn đọc từ PDF do người dùng
  tải lên, không còn hiển thị thành HTML thô. Đồng thời sửa lỗi các dòng "-" bị dồn thành một đoạn.
- Open WebUI: tắt Functions/Tools (`ENABLE_PLUGINS=false`); quản trị không xem/xuất được chat của nhân viên; nhân viên không chia sẻ chat;
  tắt chia sẻ cộng đồng; phiên đăng nhập 30 ngày. Các cài đặt lưu trong CSDL được áp qua API mỗi lần chạy bộ cài (kể cả Box đã cài).
  `onebee-webui.py` dừng và báo lỗi (thay vì bỏ qua) khi không đọc được quyền mặc định của người dùng.
- Máy trạm: báo thêm **số** tài khoản có quyền sudo (không gửi tên); Box cảnh báo (email hằng ngày, `onebee-box may-tram`) khi hơn 1 tài khoản.
  Bộ cài Desktop cảnh báo tài khoản sudo ngoài danh sách `onebee_tai_khoan_quan_tri`. Tài liệu cài hàng loạt: nhân viên dùng tài khoản thường.
- Sửa tài liệu `quan-ly-may-tram.md`: `them-may` không đụng khóa SSH đã ghim; cách xóa khóa cũ khi máy cài lại.
### Bảo mật — Pha 3 (xem `docs/security-audit.md`, F3: CA riêng, dịch vụ vẫn HTTP)
- **Biến bắt buộc mới** trong `box/ansible/group_vars/all.yml`: `onebee_box_ma_don_vi` (viết tắt tên khách; bộ cài dừng nếu thiếu/không hợp lệ) và
  `onebee_box_dia_chi` (IP tĩnh; thay `onebee_box_address`). IP chốt MỘT lần trong Ansible (`onebee_box_ip`) cho cả shell lẫn compose (sửa N3).
- **CA riêng mỗi Box**: gốc (10 năm, pathlen:1) + trung gian (1 năm, pathlen:0), sinh bằng openssl (`box-stack/files/onebee-ca.sh`), **cả hai có
  nameConstraints critical**: chỉ IP Box (/32) và `<mã>.onebee.internal`. Khóa gốc ở `secrets/ca` (0700), không gắn vào container; trung gian tự gia hạn khi
  còn < 60 ngày (lúc sao lưu đêm), cảnh báo nếu còn < 30 ngày. Đổi mã/IP bị chặn (xoay CA có chủ ý). Box tin CA của chính nó; `onebee-box in-ca`,
  `trang-thai` hiện hạn CA; `/onebee-ca.crt` phục vụ chứng chỉ gốc (công khai). Khôi phục toàn bộ giữ nguyên CA cũ (máy trạm không phải nhận lại).
- **Máy trạm — role mới `ket-noi-box`**: `them-may`/`dong-bo-may` in thêm `BOX_CA` + `BOX_CA_VAN_TAY`. Máy chỉ cài CA khi vân tay khớp **và** chứng chỉ đúng
  là CA OneBee có ràng buộc (CA:TRUE, nameConstraints critical, IP duy nhất = IP Box /32, DNS chỉ `<nhãn>.onebee.internal`, không loại tên khác); CA
  "mọi tên" bị từ chối. Cài vào kho hệ thống, Firefox (chính sách `Certificates.Install`, trộn với file của gói) và Chromium/Chrome
  (`CACertificatesWithConstraints`); thiếu `BOX_CA` thì gỡ sạch (kể cả hồ sơ Firefox, bằng certutil).
- `dong-bo-may` giờ chạy lại đúng các task của bộ cài desktop (CA, cấu hình `hoi`, mục menu) trên máy trạm — không còn giới hạn "chỉ ghi file cấu hình".
- Caddy của Box: gắn cả thư mục Caddyfile + `/data` `/config` (sửa N5).
### Bảo mật — Pha 4 (xem `docs/security-audit.md`, F3: HTTPS nội bộ, `docs/adr/0005-…`)
- **`onebee_box_https: true`** bật HTTPS: Caddy là dịch vụ DUY NHẤT công bố cổng (80 chứng chỉ gốc + hướng dẫn, 443 trang giới thiệu, 3000/5678/3001/8000 TLS); 4 dịch vụ
  backend mất `ports:`. Chứng chỉ do CA riêng cấp (`default_sni` cho kết nối bằng IP; `box.<mã>.onebee.internal` cho kỹ thuật qua Tailscale); `http://` tới cổng TLS → 308.
  Chốt chặn: lần bật đầu, mọi máy đã cấp phải đã nhận CA (không thì giữ HTTP và nêu tên máy). Dấu `secrets/https-da-bat`; chuyển HTTP↔HTTPS dừng các dịch vụ giữ cổng rồi
  khởi động backend trước, Caddy sau. Cuối bộ cài tự `dong-bo-may --tat-ca` khi CA/HTTPS đổi. Mặc định `false` (một bản phát hành giữ nhánh HTTP).
- Ứng dụng: n8n sau proxy (`N8N_PROTOCOL/HOST/EDITOR_BASE_URL/PROXY_HOPS`, bỏ `N8N_SECURE_COOKIE=false`); Open WebUI cookie Secure + `CORS_ALLOW_ORIGIN` + `WEBUI_URL` qua API;
  Uptime Kuma Trust Proxy + theo dõi cổng Caddy; Caddy `no-new-privileges`, `cap_drop ALL` + `NET_BIND_SERVICE`; kiểm sức khỏe kiểm cả nội dung.
- Máy trạm: `hoi`, `onebee-bao-tinh-trang`, `onebee-sao-luu` chỉ tin CA OneBee (ghim), **từ chối `http://` khi có dấu bền `/var/lib/onebee/https-bat`** (cờ `BOX_HTTPS=1`; chỉ Box đẩy `BOX_HTTPS=0` mới xóa);
  báo lỗi dễ hiểu (chứng chỉ lạ = có thể bị tấn công; 502/503/504; 301/308). `onebee-sao-luu` đọc cấu hình từng dòng, không chạy như mã shell (F7). Firefox/Chromium: trang chủ + dấu trang https.
- Kiểm thử: Caddy 2.11.4 thật (đã chạy), compose hai chế độ, ca, client TLS thật, `tests/box/check-https.sh`.
### Bảo mật — Pha 2 (xem `docs/security-audit.md`, F2)
- **Báo cáo tình trạng máy trạm có chữ ký** (HMAC-SHA256, khóa suy từ mật khẩu kho sao lưu của máy — chưa từng đi qua mạng). n8n không giữ khóa;
  Box tự kiểm chữ ký + độ lệch giờ (chống phát lại) khi in bảng/báo cáo. Báo cáo sai chữ ký được nêu rõ; báo cáo cũ không ký vẫn nhận (chuyển
  tiếp) nhưng gắn nhãn "chưa ký" và không được dùng để chọn địa chỉ SSH máy chưa ghim. Chữ ký đúng mà giờ ký lệch >10 phút → nhãn "lệch giờ".
- **n8n chỉ nhận báo cáo của máy đã cấp**: quy trình "Nhận tình trạng máy trạm" đọc file đánh dấu theo tên trong `/srv/onebee/may-da-cap/`
  (Box ghi, gắn chỉ đọc vào n8n); tên chưa cấp/đã thu hồi → dừng, không ghi file. Hết đường tạo file tên tùy ý.
- **SSH máy trạm: chứng minh rồi mới ghim.** Bỏ `StrictHostKeyChecking=accept-new`. Lần đầu vào máy: dùng IP trong báo cáo CÓ CHỮ KÝ (≤ 2 giờ),
  SSH đọc mật khẩu kho sao lưu trên máy và so với bản Box giữ; trùng mới ghim khóa SSH. Các lần sau `StrictHostKeyChecking=yes` + chứng minh
  lại (kể cả khóa ghim do bản cũ tạo). Máy giả ở IP đã báo không được ghim và không nhận gì.
- Lệnh mới: `thu-hoi-may` (gỡ kho HTTP, khóa Trợ lý AI, ghim SSH, chỗ báo tình trạng; bền qua `khoi-phuc-toan-bo`), `ghim-lai-may`,
  `dong-bo-may` (đẩy lại `may-tram.env` từ Box, chỉ tới máy đã chứng minh; thiếu bí mật thì bỏ qua máy, không đẩy file thiếu — kiểm cả ở playbook).
  Cấp lại máy đã thu hồi **đổi cả mật khẩu kho sao lưu** (kho + mật khẩu cũ cất riêng). Dấu thu hồi ở `secrets/thu-hoi/<tên>`.
  Sau rà soát Opus: sửa `ssh` nuốt danh sách khiến `--tat-ca` chỉ làm máy đầu (thêm `-n`), file tạm chứa mật khẩu dọn bằng trap EXIT,
  `kho` mặc định đóng, nhãn "lệch giờ".
  `in_cau_hinh_may` tách khỏi `them-may`: chỉ đọc bí mật có sẵn, không tạo tài khoản/khóa. Một hàm `may_da_cap` liệt kê máy cho mọi nơi;
  `secret_co_san` không tự sinh khóa. Nhật ký `/var/log/onebee-box/` chỉ root đọc.
- `onebee-webui.py`: thêm `lay-khoa` (chỉ đọc khóa đã cấp) và `xoa-tai-khoan`.
### Kiểm thử (Pha 1, 2)
- Pha 2: `tests/box/test_onebee_box_shell.py` (12 test chạy các lệnh shell của `onebee-box` với `ssh`/`ansible-playbook`/Open WebUI giả:
  chứng minh trước khi ghim, báo cáo chưa ký, máy giả, khóa SSH đổi, thu hồi–cấp lại, dong-bo-may, danh sách n8n); chữ ký và quy tắc `kho` trong
  `test_onebee_may_tram.py`; khớp chữ ký máy trạm ↔ Box trong `tests/desktop/test_onebee_bao_tinh_trang.py`; `check-quan-ly-tap-trung.sh`
  và `check-khoi-phuc-toan-bo.sh` (Docker lồng, CHƯA chạy) thêm ca ghim, thu hồi, dong-bo-may, báo cáo giả, thu hồi bền qua khôi phục.
  Mã JS của nút Code quy trình 06 đã chạy thử bằng Node với dữ liệu giả và nối đầu-cuối với bộ kiểm chữ ký của Box.
- Pha 1: mới: `tests/box/test_onebee_webui.py` (Open WebUI giả), `tests/desktop/test_onebee_bao_tinh_trang.py`, ca cảnh báo sudo trong
  `test_onebee_may_tram.py`; `verify-box-install.sh` và `check-n8n-inside.sh` thêm kiểm n8n/Open WebUI/CSP sandbox. CI chạy thêm test Desktop.
- Chưa chạy được trong môi trường phát triển (cần Docker lồng/systemd): `run-box-test-in-systemd-container.sh` — chạy trên máy có Docker
  hoặc CI (`workflow_dispatch` với `box`) trước khi phát hành.
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
