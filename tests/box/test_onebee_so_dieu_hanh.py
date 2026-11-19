#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Kiểm thử Ứng dụng Sổ điều hành H-P-D-I (box-stack: so-dieu-hanh.html.j2, so-dieu-hanh.css, so-dieu-hanh.js), không cần Box thật.
Trang: tĩnh, không nguồn ngoài, không innerHTML, mỗi tệp dưới 40 KB, đủ bốn khu H, P, D, I và hai khu Kho, Kế toán,
chỉ gọi /api/, /files/, /ai/, /quy-trinh/webhook/onebee-{phe-duyet,may-xin-vao,duyet-may};
khu [M] Máy trạm (duyệt máy xin vào Box) chạy THẬT bằng node với DOM giả: bảng, ô chọn phòng, nút Duyệt/Từ chối gọi đúng điểm nhận;
mã JavaScript chạy THẬT bằng node (nếu có): kiểm dữ liệu nhập, đọc số dòng, thông báo lỗi tiếng Việt, tóm tắt tuần chỉ có số liệu tổng hợp.
Bộ cài tạo thư mục portal/site/so-dieu-hanh trước khi sinh trang; Caddyfile có tuyến sau đăng nhập; Authelia có luật theo nhóm; trang chủ và
menu máy trạm trỏ tới ứng dụng. Chạy: python3 -m unittest"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "../..")
ROLES = os.path.join(ROOT, "box/ansible/roles")
STACK = os.path.join(ROLES, "box-stack")
TRANG = os.path.join(STACK, "templates/so-dieu-hanh.html.j2")
CSS = os.path.join(STACK, "files/so-dieu-hanh.css")
JS = os.path.join(STACK, "files/so-dieu-hanh.js")
JS_KHO = os.path.join(STACK, "files/so-dieu-hanh-kho.js")
MUC_MENU = os.path.join(ROOT, "desktop/ansible/roles/quan-ly-tap-trung/tasks/muc-menu.yml")
NODE = shutil.which("node")


def nhom_cam_nang():
    with open(os.path.join(STACK, "tasks/main.yml"), encoding="utf-8") as f:
        for t in yaml.safe_load(f):
            facts = t.get("ansible.builtin.set_fact") or {}
            if "onebee_cam_nang_nhom" in facts:
                return facts["onebee_cam_nang_nhom"]
    raise AssertionError("tasks box-stack thiếu onebee_cam_nang_nhom")


def bien(**them):
    with open(os.path.join(ROOT, "box/ansible/group_vars/all.yml"), encoding="utf-8") as f:
        v = yaml.safe_load(f)
    # Nguồn dữ liệu dùng chung mà bộ cài nạp bằng lookup khi sinh trang chủ
    with open(os.path.join(ROOT, "desktop/ansible/roles/theme/files/onebee-cam-nang.json"), encoding="utf-8") as f:
        v["onebee_cam_nang"] = json.load(f)
    v["onebee_cam_nang_nhom"] = nhom_cam_nang()
    v.update(onebee_box_ip="192.168.1.10", onebee_box_ma_don_vi="anphu", onebee_https_hieu_luc=True, onebee_sso_hieu_luc=True,
             onebee_kuma_dia_chi="0.0.0.0", onebee_box_ten_don_vi="HTX An Phú")
    v.update(them)
    return v


def render(duong_dan, **them):
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True, undefined=jinja2.StrictUndefined)
    env.filters["bool"] = bool
    with open(duong_dan, encoding="utf-8") as f:
        return env.from_string(f.read()).render(**bien(**them))


def doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


class TrangTinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html, cls.css, cls.js = render(TRANG), doc(CSS), doc(JS)
        cls.js_kho = doc(JS_KHO)
        cls.tat_ca = {"so-dieu-hanh.html": cls.html, "so-dieu-hanh.css": cls.css, "so-dieu-hanh.js": cls.js,
                      "so-dieu-hanh-kho.js": cls.js_kho}

    def test_moi_tep_duoi_40kb(self):
        tong = sum(len(t.encode("utf-8")) for t in self.tat_ca.values())
        self.assertLess(tong, 80 * 1024, f"cả trang (HTML + CSS + JS) {tong} byte")
        for ten, noi_dung in self.tat_ca.items():
            self.assertLess(len(noi_dung.encode("utf-8")), 40 * 1024, f"{ten} {len(noi_dung.encode('utf-8'))} byte")

    def test_khong_innerhtml_khong_ma_dong(self):
        for ten, noi_dung in self.tat_ca.items():
            for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "srcdoc"):
                self.assertNotIn(cam, noi_dung, f"{ten} dùng {cam}")

    def test_khong_tai_gi_tu_internet(self):
        for ten, noi_dung in self.tat_ca.items():
            self.assertNotRegex(noi_dung, r"https?://", f"{ten} có địa chỉ http(s)")
            self.assertIsNone(re.search(r"""(src|href|action|poster|data)\s*=\s*["']?\s*(https?:)?//""", noi_dung), ten)
            self.assertNotIn("@import", noi_dung, ten)
            self.assertNotRegex(noi_dung, r"url\(\s*[\"']?(https?:)?//", ten)

    def test_tai_nguyen_cung_goc_va_khong_ma_nhung(self):
        # CSP của Caddy chỉ cho script/style từ chính Box ('self'): trang không được có script/style nhúng, thuộc tính style, trình xử lý on…=
        h = self.html
        self.assertIn('<script src="/so-dieu-hanh/so-dieu-hanh.js"></script>', h)
        self.assertIn('<script src="/so-dieu-hanh/so-dieu-hanh-kho.js"></script>', h)
        self.assertIn('<link rel="stylesheet" href="/so-dieu-hanh/so-dieu-hanh.css">', h)
        self.assertEqual(len(re.findall(r"<script\b", h)), 2)
        self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)[^>]*>", h), "script nhúng")
        self.assertNotRegex(h, r"<style\b")
        self.assertNotRegex(h, r"""\sstyle\s*=""")
        self.assertNotRegex(h, r"""\son[a-z]+\s*=""")
        self.assertNotRegex(h, r"<(iframe|object|embed|form[^>]*\saction=)")

    def test_du_bon_khu_h_p_d_i(self):
        h = self.html
        for khu in "hpdi":
            self.assertIn(f'id="khu-{khu}"', h)
            self.assertIn(f'data-khu="khu-{khu}"', h)
        for the in ("[H]", "[P]", "[D]", "[I]"):
            self.assertIn(the, h)
        self.assertIn("luu-y-ai", h)     # dòng nhắc "AI có thể sai" luôn hiện cạnh kết quả
        self.assertIn("AI có thể sai", h)

    def test_co_khu_m_may_tram_chi_hien_cho_quan_ly_ky_thuat(self):
        h = self.html
        self.assertRegex(h, r'<button [^>]*data-khu="khu-m"[^>]*id="nut-khu-m"[^>]* hidden>\[M\] Máy trạm</button>')
        self.assertIn('<section id="khu-m" class="khu" role="tabpanel">', h)
        for cot in ("Tên máy", "Máy", "IP", "Phòng xin", "Mã đối chiếu", "Lúc", "Trạng thái"):
            self.assertIn(f"<th>{cot}</th>", h)
        self.assertIn("So mã 6 số với màn hình máy trạm trước khi duyệt — khác mã thì Từ chối", h)
        self.assertIn("sudo onebee-box them-phong", h)
        self.assertIn('"khu-m"', self.js)
        self.assertIn('VAI_TRO_MAY = ["quan_ly", "ky_thuat"]', self.js)
        self.assertIn('getElementById("nut-khu-m").hidden', self.js)
        for cam in ("alert(", "confirm(", "prompt("):
            self.assertNotIn(cam, self.js)
        self.assertIn("CHU_KY_TAI_MAY_MS = 10000", self.js)

    def test_tieu_de_ten_don_vi_thoat_html_va_mo_hinh_ai(self):
        h = render(TRANG, onebee_box_ten_don_vi='<script>alert("x")</script>')
        self.assertNotIn('<script>alert("x")', h)
        self.assertIn("&lt;script&gt;", h)
        self.assertIn(f'data-mo-hinh-ai="{bien()["onebee_box_ai_model"]}"', self.html)
        self.assertIn("HTX An Phú", self.html)
        self.assertIn("<title>Sổ điều hành", render(TRANG, onebee_box_ten_don_vi=""))

    def test_chi_goi_dung_cac_duong_dan_da_giao_kem(self):
        js = self.js + "\n" + self.js_kho
        duong = set(re.findall(r"""["'](/(?:api|files|ai|quy-trinh)/[A-Za-z0-9_/.\-]*)""", js))
        da_giao = {"/api/toi", "/api/don_hang", "/api/yeu_cau_ho_tro", "/api/khao_sat", "/api/khao_sat_tong_hop", "/api/tinh_trang_may",
                   "/api/tep_dinh_kem", "/files/", "/ai/hoi", "/ai/tom-tat", "/quy-trinh/webhook/onebee-phe-duyet",
                   "/quy-trinh/webhook/onebee-may-xin-vao", "/quy-trinh/webhook/onebee-duyet-may", "/api/mat_hang", "/api/ton_kho", "/api/so_kho", "/api/so_nhat_ky", "/api/bang_can_doi", "/api/rpc/them_nhap_kho"}
        self.assertEqual(duong, da_giao)
        self.assertNotIn("/ai/api/chat", js)   # dịch vụ Trợ lý chỉ mở /ai/hoi và /ai/tom-tat (Giai đoạn 3)
        self.assertNotIn("/webhook/", re.sub(r"/quy-trinh/webhook/", "", js))   # không gọi webhook không qua /quy-trinh/
        self.assertNotIn(":5678", js)
        self.assertNotIn(":3000", js)

    def test_du_lieu_nguoi_dung_chi_hien_bang_textcontent(self):
        js = self.js
        self.assertIn("textContent", js)
        self.assertNotRegex(js, r"\.(innerText|outerText)\s*=")
        # mọi lần gọi fetch đều xin JSON để phiên hết hạn trả 401 chứ không đổi sang HTML trang đăng nhập
        self.assertIn("application/json", js)
        self.assertIn("no-store", js)

    def test_html_la_html_hop_le_co_lang_vi(self):
        self.assertTrue(self.html.lstrip().lower().startswith("<!doctype html>"))
        self.assertIn('<html lang="vi">', self.html)
        self.assertIn('name="viewport"', self.html)


@unittest.skipUnless(NODE, "cần node")
class MaJavaScript(unittest.TestCase):
    """Chạy so-dieu-hanh.js THẬT trong node (không có `document`, nên chỉ nạp các hàm thuần)."""

    def chay(self, bieu_thuc):
        ma = (
            "const vm = require('vm'); const fs = require('fs');\n"
            "const ctx = vm.createContext({});\n"
            "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx, {filename: 'so-dieu-hanh.js'});\n"
            f"console.log(JSON.stringify(vm.runInContext({json.dumps(bieu_thuc)}, ctx)));\n"
        )
        r = subprocess.run([NODE, "-e", ma, JS], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_doc_so_dong_tu_content_range(self):
        for gia_tri, mong_doi in (("0-4/5", 5), ("*/0", 0), ("*/137", 137), ("0-0/*", None), ("", None), ("sai", None)):
            self.assertEqual(self.chay(f"docSoDong({json.dumps(gia_tri)})"), mong_doi, gia_tri)
        self.assertIsNone(self.chay("docSoDong(null)"))

    def test_don_hang_hop_le(self):
        kq = self.chay("""dungDonHang({khach_hang: '  HTX An Phú ', mat_hang: 'Mật ong', so_luong_kg: '3', don_gia: '100000',
                           ngay_giao: '2026-12-01', ghi_chu: ''})""")
        self.assertEqual(kq["than"], {"khach_hang": "HTX An Phú", "mat_hang": "Mật ong", "so_luong_kg": 3, "don_gia": 100000,
                                      "thanh_tien": 300000, "ngay_giao": "2026-12-01"})
        self.assertNotIn("loi", kq)

    def test_don_hang_sai_bi_chan_o_trinh_duyet_kem_loi_giai_thich(self):
        co_ban = {"khach_hang": "A", "mat_hang": "B", "so_luong_kg": "2", "don_gia": "10", "ngay_giao": "", "ghi_chu": ""}
        for sua, tu_khoa in (({"khach_hang": "   "}, "khách hàng"), ({"mat_hang": ""}, "mặt hàng"), ({"so_luong_kg": "0"}, "số lượng"),
                             ({"so_luong_kg": "-3"}, "số lượng"), ({"so_luong_kg": "abc"}, "số lượng"), ({"don_gia": "-1"}, "đơn giá"),
                             ({"don_gia": ""}, "đơn giá"), ({"ngay_giao": "mai"}, "ngày giao"),
                             ({"khach_hang": "x" * 201}, "khách hàng")):
            kq = self.chay(f"dungDonHang({json.dumps({**co_ban, **sua})})")
            self.assertIn("loi", kq, sua)
            self.assertIn(tu_khoa, kq["loi"].lower(), sua)
            self.assertNotIn("than", kq, sua)

    def test_thong_bao_loi_tieng_viet(self):
        def tb(ma, than):
            return self.chay(f"thongBaoLoi({ma}, {json.dumps(than)})")
        self.assertIn("hết hạn", tb(401, None))
        self.assertIn("không có quyền", tb(403, {"code": "42501", "message": "permission denied for view khao_sat_tong_hop"}))
        self.assertIn("quá lớn", tb(413, None))
        self.assertIn("không được nhận", tb(415, {"loi": ""}))
        self.assertIn("chưa sẵn sàng", tb(503, None))
        self.assertIn("chưa sẵn sàng", tb(502, {"loi": ""}))
        self.assertIn("Mức độ", tb(400, {"code": "23514", "message": 'new row violates check constraint "muc_do_trong_danh_muc"'}))
        self.assertIn("Loại sự cố", tb(400, {"message": 'violates check constraint "loai_trong_danh_muc"'}))
        self.assertIn("tự duyệt", tb(400, {"message": 'violates check constraint "khong_tu_duyet"'}))
        self.assertIn("Số lượng", tb(400, {"message": 'violates check constraint "so_luong_duong_don_gia_khong_am"'}))
        self.assertIn("chưa hợp lệ", tb(400, {"message": "gì đó không rõ"}))
        # Dịch vụ của Box trả lời tiếng Việt thì dùng nguyên văn
        self.assertEqual(tb(409, {"loi": "Chốt chặn: không tự phê duyệt đơn của chính mình"}), "Chốt chặn: không tự phê duyệt đơn của chính mình")
        self.assertIn("mã 418", tb(418, None))

    SO_LIEU = {
        "don_hang": {"tong": 12, "cho_duyet": 3, "da_duyet": 7, "tu_choi": 2},
        "ho_tro": {"tong": 5, "gap": 1},
        "may_tram": 4,
        "tep": {"tong": 9, "sach": 8, "nhiem": 1},
        "khao_sat": [{"tuan": "2026-11-09", "so_phieu": 6, "diem_tb": 4.2}],
    }

    def test_tom_tat_tuan_chi_gui_so_lieu_tong_hop(self):
        # Dữ liệu "bẩn": có tên người, số điện thoại, tên khách ở mọi chỗ — chỉ con số được phép đi qua
        ban = json.loads(json.dumps(self.SO_LIEU))
        ban["don_hang"].update(nguoi_tao="Nguyễn Văn An", khach_hang="HTX Bình Minh", ghi_chu="gọi 0912345678")
        ban["ho_tro"]["nguoi_bao"] = "Trần Thị Bình"
        ban["khao_sat"][0].update(gop_y="Anh Cường chậm quá", ten="Lê Hoa")
        ban["nguoi_dung"] = "binh"
        ban["may_tram"] = 4
        ban["tep"]["ten_tep"] = "bao-gia-nguyen-van-an.pdf"
        ban["khao_sat"].append({"tuan": "Nguyễn Văn An", "so_phieu": "0912345678", "diem_tb": "x"})
        loi_nhac = self.chay(f"taoLoiNhacTomTat({json.dumps(ban)})")
        for ten in ("Nguyễn", "Văn An", "Bình Minh", "0912345678", "Trần", "Cường", "Lê Hoa", "binh", "bao-gia", "nguoi_tao", "khach_hang",
                    "ghi_chu", "gop_y", "ten_tep", "nguoi_bao"):
            self.assertNotIn(ten, loi_nhac, ten)
        phan_json = loi_nhac[loi_nhac.index("{"):]
        so_lieu = json.loads(phan_json)
        self.assertEqual(so_lieu["don_hang"], self.SO_LIEU["don_hang"])
        self.assertEqual(so_lieu["ho_tro"], self.SO_LIEU["ho_tro"])
        self.assertEqual(so_lieu["may_tram"], 4)
        self.assertEqual(so_lieu["tep"], self.SO_LIEU["tep"])
        self.assertEqual(so_lieu["khao_sat"], self.SO_LIEU["khao_sat"])   # dòng có tuần/số phiếu không hợp lệ bị bỏ
        self.assertIn("tiếng Việt", loi_nhac)
        self.assertIn("không bịa", loi_nhac)

    def test_mau_tom_tat_la_chuoi_json_mot_dong_de_bai_kiem_tren_box_doc_duoc(self):
        dong = [d for d in doc(JS).splitlines() if d.startswith("var MAU_TOM_TAT = ")]
        self.assertEqual(len(dong), 1)
        mau = json.loads(dong[0][len("var MAU_TOM_TAT = "):].rstrip().rstrip(";"))
        self.assertEqual(self.chay("MAU_TOM_TAT"), mau)
        self.assertEqual(self.chay("taoLoiNhacTomTat({})").startswith(mau), True)

    def test_so_lieu_thieu_van_tao_duoc_loi_nhac(self):
        loi_nhac = self.chay("taoLoiNhacTomTat({don_hang: {tong: 'abc', cho_duyet: -1}})")
        so_lieu = json.loads(loi_nhac[loi_nhac.index("{"):])
        self.assertEqual(so_lieu, {})

    def test_khong_co_ten_tuy_y_di_vao_so_lieu_gui_ai(self):
        loi_nhac = self.chay("taoLoiNhacTomTat({__proto__: {x: 1}, constructor: 'a', don_hang: {tong: 2, toString: 'b'}})")
        self.assertEqual(json.loads(loi_nhac[loi_nhac.index("{"):]), {"don_hang": {"tong": 2}})


@unittest.skipUnless(NODE, "cần node")
class KhuMayTram(unittest.TestCase):
    """Chạy khu [M] bằng DOM giả tối thiểu: dựng bảng bằng textContent, gọi đúng điểm nhận Node-RED, giữ lựa chọn dở dang."""
    HARNESS = r"""
const vm = require('vm'), fs = require('fs');
function El(tag) {
  const e = { tag, children: [], attrs: {}, ls: {}, hidden: false, className: '', value: '', _t: '' };
  e.appendChild = c => { e.children.push(c); return c; };
  e.removeChild = c => { e.children.splice(e.children.indexOf(c), 1); };
  Object.defineProperty(e, 'firstChild', { get: () => e.children[0] || null });
  e.setAttribute = (k, v) => { e.attrs[k] = v; };
  e.addEventListener = (k, f) => { e.ls[k] = f; };
  e.contains = n => n === e || e.children.some(c => c.contains(n));
  Object.defineProperty(e, 'textContent', { get: () => e._t + e.children.map(c => c.textContent).join('|'), set: v => { e._t = String(v); e.children = []; } });
  return e;
}
const ids = {};
['bang-may-xin-vao', 'm-chua-co-phong', 'm-loi', 'm-kq'].forEach(i => { ids[i] = El('x'); });
const goi = [];
let tra = null;
const ctx = vm.createContext({
  document: { getElementById: i => ids[i] || null, createElement: El, addEventListener() {}, hidden: false, activeElement: null },
  window: {}, console, setTimeout, setInterval, clearInterval,
  fetch: (url, o) => { goi.push({ url, method: o.method, body: o.body ? JSON.parse(o.body) : null });
    return Promise.resolve({ ok: true, text: () => Promise.resolve(JSON.stringify(tra)) }); },
});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const chay = b => vm.runInContext(b, ctx);
const doi = () => new Promise(r => setTimeout(r, 30));
const dong = () => ids['bang-may-xin-vao'].children.map(tr => tr.children.map(td => td.textContent));
const YC = (id, tt, them) => Object.assign({ id: id.repeat(32), ten: 'kt-' + id, phong_xin: 'ke-toan', hostname: 'pc-' + id, ip: '10.0.0.' + id, ma_so: null, luc: 1700000000, trang_thai: tt }, them);
const PB = [{ ma: 'ke-toan', ten: 'Phòng Kế toán' }, { ma: 'kho', ten: 'Phòng Kho' }];
const kq = {};
(async () => {
  tra = { yeu_cau: [YC('a', 'CHO_DUYET', { ma_so: '012345' }), YC('b', 'CHO_MA'), YC('c', 'LOI', { loi: 'không mã hóa được' }), YC('d', 'DANG_CAP', { phong_xin: '' })], phong_ban: PB };
  await chay('taiMay(true)');
  kq.url = goi[0].url;
  kq.dong = dong();
  const hang = ids['bang-may-xin-vao'].children[0];
  kq.maClass = hang.children[4].className;
  const thaoTac = hang.children[7];
  const oMa = thaoTac.children[0].children[0], oChon = thaoTac.children[0].children[1], nutDuyet = thaoTac.children[0].children[2];
  kq.chonRong = oChon.children.map(o => o.value + '=' + o.textContent);
  kq.chonGiaTri = oChon.value;
  kq.nutHang1 = thaoTac.children[0].children.map(c => c.textContent);
  kq.maPlaceholder = oMa.placeholder;
  // Duyệt phải gõ lại mã 6 số: chưa gõ thì nút tắt và bấm cũng không gọi Box
  kq.duyetTatBanDau = nutDuyet.disabled;
  const truocMa = goi.length;
  nutDuyet.ls.click();
  kq.duyetThieuMa = { goi: goi.length - truocMa, kq: ids['m-kq'].textContent, loi: ids['m-kq'].className };
  oMa.value = '01 23'; oMa.ls.input(); kq.tatKhi5So = nutDuyet.disabled;
  oMa.value = '012 345'; oMa.ls.input(); kq.batKhi6So = !nutDuyet.disabled;
  kq.nutHang2 = thaoTac.children[1].children.map(c => c.textContent);
  kq.khongNutCuaDongKhac = ids['bang-may-xin-vao'].children.slice(1).map(tr => tr.children[7].textContent);
  kq.canhBaoPhong = ids['m-chua-co-phong'].hidden;
  // Từ chối không ghi lý do: không gọi Box
  const truoc = goi.length;
  thaoTac.children[1].children[1].ls.click();
  kq.tuChoiTrong = { goi: goi.length - truoc, kq: ids['m-kq'].textContent, loi: ids['m-kq'].className };
  // đổi phòng + gõ lý do rồi tải lại: lựa chọn dở dang còn nguyên
  oChon.value = 'kho'; oChon.ls.change();
  const oLy = thaoTac.children[1].children[0]; oLy.value = 'Mã lệch'; oLy.ls.input();
  await chay('taiMay(true)');
  const t2 = ids['bang-may-xin-vao'].children[0].children[7];
  kq.giuChon = t2.children[0].children[1].value; kq.giuLyDo = t2.children[1].children[0].value;
  kq.giuMa = t2.children[0].children[0].value; kq.giuNutBat = !t2.children[0].children[2].disabled;
  // duyệt
  tra = { yeu_cau: [], phong_ban: PB };
  t2.children[0].children[2].ls.click();
  await doi();
  const post = goi.filter(g => g.method === 'POST');
  kq.duyet = post[0]; kq.sauDuyet = goi[goi.length - 1].url; kq.thongBaoDuyet = ids['m-kq'].textContent;
  kq.bangRong = dong();
  // từ chối có lý do
  tra = { yeu_cau: [YC('e', 'CHO_DUYET', { ma_so: '999000' })], phong_ban: PB };
  await chay('taiMay(true)');
  const t3 = ids['bang-may-xin-vao'].children[0].children[7];
  const oLy3 = t3.children[1].children[0]; oLy3.value = '  Mã khác  '; oLy3.ls.input();
  t3.children[1].children[1].ls.click();
  await doi();
  kq.tuChoi = goi.filter(g => g.method === 'POST')[1];
  // không có phòng ban: nhắc tạo phòng, vẫn từ chối được nhưng không có ô chọn phòng/nút Duyệt
  tra = { yeu_cau: [YC('f', 'CHO_DUYET', { ma_so: '000001' })], phong_ban: [] };
  await chay('taiMay(true)');
  kq.khongPhong = { canhBao: ids['m-chua-co-phong'].hidden, hang: ids['bang-may-xin-vao'].children[0].children[7].children.length,
                    ma: ids['bang-may-xin-vao'].children[0].children[4].textContent };
  // đang gõ trong bảng: tự tải lại bị bỏ qua, không mất chữ
  const nTruoc = goi.length;
  ctx.document.activeElement = ids['bang-may-xin-vao'].children[0].children[7].children[0].children[0];
  await chay('taiMay(false)');
  kq.boQuaKhiDangGo = goi.length === nTruoc;
  kq.dinhDang = chay("[dinhDangMa('012345'), dinhDangMa(null), dinhDangMa('12345'), dinhDangMa('1234567'), dinhDangMa('ab1234')]");
  kq.nhan = chay("[nhanTrangThaiMay({trang_thai:'LOI', loi:'x'}), nhanTrangThaiMay({trang_thai:'CHO_DUYET'}), nhanTrangThaiMay({trang_thai:'?'})]");
  console.log(JSON.stringify(kq));
})().catch(e => { console.error(e); process.exit(1); });
"""

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([NODE, "-e", cls.HARNESS, JS], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        cls.kq = json.loads(r.stdout)

    def test_bang_yeu_cau_dung_cot_va_goi_dung_diem_nhan(self):
        k = self.kq
        self.assertEqual(k["url"], "/quy-trinh/webhook/onebee-may-xin-vao")
        self.assertEqual(k["dong"][0][:3], ["kt-a", "pc-a", "10.0.0.a"])
        self.assertEqual(k["dong"][0][3], "ke-toan")
        self.assertEqual(k["dong"][0][4], "012 345")                 # mã đối chiếu hiển thị "123 456"
        self.assertEqual(k["maClass"], "ma-doi-chieu")
        self.assertEqual(k["dong"][0][6], "Chờ duyệt")
        self.assertEqual(k["dong"][1][4], "—")                      # chưa có mã (máy chưa gửi bước 3)
        self.assertEqual(k["dong"][1][6], "Chờ máy hiện mã")
        self.assertEqual(k["dong"][2][6], "Lỗi: không mã hóa được")
        self.assertEqual(k["dong"][3][3], "—")
        self.assertEqual(k["dong"][3][6], "Đang cấp khóa")

    def test_chi_dong_cho_duyet_co_nut_va_phong_mac_dinh_la_phong_xin(self):
        k = self.kq
        self.assertEqual(k["chonRong"], ["ke-toan=Phòng Kế toán (ke-toan)", "kho=Phòng Kho (kho)"])
        self.assertEqual(k["chonGiaTri"], "ke-toan")
        self.assertEqual(k["nutHang1"][-1], "Duyệt")
        self.assertEqual(k["nutHang2"][-1], "Từ chối")
        self.assertEqual(k["khongNutCuaDongKhac"], ["—", "—", "—"])
        self.assertTrue(k["canhBaoPhong"])                           # có phòng ban thì ẩn dòng nhắc tạo phòng

    def test_tu_choi_bat_buoc_ly_do_va_giu_lua_chon_khi_tai_lai(self):
        k = self.kq
        self.assertEqual(k["tuChoiTrong"], {"goi": 0, "kq": "Từ chối phải ghi lý do.", "loi": "thong-bao loi"})
        self.assertEqual((k["giuChon"], k["giuLyDo"], k["giuMa"], k["giuNutBat"]), ("kho", "Mã lệch", "012 345", True))
        self.assertTrue(k["boQuaKhiDangGo"])

    def test_duyet_bat_buoc_go_lai_ma_6_so(self):
        k = self.kq
        self.assertIn("6 số", k["maPlaceholder"])
        self.assertTrue(k["duyetTatBanDau"])                          # chưa gõ mã thì nút Duyệt tắt
        self.assertEqual(k["duyetThieuMa"]["goi"], 0)                 # bấm vào cũng không gọi Box
        self.assertIn("Gõ đủ 6 số", k["duyetThieuMa"]["kq"])
        self.assertEqual(k["duyetThieuMa"]["loi"], "thong-bao loi")
        self.assertTrue(k["tatKhi5So"])
        self.assertTrue(k["batKhi6So"])                               # đủ 6 số (bỏ qua dấu cách) thì bật

    def test_duyet_gui_phong_da_chon_roi_tai_lai_bang(self):
        k = self.kq
        self.assertEqual(k["duyet"]["url"], "/quy-trinh/webhook/onebee-duyet-may")
        self.assertEqual(k["duyet"]["body"], {"id": "a" * 32, "quyet_dinh": "DUYET", "phong": "kho", "ly_do": "", "ma_so": "012345"})
        self.assertEqual(k["sauDuyet"], "/quy-trinh/webhook/onebee-may-xin-vao")
        self.assertIn("Đã duyệt máy kt-a vào phòng kho", k["thongBaoDuyet"])
        self.assertEqual(k["bangRong"], [["Chưa có máy nào xin vào."]])
        self.assertEqual(k["tuChoi"]["body"], {"id": "e" * 32, "quyet_dinh": "TU_CHOI", "phong": "", "ly_do": "Mã khác", "ma_so": ""})

    def test_chua_co_phong_ban_nhac_tao_phong_va_khong_co_nut_duyet(self):
        k = self.kq["khongPhong"]
        self.assertFalse(k["canhBao"])
        self.assertEqual(k["hang"], 1)                               # chỉ còn hàng lý do + Từ chối
        self.assertEqual(k["ma"], "000 001")

    def test_dinh_dang_ma_va_nhan_trang_thai(self):
        self.assertEqual(self.kq["dinhDang"], ["012 345", "—", "—", "—", "—"])
        self.assertEqual(self.kq["nhan"], ["Lỗi: x", "Chờ duyệt", "Không rõ"])


class BoCaiVaNoiTrang(unittest.TestCase):
    def test_thu_muc_trang_duoc_tao_truoc_khi_sinh_trang(self):
        with open(os.path.join(STACK, "tasks/main.yml"), encoding="utf-8") as f:
            viec = yaml.safe_load(f)
        vi_tri_thu_muc = vi_tri_trang = None
        for i, t in enumerate(viec):
            noi_dung = json.dumps(t, ensure_ascii=False)
            if "portal/site/so-dieu-hanh" in noi_dung and "ansible.builtin.file" in t and vi_tri_thu_muc is None:
                vi_tri_thu_muc = i
            if "so-dieu-hanh.html.j2" in noi_dung and vi_tri_trang is None:
                vi_tri_trang = i
        self.assertIsNotNone(vi_tri_thu_muc, "chưa có việc tạo thư mục portal/site/so-dieu-hanh")
        self.assertIsNotNone(vi_tri_trang, "chưa có việc sinh trang so-dieu-hanh")
        self.assertLessEqual(vi_tri_thu_muc, vi_tri_trang)
        noi_dung = json.dumps(viec, ensure_ascii=False)
        for tep in ("so-dieu-hanh.css", "so-dieu-hanh.js", "portal/site/so-dieu-hanh/index.html"):
            self.assertIn(tep, noi_dung)

    def test_trang_chu_tro_toi_ung_dung_thay_bieu_mau_cu(self):
        h = render(os.path.join(STACK, "templates/index.html.j2"), onebee_box_ten_mdns="onebee", onebee_https_hieu_luc=True)
        self.assertIn('href="/so-dieu-hanh/"', h)
        self.assertIn("Sổ điều hành", h)
        self.assertNotIn("form/onebee-ho-tro", h)
        self.assertNotIn("form/onebee-don-hang", h)

    def test_trang_chu_o_che_do_http_khong_dan_toi_tuyen_khong_co(self):
        h = render(os.path.join(STACK, "templates/index.html.j2"), onebee_box_ten_mdns="onebee", onebee_https_hieu_luc=False)
        self.assertNotIn('href="/so-dieu-hanh/"', h)
        self.assertIn("HTTPS", h)

    def test_menu_bao_can_ho_tro_mo_ung_dung_tren_ten_box(self):
        with open(MUC_MENU, encoding="utf-8") as f:
            viec = yaml.safe_load(f)
        conf = next(t for t in viec if t.get("name", "").startswith("Ghi địa chỉ"))
        noi_dung = conf["ansible.builtin.copy"]["content"]
        self.assertIn("HO_TRO_URL=https://{{ onebee_may_tram.BOX_TEN }}/so-dieu-hanh/", noi_dung)
        self.assertNotIn("5678", noi_dung)
        self.assertNotIn("form/", noi_dung)
        dieu_kien = json.dumps(conf["when"])
        self.assertIn("BOX_TEN", dieu_kien)
        self.assertIn("BOX_HTTPS", dieu_kien)


class TuyenCaddy(unittest.TestCase):
    """Không cần Caddy thật (bài có Caddy thật ở test_onebee_caddy_sso.py): kiểm văn bản Caddyfile sinh ra."""

    def caddyfile(self, **them):
        return render(os.path.join(STACK, "templates/Caddyfile.j2"), onebee_box_ports={"portal": 80,
                                                                                         "rest_server": 8000, "uptime_kuma": 3001}, **them)

    def khoi(self, nd, mo_dau):
        i = nd.index(mo_dau)
        sau = nd[i:]
        return sau[:sau.index("\n\t}\n") + 4] if "\n\t}\n" in sau else sau

    def test_co_sso_trang_nam_sau_forward_auth(self):
        nd = self.caddyfile()
        k = self.khoi(nd, "@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\thandle @so_dieu_hanh {")
        self.assertIn("import onebee_sso", k)
        self.assertLess(k.index("import onebee_sso"), k.index("file_server"))
        self.assertIn("root * /srv\n", k)
        for tieu_de in ("Content-Security-Policy", "default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'self'",
                        "form-action 'none'", "frame-ancestors 'none'", "base-uri 'none'", "Cache-Control", "X-Content-Type-Options nosniff"):
            self.assertIn(tieu_de, k, tieu_de)
        self.assertNotIn("unsafe-inline", k)
        self.assertNotIn("unsafe-eval", k)

    def test_vao_bang_ip_chuyen_sang_ten_box(self):
        nd = self.caddyfile()
        khoi_ip = nd[nd.index("https://192.168.1.10:443 {"):nd.index("https://box.anphu.onebee.internal:443 {")]
        self.assertIn("@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*", khoi_ip)
        self.assertIn("redir https://box.anphu.onebee.internal{uri} 308", khoi_ip)

    def test_sso_tam_tat_tra_503(self):
        nd = self.caddyfile(onebee_sso_hieu_luc=False)
        k = self.khoi(nd, "@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\thandle @so_dieu_hanh {")
        self.assertIn("respond", k)
        self.assertIn("503", k)
        self.assertNotIn("file_server", k)

    def test_che_do_http_khong_co_ung_dung(self):
        nd = self.caddyfile(onebee_https_hieu_luc=False)
        self.assertIn("@so_dieu_hanh path /so-dieu-hanh /so-dieu-hanh/*\n\trespond @so_dieu_hanh 404", nd)
        self.assertLess(nd.index("respond @so_dieu_hanh 404"), nd.index("file_server"))


class LuatAuthelia(unittest.TestCase):
    def test_luat_cho_trang(self):
        with tempfile.TemporaryDirectory():
            cfg = yaml.safe_load(render(os.path.join(ROLES, "box-dinh-danh/templates/configuration.yml.j2")))
        luat = [r for r in cfg["access_control"]["rules"] if any("so-dieu-hanh" in x for x in r.get("resources", []))]
        self.assertEqual(len(luat), 2)
        theo_nhom = {tuple(r["subject"]): r["policy"] for r in luat}
        self.assertEqual(theo_nhom, {("group:ky_thuat", "group:quan_ly", "group:thu_kho", "group:ke_toan"): "two_factor",
                                     ("group:nhan_vien",): "one_factor"})
        for r in luat:
            self.assertEqual(r["domain"], "box.anphu.onebee.internal")
            for duong in ("/so-dieu-hanh/", "/so-dieu-hanh", "/so-dieu-hanh/so-dieu-hanh.js",
                          "/so-dieu-hanh/so-dieu-hanh-kho.js", "/so-dieu-hanh/?may=ketoan-01"):
                self.assertTrue(any(re.search(x, duong) for x in r["resources"]), duong)
            for duong in ("/so-dieu-hanh-gia/", "/x/so-dieu-hanh/", "/so-dieu-hanhx"):
                self.assertFalse(any(re.search(x, duong) for x in r["resources"]), duong)


if __name__ == "__main__":
    unittest.main()
