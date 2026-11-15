<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 Dương Minh Thiện, HTX OneBee -->
# Kiến trúc OneBee DX-OS Open-Core (3 tầng & 4 nguyên lý thiết kế)

Tài liệu này mô tả kiến trúc tổng thể của **OneBee DX-OS Open-Core** — hệ điều hành và nền tảng số lõi mở dành cho Hợp tác xã và doanh nghiệp nhỏ & vừa (SME), kế thừa OneBee OS và nâng cấp đáp ứng trọn vẹn định hướng nền tảng chuyển đổi số (DX-OS) OLP 2026.

---

## 1. Sơ đồ kiến trúc 3 tầng (theo chuẩn Đề thi OLP 2026)

```mermaid
flowchart TB
    subgraph T3["Tầng Nền tảng Kinh doanh số (Định hướng mở rộng)"]
        direction LR
        T3A["Cổng kết nối TMĐT / Ngân hàng / Hoá đơn điện tử"]
        T3B["Phân tích dữ liệu mở rộng & AI đa tác nhân"]
    end

    subgraph T2["Tầng Không gian Năng lực số (Web Workspace H-P-D-I)"]
        direction LR
        H["[H] Điều phối công việc<br/>Tạo đơn hàng, đính kèm PDF,<br/>gửi yêu cầu hỗ trợ"]
        P["[P] Vận hành quy trình<br/>Phê duyệt đơn 2 bước,<br/>xử lý sự cố & khảo sát"]
        D["[D] Điều hành & Giám sát<br/>KPI đơn hàng, Uptime Kuma,<br/>tình trạng máy trạm LAN"]
        I["[I] Trợ lý AI nội bộ<br/>Hỏi đáp RAG NĐ 30/Luật HTX,<br/>tóm tắt điều hành an toàn PII"]
    end

    subgraph T1["Tầng Nền tảng Dịch vụ Lõi số (Headless PaaS — 100% OSI)"]
        direction TB
        GW["🚪 Cổng API & Reverse Proxy (Caddy 2.11.4)<br/>TLS 1.3 · HTTP/1.1+HTTP/2 · Tước Remote-*/Cookie giả mạo"]
        SSO["🔐 Định danh & SSO (Authelia 4.39.28 + onebee-dinh-danh)<br/>1FA nhân viên · 2FA TOTP quản lý/kỹ thuật · JWT ES256 (60s)"]
        DB["🗄️ Dữ liệu cấu trúc (PostgreSQL 18.7 + pgvector 0.8.7 + PostgREST 16.5)<br/>RLS theo nguoi_tao/phong_ban · ràng buộc CHECK · tự sinh OpenAPI"]
        FS["📦 Kho tệp & Kiểm dịch biên mạng (SeaweedFS 4.53 + ClamAV 1.5.4)<br/>Quét clamscan đồng bộ -> CLEAN / INFECTED trước khi lưu đối tượng"]
        WF["⚙️ Động cơ quy trình (Node-RED 5.0.9)<br/>Điều phối luồng phê duyệt & gửi thư SMTP qua node-red-node-email"]
        AI["🤖 Trợ lý AI & RAG lõi (onebee-ai-rag.py MIT + Ollama 0.34.4 Gemma 4)<br/>BM25 tiếng Việt + kho mẫu NĐ 30/Luật HTX + CLI `hoi`"]
        BK["💾 Sao lưu bất biến & Giám sát (restic rest-server 0.14.0 + Uptime Kuma 2.5.5)"]
    end

    subgraph DESK["💻 Máy trạm văn phòng OneBee OS Desktop (Linux Mint 22.x / Ubuntu)"]
        DS["LibreOffice (.docx/.xlsx) · IBus Bamboo · `hoi` CLI · `onebee-sao-luu` · `onebee-bao-tinh-trang`"]
    end

    DESK -->|HTTPS + CA riêng / Bearer CLI| GW
    T2 -->|HTTPS + Cookie SSO| GW
    GW -->|forward_auth| SSO
    GW -->|/api/*| DB
    GW -->|/files/*| FS
    GW -->|/quy-trinh/*| WF
    GW -->|/ai/*, /ai-cli/*| AI
    T3 -.->|Định hướng API chuẩn mở| GW
```

---

## 2. Bảng ánh xạ thành phần lõi & Giấy phép OSI (100% Open-Core)

Mọi thành phần cài đặt mặc định trên OneBee DX-OS đều sử dụng giấy phép nguồn mở được **OSI phê duyệt** (chi tiết tệp giấy phép kiểm chứng tại [LICENSES.md](../LICENSES.md) và [ADR 0006](adr/0006-loi-dx-os-open-core.md)):

| Nhóm chức năng lõi (DX-OS) | Thành phần hiện thực | Phiên bản ghim | Giấy phép OSI (SPDX) |
|---|---|---|---|
| **Tầng Không gian Năng lực số** (`H-P-D-I`) | Giao diện Web H-P-D-I thuần HTML/CSS/JS tĩnh & `onebee-ai-rag.py` UI | 1.3.0 | `MIT` |
| **Tầng Nền tảng Dịch vụ Lõi số** — Cổng API & TLS | Caddy | 2.11.4 | `Apache-2.0` |
| Định danh tập trung & SSO (`forward_auth`) | Authelia + cầu nối Python `onebee-dinh-danh` | 4.39.28 + 3.14 | `Apache-2.0` + `MIT` |
| CSDL quan hệ + Vector RAG | PostgreSQL + pgvector | 18.7 + 0.8.7 | `PostgreSQL` |
| API dữ liệu tự sinh & phân quyền RLS | PostgREST | 16.5 | `MIT` |
| Kho tệp đối tượng & API S3/Filer | SeaweedFS | 4.53 | `Apache-2.0` |
| Kiểm dịch mã độc biên mạng | ClamAV (`clamscan`, loại bỏ `libclamunrar` non-OSI) + `cvdupdate` | 1.5.4 + 1.2.0 | `GPL-2.0-only` + `Apache-2.0` |
| Động cơ quy trình nghiệp vụ | Node-RED + `node-red-node-email` | 5.0.9 + 5.2.5 | `Apache-2.0` |
| Trợ lý AI nội bộ & RAG tiếng Việt | `onebee-ai-rag.py` + Ollama + Gemma 4 (`gemma4:e2b-it-qat`) | MIT + 0.34.4 | `MIT` + `Apache-2.0` |
| Giám sát hệ thống & dịch vụ | Uptime Kuma | 2.5.5 | `MIT` |
| Sao lưu 2 tầng chống mã độc tống tiền | `restic` + `rest-server` (`--append-only`) | 0.14.0 | `BSD-2-Clause` |
| Tự động hóa hạ tầng & máy trạm | Ansible + Bash/Python (`onebee-box`, `hoi`) | GPL-3.0+ / MIT | `MIT` (mã nguồn OneBee) |

---

## 3. Đối chiếu 4 nguyên lý thiết kế (theo Mục 4 Đề thi)

> **Nguyên tắc trung thực kỹ thuật:** Bảng dưới đây phân tách rạch ròi giữa phần **đã triển khai chạy thật** trong mã nguồn/kiểm thử và phần **định hướng kiến trúc** trong lộ trình tiếp theo.

| Nguyên lý thiết kế | Phần đã chạy thật trên OneBee DX-OS | Phần định hướng mở rộng (Roadmap) |
|---|---|---|
| **(i) Tách dữ liệu nóng/lạnh** | **Dữ liệu nóng:** PostgreSQL 18.7 OLTP phục vụ truy vấn tác nghiệp độ trễ thấp (`don_hang`, `yeu_cau_ho_tro`, `khao_sat`, `tep_dinh_kem`). **Dữ liệu lạnh:** `restic` sao lưu đóng băng bất biến 2 tầng (`--private-repos --append-only`, đồng bộ hằng đêm 23:00 ra ổ ngoài). | Bổ sung phân tầng lưu trữ phân tích dạng **Lakehouse (Apache Iceberg)** trên kho đối tượng SeaweedFS cho dữ liệu lịch sử dài hạn và báo cáo BI đa kỳ. |
| **(ii) Hội tụ IT/OT & Bản sao số** | Công cụ máy trạm `onebee-bao-tinh-trang` gửi định kỳ trạng thái phần cứng/hệ điều hành/bản sao lưu có chữ ký HMAC về chung CSDL tác nghiệp của Box (hội tụ telemetry CNTT vào **Không gian Điều hành [D]** và **Tầng Nền tảng Dịch vụ Lõi số**). | Mở rộng chuẩn kết nối **IoT / NGSI-LD** thu nhận dữ liệu cảm biến nhà kho/vườn trồng HTX (nhiệt độ, độ ẩm, điện năng) hội tụ về cùng đường ống PostgreSQL/Node-RED. |
| **(iii) Quản trị dữ liệu & chất lượng** | Mọi bảng tác nghiệp trong PostgreSQL áp đặt ràng buộc `CHECK` (trạng thái hợp lệ, giá trị dương), **Row-Level Security (RLS)** cô lập dữ liệu theo vai trò (`nhan_vien`, `ky_thuat`, `quan_ly`), **PostgREST** tự động sinh đặc tả OpenAPI phản ánh đúng schema, kèm bảng lịch sử thay đổi và kiểm soát chống rò rỉ PII ở `/ai/tom-tat`. | Tích hợp danh mục dữ liệu & truy xuất nguồn gốc tập trung (**OpenMetadata**) khi HTX/SME có nhiều cơ sở dữ liệu liên phòng ban. |
| **(iv) Zero-Trust + GitOps + Kiểm dịch biên mạng** | **Zero-Trust:** Mọi cổng backend đóng hoàn toàn ra LAN; chỉ Caddy công bố cổng; xác thực bắt buộc qua Authelia `forward_auth` + cầu nối JWT `ES256` thời hạn ngắn (`60s`); tự động tước header giả mạo (`Remote-*`, `Authorization`, `Cookie`) trước khi định tuyến. **Kiểm dịch biên mạng:** mọi tệp tải lên `/files/` đi qua `clamscan` trả trạng thái `CLEAN` / `INFECTED` trước khi ghi SeaweedFS. **GitOps:** toàn bộ Box & Desktop quản trị bằng playbook Ansible idempotent (`changed=0` khi chạy lại). | Tích hợp ký ảnh container (Cosign) và tự động đối chiếu chính sách bảo mật khi đồng bộ cấu hình đa chi nhánh. |
