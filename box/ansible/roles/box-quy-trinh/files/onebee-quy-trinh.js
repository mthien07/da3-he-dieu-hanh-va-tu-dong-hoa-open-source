// Quản lý bởi OneBee OS (box/ansible/roles/box-quy-trinh) — không sửa tay trên Box.
// Mã các luồng của động cơ quy trình (Node-RED): mỗi nút function trong flows.json chỉ gọi xuLy('<điểm nhận>', msg).
// Chỉ dùng thư viện chuẩn Node.js (không gói npm nào): gửi thư SMTP, kiểm khóa, ghi tình trạng máy trạm, gọi API dữ liệu qua Caddy.
// Settings.js nạp tệp này vào functionGlobalContext.onebee; cấu hình (kể cả khóa) đọc MỘT lần từ <ONEBEE_CAU_HINH>/cau-hinh.json.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');
const tls = require('tls');

const THU_MUC = process.env.ONEBEE_CAU_HINH || '/cau-hinh';
const CH = JSON.parse(fs.readFileSync(path.join(THU_MUC, 'cau-hinh.json'), 'utf8'));
const TEN_MAY = /^[a-z0-9][a-z0-9-]{0,31}$/;
const CHO_SMTP_MS = 20000;   // < 30 giây: onebee-box gọi với curl -m 30

class LoiHttp extends Error {
  constructor(ma, thongBao) { super(thongBao); this.ma = ma; }
}

// ---------- Tiện ích ----------
const tieuDe = (msg, ten) => {
  const v = msg && msg.req && msg.req.headers ? msg.req.headers[ten] : undefined;
  return typeof v === 'string' ? v : '';
};
const than = msg => {
  const b = msg ? msg.payload : undefined;
  if (!b || typeof b !== 'object' || Array.isArray(b)) throw new LoiHttp(400, 'Thân yêu cầu phải là một đối tượng JSON');
  return b;
};
// Chữ một dòng: mọi ký tự điều khiển (xuống dòng, tab…) thành dấu cách — không chèn được tiêu đề thư khác
const motDong = (v, toiDa = 200) => String(v === undefined || v === null ? '' : v).replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, toiDa);
// Chữ nhiều dòng: giữ xuống dòng, bỏ ký tự điều khiển khác
const nhieuDong = (v, toiDa = 8000) => String(v === undefined || v === null ? '' : v)
  .replace(/\r\n?/g, '\n').replace(/[\u0000-\u0009\u000b-\u001f\u007f]/g, ' ').slice(0, toiDa);
// So khóa: Node-RED chỉ giữ SHA-256 của khóa; so bằng timingSafeEqual
function dungKhoa(giaTri, bamMongDoi) {
  if (!giaTri || !/^[0-9a-f]{64}$/.test(bamMongDoi || '')) return false;
  const a = crypto.createHash('sha256').update(giaTri, 'utf8').digest();
  return crypto.timingSafeEqual(a, Buffer.from(bamMongDoi, 'hex'));
}
function kiemKhoaBox(msg) {
  if (!dungKhoa(tieuDe(msg, 'x-onebee-key'), CH.khoa_box_sha256)) throw new LoiHttp(403, 'Sai khóa X-OneBee-Key');
}
// Số tiền kiểu Việt Nam: 17.500.000 (không phụ thuộc dữ liệu ngôn ngữ của Node)
const tien = n => {
  const x = Math.round(Number(n) || 0);
  return (x < 0 ? '-' : '') + String(Math.abs(x)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
};
const ngayVn = s => (/^\d{4}-\d{2}-\d{2}$/.test(s) ? s.split('-').reverse().join('/') : s);
// Ngày hôm nay (YYYY-MM-DD) theo múi giờ của Box — không theo giờ UTC của container
const homNay = () => new Intl.DateTimeFormat('en-CA', { timeZone: CH.mui_gio, year: 'numeric', month: '2-digit', day: '2-digit' })
  .format(new Date());
// Ghi tệp: ghi tệp tạm rồi đổi tên (người đọc không bao giờ thấy tệp ghi dở)
function ghiTep(dich, noiDung) {
  const tam = `${dich}.${process.pid}.${crypto.randomBytes(4).toString('hex')}.tam`;
  fs.writeFileSync(tam, noiDung, { mode: 0o600 });
  fs.renameSync(tam, dich);
}

// ---------- Gửi thư SMTP (RFC 5321/5322, chỉ thư viện chuẩn) ----------
function diaChi(s) {
  const t = String(s || '').trim();
  const m = /<([^<>\s@]+@[^<>\s@]+)>\s*$/.exec(t) || /^([^<>\s@]+@[^<>\s@]+)$/.exec(t);
  return m ? m[1] : '';
}
// Mã hóa chữ UTF-8 trong tiêu đề thư (RFC 2047), mỗi đoạn ≤ 45 byte (không cắt giữa một ký tự)
function maHoaTieuDe(chu) {
  const doan = [];
  let cur = '';
  for (const k of chu) {
    if (Buffer.byteLength(cur + k, 'utf8') > 45) { doan.push(cur); cur = ''; }
    cur += k;
  }
  if (cur) doan.push(cur);
  if (!doan.length) doan.push('');
  return doan.map(d => `=?UTF-8?B?${Buffer.from(d, 'utf8').toString('base64')}?=`).join('\r\n ');
}
function soanThu(tu, tenTu, nhan, tieuDeThu, noiDung) {
  const b64 = Buffer.from(noiDung.replace(/\r?\n/g, '\r\n'), 'utf8').toString('base64').replace(/.{1,76}/g, '$&\r\n');
  return [
    `From: ${tenTu ? maHoaTieuDe(tenTu) + ' ' : ''}<${tu}>`,
    `To: ${nhan.map(n => `<${n}>`).join(', ')}`,
    `Subject: ${maHoaTieuDe(tieuDeThu)}`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: <${crypto.randomBytes(12).toString('hex')}@onebee-box>`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=utf-8',
    'Content-Transfer-Encoding: base64',
    '',
    b64,
  ].join('\r\n');
}

// Đọc từng phản hồi SMTP (một hoặc nhiều dòng "250-…", dòng cuối "250 …")
class DocSmtp {
  constructor(sock) {
    this.sock = sock; this.dem = ''; this.dong = []; this.phanHoi = []; this.cho = []; this.loi = null;
    sock.on('data', d => this.nhan(d));
    sock.on('error', e => this.hong(e));
    sock.on('close', () => this.hong(new Error('Máy chủ thư đóng kết nối')));
  }
  nhan(d) {
    this.dem += d.toString('utf8');
    let i;
    while ((i = this.dem.indexOf('\n')) >= 0) {
      const dong = this.dem.slice(0, i).replace(/\r$/, '');
      this.dem = this.dem.slice(i + 1);
      this.dong.push(dong);
      if (/^\d{3}(?: |$)/.test(dong)) {
        const ph = { ma: Number(dong.slice(0, 3)), dong: this.dong };
        this.dong = [];
        const c = this.cho.shift();
        if (c) c.ok(ph); else this.phanHoi.push(ph);
      }
    }
  }
  hong(e) {
    if (!this.loi) this.loi = e;
    while (this.cho.length) this.cho.shift().loi(this.loi);
  }
  doc(maMongDoi) {
    const mong = [].concat(maMongDoi);
    return new Promise((ok, loi) => {
      const xong = ph => (mong.includes(ph.ma) ? ok(ph) : loi(new Error(`Máy chủ thư trả ${ph.dong.join(' / ')}`)));
      if (this.phanHoi.length) return xong(this.phanHoi.shift());
      if (this.loi) return loi(this.loi);
      this.cho.push({ ok: xong, loi });
    });
  }
  lenh(dong, maMongDoi) {
    this.sock.write(dong + '\r\n');
    return this.doc(maMongDoi);
  }
}
function ketNoi(t) {
  return new Promise((ok, loi) => {
    const s = t.ssl
      ? tls.connect({ host: t.host, port: t.port, servername: t.host }, () => ok(s))
      : net.connect({ host: t.host, port: t.port }, () => ok(s));
    s.setTimeout(CHO_SMTP_MS, () => s.destroy(new Error(`Máy chủ thư ${t.host}:${t.port} không trả lời`)));
    s.once('error', loi);
  });
}
function nangTls(s, host) {
  s.removeAllListeners('data'); s.removeAllListeners('error'); s.removeAllListeners('close');
  return new Promise((ok, loi) => {
    const t = tls.connect({ socket: s, servername: host }, () => ok(t));
    t.setTimeout(CHO_SMTP_MS, () => t.destroy(new Error('Máy chủ thư không trả lời sau STARTTLS')));
    t.once('error', loi);
  });
}
async function guiThu(tieuDeThu, noiDung) {
  const t = CH.thu || {};
  if (!t.host) throw new LoiHttp(503, 'Box chưa cấu hình email (onebee_box_email.smtp_host)');
  const tu = diaChi(t.gui_tu);
  const tenTu = motDong(String(t.gui_tu || '').replace(/<[^>]*>\s*$/, '').replace(/"/g, ''), 100);
  const nhan = String(t.nhan || '').split(',').map(diaChi).filter(Boolean);
  if (!tu || !nhan.length) throw new LoiHttp(503, 'Thiếu địa chỉ gửi hoặc nhận thư (onebee_box_email.gui_tu, nhan)');
  let s = await ketNoi(t);
  try {
    let r = new DocSmtp(s);
    await r.doc(220);
    await r.lenh('EHLO onebee-box', 250);
    if (!t.ssl && t.starttls) {
      await r.lenh('STARTTLS', 220);
      s = await nangTls(s, t.host);
      r = new DocSmtp(s);
      await r.lenh('EHLO onebee-box', 250);
    }
    if (t.user) await r.lenh('AUTH PLAIN ' + Buffer.from(`\0${t.user}\0${t.password || ''}`, 'utf8').toString('base64'), 235);
    await r.lenh(`MAIL FROM:<${tu}>`, 250);
    for (const n of nhan) await r.lenh(`RCPT TO:<${n}>`, [250, 251]);
    await r.lenh('DATA', 354);
    await r.lenh(soanThu(tu, tenTu, nhan, motDong(tieuDeThu, 300), nhieuDong(noiDung, 60000)) + '\r\n.', 250);
    await r.lenh('QUIT', 221).catch(() => {});
  } finally {
    s.destroy();
  }
}

// ---------- 01: báo cáo sao lưu ----------
// Box gửi: trang_thai ("DAT"/"LOI"/"THU"), noi_dung, may_tram: [{ten, canh_bao: [...], tom_tat}] (cảnh báo do Box tính sẵn)
function soanBaoCaoSaoLuu(b) {
  if (b.trang_thai === 'THU') return { tieu_de: '[OneBee Box] Email thử — cấu hình email đã dùng được', noi_dung: String(b.noi_dung || '') };
  const ok = b.trang_thai === 'DAT';
  const may = Array.isArray(b.may_tram) ? b.may_tram : [];
  const cb = m => (Array.isArray(m.canh_bao) ? m.canh_bao.map(x => motDong(x)) : []);
  const canXuLy = may.filter(m => cb(m).length);
  const dong = may.map(m => `- ${motDong(m.ten, 40)}: ${cb(m).length ? 'CẦN XỬ LÝ — ' + cb(m).join('; ') : 'ổn'}${m.tom_tat ? ' (' + motDong(m.tom_tat) + ')' : ''}`);
  let tieu = `[OneBee Box] Sao lưu ${ok ? 'ĐẠT' : 'LỖI'}`;
  if (canXuLy.length) tieu += ` — ${canXuLy.length} máy trạm cần xử lý`;
  const noi = [
    ok ? 'Sao lưu OneBee Box ra ổ ngoài: ĐẠT.' : 'Sao lưu OneBee Box: LỖI — cần kiểm tra ngay (sudo onebee-box trang-thai).',
    '', String(b.noi_dung || ''), '',
    may.length ? 'Tình trạng máy trạm:' : 'Chưa cấp máy trạm nào (sudo onebee-box them-may <tên-máy>).', ...dong,
    canXuLy.length ? '\nXem chi tiết: sudo onebee-box may-tram · cập nhật tất cả: sudo onebee-box cap-nhat-may --tat-ca' : '',
  ].join('\n');
  return { tieu_de: tieu, noi_dung: noi };
}

// ---------- 02: nhắc hạn nộp báo cáo, thuế ----------
function soanNhacHan(ngay) {
  const today = new Date(ngay + 'T00:00:00Z');
  const cuoiThang = (y, m) => new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  const denHan = (item, d) => {
    const y = d.getUTCFullYear(); const m = d.getUTCMonth();
    const can = item.ngay === 'cuoi_thang' ? cuoiThang(y, m) : Number(item.ngay);
    if (d.getUTCDate() !== can) return false;
    if (item.loai === 'thang') return true;
    if (item.loai === 'quy') return [0, 3, 6, 9].includes(m);   // tháng đầu mỗi quý
    if (item.loai === 'nam') return m === Number(item.thang) - 1;
    return false;
  };
  const fmt = d => d.toISOString().slice(0, 10).split('-').reverse().join('/');
  const dong = [];
  for (const n of CH.nhac_truoc || []) {
    const d = new Date(today.getTime() + n * 86400000);
    for (const item of CH.lich_han || []) {
      if (denHan(item, d)) dong.push({ n, chu: `- ${item.ten}: hạn ${fmt(d)} (${n === 0 ? 'HÔM NAY' : 'còn ' + n + ' ngày'})` });
    }
  }
  if (!dong.length) return null;
  dong.sort((a, b) => a.n - b.n);
  return {
    tieu_de: `[OneBee] Nhắc hạn nộp: ${dong.length} việc — gần nhất ${dong[0].n === 0 ? 'HÔM NAY' : 'còn ' + dong[0].n + ' ngày'}`,
    noi_dung: ['Các hạn nộp sắp tới:', '', ...dong.map(l => l.chu), '',
      'Hạn trùng ngày nghỉ thì được lùi sang ngày làm việc kế tiếp. Lịch này là bản mẫu — kế toán kiểm lại theo quy định hiện hành.'].join('\n'),
  };
}

// ---------- 05: tổng hợp đơn hàng trong ngày (Box đọc CSDL rồi gửi danh sách) ----------
const TRANG_THAI = { CHO_DUYET: 'chờ duyệt', DA_DUYET: 'đã duyệt', TU_CHOI: 'từ chối' };
function soanTongHopDonHang(b) {
  const ngay = /^\d{4}-\d{2}-\d{2}$/.test(b.ngay || '') ? b.ngay : homNay();
  const don = (Array.isArray(b.don) ? b.don : []).filter(d => d && typeof d === 'object');
  const tong = don.reduce((s, d) => s + (Number(d.thanh_tien) || 0), 0);
  if (!don.length) {
    return { tieu_de: `[OneBee] Đơn hàng hôm nay: 0 đơn — 0 đồng`, noi_dung: `Hôm nay ${ngayVn(ngay)} chưa có đơn hàng nào được nhập.` };
  }
  const theoHang = {};
  const theoTrangThai = {};
  for (const d of don) {
    const k = motDong(d.mat_hang, 80);
    theoHang[k] = theoHang[k] || { kg: 0, tien: 0 };
    theoHang[k].kg += Number(d.so_luong_kg) || 0;
    theoHang[k].tien += Number(d.thanh_tien) || 0;
    const tt = TRANG_THAI[d.trang_thai_duyet] || 'khác';
    theoTrangThai[tt] = (theoTrangThai[tt] || 0) + 1;
  }
  return {
    tieu_de: `[OneBee] Đơn hàng hôm nay: ${don.length} đơn — ${tien(tong)} đồng`,
    noi_dung: [
      `Hôm nay ${ngayVn(ngay)} có ${don.length} đơn hàng, tổng ${tien(tong)} đồng.`,
      `Trạng thái: ${Object.entries(theoTrangThai).map(([k, v]) => `${v} ${k}`).join(', ')}.`, '',
      'Theo mặt hàng:', ...Object.entries(theoHang).map(([k, v]) => `- ${k}: ${tien(v.kg)} kg — ${tien(v.tien)} đồng`), '',
      'Chi tiết:', ...don.map(d => `- ${motDong(d.khach_hang, 80)}: ${motDong(d.mat_hang, 80)} ${tien(d.so_luong_kg)} kg × ${tien(d.don_gia)}`
        + ` = ${tien(d.thanh_tien)} đồng, giao ${ngayVn(motDong(d.ngay_giao, 20))}${d.ghi_chu ? ' (' + motDong(d.ghi_chu) + ')' : ''}`
        + ` — ${TRANG_THAI[d.trang_thai_duyet] || 'sổ cũ'}`),
    ].join('\n'),
  };
}

// ---------- 06: nhận tình trạng máy trạm ----------
// Node-RED KHÔNG giữ khóa ký: chỉ (1) đòi khóa lọc chung khi Box còn dùng, (2) chỉ nhận máy ĐÃ CẤP (tệp đánh dấu trong may-da-cap/,
// gắn chỉ đọc), (3) lưu nguyên bao bì có chữ ký. Box tự kiểm chữ ký bằng mật khẩu kho sao lưu của máy (onebee-may-tram.py).
function tinhTrang(msg) {
  if (CH.khoa_chung && !dungKhoa(tieuDe(msg, 'x-onebee-key'), CH.khoa_tram_sha256)) throw new LoiHttp(403, 'Sai khóa gửi tình trạng');
  const b = than(msg);
  const ten = String(b.ten || '');
  if (!TEN_MAY.test(ten)) throw new LoiHttp(400, 'Tên máy trạm không hợp lệ');
  let daCap = false;
  try { daCap = fs.statSync(path.join(CH.may_da_cap, ten)).isFile(); } catch (e) { daCap = false; }
  if (!daCap) throw new LoiHttp(403, 'Máy trạm chưa được cấp');
  const nhanLuc = Math.floor(Date.now() / 1000);   // giờ nhận theo đồng hồ Box, không tin đồng hồ máy trạm
  let tt;
  if (typeof b.du_lieu === 'string') {
    if (b.du_lieu.length > 4096 || !/^[0-9a-f]{64}$/.test(String(b.ky || ''))) throw new LoiHttp(400, 'Báo cáo không đúng dạng');
    tt = { ten, dinh_dang: 2, du_lieu: b.du_lieu, ky: b.ky, nhan_luc: nhanLuc };
  } else {
    // Dạng cũ (máy chạy mã desktop cũ, chưa ký): chỉ giữ trường đã biết, kiểm kiểu + giới hạn. Box gắn nhãn "chưa ký"
    const so = (v, max) => { const n = Number(v); return v !== null && v !== '' && Number.isFinite(n) && n >= 0 && n <= max ? Math.round(n * 10) / 10 : null; };
    const chu = (v, n) => (typeof v === 'string' ? v.replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, n) : null);
    const ip = typeof b.ip === 'string' && /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(b.ip) ? b.ip : null;
    tt = {
      ten, ip, hostname: chu(b.hostname, 64), phien_ban: chu(b.phien_ban, 32), he_dieu_hanh: chu(b.he_dieu_hanh, 64),
      cap_nhat_cho: so(b.cap_nhat_cho, 100000), bao_mat_cho: so(b.bao_mat_cho, 100000),
      can_khoi_dong_lai: b.can_khoi_dong_lai === true,
      o_trong_phan_tram: so(b.o_trong_phan_tram, 100), o_trong_gb: so(b.o_trong_gb, 1e6),
      khoi_dong_gio: so(b.khoi_dong_gio, 1e6), sao_luu_cuoi: so(b.sao_luu_cuoi, 1e11), sudo_so: so(b.sudo_so, 1000),
      nhan_luc: nhanLuc,
    };
  }
  ghiTep(path.join(CH.tinh_trang, `${ten}.json`), JSON.stringify(tt));
  return { ok: true };
}

// ---------- 10: cảnh báo sự cố ----------
function soanCanhBao(b) {
  const muc = motDong(b.muc_do, 20).toUpperCase();
  const ten = ['WARN', 'CANH_BAO'].includes(muc) ? 'CẢNH BÁO' : ['CRIT', 'KHAN_CAP', 'LOI'].includes(muc) ? 'BÁO ĐỘNG KHẨN' : 'THÔNG BÁO';
  const donVi = motDong(b.don_vi, 100) || 'OneBee Box';
  const tieu = motDong(b.tieu_de, 200) || 'Thông báo hệ thống';
  return {
    tieu_de: `[${ten}] ${donVi}: ${tieu}`,
    noi_dung: [`[${ten} — ${donVi}]`, tieu, `Thời gian: ${motDong(b.thoi_gian, 40)}`, '', nhieuDong(b.noi_dung, 4000), '',
      'Được gửi tự động từ OneBee Box.'].join('\n'),
  };
}

// ---------- Phê duyệt đơn hàng ----------
// Người duyệt = Remote-User do forward_auth gắn (Caddy xóa bản máy khách tự gửi). Ghi trạng thái bằng cách gọi lại Caddy /api/ kèm cookie
// phiên của chính người duyệt → cầu nối ký JWT của người đó → RLS, trigger, ràng buộc khong_tu_duyet trong CSDL là rào chắn cuối.
function cookiePhien(msg) {
  return tieuDe(msg, 'cookie').split(';').map(x => x.trim()).filter(x => /^authelia_session[A-Za-z0-9_-]*=/.test(x)).join('; ');
}
function goiApi(phuongThuc, duongDan, cookie, thanGui) {
  const u = new URL(duongDan, CH.api_goc);
  const laHttps = u.protocol === 'https:';
  const du = thanGui === undefined ? null : Buffer.from(JSON.stringify(thanGui), 'utf8');
  const headers = { Accept: 'application/json', Cookie: cookie };
  if (du) Object.assign(headers, { 'Content-Type': 'application/json', 'Content-Length': du.length, Prefer: 'return=representation' });
  const opts = { method: phuongThuc, hostname: u.hostname, port: u.port || (laHttps ? 443 : 80), path: u.pathname + u.search, headers, timeout: 15000 };
  if (laHttps) {
    opts.servername = u.hostname;
    if (CH.ca && fs.existsSync(CH.ca)) opts.ca = fs.readFileSync(CH.ca);
  }
  return new Promise((ok, loi) => {
    const req = (laHttps ? https : http).request(opts, res => {
      const phan = [];
      res.on('data', d => phan.push(d));
      res.on('end', () => {
        const chu = Buffer.concat(phan).toString('utf8');
        let du2 = chu;
        try { du2 = JSON.parse(chu); } catch (e) { du2 = chu; }
        ok({ ma: res.statusCode, than: du2 });
      });
    });
    req.on('timeout', () => req.destroy(new Error('API dữ liệu không trả lời')));
    req.on('error', loi);
    if (du) req.write(du);
    req.end();
  });
}
async function pheDuyet(msg) {
  const nguoi = tieuDe(msg, 'remote-user');
  const cookie = cookiePhien(msg);
  if (!nguoi || !cookie) throw new LoiHttp(401, 'Cần đăng nhập');
  const b = than(msg);
  if ((b.loai || 'don_hang') !== 'don_hang') throw new LoiHttp(400, 'Chỉ duyệt được đơn hàng (loai: don_hang)');
  const id = Number(b.id);
  if (!Number.isSafeInteger(id) || id <= 0) throw new LoiHttp(400, 'Mã đơn (id) phải là số nguyên dương');
  const quyetDinh = b.trang_thai_duyet;
  if (!['DA_DUYET', 'TU_CHOI'].includes(quyetDinh)) throw new LoiHttp(400, 'trang_thai_duyet phải là DA_DUYET hoặc TU_CHOI');
  const lyDo = motDong(b.ly_do_duyet, 500);
  if (quyetDinh === 'TU_CHOI' && !lyDo) throw new LoiHttp(400, 'Từ chối phải ghi lý do (ly_do_duyet)');

  const doc = await goiApi('GET', `/api/don_hang?id=eq.${id}&select=id,nguoi_tao,trang_thai_duyet`, cookie);
  if (doc.ma === 401 || doc.ma === 403) throw new LoiHttp(doc.ma, 'Phiên đăng nhập không đủ quyền đọc đơn hàng');
  if (doc.ma !== 200 || !Array.isArray(doc.than)) throw new LoiHttp(502, `API dữ liệu trả mã ${doc.ma}`);
  const don = doc.than[0];
  if (!don) throw new LoiHttp(404, `Không có đơn ${id}`);
  if (don.nguoi_tao === nguoi) throw new LoiHttp(403, 'Không được tự duyệt đơn của chính mình');
  if (don.trang_thai_duyet !== 'CHO_DUYET') throw new LoiHttp(409, `Đơn ${id} đã được xử lý (${don.trang_thai_duyet || 'sổ cũ'})`);

  const ghi = await goiApi('PATCH', `/api/don_hang?id=eq.${id}&trang_thai_duyet=eq.CHO_DUYET`, cookie,
    { trang_thai_duyet: quyetDinh, ly_do_duyet: lyDo || null });
  if (ghi.ma === 400 && JSON.stringify(ghi.than).includes('khong_tu_duyet')) throw new LoiHttp(403, 'Không được tự duyệt đơn của chính mình');
  if (ghi.ma === 401 || ghi.ma === 403) throw new LoiHttp(ghi.ma, 'Phiên đăng nhập không có quyền duyệt đơn');
  if (ghi.ma !== 200 || !Array.isArray(ghi.than)) throw new LoiHttp(502, `API dữ liệu trả mã ${ghi.ma}`);
  if (!ghi.than.length) throw new LoiHttp(409, `Đơn ${id} vừa được người khác xử lý`);
  const r = ghi.than[0];
  if ((CH.thu || {}).host) {   // báo kết quả qua thư: không chờ, lỗi thư không làm hỏng việc duyệt
    guiThu(`[OneBee] Đơn hàng ${id} ${quyetDinh === 'DA_DUYET' ? 'đã được duyệt' : 'bị từ chối'}`,
      `Đơn ${id} (người tạo: ${motDong(don.nguoi_tao, 64)}) — ${TRANG_THAI[quyetDinh]} bởi ${motDong(r.nguoi_duyet, 64)}`
      + `${lyDo ? '. Lý do: ' + lyDo : ''}.`).catch(e => console.warn(`[onebee] Không gửi được thư báo duyệt đơn ${id}: ${e.message}`));
  }
  return { id: r.id, trang_thai_duyet: r.trang_thai_duyet, nguoi_duyet: r.nguoi_duyet, ly_do_duyet: r.ly_do_duyet, thoi_gian_duyet: r.thoi_gian_duyet };
}

// ---------- Điểm nhận ----------
const DIEM_NHAN = {
  'suc-khoe': async () => ({ ok: true }),
  'bao-cao-sao-luu': async msg => {
    kiemKhoaBox(msg);
    const t = soanBaoCaoSaoLuu(than(msg));
    await guiThu(t.tieu_de, t.noi_dung);
    return { ok: true, tieu_de: t.tieu_de };
  },
  'nhac-han': async msg => {
    kiemKhoaBox(msg);
    const b = than(msg);
    if (b.hom_nay !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(String(b.hom_nay))) throw new LoiHttp(400, 'hom_nay theo dạng YYYY-MM-DD');
    const t = soanNhacHan(b.hom_nay || homNay());
    if (t) await guiThu(t.tieu_de, t.noi_dung);
    return { ok: true, tieu_de: t ? t.tieu_de : null };
  },
  'nhac-han-theo-lich': async () => {
    const t = soanNhacHan(homNay());
    if (t) await guiThu(t.tieu_de, t.noi_dung);
    return { ok: true, tieu_de: t ? t.tieu_de : null };
  },
  'tong-hop-don-hang': async msg => {
    kiemKhoaBox(msg);
    const t = soanTongHopDonHang(than(msg));
    await guiThu(t.tieu_de, t.noi_dung);
    return { ok: true, tieu_de: t.tieu_de };
  },
  'tinh-trang': async msg => tinhTrang(msg),
  'canh-bao': async msg => {
    kiemKhoaBox(msg);
    const t = soanCanhBao(than(msg));
    await guiThu(t.tieu_de, t.noi_dung);
    return { ok: true, tieu_de: t.tieu_de };
  },
  'phe-duyet': pheDuyet,
};

async function xuLy(ten, msg) {
  const m = msg || {};
  let ma = 200;
  let kq;
  try {
    const f = DIEM_NHAN[ten];
    if (!f) throw new LoiHttp(404, 'Không có điểm nhận này');
    kq = await f(m);
  } catch (e) {
    ma = e instanceof LoiHttp ? e.ma : 502;
    kq = { ok: false, loi: e instanceof LoiHttp ? e.message : `Lỗi xử lý: ${e.message}` };
    if (!(e instanceof LoiHttp) || ma >= 500) console.warn(`[onebee] ${ten}: ${e.message}`);
  }
  m.statusCode = ma;
  m.payload = kq;
  m.headers = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
  return m;
}

module.exports = { xuLy, soanBaoCaoSaoLuu, soanNhacHan, soanTongHopDonHang, soanCanhBao, soanThu, maHoaTieuDe, dungKhoa, tien };
