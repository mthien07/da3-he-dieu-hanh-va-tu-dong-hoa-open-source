#!/usr/bin/env bash
# Chạy BÊN TRONG máy đã cài OneBee OS (người dùng thường). Cần: poppler-utils, hunspell.
# 1) Mở file Word mẫu (Times New Roman/Arial/Calibri/Cambria) bằng LibreOffice, xuất PDF:
#    font được thay đúng (Liberation/Carlito/Noto Serif), chữ tiếng Việt giữ nguyên dấu, không lẫn font.
# 2) Kiểm tra chính tả tiếng Việt (hunspell vi_VN) nhận đúng từ có dấu, bắt được từ sai.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE="${HERE}/../fixtures/mau-van-ban-tieng-viet.docx"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
fails=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; fails=$((fails + 1)); }

cp "${FIXTURE}" "${WORK}/mau.docx"
if HOME="${WORK}" soffice --headless --norestore --convert-to pdf --outdir "${WORK}" "${WORK}/mau.docx" >/dev/null 2>&1 \
   && [[ -s "${WORK}/mau.pdf" ]]; then
  pass "LibreOffice mở file .docx mẫu và xuất PDF"
else
  fail "LibreOffice mở file .docx mẫu và xuất PDF"
fi

fonts="$(pdffonts "${WORK}/mau.pdf" 2>/dev/null)"
for f in LiberationSerif LiberationSans Carlito NotoSerif; do
  if grep -q "${f}" <<<"${fonts}"; then pass "PDF dùng font thay thế ${f}"; else fail "PDF dùng font thay thế ${f}"; fi
done
# Chỉ đúng 4 font trên: có font lạ (Caladea, DejaVu...) nghĩa là có chữ bị lẫn sang font dự phòng
n_fonts="$(tail -n +3 <<<"${fonts}" | wc -l)"
if [[ ${n_fonts} -eq 4 ]]; then pass "Không có chữ bị lẫn sang font dự phòng (PDF đúng 4 font)"
else fail "Có chữ bị lẫn font: PDF có ${n_fonts} font"; printf '%s\n' "${fonts}"; fi

text="$(pdftotext -layout "${WORK}/mau.pdf" - 2>/dev/null)"
for phrase in "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" "Hợp tác xã OneBee" "Báo cáo tình hình hoạt động quý III" \
              "Người lập biểu ký, ghi rõ họ tên" "Chi phí văn phòng phẩm" "1.250.000"; do
  if grep -qF "${phrase}" <<<"${text}"; then pass "PDF giữ đúng chữ: ${phrase}"; else fail "PDF giữ đúng chữ: ${phrase}"; fi
done

misspelled="$(echo "Hợp tác xã báo cáo tài chính nghiệp vụ Tây Ninh" | hunspell -d vi_VN -l)"
if [[ -z "${misspelled}" ]]; then pass "Chính tả tiếng Việt: câu đúng không bị báo lỗi"; else fail "Chính tả báo lỗi nhầm: ${misspelled}"; fi
if echo "Hợp tác xãx" | hunspell -d vi_VN -l | grep -q "xãx"; then pass "Chính tả tiếng Việt: bắt được từ sai"; else fail "Chính tả tiếng Việt: không bắt được từ sai"; fi

echo "----"
if [[ ${fails} -eq 0 ]]; then echo "KẾT QUẢ: tài liệu văn phòng đạt"; else echo "KẾT QUẢ: ${fails} mục KHÔNG đạt"; exit 1; fi
