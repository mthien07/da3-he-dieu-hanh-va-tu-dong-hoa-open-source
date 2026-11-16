# SPDX-License-Identifier: MIT
"""Kiểm thử kho tệp của OneBee Box (không cần Docker): dịch vụ SeaweedFS + cổng /files/ (chỉ HTTPS, sau forward_auth,
không công bố cổng), image ClamAV dựng cục bộ đã bỏ libclamunrar, kiểm dịch từng lượt (sạch mới vào kho, nhiễm bị chặn),
metadata ghi/đọc qua cầu nối danh tính bằng JWT của người dùng (RLS), giới hạn 10 MB và danh mục đuôi cho phép.
Chạy: python3 -m unittest"""
import hashlib
import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jinja2
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
ROLE = os.path.join(ROOT, "box/ansible/roles/box-kho-tep")
KHO_TEP_PY = os.path.join(ROLE, "files/onebee-kho-tep.py")
DOCKERFILE = os.path.join(ROLE, "files/clamav-khong-unrar.Dockerfile")
TASKS = os.path.join(ROLE, "tasks/main.yml")
TEMPLATES = os.path.join(ROOT, "box/ansible/roles/box-stack/templates")
GROUP_VARS = os.path.join(ROOT, "box/ansible/group_vars/all.yml")
SITE = os.path.join(ROOT, "box/ansible/site.yml")
LUOC_DO = os.path.join(ROOT, "box/ansible/roles/box-du-lieu/files/luoc-do")
GIA_TRI = yaml.safe_load(open(GROUP_VARS, encoding="utf-8"))
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def nap_module():
    spec = importlib.util.spec_from_file_location("onebee_kho_tep", KHO_TEP_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ve(ten_mau: str, **bien) -> str:
    v = dict(GIA_TRI, onebee_box_ip="192.168.1.50", onebee_box_ma_don_vi="anphu",
             onebee_https_hieu_luc=True, onebee_sso_hieu_luc=True, onebee_kuma_dia_chi="0.0.0.0")
    v.update(bien)
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True)   # như Ansible
    env.filters["bool"] = bool
    with open(os.path.join(TEMPLATES, ten_mau), encoding="utf-8") as f:
        return env.from_string(f.read()).render(**v)


class CauHinhKhoTep(unittest.TestCase):
    def test_compose_hai_dich_vu_khong_cong_bo_cong_va_o_dung_mang(self):
        for https in (False, True):
            c = yaml.safe_load(ve("docker-compose.yml.j2", onebee_https_hieu_luc=https))
            s = c["services"]
            for ten in ("seaweedfs", "kho-tep"):
                self.assertNotIn("ports", s[ten], (ten, https))
                self.assertIn("no-new-privileges:true", s[ten]["security_opt"], (ten, https))
                self.assertEqual(s[ten]["logging"], c["x-logging"], (ten, https))
        self.assertEqual(s["seaweedfs"]["image"], GIA_TRI["onebee_box_images"]["seaweedfs"])
        self.assertEqual(s["kho-tep"]["image"], "onebee/clamav-khong-unrar:1.5.4")
        self.assertEqual(s["seaweedfs"]["networks"], ["kho_tep"])
        self.assertEqual(set(s["kho-tep"]["networks"]), {"sso", "kho_tep"})
        self.assertEqual(s["kho-tep"]["command"], ["serve"])          # thay CMD /init của image ClamAV (không clamd)
        self.assertIn("healthcheck", s["kho-tep"])                     # kiểm cổng tệp, không phải clamd của image
        self.assertTrue(c["networks"]["kho_tep"]["internal"])
        self.assertTrue(any(v.endswith(":/var/lib/clamav:ro") for v in s["kho-tep"]["volumes"]))
        self.assertTrue(any(v.endswith(":/data/kho-tep") for v in s["kho-tep"]["volumes"]))
        self.assertIn("CAU_NOI_URL", s["kho-tep"]["environment"])       # metadata qua cầu nối, không nối thẳng PostgREST
        self.assertNotIn("PGRST_DB_URI", s["kho-tep"]["environment"])

    def test_dockerfile_dung_cach_2_bo_libclamunrar_va_ghim_digest(self):
        noi_dung = open(DOCKERFILE, encoding="utf-8").read()
        self.assertIn(GIA_TRI["onebee_box_images"]["clamav"], noi_dung)
        self.assertIn("rm -f /usr/lib/libclamunrar.so* /usr/lib/libclamunrar_iface.so*", noi_dung)
        self.assertRegex(noi_dung, r"(?m)^FROM scratch$")
        self.assertIn("COPY --from=goc / /", noi_dung)
        for ten in ("seaweedfs", "clamav"):
            self.assertRegex(GIA_TRI["onebee_box_images"][ten], r":4\.53@sha256:[0-9a-f]{64}$" if ten == "seaweedfs"
                             else r":1\.5\.4-debian13-slim@sha256:[0-9a-f]{64}$")

    def test_role_dung_image_chi_khi_dockerfile_doi_va_chay_2_dich_vu(self):
        ds = yaml.safe_load(open(TASKS, encoding="utf-8"))
        dung = next(t for t in ds if "Dựng image" in t.get("name", ""))
        self.assertIn("onebee_clamav_dockerfile is changed",
                      dung["when"] if isinstance(dung["when"], str) else " ".join(dung["when"]))
        self.assertIn("docker image inspect", yaml.safe_dump(next(t for t in ds if "Kiểm image" in t.get("name", ""))))
        lenh = [str(t.get("ansible.builtin.command", "")) for t in ds]
        self.assertTrue(any("up -d --no-deps seaweedfs" in x for x in lenh))
        self.assertTrue(any("up -d --no-deps" in x and "kho-tep" in x for x in lenh))
        self.assertFalse(any("--no-deps ollama" in x and "kho-tep" in x for x in lenh))   # không chờ ở box-stack

    def test_caddy_files_chi_o_https_sau_forward_auth(self):
        https = ve("Caddyfile.j2")
        dau = https.index("handle /files/*")
        khoi = https[dau:https.index("\n\t}", dau)]
        self.assertLess(khoi.index("import onebee_sso"), khoi.index("reverse_proxy kho-tep:8080"))
        self.assertIn("uri strip_prefix /files", khoi)
        self.assertIn("max_size 11MB", khoi)
        http = ve("Caddyfile.j2", onebee_https_hieu_luc=False, onebee_sso_hieu_luc=False)
        self.assertNotIn("kho-tep", http)                                  # HTTP: tuyến không tồn tại
        tat_sso = ve("Caddyfile.j2", onebee_sso_hieu_luc=False)
        self.assertNotIn("reverse_proxy kho-tep", tat_sso)                 # SSO tạm tắt: đóng, không mở toang
        self.assertIn('respond "Đăng nhập một lần đang tạm tắt', tat_sso)

    def test_luoc_do_004_cap_quyen_metadata_theo_nguoi_tao(self):
        sql = open(os.path.join(LUOC_DO, "004-kho-tep.sql"), encoding="utf-8").read()
        for cot in ("khoa_luu_tru", "trang_thai_quet", "ket_qua_quet"):
            self.assertIn(cot, sql)
        self.assertIn("CREATE POLICY nhan_vien_them ON onebee.tep_dinh_kem FOR INSERT TO nhan_vien", sql)
        self.assertIn("nguoi_tao = onebee_noi_bo.nguoi_dung()", sql)
        self.assertIn("GRANT INSERT (ten_tep, kich_thuoc, sha256, khoa_luu_tru, trang_thai_quet, ket_qua_quet)", sql)
        self.assertIn("CREATE POLICY nhan_vien_doc ON onebee.tep_dinh_kem FOR SELECT TO nhan_vien", sql)
        self.assertIn("GRANT SELECT ON onebee.tep_dinh_kem TO ky_thuat, quan_ly", sql)
        self.assertNotRegex(sql, r"GRANT [^;]*\b(?:UPDATE|DELETE)\b")
        self.assertIn("FORCE ROW LEVEL SECURITY", open(os.path.join(LUOC_DO, "001-khoi-tao.sql"), encoding="utf-8").read())

    def test_site_sao_luu_va_chan_doan_co_kho_tep(self):
        roles = [r if isinstance(r, str) else r["role"]
                 for r in yaml.safe_load(open(SITE, encoding="utf-8"))[0]["roles"]]
        self.assertEqual(roles[roles.index("box-du-lieu") + 1], "box-kho-tep")
        sao = open(os.path.join(TEMPLATES, "onebee-box-sao-luu.sh.j2"), encoding="utf-8").read()
        self.assertIn("seaweedfs kho-tep", sao)                 # tạm dừng khi chụp để volume nhất quán
        self.assertIn('"${DATA}/seaweedfs"', sao)               # dữ liệu kho tệp nằm trong bản sao lưu
        self.assertIn('rm -rf "${DATA}/ai-rag"', sao)
        self.assertIn('"${DATA}/seaweedfs" "${KET_XUAT_DIR}"', sao)   # xóa trước khi khôi phục
        chan = open(os.path.join(TEMPLATES, "onebee-box-chan-doan.sh.j2"), encoding="utf-8").read()
        self.assertIn("kiem_kho_tep", chan)
        self.assertIn("chu_ky_clamav", chan)
        self.assertIn("onebee-seaweedfs", chan)
        self.assertIn("onebee-kho-tep", chan)


class FilerGia:
    """SeaweedFS filer giả: nhận multipart POST (đường dẫn là khóa đối tượng), trả lại qua GET."""

    def __init__(self):
        self.tep = {}
        self.yeu_cau = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _xong(self, ma):
                self.send_response(ma)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self):  # noqa: N802
                than = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                outer.yeu_cau.append({"method": "POST", "path": self.path})
                outer.tep[self.path] = bo_multipart(than, self.headers.get("Content-Type") or "")
                self._xong(201)

            def do_GET(self):  # noqa: N802
                if self.path not in outer.tep:
                    return self._xong(404)
                du_lieu = outer.tep[self.path]
                self.send_response(200)
                self.send_header("Content-Length", str(len(du_lieu)))
                self.end_headers()
                self.wfile.write(du_lieu)

            def do_DELETE(self):  # noqa: N802
                outer.tep.pop(self.path, None)
                self._xong(204)

        self.sv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.sv.daemon_threads = True
        threading.Thread(target=self.sv.serve_forever, daemon=True).start()


def bo_multipart(than: bytes, loai: str) -> bytes:
    rong = loai.split("boundary=")[1].encode()
    for phan in than.split(b"--" + rong):
        if b"Content-Disposition" in phan:
            return phan.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
    raise AssertionError("không thấy phần tệp trong multipart")


class CauNoiGia:
    """Cầu nối danh tính + PostgREST giả: ký danh tính từ Remote-User (như thật) và áp RLS đơn giản cho tep_dinh_kem."""

    def __init__(self):
        self.dong = []
        self.yeu_cau = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _nguoi(self):
                nguoi = self.headers.get("Remote-User") or ""
                nhom = [x for x in (self.headers.get("Remote-Groups") or "").split(",") if x]
                return nguoi, nhom

            def _tra(self, ma, du_lieu):
                raw = json.dumps(du_lieu, ensure_ascii=False).encode()
                self.send_response(ma)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):  # noqa: N802
                nguoi, nhom = self._nguoi()
                than = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                ban_ghi = json.loads(than)
                outer.yeu_cau.append({"method": "POST", "path": self.path, "nguoi": nguoi, "nhom": nhom,
                                      "prefer": self.headers.get("Prefer"), "than": ban_ghi})
                if not nguoi:
                    return self._tra(401, {"loi": "Chưa đăng nhập"})
                dong = dict(ban_ghi, nguoi_tao=nguoi, id=len(outer.dong) + 1)   # như DEFAULT nguoi_tao từ JWT
                outer.dong.append(dong)
                self._tra(201, [dong])

            def do_GET(self):  # noqa: N802
                nguoi, nhom = self._nguoi()
                url = urllib.parse.urlsplit(self.path)
                outer.yeu_cau.append({"method": "GET", "path": url.path, "query": url.query, "nguoi": nguoi, "nhom": nhom})
                if not nguoi:
                    return self._tra(401, {"loi": "Chưa đăng nhập"})
                ds = [d for d in outer.dong
                      if d["nguoi_tao"] == nguoi or any(n in ("quan_ly", "ky_thuat") for n in nhom)]
                tham_so = urllib.parse.parse_qs(url.query)
                if "id" in tham_so and tham_so["id"][0].startswith("eq."):
                    ma = int(tham_so["id"][0][3:])
                    ds = [d for d in ds if d["id"] == ma]
                self._tra(200, ds)

        self.sv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.sv.daemon_threads = True
        threading.Thread(target=self.sv.serve_forever, daemon=True).start()


class KhoTepStoreTest(unittest.TestCase):
    def setUp(self):
        self.mod = nap_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.filer = FilerGia()
        self.cau_noi = CauNoiGia()
        self.clamscan = os.path.join(self.tmp.name, "clamscan-gia")
        with open(self.clamscan, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\ntep="${3:-}"\n'
                    'grep -q "EICAR-STANDARD-ANTIVIRUS-TEST-FILE" "$tep" && { echo "$tep: Eicar-Test-Signature FOUND"; exit 1; }\n'
                    'echo "$tep: OK"\nexit 0\n')
        os.chmod(self.clamscan, 0o755)
        self.store = self.mod.KhoTepStore(
            goc_dir=os.path.join(self.tmp.name, "kho-tep"),
            filer_url="http://127.0.0.1:%d" % self.filer.sv.server_port,
            cau_noi_url="http://127.0.0.1:%d" % self.cau_noi.sv.server_port,
            clamscan_cmd=self.clamscan,
            clamav_dir=os.path.join(self.tmp.name, "clamav"),
        )

    def tearDown(self):
        for sv in (self.filer.sv, self.cau_noi.sv):
            sv.shutdown()
            sv.server_close()
        self.tmp.cleanup()

    def test_gioi_han_va_danh_muc_dung_dac_ta(self):
        self.assertEqual(self.mod.MAX_UPLOAD_BYTES, 10 * 1024 * 1024)
        self.assertEqual(self.mod.DUOI_CHO_PHEP, (".pdf", ".png", ".jpg", ".txt", ".docx", ".xlsx", ".odt", ".ods"))

    def test_tep_sach_201_ghi_metadata_qua_cau_noi_va_tai_lai_dung_sha(self):
        noi_dung = "Hợp đồng mua bán mật ong hoa nhãn số 01/2026.".encode("utf-8")
        ma, kq = self.store.luu_va_quet("an", ["nhan_vien"], "hop-dong.txt", noi_dung)
        self.assertEqual(ma, 201, kq)
        tep = kq["tep"]
        self.assertEqual(tep["trang_thai_quet"], "CLEAN")
        self.assertEqual(tep["sha256"], hashlib.sha256(noi_dung).hexdigest())
        self.assertEqual(tep["nguoi_tao"], "an")
        ghi = self.cau_noi.yeu_cau[-1]
        self.assertEqual((ghi["method"], ghi["nguoi"], ghi["nhom"]), ("POST", "an", ["nhan_vien"]))
        self.assertEqual(ghi["prefer"], "return=representation")
        self.assertNotIn("nguoi_tao", ghi["than"])            # CSDL lấy từ JWT, không tin trường do máy khách gửi
        self.assertIn(tep["khoa_luu_tru"], self.filer.tep)     # tệp sạch đã vào SeaweedFS
        ma_tai, du_lieu, loai = self.store.doc_tep("an", ["nhan_vien"], tep["id"])
        self.assertEqual((ma_tai, du_lieu, loai), (200, noi_dung, "application/octet-stream"))

    def test_eicar_bi_cach_ly_khong_vao_kho_va_khong_tai_duoc(self):
        ma, kq = self.store.luu_va_quet("an", ["nhan_vien"], "eicar.txt", EICAR)
        self.assertEqual(ma, 422, kq)
        tep = kq["tep"]
        self.assertEqual(tep["trang_thai_quet"], "INFECTED")
        self.assertIn("Eicar-Test-Signature", tep["ket_qua_quet"])
        self.assertEqual(self.filer.tep, {})                   # tuyệt đối không đẩy tệp nhiễm vào kho
        self.assertEqual(len(os.listdir(self.store.cach_ly_dir)), 1)
        self.assertEqual(self.store.doc_tep("an", ["nhan_vien"], tep["id"])[0], 422)

    def test_duoi_ngoai_danh_muc_415_va_qua_lon_413_khong_ghi_metadata(self):
        self.assertEqual(self.store.luu_va_quet("an", ["nhan_vien"], "ma-doc.exe", b"MZ\x90\x00")[0], 415)
        lon = b"x" * (self.mod.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(self.store.luu_va_quet("an", ["nhan_vien"], "qua-lon.txt", lon)[0], 413)
        self.assertEqual(self.cau_noi.yeu_cau, [])
        self.assertEqual(self.filer.tep, {})

    def test_loi_clamscan_khong_bao_gio_coi_la_sach(self):
        store = self.mod.KhoTepStore(
            goc_dir=os.path.join(self.tmp.name, "kho-hong"),
            filer_url="http://127.0.0.1:%d" % self.filer.sv.server_port,
            cau_noi_url="http://127.0.0.1:%d" % self.cau_noi.sv.server_port,
            clamscan_cmd=os.path.join(self.tmp.name, "khong-co-clamscan"),
        )
        ma, kq = store.luu_va_quet("an", ["nhan_vien"], "hop-dong.txt", b"noi dung")
        self.assertEqual(ma, 503, kq)
        self.assertEqual(self.filer.tep, {})                   # chưa quét được thì không vào kho

    def test_nhan_vien_khac_khong_doc_duoc_metadata_lan_tep(self):
        ma, kq = self.store.luu_va_quet("an", ["nhan_vien"], "hop-dong.txt", b"noi dung cua an")
        self.assertEqual(ma, 201)
        id_an = kq["tep"]["id"]
        self.assertEqual(self.store.doc_tep("chi", ["nhan_vien"], id_an)[0], 404)
        self.assertEqual(self.store.danh_sach("chi", ["nhan_vien"]), (200, []))
        self.assertEqual(self.store.doc_tep("binh", ["quan_ly"], id_an)[0], 200)   # quản lý đọc để điều tra

    def test_cap_nhat_chu_ky_clamav_ngoai_tuyen(self):
        nguon = os.path.join(self.tmp.name, "usb")
        dich = os.path.join(self.tmp.name, "clamav")
        os.makedirs(nguon)
        with open(os.path.join(nguon, "daily.cvd"), "wb") as f:
            f.write(b"ClamAV-VDB:" + b"x" * 100)
        self.assertEqual(self.mod.cap_nhat_chu_ky_clamav(nguon, dich), ["daily.cvd"])
        self.assertTrue(os.path.exists(os.path.join(dich, "daily.cvd")))
        rong = os.path.join(self.tmp.name, "usb-rong")
        os.makedirs(rong)
        with self.assertRaises(ValueError):
            self.mod.cap_nhat_chu_ky_clamav(rong, dich)


if __name__ == "__main__":
    unittest.main()
