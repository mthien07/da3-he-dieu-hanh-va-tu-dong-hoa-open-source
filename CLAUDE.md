# OneBee OS (DA3) Workspace Instructions

## Project Context
- Repository: `mthien07/da3-he-dieu-hanh-va-tu-dong-hoa-open-source`
- Language: Tiếng Việt (mọi câu hỏi, báo cáo, commit message, tài liệu).

## Mandatory Commit Conventions
- Commit author: `Dương Minh Thiện <thien20071005@gmail.com>`
- Convention: Conventional Commits tiếng Việt (`feat(box): ...`, `feat(desktop): ...`, `test: ...`, `fix: ...`).
- Tuyệt đối không đề cập AI trong git commit message.
- Tuyệt đối không commit file cấu hình chứa bí mật (`.env`, private key, token).

## Quality Standards
- Kiểm thử hồi quy (TDD): Luôn có unit test / regression test trong `tests/` để chứng minh tính năng hoạt động.
- Idempotency (Tính lũy nghiệm): Bộ cài và Ansible Playbook chạy lại lần 2 phải đạt `changed=0 failed=0`.
- Lint & Cú pháp: `shellcheck`, `yamllint`, `ansible-lint` sạch 100%.

## Current Active Plan
- Kế hoạch hiện tại: `plans/261022-1500-nang-cap-vuot-troi-tu-nguon-mo/plan.md`
- Thực hiện lần lượt từ Task 01 đến Task 05 theo đúng đặc tả kỹ thuật trong từng file task.
