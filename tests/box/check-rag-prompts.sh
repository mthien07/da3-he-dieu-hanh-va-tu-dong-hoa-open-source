#!/usr/bin/env bash
# check-rag-prompts.sh — Kiểm tra kho mẫu soạn văn bản, kho tri thức và hai đường /ai/ của dịch vụ Trợ lý AI.
# Chạy độc lập, không cần Docker: chỉ đọc tệp trong repo.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
AI_FILES="${ROOT}/box/ansible/roles/box-ai/files"
PROMPTS_DIR="${AI_FILES}/prompts"
KNOWLEDGE_DIR="${AI_FILES}/knowledge"
SCRIPT="${AI_FILES}/onebee-ai-rag.py"
ROLE="${ROOT}/box/ansible/roles/box-ai/tasks/main.yml"
BOX_SCRIPT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-box.sh.j2"
COMPOSE="${ROOT}/box/ansible/roles/box-stack/templates/docker-compose.yml.j2"
SQL="${ROOT}/box/ansible/roles/box-du-lieu/files/luoc-do/004-tri-thuc-va-lich-su-hoi-ai.sql"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

echo "=== KHO MẪU SOẠN VĂN BẢN VÀ KHO TRI THỨC CỦA TRỢ LÝ AI ==="

[[ -d "${PROMPTS_DIR}" ]] || fail "Thư mục prompts không tồn tại"
[[ -d "${KNOWLEDGE_DIR}" ]] || fail "Thư mục knowledge không tồn tại"
pass "Thư mục prompts và knowledge tồn tại"

for slug in to-trinh bien-ban hop-dong bao-cao; do
  pfile="${PROMPTS_DIR}/${slug}.json"
  [[ -f "${pfile}" ]] || fail "Thiếu file mẫu prompt ${slug}.json"
  python3 -c "import json, sys; d = json.load(open('${pfile}')); sys.exit(0 if d.get('command') and d.get('title') and d.get('content') else 1)" \
    || fail "File ${slug}.json không đúng cấu trúc (thiếu command, title, content)"
done
pass "Bốn mẫu soạn văn bản hợp lệ"

grep -q "Nghị định số 30/2020/NĐ-CP" "${PROMPTS_DIR}/to-trinh.json" || fail "to-trinh.json không nhắc đến Nghị định 30/2020/NĐ-CP"
grep -q "Biên bản cuộc họp" "${PROMPTS_DIR}/bien-ban.json" || fail "bien-ban.json thiếu tiêu đề biên bản"
grep -q "Luật Hợp tác xã 2023" "${PROMPTS_DIR}/hop-dong.json" || fail "hop-dong.json không nhắc đến Luật Hợp tác xã 2023"
grep -q "quỹ chung không chia" "${PROMPTS_DIR}/bao-cao.json" || fail "bao-cao.json thiếu quy định trích quỹ chung không chia"
pass "Nội dung bốn mẫu soạn văn bản đúng thể thức hành chính và Luật HTX 2023"

[[ -f "${KNOWLEDGE_DIR}/nghi-dinh-30-2020-nd-cp.md" ]] || fail "Thiếu tài liệu NĐ 30 trong knowledge"
[[ -f "${KNOWLEDGE_DIR}/luat-hop-tac-xa-2023.md" ]] || fail "Thiếu tài liệu Luật HTX 2023 trong knowledge"
grep -q "Thể thức văn bản hành chính" "${KNOWLEDGE_DIR}/nghi-dinh-30-2020-nd-cp.md" || fail "Tài liệu NĐ 30 thiếu thể thức"
grep -q "Tài sản chung không chia" "${KNOWLEDGE_DIR}/luat-hop-tac-xa-2023.md" || fail "Tài liệu Luật HTX thiếu nội dung tài sản chung không chia"
pass "Kho tri thức pháp lý gốc đầy đủ"

[[ -f "${SCRIPT}" ]] || fail "Thiếu mã dịch vụ onebee-ai-rag.py"
grep -q '"/ai/hoi", "/ai/tom-tat"' "${SCRIPT}" || fail "Dịch vụ không mở đúng hai đường /ai/hoi và /ai/tom-tat"
grep -q 'TÀI LIỆU THAM KHẢO' "${SCRIPT}" || fail "Lời nhắc thiếu khối tài liệu tham khảo"
grep -q 'NHAC_KIEM_TRA' "${SCRIPT}" || fail "Thiếu dòng nhắc kiểm tra lại"
grep -q 'ON CONFLICT (nguon, doan) DO UPDATE' "${SCRIPT}" || fail "Câu lệnh nạp tri thức không cập nhật đúng dòng cũ"
grep -q 'lenh == "nap-tri-thuc"' "${SCRIPT}" || fail "Thiếu lệnh nap-tri-thuc"
pass "Dịch vụ Trợ lý AI: hai đường /ai/, lời nhắc có trích nguồn + dòng nhắc kiểm tra, nạp tri thức không trùng"

grep -q "nap-tri-thuc) with_lock cmd_nap_tri_thuc ;;" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh nap-tri-thuc"
grep -q "cap-khoa-hoi) shift; cmd_cap_khoa_hoi" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh cap-khoa-hoi"
grep -q "go-khoa-hoi) shift; cmd_go_khoa_hoi" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu lệnh go-khoa-hoi"
pass "onebee-box có lệnh nạp tri thức và cấp/thu hồi khóa Trợ lý AI"

grep -q 'dest: "{{ onebee_box_dir }}/ai-rag/{{ item.dest }}/"' "${ROLE}" || fail "Role box-ai không chép mẫu/tri thức vào thư mục dịch vụ đọc"
grep -q "{src: prompts, dest: prompts}" "${ROLE}" || fail "Role box-ai thiếu bước chép prompts"
grep -q "{src: knowledge, dest: knowledge}" "${ROLE}" || fail "Role box-ai thiếu bước chép knowledge"
grep -q 'onebee_box_data }}/knowledge:/du-lieu-tri-thuc:ro' "${COMPOSE}" || fail "Compose không gắn thư mục tri thức của đơn vị"
pass "Bộ cài chép mẫu/tri thức và gắn thư mục tri thức của đơn vị"

[[ -f "${SQL}" ]] || fail "Thiếu tệp lược đồ 004 cho tri thức"
grep -q "CREATE FUNCTION onebee.tim_tri_thuc" "${SQL}" || fail "Lược đồ thiếu hàm tìm tri thức"
grep -q "GRANT SELECT ON onebee.tai_lieu_tri_thuc TO nhan_vien" "${SQL}" || fail "Lược đồ thiếu quyền đọc tri thức cho nhân viên"
pass "Lược đồ tri thức và nhật ký hỏi đáp có hàm tìm kiếm và quyền tối thiểu"

[[ ! -e "${AI_FILES}/onebee-webui.py" ]] || fail "Còn tệp dịch vụ cũ onebee-webui.py"

echo ""
echo "===> TẤT CẢ CÁC BÀI KIỂM TRA KHO MẪU VÀ TRI THỨC ĐÃ ĐẠT (PASS)"
