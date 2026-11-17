<p align="center">
  <img src="https://img.shields.io/badge/🐝_HTX_OneBee-Open_Source_OS-e85d04?style=for-the-badge&labelColor=0a1628" alt="OneBee Open Source"/>
</p>

<h1 align="center">🐧 Hệ điều hành & Tự động hóa Open Source</h1>

<p align="center">
  <strong>OneBee OS — máy văn phòng Linux tiếng Việt + máy chủ nội bộ có AI chạy tại chỗ, cho HTX và doanh nghiệp nhỏ</strong>
</p>

<p align="center">
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/actions/workflows/ci.yml"><img src="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/releases"><img src="https://img.shields.io/github/v/release/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source?include_prereleases&style=flat-square&label=Ph%C3%A1t%20h%C3%A0nh&color=00d4aa" alt="Phát hành"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License MIT"/></a>
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/commits"><img src="https://img.shields.io/github/last-commit/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source?style=flat-square&label=C%E1%BA%ADp%20nh%E1%BA%ADt" alt="Cập nhật"/></a>
  <img src="https://img.shields.io/badge/AI-ch%E1%BA%A1y%20t%E1%BA%A1i%20ch%E1%BB%97%20(Gemma%204)-8a2be2?style=flat-square" alt="AI chạy tại chỗ"/>
  <img src="https://img.shields.io/badge/H%E1%BB%99i_thi-KN%C4%90MST_2026-f4b942?style=flat-square" alt="Hội thi"/>
</p>

<p align="center">
  <a href="docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md"><b>📖 Cài từ A đến Z</b></a> ·
  <a href="#-tài-liệu">Tài liệu</a> ·
  <a href="tests/README.md">Kiểm thử</a> ·
  <a href="plans/reports/261010-kiem-thu-tren-may-that.md">Kết quả kiểm thử</a> ·
  <a href="SECURITY.md">Bảo mật</a> ·
  <a href="CONTRIBUTING.md">Đóng góp</a>
</p>

---

## 🎯 Vấn đề
- Máy văn phòng ở HTX, hộ kinh doanh, doanh nghiệp nhỏ thường dùng phần mềm không bản quyền → rủi ro pháp lý, dễ nhiễm mã độc.
- Không có người chuyên CNTT: không ai sao lưu, cập nhật, không ai hỗ trợ khi máy hỏng.
- Muốn dùng AI nhưng ngại đưa dữ liệu nội bộ lên dịch vụ nước ngoài.

## 💡 Sản phẩm
| Thành phần | Làm gì |
|---|---|
| **OneBee OS Desktop** | Bộ cài biến Linux Mint 22 thành máy văn phòng tiếng Việt: gõ Telex (IBus + Bamboo), LibreOffice lưu mặc định .docx/.xlsx, font thay thế giữ bố cục file Word, tự cập nhật, tự sao lưu lên Box, lệnh `hoi` hỏi Trợ lý AI, báo cần hỗ trợ, hỗ trợ từ xa có đồng ý |
| **OneBee Box** | Bộ cài máy chủ nội bộ (Ubuntu Server 24.04) theo kiến trúc **DX-OS Open-Core**: đăng nhập một lần (Authelia), cơ sở dữ liệu PostgreSQL có API tự sinh và phân quyền tới từng dòng, kho tệp có kiểm dịch mã độc, động cơ quy trình Node-RED (duyệt đơn, email báo cáo, nhắc hạn thuế/BHXH), Trợ lý AI tiếng Việt chạy tại chỗ (Gemma 4 qua Ollama), ứng dụng **Sổ điều hành** H-P-D-I kèm **sổ kho và sổ kế toán nhật ký kép** (duyệt đơn tự xuất kho và sinh bút toán, xuất CSV), thư mục chung, sao lưu 2 tầng chống mã độc tống tiền, quản lý và cập nhật máy trạm từ 1 lệnh |
| **Dịch vụ** | Khảo sát → sao lưu nguyên ổ Windows → cài → đào tạo 3 buổi → bảo trì (theo dõi báo cáo hằng ngày, xử lý yêu cầu hỗ trợ có đo thời gian) |

```
 Máy trạm (Linux Mint + OneBee OS)                 OneBee Box (Ubuntu Server 24.04, trong LAN)
 ├─ gõ tiếng Việt, LibreOffice          sao lưu    ├─ Caddy (HTTPS) → Authelia (đăng nhập một lần) → API, kho tệp, AI, Sổ điều hành
 ├─ onebee-sao-luu (12:00)         ───────────────▶├─ restic rest-server (chỉ-thêm) → ổ ngoài 23:00
 ├─ onebee-bao-tinh-trang (mỗi giờ) ──────────────▶├─ PostgreSQL + Node-RED: đơn hàng, hỗ trợ, khảo sát, email báo cáo, nhắc hạn
 ├─ hoi "câu hỏi"                   ──────────────▶├─ Ollama (Gemma 4) — không gửi dữ liệu ra ngoài · Samba: thư mục chung
 └─ onebee-ho-tro (khi người dùng bấm)◀──SSH────── └─ onebee-box: them-may, may-tram, cap-nhat-may, bao-cao-tuan …
```

<table>
  <tr>
    <td width="50%"><img src="docs/huong-dan/anh/01-trang-gioi-thieu-box.png" alt="Trang giới thiệu OneBee Box"/><br/><sub>Trang giới thiệu của OneBee Box trong mạng LAN</sub></td>
    <td width="50%"><img src="docs/huong-dan/anh/02-tro-ly-ai-tieng-viet.png" alt="Trợ lý OneBee soạn thông báo tiếng Việt"/><br/><sub>Trợ lý AI tiếng Việt chạy tại chỗ soạn thông báo họp HTX</sub></td>
  </tr>
</table>

<sub>Ảnh chụp từ Box chạy trong môi trường kiểm thử, không phải tại đơn vị thật.</sub>

## 🏛️ Kiến trúc DX-OS Open-Core
OneBee Box được dựng theo Khung kiến trúc Hệ điều hành Chuyển đổi số (DX-OS) của Đề thi OLP 2026:
- **Tầng Nền tảng Dịch vụ Lõi số** (chạy ngầm, không giao diện người dùng cuối): Caddy, Authelia, PostgreSQL + PostgREST, SeaweedFS + ClamAV, Node-RED, Ollama + dịch vụ RAG, restic.
- **Tầng Không gian Năng lực số**: ứng dụng Sổ điều hành đi trọn bốn không gian H-P-D-I (gửi đơn kèm tệp, duyệt, bảng điều hành, hỏi Trợ lý AI), chỉ gọi API của tầng dưới.
- **Tầng Nền tảng Kinh doanh số**: định hướng, chưa có ứng dụng cắm-rút.

Chi tiết, bốn nguyên lý thiết kế và phần chưa làm: [docs/kien-truc-dx-os.md](docs/kien-truc-dx-os.md) · Lộ trình: [ROADMAP.md](ROADMAP.md).

## 🚀 Cài đặt
> **Người không chuyên**: làm theo [Hướng dẫn cài từ A đến Z](docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md) — có sơ đồ, từng lệnh dán được, kết quả phải thấy.

Bản phát hành (file nén + SHA256SUMS): [Releases](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/releases).
Tự thử trên máy ảo trước khi cài cho đơn vị: [thu-nghiem-tren-may-ao.md](docs/huong-dan/thu-nghiem-tren-may-ao.md).

**Máy trạm** — Linux Mint 22.x 64-bit, có Internet:
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee && sudo ./desktop/onebee-install.sh
```
**Box** — Ubuntu Server 24.04 LTS 64-bit trong LAN: như trên, lệnh cuối là `sudo ./box/onebee-box-install.sh`.

## 📚 Tài liệu
| Việc | Tài liệu |
|---|---|
| **Cài từ A đến Z cho người không chuyên** | [huong-dan-cai-dat-tu-a-den-z.md](docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md) |
| Cài máy trạm / Box | [cai-dat-onebee-os-desktop.md](docs/huong-dan/cai-dat-onebee-os-desktop.md) · [cai-dat-onebee-box.md](docs/huong-dan/cai-dat-onebee-box.md) |
| Cài nhiều máy, sao lưu Windows bằng Clonezilla | [cai-hang-loat.md](docs/huong-dan/cai-hang-loat.md) |
| Trợ lý AI, quy trình tự động, email | [dung-tro-ly-ai-va-quy-trinh-tu-dong.md](docs/huong-dan/dung-tro-ly-ai-va-quy-trinh-tu-dong.md) |
| Quản lý, cập nhật máy trạm, hỗ trợ từ xa | [quan-ly-may-tram.md](docs/huong-dan/quan-ly-may-tram.md) |
| Vào máy từ xa để cài tiếp (máy mới cài hệ điều hành, ở nơi khác) | [truy-cap-tu-xa-khi-cai-may.md](docs/huong-dan/truy-cap-tu-xa-khi-cai-may.md) |
| Kiểm trải nghiệm trên máy thật (phiên Cinnamon, Trợ lý AI, trang chủ Box) | [kiem-thu-trai-nghiem-may-that.md](docs/kiem-thu-trai-nghiem-may-that.md) · kết quả: [reports/trai-nghiem/](reports/trai-nghiem/) |
| Chạy thử tại đơn vị, đào tạo, tờ phím tắt | [chay-thu-tai-don-vi.md](docs/huong-dan/chay-thu-tai-don-vi.md) · [dao-tao-buoi-1-3.md](docs/huong-dan/dao-tao-buoi-1-3.md) · [to-phim-tat.md](docs/huong-dan/to-phim-tat.md) |
| Đo trước/sau | [do-truoc-sau.md](docs/huong-dan/do-truoc-sau.md) |
| Kinh doanh: cách tính giá, mẫu hợp đồng (nháp), khảo sát khách | [docs/kinh-doanh/](docs/kinh-doanh/) |
| **Kiến trúc DX-OS Open-Core** (3 tầng, 4 nguyên lý), giao diện API, lộ trình | [kien-truc-dx-os.md](docs/kien-truc-dx-os.md) · [openapi-dxos.md](docs/api/openapi-dxos.md) · [ROADMAP.md](ROADMAP.md) |
| **Hồ sơ dự thi OLP 2026**: tự chấm có lệnh kiểm, kịch bản trình diễn 15 phút, thư nộp bài | [olp-2026-tu-cham-pof.md](docs/olp-2026-tu-cham-pof.md) · [kịch bản](docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md) · [thư nộp bài](docs/hoi-thi/olp-2026-thu-nop-bai.md) |
| Quyết định kiến trúc | [docs/adr/](docs/adr/) · Lõi DX-OS open-core (SSO, cổng API, dữ liệu, kho tệp, quy trình): [ADR 0006](docs/adr/0006-loi-dx-os-open-core.md) · Thay đổi: [CHANGELOG.md](CHANGELOG.md) |

## 📌 Trạng thái (1.0.0 — bản phát hành đầu tiên, chưa thử trên máy thật)
- ✅ Đủ tính năng cho 1 đơn vị: máy trạm, Box, Trợ lý AI, quy trình email, quản lý máy trạm, hỗ trợ từ xa, sổ hỗ trợ + khảo sát,
  giám sát, HTTPS nội bộ (CA riêng của Box), xoay khóa, **khôi phục toàn bộ Box khi hỏng ổ**; giao diện quen thuộc như Windows
  (thanh tác vụ ghim sẵn ứng dụng, Win+E/D/L, LibreOffice dạng Ribbon).
- ✅ Nghiệm thu tự động trong container ngày 14–15/10/2026 ([báo cáo](plans/reports/261014-nghiem-thu-v1-docker.md)):
  tường lửa (cả khi dừng/bật lại Docker), hỏng ổ → khôi phục, bật/tắt HTTPS, xoay khóa, khởi động lại); **Desktop trong container Linux Mint 22.3 71 PASS / 0 FAIL**;
  cả hai bộ cài chạy lần 2 `changed=0 failed=0`. Unit test Box 119 + Desktop 62 + AI 17 bài; lint sạch.
- ✅ Model AI chọn bằng bộ chấm 40 câu tiếng Việt (98%): [ADR 0003](docs/adr/0003-chon-model-ai-gemma.md), [reports/ai/](reports/ai/).
- ✅ Trải nghiệm người dùng (bản 1.2.0 đang chuẩn bị): **Trung tâm OneBee** tự mở ở lần đăng nhập đầu, trang **Kiểm tra máy** và nhắc sao lưu trễ để nhân viên tự xử lý bằng chuột,
  4 gợi ý tiếng Việt và 4 mẫu soạn văn bản của Trợ lý AI, trang chủ Box có mục soạn văn bản và số máy trạm đã sao lưu.
  **Chưa kiểm trên máy thật**: chưa có file kết quả nào trong [reports/trai-nghiem/](reports/trai-nghiem/); phiếu kiểm: [kiem-thu-trai-nghiem-may-that.md](docs/kiem-thu-trai-nghiem-may-that.md).
- 🔧 **Lõi DX-OS Open-Core** (đăng nhập một lần, API dữ liệu, kho tệp, quy trình, AI trên lõi, Sổ điều hành) dự thi OLP 2026: đang hoàn thiện cho bản 1.3.0,
  kiểm bằng bộ kiểm Box ([tests/README.md](tests/README.md)), **chưa thử trên Box thật**. Phần chưa làm (Lakehouse, IoT, bản chạy thử công khai nếu chưa có host) ghi ở [ROADMAP.md](ROADMAP.md).
- ⏳ **Chưa cài trên máy thật tại đơn vị nào** (phiên Cinnamon thật, phần cứng, LAN thật, Windows mở thư mục chung, tốc độ AI) →
  [phiếu kiểm thử máy thật](plans/reports/261010-kiem-thu-tren-may-that.md), [danh sách thử](docs/huong-dan/thu-nghiem-tren-may-ao.md).
- ⏳ Chạy thử 4 tuần tại HTX OneBee → số liệu thật cho giá, video hướng dẫn.

Mọi con số về tốc độ, chi phí, tiết kiệm chỉ công bố khi có file đo trong `reports/`. Hiện **chưa có** số đo trên máy thật.

## 💰 Giá dịch vụ
Chưa có giá chính thức — tính từ chi phí thật của đợt chạy thử: [bang-gia.md](docs/kinh-doanh/bang-gia.md).
Dải giá trong hồ sơ hội thi là giả định nội bộ, chưa có cơ sở chi phí.

## 🤝 Đóng góp và bảo mật
- Báo lỗi / đề xuất: [Issues](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/issues) (có mẫu sẵn) · Hướng dẫn đóng góp, cách chạy kiểm thử: [CONTRIBUTING.md](CONTRIBUTING.md)
- Lỗ hổng bảo mật: **báo riêng**, không mở Issue — [SECURITY.md](SECURITY.md) · Quy tắc ứng xử: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Thấy dự án hữu ích? Bấm ⭐ để nhiều HTX biết tới hơn.

## ⚖️ Giấy phép
**Vì sao MIT:** đơn vị nhỏ (HTX, hộ kinh doanh) được dùng, sửa, cài lại cho đơn vị khác và bán dịch vụ cài đặt, bảo trì mà không phải công bố lại mã riêng; MIT tương thích với mọi thành phần Apache-2.0, BSD, PostgreSQL License bên dưới. Thành phần GPL (ClamAV, Samba, Ansible) chạy như chương trình riêng, không liên kết vào mã của dự án.
Mã nguồn repo: **MIT** ([LICENSE](LICENSE)). Thành phần giữ giấy phép của tác giả ([LICENSES.md](LICENSES.md)). Lưu ý khi giới thiệu "mã nguồn mở":
| Thành phần | Giấy phép |
|---|---|
| Linux Mint/Ubuntu, LibreOffice, IBus/Bamboo, restic, Samba, x11vnc | Nguồn mở (chuẩn OSI) |
| Gemma 4 | Apache-2.0 (theo model card — kiểm lại trước khi ghi vào hợp đồng) |
| Node-RED | Apache-2.0 — nguồn mở chuẩn OSI; thay động cơ quy trình fair-code cũ |
| PostgreSQL, pgvector | PostgreSQL License (kiểu BSD/MIT) |
| PostgREST, Uptime Kuma, Ollama | MIT |
| Authelia, Caddy, SeaweedFS | Apache-2.0 |
| ClamAV | GPL-2.0-only; image dựng cục bộ **bỏ `libclamunrar`** (giấy phép UnRAR không thuộc OSI) |

## 🖥️ Demo web và hồ sơ hội thi
`demo/index.html` là giao diện **mô phỏng** (số liệu minh họa, không chạy AI thật). Hồ sơ dự thi: `docs/hoi-thi/`.

## 📞 Liên hệ

**Tác giả dự án: Dương Minh Thiện**
- 📱 0777 794 089

**Hợp tác xã OneBee**
- 📍 45 đường số 6, KDC Thái Dương, Phường Long An, Tây Ninh
- 📱 0385 944 909
- 🔢 MST: 1102128064
- 👤 Người đại diện: DUONG MINH THIEN

---

<p align="center">
  <em>Dự án dự thi Hội thi Khởi nghiệp Đổi mới Sáng tạo tỉnh Tây Ninh năm 2026</em><br/>
  <strong>🐝 HTX OneBee — Chuyển đổi số cho cộng đồng</strong>
</p>
