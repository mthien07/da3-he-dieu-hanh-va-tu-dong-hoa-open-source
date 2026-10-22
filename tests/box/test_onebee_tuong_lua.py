#!/usr/bin/env python3
"""Kiểm thử tường lửa OneBee Box (box-firewall/files/onebee-tuong-lua) bằng iptables GIẢ ghi lại từng lệnh (không đụng tường lửa thật).
Kiểm cấu trúc quy tắc (rà soát bảo mật F5): lọc MỌI cổng mạng trừ lo/docker*/br-*; LAN chỉ qua cổng mạng chính; Tailscale chỉ địa chỉ khai báo;
chạy lại không nhân đôi quy tắc. Chạy: python3 -m unittest"""
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "../../box/ansible/roles/box-firewall/files/onebee-tuong-lua")

IPT_GIA = r'''#!/bin/bash
# iptables giả: nhớ trạng thái trong thư mục $ONEBEE_FW (một file mỗi chuỗi, mỗi dòng một quy tắc dạng "-A chuỗi …");
# bảng khác filter (-t mangle) nằm trong thư mục con cùng tên
d="$ONEBEE_FW/$(basename "$0")"; mkdir -p "$d"
echo "$0 $*" >> "$ONEBEE_FW/lenh.log"
if [ "$1" = -t ]; then [ "$2" = filter ] || d="$d/$2"; mkdir -p "$d"; shift 2; fi
# ONEBEE_FW_MANGLE_LOI=1: bảng mangle không dùng được (thiếu mô-đun, LXC, iptables-nft lệch)
[ -n "${ONEBEE_FW_MANGLE_LOI:-}" ] && [ "${d##*/}" = mangle ] && exit 2
case "$1" in
  -S) if [ -n "${2:-}" ]; then [ -f "$d/$2" ] || exit 1; cat "$d/$2"; else find "$d" -maxdepth 1 -type f -exec cat {} + 2>/dev/null || true; fi ;;
  -N) [ -f "$d/$2" ] && exit 1; : > "$d/$2" ;;
  -F) : > "$d/$2" ;;
  -X) rm -f "$d/$2" ;;
  -A) c="$2"; shift 2; [ -f "$d/$c" ] || exit 1; echo "-A $c $*" >> "$d/$c" ;;
  -I) c="$2"; n="$3"; shift 3; [ -f "$d/$c" ] || : > "$d/$c"; { echo "-A $c $*"; cat "$d/$c"; } > "$d/$c.tmp"; mv "$d/$c.tmp" "$d/$c" ;;
  -D) c="$2"; shift 2; grep -vxF -- "-A $c $*" "$d/$c" > "$d/$c.tmp" || true; mv "$d/$c.tmp" "$d/$c" ;;
esac
'''
IP_GIA = r'''#!/bin/bash
case "$*" in
  "-4 route show default") echo "default via 192.168.1.1 dev enp3s0 proto dhcp" ;;
  "-4 route show dev enp3s0 scope link") echo "192.168.1.0/24 proto kernel src 192.168.1.10" ;;
esac
'''


class TuongLua(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.t = self.tmp.name
        os.makedirs(f"{t}/bin")
        for ten, nd in (("iptables", IPT_GIA), ("ip6tables", IPT_GIA), ("ip", IP_GIA)):
            open(f"{t}/bin/{ten}", "w").write(nd)
            os.chmod(f"{t}/bin/{ten}", 0o755)
        self.env = dict(os.environ, PATH=f"{t}/bin:{os.environ['PATH']}", ONEBEE_FW=f"{t}/fw", ONEBEE_TUONG_LUA_CONF=f"{t}/tuong-lua.conf")
        os.makedirs(f"{t}/fw")

    def chay(self, lenh="bat", conf=""):
        open(f"{self.t}/tuong-lua.conf", "w").write(conf)
        r = subprocess.run(["bash", SCRIPT, lenh], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def chuoi(self, ten, ipt="iptables", bang=""):
        p = f"{self.t}/fw/{ipt}/{bang + '/' if bang else ''}{ten}"
        return open(p).read().splitlines() if os.path.exists(p) else None

    def test_loc_moi_cong_mang_tru_lo_docker_br(self):
        self.chay()
        c = self.chuoi("ONEBEE-LAN-DOCKER")
        self.assertEqual(c[:3], ["-A ONEBEE-LAN-DOCKER -i lo -j RETURN", "-A ONEBEE-LAN-DOCKER -i docker+ -j RETURN", "-A ONEBEE-LAN-DOCKER -i br-+ -j RETURN"])
        self.assertIn("-A ONEBEE-LAN-DOCKER -i enp3s0 -s 192.168.1.0/24 -j RETURN", c)      # LAN chỉ qua cổng mạng chính
        self.assertEqual(c[-1], "-A ONEBEE-LAN-DOCKER -j DROP")
        self.assertFalse([x for x in c if "tailscale0" in x])                               # chưa khai thì Tailscale bị chặn
        # các chuỗi nhảy KHÔNG còn gắn với riêng cổng mạng chính
        for ten in ("DOCKER-USER", "INPUT"):
            for x in self.chuoi(ten):
                self.assertNotIn("-i ", x, x)
        self.assertEqual(sum("ONEBEE-LAN-BOX" in x for x in self.chuoi("INPUT")), 2)         # TCP + UDP
        self.assertEqual(sum("ONEBEE-LAN-DOCKER" in x for x in self.chuoi("DOCKER-USER")), 1)

    def test_mangle_loi_thi_van_chan_lan_khong_mo_toang(self):
        """bat gỡ hết quy tắc cũ rồi mới dựng: lỗi ở mangle trước khi chèn bước nhảy INPUT/DOCKER-USER = SSH/Samba/dịch vụ mở cho mọi mạng."""
        open(f"{self.t}/tuong-lua.conf", "w").write("")
        r = subprocess.run(["bash", SCRIPT, "bat"], capture_output=True, text=True, env=dict(self.env, ONEBEE_FW_MANGLE_LOI="1"))
        self.assertNotEqual(r.returncode, 0)                                                # báo lỗi (unit thất bại, quản trị thấy)
        self.assertEqual(sum("ONEBEE-LAN-BOX" in x for x in self.chuoi("INPUT")), 2)
        self.assertEqual(sum("ONEBEE-LAN-DOCKER" in x for x in self.chuoi("DOCKER-USER")), 1)

    def test_tailscale_chi_dia_chi_khai_bao_va_tach_ho_ipv4_ipv6(self):
        self.chay(conf='TAILSCALE_CHO_PHEP="100.64.1.2,100.64.9.0/24,fd7a:115c:a1e0::1"\n')
        v4 = self.chuoi("ONEBEE-LAN-BOX")
        self.assertIn("-A ONEBEE-LAN-BOX -i tailscale0 -s 100.64.1.2 -j RETURN", v4)
        self.assertIn("-A ONEBEE-LAN-BOX -i tailscale0 -s 100.64.9.0/24 -j RETURN", v4)
        self.assertFalse([x for x in v4 if "fd7a" in x])
        v6 = self.chuoi("ONEBEE-LAN-BOX", "ip6tables")
        self.assertIn("-A ONEBEE-LAN-BOX -i tailscale0 -s fd7a:115c:a1e0::1 -j RETURN", v6)
        self.assertFalse([x for x in v6 if "100.64" in x])
        # địa chỉ Tailscale chỉ có tác dụng qua tailscale0: máy ở LAN giả IP 100.64.1.2 qua cổng mạng chính không lọt
        self.assertFalse([x for x in v4 if "-i enp3s0" in x and "100.64" in x])

    def test_lan_tuy_chinh_va_chay_lai_khong_nhan_doi_quy_tac(self):
        self.chay(conf='LAN_CHO_PHEP="10.0.0.0/24,10.0.1.0/24"\n')
        truoc = {t: self.chuoi(t) for t in ("INPUT", "DOCKER-USER", "ONEBEE-LAN-BOX", "ONEBEE-LAN-DOCKER")}
        self.assertIn("-A ONEBEE-LAN-BOX -i enp3s0 -s 10.0.1.0/24 -j RETURN", truoc["ONEBEE-LAN-BOX"])
        self.assertNotIn("-A ONEBEE-LAN-BOX -i enp3s0 -s 192.168.1.0/24 -j RETURN", truoc["ONEBEE-LAN-BOX"])
        self.chay(conf='LAN_CHO_PHEP="10.0.0.0/24,10.0.1.0/24"\n')
        self.assertEqual(truoc, {t: self.chuoi(t) for t in truoc})

    def test_tat_go_sach(self):
        self.chay(conf='TAILSCALE_CHO_PHEP="100.64.1.2"\n')
        self.chay("tat")
        self.assertEqual(self.chuoi("INPUT"), [])
        self.assertEqual(self.chuoi("DOCKER-USER"), [])
        self.assertIsNone(self.chuoi("ONEBEE-LAN-BOX"))
        for ipt in ("iptables", "ip6tables"):
            self.assertEqual(self.chuoi("PREROUTING", ipt, "mangle"), [])
            self.assertIsNone(self.chuoi("ONEBEE-TAILSCALE", ipt, "mangle"))

    def test_tailscale_loc_o_mangle_khong_phu_thuoc_thu_tu_voi_tailscaled(self):
        """tailscaled (1.104, util/linuxfw) chèn -j ts-input / ts-forward vào VỊ TRÍ 1 của INPUT/FORWARD mỗi lần khởi động, và ts-input ACCEPT mọi gói
        từ tailscale0 → nếu chỉ lọc ở filter thì tailscaled khởi động sau tường lửa là máy tailnet bất kỳ vào được Box. Lọc kết nối MỚI từ tailscale0
        ở mangle/PREROUTING (chạy trước mọi chuỗi filter; tailscaled chỉ thêm ở đây quy tắc CONNMARK không chặn/không nhận gói)."""
        self.chay(conf='TAILSCALE_CHO_PHEP="100.64.1.2,fd7a:115c:a1e0::1"\n')
        self.assertEqual(self.chuoi("PREROUTING", bang="mangle"),
                         ["-A PREROUTING -i tailscale0 -m conntrack --ctstate NEW -j ONEBEE-TAILSCALE"])
        self.assertEqual(self.chuoi("ONEBEE-TAILSCALE", bang="mangle"),
                         ["-A ONEBEE-TAILSCALE -s 100.64.1.2 -j RETURN", "-A ONEBEE-TAILSCALE -j DROP"])
        self.assertEqual(self.chuoi("ONEBEE-TAILSCALE", "ip6tables", "mangle"),
                         ["-A ONEBEE-TAILSCALE -s fd7a:115c:a1e0::1 -j RETURN", "-A ONEBEE-TAILSCALE -j DROP"])
        self.chay(conf='TAILSCALE_CHO_PHEP="100.64.1.2,fd7a:115c:a1e0::1"\n')                # chạy lại không nhân đôi
        self.assertEqual(len(self.chuoi("PREROUTING", bang="mangle")), 1)
        self.chay()                                                                            # chưa khai: chặn hết kết nối mới qua Tailscale
        self.assertEqual(self.chuoi("ONEBEE-TAILSCALE", bang="mangle"), ["-A ONEBEE-TAILSCALE -j DROP"])

    def test_dich_vu_chay_sau_tailscaled(self):
        unit = open(os.path.join(os.path.dirname(SCRIPT), "onebee-tuong-lua.service"), encoding="utf-8").read()
        after = [l for l in unit.splitlines() if l.startswith("After=")]
        self.assertTrue(after and "tailscaled.service" in after[0], after)

    def test_dung_hoac_nang_cap_docker_khong_go_tuong_lua(self):
        """PartOf=docker.service + ExecStop=tat: dừng/nâng cấp Docker gỡ cả quy tắc SSH/Samba/Tailscale tới khi Docker lên lại.
        Docker dùng lại chuỗi DOCKER-USER có sẵn và giữ quy tắc trong đó qua mỗi lần khởi động → dựng TRƯỚC Docker, không gắn vòng đời."""
        unit = open(os.path.join(os.path.dirname(SCRIPT), "onebee-tuong-lua.service"), encoding="utf-8").read()
        dong = [l.strip() for l in unit.splitlines()]
        self.assertFalse([l for l in dong if l.startswith(("PartOf=", "BindsTo=", "Requisite="))], dong)
        self.assertIn("Before=docker.service", dong)
        self.assertNotIn("docker.service", [l for l in dong if l.startswith("After=")][0])
        self.assertEqual([l for l in dong if l.startswith("WantedBy=")], ["WantedBy=multi-user.target"])
        role = open(os.path.join(os.path.dirname(SCRIPT), "../tasks/main.yml"), encoding="utf-8").read()
        self.assertIn("/etc/systemd/system/docker.service.wants/onebee-tuong-lua.service", role)  # gỡ liên kết của bản cũ

    def test_ipv6_ssh_samba_ngoai_mang_noi_bo_bi_reject_ngay_khong_drop(self):
        """Mạng có IPv6 toàn cầu: Windows mở \\onebee-box bằng IPv6 trước; DROP thì treo tới khi hết thời gian chờ rồi mới lùi IPv4 → REJECT ngay."""
        self.chay()
        v6 = self.chuoi("ONEBEE-LAN-BOX", "ip6tables")
        self.assertEqual(v6[-2:], ["-A ONEBEE-LAN-BOX -p tcp -j REJECT --reject-with tcp-reset",
                                   "-A ONEBEE-LAN-BOX -j REJECT --reject-with icmp6-port-unreachable"])
        self.assertIn("-A ONEBEE-LAN-BOX -i enp3s0 -s fe80::/10 -j RETURN", v6)                # mạng nội bộ IPv6 vẫn vào được
        self.assertEqual(self.chuoi("ONEBEE-LAN-BOX")[-1], "-A ONEBEE-LAN-BOX -j DROP")          # IPv4 giữ DROP
        self.assertEqual(self.chuoi("ONEBEE-LAN-DOCKER", "ip6tables")[-1], "-A ONEBEE-LAN-DOCKER -j DROP")


if __name__ == "__main__":
    unittest.main()
