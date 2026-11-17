/* SPDX-License-Identifier: MIT */
/* Quản lý bởi OneBee OS. Sổ điều hành H-P-D-I: không thư viện ngoài, không tải gì từ Internet,
   dữ liệu người dùng chỉ vào trang bằng textContent, quyền kiểm ở CSDL (RLS). */
"use strict";

var MAU_TOM_TAT = "Tóm tắt số liệu tuần này bằng tiếng Việt, ngắn gọn, chỉ dùng đúng các con số trong JSON; không bịa thêm số liệu ngoài JSON. Trả lời bằng tiếng Việt.\n";
var DUOI_TEP = [".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx", ".xlsx", ".odt", ".ods"];
var TOI_DA_TEP = 10 * 1024 * 1024;
var TEN_KHU = ["khu-h", "khu-p", "khu-d", "khu-i", "khu-k", "khu-t"];
var VAI_TRO_KHO = ["thu_kho", "quan_ly"];
var VAI_TRO_KE_TOAN = ["ke_toan", "quan_ly"];
var HOSO = { ten: "", vai_tro: "" };
var SO_LIEU = {};
var MAT_HANG = [];

function chu(v) {
  return typeof v === "string" ? v.trim() : "";
}

function soKhongAm(v) {
  return typeof v === "number" && isFinite(v) && v >= 0;
}

/* Tổng số dòng từ Content-Range của PostgREST; không rõ tổng thì null. */
function docSoDong(giaTri) {
  if (typeof giaTri !== "string") return null;
  var m = /^\*\/\s*(\d+)$/.exec(giaTri.trim());
  if (!m) m = /^\d+-\d+\/\s*(\d+)$/.exec(giaTri.trim());
  return m ? Number(m[1]) : null;
}

/* Kiểm dữ liệu đơn hàng ở trình duyệt; ràng buộc thật vẫn ở CSDL. */
function dungDonHang(d) {
  var khach = chu(d.khach_hang), hang = chu(d.mat_hang);
  if (!khach) return { loi: "Vui lòng nhập khách hàng." };
  if (khach.length > 200) return { loi: "Khách hàng dài quá 200 ký tự." };
  if (!hang) return { loi: "Vui lòng chọn mặt hàng trong danh mục kho." };
  if (hang.length > 200) return { loi: "Mặt hàng dài quá 200 ký tự." };
  var soLuong = Number(d.so_luong_kg);
  if (!isFinite(soLuong) || soLuong <= 0) return { loi: "Số lượng phải là số lớn hơn 0." };
  if (d.don_gia === "" || d.don_gia === null || d.don_gia === undefined) return { loi: "Vui lòng nhập đơn giá." };
  var donGia = Number(d.don_gia);
  if (!isFinite(donGia) || donGia < 0) return { loi: "Đơn giá phải là số không âm." };
  var ngay = chu(d.ngay_giao);
  if (ngay) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ngay);
    var ngayThat = false;
    if (m) {
      var t = new Date(ngay + "T00:00:00Z");
      ngayThat = !isNaN(t.getTime()) && t.toISOString().slice(0, 10) === ngay;
    }
    if (!ngayThat) return { loi: "Ngày giao chưa hợp lệ (dạng năm-tháng-ngày)." };
  }
  var ghiChu = chu(d.ghi_chu);
  if (ghiChu.length > 500) return { loi: "Ghi chú dài quá 500 ký tự." };
  var than = {
    khach_hang: khach,
    mat_hang: hang,
    so_luong_kg: soLuong,
    don_gia: donGia,
    thanh_tien: Math.round(soLuong * donGia * 100) / 100
  };
  if (ngay) than.ngay_giao = ngay;
  if (ghiChu) than.ghi_chu = ghiChu;
  var maHang = Number(d.mat_hang_id);
  if (isFinite(maHang) && maHang > 0) than.mat_hang_id = maHang;
  return { than: than };
}

/* Lời giải thích tiếng Việt cho mã lỗi API và ràng buộc CSDL. */
function thongBaoLoi(ma, than) {
  var d = than && typeof than === "object" ? than : {};
  if (typeof d.loi === "string" && d.loi) return d.loi;
  var loi = typeof d.message === "string" ? d.message : "";
  if (ma === 401) return "Phiên đăng nhập đã hết hạn — mở lại trang đăng nhập OneBee rồi thử lại.";
  if (ma === 403) return "Tài khoản không có quyền xem hoặc làm việc này ở cơ sở dữ liệu (mã 403).";
  if (ma === 413) return "Dữ liệu gửi lên quá lớn (tệp tối đa 10 MB, dữ liệu tối đa 1 MB).";
  if (ma === 415) return "Định dạng tệp không được nhận — chỉ nhận PDF, ảnh, văn bản, Word, Excel, ODT và ODS.";
  if (ma === 422) return "Tệp bị chặn do phát hiện mã độc — đơn hàng chưa được gửi.";
  if (ma === 503 || ma === 502) return "Dịch vụ của Box chưa sẵn sàng hoặc không trả lời — thử lại sau ít phút.";
  if (ma === 400) {
    if (loi.indexOf("muc_do_trong_danh_muc") >= 0) return "Mức độ không nằm trong danh mục (Bình thường hoặc Gấp).";
    if (loi.indexOf("loai_trong_danh_muc") >= 0) return "Loại sự cố không nằm trong danh mục của biểu mẫu.";
    if (loi.indexOf("khong_tu_duyet") >= 0) return "Không được tự duyệt đơn do chính mình tạo.";
    if (loi.indexOf("so_luong_duong_don_gia_khong_am") >= 0) return "Số lượng phải lớn hơn 0 và đơn giá không âm.";
    // Kho và kế toán: giữ nguyên lời báo tiếng Việt của CSDL (nêu mặt hàng, tồn còn, số cần)
    if (loi.indexOf("Không đủ tồn kho") >= 0) return loi;
    if (loi.indexOf("Số lượng nhập") >= 0 || loi.indexOf("Đơn giá nhập") >= 0 || loi.indexOf("Phiếu nhập") >= 0) return loi;
    if (loi.indexOf("Bút toán không cân") >= 0 || loi.indexOf("Mỗi dòng bút toán") >= 0) return loi;
    if (loi.indexOf("mat_hang_chua_co") >= 0) {
      return "Mặt hàng của đơn chưa có trong danh mục kho — vào khu Kho thêm mặt hàng rồi duyệt lại.";
    }
    if (loi.indexOf("mat_hang_ma_key") >= 0 || loi.indexOf("mat_hang_ten_key") >= 0 || loi.indexOf("duplicate key") >= 0) {
      return "Mã hoặc tên mặt hàng đã có trong danh mục — dùng mã/tên khác.";
    }
    return "Dữ liệu gửi lên chưa hợp lệ — kiểm tra lại các ô rồi thử lại (mã 400).";
  }
  if (ma === 409) return "Việc này vừa được người khác xử lý — tải lại trang để xem trạng thái mới.";
  return "Box báo lỗi mã " + ma + " — thử lại sau hoặc báo người quản trị.";
}

/* Chỉ giữ số liệu tổng hợp; tên người, số điện thoại, ghi chú, tên tệp không vào lời nhắc. */
function lamSachSoLieu(du) {
  var kq = {}, nguon = du && typeof du === "object" ? du : {};
  function muc(ten, khoa) {
    var x = nguon[ten], ra = {};
    if (!x || typeof x !== "object") return;
    for (var i = 0; i < khoa.length; i++) if (soKhongAm(x[khoa[i]])) ra[khoa[i]] = x[khoa[i]];
    if (Object.keys(ra).length) kq[ten] = ra;
  }
  muc("don_hang", ["tong", "cho_duyet", "da_duyet", "tu_choi"]);
  muc("ho_tro", ["tong", "gap"]);
  muc("tep", ["tong", "sach", "nhiem"]);
  if (soKhongAm(nguon.may_tram)) kq.may_tram = nguon.may_tram;
  if (Array.isArray(nguon.khao_sat)) {
    var tuan = [];
    for (var i = 0; i < nguon.khao_sat.length; i++) {
      var x = nguon.khao_sat[i];
      if (!x || typeof x !== "object" || !/^\d{4}-\d{2}-\d{2}$/.test(chu(x.tuan))) continue;
      var tb = soKhongAm(x.diem_tb) ? x.diem_tb : null;
      if (tb === null) {
        var tong = 0, du = 0;
        for (var j = 1; j <= 5; j++) {
          if (soKhongAm(x["diem_" + j])) { tong += x["diem_" + j]; du++; }
        }
        if (du === 5) tb = Math.round((tong / 5) * 10) / 10;
      }
      if (tb === null || !soKhongAm(x.so_phieu)) continue;
      tuan.push({ tuan: chu(x.tuan), so_phieu: x.so_phieu, diem_tb: tb });
    }
    if (tuan.length) kq.khao_sat = tuan;
  }
  return kq;
}

function taoLoiNhacTomTat(soLieu) {
  return MAU_TOM_TAT + "\n" + JSON.stringify(lamSachSoLieu(soLieu));
}

function docJson(chuoi) {
  try { return JSON.parse(chuoi); } catch (e) { return null; }
}

function goiApi(duong, tuyChon) {
  var o = tuyChon || {}, tieuDe = { "Accept": "application/json" };
  if (o.than !== undefined) tieuDe["Content-Type"] = "application/json";
  if (o.dem) tieuDe["Prefer"] = "count=exact";
  return fetch(duong, {
    method: o.phuongThuc || "GET",
    headers: tieuDe,
    body: o.than !== undefined ? JSON.stringify(o.than) : undefined,
    credentials: "same-origin",
    cache: "no-store"
  }).then(function (r) {
    if (o.head) {
      if (!r.ok) return r.text().then(function (t) { throw thanhLoi(r.status, docJson(t)); });
      return docSoDong(r.headers.get("Content-Range"));
    }
    return r.text().then(function (t) {
      var d = docJson(t);
      if (!r.ok) throw thanhLoi(r.status, d);
      return d;
    });
  });
}

function thanhLoi(ma, than) {
  var e = new Error(thongBaoLoi(ma, than));
  e.ma = ma;
  e.than = than;
  return e;
}

function hienThongBao(id, chu, loi) {
  var o = document.getElementById(id);
  if (!o) return;
  o.textContent = chu;
  o.className = "thong-bao" + (loi ? " loi" : "");
  o.hidden = false;
}

function anThongBao(id) {
  var o = document.getElementById(id);
  if (o) o.hidden = true;
}

function chonKhu(ma) {
  for (var i = 0; i < TEN_KHU.length; i++) {
    var k = document.getElementById(TEN_KHU[i]);
    var nut = document.querySelector('[data-khu="' + TEN_KHU[i] + '"]');
    if (!k || !nut) continue;
    k.className = "khu" + (TEN_KHU[i] === ma ? " hien" : "");
    nut.setAttribute("aria-selected", TEN_KHU[i] === ma ? "true" : "false");
  }
  if (ma === "khu-d") taiBangDieuHanh().catch(function () {});
  if (ma === "khu-p") taiChoDuyet().catch(function () {});
  if (ma === "khu-k") {
    taiTonKho().catch(function (e) { hienThongBao("kq-ton", e.message, true); });
    taiSoKho().catch(function (e) { hienThongBao("kq-so-kho", e.message, true); });
  }
  if (ma === "khu-t") {
    taiNhatKy().catch(function (e) { hienThongBao("tq-nhat-ky", e.message, true); });
    taiCanDoi().catch(function (e) { hienThongBao("tq-nhat-ky", e.message, true); });
  }
}

function dem(duong) {
  return goiApi(duong, { phuongThuc: "HEAD", head: true, dem: true });
}

function taiHoSo() {
  return goiApi("/api/toi").then(function (d) {
    HOSO.ten = chu(d && d.ten);
    HOSO.vai_tro = chu(d && d.vai_tro);
    document.getElementById("ten-nguoi-dung").textContent = HOSO.ten || "—";
    document.getElementById("vai-tro").textContent = HOSO.vai_tro || "—";
    document.getElementById("h-ten").textContent = HOSO.ten || "—";
    document.getElementById("h-vai-tro").textContent = HOSO.vai_tro || "—";
    document.getElementById("h-quyen").textContent =
      "Quyền được kiểm ở cơ sở dữ liệu cho từng dòng; trang này chỉ hiển thị.";
    var quanLy = HOSO.vai_tro === "quan_ly";
    document.getElementById("h-cho-toi-o").hidden = !quanLy;
    // Khu Kho và Kế toán chỉ mở theo vai trò; quyền thật vẫn do CSDL kiểm (RLS)
    var laKho = VAI_TRO_KHO.indexOf(HOSO.vai_tro) >= 0;
    var laKeToan = VAI_TRO_KE_TOAN.indexOf(HOSO.vai_tro) >= 0;
    document.getElementById("nut-khu-k").hidden = !laKho;
    document.getElementById("nut-khu-t").hidden = !laKeToan;
    document.getElementById("k-than").hidden = !laKho;
    document.getElementById("t-than").hidden = !laKeToan;
    document.getElementById("k-chan-quyen").hidden = laKho;
    document.getElementById("t-chan-quyen").hidden = laKeToan;
    var cong = document.body.getAttribute("data-cong-giam-sat");
    if (HOSO.vai_tro && cong) {
      var o = document.getElementById("h-giam-sat-o");
      var a = document.getElementById("h-giam-sat");
      a.setAttribute("href", window.location.protocol + "//" + window.location.hostname + ":" + cong + "/giam-sat/");
      o.hidden = false;
    }
    document.getElementById("phien-loi") && (document.getElementById("phien-loi").hidden = true);
    return d;
  });
}

function taiViecCuaToi() {
  return dem("/api/don_hang?select=id&trang_thai_duyet=eq.CHO_DUYET&nguoi_tao=eq." + encodeURIComponent(HOSO.ten))
    .then(function (n) { document.getElementById("h-don-cho").textContent = n === null ? "—" : n; })
    .then(function () {
      if (HOSO.vai_tro !== "quan_ly") return null;
      return dem("/api/don_hang?select=id&trang_thai_duyet=eq.CHO_DUYET&nguoi_tao=neq." + encodeURIComponent(HOSO.ten))
        .then(function (n) { document.getElementById("h-cho-toi").textContent = n === null ? "—" : n; });
    });
}

function oChu(noiDung) {
  var td = document.createElement("td");
  td.textContent = noiDung;
  return td;
}

function taiChoDuyet() {
  return goiApi("/api/don_hang?trang_thai_duyet=eq.CHO_DUYET&select=id,khach_hang,mat_hang,thanh_tien,nguoi_tao,ghi_chu&order=thoi_gian.asc")
    .then(function (ds) {
      var than = document.getElementById("bang-cho-duyet");
      while (than.firstChild) than.removeChild(than.firstChild);
      if (!Array.isArray(ds) || ds.length === 0) {
        var trong = document.createElement("tr");
        var o = oChu("Không có đơn chờ duyệt.");
        o.setAttribute("colspan", "7");
        trong.appendChild(o);
        than.appendChild(trong);
        return;
      }
      for (var i = 0; i < ds.length; i++) {
        var d = ds[i], tr = document.createElement("tr");
        tr.appendChild(oChu(String(d.id)));
        tr.appendChild(oChu(chu(d.khach_hang)));
        tr.appendChild(oChu(chu(d.mat_hang)));
        tr.appendChild(oChu(Number(d.thanh_tien).toLocaleString("vi-VN") + " đồng"));
        tr.appendChild(oChu(chu(d.nguoi_tao)));
        var gc = chu(d.ghi_chu), tenTep = gc.indexOf("[Tệp:") >= 0 ? gc.slice(gc.indexOf("[Tệp:")) : "—";
        tr.appendChild(oChu(tenTep));
        var td = document.createElement("td");
        if (HOSO.vai_tro !== "quan_ly") {
          td.textContent = "Chỉ quản lý duyệt được";
        } else if (chu(d.nguoi_tao) === HOSO.ten) {
          td.textContent = "Không tự duyệt";
        } else {
          var duyet = document.createElement("button");
          duyet.type = "button";
          duyet.className = "nut";
          duyet.textContent = "Duyệt";
          duyet.addEventListener("click", function (id) { return function () { duyetDon(id, "DA_DUYET"); }; }(d.id));
          var tuChoi = document.createElement("button");
          tuChoi.type = "button";
          tuChoi.className = "nut tu-choi";
          tuChoi.textContent = "Từ chối";
          tuChoi.addEventListener("click", function (id) { return function () { duyetDon(id, "TU_CHOI"); }; }(d.id));
          td.appendChild(duyet);
          td.appendChild(tuChoi);
        }
        tr.appendChild(td);
        than.appendChild(tr);
      }
    });
}

function duyetDon(id, quyetDinh) {
  var lyDo = chu(document.getElementById("ly-do-duyet").value);
  if (quyetDinh === "TU_CHOI" && !lyDo) {
    hienThongBao("kq-duyet", "Từ chối phải ghi lý do.", true);
    return;
  }
  goiApi("/quy-trinh/webhook/onebee-phe-duyet", {
    phuongThuc: "POST",
    than: { id: Number(id), trang_thai_duyet: quyetDinh, ly_do_duyet: lyDo || null }
  }).then(function (d) {
    hienThongBao("kq-duyet", "Đơn " + id + " đã " + (quyetDinh === "DA_DUYET" ? "được duyệt" : "bị từ chối") +
      (d && d.nguoi_duyet ? " bởi " + d.nguoi_duyet : "") + ".", false);
    document.getElementById("ly-do-duyet").value = "";
    taiChoDuyet().catch(function (e) { hienThongBao("kq-duyet", e.message, true); });
    taiBangDieuHanh().catch(function () {});
    taiViecCuaToi().catch(function () {});
  }).catch(function (e) {
    hienThongBao("kq-duyet", e.message, true);
  });
}

function taiBangDieuHanh() {
  return goiApi("/api/khao_sat_tong_hop?select=tuan,so_phieu,diem_1,diem_2,diem_3,diem_4,diem_5&order=tuan.desc&limit=12")
    .then(function (ks) {
      document.getElementById("d-chan-quyen").hidden = true;
      document.getElementById("d-so-lieu").hidden = false;
      var viec = [
        dem("/api/don_hang?select=id"),
        dem("/api/don_hang?select=id&trang_thai_duyet=eq.CHO_DUYET"),
        dem("/api/don_hang?select=id&trang_thai_duyet=eq.DA_DUYET"),
        dem("/api/don_hang?select=id&trang_thai_duyet=eq.TU_CHOI"),
        dem("/api/yeu_cau_ho_tro?select=id"),
        dem("/api/yeu_cau_ho_tro?select=id&muc_do=eq.gap"),
        dem("/api/tinh_trang_may?select=ten"),
        dem("/api/tep_dinh_kem?select=id"),
        dem("/api/tep_dinh_kem?select=id&trang_thai_quet=eq.CLEAN"),
        dem("/api/tep_dinh_kem?select=id&trang_thai_quet=eq.INFECTED")
      ];
      return Promise.all(viec).then(function (n) { return { n: n, ks: Array.isArray(ks) ? ks : [] }; });
    })
    .then(function (d) {
      var n = d.n, ks = d.ks, than = document.getElementById("d-khao-sat");
      function hienSo(id, giaTri) {
        document.getElementById(id).textContent = giaTri === null ? "—" : String(giaTri);
      }
      hienSo("d-don-tong", n[0]);
      document.getElementById("d-don-chi-tiet").textContent =
        (n[1] === null ? "—" : n[1]) + " chờ duyệt · " + (n[2] === null ? "—" : n[2]) + " đã duyệt · " +
        (n[3] === null ? "—" : n[3]) + " từ chối";
      hienSo("d-ht-tong", n[4]);
      document.getElementById("d-ht-chi-tiet").textContent = (n[5] === null ? "—" : n[5]) + " yêu cầu gấp";
      hienSo("d-may-tong", n[6]);
      hienSo("d-tep-tong", n[7]);
      document.getElementById("d-tep-chi-tiet").textContent =
        (n[8] === null ? "—" : n[8]) + " sạch · " + (n[9] === null ? "—" : n[9]) + " cách ly";
      while (than.firstChild) than.removeChild(than.firstChild);
      SO_LIEU.khao_sat = [];
      if (!ks.length) {
        var trong = document.createElement("tr"), o = oChu("Chưa có số liệu.");
        o.setAttribute("colspan", "7");
        trong.appendChild(o);
        than.appendChild(trong);
      }
      for (var i = 0; i < ks.length; i++) {
        var x = ks[i], tr = document.createElement("tr");
        tr.appendChild(oChu(chu(x.tuan)));
        tr.appendChild(oChu(String(x.so_phieu)));
        var tong = 0, du = 0;
        for (var j = 1; j <= 5; j++) {
          var diem = Number(x["diem_" + j]);
          tr.appendChild(oChu(isFinite(diem) ? diem.toLocaleString("vi-VN", { maximumFractionDigits: 2 }) : "—"));
          if (isFinite(diem)) { tong += diem; du++; }
        }
        than.appendChild(tr);
        SO_LIEU.khao_sat.push({
          tuan: chu(x.tuan),
          so_phieu: Number(x.so_phieu),
          diem_tb: du === 5 ? Math.round((tong / 5) * 10) / 10 : null
        });
      }
      var n = d.n;
      SO_LIEU.don_hang = {};
      if (soKhongAm(n[0])) SO_LIEU.don_hang.tong = n[0];
      if (soKhongAm(n[1])) SO_LIEU.don_hang.cho_duyet = n[1];
      if (soKhongAm(n[2])) SO_LIEU.don_hang.da_duyet = n[2];
      if (soKhongAm(n[3])) SO_LIEU.don_hang.tu_choi = n[3];
      SO_LIEU.ho_tro = {};
      if (soKhongAm(n[4])) SO_LIEU.ho_tro.tong = n[4];
      if (soKhongAm(n[5])) SO_LIEU.ho_tro.gap = n[5];
      if (soKhongAm(n[6])) SO_LIEU.may_tram = n[6];
      SO_LIEU.tep = {};
      if (soKhongAm(n[7])) SO_LIEU.tep.tong = n[7];
      if (soKhongAm(n[8])) SO_LIEU.tep.sach = n[8];
      if (soKhongAm(n[9])) SO_LIEU.tep.nhiem = n[9];
      SO_LIEU.khao_sat = SO_LIEU.khao_sat.filter(function (x) { return soKhongAm(x.diem_tb); });
    })
    .catch(function (e) {
      if (e.ma === 403 || e.ma === 401) {
        document.getElementById("d-chan-quyen").hidden = false;
        document.getElementById("d-so-lieu").hidden = true;
      }
      throw e;
    });
}

function guiTep(tep, don) {
  var ten = chu(tep.name), duoi = ten.slice(ten.lastIndexOf(".")).toLowerCase();
  if (DUOI_TEP.indexOf(duoi) < 0) return Promise.reject(new Error("Định dạng tệp không nằm trong danh mục cho phép."));
  if (tep.size > TOI_DA_TEP) return Promise.reject(new Error("Tệp vượt quá giới hạn 10 MB."));
  return fetch("/files/" + encodeURIComponent(ten), {
    method: "POST",
    headers: { "Accept": "application/json" },
    body: tep,
    credentials: "same-origin",
    cache: "no-store"
  }).then(function (r) {
    return r.text().then(function (t) {
      var d = docJson(t);
      if (!r.ok) throw thanhLoi(r.status, d);
      var meta = d && d.tep ? d.tep : (Array.isArray(d) ? d[0] : d);
      if (!meta || meta.trang_thai_quet !== "CLEAN") {
        throw new Error("Tệp bị chặn do phát hiện mã độc hoặc chưa qua kiểm dịch — đơn hàng chưa được gửi.");
      }
      return meta;
    });
  });
}

function ganTepVaoDon(maTep, maDon) {
  if (!maTep || !maDon) return Promise.resolve();
  return goiApi("/api/tep_dinh_kem?id=eq." + encodeURIComponent(maTep), {
    phuongThuc: "PATCH",
    than: { doi_tuong_gan: "don_hang:" + maDon }
  }).catch(function () {});   // lược đồ kho tệp chưa có cột đối tượng gắn: tệp vẫn trong kho, đơn vẫn tạo được
}

function taiDon(ev) {
  ev.preventDefault();
  anThongBao("kq-don");
  var chonHang = document.getElementById("don-mat-hang");
  var maHang = chonHang.value ? Number(chonHang.value) : null;
  var d = {
    khach_hang: document.getElementById("don-khach").value,
    mat_hang: maHang ? tenMatHang(maHang) : "",
    mat_hang_id: maHang,
    so_luong_kg: document.getElementById("don-so-luong").value,
    don_gia: document.getElementById("don-gia").value,
    ngay_giao: document.getElementById("don-ngay-giao").value,
    ghi_chu: document.getElementById("don-ghi-chu").value
  };
  var kq = dungDonHang(d);
  if (kq.loi) { hienThongBao("kq-don", kq.loi, true); return; }
  var nut = ev.target.querySelector('button[type="submit"]');
  nut.disabled = true;
  var tep = document.getElementById("don-tep").files[0] || null;
  var than = kq.than, metaTep = null;
  (tep ? guiTep(tep).then(function (m) {
    metaTep = m;
    var nhan = "[Tệp: " + chu(m.ten_tep) + "]";
    than.ghi_chu = (than.ghi_chu ? than.ghi_chu + " " : "") + nhan;
    if (than.ghi_chu.length > 500) than.ghi_chu = than.ghi_chu.slice(0, 500);
  }) : Promise.resolve())
    .then(function () {
      return goiApi("/api/don_hang", { phuongThuc: "POST", than: than });
    })
    .then(function (tra) {
      var don = Array.isArray(tra) ? tra[0] : tra;
      var id = don && don.id ? don.id : null;
      return ganTepVaoDon(metaTep && metaTep.id, id).then(function () {
        hienThongBao("kq-don", "Đã gửi đơn" + (id ? " số " + id : "") + " ở trạng thái chờ duyệt" +
          (metaTep ? "; tệp đính kèm đã qua kiểm dịch (CLEAN)" : "") + ".", false);
        ev.target.reset();
        document.getElementById("don-thanh-tien").textContent = "0";
        taiViecCuaToi().catch(function () {});
        taiBangDieuHanh().catch(function () {});
        taiChoDuyet().catch(function () {});
      });
    })
    .catch(function (e) { hienThongBao("kq-don", e.message, true); })
    .then(function () { nut.disabled = false; });
}

function taiHoTro(ev) {
  ev.preventDefault();
  anThongBao("kq-ho-tro");
  var d = {
    may: chu(document.getElementById("ht-may").value),
    loai: document.getElementById("ht-loai").value,
    muc_do: document.getElementById("ht-muc-do").value,
    nguoi_bao: chu(document.getElementById("ht-nguoi-bao").value),
    mo_ta: chu(document.getElementById("ht-mo-ta").value)
  };
  if (!d.loai) { hienThongBao("kq-ho-tro", "Vui lòng chọn loại sự cố.", true); return; }
  if (d.may.length > 64) { hienThongBao("kq-ho-tro", "Tên máy dài quá 64 ký tự.", true); return; }
  if (d.nguoi_bao.length > 100) { hienThongBao("kq-ho-tro", "Người báo dài quá 100 ký tự.", true); return; }
  if (d.mo_ta.length > 1500) { hienThongBao("kq-ho-tro", "Mô tả dài quá 1500 ký tự.", true); return; }
  goiApi("/api/yeu_cau_ho_tro", { phuongThuc: "POST", than: d })
    .then(function () {
      hienThongBao("kq-ho-tro", "Đã ghi nhận yêu cầu hỗ trợ.", false);
      ev.target.reset();
      taiBangDieuHanh().catch(function () {});
    })
    .catch(function (e) { hienThongBao("kq-ho-tro", e.message, true); });
}

function taiKhaoSat(ev) {
  ev.preventDefault();
  anThongBao("kq-khao-sat");
  var d = { gop_y: chu(document.getElementById("ks-gop-y").value) };
  for (var i = 1; i <= 5; i++) {
    var diem = Number(document.getElementById("ks-" + i).value);
    if (!isFinite(diem) || diem < 1 || diem > 5 || Math.floor(diem) !== diem) {
      hienThongBao("kq-khao-sat", "Điểm phải là số nguyên từ 1 đến 5.", true);
      return;
    }
    d["diem_" + i] = diem;
  }
  if (d.gop_y.length > 500) { hienThongBao("kq-khao-sat", "Góp ý dài quá 500 ký tự.", true); return; }
  goiApi("/api/khao_sat", { phuongThuc: "POST", than: d })
    .then(function () {
      hienThongBao("kq-khao-sat", "Đã gửi phiếu khảo sát ẩn danh.", false);
      ev.target.reset();
      taiBangDieuHanh().catch(function () {});
    })
    .catch(function (e) { hienThongBao("kq-khao-sat", e.message, true); });
}

function hoiTroLy() {
  anThongBao("i-ket-qua");
  var cauHoi = chu(document.getElementById("i-cau-hoi").value);
  if (!cauHoi) { hienThongBao("i-ket-qua", "Vui lòng nhập câu hỏi.", true); return; }
  var nut = document.getElementById("i-hoi");
  nut.disabled = true;
  goiApi("/ai/hoi", { phuongThuc: "POST", than: { cau_hoi: cauHoi } })
    .then(function (d) {
      var traLoi = chu(d && d.tra_loi);
      var nguon = d && Array.isArray(d.nguon) ? d.nguon : [];
      if (nguon.length) {
        traLoi += "\n\nNguồn tham khảo:";
        for (var i = 0; i < nguon.length; i++) {
          traLoi += "\n[" + (i + 1) + "] " + chu(nguon[i].tieu_de) + " (" + chu(nguon[i].nguon) + ")";
        }
      }
      hienThongBao("i-ket-qua", traLoi || "Trợ lý không trả lời được.", false);
    })
    .catch(function (e) { hienThongBao("i-ket-qua", e.message, true); })
    .then(function () { nut.disabled = false; });
}

function tomTatTuan() {
  anThongBao("i-ket-qua");
  if (HOSO.vai_tro !== "quan_ly") {
    hienThongBao("i-ket-qua", "Tóm tắt tuần dành cho quản lý — tài khoản này không đọc được số liệu tổng hợp.", true);
    return;
  }
  var nut = document.getElementById("i-tom-tat");
  nut.disabled = true;
  taiBangDieuHanh()
    .then(function () {
      var noiDung = taoLoiNhacTomTat(SO_LIEU);
      return goiApi("/ai/tom-tat", { phuongThuc: "POST", than: { noi_dung: noiDung } });
    })
    .then(function (d) {
      hienThongBao("i-ket-qua", chu(d && d.tom_tat) || "Trợ lý không trả lời được.", false);
    })
    .catch(function (e) { hienThongBao("i-ket-qua", e.message, true); })
    .then(function () { nut.disabled = false; });
}

function capNhatThanhTien() {
  var soLuong = Number(document.getElementById("don-so-luong").value);
  var donGia = Number(document.getElementById("don-gia").value);
  var tong = isFinite(soLuong) && isFinite(donGia) && soLuong > 0 && donGia >= 0
    ? Math.round(soLuong * donGia * 100) / 100 : 0;
  document.getElementById("don-thanh-tien").textContent = tong.toLocaleString("vi-VN");
}

/* Mục menu mở ứng dụng kèm may/loai/mo_ta của máy trạm: điền sẵn, không tự gửi. */
function dienSanTuDiaChi() {
  if (typeof window === "undefined" || !window.location || typeof URLSearchParams === "undefined") return false;
  var q = new URLSearchParams(window.location.search);
  var may = chu(q.get("may")), loai = chu(q.get("loai")), moTa = chu(q.get("mo_ta"));
  if (may) document.getElementById("ht-may").value = may;
  if (loai) {
    var chon = document.getElementById("ht-loai"), ds = chon.options;
    for (var i = 0; i < ds.length; i++) {
      if (ds[i].value === loai || chu(ds[i].textContent) === loai) { chon.selectedIndex = i; break; }
    }
  }
  if (moTa) document.getElementById("ht-mo-ta").value = moTa;
  return Boolean(may || loai || moTa);
}

/* ---------- Danh mục mặt hàng cho biểu mẫu đơn ---------- */

function tenMatHang(id) {
  for (var i = 0; i < MAT_HANG.length; i++) {
    if (String(MAT_HANG[i].id) === String(id)) return chu(MAT_HANG[i].ten);
  }
  return "";
}

function dienChonMatHang(chon, giuChon) {
  var cu = giuChon ? chon.value : "";
  while (chon.firstChild) chon.removeChild(chon.firstChild);
  var dau = document.createElement("option");
  dau.value = "";
  dau.textContent = "— chọn mặt hàng —";
  chon.appendChild(dau);
  for (var i = 0; i < MAT_HANG.length; i++) {
    var m = MAT_HANG[i];
    if (m.hoat_dong === false) continue;
    var o = document.createElement("option");
    o.value = String(m.id);
    o.textContent = chu(m.ten) + (chu(m.don_vi) ? " (" + chu(m.don_vi) + ")" : "");
    chon.appendChild(o);
  }
  if (cu) chon.value = cu;
}

function taiVatTu() {
  return goiApi("/api/mat_hang?select=id,ten,don_vi,hoat_dong&order=ten.asc").then(function (ds) {
    MAT_HANG = Array.isArray(ds) ? ds : [];
    dienChonMatHang(document.getElementById("don-mat-hang"), true);
    dienChonMatHang(document.getElementById("nk-mat-hang"), true);
    var conHang = 0;
    for (var i = 0; i < MAT_HANG.length; i++) if (MAT_HANG[i].hoat_dong !== false) conHang++;
    document.getElementById("don-mat-hang-trong").hidden = conHang > 0;
  });
}

function khoiDong() {
  var moKhuP = dienSanTuDiaChi();
  var nutKhu = document.querySelectorAll("[data-khu]");
  for (var i = 0; i < nutKhu.length; i++) {
    nutKhu[i].addEventListener("click", function () { chonKhu(this.getAttribute("data-khu")); });
  }
  document.getElementById("form-don").addEventListener("submit", taiDon);
  document.getElementById("form-ho-tro").addEventListener("submit", taiHoTro);
  document.getElementById("form-khao-sat").addEventListener("submit", taiKhaoSat);
  document.getElementById("i-hoi").addEventListener("click", hoiTroLy);
  document.getElementById("i-tom-tat").addEventListener("click", tomTatTuan);
  document.getElementById("d-tai-lai").addEventListener("click", function () { taiBangDieuHanh().catch(function () {}); });
  document.getElementById("form-nhap-kho").addEventListener("submit", guiNhapKho);
  document.getElementById("form-mat-hang").addEventListener("submit", guiMatHang);
  document.getElementById("k-loc").addEventListener("click", function () {
    taiSoKho().catch(function (e) { hienThongBao("kq-so-kho", e.message, true); });
  });
  document.getElementById("t-loc").addEventListener("click", function () {
    taiNhatKy().catch(function (e) { hienThongBao("tq-nhat-ky", e.message, true); });
    taiCanDoi().catch(function (e) { hienThongBao("tq-nhat-ky", e.message, true); });
  });
  document.getElementById("k-xuat-ton").addEventListener("click", xuatTonKhoCsv);
  document.getElementById("k-xuat-so").addEventListener("click", xuatSoKhoCsv);
  document.getElementById("t-xuat-nhat-ky").addEventListener("click", xuatNhatKyCsv);
  document.getElementById("t-xuat-can-doi").addEventListener("click", xuatCanDoiCsv);
  document.getElementById("don-so-luong").addEventListener("input", capNhatThanhTien);
  document.getElementById("don-gia").addEventListener("input", capNhatThanhTien);
  capNhatThanhTien();
  taiHoSo()
    .then(function () {
      return taiVatTu().catch(function () { return null; });
    })
    .then(function () {
      return taiViecCuaToi();
    })
    .then(function () {
      return taiChoDuyet();
    })
    .then(function () {
      if (HOSO.vai_tro === "quan_ly") return taiBangDieuHanh();
      return null;
    })
    .then(function () { if (moKhuP) chonKhu("khu-p"); })
    .catch(function (e) { hienThongBao("thong-bao-chung", e.message, true); });
}

if (typeof document !== "undefined" && typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", khoiDong);
}
