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

## 🚀 Chạy Demo

```bash
# Clone repo
git clone https://github.com/mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source.git
cd da3-he-dieu-hanh-va-tu-dong-hoa-open-source

# Mở demo web (không cần cài đặt)
open demo/index.html
```

> 💡 Demo web giả lập giao diện **OneBee OS Desktop** với Terminal AI tương tác.

## 📁 Cấu trúc dự án

```
da3-he-dieu-hanh-va-tu-dong-hoa-open-source/
├── demo/
│   └── index.html          # Web demo Linux Desktop simulator
├── docs/
│   ├── m02-m03-ho-so-du-thi.md  # Hồ sơ dự thi M-02 & M-03
│   ├── pitch-deck.md            # Pitch Deck (10 slides)
│   └── video-script.md          # Kịch bản video 3 phút
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

- ✅ Hồ sơ dự thi M-02/M-03
- ✅ Pitch Deck
- ✅ Video Script
- ✅ Web Demo tương tác (Linux Desktop Simulator)
- 🔄 Triển khai pilot nội bộ (theo kế hoạch)

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
