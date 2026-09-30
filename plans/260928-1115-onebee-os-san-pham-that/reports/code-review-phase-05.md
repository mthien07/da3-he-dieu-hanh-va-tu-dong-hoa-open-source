# Code review — Phase 05 (feat/phase-05-chuan-bi-chay-thu)

Scope: `git diff main...HEAD` + uncommitted diff. Docker not touched.

## Verified OK
- **Jinja scoping (the main risk):** rendered all 9 workflows with the real `ansible.builtin.template` module (ansible-core 2.19.13).
  The `{% set email_tu_nut/email_bo_qua_loi %}` before the include does reach `_gui-email.json.j2`.
  01, 02 and 05 still render `$json.subject` / `$json.text` with no `onError`. Their parsed JSON is **identical to main**; only the indentation changed.
  07 renders `$('Tạo yêu cầu').first().json.*` plus `"onError": "continueRegularOutput"`.
- All rendered JSON is valid, every connection points to an existing node, and webhookIds and paths are unique (0001–0009).
- n8n semantics look right:
  - The dropdown `fieldOptions.values[].option` format is the same as in 03, which already passes testing.
  - `responseMode: lastNode` with a Form completion node follows the same pattern as 04.
  - `onError` is set at node level.
  - The completion node reads from `$('Tạo yêu cầu')`, so it does not depend on the email node's output.
  - readWriteFile with `append` opens the file with flag `a` and creates it if missing. `ho-tro` (uid 1000, 0700) is under `~/.n8n-files`.
- CSV: I ran the rendered `_csv-js` through node and read the output back with Python `csv`. Quotes, CRLF, a lone CR, commas and `= + - @` prefixes all came back correctly.
  The `'` formula prefix never touches the code, the timestamp, the scores or the minutes, because they all start with a digit.
- Week boundary: the Box and n8n both run in Asia/Ho_Chi_Minh, so the naive-local Monday–Sunday window is consistent.
- `sed -n '2,14p'` help range is correct. The unit tests pass (4/4).
- Upgrade note: 01–06 change on disk because of whitespace, so the template task reports changed and everything is re-imported. That would happen anyway because 07–09 are new. UI edits to 01–06 are overwritten, as already documented.

## Findings (ranked)

### M1 — Report prints free-text "dropdown" values → privacy and table breakage
`07-yeu-cau-ho-tro.json.j2:8` (`j.loai`), `08-xu-ly-yeu-cau.json.j2:9` (`j.cach_xu_ly`), `onebee-bao-cao-tuan.py:69,77-79`.
n8n does not enforce dropdown options on the server. The integration test relies on this itself: it posts `field-0=5` even though the option is "5 — Rất đồng ý".
- **Scenario:** a POST to `/form/onebee-ho-tro` with `field-1=Chị Lan 0909… | lương` (curl or devtools, using the shared `nhanvien` password). The text appears verbatim in the report's "Loại" table, and the `|` breaks the Markdown table. I reproduced this locally.
- **Fix:** in the Code nodes, whitelist the value against `{{ onebee_ho_tro_loai | to_json }}` / `{{ onebee_ho_tro_cach_xu_ly | to_json }}`, then throw or map it to "Khác". In the report, print only known labels and fold anything else into "Khác".

### M2 — Typo/unknown request codes count as "Xử lý xong"
`08-xu-ly-yeu-cau.json.j2:6` (format check only) and `onebee-bao-cao-tuan.py:58,65,77`.
- **Scenario:** the technician types `261005-080000-21` instead of `-12`. The report shows "Xử lý xong: 1" while the real request is still listed under "Còn mở", and "xong" can end up larger than "mới".
- **Fix (Python, simplest):** limit `xong_tuan`, `cach` and `phut` to codes that exist in `yeu_cau`, and print the count of unknown codes as a data-quality line. Optionally, have 08 read `yeu-cau.csv` and reject unknown codes.

### M3 — Resolution-time and effort stats are wrong
`onebee-bao-cao-tuan.py:55-56,70-72`.
- The "Từ lúc báo đến lúc xong" figure includes codes whose last record is "Chưa xử lý được". In my run an unresolved request contributed 98 h as its "done" time.
- `xu_ly` keeps only the last record per code, so "Công xử lý" drops earlier attempts. In my run, 60 min "Chưa xử lý được" followed by 30 min gave a total of 30.
- **Fix:** exclude `"Chưa xử lý được"` from `cho`. For minutes, sum every xu-ly record whose timestamp is in the week, and use the last record only for status.

### M4 — Email failure is silent and the user is told the technician was notified
`07-yeu-cau-ho-tro.json.j2:27` together with `_gui-email` `onError: continueRegularOutput`.
- **Scenario:** SMTP is down or not configured. The execution still counts as a success and the user sees "Kỹ thuật OneBee sẽ liên hệ". A GẤP request goes unnoticed until the weekly report.
- Also, the form response waits for the SMTP attempt, which can take up to about 2 minutes on nodemailer's default timeouts when the host is unreachable.
- **Fix:** make the completion message conditional, for example `$('Gửi email').first().json.error ? '… Email cho kỹ thuật CHƯA gửi được — hãy gọi điện.' : '…'`. Consider setting a short SMTP timeout.

### L1 — Survey threshold vs. week windows and repeated runs
`onebee-bao-cao-tuan.py:83-95`, `chay-thu-tai-don-vi.md:41`.
- The survey link goes out at the end of week 2 and week 4. If replies straddle Sunday, each week can end up with fewer than 3 replies, and the scores are never shown.
- The report can be run mid-week. If it is run at 3 replies and again at 4, the difference reveals the 4th person's exact scores.
- **Fix:** show scores only for completed weeks, or aggregate by survey round or date range, and note this in the docs.

### L2 — Impossible dates crash the report
`onebee-box.sh.j2:59` and `onebee-bao-cao-tuan.py:114`: `2026-02-30` passes the regex and then raises a Python `ValueError` traceback.
- **Fix:** validate with `date -d "${ngay}" +%F`, or wrap `fromisoformat` and exit with a Vietnamese message.

### L3 — Label coupling across three places
`vars/main.yml`, `09-…j2` (`cau`), `onebee-bao-cao-tuan.py:25,59,80`.
- The report matches exact strings: "Chưa xử lý được", "Quay về Windows (máy/phần mềm)", and the survey question order.
- **Scenario:** renaming a label in vars silently sets "Phải quay về Windows" to 0, or treats every request as resolved.
- **Fix:** add a unit test that loads `vars/main.yml` and asserts the constants, or pass the labels to the script.

### L4 — Raw form payloads persist in n8n execution history
07, 08 and 09 (settings).
- By default n8n saves successful executions for about 14 days, and they are also in the restic backup of `data/n8n`. That history includes the reporter's name, the description and the survey comment with an exact timestamp, visible in the n8n UI.
- **Fix:** set `"saveDataSuccessExecution": "none"` in the settings of 07, 08 and 09. The CSV is already the record.

### L5 — Integration test is not re-runnable on the same Box
`tests/box/check-n8n-inside.sh:84-88`: it checks absolute counts (`wc -l == 1/3`, `**1**`). This is the same pattern as the existing 04 test, so it is fine for a fresh container. The `sleep 3` calls are redundant, because a `lastNode` POST is synchronous.

### L6 — Hard-coded `:5678` and `<ip-box>`
- `quan-ly-tap-trung/tasks/main.yml:167`: the desktop launcher hard-codes `:5678`, but `onebee_box_ports.n8n` can be configured. The port could be derived from `TINH_TRANG_URL`, which already includes it.
- The email text in 07 shows a literal `http://<ip-box>:5678/…`, even though `onebee_box_address` / `WEBHOOK_URL` are known when the template is rendered.

### L7 — Cosmetic
- The trailing newline of `_csv-js.j2` is stripped, which produces `…});// Nhân viên…` on one line. The JS is still valid.
- In 07 the node x-positions (360 → 480 → 720) are uneven.
- The changelog still contains the placeholder `KẾT_QUẢ_BOX_05`.
