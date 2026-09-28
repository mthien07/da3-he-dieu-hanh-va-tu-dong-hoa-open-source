# Code review — OneBee Box v0.1 + backup-client + fonts (28/9/2026)

Scope: `box/**`, `desktop/ansible/roles/backup-client`, fonts/xcd change, `tests/box`, `tests/desktop/extended`. Static review; box test not re-run (caller reports it passes). Paths relative to repo root; `CLI` = `box/ansible/roles/box-stack/templates/onebee-box.sh.j2`.

## CRITICAL / HIGH
1. **Backup can silently go to the system disk when the external disk is not mounted** — `CLI:48-52`. The check only tests `-d /mnt/onebee-sao-luu`, and that mountpoint dir must exist for fstab anyway. If the disk is unplugged or the mount failed, `restic init` creates a NEW repo on `/`: it fills the root disk and gives false "backup OK". The same-device check at `:49` only warns. Fix: `mountpoint -q "$(dirname "$BACKUP_REPO")" || die ...`. Never `restic init` automatically in the timer path; init only in `khoi-phuc-thu` or an explicit `khoi-tao` command. Docs step 5 should give an fstab line with `nofail,x-systemd.device-timeout=10s`. Without `nofail`, a missing disk leaves a headless server in emergency mode at boot, and with `nofail` bug #1 bites.
2. **The Box backup cannot be restored if the Box disk dies** — `CLI:47`. The `restic-box` password exists only in `/etc/onebee-box/secrets`, on the Box disk. A copy sits *inside* the encrypted backup, which you cannot open without that password. The workstation repo passwords and the n8n key are in the same place. Fix: add a `onebee-box khoa-khoi-phuc` command that prints the restic-box password and N8N_ENCRYPTION_KEY. Docs should say to print them and store them offline; the installer's final message should remind the admin. Also write a disaster-recovery runbook (reinstall → put secrets back → `restic restore` → `compose up`). Only one test file is exercised today.
3. **The append-only "chống ransomware" claim can be defeated by forged snapshot times** — `CLI:65-70`. An attacker with the workstation credentials (they are in `sao-luu.env`) can run `restic backup --time <future dates>` about 17 times with the same host and paths. The Box's nightly `forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune` then keeps the fakes and prunes every real snapshot. This is the known restic append-only caveat. Fix: before forgetting, skip the repo and alert if any snapshot has `time > now+1d` or an abnormal count, e.g. `restic snapshots --json | python3 ...`. Add `--keep-within 30d` as a floor. Consider not auto-pruning workstation repos in v0.1, since disk growth is the cheaper risk.
4. **A pause error can leave services frozen indefinitely** — `CLI:55-56`. The trap is installed *after* `compose pause`. If `pause` fails partway (a service is stopped or crashed), `set -e` exits with some containers paused and no unpause. Fix: set the trap before the pause. The unpause should also run on ERR/INT/TERM.

## MEDIUM
5. **Services stay paused for the whole backup, including the Samba share** — `CLI:58`. The first backup of a large `chung` share can take hours, and AI/n8n/Uptime Kuma are frozen the whole time; monitoring is blind and n8n schedules are missed. `IOSchedulingClass=idle` + `Nice=10` (`box-backup/templates/onebee-box-sao-luu.service.j2:10-11`) makes the pause even longer under load. Fix: run 2 backups. Run pause → backup of the DB dirs (`open-webui`, `n8n`, `uptime-kuma`, `BOX_DIR`, `SECRETS`) → unpause, then back up `chung` with the services running. Drop `idle` IO, or apply it only to the second phase.
6. **One failing workstation repo stops all later pruning, and the failure is silent** — `CLI:62,69`. The script uses `set -e`. A workstation doing a catch-up backup at 23:00 makes `forget --prune` fail with "already locked", which aborts the remaining repos and marks the unit failed. Nobody is notified: there is no OnFailure or Uptime Kuma push, and a missing disk also fails every night without anyone seeing it. Fix: `--retry-lock 10m`, `|| { warn; rc=1; continue; }` per repo, `flock /run/onebee-box-sao-luu.lock` for the whole command (the timer and a manual `sao-luu`/`khoi-phuc-thu` can currently run concurrently and fight over pause/lock). Add `OnFailure=` or an Uptime Kuma push monitor.
7. **`docker.io` conflicts with an existing `docker-ce`** — `box/ansible/roles/docker/tasks/main.yml:6`. Real servers often already have docker-ce/containerd.io, and apt will either fail or remove them. Fix: pre-check `dpkg -s docker-ce` and skip installing docker.io, or `die` with a clear message in the bootstrap.
8. **The printed IP can be wrong** — `CLI:26,41` and `onebee-box-install.sh:43`. `hostname -I | awk '{print $1}'` can pick a docker bridge, Tailscale 100.x or IPv6 address, which yields a broken or unreachable `RESTIC_REPOSITORY`. The IP is also baked in, so a DHCP change breaks every workstation. Fix: use `ip -4 route get 1.1.1.1 | awk '/src/{for(i=1;i<NF;i++) if($i=="src") print $(i+1)}'`, or make it overridable via a `onebee_box_host` var (hostname/mDNS preferred).
9. **Network exposure** — `docker-compose.yml.j2:9,27,44,61,69`. Ports are published on `0.0.0.0` and `[::]` and bypass ufw (the ADR acknowledges this). Open WebUI, n8n and Uptime Kuma all use "first visitor becomes admin", so anyone on the LAN (or guest Wi-Fi) who opens them before the admin takes over. Fix: add an `onebee_box_bind_ip` var in the port mappings. The installer should warn loudly, or the playbook should pre-create the admins, and docs should say "làm ngay".
10. **No docker log rotation** (json-file defaults to unbounded). On a 24/7 box the root disk fills slowly. Fix: `/etc/docker/daemon.json` with `log-opts max-size=10m,max-file=3`, or a `logging:` anchor in compose.
11. **Workstation backups share the data disk with no quota** (`/srv/onebee/restic`). One workstation, or a compromised one appending junk, can fill `/srv` and break the n8n/Open WebUI DBs and Samba. Fix: a separate LV or disk for `restic`, or at least a disk-usage alert in `trang-thai` and Uptime Kuma.

## LOW
12. `CLI:39`: `htpasswd -B -b ... "$http_pw"` puts the password in argv (visible in `ps`). Use `htpasswd -B -i` with stdin. `2>/dev/null` also hides the real error.
13. `box-stack/tasks/main.yml:18`: n8n data is owned by uid 1000, which on Ubuntu is the first human admin. That non-root user can read n8n credentials and config. Acceptable, but document it, or chown to a dedicated uid via `user:` in compose.
14. `samba/tasks/main.yml:34`: no `hosts allow` / `interfaces`, so smbd listens on the docker bridges and VPN too. A single shared account gives no per-person audit (fine for v0.1; document it).
15. `box-base/tasks/main.yml:14`: timezone set via symlink only, so `/etc/timezone` is stale. Prefer `timedatectl set-timezone`, or `community.general.timezone` if that collection is available.
16. `CLI:52`: `restic cat config || restic init` treats any error (lock, wrong password, I/O) as "no repo". For a local repo, test `[ -f "$BACKUP_REPO/config" ]`.
17. `tests/desktop/run-desktop-extended-tests.sh:103`: `check-libreoffice... | grep FAIL || echo PASS` prints PASS if the python script crashes without printing "FAIL".
18. The box test uses the **slim** Open WebUI image by default (`run-box-...sh:82`), while production uses the full image with `OFFLINE_MODE=true`, so the production image path is not covered by default. README "✅ bộ cài chạy thật" vs the guide's "Chưa kiểm trên máy thật": keep wording consistent (container-verified only).

## OK / verified by reading
- Secrets: the `password` lookup writes 0600 files in a 0700 dir; `.env` is 0600 with `no_log`; the Samba password is `no_log`. restic redacts the password in `rest:` URLs in its logs. No docker.sock mounted anywhere. Ollama is not published.
- The `RETURN` trap in `khoi-phuc-thu` works as intended (checked in bash). rest-server `--private-repos` + htpasswd kept outside the user paths is fine.
- backup-client: the env is sourced only after the file is forced to root 0600. Timer is Persistent. The 12:00 client vs 23:00 box schedule mostly avoids lock clashes (see #6 for catch-up runs).
- The fontconfig 29- rule and the LO FontPairs are correct; the test asserts exactly 4 fonts in the PDF.

## Unresolved questions
- Does `restic/rest-server:0.14.0` run as root? `forget --prune` runs as root on the host and writes new index/pack files owned by root with mode 0400/0600. If the image runs as non-root, the next workstation backup would fail. The test never runs a workstation backup *after* the Box prune; add that step.
- Should the Box be allowed to read every workstation's `/home` (it holds all repo passwords)? That is a privacy and design decision to state explicitly in ADR 0002.
- Is the full Open WebUI image + `OFFLINE_MODE` RAG/embedding behaviour acceptable for Phase 3?


## Đã xử lý (28/9)
- H1: `mountpoint -q` bắt buộc; `restic init` chỉ ở `onebee-box khoi-tao`; hướng dẫn fstab `nofail`. Test: umount → từ chối, không ghi `/`.
- H2: `onebee-box in-khoa` + mục "Khôi phục toàn bộ" trong hướng dẫn (chưa diễn tập máy thật).
- H3: `--keep-within 30d` cho kho máy trạm + bỏ qua kho có bản ngày tương lai (CẢNH BÁO). Test: bản `--time 2031` → không dọn.
- H4: trap unpause đặt trước pause; pause/unpause lỗi → dừng có thông báo.
- M5: 2 lượt (csdl khi tạm dừng, chung sau khi chạy lại). M6: tiếp tục từng kho + `--retry-lock 5m` + flock (chưa có cảnh báo tự động — ghi giới hạn).
- M7: có docker-ce thì bỏ qua docker.io. M8: IP từ `ip route get` + biến `onebee_box_address`.
- M9: ghi rõ trong hướng dẫn/ADR (chưa tự tạo tài khoản quản trị). M10: log json-file 3×10MB. M11: ghi giới hạn.
- Low: `htpasswd -i`; `hosts allow`; `/etc/timezone`; test UNO trên Ubuntu không còn PASS giả; README "chạy được".
- Q1 (rest-server sau khi Box dọn): test thêm — máy trạm vẫn sao lưu được. Q2: ghi quyền riêng tư vào ADR 0002.
