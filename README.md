<p align="center">
  <img src="https://img.shields.io/badge/🐝_HTX_OneBee-DX--OS_Open--Core-e85d04?style=for-the-badge&labelColor=0a1628" alt="OneBee Open Source"/>
</p>

<h1 align="center">🐧 Hệ điều hành & Tự động hóa Open Source (OneBee OS v1.3.0)</h1>

<p align="center">
  <strong>Khung nền tảng chuyển đổi số Lõi Mở (DX-OS Open-Core) 100% chuẩn OSI cho Doanh nghiệp Siêu nhỏ và Hợp tác xã (MSME/HTX)</strong>
</p>

<p align="center">
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/actions/workflows/ci.yml"><img src="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/releases"><img src="https://img.shields.io/github/v/release/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source?include_prereleases&style=flat-square&label=Ph%C3%A1t%20h%C3%A0nh&color=00d4aa" alt="Phát hành"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT_(100%25_OSI)-blue?style=flat-square" alt="License MIT"/></a>
  <a href="https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/commits"><img src="https://img.shields.io/github/last-commit/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source?style=flat-square&label=C%E1%BA%ADp%20nh%E1%BA%ADt" alt="Cập nhật"/></a>
  <img src="https://img.shields.io/badge/AI-RAG_t%E1%BA%A1i_ch%E1%BB%97_(Ollama)-8a2be2?style=flat-square" alt="AI chạy tại chỗ"/>
  <img src="https://img.shields.io/badge/OLP_2026-DX--OS_Open--Core-f4b942?style=flat-square" alt="OLP 2026"/>
</p>

<p align="center">
  <a href="docs/kien-truc-dx-os.md"><b>🏛️ Kiến trúc DX-OS</b></a> ·
  <a href="docs/olp-2026-tu-cham-pof.md"><b>✅ Tự chấm 40 tiêu chí PoF</b></a> ·
  <a href="docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md"><b>📖 Cài từ A đến Z</b></a> ·
  <a href="docs/api/openapi-dxos.md">OpenAPI</a> ·
  <a href="tests/README.md">Kiểm thử</a> ·
  <a href="SECURITY.md">Bảo mật</a> ·
  <a href="CONTRIBUTING.md">Đóng góp</a>
</p>

---

## 🎯 Vấn đề
- Máy văn phòng ở HTX, hộ kinh doanh, doanh nghiệp siêu nhỏ thường dùng phần mềm không bản quyền hoặc bị khóa chặt vào đám mây trả phí → rủi ro pháp lý, dễ nhiễm mã độc.
- Không có người chuyên CNTT: không ai phân quyền dữ liệu, không ai sao lưu, cập nhật, hoặc kiểm soát phê duyệt đơn hàng/phiếu chi.
- Muốn dùng AI hỗ trợ soạn văn bản hành chính và tra cứu quy trình nhưng không thể đưa dữ liệu nội bộ lên dịch vụ nước ngoài.

## 💡 Giải pháp OneBee OS v1.3.0 (DX-OS Open-Core)
| Thành phần | Làm gì |
|---|---|
| **OneBee OS Desktop** | Bộ cài biến Ubuntu 24.04 / Linux Mint 22 thành máy văn phòng tiếng Việt: gõ Telex (`ibus-bamboo`), LibreOffice lưu mặc định `.docx`/`.xlsx`, font tương thích văn bản hành chính, tự cập nhật, tự sao lưu Restic lên Box, lệnh `hoi` hỏi Trợ lý AI nội bộ, báo sự cố và hỗ trợ từ xa. |
| **OneBee Box (DX-OS Open-Core)** | Hộp dịch vụ nội bộ 3 tầng chạy 100% bằng phần mềm nguồn mở chuẩn OSI trên Ubuntu Server 24.04:<br>• **`[H]` Con người & Định danh**: SSO tập trung qua **Authelia** (`Apache-2.0`) + Cầu nối JWT 60s (`onebee-cau-noi.py`).<br>• **`[P]` Quy trình & Poka-yoke**: **Node-RED** (`Apache-2.0`) điều phối 11 luồng nghiệp vụ và phê duyệt quản lý chống tự duyệt phiếu của chính mình.<br>• **`[D]` Dữ liệu & Kho tệp an toàn**: **PostgreSQL 16 + `pgvector` + PostgREST** phân quyền tận dòng (**RLS**) cho `nhan_vien`, `ky_thuat`, `quan_ly`; kho đối tượng **SeaweedFS** kèm quét & cách ly mã độc **ClamAV** (`onebee-kho-tep.py`).<br>• **`[I]` Trí tuệ Nhân tạo & Nghị định 30**: Dịch vụ **`onebee-ai-rag.py`** (`MIT`) + **Ollama** tra cứu RAG nội bộ, ẩn danh hóa PII và sinh văn bản hành chính theo **Nghị định 30/2020/NĐ-CP**. |
| **Sổ điều hành HTX (`/so-dieu-hanh/`)** | Giao diện web 1 trang tiếng Việt hợp nhất cả 4 trụ cột `[H]-[P]-[D]-[I]`: tạo phiếu Đơn hàng / Hỗ trợ / Khảo sát, đính kèm tệp có quét virus, hàng đợi phê duyệt quản lý Poka-yoke và khung hỏi AI / tạo công văn. |

```
 Máy trạm (Ubuntu/Mint + OneBee Desktop)           OneBee Box (Ubuntu Server 24.04 — DX-OS Open-Core, 100% OSI)
 ├─ Gõ tiếng Việt, LibreOffice          sao lưu    ├─ [H] Authelia SSO + Cầu nối JWT 60s (onebee-cau-noi.py)
 ├─ onebee-sao-luu (hằng ngày)     ───────────────▶├─ [P] Node-RED (11 luồng + Phê duyệt Poka-yoke) + Sổ điều hành HTX
 ├─ onebee-bao-tinh-trang (mỗi giờ) ──────────────▶├─ [D] PostgreSQL 16 (pgvector + RLS) + PostgREST + SeaweedFS + ClamAV
 ├─ hoi "câu hỏi"                   ──────────────▶├─ [I] OneBee AI RAG (MIT) + Ollama + Mẫu văn bản Nghị định 30
 └─ onebee-ho-tro / cảnh báo        ◀──HTTPS/LAN── └─ Restic Backup + Uptime Kuma + MeshCentral + Caddy TLS nội bộ
```

<table>
  <tr>
    <td width="50%"><img src="docs/huong-dan/anh/01-trang-gioi-thieu-box.png" alt="Trang giới thiệu OneBee Box"/><br/><sub>Trang giới thiệu của OneBee Box trong mạng LAN</sub></td>
    <td width="50%"><img src="docs/huong-dan/anh/02-tro-ly-ai-tieng-viet.png" alt="Trợ lý OneBee soạn thông báo tiếng Việt"/><br/><sub>Trợ lý AI tiếng Việt chạy tại chỗ soạn thông báo họp HTX</sub></td>
  </tr>
</table>

<sub>Ảnh chụp từ Box chạy trong môi trường kiểm thử, không phải tại đơn vị thật.</sub>

## 🚀 Cài đặt
> **Người không chuyên**: làm theo [Hướng dẫn cài từ A đến Z](docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md) — có sơ đồ, từng lệnh dán được, kết quả phải thấy.

Bản phát hành (file nén + SHA256SUMS): [Releases](https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source/releases).
Tự thử trên máy ảo trước khi cài cho đơn vị: [thu-nghiem-tren-may-ao.md](docs/huong-dan/thu-nghiem-tren-may-ao.md).

**Máy trạm** — Ubuntu 24.04 / Linux Mint 22.x 64-bit:
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git
cd da3-he-dieu-hanh-va-tu-dong-hoa-open-source
sudo bash scripts/install-desktop.sh
```

**OneBee Box** — Ubuntu Server 24.04 64-bit, RAM ≥ 8 GB, ổ trống ≥ 40 GB:
```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git
cd da3-he-dieu-hanh-va-tu-dong-hoa-open-source
sudo bash scripts/install-box.sh
```
Sau khi cài xong, mở `https://onebee-box.local/` (Cổng nội bộ) hoặc `https://onebee-box.local/so-dieu-hanh/` (Sổ điều hành HTX). Xem thông tin kết nối bằng `sudo onebee-box thong-tin-may-tram`.

## 📚 Tài liệu
- **Hồ sơ OLP 2026 & Kiến trúc DX-OS Open-Core**:
  - [Kiến trúc 3 tầng DX-OS & 4 nguyên tắc thiết kế](docs/kien-truc-dx-os.md)
  - [ADR 0006 — Khảo sát, chấm điểm & chọn lõi DX-OS Open-Core](docs/adr/0006-loi-dx-os-open-core.md)
  - [ADR 0007 — Chuyển đổi động cơ quy trình sang Node-RED (Apache-2.0)](docs/adr/)
  - [Bảng tự chấm 40 tiêu chí Proof of Freedom (PoF)](docs/olp-2026-tu-cham-pof.md)
  - [Đặc tả OpenAPI 3.0 của các dịch vụ DX-OS](docs/api/openapi-dxos.md)
  - [Kịch bản trình diễn trực tiếp 10 phút](docs/hoi-thi/olp-2026-kich-ban-trinh-dien.md) · [Thư nộp bài OLP 2026](docs/hoi-thi/olp-2026-thu-nop-bai.md)
  - [Lộ trình phát triển (ROADMAP)](ROADMAP.md) · [Nhật ký thay đổi (CHANGELOG)](CHANGELOG.md)
- **Hướng dẫn cài đặt & vận hành**:
  - [Hướng dẫn cài từ A đến Z](docs/huong-dan/huong-dan-cai-dat-tu-a-den-z.md)
  - [Bộ cài đặt USB ngoại tuyến (Air-gapped)](docs/usb-cai-dat-ngoai-tuyen.md)
  - [Thử nghiệm trên máy ảo](docs/huong-dan/thu-nghiem-tren-may-ao.md)
  - [Sổ tay dùng máy hàng ngày](docs/so-tay-nguoi-dung-1-trang.md) · [Sổ tay người phụ trách](docs/so-tay-it-don-vi.md)
  - [Quy trình triển khai 5 bước](docs/quy-trinh-trien-khai-5-buoc.md)

## 🧪 Kiểm thử
Chạy toàn bộ kiểm thử tự động (header giấy phép SPDX, kết xuất mẫu Jinja2, unit tests cho Desktop, Box, AI và lõi DX-OS):
```bash
python3 scripts/chen-giay-phep.py --kiem
python3 tests/kiem-tra-mau-jinja.py
python3 -m unittest discover -s tests/box -p "test_*.py"
python3 -m unittest discover -s tests/desktop -p "test_*.py"
python3 -m unittest discover -s tests/ai -p "test_*.py"
```
Chi tiết xem tại [tests/README.md](tests/README.md) và [Kết quả kiểm thử trên máy thật](docs/kiem-thu-tren-may-that.md).

## 📄 Giấy phép
Mã nguồn trong repo này phát hành theo giấy phép **MIT** — xem [LICENSE](LICENSE) — cho phép mọi tổ chức, doanh nghiệp, sinh viên tự do sử dụng, nghiên cứu, sửa đổi và phân phối lại (kể cả thương mại) nhằm bảo đảm chủ quyền số và không khóa chặt nhà cung cấp. Mọi tệp mã nguồn trong kho đều mang dòng định danh `SPDX-License-Identifier: MIT` ở phần đầu tệp.
Danh mục giấy phép chuẩn OSI của toàn bộ các phần mềm đi kèm xem tại [LICENSES.md](LICENSES.md).

---

**Tác giả dự án: Dương Minh Thiện**
- 📱 0777 794 089

**Hợp tác xã OneBee**
- 📍 45 đường số 6, KDC Thái Dương, Phường Long An, Tây Ninh
- 📱 0385 944 909
- 🔢 MST: 1102128064
- 👤 Người đại diện: DUONG MINH THIEN

---

<p align="center">
  <em>Dự án dự thi Khối Phần mềm Nguồn mở — OLP 2026 & Hội thi Khởi nghiệp Đổi mới Sáng tạo tỉnh Tây Ninh năm 2026</em><br/>
  <strong>🐝 HTX OneBee — Chuyển đổi số mở cho cộng đồng</strong>
</p>
