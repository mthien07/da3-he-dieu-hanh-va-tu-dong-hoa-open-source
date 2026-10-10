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
# iptables giả: nhớ trạng thái trong thư mục $ONEBEE_FW (một file mỗi chuỗi, mỗi dòng một quy tắc dạng "-A chuỗi …")
d="$ONEBEE_FW/$(basename "$0")"; mkdir -p "$d"
echo "$0 $*" >> "$ONEBEE_FW/lenh.log"
case "$1" in
  -S) if [ -n "${2:-}" ]; then [ -f "$d/$2" ] || exit 1; cat "$d/$2"; else cat "$d"/* 2>/dev/null || true; fi ;;
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

    def chuoi(self, ten, ipt="iptables"):
        p = f"{self.t}/fw/{ipt}/{ten}"
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
        self.chay()
        self.chay("tat")
        self.assertEqual(self.chuoi("INPUT"), [])
        self.assertEqual(self.chuoi("DOCKER-USER"), [])
        self.assertIsNone(self.chuoi("ONEBEE-LAN-BOX"))


if __name__ == "__main__":
    unittest.main()
