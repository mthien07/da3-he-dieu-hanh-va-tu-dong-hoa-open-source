# Nhật ký thay đổi

## [1.2.0] — 14/11/2026 — Trải nghiệm người dùng: Trung tâm OneBee, tự phục vụ, Trợ lý AI dùng được ngay
Đã chạy phiếu kiểm trải nghiệm tự động trên máy ảo Linux Mint 22.3 kèm một Box thử (`reports/trai-nghiem/261113-may-ao-vmware-mint-22-3.md`): các mục không đạt đã sửa hoặc ghi là giới hạn đã biết. Chưa có người xác nhận lại các mục về cảm nhận và chưa thử trên máy thật hay từ điện thoại.
Bản 1.1.0 trên GitHub không có file tải (phiên bản trong bộ cài chưa được nâng). Bản 1.2.0 là bản có file tải kế tiếp.
### Sửa
- Bộ cài Desktop và Box ghi đúng phiên bản; thêm test chặn việc phát hành khi phiên bản trong mã thấp hơn tag.
- Trợ lý tập tin Windows: nút nào cũng mở được ứng dụng hoặc nói rõ vì sao chưa mở được; không còn nhận chương trình Linux là
  "phần mềm Windows"; lời gợi ý chỉ nêu ứng dụng thật sự có trên máy.
- Trang chủ Box, tờ phím tắt, sổ tay A4, giáo án và kịch bản video dùng cùng một phím khóa màn hình (Super + L) và cùng tên gọi
  như trên máy ("Trợ lý AI OneBee", "Chia sẻ nội bộ (OneBee Box)", "Cho phép hỗ trợ từ xa (OneBee)").
- Máy trạm (Mint 22.3): chỉ bật `mintupdate-automation-autoremove.timer` khi file timer tồn tại trên máy, tránh lỗi bộ cài trên bản mintupdate mới đã bỏ timer này.
- Trợ lý AI trên Box: 4 mẫu soạn văn bản (`/to-trinh`, `/bien-ban`, `/hop-dong`, `/bao-cao`) được tạo đúng theo API Open WebUI v0.11.4,
  mọi nhân viên đều thấy và chạy lại không đổi; bộ cài thôi tự tạo bộ tri thức rỗng, lệnh `onebee-box dong-bo-tri-thuc` không tạo trùng.
- Bộ cài Desktop, bộ cài Box (cả đường cài từ USB) và `onebee-box cap-nhat-may` / `dong-bo-may` chạy Ansible bằng `LC_ALL=C.UTF-8`:
  Mint cài bằng tiếng Việt đặt `LANG=vi_VN` làm bộ cài dừng ngay với "Ansible requires the locale encoding to be UTF-8; Detected TCVN".
  Test `tests/desktop/test_onebee_locale_ansible.py`; lần cài đầu trong test container Desktop và Box chạy với `LANG=vi_VN`.
- Trang chủ Box ghi cách xuất PDF đúng chữ LibreOffice hiện trên màn hình: nút PDF (chữ gợi ý `Export Directly as PDF`) hoặc
  menu "Tập tin → Export As → Xuất dạng PDF...". Lời dặn của Trợ lý (`tro-ly-onebee-loi-dan.md`) vẫn ghi cách cũ: sửa lời dặn
  phải chấm lại chất lượng Trợ lý bằng Ollama, chưa làm.
### Thêm
- Trợ lý AI trên Box: bản dịch tiếng Việt bổ sung (`box-ai/files/giao-dien-tieng-viet.json`) cho chữ tiếng Anh còn sót ở trang đăng nhập,
  khi hỏi, thanh bên và trang Cài đặt → Tài khoản; gửi qua trường `I18N` của cài đặt quản trị Open WebUI, giữ bản dịch quản trị tự thêm,
  chạy lại không đổi. Tên "Open WebUI" và "Gravatar" giữ nguyên.
- `desktop/ansible/roles/theme/files/onebee-cam-nang.json`: một nguồn cho phím tắt và tên gọi; test
  `tests/desktop/test_onebee_cam_nang.py` báo lỗi khi cấu hình máy hoặc tài liệu lệch nguồn này.
- `tests/desktop/check-exe-handler.sh` được chạy trong CI.
- Máy trạm (Cinnamon 6.6 / Mint 22.3): nạp sẵn bộ gõ tiếng Việt (mặc định tiếng Việt trước, `Super + Space` sang tiếng Anh) ở cả khóa `sources` của `org.cinnamon.desktop.input-sources` và `preload-engines` của IBus.
- Nút **Bắt đầu** trên máy có `mint-artwork`: gộp `menu-settings-override.json` (`menu-custom=true`, biểu tượng `onebee-logo`, nhãn `Bắt đầu`) vào mặc định của applet menu sau khi chuyển hướng file gốc bằng `dpkg-divert`.
- Tắt cửa sổ chào (`mintwelcome`) và báo cáo hệ thống (`mintreport`) lúc đăng nhập bằng `dpkg-divert --local --rename` (bền qua cập nhật gói); trình quản lý cập nhật (`com.linuxmint.updates`) không tự bật cửa sổ hay thông báo cho nhân viên.
- Đồng hồ thanh tác vụ Cinnamon hiển thị giờ và ngày/tháng/năm kiểu Việt Nam (`%H:%M  %d/%m/%Y`) qua `calendar-settings-override.json`.
- Màn hình đăng nhập LightDM (`slick-greeter.conf`) dùng hình nền OneBee (`force: false`, giữ nguyên nếu quản trị đã tự chỉnh).
- **Trung tâm OneBee** (`onebee-trung-tam`, role `trung-tam`): tự mở ở lần đăng nhập đầu của mỗi người và ghim đầu menu Bắt đầu; gồm trang Bắt đầu (6 ô lớn dẫn tới Soạn văn bản, Bảng tính, Thư mục của tôi, Thư mục chung, Trợ lý AI, Cần giúp đỡ), trang Phím tắt (đọc từ `onebee-cam-nang.json`) và trang Cần giúp đỡ.
- Biến `onebee_dien_thoai_ho_tro` trong `desktop/ansible/group_vars/all.yml`: số điện thoại hỗ trợ khẩn cấp hiển thị ở trang Cần giúp đỡ của Trung tâm OneBee (để trống thì ẩn).
- Trang **Kiểm tra máy** trong Trung tâm OneBee: bấm "Kiểm tra ngay" để thấy từng mục đạt hay lỗi kèm gợi ý tiếng Việt, rồi gửi yêu cầu hỗ trợ kèm kết quả, không cần mở Terminal. `onebee-chan-doan` có thêm `--json` (đầu ra chữ giữ nguyên).
- "Báo cần hỗ trợ (OneBee)" mở biểu mẫu đã điền sẵn tên máy qua lệnh mới `onebee-bao-ho-tro` (địa chỉ biểu mẫu nằm trong `/etc/onebee-ho-tro.conf`); với file Windows lạ, trợ lý tập tin điền sẵn thêm loại "Phần mềm chỉ chạy trên Windows" và tên file. Box đời cũ đẩy lại mục menu kiểu cũ vẫn dùng được, chỉ mất phần điền sẵn, hết khi Box được cài bản mới.
- Nhắc sao lưu trễ: máy đã nối Box mà quá 72 giờ chưa sao lưu thì người đang đăng nhập nhận một thông báo (tối đa một lần mỗi ngày), qua dịch vụ systemd mức người dùng `onebee-nhac-sao-luu`.
- Ngưỡng báo sao lưu trễ của `onebee-chan-doan` trên máy trạm đổi từ 26 giờ sang 72 giờ cho khớp Box (máy tắt cuối tuần không bị báo nhầm).
- Trợ lý AI trên Box: 4 gợi ý tiếng Việt bấm được trên màn hình trò chuyện mới (chèn câu mở đầu vào ô nhập để người dùng viết tiếp)
  và dòng nhắc "Trợ lý AI có thể sai" trên giao diện web.
- Trang chủ Box: cẩm nang phím tắt lấy từ `onebee-cam-nang.json`, cùng nguồn với máy văn phòng; không còn hướng dẫn mở Terminal.
- Trang chủ Box: mục "Soạn văn bản bằng Trợ lý AI" có 4 thẻ mở thẳng Trợ lý với câu mở đầu điền sẵn (từ `goi-y.json`), người dùng viết tiếp rồi tự bấm gửi.
- Trang chủ Box: ô "Máy trạm đã sao lưu" cho quản lý biết bao nhiêu máy đã sao lưu trong 3 ngày; chỉ hiện hai con số, không có tên máy,
  cập nhật sau lần sao lưu đêm.

## [1.1.0] — 22/10/2026 — Năm tính năng mới và bộ cài USB offline
Phiên bản 1.0.0 chuyển hóa OneBee OS (DA3) thành sản phẩm thương mại hoàn chỉnh, hấp thụ tinh hoa kiến trúc từ các dự án mã nguồn mở hàng đầu thế giới (CasaOS, YunoHost, Zorin OS, Nextcloud, Synology/TrueNAS).

### Tính năng Nổi bật Vượt trội (5 Trụ cột Tinh hoa Nguồn mở):
1. **Zero-Config LAN Discovery & Web Dashboard (CasaOS/Umbrel):**
   - Hỗ trợ tên miền nội bộ `http://onebee.local` qua mDNS/Avahi tự động nhận diện trong mạng LAN.
   - Trang chủ Dashboard cổng 80 trực quan hiển thị trạng thái hệ thống, tài nguyên và lối tắt dịch vụ.
2. **OneBee Diagnosis — Bộ Tự Chẩn Đoán Lỗi 7 Hạng Mục (YunoHost):**
   - Lệnh `sudo onebee-box chan-doan [--json]` quét toàn diện: Mạng, Tài nguyên, Docker, AI, Samba, Sao lưu, Chứng chỉ SSL.
   - Công cụ máy trạm `onebee-chan-doan` cho nhân viên tự kiểm tra kết nối không cần quyền root.
3. **Windows App Helper & `.exe` Interceptor (Zorin OS):**
   - Tự động bắt sự kiện mở file cài đặt Windows (`.exe`, `.msi`) trên máy trạm Mint.
   - Hộp thoại Zenity tiếng Việt gợi ý ứng dụng Linux tương đương (Zalo Web/Native, Chromium, IBus Bamboo, Foxit/Evince, VLC, Hỗ trợ từ xa OneBee).
4. **Kho Mẫu Prompt Hành chính NĐ 30 & Bộ Tri thức RAG Open WebUI (Nextcloud/Dify):**
   - 4 mẫu prompt chuẩn: `/to-trinh` (Nghị định 30/2020/NĐ-CP), `/bien-ban` (Họp HTX), `/hop-dong` (Bao tiêu nông sản Luật HTX 2023), `/bao-cao` (Tài chính & quỹ chung không chia).
   - Danh mục tri thức `Thư viện Pháp lý HTX`: mới có khung, **chưa nạp tài liệu** (xem 1.2.0).
5. **Cảnh báo Sự cố Chủ động qua Telegram & n8n (Synology/TrueNAS):**
   - Gửi cảnh báo tức thời vào điện thoại quản trị viên (`ℹ️ INFO`, `⚠️ WARN`, `🚨 CRIT`) khi sao lưu hoàn tất, ổ đĩa đầy hoặc dịch vụ dừng.
   - Lệnh quản trị `sudo onebee-box dat-telegram` và `sudo onebee-box canh-bao`.
   - Workflow n8n `10-canh-bao-su-co` mở rộng kết nối Zalo OA và Email.

### Bộ Đóng Gói Offline & Tài liệu Thương mại Hóa:
- **Bộ cài Offline 1-Click từ USB:** `scripts/dong-goi-usb-offline.sh` và `scripts/cai-tu-usb-offline.sh` giúp lắp đặt tại vùng sâu vùng xa không cần Internet.
- **Sổ tay hướng dẫn nhanh 1 trang A4:** `docs/thuong-mai/huong-dan-nhanh-a4-can-bo-htx.md` tóm tắt cách dùng cho xã viên.
- **Biên bản nghiệm thu bàn giao:** `docs/thuong-mai/bien-ban-nghiem-thu-ban-giao.md` mẫu pháp lý chuẩn cho HTX.
- **Quy trình thao tác chuẩn (SOP):** `docs/thuong-mai/sop-quy-trinh-trien-khai-thuc-dia.md` hướng dẫn triển khai thực địa từ A-Z.

---
- **`sudo onebee-box chan-doan [--json]`**: 1 lệnh kiểm 7 hạng mục — mạng (router, Internet qua 1.1.1.1/8.8.8.8, Tailscale), tài nguyên (ổ `/` + dữ liệu,
  RAM trống, tải CPU), 6 container (chạy + healthcheck), Trợ lý AI (prompt thử tới Ollama cổng 11434 trong mạng Docker, đo thời gian),
  Samba (smbd + tài khoản thư mục chung ghi được), bản sao lưu Box mới nhất (đọc kho restic, không khóa kho), CA gốc/trung gian và chứng chỉ HTTPS
  đang phục vụ. Bảng màu [OK]/[CẢNH BÁO]/[LỖI] kèm gợi ý tiếng Việt, kết luận chung; `--json` cho n8n/trang chủ. Mã thoát 0/1/2. Chỉ đọc.
- **`onebee-chan-doan`** trên máy trạm (nhân viên chạy không cần sudo): router, Box, cổng dịch vụ trên Box, sao lưu của máy, ổ `/home`.
- Test: `tests/box/check-diagnosis.sh`, `tests/desktop/check-chan-doan-may-tram.sh` (chạy trong CI).

### Thêm
- `scripts/mo-truy-cap-tu-xa.sh` (`--tat` để tắt): cầu nối **tạm** để kỹ thuật vào cài tiếp một máy mới cài hệ điều hành ở nơi khác mạng —
  Tailscale SSH và chia sẻ màn hình GNOME (RDP, mật khẩu ngẫu nhiên chỉ root đọc). Chỉ Ubuntu 24.04 / Mint 22 (nền noble), amd64.
  Không thay `onebee-ho-tro` (ADR 0004); tắt khi bàn giao máy.
- Hướng dẫn `docs/huong-dan/truy-cap-tu-xa-khi-cai-may.md`, nối từ `quan-ly-may-tram.md`, `huong-dan-cai-dat-tu-a-den-z.md` và README.
- Giao diện quen như Windows (máy trạm Cinnamon): nút **Bắt đầu** dùng logo OneBee (`onebee-logo`, SVG + PNG 48px); Trợ lý AI dùng logo;
  bộ biểu tượng thư mục vàng Mint-Y-Sand; phím **Win+R** (Chạy lệnh), **Win+Shift+S** (chụp vùng vào clipboard, dán bằng Ctrl+V), **Ctrl+Shift+Esc** (Quản lý tác vụ, qua dconf
  hệ thống); Nemo ẩn file ẩn, nhấp đúp; thanh tác vụ xem trước cửa sổ khi rê chuột; lối tắt **Chia sẻ nội bộ (OneBee Box)** trên màn hình nền
  (`smb://<IP Box>/chung`, đặt lúc đăng nhập); LibreOffice bộ biểu tượng **Colibre** (kiểu giống Microsoft Office).
- Phiếu `docs/kiem-thu-tren-may-that.md` mục E2 kiểm cầu nối trên máy thật. Test tự động `tests/desktop/test_mo_truy_cap_tu_xa.py` dùng lệnh giả;
  **chưa chạy trên máy thật**.

## [1.0.0] — 15/10/2026 — Bản phát hành chính thức đầu tiên
Bản đủ tính năng cho một đơn vị, gồm mọi thay đổi từ 1.0.0-rc.1 (các mục dưới đây). Đã nghiệm thu tự động trong container
(`reports/nghiem-thu-v1-docker.md`); **chưa cài trên máy thật tại đơn vị nào** — phiếu `docs/kiem-thu-tren-may-that.md` nhóm B–E còn mở,
chưa có số đo tốc độ AI trên máy thật.
### Tính năng chính
- **OneBee OS Desktop** (Linux Mint 22.x): gõ Telex (IBus + Bamboo), LibreOffice lưu mặc định .docx/.xlsx/.pptx, font thay thế, tự cập nhật,
  tự sao lưu lên Box, lệnh `hoi` hỏi Trợ lý AI, báo tình trạng máy, báo cần hỗ trợ, hỗ trợ từ xa có đồng ý.
- **OneBee Box** (Ubuntu Server 24.04): Trợ lý AI chạy tại chỗ (Ollama + Open WebUI, `gemma4:e2b-it-qat`), n8n gửi email (báo cáo sao lưu, nhắc hạn,
  đơn hàng, tóm tắt PDF, sổ hỗ trợ), giám sát Uptime Kuma, thư mục chung Samba (SMB 3.1.1 bắt buộc mã hóa), sao lưu 2 tầng bằng restic
  (rest-server chỉ-thêm → ổ ngoài) và khôi phục toàn bộ khi hỏng ổ, tường lửa chỉ mở cho LAN.
- **Quản lý tập trung**: `onebee-box them-may`, `may-tram`, `cap-nhat-may`, `dong-bo-may`, `xoay-khoa`, `bao-cao-tuan`; HTTPS nội bộ bằng CA riêng
  có ràng buộc tên (tùy chọn `onebee_box_https`).
### Giao diện quen thuộc như Windows (Desktop)
- Nút thu nhỏ/phóng to/đóng bên phải; Win+E mở thư mục cá nhân, Win+D hiện màn hình nền, Win+L khóa màn hình (Super+L không còn mở bảng gỡ lỗi
  Looking Glass, kỹ thuật mở bằng Alt+F2 → `lg`); màn hình nền có Máy tính, Thùng rác, Thư mục cá nhân.
- Ghim sẵn Nemo, Firefox, Writer, Calc, Impress, **Trợ lý AI OneBee** (mở giao diện web của Trợ lý trên Box) ở thanh tác vụ và menu bắt đầu.
- LibreOffice mở mặc định giao diện dạng tab (Ribbon) cho Writer, Calc, Impress; vẫn lưu mặc định .docx/.xlsx/.pptx.
- Đều là giá trị mặc định: tài khoản đã tự đổi trước khi cài giữ lựa chọn cũ. Đã kiểm giá trị cấu hình trong container Mint 22.3 có gói
  `cinnamon-common` + `nemo-data` thật; **chưa kiểm trong phiên Cinnamon thật** (hiển thị nút menu, ghim thanh tác vụ, Ribbon, bấm phím thật).
### Sửa lũy nghiệm bộ cài
- Bước "Cập nhật danh mục gói" (Box và Desktop) không còn báo `changed` khi danh mục cũ hơn 1 giờ — lần cài đầu kéo dài hơn 1 giờ (tải image chậm)
  từng làm lần chạy lại báo `changed=1`. Làm mới danh mục không đổi trạng thái hệ thống.
### Sửa lỗi tìm được khi kiểm thử Docker và rà soát mã (14/10/2026, chi tiết: `docs/kiem-thu-tren-may-that.md` mục "Đợt sửa 14/10/2026")
- **Open WebUI chế độ HTTP chặn Origin lạ:** `CORS_ALLOW_ORIGIN` = IP Box + `box.<mã>.onebee.internal` (cổng 3000) cả khi chưa bật HTTPS — trước đây phản chiếu mọi Origin
  kèm `allow-credentials`. Test `check-https.sh` không còn đạt giả khi curl lỗi. Danh sách này áp cho cả kết nối thời gian thực (WebSocket) của chat:
  mở Trợ lý bằng địa chỉ khác (tên do router cấp, IP Tailscale, `localhost` qua đường hầm SSH) phải khai thêm vào biến mới `onebee_box_cors_them`
  (xem `docs/huong-dan/cai-dat-onebee-box.md`); test kiểm cả chiều Origin hợp lệ được nhận.
- **Tường lửa:** kết nối mới qua Tailscale bị lọc ở bảng `mangle`, đúng cả khi tailscaled khởi động lại sau tường lửa (trước đây máy tailnet bất kỳ có thể vào Box);
  IPv6 ngoài mạng nội bộ tới SSH/Samba bị từ chối ngay thay vì im lặng, để máy khách lùi về IPv4 thay vì chờ hết giờ (chưa kiểm trên Windows thật — phiếu B15).
  Quy tắc `mangle` dựng sau cùng: máy thiếu mô-đun `mangle` thì bộ cài báo lỗi nhưng mạng nội bộ vẫn được lọc, không mở toang SSH/Samba.
  Dịch vụ `onebee-tuong-lua` dựng **trước** Docker và không còn gắn vòng đời với Docker: trước đây dừng/nâng cấp Docker gỡ luôn quy tắc SSH/Samba/Tailscale
  tới khi Docker chạy lại. Docker dùng lại chuỗi `DOCKER-USER` có sẵn và giữ quy tắc trong đó nên container lên là đã bị lọc.
- **Gia hạn CA trung gian** chạy mỗi đêm cả khi chưa gắn ổ sao lưu.
- **`xoay-khoa`:** `--box` tự đẩy khóa tình trạng mới xuống mọi máy; máy đang tắt, máy thiếu bí mật hoặc máy bị lỗi khi đẩy cấu hình đều được nhắc
  đúng lý do kèm lệnh `dong-bo-may <máy>` (không dừng giữa chừng); không chạy chồng với sao lưu, và chỉ giữ khóa sau bước xác nhận (để treo ở dấu nhắc
  không chặn sao lưu đêm).
- **`hoi` và báo tình trạng:** không tự theo chuyển hướng 308 bằng CA công cộng — vẫn chỉ tin CA của Box, kể cả khi địa chỉ viết hoa `HTTPS://`
  (trước đây địa chỉ viết hoa dùng kho CA của hệ điều hành).
- **Máy trạm — xoay CA:** gỡ CA OneBee cũ khỏi hồ sơ Firefox theo vân tay CA hiện tại mỗi lần chạy (tự lành nếu lần trước gỡ hụt); không đụng CA khác.
  Firefox đang mở lúc xoay CA chỉ thôi tin CA cũ sau khi khởi động lại.
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
### Bảo mật — Pha 5 (xem `docs/security-audit.md`)
- **Tường lửa Box lọc mọi cổng mạng** trừ `lo` và mạng Docker (trước đây chỉ cổng mạng chính): card phụ, `wg0`, `tun0` bị chặn; qua Tailscale chỉ máy kỹ thuật khai trong `onebee_box_tailscale_cho_phep`.
  **Box đang nối Tailscale phải khai biến này, nếu không kỹ thuật mất đường vào Box** (bộ cài cảnh báo). Thay đổi hành vi so với bản cũ ("VPN không bị chặn").
- **Thư mục chung Samba: chỉ SMB 3.1.1 + bắt buộc mã hóa** (Windows 10+, Linux; máy cũ/máy quét cũ không nối được — `onebee_box_samba_smb3: false` để tắt).
- Container: `no-new-privileges` cho mọi dịch vụ; rest-server `cap_drop ALL` + `read_only`. CSV/email: mọi ký tự điều khiển bị thay (kể cả `\r`), quy trình 04 dùng chung mã CSV.
- Chuỗi cung ứng: GitHub Actions ghim SHA; `renovate.json`. Nhật ký quản lý máy trạm giữ 90 ngày (logrotate). `onebee-box gia-han-ca`; xoay CA qua `onebee_box_xoay_ca`.
- Sửa sau rà soát Pha 3–4: `onebee-kiem-ca.py` đọc ràng buộc tên NGHIÊM (chứng chỉ giả dòng `Excluded:` trong tên DNS để giấu `DNS:com` bị từ chối; chính sách Chrome dùng cùng bộ đọc);
  gia hạn CA trung gian chép tới Caddy + khởi động lại; dấu `https-da-bat` ghi SAU khi dịch vụ chuyển xong; khôi phục xóa chứng chỉ lá Caddy; `onebee_box_address` cũ báo lỗi rõ;
  `dong-bo-may` trả lại cấu hình cũ khi CA mới không đạt; `hoi`/báo tình trạng theo 308 một lần tới https cùng máy chủ; `onebee-sao-luu` không bỏ dòng cuối/dấu `=` cuối.
### Bảo mật — Pha 4b/4c (xem `docs/security-audit.md`, F2/F10)
- **`onebee-box xoay-khoa [--may <tên>|--tat-ca] [--box]`**: đổi mật khẩu kho HTTP + khóa `hoi` theo máy rồi `dong-bo-may`; `--box` đổi mật khẩu quản trị Trợ lý AI/giám sát (trong dịch vụ),
  chủ n8n, biểu mẫu, khóa webhook, `WEBUI_SECRET_KEY` rồi chạy lại bộ cài. Không xoay `RESTIC_PASSWORD`/`N8N_ENCRYPTION_KEY`. `onebee-webui.py`: `xoay-khoa`, `doi-mat-khau-quan-tri`; `onebee-kuma.js`: `KUMA_PASS_MOI`.
- **`hoi` theo từng nhân viên**: `hoi --dang-nhap` (email + mật khẩu → chỉ lưu khóa `~/.config/onebee/hoi-khoa` 0600, từ chối khi URL còn http://), `hoi --dan-khoa` (kiểm khóa trước khi lưu),
  `hoi --dang-xuat`. Khóa máy chỉ còn là chuyển tiếp (nhắc dùng khóa riêng); `onebee_box_hoi_khoa_may: false` + `onebee-box go-khoa-hoi-may` bỏ hẳn khóa máy và đóng F10.
- `onebee_box_khoa_tinh_trang_chung: false`: bỏ khóa gửi tình trạng dùng chung (n8n không đòi, Box không đẩy `TINH_TRANG_KEY`; client coi khóa là tùy chọn). Mặc định `true` (chuyển tiếp).
- Sửa: `secret()` có thể trả mã 141 (SIGPIPE) khi sinh mật khẩu lần đầu dưới `pipefail` → nguồn ngẫu nhiên hữu hạn.
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
