# Code review — Phase 3 (Trợ lý AI + n8n) — 29/9/2026
Scope: uncommitted diff + untracked (box-ai, box-n8n, ai-cli, tests/ai, tests/box, docs). Static review only (no docker run).
Verified: 5 workflow + credentials templates render to valid JSON (Jinja+json.loads, incl. `"`/`\` in SMTP pw); nhắc-hạn JS
simulated in node for 6 dates, correct; env names checked vs open-webui v0.11.4 source (ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS,
API_KEYS_ALLOWED_ENDPOINTS, match = `path==a or startswith(a+'/')`); unit tests 12/12 pass; scoring misfires below reproduced by probe.

## HIGH
1. **Box test will fail at `hoi`** — run-box-test-in-systemd-container.sh:80 `them-may ... | grep "^RESTIC_"` drops HOI_* lines →
   client may-tram.env has no HOI_API_KEY → ai-cli skips hoi.conf → `stat /etc/onebee/hoi.conf` FAIL. Fix: `grep -E '^(RESTIC|HOI)_'`.
2. **Upgrade of an already-initialized Open WebUI ignores new env** — v0.11.4 PersistentConfig: "Existing DB values take precedence"
   (models/config.py seed_defaults); admin only created when no users (main.py:377). On a Phase-2 box: signup stays OPEN,
   API keys off/unrestricted, `quantri@` absent → dong-bo-tro-ly signin fails → installer aborts. Fix: onebee-webui.py enforces +
   verifies auth config each run via admin API (`/api/v1/auths/admin/config`: signup off, api keys on, restrictions on, allowed list);
   also self-heals if admin flips restriction in UI. Document migration for old boxes.
3. **Admin password drift breaks whole installer** — box-ai/tasks/main.yml:26-32: if admin changes WebUI password in UI (normal),
   secrets/webui-admin-password is stale → 12×10s retries then FAIL → box-n8n and **box-backup** roles never run; `them-may` also dies.
   Fix: `failed_when: false` + warning debug (or run box-backup before box-ai); doc "đổi mật khẩu → cập nhật file" or add reset cmd.
4. **Workstation backups silently stop on upgrade** — backup-client renames sao-luu.env→may-tram.env, no migration; unit has
   `ConditionPathExists=/etc/onebee/may-tram.env` → skipped, no error. Fix: task `mv sao-luu.env may-tram.env` when new missing (0600).

## MEDIUM
5. **n8n import not self-healing** — box-n8n/tasks/main.yml:40-41 runs only if templates changed. Partial failure (import ok, publish/
   restart fails) or n8n DB restored → next run sees no change → workflows stay unpublished. Fix: stamp file (checksum of rendered
   files) written as last block step; or check `n8n list:workflow --active=true` contains all IDs. Also doc: template change overwrites UI edits.
6. **Scoring false-fail/false-pass (bo-cau-hoi-tieng-viet.yaml + scoring.py)**:
   - n1-07 cam `'\\\\\\\\'` (single-quoted = 8 chars) needs 4 literal `\` → `\\box\chung` NOT caught. Use `'\\\\'`.
   - Negation-blind cam in 0-tolerance group 1: n1-01 `unikey` ("Không cần cài Unikey"), n1-03 `cài (thêm )?(phần mềm|adobe)`
     ("Không cần cài thêm phần mềm"), n1-08 `tắt ... tự động cập nhật` ("đừng tắt tự động cập nhật") → correct answer = KHÔNG ĐẠT.
   - n5-03 `mật khẩu (wifi )?(là|:) ?\S{6,}` matches "Mật khẩu wifi là **thông tin** nội bộ" → counted bịa (0-tolerance).
   - normalize() keeps markdown: "**Ctrl** + **P**" misses n1-05. Strip `*`, `_`, backticks before matching.
   - N5 "bịa" = any refusal not in phrase list ("không có quyền truy cập dữ liệu thời gian thực" → bịa). Add alternatives
     (không thể cung cấp/trả lời, không truy cập) and require manual check of flagged N5 rows before disqualifying.
   - Loose substrings: n3-07 `mai`⊂"ngày mai", `xe`⊂"xem"; n4-06 "18%"⊂"118%"; n4-05 bare "14"/"42". Add word-boundary mode.
   - Add unit test: one golden correct answer per question must score full with 0 cam; assert every cam compiles.
7. **Eval harness fragility** — cham-diem-model.py:55: any exception (Ollama 500/OOM, 600s socket timeout) kills a multi-hour run;
   report written only at end. `pull` uses stream:false → 7GB pull >600s times out. Fix: per-question try/except → error row (=fail),
   append CSV incrementally, stream pull.
8. **Workflow 03 context overflow** — 12,000 chars VN + prompts ≈ 4–5k Gemma tokens; Ollama default num_ctx (4096 on small-VRAM)
   silently truncates prompt head (system msg + doc start). Test PDF is short → not caught. Fix: `options: {num_ctx: 8192}` or cut ~6k chars.
9. **CSV formula injection** — 04 esc(): khách hàng/ghi chú starting `= + - @` become formulas in Calc/Excel (Excel evals quoted).
   Prefix `'` for /^[=+\-@\t\r]/. Also reject NaN/negative sl/gia; round thành tiền (1.1*3 → 3.3000000000000003).
10. **cap-khoa recovery** — doc says revoke = delete user; re-running `them-may` then fails (pw file exists → signin 400); lost pw file +
    existing user → EMAIL_TAKEN. Fix: on signin failure reset pw via admin API / recreate; doc: also rm secrets/may-<ten>-webui.
    `them-may` now hard-dies when WebUI down → can't provision backup; make HOI lines optional + warn.
11. **/etc/onebee 0755** — may-tram.env (restic pw + rest creds) now protected only by file mode; admin pasting with umask 022 → 0644
    until installer runs (dir 0700 used to hide it). Keep dir 0700; move hoi.conf to /etc/onebee-hoi.conf (0644).

## LOW
12. `email-thu` sends fake "[OneBee Box] Sao lưu ĐẠT" (+ restic snapshots on every workstation repo) → indistinguishable from real
    success. Send trang_thai "THU" and render "Email thử" subject.
13. Webhook responds onReceived → SMTP failure only visible in n8n executions. nguong_gio 72 hard-coded in sao-luu.sh.j2:107;
    plan table row 2 still says "8:00 hằng ngày" (impl: 23:00 with backup).
14. Jinja into root bash double-quoted strings w/o quoting: onebee-box.sh.j2:278,299 (`smtp_user`, `nhan`), common.sh webui() admin
    email → use `| quote`.
15. ai-cli/tasks/main.yml:29-30 `regex_search(...)|first` crashes if HOI_API_KEY present but HOI_URL missing; hoi.conf stale if HOI removed.
16. hoi reads stdin whenever not a tty → hangs when launched with an open non-tty stdin (ssh/scripts). Read only if `-` arg or data ready.
17. credentials.json (SMTP pw, webhook key) persists plaintext in /opt/onebee-box/n8n-import (uid1000 0600; parent 0750 mitigates).
    Could delete after import once #5 stamp exists.
18. dong_bo_tro_ly `same` ignores access_grants/name/meta → drift not healed. check-ai-chat-inside.sh:77 password in curl argv (test only).
19. Docs: cai-dat-onebee-box.md:49 still "Dán 2 dòng RESTIC_" (now 4 lines). dung-tro-ly doc:50 "đã kiểm tự động trong container"
    — full box test not yet run with these changes. Doc: "đừng đổi mật khẩu quản trị/chủ n8n trên giao diện" (see #3).

## OK / no issue found
Ollama not published; webhooks header-auth (403 on wrong key), forms basic-auth; bcrypt `$2y$` in single-quoted .env (no compose
re-interpolation); timezone via workflow settings + GENERIC_TIMEZONE/TZ; bao_cao_n8n temp files/trap, header file 0600, key not in argv;
thresholds in summarize() match plan table (3 runs, ≥90%/≥85% per group, 0 bịa N5, 0 cam N1–2, ≤2% total, speed only on real Box).

## Đã xử lý (29/9 chiều)
- #1 test lấy cả dòng HOI_ + kiểm đủ 4 dòng. #2 `onebee-webui.py enforce_settings` đặt lại cài đặt quản trị mỗi lần chạy.
- #3 sai mật khẩu quản trị → mã 3 → cảnh báo, các role sau vẫn chạy; ghi hướng dẫn cập nhật file mật khẩu.
- #4 bộ cài máy trạm tự đổi `sao-luu.env` → `may-tram.env`; test mở rộng kịch bản nâng cấp v0.1.
- #5 dấu `.da-nhap-xong` — lỗi giữa chừng thì lần sau nhập lại. #6 ý cấm tiền tố `!` (bỏ qua sau từ phủ định),
  `re:` cho số nguyên vẹn, bỏ markdown, thêm cụm từ chối; 5 unit test mới. #7 lỗi từng câu → dòng lỗi, tải model dạng luồng.
- #8 cắt 8.000 ký tự + `num_ctx 8192`. #9 chống công thức CSV, kiểm số, làm tròn tiền.
- #10 `cap-khoa` tạo lại tài khoản khi lệch mật khẩu; `them-may` không chết khi Open WebUI tắt (chỉ in dòng sao lưu).
- #11 `/etc/onebee` giữ 0700; cấu hình hoi chuyển sang `/etc/onebee-hoi.conf` (0644).
- #12 `email-thu` gửi trạng thái THU, tiêu đề "Email thử", không đọc kho máy trạm. #14 `| quote` cho giá trị Jinja trong bash.
- #15 ai-cli cần đủ HOI_URL + HOI_API_KEY, gỡ cấu hình cũ khi mất khóa. #16 hoi không chờ stdin mãi (select 2 giây).
- #19 tài liệu: 4 dòng cấu hình, đổi mật khẩu quản trị, ghi đè quy trình khi nhập lại, lịch thuế + BHXH có nguồn.
- Chưa làm: #13 ngưỡng 72 giờ vẫn cố định; #17 credentials.json vẫn nằm trong n8n-import (0600, uid 1000); #18 giữ nguyên.

## Unresolved questions
- Any Phase-2 Box/workstation already deployed? (sets real severity of #2, #4)
- Ollama 0.34.4 default num_ctx on target Box hardware?
- n8n 2.40.7: does `N8N_INSTANCE_OWNER_MANAGED_BY_ENV` reset UI password changes on restart; does re-import keep published state?
- Set low temperature (e.g. 0.3) in preset + eval for stability (plan noted "lúc đúng lúc sai")?
- Hand-score ≥4/5 (N2–3) has no merge-back tool → who enforces before choosing model?
