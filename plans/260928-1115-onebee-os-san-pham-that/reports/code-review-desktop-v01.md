# Code review — OneBee OS Desktop v0.1 (uncommitted changes)

Date: 2026-09-28 · Scope: desktop/, tests/desktop/, .github/workflows/ci.yml, docs claims.
Local: shellcheck, yamllint, ansible-lint (production profile) all pass. Two HIGH bugs below were **reproduced in linuxmintd/mint22.3-amd64**. Container tests pass only because they check the wrong layer.

## HIGH

**H1. IBus preload-engines never reaches the IBus panel → Bamboo not preloaded on real desktop**
- `roles/vietnamese/tasks/main.yml:29-39` writes `/etc/dconf/db/ibus.d/10-onebee`. That db is only in dconf profile `ibus`, which only `ibus-dconf` uses (ibus 1.5.29 `conf/dconf/main.c:75` sets DCONF_PROFILE=ibus for itself only).
- The panel (`ui/gtk3/panel.vala:186,630`) reads `GLib.Settings("org.freedesktop.ibus.general")` under the user's default profile (`user-db:user` only).
- Reproduced: `DCONF_PROFILE=ibus dconf read …` → `['BambooUs','Bamboo']`, but `gsettings get org.freedesktop.ibus.general preload-engines` → `@as []`. With an empty list the panel picks engines from xkb + locale. So the OneBee setting does nothing: an English-locale user gets only the US layout.
- The test `verify-desktop-install.sh:26-27` queries with DCONF_PROFILE=ibus, so it gives a false PASS.
- Fix: add a gschema override (see H2 for naming): `[org.freedesktop.ibus.general]` `preload-engines=['xkb:us::eng','Bamboo']` (or BambooUs), then run glib-compile-schemas. Change the test to `GSETTINGS_BACKEND=memory gsettings get org.freedesktop.ibus.general preload-engines | grep -q Bamboo`. The ibus.d file can stay, but it is optional.
- Note: users who already have preload-engines in their own dconf keep their value, whichever method you use (see Q1).

**H2. Wallpaper override is outranked by Mint's own override → Mint wallpaper stays**
- `roles/theme/tasks/main.yml:28` uses the name `90_onebee.gschema.override`. glib-compile-schemas applies overrides in lexicographic order and the later file wins. `mint-artwork.gschema.override` (package mint-artwork 1.9.3, on every real Mint install) sets `[org.cinnamon.desktop.background] picture-uri=…/linuxmint/default_background.jpg`. Since "m" sorts after "9", Mint wins.
- Reproduced: after installing mint-artwork plus the 90_onebee override and compiling, `gsettings get` returns `file:///usr/share/backgrounds/linuxmint/default_background.jpg`.
- The container test skips mint-artwork (`run-desktop-test-in-mint-container.sh:21`), so it gives a false PASS.
- Fix: rename to `zz_onebee.gschema.override` (sorts after "mint-artwork"), have the task remove any old `90_onebee.gschema.override`, and add `mint-artwork` to the test's apt-get install line.
- Note: users who already changed their wallpaper keep it. That is expected, but the docs should say so.

## MEDIUM

**M1. Supply chain: third-party PPA + unattended full upgrades = automatic root for the PPA owner.**
- `ibus-bamboo.yml:5-13` adds the PPA for all packages. `mintupdate.yml` then enables daily automatic upgrades of everything. A compromised or rogue PPA upload (any package name, e.g. a fake `libc6`) gets installed as root on every OneBee machine without anyone noticing.
- The key is pinned and its fingerprint matches (5AD2…D014 verified with gpg). That part is good.
- Fix: add `/etc/apt/preferences.d/onebee-ibus-bamboo` with `Package: *` / `Pin: release o=LP-PPA-bamboo-engine-ibus-bamboo` / `Pin-Priority: -1`, plus a second stanza that allows only `ibus-bamboo` at priority 500. Check the origin string against the PPA's Release file.

**M2. Test suite asserts the wrong layer for the desktop-facing features (H1, H2).**
- The docs and changelog claim "30 mục kiểm tra" and the README says "chạy thật, đã kiểm tự động". Two of those 30 checks are false positives. Fix them as described in H1 and H2.
- Also run gsettings with the default dconf profile, not the memory backend, wherever a check needs system-db semantics.

**M3. Bootstrap apt has no lock wait.** `onebee-install.sh:40-41`: on a freshly installed Mint, mintupdate/apt-daily often hold the dpkg lock at first login, and `apt-get` fails at once. Fix: `apt-get -o DPkg::Lock::Timeout=600 …`. Also set `lock_timeout: 600` on the apt tasks, or raise it via a module default in site.yml (the default is 60 s).

**M4. `/etc/default/locale` is overwritten whole (`base/tasks/main.yml:24-32`).** This drops any LC_* or LANGUAGE lines the installer or admin wrote (for example LC_TIME or LC_PAPER=vi_VN). Fix: use `lineinfile` with regexp `^LANG=`, or also manage `LANGUAGE=vi:en`. Existing users with an AccountsService `Language=` entry (`/var/lib/AccountsService/users/*`) keep their session language, so "Hệ thống tiếng Việt" is not guaranteed on a machine installed in English (see Q2).

## LOW

- **L1.** `mintupdate.yml:24-31` only runs `systemctl enable`. `mintupdate-automation` also runs `start`, so on a live system the timers stay inactive until reboot, and log-out (what the docs suggest) does not start them. Fix: add a `systemctl start` task when `ansible_service_mgr == 'systemd'`, or tell the docs to say "khởi động lại".
- **L2.** `verify-desktop-install.sh:19-22` always requires `ibus-bamboo` and checks `grep Bamboo`. With `onebee_input_method: unikey` (documented in the guide §5) verify FAILs. Fix: branch on the installed package or on a variable.
- **L3.** `onebee-install.sh:38` skips the install if any `ansible-playbook` already exists (pip or pipx, an old version). `deb822_repository` needs ≥2.15, and python3-apt is installed only in that same branch. Fix: always `apt-get install ansible-core python3-apt` (idempotent), or check the version.
- **L4.** `office/files/onebee-office-defaults.xcd:5-8` depends on writer, calc and impress. If any one of those LO modules is removed later, configmgr skips the whole xcd silently and all defaults are lost. Acceptable; add a note to the docs.
- **L5.** `tests/desktop/__pycache__/*.pyc` is untracked and not ignored, so it will be committed with `git add tests/`. Add `__pycache__/` to .gitignore.
- **L6.** CI: `pip install ansible-core ansible-lint yamllint` is unpinned and the actions are pinned by tag, not SHA. A new release can break lint. Pin versions (requirements file).
- **L7.** The Ubuntu-noble fallback path installs `firefox-locale-vi` (a snap transitional package in Ubuntu universe). It is untested and may pull the snap. The code already warns about this; the docs call it Mint-only. OK for v0.1.

## Verified OK
- Root check, OS/arch check, `set -euo pipefail` + PIPESTATUS handling.
- The explicit ANSIBLE_CONFIG avoids the world-writable-cwd config lookup.
- PPA key fingerprint matches the comment.
- xcd `oor:op="fuse"` + dependencies load correctly (UNO test).
- Idempotency of the locale, timezone, systemctl `creates:`, touchfile `force:false`, and dconf/fc-cache handlers.
- BambooUs/Bamboo engine names exist in upstream bamboo.xml.
- Docs "30 mục" count matches the script.

## Unresolved questions
- Q1: Should OneBee force IBus engines and wallpaper for **existing** users, via a per-user `gsettings set` at first login (an `/etc/xdg/autostart` one-shot)? A system override only affects users who never changed the key.
- Q2: Target machines: always a fresh install in Vietnamese (as the guide §2 says), or retrofit onto existing English Mint installs? That decides whether M4 and Q1 matter.
- Q3: IBus default hotkey Super+Space on Cinnamon: does it conflict with Cinnamon keybindings or the menu's Super key? This needs a real VM test.
- Q4: Default engine order: should `xkb:us::eng` come first, not `BambooUs`? BambooUs is a Bamboo engine in English mode, and the language indicator may confuse users.

## Đã xử lý (28/9, sau review)
- H1: bộ gõ đặt qua gschema override `zz_onebee-ibus` ([org.freedesktop.ibus.general]); test đọc qua gsettings. Bỏ file dconf ibus.d.
- H2: đổi tên `zz_onebee-theme.gschema.override`; test cài thêm mint-artwork → PASS thật.
- M1: apt pin — PPA chỉ cấp `ibus-bamboo` (500), mọi gói khác -1; có test.
- M2: số mục kiểm tra cập nhật (31 + 4 UNO). M3: DPkg::Lock::Timeout=600 + apt lock_timeout 600 (module_defaults).
- M4: `lineinfile ^LANG=`, giữ LC_*. L1: start timer khi /run/systemd/system tồn tại; docs nói khởi động lại.
- L2: verify tự nhận bamboo/unikey. L3: kiểm tra gói ansible-core + python3-apt bằng dpkg. L5: .gitignore __pycache__. L6: requirements-dev.txt ghim phiên bản.
- L4: ghi vào hướng dẫn (giới hạn). L7: chấp nhận cho v0.1 (chỉ hỗ trợ chính thức Mint).
- Q1–Q4: còn mở — cần thử trên VM Mint thật.
