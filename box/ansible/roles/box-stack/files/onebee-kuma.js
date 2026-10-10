// Cấu hình Uptime Kuma của OneBee Box: tạo tài khoản quản trị (lần đầu), email báo khi dịch vụ ngừng, danh sách theo dõi.
// Chạy bên trong container Uptime Kuma: docker exec -i -w /app -e ... onebee-uptime-kuma node - < onebee-kuma.js
// Biến: KUMA_USER, KUMA_PASS, KUMA_MONITORS (JSON), KUMA_SMTP (JSON, rỗng = không gửi email),
//       KUMA_PASS_MOI (đặt = đổi mật khẩu quản trị sang giá trị này sau khi đăng nhập; dùng cho onebee-box xoay-khoa --box),
//       KUMA_TRUST_PROXY ("1" = tin tiêu đề X-Forwarded-* của Caddy đứng trước; "0" = không; trống = không đụng)
// Mã thoát: 0 xong · 1 lỗi (thử lại được) · 3 sai mật khẩu quản trị
const { io } = require("socket.io-client");
const user = process.env.KUMA_USER, pass = process.env.KUMA_PASS;
const monitors = JSON.parse(process.env.KUMA_MONITORS || "[]");
const smtp = process.env.KUMA_SMTP ? JSON.parse(process.env.KUMA_SMTP) : null;
const socket = io("http://127.0.0.1:3001", { transports: ["websocket"], reconnection: false, timeout: 20000 });
const call = (ev, ...args) => new Promise((ok, fail) => {
  const t = setTimeout(() => fail(new Error(`hết giờ chờ ${ev}`)), 30000);
  socket.emit(ev, ...args, (res) => { clearTimeout(t); ok(res); });
});
const once = (ev) => new Promise((ok, fail) => {
  const t = setTimeout(() => fail(new Error(`hết giờ chờ ${ev}`)), 30000);
  socket.once(ev, (d) => { clearTimeout(t); ok(d); });
});
const out = (code, msg) => { console.log(msg); socket.close(); process.exit(code); };
let doi = 0;
socket.on("connect_error", (e) => out(1, `LỖI: không kết nối được Uptime Kuma: ${e.message}`));
socket.on("connect", async () => {
  try {
    if (await call("needSetup")) {
      const r = await call("setup", user, pass);
      if (!r.ok) out(1, `LỖI: không tạo được tài khoản quản trị: ${r.msg}`);
      console.log("Uptime Kuma: đã tạo tài khoản quản trị"); doi++;
    }
    const danhSach = once("monitorList"), thongBao = once("notificationList");
    const login = await call("login", { username: user, password: pass, token: "" });
    if (!login.ok) out(3, "LỖI: sai mật khẩu quản trị Uptime Kuma (đã đổi trên web? ghi mật khẩu mới vào /etc/onebee-box/secrets/uptime-kuma-password)");
    const coSan = Object.values(await danhSach).map((m) => m.name);
    if (process.env.KUMA_TRUST_PROXY) {
      const muon = process.env.KUMA_TRUST_PROXY === "1";
      const g = await call("getSettings");   // gửi lại NGUYÊN cài đặt hiện có như giao diện web (setSettings ghi đè entryPage, múi giờ…)
      if (!g.ok) out(1, `LỖI: không đọc được cài đặt Uptime Kuma: ${g.msg}`);
      if (Boolean(g.data.trustProxy) !== muon) {
        const r = await call("setSettings", { ...g.data, trustProxy: muon }, pass);
        if (!r.ok) out(1, `LỖI: không lưu được cài đặt Trust Proxy: ${r.msg}`);
        doi++;
      }
    }
    const tb = await thongBao;
    let tbId = null;
    if (smtp) {
      const cu = tb.find((n) => n.name === "OneBee email");
      const cfg = { name: "OneBee email", type: "smtp", isDefault: true, applyExisting: true, ...smtp };
      const r = await call("addNotification", cfg, cu ? cu.id : null);
      if (!r.ok) out(1, `LỖI: không lưu được email báo: ${r.msg}`);
      tbId = r.id;
    }
    for (const m of monitors) {
      if (coSan.includes(m.name)) continue;
      const r = await call("add", {
        type: "http", method: "GET", interval: 60, retryInterval: 60, resendInterval: 0, maxretries: 1, timeout: 48,
        maxredirects: 10, ignoreTls: false, upsideDown: false, accepted_statuscodes: ["200-299"], conditions: [],
        kafkaProducerBrokers: [], kafkaProducerSaslOptions: {}, rabbitmqNodes: [],
        notificationIDList: tbId ? { [tbId]: true } : {}, ...m,
      });
      if (!r.ok) out(1, `LỖI: không thêm được theo dõi ${m.name}: ${r.msg}`);
      doi++;
    }
    if (process.env.KUMA_PASS_MOI) {
      const r = await call("changePassword", { currentPassword: pass, newPassword: process.env.KUMA_PASS_MOI });
      if (!r.ok) out(1, `LỖI: không đổi được mật khẩu quản trị Uptime Kuma: ${r.msg}`);
      doi++;
    }
    out(0, doi ? `Uptime Kuma: đã cập nhật (${doi} thay đổi)` : "Uptime Kuma: không đổi");
  } catch (e) { out(1, `LỖI: ${e.message}`); }
});
