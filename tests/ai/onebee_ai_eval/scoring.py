"""Chấm 1 câu trả lời theo ý bắt buộc (khớp chuỗi) và ý cấm (regex). So khớp chữ thường, NFC, giữ dấu."""
import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[*_`#>]+", "", text)  # bỏ định dạng markdown (**đậm**, `mã`, # tiêu đề) trước khi so khớp
    text = text.replace("hoà", "hòa").replace("thuỷ", "thủy").replace("uỷ", "ủy")  # hai kiểu đặt dấu phổ biến
    return re.sub(r"\s+", " ", text)


# Từ phủ định đứng ngay trước ý cấm → câu trả lời đang KHUYÊN KHÔNG làm, không tính là phạm lỗi
PHU_DINH = re.compile(r"(không|đừng|chớ|tránh|không nên|không cần|không được)\s+(\S+\s+){0,2}$")


def cam_hit(pattern, text):
    """Ý cấm có tiền tố "!" = bỏ qua chỗ khớp nằm ngay sau từ phủ định (vd "đừng tắt tự động cập nhật")."""
    if not pattern.startswith("!"):
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    for m in re.finditer(pattern[1:], text, flags=re.IGNORECASE):
        if not PHU_DINH.search(text[max(0, m.start() - 40):m.start()]):
            return True
    return False


def score_answer(question, answer):
    """Trả về: y_dat, y_tong, y_thieu (list), cam_pham (list), dat_khong_bia (chỉ ý nghĩa với nhóm 5)."""
    text = normalize(answer)
    thieu = []
    def hit(a):
        a = str(a)
        if a.startswith("re:"):  # cách viết dạng regex, vd "re:(?<!\d)18 ?%" để không khớp nhầm "118%"
            return re.search(a[3:], text) is not None
        return normalize(a) in text

    for alternatives in question["bat_buoc"]:
        if not any(hit(a) for a in alternatives):
            thieu.append(" / ".join(str(a) for a in alternatives))
    cam_pham = [p for p in question.get("cam") or [] if cam_hit(p, text)]
    y_tong = len(question["bat_buoc"])
    return {
        "y_dat": y_tong - len(thieu),
        "y_tong": y_tong,
        "y_thieu": thieu,
        "cam_pham": cam_pham,
        # Nhóm 5: chỉ đạt khi nói rõ "không biết" VÀ không đưa ra thông tin bịa
        "dat_khong_bia": not thieu and not cam_pham,
    }
