#!/usr/bin/env bash
# check-rag-prompts.sh — Kiểm thử kho mẫu prompt hành chính NĐ 30 và bộ tri thức RAG Open WebUI
# Chạy độc lập, không cần Docker thật.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
AI_FILES="${ROOT}/box/ansible/roles/box-ai/files"
PROMPTS_DIR="${AI_FILES}/prompts"
KNOWLEDGE_DIR="${AI_FILES}/knowledge"
SCRIPT="${AI_FILES}/onebee-webui.py"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; exit 1; }

echo "=== KIỂM TRA TASK 04: KHO PROMPT HÀNH CHÍNH & TRI THỨC RAG ==="

# 1. Kiểm tra tồn tại thư mục và các tệp mẫu prompt
[[ -d "${PROMPTS_DIR}" ]] || fail "Thư mục prompts không tồn tại"
[[ -d "${KNOWLEDGE_DIR}" ]] || fail "Thư mục knowledge không tồn tại"
pass "Thư mục prompts và knowledge tồn tại"

# 2. Kiểm tra 4 mẫu prompt cốt lõi
for slug in to-trinh bien-ban hop-dong bao-cao; do
  pfile="${PROMPTS_DIR}/${slug}.json"
  [[ -f "${pfile}" ]] || fail "Thiếu file mẫu prompt ${slug}.json"
  python3 -c "import json, sys; d = json.load(open('${pfile}')); sys.exit(0 if d.get('command') and d.get('title') and d.get('content') else 1)" \
    || fail "File ${slug}.json không đúng cấu trúc (thiếu command, title, content)"
  pass "Mẫu prompt ${slug}.json hợp lệ"
done

# 3. Kiểm tra nội dung đặc thù hành chính & HTX trong các mẫu prompt
grep -q "Nghị định số 30/2020/NĐ-CP" "${PROMPTS_DIR}/to-trinh.json" || fail "to-trinh.json không nhắc đến Nghị định 30/2020/NĐ-CP"
grep -q "Biên bản cuộc họp" "${PROMPTS_DIR}/bien-ban.json" || fail "bien-ban.json thiếu tiêu đề biên bản"
grep -q "Luật Hợp tác xã 2023" "${PROMPTS_DIR}/hop-dong.json" || fail "hop-dong.json không nhắc đến Luật Hợp tác xã 2023"
grep -q "quỹ chung không chia" "${PROMPTS_DIR}/bao-cao.json" || fail "bao-cao.json thiếu quy định trích quỹ chung không chia"
pass "Nội dung 4 mẫu prompt chứa đầy đủ yêu cầu thể thức hành chính và Luật HTX 2023"

# 4. Kiểm tra tài liệu tri thức RAG
[[ -f "${KNOWLEDGE_DIR}/nghi-dinh-30-2020-nd-cp.md" ]] || fail "Thiếu tài liệu NĐ 30 trong knowledge"
[[ -f "${KNOWLEDGE_DIR}/luat-hop-tac-xa-2023.md" ]] || fail "Thiếu tài liệu Luật HTX 2023 trong knowledge"
grep -q "Thể thức văn bản hành chính" "${KNOWLEDGE_DIR}/nghi-dinh-30-2020-nd-cp.md" || fail "Tài liệu NĐ 30 thiếu thể thức"
grep -q "Tài sản chung không chia" "${KNOWLEDGE_DIR}/luat-hop-tac-xa-2023.md" || fail "Tài liệu Luật HTX thiếu nội dung tài sản chung không chia"
pass "Bộ tài liệu tri thức pháp lý RAG đầy đủ và chính xác"

# 5. Kiểm tra onebee-webui.py có hàm dong-bo-prompts và dong-bo-tri-thuc
grep -q "def dong_bo_prompts" "${SCRIPT}" || fail "onebee-webui.py thiếu hàm dong_bo_prompts"
grep -q "def dong_bo_tri_thuc" "${SCRIPT}" || fail "onebee-webui.py thiếu hàm dong_bo_tri_thuc"
grep -q "dong-bo-prompts" "${SCRIPT}" || fail "onebee-webui.py thiếu nhánh CLI dong-bo-prompts"
grep -q "dong-bo-tri-thuc" "${SCRIPT}" || fail "onebee-webui.py thiếu nhánh CLI dong-bo-tri-thuc"
pass "onebee-webui.py đã tích hợp đầy đủ lệnh đồng bộ prompt và tri thức RAG"

# 6. Kiểm tra onebee-box.sh.j2 có điều hướng lệnh
BOX_SCRIPT="${ROOT}/box/ansible/roles/box-stack/templates/onebee-box.sh.j2"
grep -q "dong-bo-prompts) webui dong-bo-prompts ;;" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu điều hướng dong-bo-prompts"
grep -q "dong-bo-tri-thuc) webui dong-bo-tri-thuc ;;" "${BOX_SCRIPT}" || fail "onebee-box.sh.j2 thiếu điều hướng dong-bo-tri-thuc"
pass "onebee-box.sh.j2 đã tích hợp lệnh CLI quản trị tương ứng"

# 7. Kiểm tra Ansible role box-ai có bước sao chép prompts và knowledge
ANSIBLE_AI="${ROOT}/box/ansible/roles/box-ai/tasks/main.yml"
grep -q "src: prompts" "${ANSIBLE_AI}" || fail "Ansible box-ai thiếu bước copy prompts"
grep -q "src: knowledge" "${ANSIBLE_AI}" || fail "Ansible box-ai thiếu bước copy knowledge"
pass "Ansible tasks đã khai báo cài đặt prompts và knowledge lên Box"

echo ""
echo "===> TẤT CẢ CÁC BÀI TEST TASK 04 ĐÃ ĐẠT (PASS)!"
