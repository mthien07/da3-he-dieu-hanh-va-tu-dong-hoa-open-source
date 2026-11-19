#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dương Minh Thiện, HTX OneBee
# Phòng ban + máy trạm xin vào Box (gọi từ run-box-test-in-systemd-container.sh): $1 = container Box, $2 = container máy trạm Mint.
# Kiểm: thư mục riêng từng phòng (phòng khác không vào được, không thấy trong danh sách) → máy trạm xin vào qua LAN (cổng 80),
# mã đối chiếu hai bên trùng nhau → duyệt → máy nhận cấu hình có phòng (giải mã được, vân tay CA đúng) → từ chối trả lý do
# → sao lưu Box có bản riêng từng phòng, khôi phục riêng một phòng → chạy lại dong-bo-phong không đổi gì.
set -euo pipefail
BOX="$1"; CLIENT="$2"
box() { docker exec "${BOX}" bash -euo pipefail -c "$1"; }
may() { docker exec "${CLIENT}" bash -euo pipefail -c "$1"; }
BOX_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${BOX}")"

echo "===== PHÒNG BAN: THƯ MỤC RIÊNG, PHÒNG KHÁC KHÔNG VÀO ĐƯỢC, KHÔNG THẤY ====="
box 'onebee-box them-phong ke-toan "Phòng Kế toán" gnucash >/dev/null
     onebee-box them-phong kho "Kho vận" >/dev/null
     if onebee-box dong-bo-phong | grep -q DA_DOI; then echo "FAIL  dong-bo-phong chạy lại vẫn đổi cấu hình"; exit 1; fi
     [ "$(stat -c "%a %G" /srv/onebee/phong-ban/ke-toan)" = "2770 pb-ke-toan" ] || { echo "FAIL  Thư mục phòng sai quyền"; exit 1; }
     testparm -s >/dev/null 2>&1 || { echo "FAIL  smb.conf lỗi sau khi thêm phòng"; exit 1; }
     mk="$(cat /etc/onebee-box/secrets/phong-ke-toan-samba)"
     echo "Sổ sách quý III" > /root/so-sach.txt
     smbclient //127.0.0.1/pb-ke-toan -U "pb-ke-toan%${mk}" -m SMB3 -c "put /root/so-sach.txt so-sach.txt" >/dev/null 2>&1 \
       || { echo "FAIL  Tài khoản phòng Kế toán không ghi được vào thư mục của phòng"; exit 1; }
     if smbclient //127.0.0.1/pb-kho -U "pb-ke-toan%${mk}" -m SMB3 -c ls >/dev/null 2>&1; then
       echo "FAIL  Phòng Kế toán vào được thư mục phòng Kho"; exit 1; fi
     ds="$(smbclient -L 127.0.0.1 -U "pb-ke-toan%${mk}" -m SMB3 2>/dev/null)"
     grep -q "pb-ke-toan" <<<"${ds}" && ! grep -q "pb-kho" <<<"${ds}" \
       || { echo "FAIL  Danh sách chia sẻ của phòng Kế toán vẫn thấy phòng Kho"; exit 1; }
     mkc="$(cat /etc/onebee-box/secrets/samba-onebee 2>/dev/null || true)"
     if [ -n "${mkc}" ] && smbclient //127.0.0.1/pb-ke-toan -U "onebee%${mkc}" -m SMB3 -c ls >/dev/null 2>&1; then
       echo "FAIL  Tài khoản thư mục chung vào được thư mục riêng của phòng"; exit 1; fi
     systemctl is-active -q onebee-xin-vao.path || { echo "FAIL  Chưa bật dịch vụ nhận yêu cầu xin vào"; exit 1; }
     echo "PASS  Phòng ban: mỗi phòng một thư mục riêng; phòng khác và tài khoản chung không vào được, không thấy trong danh sách"'

echo "===== MÁY TRẠM XIN VÀO → DUYỆT → NHẬN CẤU HÌNH CÓ PHÒNG ====="
# Chạy lệnh xin vào thật trên máy Mint (gốc tạm để không đè cấu hình của máy ketoan-01 đã cài ở trên)
# Người ngồi máy trạm gõ lại mã thấy trên Box: đưa vào qua ống có tên (mở đọc-ghi để lệnh không bị chặn lúc khởi chạy)
may 'rm -rf /tmp/xv /tmp/xv.log /tmp/xv.ma && mkfifo /tmp/xv.ma'
docker exec -d -e PYTHONUNBUFFERED=1 -e ONEBEE_XIN_VAO_GOC=/tmp/xv -e ONEBEE_XIN_VAO_CHU_KY=1 "${CLIENT}" bash -c \
  "exec 3<>/tmp/xv.ma; /root/onebee-test/desktop/onebee-xin-vao --box ${BOX_IP} --ten kt-02 --phong ke-toan --cho 5 --khong-cai <&3 > /tmp/xv.log 2>&1; echo \"MA_THOAT=\$?\" >> /tmp/xv.log"
id=""; for _ in $(seq 60); do
  id="$(box 'python3 - <<"PY"
import glob, json
for t in glob.glob("/srv/onebee/xin-vao/*.json"):
    if t.endswith((".duyet.json", ".tu-choi.json")): continue
    d = json.load(open(t))
    if d.get("ten") == "kt-02" and d.get("ma_so"): print(d["id"], d["ma_so"])
PY')"; [ -n "${id}" ] && break; sleep 1
done
[ -n "${id}" ] || { echo "FAIL  Box không nhận được yêu cầu xin vào của máy kt-02"; may 'cat /tmp/xv.log' || true; exit 1; }
ma_box="${id#* }"; id="${id%% *}"
ma_may="$(may "grep -oE 'MÃ ĐỐI CHIẾU: +[0-9]{3} [0-9]{3}' /tmp/xv.log | grep -oE '[0-9]{3} [0-9]{3}' | tr -d ' '")"
[ "${ma_may}" = "${ma_box}" ] || { echo "FAIL  Mã đối chiếu máy trạm (${ma_may}) khác mã Box (${ma_box})"; exit 1; }
echo "PASS  Máy trạm tìm thấy Box qua LAN, gửi yêu cầu; mã đối chiếu hai bên trùng nhau (${ma_box})"
# Ghi vào ống có tên chỉ xong khi lệnh xin vào còn đang đọc → giới hạn thời gian, không treo khi lệnh đã thoát
may "timeout 10 bash -c 'echo \"${ma_box:0:3} ${ma_box:3}\" > /tmp/xv.ma'" || { echo "FAIL  Lệnh xin vào đã thoát trước khi hỏi mã"; may 'cat /tmp/xv.log'; exit 1; }
box "onebee-box xin-vao | grep -q kt-02 && onebee-box duyet-may ${id} ke-toan </dev/null >/dev/null"
for _ in $(seq 30); do may 'grep -q "^MA_THOAT=" /tmp/xv.log' && break; sleep 1; done
may 'grep -q "^MA_THOAT=0$" /tmp/xv.log || { echo "FAIL  Lệnh xin vào không thành công"; cat /tmp/xv.log; exit 1; }
     f=/tmp/xv/etc/onebee/may-tram.env
     [ "$(stat -c %a "${f}")" = 600 ] || { echo "FAIL  Cấu hình nhận về không khóa quyền 600"; exit 1; }
     grep -qx "MAY_TRAM=kt-02" "${f}" && grep -qx "PHONG_BAN=ke-toan" "${f}" && grep -qx "SAMBA_PHONG_USER=pb-ke-toan" "${f}" \
       && grep -q "^RESTIC_PASSWORD=." "${f}" && grep -q "^BOX_CA_VAN_TAY=[0-9a-f]\{64\}$" "${f}" \
       || { echo "FAIL  Cấu hình nhận về thiếu dòng (máy, phòng, Samba phòng, sao lưu, vân tay CA)"; sed "s/=.*/=***/" "${f}"; exit 1; }'
# So băm (không in mật khẩu); bỏ dấu xuống dòng hai phía — tệp bí mật trên Box không có dòng mới ở cuối
mk_may="$(may "grep -oP '^SAMBA_PHONG_PASS=\K.*' /tmp/xv/etc/onebee/may-tram.env | tr -d '\n' | sha256sum")"
mk_box="$(box "tr -d '\n' < /etc/onebee-box/secrets/phong-ke-toan-samba | sha256sum")"
[ "${mk_may}" = "${mk_box}" ] || { echo "FAIL  Mật khẩu Samba phòng trên máy khác bản Box giữ"; exit 1; }
box '[ -f /srv/onebee/phong-ban-so/may/kt-02 ] && [ "$(cat /srv/onebee/phong-ban-so/may/kt-02)" = ke-toan ] \
       || { echo "FAIL  Box chưa ghi máy kt-02 vào phòng Kế toán"; exit 1; }'
may 'grep -q "^XIN_VAO_" /tmp/xv/etc/onebee/may-tram.env && { echo "FAIL  Dòng ký xin vào lọt vào cấu hình máy"; exit 1; } || true'
echo "PASS  Duyệt → Box cấp khóa, máy trạm kiểm chữ ký của Box và giải mã được cấu hình (phòng Kế toán, mật khẩu Samba của phòng)"
# kt-02 chỉ nhận cấu hình vào thư mục tạm, không cài thật (không bao giờ nhận CA) → thu hồi để các phần sau (chốt chặn bật HTTPS) không vướng
box 'onebee-box thu-hoi-may kt-02 --dong-y >/dev/null; [ ! -e /srv/onebee/phong-ban-so/may/kt-02 ] || { echo "FAIL  Thu hồi chưa gỡ máy khỏi phòng"; exit 1; }'

echo "===== TỪ CHỐI MÁY XIN VÀO ====="
may 'rm -rf /tmp/xv2 /tmp/xv2.log /tmp/xv2.ma && mkfifo /tmp/xv2.ma'
docker exec -d -e PYTHONUNBUFFERED=1 -e ONEBEE_XIN_VAO_GOC=/tmp/xv2 -e ONEBEE_XIN_VAO_CHU_KY=1 "${CLIENT}" bash -c \
  "exec 3<>/tmp/xv2.ma; /root/onebee-test/desktop/onebee-xin-vao --box ${BOX_IP} --ten la-01 --cho 5 --khong-cai <&3 > /tmp/xv2.log 2>&1; echo \"MA_THOAT=\$?\" >> /tmp/xv2.log"
id2=""; for _ in $(seq 60); do
  id2="$(box "grep -l '\"ten\": *\"la-01\"' /srv/onebee/xin-vao/*.json 2>/dev/null | head -1 | xargs -r basename | cut -c1-32" || true)"
  [ -n "${id2}" ] && break; sleep 1
done
[ -n "${id2}" ] || { echo "FAIL  Box không nhận được yêu cầu của máy la-01"; exit 1; }
for _ in $(seq 30); do may 'grep -qE "MÃ ĐỐI CHIẾU: +[0-9]{3} [0-9]{3}" /tmp/xv2.log' && break; sleep 1; done
may 'ma="$(grep -oE "MÃ ĐỐI CHIẾU: +[0-9]{3} [0-9]{3}" /tmp/xv2.log | grep -oE "[0-9]{3} [0-9]{3}")" \
       && timeout 10 bash -c "echo \"${ma}\" > /tmp/xv2.ma"' || { echo "FAIL  Máy la-01 không hiện mã đối chiếu"; may 'cat /tmp/xv2.log'; exit 1; }
box "onebee-box tu-choi-may ${id2} Máy không thuộc đơn vị >/dev/null"
for _ in $(seq 30); do may 'grep -q "^MA_THOAT=" /tmp/xv2.log' && break; sleep 1; done
may 'grep -q "^MA_THOAT=1$" /tmp/xv2.log && grep -q "Máy không thuộc đơn vị" /tmp/xv2.log \
       || { echo "FAIL  Máy bị từ chối mà không báo lý do"; cat /tmp/xv2.log; exit 1; }
     [ ! -e /tmp/xv2/etc/onebee/may-tram.env ] || { echo "FAIL  Máy bị từ chối vẫn có cấu hình"; exit 1; }'
echo "PASS  Từ chối: máy nhận lý do, không có cấu hình, không được cấp"

echo "===== SAO LƯU TÁCH THEO PHÒNG + KHÔI PHỤC MỘT PHÒNG ====="
box 'onebee-box sao-luu > /root/sl-phong.log 2>&1 || { tail -20 /root/sl-phong.log; exit 1; }
     . /usr/local/lib/onebee-box/common.sh; export RESTIC_REPOSITORY="${BACKUP_REPO}" RESTIC_PASSWORD_FILE=/etc/onebee-box/secrets/restic-box
     for p in ke-toan kho; do
       n="$(restic snapshots --tag "onebee-box,phong-${p}" --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")"
       [ "${n}" -ge 1 ] || { echo "FAIL  Không có bản sao lưu riêng của phòng ${p}"; exit 1; }
     done
     rm /srv/onebee/phong-ban/ke-toan/so-sach.txt
     onebee-box khoi-phuc-phong ke-toan > /root/kp-phong.log 2>&1 || { cat /root/kp-phong.log; exit 1; }
     f="$(find /srv/onebee/phong-ban/ke-toan -path "*khoi-phuc-*" -name so-sach.txt | head -1)"
     [ -n "${f}" ] && cmp -s "${f}" /root/so-sach.txt || { echo "FAIL  Khôi phục phòng Kế toán không lấy lại đúng tệp"; cat /root/kp-phong.log; exit 1; }
     [ -z "$(find /srv/onebee/phong-ban/kho -path "*khoi-phuc-*")" ] || { echo "FAIL  Khôi phục phòng Kế toán chép sang phòng Kho"; exit 1; }
     rm -rf /srv/onebee/phong-ban/ke-toan/khoi-phuc-*
     echo "PASS  Sao lưu Box có bản riêng từng phòng; khôi phục riêng phòng Kế toán lấy lại đúng tệp đã xóa"'
