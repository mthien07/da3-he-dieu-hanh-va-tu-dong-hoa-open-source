# Kế hoạch Nâng cấp các tính năng Vượt trội từ Mã nguồn mở cho OneBee OS (DA3)

**Ngày lập:** 22/10/2026  
**Dự án:** OneBee OS — `mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source`  
**Nhánh thực hiện:** `main` (tạo nhánh tính năng: `feat/nang-cap-tinh-hoa-nguon-mo`)  
**Tác giả commit:** `Dương Minh Thiện <thien20071005@gmail.com>`  
**Phân vai:**
- **Antigravity (Gemini):** Phân tích kiến trúc ngược (Reverse-engineer), lập Master Plan & Task Specs, kiểm tra nghiệm thu.
- **Claude Code:** Goal Runner (`/goal`), trực tiếp code thực thi (Implement, Refactor, viết Unit Tests & Ansible Playbooks).
- **Đại ca Thiện:** Phê duyệt lộ trình, thử nghiệm trên máy thật/VM, nghiệm thu tính năng.

---

## 1. Mục tiêu & Cảm hứng từ các dự án mã nguồn mở hàng đầu

Sau khi phân tích ngược các dự án mã nguồn mở thành công nhất trong cùng phân khúc, OneBee OS sẽ "hấp thụ" 5 tính năng cốt lõi tinh hoa nhất để chuyển mình từ sản phẩm dự thi thành **sản phẩm thương mại chạy thực tế hoàn hảo**:

| STT | Dự án truyền cảm hứng | Tính năng bóc tách & đưa vào OneBee OS | Giá trị thực tế mang lại |
| :---: | :--- | :--- | :--- |
| **01** | **CasaOS / Umbrel** | **Zero-Config LAN Discovery (`onebee.local`) & Web Dashboard** | Không cần nhớ IP; gõ `onebee.local` là vào ngay cổng thông tin máy chủ. |
| **02** | **YunoHost** | **Công cụ Tự chẩn đoán lỗi (`onebee-box chan-doan`)** | 1 lệnh quét toàn diện mạng, RAM, disk, docker, SSL, backup; xuất báo cáo tiếng Việt. |
| **03** | **Zorin OS** | **Trình bẫy file Windows (`.exe` Interceptor & App Helper)** | Đúp chuột vào file `.exe` sẽ hiện gợi ý phần mềm Linux thay thế hoặc chạy WINE. |
| **04** | **Nextcloud / Dify** | **Kho Prompt hành chính NĐ 30 & Chat tài liệu nội bộ (Local RAG)** | Có sẵn nút bấm soạn công văn, biên bản họp; nạp tài liệu mẫu HTX vào AI tra cứu. |
| **05** | **Synology / TrueNAS** | **Cảnh báo sự cố chủ động qua Telegram / Webhook n8n** | Tự động bắn tin nhắn khi sao lưu lỗi hoặc ổ cứng sắp đầy (>85%). |

---

## 2. Danh mục các Task thực thi chi tiết cho Claude Code

| Task | Tên task & File chi tiết | Mức độ ưu tiên | Thành phần tác động |
| :---: | :--- | :---: | :--- |
| **Task 01** | [LAN Discovery `onebee.local` & Web Dashboard](task-01-lan-discovery-mdns-va-web-dashboard.md) | **Cao (P1)** | `box/ansible`, Caddy, Avahi mDNS, Landing HTML |
| **Task 02** | [Bộ công cụ Tự chẩn đoán lỗi OneBee Diagnosis](task-02-cong-cu-tu-chan-doan-onebee-diagnosis.md) | **Cao (P1)** | `box/scripts/onebee-box`, `desktop/scripts` |
| **Task 03** | [Windows App Helper & Gợi ý thay thế](task-03-windows-app-helper-va-goi-y-thay-the.md) | **Trung bình (P2)** | `desktop/onebee-install.sh`, MIME Desktop file, Python/Bash GUI |
| **Task 04** | [Kho Prompt hành chính & Tri thức nội bộ RAG](task-04-rag-chat-tai-lieu-va-mau-prompt-hanh-chinh.md) | **Trung bình (P2)** | Open WebUI API / Pipelines, Knowledge presets |
| **Task 05** | [Cảnh báo sự cố chủ động qua Telegram/Zalo](task-05-canh-bao-su-co-qua-telegram-zalo.md) | **Trung bình (P2)** | `n8n` workflows, `onebee-box` alerts hook |

---

## 3. Quy chuẩn kỹ thuật bắt buộc khi thực hiện (Quality Gates)

1. **Idempotency (Tính lũy nghiệm):** Chạy lại playbook Ansible lần 2 bắt buộc `changed=0 failed=0`.
2. **Kiểm thử hồi quy (TDD):** Mỗi tính năng đều phải có script test tự động trong thư mục `tests/box/` hoặc `tests/desktop/`.
3. **Tiêu chuẩn mã nguồn:**
   - Script shell đạt chuẩn `shellcheck` 100%.
   - Playbook YAML đạt chuẩn `yamllint` và `ansible-lint`.
4. **Bảo mật:** Không để lọt mật khẩu, API token hay thông tin riêng tư vào git commit.
5. **Commit Message:** Chuẩn Conventional Commits bằng tiếng Việt: `feat(box): ...`, `feat(desktop): ...`, `test: ...`. Tác giả: `Dương Minh Thiện <thien20071005@gmail.com>`.
