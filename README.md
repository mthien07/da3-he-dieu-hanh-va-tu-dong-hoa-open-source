<p align="center">
  <img src="https://img.shields.io/badge/🐝_HTX_OneBee-Open_Source_OS-e85d04?style=for-the-badge&labelColor=0a1628" alt="OneBee Open Source"/>
</p>

<h1 align="center">🐧 Hệ điều hành & Tự động hóa Open Source</h1>

<p align="center">
  <strong>OneBee OS — Linux + AI on-premise cho doanh nghiệp tự chủ công nghệ</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Hội_thi-KNĐMST_2026-f4b942?style=flat-square" alt="Contest"/>
  <img src="https://img.shields.io/badge/Giai_đoạn-Ý_tưởng-00d4aa?style=flat-square" alt="Stage"/>
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/HTX_OneBee-MST_1102128064-grey?style=flat-square" alt="Tax ID"/>
</p>

---

## 🎯 Vấn đề

- Chi phí bản quyền Windows + Office cho 20 máy tính có thể lên đến **hàng trăm triệu đồng**
- Rủi ro pháp lý khi sử dụng phần mềm bẻ khóa
- Dữ liệu doanh nghiệp phụ thuộc hoàn toàn vào cloud nước ngoài
- Thiếu giải pháp AI chạy nội bộ (on-premise) cho doanh nghiệp nhỏ

## 💡 Giải pháp

Gói dịch vụ **chuyển đổi hạ tầng CNTT toàn diện**: cài đặt Linux, tùy biến giao diện thân thiện, triển khai AI cục bộ và đào tạo vận hành — giúp doanh nghiệp **tự chủ công nghệ** với chi phí hợp lý.

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                  🏢 HẠ TẦNG DOANH NGHIỆP                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              🖥️ Linux Desktop (Client)               │    │
│  │  Ubuntu/Linux Mint │ LibreOffice │ Firefox           │    │
│  │  Theme tùy biến (giống Windows) │ Shortcut quen      │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │ LAN / VPN                          │
│  ┌─────────────────────▼───────────────────────────────┐    │
│  │              🖧 Linux Server                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │ Ollama   │  │ n8n      │  │ Harness          │   │    │
│  │  │ vLLM     │  │ Workflow │  │ Engineering      │   │    │
│  │  │ AI local │  │ Engine   │  │ Auto-ops         │   │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │    │
│  │                                                     │    │
│  │  🔒 Auto-backup │ 🔄 Auto-update │ 📊 Monitoring   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🐧 **Linux Desktop thân thiện** | Giao diện tùy biến giống Windows, dễ chuyển đổi |
| 📝 **LibreOffice** | Thay thế MS Office, tương thích file .docx/.xlsx/.pptx |
| 🤖 **AI on-premise** | Ollama + LLM mã nguồn mở (Llama, Mistral, Gemma) |
| 🔧 **Harness Engineering** | Tự động backup, update, monitoring, security |
| ⚡ **n8n Automation** | Workflow tự động hóa quy trình nội bộ |
| 🔒 **Bảo mật nội bộ** | Dữ liệu không rời khỏi mạng LAN doanh nghiệp |
| 💬 **AI Terminal** | Chatbot CLI hỗ trợ người dùng Linux mới bằng tiếng Việt |

## 🛠️ Công nghệ sử dụng

| Lớp | Công nghệ |
|-----|-----------|
| Desktop OS | Ubuntu, Linux Mint |
| Server OS | Debian, Rocky Linux |
| Văn phòng | LibreOffice, GIMP, Inkscape |
| AI/LLM | Ollama, vLLM (Llama 3, Mistral, Gemma) |
| Tự động hóa | n8n, Bash scripting, systemd |
| Monitoring | Grafana, Prometheus, htop |
| Cài đặt hàng loạt | Preseed, Kickstart |

## 🚀 Cài OneBee OS Desktop (v0.1)

Trên máy đã cài **Linux Mint 22.x** (64-bit), có mạng Internet:

```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee
sudo ./desktop/onebee-install.sh
```

Chi tiết: [docs/huong-dan/cai-dat-onebee-os-desktop.md](docs/huong-dan/cai-dat-onebee-os-desktop.md)

## 🖧 Cài OneBee Box (máy chủ nội bộ, v0.1)

Trên máy **Ubuntu Server 24.04 LTS** (64-bit) trong mạng LAN:

```bash
sudo apt install -y git
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git onebee
cd onebee
sudo ./box/onebee-box-install.sh
```

Trợ lý AI chạy tại chỗ (Open WebUI + Ollama), tự động hóa n8n, giám sát, thư mục chung, sao lưu máy trạm + Box.
Chi tiết: [docs/huong-dan/cai-dat-onebee-box.md](docs/huong-dan/cai-dat-onebee-box.md)

Kiểm thử tự động (cần Docker): xem [tests/README.md](tests/README.md)

## 🖥️ Demo web

Mở `demo/index.html` bằng trình duyệt — giao diện **mô phỏng** OneBee OS Desktop, số liệu minh họa.

## 📁 Cấu trúc dự án

```
da3-he-dieu-hanh-va-tu-dong-hoa-open-source/
├── desktop/                 # OneBee OS Desktop: onebee-install.sh + playbook Ansible
├── box/                     # OneBee Box: onebee-box-install.sh + playbook Ansible (Docker Compose)
├── tests/                   # Kiểm thử tự động (Desktop trên Mint 22.3, Box trong Docker lồng)
├── demo/index.html          # Web demo mô phỏng
├── docs/
│   ├── huong-dan/           # Hướng dẫn cài đặt, vận hành
│   ├── adr/                 # Quyết định kiến trúc
│   ├── hoi-thi/             # Hồ sơ dự thi M-02/M-03, pitch deck, kịch bản video
│   └── project-changelog.md
├── plans/                   # Kế hoạch làm sản phẩm theo phase
├── LICENSES.md              # Giấy phép các thành phần
└── README.md
```

## 💰 Bảng giá dịch vụ

| Gói | Đối tượng | Nội dung | Giá |
|-----|-----------|----------|-----|
| 🌱 **Starter** | HTX, Hộ KD (≤5 máy) | Ubuntu + LibreOffice + Ollama | 5-10 triệu |
| 🏢 **Business** | SME (5-20 máy) | Server + Client + n8n + AI CLI | 20-40 triệu |
| 🏭 **Enterprise** | DN (20-100 máy) | Server cluster + AI on-premise + Custom Distro | 50-150 triệu |
| 🔧 **Bảo trì** | Tất cả | Hỗ trợ kỹ thuật, update, nâng cấp AI | 2-5 triệu/tháng |

## 📌 Trạng thái dự án

- ✅ Hồ sơ dự thi M-02/M-03, pitch deck, kịch bản video (`docs/hoi-thi/`)
- ✅ Web demo mô phỏng
- ✅ **OneBee OS Desktop v0.1** — bộ cài chạy được; kiểm tự động trên container Linux Mint 22.3 (gồm gõ Telex thật qua IBus)
- ✅ **OneBee Box v0.1** — bộ cài chạy được; kiểm tự động trong container Ubuntu 24.04 + systemd (AI hỏi đáp, sao lưu/khôi phục)
- 🔄 Kiểm trên máy ảo/máy thật (phiên Cinnamon, phần cứng, mạng LAN thật)
- ⏳ Trợ lý `hoi` + chọn model AI tiếng Việt, cài hàng loạt, mô hình điểm tại HTX OneBee — Phase 3–5

Kế hoạch: [plans/260928-1115-onebee-os-san-pham-that/plan.md](plans/260928-1115-onebee-os-san-pham-that/plan.md)

## 📞 Liên hệ

**Hợp tác xã OneBee**
- 📍 45 đường số 6, KDC Thái Dương, Phường Long An, Tây Ninh
- 📱 0385 944 909
- 🔢 MST: 1102128064
- 👤 Người đại diện: HUỲNH TRỌNG HIẾU

---

<p align="center">
  <em>Dự án dự thi Hội thi Khởi nghiệp Đổi mới Sáng tạo tỉnh Tây Ninh năm 2026</em><br/>
  <strong>🐝 HTX OneBee — Chuyển đổi số cho cộng đồng</strong>
</p>
