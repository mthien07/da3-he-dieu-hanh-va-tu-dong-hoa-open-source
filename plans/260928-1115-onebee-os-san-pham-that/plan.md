# OneBee OS — Kế hoạch làm sản phẩm thật (DA3)

Lập ngày 28/9/2026 · Repo `mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source` · nhánh `main`
Mốc tính theo tuần kể từ khi anh chốt Phase 0 (Tuần 1), không gắn lịch. Số tuần là **dự kiến**.

## Sản phẩm (chốt từ hồ sơ dự thi — "Máy cũ chạy mới, dữ liệu ở nhà")
1. **OneBee OS Desktop** — Linux Mint cài sẵn tiếng Việt, văn phòng, giao diện quen Windows
2. **OneBee Box** — 1 máy chủ nội bộ: AI chạy tại chỗ, tự động hóa n8n, thư mục chung, sao lưu, giám sát
3. **Trợ lý `hoi`** — hỏi đáp tiếng Việt ngay trên máy, gọi AI trên Box
4. **Bộ triển khai & bảo trì hàng loạt** — lõi của gói bảo trì (nguồn thu chính trong mô hình KD)

## Các phase
| # | Phase | Tuần | Trạng thái | File |
|---|-------|------|-----------|------|
| 0 | Chuẩn bị: lab test, giấy phép, dọn repo, CI | 1 | ✅ Xong (28/9) | [phase-00](phase-00-chuan-bi-phan-cung-lab-repo.md) |
| 1 | OneBee OS Desktop v0.1 | 2–4 | ✅ Code + test mở rộng đạt (28/9); còn thử phiên Cinnamon thật | [phase-01](phase-01-onebee-os-desktop-v01.md) |
| 2 | OneBee Box v0.1 | 4–6 | ✅ Code + test Docker lồng đạt (28/9); còn thử máy thật | [phase-02](phase-02-onebee-box-may-chu-noi-bo-v01.md) |
| 3 | Trợ lý AI tiếng Việt + workflow n8n mẫu | 6–8 | ✅ Xong (29/9) — model gemma4:e2b-it-qat, anh duyệt; đo tốc độ trên Box thật để sau | [phase-03](phase-03-tro-ly-ai-tieng-viet-va-workflow-n8n.md) |
| 4 | Cài hàng loạt, quản lý tập trung, đo đạc | 8–10 | 🔄 Code + test container (29/9); chờ máy thật: cài 3 máy, đo trước/sau | [phase-04](phase-04-cai-hang-loat-quan-ly-tap-trung-do-dac.md) |
| 5 | Mô hình điểm tại HTX OneBee | 10–14 | Chưa bắt đầu | [phase-05](phase-05-mo-hinh-diem-tai-htx-onebee.md) |
| 6 | Đóng gói dịch vụ bán được, release v1.0 | 14–16 | Chưa bắt đầu | [phase-06](phase-06-dong-goi-dich-vu-release-v1.md) |

## Nguyên tắc
- YAGNI/KISS: dùng phần mềm có sẵn (Mint, Ansible, Docker Compose, Ollama, n8n, restic). Chỉ viết phần "keo dán" + tiếng Việt hóa.
- v0.x KHÔNG tự build ISO/distro riêng: cài Mint chuẩn rồi chạy bộ cài OneBee. ISO riêng xét lại sau pilot.
- Mọi con số đưa ra ngoài (RAM, tốc độ, tiền tiết kiệm) chỉ lấy từ đo đạc Phase 4–5.
- Mỗi phase xong: anh xem chạy thật trên VM/máy thật rồi mới qua phase sau.

## Phụ thuộc chính
- Linux Mint 22.3 "Zena": nền Ubuntu 24.04, chỉ 64-bit (amd64), hỗ trợ đến 4/2029 → máy 32-bit ngoài phạm vi.
- Không có máy cũ để thử (anh chốt 28/9) → kiểm tự động trong container `linuxmintd/mint22.3-amd64` (CI) + máy ảo Mint trên MacBook (Parallels) cho phần giao diện. Máy thật: dùng máy của đơn vị pilot ở Phase 5.
- Phần mềm chỉ chạy Windows ở HTX (kê khai thuế, BHXH, ký số token) — rủi ro lớn nhất, phải khảo sát ở Phase 0.

## Phân vai
- Em: script, Ansible, Docker Compose, CLI, workflow, CI/test, tài liệu.
- Anh: phần cứng, chạy thử máy thật, đơn vị pilot, push GitHub, quyết định sản phẩm.

## Đã chốt (28/9)
- Làm tiếp trên repo da3 hiện tại; không chạy theo lịch hội thi; không có máy cũ để test.

## Câu hỏi còn mở
1. Máy làm Box thật: dùng máy nào? Có GPU không? (quyết định model AI ở Phase 3)
