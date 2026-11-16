#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Kiểm chế độ bản chạy thử công khai trên Box thử: bật onebee_box_che_do_demo → bộ cài nạp dữ liệu mẫu,
# bật bộ hẹn giờ 03:00 và dựng thanh thông báo demo trên trang Sổ điều hành; nạp lại hai lần không lỗi,
# số dòng không đổi; tắt chế độ demo → bộ hẹn giờ, dịch vụ và tệp dữ liệu mẫu bị gỡ, chạy lại bộ cài không đổi.
# Bài kiểm thanh thông báo cần trang Sổ điều hành của giai đoạn trước đã được gộp.
# Cách dùng: tests/box/check-ban-demo.sh <container-Box>   (repo đã chép vào /root/onebee-test trong Box)
set -euo pipefail
BOX="${1:?Cách dùng: check-ban-demo.sh <container-Box>}"
box() { docker exec "${BOX}" bash -euo pipefail -c "$(cat)"; }
cai() {
  docker exec "${BOX}" bash -euo pipefail -c \
    "/root/onebee-test/box/onebee-box-install.sh > /root/cai-$1.log 2>&1 || { tail -40 /root/cai-$1.log; exit 1; }"
}

echo "===== BẢN CHẠY THỬ CÔNG KHAI: BẬT CHẾ ĐỘ DEMO ====="
box <<'EOF'
sed -i -E 's#^onebee_box_che_do_demo: .*#onebee_box_che_do_demo: true#' /root/onebee-test/box/ansible/group_vars/all.yml
grep -qx 'onebee_box_che_do_demo: true' /root/onebee-test/box/ansible/group_vars/all.yml \
  || { echo 'FAIL  Không bật được onebee_box_che_do_demo'; exit 1; }
EOF
cai bat-demo

echo "===== BẢN CHẠY THỬ CÔNG KHAI: DỮ LIỆU MẪU ====="
box <<'EOF'
dem() {
  docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c "
    SELECT (SELECT count(*) FROM onebee.don_hang WHERE nguon = 'nap-du-lieu-demo') || ',' ||
           (SELECT count(*) FROM onebee.yeu_cau_ho_tro WHERE nguon = 'nap-du-lieu-demo') || ',' ||
           (SELECT count(*) FROM onebee.xu_ly_ho_tro WHERE nguon = 'nap-du-lieu-demo') || ',' ||
           (SELECT count(*) FROM onebee.khao_sat WHERE nguon = 'nap-du-lieu-demo') || ',' ||
           (SELECT count(*) FROM onebee.tinh_trang_may WHERE ten LIKE 'demo-%')"
}
truoc="$(dem)" || { echo 'FAIL  Không đọc được số dòng dữ liệu mẫu'; exit 1; }
[ "${truoc}" = '5,3,1,3,3' ] || { echo "FAIL  Dữ liệu mẫu sai số dòng: ${truoc} (mong 5,3,1,3,3)"; exit 1; }
for lan in 1 2; do
  systemctl start onebee-demo-reset.service \
    || { systemctl status --no-pager -l onebee-demo-reset.service | tail -20; echo "FAIL  Nạp dữ liệu mẫu lần ${lan} lỗi"; exit 1; }
done
sau="$(dem)" || { echo 'FAIL  Không đọc được số dòng sau khi nạp lại'; exit 1; }
[ "${truoc}" = "${sau}" ] || { echo "FAIL  Số dòng đổi sau khi nạp lại: ${truoc} → ${sau}"; exit 1; }
echo "PASS  Nạp dữ liệu mẫu hai lần không lỗi, số dòng không đổi (${sau})"
trang_thai="$(docker exec onebee-postgres psql -X -q -At -U postgres -d onebee -c \
  "SELECT string_agg(DISTINCT trang_thai_duyet, ',' ORDER BY trang_thai_duyet) FROM onebee.don_hang WHERE nguon = 'nap-du-lieu-demo'")"
[ "${trang_thai}" = 'CHO_DUYET,DA_DUYET,TU_CHOI' ] || { echo "FAIL  Đơn mẫu thiếu trạng thái: ${trang_thai}"; exit 1; }
echo 'PASS  Đơn mẫu có đủ ba trạng thái chờ duyệt / đã duyệt / từ chối'
EOF

echo "===== BẢN CHẠY THỬ CÔNG KHAI: BỘ HẸN GIỜ 03:00 ====="
box <<'EOF'
systemctl is-enabled -q onebee-demo-reset.timer || { echo 'FAIL  Bộ hẹn giờ demo chưa được bật'; exit 1; }
grep -q '^OnCalendar=\*-\*-\* 03:00:00$' /etc/systemd/system/onebee-demo-reset.timer \
  || { systemctl cat onebee-demo-reset.timer; echo 'FAIL  Bộ hẹn giờ không đặt 03:00'; exit 1; }
systemctl list-timers --all --no-pager | grep -q onebee-demo-reset.timer \
  || { echo 'FAIL  Bộ hẹn giờ không có trong danh sách đang chạy'; exit 1; }
echo 'PASS  Có bộ hẹn giờ đặt lại dữ liệu mẫu lúc 03:00 mỗi ngày'
EOF

echo "===== BẢN CHẠY THỬ CÔNG KHAI: THANH THÔNG BÁO DEMO ====="
box <<'EOF'
trang="$(find /opt/onebee-box/portal/site -maxdepth 4 -type f -path '*so-dieu-hanh*' 2>/dev/null | head -1)"
[ -n "${trang}" ] || { echo 'FAIL  Chưa có trang Sổ điều hành — chạy bài kiểm này sau khi gộp giai đoạn Sổ điều hành'; exit 1; }
grep -q 'Dữ liệu giả lập' "${trang}" && grep -q '03:00' "${trang}" \
  || { echo "FAIL  Trang ${trang} thiếu thanh thông báo demo"; exit 1; }
echo "PASS  Thanh thông báo demo hiện trên trang Sổ điều hành (${trang})"
EOF

echo "===== BẢN CHẠY THỬ CÔNG KHAI: CHẠY LẠI BỘ CÀI ====="
cai bat-demo-lan-2
box <<'EOF'
grep -Eq 'changed=0 .*failed=0' /root/cai-bat-demo-lan-2.log \
  || { grep -B2 'changed:' /root/cai-bat-demo-lan-2.log | head -30; echo 'FAIL  Chạy lại bộ cài khi bật demo còn thay đổi'; exit 1; }
echo 'PASS  Chạy lại bộ cài khi bật demo: changed=0'
EOF

echo "===== BẢN CHẠY THỬ CÔNG KHAI: TẮT CHẾ ĐỘ DEMO ====="
box <<'EOF'
sed -i -E 's#^onebee_box_che_do_demo: .*#onebee_box_che_do_demo: false#' /root/onebee-test/box/ansible/group_vars/all.yml
grep -qx 'onebee_box_che_do_demo: false' /root/onebee-test/box/ansible/group_vars/all.yml \
  || { echo 'FAIL  Không tắt được onebee_box_che_do_demo'; exit 1; }
EOF
cai tat-demo
box <<'EOF'
[ ! -e /etc/systemd/system/onebee-demo-reset.timer ] || { echo 'FAIL  Tắt demo nhưng còn tệp bộ hẹn giờ'; exit 1; }
[ ! -e /etc/systemd/system/onebee-demo-reset.service ] || { echo 'FAIL  Tắt demo nhưng còn tệp dịch vụ đặt lại'; exit 1; }
! systemctl list-timers --all --no-pager | grep -q onebee-demo-reset.timer \
  || { echo 'FAIL  Tắt demo nhưng bộ hẹn giờ vẫn chạy'; exit 1; }
[ ! -e /usr/local/lib/onebee-box/nap-du-lieu-demo.sql ] || { echo 'FAIL  Tắt demo nhưng còn tệp dữ liệu mẫu'; exit 1; }
echo 'PASS  Tắt chế độ demo: bộ hẹn giờ, dịch vụ đặt lại và tệp dữ liệu mẫu đều bị gỡ'
EOF

cai tat-demo-lan-2
box <<'EOF'
grep -Eq 'changed=0 .*failed=0' /root/cai-tat-demo-lan-2.log \
  || { grep -B2 'changed:' /root/cai-tat-demo-lan-2.log | head -30; echo 'FAIL  Chạy lại bộ cài khi tắt demo còn thay đổi'; exit 1; }
echo 'PASS  Chạy lại bộ cài khi tắt demo: changed=0'
EOF

echo 'KẾT QUẢ: ĐẠT — dữ liệu mẫu nạp lại an toàn, hẹn giờ 03:00, thanh thông báo demo, tắt gỡ đúng'
