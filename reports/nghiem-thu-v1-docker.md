# Nghiệm thu v1.0.0 trong container Docker (14–15/10/2026)

**Kết luận:** mã nguồn v1.0.0 **đạt toàn bộ** bài nghiệm thu tự động trong container: Box 126 PASS / 0 FAIL, Desktop 71 PASS / 0 FAIL,
cả hai bộ cài chạy lần 2 `changed=0 failed=0`. **Đây không phải nghiệm thu trên máy thật** — chưa cài tại đơn vị nào, chưa có số đo tốc độ
trên phần cứng thật (phiếu `docs/kiem-thu-tren-may-that.md` nhóm B–E còn mở).

## Phạm vi và mã được kiểm

| Hạng mục | Commit | Môi trường | Kết quả |
|---|---|---|---|
| OneBee Box — kiểm thử đầy đủ (`tests/box/run-box-test-in-systemd-container.sh`) | `b13d00d` (mã `box/`, `tests/box/`, `scripts/` không đổi tới `119ec76`) | Ubuntu 24.04 + systemd, Docker lồng, `--privileged`; model sản phẩm `gemma4:e2b-it-qat` | **126 PASS / 0 FAIL**, "TẤT CẢ BƯỚC KIỂM THỬ BOX ĐẠT" |
| OneBee OS Desktop (`tests/desktop/run-desktop-test-in-mint-container.sh`) | `119ec76` | `linuxmintd/mint22.3-amd64` + `mintupdate mint-artwork cinnamon-desktop-data cinnamon-common nemo-data` | Lần 1 `ok=66 changed=41 failed=0`; lần 2 `ok=62 changed=0 failed=0`; **71 PASS / 0 FAIL** |
| Desktop kiểm thử mở rộng (gõ Telex thật, file Word, systemd, Unikey, Ubuntu) | `e19e3ef` | GitHub Actions, CI run `38594774522` | Đạt |
| Unit test + mẫu Jinja | `119ec76` | Image `ubuntu:24.04` như CI | Box 118 (11 bỏ qua vì thiếu công cụ trong image), Desktop 62 (1 bỏ qua), AI 17: OK; 23 mẫu Jinja, 0 lỗi |
| Lint | `e19e3ef` | CI + `requirements-dev.txt` (ansible-core 2.19.13, ansible-lint 26.9.0, yamllint 1.38.0) | `ansible-lint site.yml` Box/Desktop 0 lỗi, `yamllint -s .` sạch, `shellcheck` sạch |

Sau nghiệm thu chỉ đổi chuỗi phiên bản `1.0.0-rc.1` → `1.0.0` trong `group_vars` (ghi vào `/etc/onebee-release`), changelog, README và tài liệu — không đổi mã cài đặt.

Máy chạy container: Docker Desktop 29.3.1, linux/amd64, kernel `6.12.76-linuxkit`, 16 CPU, 16 GB RAM.
Nhật ký gốc (không đưa vào kho vì dài và có dữ liệu thử): `~/onebee-da3-test-logs/box-test-full-8-b13d00d.log`
(SHA-256 bắt đầu `9cfabf294febd9e5`); log Desktop lưu ở thư mục tạm của phiên kiểm thử (SHA-256 bắt đầu `d63069928b01183b`).
Danh sách đầy đủ các mục PASS ở phụ lục được trích nguyên văn từ hai log này (thời gian ghi trong một vài dòng là thời gian trong container, không phải số đo hiệu năng).

## Box: các bước đã chạy
Cài lần 1 → cài lần 2 (idempotent) → kiểm 44 mục dịch vụ → SSH chỉ bằng khóa → AI hỏi đáp thật → quy trình n8n qua email →
sao lưu Box ra ổ ngoài + khôi phục → máy trạm Mint 22.3 sao lưu lên Box → quản lý tập trung qua SSH → tường lửa chỉ mở cho LAN →
tắt Trợ lý AI (lệnh `hoi` báo lỗi dễ hiểu) → bản sao lưu giả mạo ngày tương lai → hỏng ổ Box, cài lại + khôi phục toàn bộ bằng khóa in giấy →
bật HTTPS (chốt chặn máy chưa nhận CA, máy trạm qua HTTPS, chạy lại `changed=0`, tắt HTTPS) → xoay khóa máy trạm + Box →
chưa gắn ổ sao lưu → khởi động lại Box.

Các bản sửa ngày 14/10 có mục kiểm riêng trong lần chạy này:
- CORS/WebSocket Open WebUI (`b13d00d`): Origin lạ bị chặn cả API lẫn bắt tay WebSocket; Origin hợp lệ được CORS và WebSocket `101`, ở cả HTTP và HTTPS.
- Xoay khóa (`3a3ecda`): mật khẩu kho cũ bị từ chối (401), khóa `hoi` cũ hết hiệu lực, máy trạm nhận khóa mới qua `dong-bo-may`; `--box` đổi mật khẩu quản trị/n8n/biểu mẫu và đồng bộ webhook.
- Tường lửa (`96663cd`): chỉ LAN vào được dịch vụ, cổng chỉ mở IPv4. Trường hợp bảng `mangle` lỗi chỉ kiểm bằng unit test (`tests/box/test_onebee_tuong_lua.py`), không giả lập được trong runner.
- Ghim CA khi địa chỉ viết hoa (`1e31337`) và gỡ CA cũ khỏi hồ sơ Firefox (`97b11f6`): kiểm bằng unit test; runner kiểm máy trạm tin đúng CA của Box (kho hệ thống, Firefox, Chromium).

## Lịch sử lần chạy trên mã cuối
- Lượt 6 (`b13d00d`, 21:51–23:13 14/10): đạt từ cài đặt tới AI hỏi đáp; dừng ở phần n8n vì tải image `axllent/mailpit` từ Docker Hub bị ngắt (`EOF`) — lỗi mạng, không phải lỗi sản phẩm.
- Lượt 7 (23:15–23:20): Docker trong Box giả lập bị ngắt khi tải image (`EOF`) ở lần cài 1 — lỗi mạng.
- Lượt 8 (23:37 14/10 – 01:03 15/10): **đạt toàn bộ**. Không sửa mã giữa các lượt; chỉ tải sẵn image mailpit và chạy khi không có bài thử khác dùng mạng.
- Desktop: lượt đầu (agent UI) hỏng vì `packages.linuxmint.com` từ chối kết nối trước khi chạy mã OneBee; lượt sau đạt 51 PASS (thiếu schema Cinnamon/Nemo nên một số mục bị bỏ qua); bổ sung `cinnamon-common` + `nemo-data` (`119ec76`) thì đạt 71 PASS.

## Những gì bài nghiệm thu này KHÔNG chứng minh
- **Máy thật:** phần cứng Box, ổ USB thật, LAN thật, router, máy in/máy quét, Windows 10/11 mở `\\onebee-box` (B15), Tailscale thật.
- **Phiên Cinnamon thật:** container không có phiên đồ họa Cinnamon — chưa thấy trên màn hình nút menu, ứng dụng ghim, biểu tượng màn hình nền, Ribbon hiển thị, bấm thật Win+E/D/L. Bài thử chỉ kiểm giá trị cấu hình (gsettings, file applet, cấu hình LibreOffice qua UNO).
- **Nhận diện Linux Mint:** image `linuxmintd/mint22.3-amd64` có `/etc/os-release` là Ubuntu 24.04.5, nên bộ cài đi nhánh "không phải Linux Mint" (cảnh báo) — nhánh nhận diện Mint chưa được chạy.
- **Tốc độ:** kernel `linuxkit` trên máy phát triển, không phải phần cứng mục tiêu. Báo cáo này không công bố số đo tốc độ AI, thời gian cài hay tài nguyên.
- **Vòng đời tường lửa gắn Docker** (rà soát bảo mật mục 10, `plans/reports/security-261014-2145-review-truoc-phat-hanh-v1.md`): dừng/nâng cấp Docker gỡ quy tắc tường lửa tới khi Docker chạy lại — vấn đề có từ trước, chưa sửa, runner không kiểm.

## Câu hỏi còn mở
- Có tách quy tắc INPUT + `mangle` của tường lửa sang unit không gắn Docker trước khi phát hành không (mục 10 rà soát bảo mật)?

## Phụ lục A — Box: 126 mục PASS (log lượt 8, commit `b13d00d`)
```text
PASS  Lần cài đầu: giám sát chỉ mở trong Box tới khi có tài khoản quản trị, rồi mới mở ra LAN
PASS  Chạy lần 2 không thay đổi gì
PASS  Có file phiên bản Box
PASS  Docker đang chạy và bật cùng máy
PASS  Container onebee-portal đang chạy
PASS  Container onebee-ollama đang chạy
PASS  Container onebee-open-webui đang chạy
PASS  Container onebee-n8n đang chạy
PASS  Container onebee-uptime-kuma đang chạy
PASS  Container onebee-rest-server đang chạy
PASS  Trang giới thiệu :80 hiển thị OneBee Box
PASS  Open WebUI :3000 khỏe (/health)
PASS  n8n :5678 khỏe (/healthz)
PASS  Uptime Kuma :3001 trả lời
PASS  Uptime Kuma: tài khoản quản trị tạo sẵn + 5 mục theo dõi (không còn "ai mở trước thành quản trị")
PASS  Giám sát mở ra LAN chỉ sau khi đã có tài khoản quản trị
PASS  Open WebUI :3000 không cho Origin lạ đọc API kèm cookie (CORS giới hạn cả ở chế độ HTTP)
PASS  Open WebUI :3000 cho Origin hợp lệ (http://<IP Box>:3000) đọc API: access-control-allow-origin trả đúng Origin đó
PASS  Open WebUI :3000 nhận bắt tay WebSocket (chat thời gian thực) từ Origin hợp lệ (101)
PASS  Open WebUI :3000 từ chối bắt tay WebSocket từ Origin lạ (có phản hồi, không phải 101)
PASS  Kho sao lưu :8000 đòi mật khẩu (401)
PASS  Trang giới thiệu gửi kèm tiêu đề bảo mật (chống nhúng khung, không lộ tên máy chủ web)
PASS  n8n khóa chặt: không có nút chạy lệnh hệ thống, nút Code không đọc biến môi trường
PASS  n8n: tắt mô-đun Agents và MCP, chặn nút Git (rà soát bảo mật 10/10)
PASS  Các image dịch vụ ghim theo digest (@sha256), n8n không còn dòng 2.40.x đã ngừng vá
PASS  Open WebUI: tắt Functions/Tools; quản trị không đọc/xuất chat; tắt chia sẻ chat (biến môi trường)
PASS  Open WebUI (CSDL): không đăng ký tự do, không chia sẻ cộng đồng, phiên 30 ngày, nhân viên tạo được khóa API nhưng không chia sẻ chat
PASS  n8n chỉ ĐỌC được danh sách máy đã cấp (may-da-cap): gắn read-only, không tự thêm máy để nhận báo cáo giả
PASS  Ollama KHÔNG mở cổng ra ngoài (11434)
PASS  Ollama chạy được bên trong (Open WebUI gọi tới)
PASS  Open WebUI không gọi AI đám mây (ENABLE_OPENAI_API=false)
PASS  CA riêng: thư mục 700, khóa 600, gốc + trung gian có ràng buộc tên critical (chỉ IP Box /32 + <mã>.onebee.internal)
PASS  CA riêng: Box tin CA của chính nó; chứng chỉ gốc công khai tại /onebee-ca.crt; khóa CA không gắn vào container nào
PASS  onebee-box in-ca in vân tay đúng chứng chỉ gốc
PASS  File .env chỉ root đọc (600)
PASS  Thư mục bí mật chỉ root vào (700)
PASS  Khóa bí mật đã sinh, không để trống
PASS  Samba đang chạy
PASS  Thư mục chung: đăng nhập bằng mật khẩu thấy share 'chung'
PASS  Thư mục chung: KHÔNG cho khách vào
PASS  Thư mục chung: ghi được file qua mạng
PASS  Lịch sao lưu Box đã bật
PASS  Có lệnh quản trị onebee-box
PASS  Bật cập nhật bảo mật tự động
PASS  Tường lửa bật: chỉ mạng LAN cho phép vào dịch vụ của Box (dịch vụ Docker + Samba/SSH)
PASS  Cổng dịch vụ chỉ mở IPv4 (cổng IPv6 của Docker đi vòng tường lửa)
PASS  Chưa có khóa SSH của quản trị → giữ đăng nhập mật khẩu + cảnh báo (không tự khóa mình ở ngoài)
PASS  Có khóa quản trị → SSH vào Box chỉ bằng khóa, không cho root; quản trị vào được bằng khóa
PASS  Tải model gemma4:e2b-it-qat vào Ollama
PASS  Đăng ký tự do đã tắt (người lạ nhận mã 403)
PASS  Tài khoản quản trị tạo sẵn đăng nhập được (mật khẩu trong in-khoa)
PASS  Có "Trợ lý OneBee" với lời dặn tiếng Việt
PASS  Trợ lý biết ngày hôm nay; tắt công cụ có sẵn (web trả lời giống lệnh hoi, không gọi nhầm "tạo lịch")
PASS  Hỏi đáp tiếng Việt qua Trợ lý OneBee → Ollama chạy tại chỗ
PASS  Hộp thư giả lập (Mailpit) sẵn sàng
PASS  Chủ n8n tạo sẵn đăng nhập được (không còn "ai mở trước thành chủ")
PASS  onebee-box email-thu → email tới hộp thư quản trị
PASS  Webhook sai khóa bị chặn (403), biểu mẫu đòi mật khẩu nhân viên (401)
PASS  Nhắc hạn thuế: ngày 17/10 → email "hạn 20/10, còn 3 ngày"
PASS  Nhập 2 đơn qua biểu mẫu → ghi vào thư mục chung (don-hang/don-hang-2026-10.csv)
PASS  Tổng hợp đơn trong ngày → email "2 đơn — 17.500.000 đồng"
PASS  Tóm tắt PDF bằng AI nội bộ qua biểu mẫu n8n
PASS  Trang tóm tắt PDF: hiển thị dạng chữ đã thoát HTML + CSP sandbox của n8n còn nguyên
PASS  Nhân viên báo cần hỗ trợ → ghi sổ (mã 261015-002532-68) + email GẤP cho kỹ thuật
PASS  Kỹ thuật ghi xử lý (tài khoản riêng, nhân viên không mở được); khảo sát ẩn danh ghi 3 phiếu
PASS  onebee-box bao-cao-tuan: đếm đúng yêu cầu/xử lý/khảo sát, không lộ tên người báo và nội dung
PASS  Biểu mẫu hỗ trợ chỉ nhận loại sự cố có sẵn (chữ tự gõ bị từ chối, không ghi sổ)
PASS  Máy chủ email hỏng → yêu cầu vẫn ghi sổ, người báo được dặn gọi điện
PASS  Dịch vụ ngừng (Ollama) → Uptime Kuma gửi email báo quản trị
PASS  Chưa tạo kho sao lưu thì sao-luu từ chối (không tự tạo kho)
PASS  Sao lưu/khôi phục Box
PASS  in-khoa in đủ khóa để cất ngoài Box
PASS  Cấp cho máy ketoan-01: sao lưu, khóa Trợ lý AI, báo tình trạng, khóa SSH quản trị (11 dòng cấu hình, gồm CA riêng của Box)
PASS  Cài OneBee OS Desktop trên máy trạm: tự bật lịch sao lưu, khóa quyền file cấu hình (600)
PASS  Máy trạm tin CA riêng của Box: vân tay khớp, đã vào kho hệ thống + chính sách Firefox + Chromium
PASS  Máy trạm sao lưu /home lên Box
PASS  Nhân viên trên máy trạm hỏi Trợ lý bằng lệnh hoi: Chào anh/chị, tôi hướng dẫn anh/chị cách lưu văn bản thành file PDF trên máy tín...
PASS  Khóa của máy trạm chỉ gọi được hỏi đáp (API khác bị chặn 403)
PASS  Máy trạm khôi phục đúng file đã xóa
PASS  Máy trạm KHÔNG xóa được bản sao lưu (chế độ chỉ-thêm, chống mã độc tống tiền)
PASS  Máy trạm: tài khoản quản trị của Box (ẩn, chỉ nhận khóa từ IP Box), SSH tắt đăng nhập mật khẩu và root, chỉ cho tài khoản quản trị
PASS  Menu máy trạm có "Báo cần hỗ trợ (OneBee)" mở đúng biểu mẫu trên Box
PASS  Máy trạm gửi tình trạng CÓ CHỮ KÝ → Box lưu (tên, IP, phiên bản, ổ trống, gói chờ cập nhật)
PASS  Khóa sai bị chặn (403); tên máy bậy (../) và máy CHƯA CẤP (kể cả có khóa chung) không ghi được file
PASS  Báo cáo giả (sai chữ ký) của máy đã cấp bị Box phát hiện và nêu trong bảng tình trạng
PASS  onebee-box may-tram: nêu đúng máy chưa sao lưu (kho-02), tóm tắt máy đang ổn
PASS  Máy trạm cần khởi động lại sau cập nhật → Box cảnh báo
PASS  Box cập nhật máy trạm qua SSH bằng 1 lệnh (87s); lần đầu máy chứng minh biết mật khẩu kho sao lưu rồi mới ghim khóa SSH
PASS  Lần 2: vào máy bằng khóa đã ghim (StrictHostKeyChecking=yes), không ghim lại
PASS  dong-bo-may: đẩy lại cấu hình xuống máy đã chứng minh, máy báo tình trạng thành công, nhật ký không chứa mật khẩu
PASS  Máy chưa báo tình trạng (chưa biết địa chỉ) → báo rõ, không treo
PASS  Lấy được khóa của Box cũng không vào được từ máy khác; SSH không nhận mật khẩu
PASS  thu-hoi-may: máy hết quyền vào kho HTTP, hết chỗ báo tình trạng, không còn trong danh sách cập nhật; cấp lại được
PASS  onebee-box sao-luu chạy chính sách giữ bản cho cả kho máy trạm
PASS  Sao lưu xong → email báo cáo tình trạng từng máy trạm, nêu máy cần xử lý (kho-02)
PASS  Box dọn được bản cũ trong kho máy trạm (máy trạm thì không)
PASS  Máy trạm trong mạng LAN vào được: trang giới thiệu, Trợ lý AI, giám sát, kho sao lưu, thư mục chung
PASS  Máy ngoài mạng cho phép (vd Wi-Fi khách) bị chặn hết: AI, trang giới thiệu, kho sao lưu, thư mục chung
PASS  Box tự gọi dịch vụ của mình không bị chặn; trả lại danh sách cũ → máy trạm vào lại được
PASS  Box tắt Trợ lý → hoi báo "Không kết nối được OneBee Box" (không treo, không lỗi khó hiểu)
PASS  Máy trạm vẫn sao lưu được sau khi Box dọn kho
PASS  (giả lập) Kẻ xấu tạo bản sao lưu mang ngày tương lai
PASS  Box phát hiện bản ngày tương lai, KHÔNG dọn kho đó (3 bản giữ nguyên)
PASS  (giả lập) Hỏng ổ Box: mất hết dữ liệu, khóa bí mật, cấu hình — còn bản in khóa và ổ sao lưu
PASS  Cài lại Box trên ổ mới (khóa bí mật mới, dữ liệu trống)
PASS  khoi-phuc-toan-bo bằng khóa in ra giấy: mật khẩu, tài khoản Trợ lý AI + n8n, sổ hỗ trợ trở lại như cũ
PASS  Máy trạm sau khôi phục Box: sao lưu, hỏi Trợ lý AI, báo tình trạng vẫn chạy — không phải cấu hình lại
PASS  Box khôi phục vẫn cập nhật được máy trạm (khóa SSH + khóa máy trạm đã ghi nhận được lấy lại)
PASS  Còn máy chưa nhận CA (kho-03) → bộ cài giữ HTTP, nêu tên máy, dịch vụ vẫn chạy
PASS  Chỉ Caddy công bố cổng (80, 443, 3000, 3001, 5678, 8000); 4 dịch vụ backend không còn cổng nào
PASS  TLS đúng ở mọi cổng khi nối bằng IP (không SNI), chuỗi tới CA riêng của Box
PASS  http://IP:3000 → 308 sang https; cổng 80 phục vụ chứng chỉ gốc
PASS  Cookie đăng nhập Open WebUI có Secure; Origin lạ không được CORS, Origin hợp lệ được CORS + WebSocket (101), Origin lạ bị từ chối WebSocket; biểu mẫu n8n vẫn có CSP sandbox
PASS  onebee-box dong-bo-tro-ly chạy được qua HTTPS (Box tin CA của chính nó)
PASS  Sau khi Box bật HTTPS, máy trạm nhận URL https + cờ BOX_HTTPS=1 + dấu bền (tự đồng bộ cuối bộ cài)
PASS  Máy trạm sao lưu (restic rest:https), hỏi Trợ lý AI và báo tình trạng qua HTTPS, chỉ tin CA riêng của Box
PASS  Firefox được đặt trang chủ + dấu trang https
PASS  Chạy lại bộ cài ở chế độ HTTPS: changed=0
PASS  Tắt HTTPS: dịch vụ chạy lại ở HTTP, dấu HTTPS bị xóa
PASS  Hoàn tác: máy trạm nhận cờ BOX_HTTPS=0, xóa dấu bền, sao lưu lại qua HTTP
PASS  xoay-khoa --may: mật khẩu kho HTTP cũ bị từ chối (401), mật khẩu mới dùng được, không lọt vào nhật ký
PASS  Khóa hoi cũ của máy hết hiệu lực
PASS  Máy trạm nhận mật khẩu + khóa mới qua dong-bo-may: sao lưu và hoi vẫn chạy
PASS  xoay-khoa --box: mật khẩu quản trị Trợ lý AI/chủ n8n/biểu mẫu mới dùng được, cũ bị từ chối; webhook n8n đồng bộ khóa mới
PASS  Chưa gắn ổ ngoài thì từ chối sao lưu, không ghi vào ổ hệ thống
PASS  Sau khởi động lại, dịch vụ tự chạy lại
```

## Phụ lục B — Desktop: 71 mục PASS (commit `119ec76`)
```text
PASS  Có file phiên bản /etc/onebee-release
PASS  Locale vi_VN.UTF-8 đã tạo
PASS  Ngôn ngữ mặc định là vi_VN.UTF-8
PASS  Múi giờ Asia/Ho_Chi_Minh
PASS  Đã cài gói language-pack-vi
PASS  Đã cài gói language-pack-gnome-vi
PASS  Đã cài gói firefox-locale-vi
PASS  Đã cài gói ibus
PASS  Đã cài gói ibus-bamboo
PASS  Đã cài gói fonts-liberation2
PASS  Đã cài gói fonts-crosextra-carlito
PASS  Đã cài gói fonts-crosextra-caladea
PASS  Đã cài gói fonts-noto-core
PASS  Đã cài gói libreoffice-writer
PASS  Đã cài gói libreoffice-calc
PASS  Đã cài gói libreoffice-impress
PASS  Đã cài gói libreoffice-l10n-vi
PASS  Đã cài gói hunspell-vi
PASS  IBus là bộ gõ mặc định (im-config)
PASS  Bộ gõ Bamboo được nạp sẵn trong IBus (gsettings org.freedesktop.ibus.general)
PASS  PPA ibus-bamboo chỉ cấp được gói ibus-bamboo (gói khác bị chặn)
PASS  Arial → Liberation Sans
PASS  Times New Roman → Liberation Serif
PASS  Calibri → Carlito
PASS  Cambria → Noto Serif (Caladea thiếu chữ tiếng Việt)
PASS  Font Noto có đủ dấu tiếng Việt (ạ ử ỗ)
PASS  Có file cấu hình định dạng mặc định LibreOffice
PASS  Có hình nền OneBee
PASS  Cinnamon dùng hình nền OneBee mặc định
PASS  Có file schema bố cục Windows (zz_onebee-windows-layout)
PASS  Nút cửa sổ: thu nhỏ, phóng to, đóng ở góc phải
PASS  Win+D hiện màn hình nền
PASS  Win+E mở thư mục cá nhân (Nemo)
PASS  Win+L khóa màn hình (vẫn giữ Ctrl+Alt+L)
PASS  Win+L không còn là phím bảng gỡ lỗi Looking Glass
PASS  Màn hình nền hiện biểu tượng computer
PASS  Màn hình nền hiện biểu tượng trash
PASS  Màn hình nền hiện biểu tượng home
PASS  Bảng điều khiển ở đáy màn hình, cao 40px
PASS  Menu bắt đầu có biểu tượng lưới ứng dụng (không còn logo Mint)
PASS  Menu bắt đầu ghim sẵn firefox
PASS  Menu bắt đầu ghim sẵn libreoffice-writer
PASS  Menu bắt đầu ghim sẵn libreoffice-calc
PASS  Menu bắt đầu ghim sẵn libreoffice-impress
PASS  Menu bắt đầu ghim sẵn nemo
PASS  Menu bắt đầu ghim sẵn onebee-tro-ly-ai
PASS  Menu bắt đầu ghim sẵn cinnamon-settings
PASS  Có lệnh mở Trợ lý AI + mục menu Trợ lý AI OneBee
PASS  Thanh tác vụ có file ghim sẵn ứng dụng (JSON hợp lệ)
PASS  Thanh tác vụ ghim sẵn nemo
PASS  Thanh tác vụ ghim sẵn firefox
PASS  Thanh tác vụ ghim sẵn libreoffice-writer
PASS  Thanh tác vụ ghim sẵn libreoffice-calc
PASS  Thanh tác vụ ghim sẵn libreoffice-impress
PASS  Thanh tác vụ ghim sẵn onebee-tro-ly-ai
PASS  Phím Super mở menu bắt đầu (applet menu mặc định)
PASS  LibreOffice mở mặc định giao diện Ribbon (tab) cho Writer, Calc, Impress
PASS  Bật tự động nâng cấp mintupdate
PASS  Bật tự động dọn gói thừa mintupdate
PASS  Có lệnh sao lưu onebee-sao-luu + restic
PASS  Thư mục cấu hình /etc/onebee chỉ root vào (700)
PASS  Có lệnh hỏi Trợ lý AI (hoi)
PASS  Có lệnh báo tình trạng về Box
PASS  Có hỗ trợ từ xa (onebee-ho-tro + x11vnc + mục menu)
PASS  LibreOffice TextDocument lưu mặc định: MS Word 2007 XML
PASS  LibreOffice SpreadsheetDocument lưu mặc định: Calc MS Excel 2007 XML
PASS  LibreOffice PresentationDocument lưu mặc định: Impress MS PowerPoint 2007 XML
PASS  LibreOffice Writer mở mặc định giao diện Ribbon (Tabbed): Tabbed
PASS  LibreOffice Calc mở mặc định giao diện Ribbon (Tabbed): Tabbed
PASS  LibreOffice Impress mở mặc định giao diện Ribbon (Tabbed): Tabbed
PASS  LibreOffice tắt cảnh báo khi lưu định dạng Microsoft
```
