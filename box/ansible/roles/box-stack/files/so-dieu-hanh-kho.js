/* SPDX-License-Identifier: MIT */
/* Quản lý bởi OneBee OS. Khu Kho và Khu Kế toán của Sổ điều hành: tồn kho, nhập kho, sổ kho, sổ nhật ký kép,
   bảng cân đối tài khoản và xuất CSV. Không thư viện ngoài; dữ liệu chỉ vào trang bằng textContent;
   quyền kiểm ở CSDL (RLS). Nạp sau so-dieu-hanh.js. */
"use strict";

/* ---------- Kho và kế toán ---------- */

function soHien(v, toiDa) {
  var n = Number(v);
  return isFinite(n) ? n.toLocaleString("vi-VN", { maximumFractionDigits: toiDa || 2 }) : "—";
}

/* CSV cho LibreOffice/Excel Việt Nam: BOM UTF-8, phân cách ';', số thập phân bằng dấu phẩy */
function soCsv(v) {
  var n = Number(v);
  return isFinite(n) ? n.toFixed(2).replace(".", ",") : "";
}

function oCsv(v) {
  var s = v === null || v === undefined ? "" : String(v);
  return '"' + s.replace(/"/g, '""') + '"';
}

function xuatCsv(ten, tieuDe, cacDong) {
  var dong = [tieuDe.map(oCsv).join(";")];
  for (var i = 0; i < cacDong.length; i++) dong.push(cacDong[i].map(oCsv).join(";"));
  var blob = new Blob(["\uFEFF" + dong.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = ten;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
}

function tenTepCsv(goc) {
  var d = new Date();
  var ngay = d.getFullYear() + String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
  return goc + "-" + ngay + ".csv";
}

var TON_KHO = [];
function taiTonKho() {
  return goiApi("/api/ton_kho?select=ma,ten,don_vi,ton,gia_von,gia_ban,ton_toi_thieu,hoat_dong&order=ten.asc").then(function (ds) {
    TON_KHO = Array.isArray(ds) ? ds : [];
    var than = document.getElementById("bang-ton-kho");
    while (than.firstChild) than.removeChild(than.firstChild);
    if (!TON_KHO.length) {
      var trong = document.createElement("tr"), o = oChu("Chưa có mặt hàng — thêm ở ô bên cạnh.");
      o.setAttribute("colspan", "7");
      trong.appendChild(o);
      than.appendChild(trong);
      return;
    }
    for (var i = 0; i < TON_KHO.length; i++) {
      var x = TON_KHO[i], tr = document.createElement("tr");
      tr.appendChild(oChu(chu(x.ma)));
      tr.appendChild(oChu(chu(x.ten)));
      tr.appendChild(oChu(chu(x.don_vi)));
      tr.appendChild(oChu(soHien(x.ton)));
      tr.appendChild(oChu(soHien(x.gia_von)));
      tr.appendChild(oChu(soHien(x.gia_ban)));
      tr.appendChild(oChu(soHien(x.ton_toi_thieu)));
      if (Number(x.ton) < Number(x.ton_toi_thieu)) tr.className = "duoi-ton";
      than.appendChild(tr);
    }
  });
}

function locNgay(duongCoBan, oTu, oDen) {
  var q = [];
  var tu = chu(document.getElementById(oTu).value), den = chu(document.getElementById(oDen).value);
  if (tu) q.push("ngay=gte." + tu);
  if (den) q.push("ngay=lte." + den);
  return duongCoBan + (q.length ? "&" + q.join("&") : "");
}

var SO_KHO = [];
function taiSoKho() {
  var duong = locNgay("/api/so_kho?select=so_phieu,ngay,loai,ten_hang,don_vi,so_luong,don_gia,thanh_tien,dien_gia" +
    "&order=ngay.desc,phieu_id.desc,dong_id.desc&limit=200", "k-tu-ngay", "k-den-ngay");
  return goiApi(duong).then(function (ds) {
    SO_KHO = Array.isArray(ds) ? ds : [];
    var than = document.getElementById("bang-so-kho");
    while (than.firstChild) than.removeChild(than.firstChild);
    if (!SO_KHO.length) {
      var trong = document.createElement("tr"), o = oChu("Chưa có phiếu kho nào trong khoảng ngày này.");
      o.setAttribute("colspan", "8");
      trong.appendChild(o);
      than.appendChild(trong);
      return;
    }
    for (var i = 0; i < SO_KHO.length; i++) {
      var x = SO_KHO[i], tr = document.createElement("tr");
      tr.appendChild(oChu(chu(x.so_phieu)));
      tr.appendChild(oChu(chu(x.ngay)));
      tr.appendChild(oChu(x.loai === "NHAP" ? "Nhập" : "Xuất"));
      tr.appendChild(oChu(chu(x.ten_hang)));
      tr.appendChild(oChu(soHien(x.so_luong) + " " + chu(x.don_vi)));
      tr.appendChild(oChu(soHien(x.don_gia)));
      tr.appendChild(oChu(soHien(x.thanh_tien)));
      tr.appendChild(oChu(chu(x.dien_gia)));
      than.appendChild(tr);
    }
  });
}

var NHAT_KY = [];
function taiNhatKy() {
  var duong = locNgay("/api/so_nhat_ky?select=so_hieu,ngay,dien_gia,chung_tu,tai_khoan,ten_tai_khoan,no,co" +
    "&order=ngay.desc,but_toan_id.desc,dong_id.desc&limit=500", "t-tu-ngay", "t-den-ngay");
  return goiApi(duong).then(function (ds) {
    NHAT_KY = Array.isArray(ds) ? ds : [];
    var than = document.getElementById("bang-nhat-ky");
    while (than.firstChild) than.removeChild(than.firstChild);
    if (!NHAT_KY.length) {
      var trong = document.createElement("tr"), o = oChu("Chưa có bút toán nào trong khoảng ngày này.");
      o.setAttribute("colspan", "8");
      trong.appendChild(o);
      than.appendChild(trong);
      return;
    }
    for (var i = 0; i < NHAT_KY.length; i++) {
      var x = NHAT_KY[i], tr = document.createElement("tr");
      tr.appendChild(oChu(chu(x.so_hieu)));
      tr.appendChild(oChu(chu(x.ngay)));
      tr.appendChild(oChu(chu(x.dien_gia)));
      tr.appendChild(oChu(chu(x.chung_tu)));
      tr.appendChild(oChu(chu(x.tai_khoan)));
      tr.appendChild(oChu(chu(x.ten_tai_khoan)));
      tr.appendChild(oChu(Number(x.no) > 0 ? soHien(x.no) : ""));
      tr.appendChild(oChu(Number(x.co) > 0 ? soHien(x.co) : ""));
      than.appendChild(tr);
    }
  });
}

var CAN_DOI = [];
function taiCanDoi() {
  return goiApi("/api/bang_can_doi?select=tai_khoan,ten,loai,tong_no,tong_co,du&order=tai_khoan.asc").then(function (ds) {
    CAN_DOI = Array.isArray(ds) ? ds : [];
    var than = document.getElementById("bang-can-doi");
    while (than.firstChild) than.removeChild(than.firstChild);
    if (!CAN_DOI.length) {
      var trong = document.createElement("tr"), o = oChu("Chưa có số liệu.");
      o.setAttribute("colspan", "6");
      trong.appendChild(o);
      than.appendChild(trong);
      return;
    }
    for (var i = 0; i < CAN_DOI.length; i++) {
      var x = CAN_DOI[i], tr = document.createElement("tr");
      var du = Number(x.du) || 0, duNo = 0, duCo = 0;
      if (x.loai === "tai_san" || x.loai === "chi_phi") {
        if (du >= 0) duNo = du; else duCo = -du;
      } else {
        if (du <= 0) duCo = -du; else duNo = du;
      }
      tr.appendChild(oChu(chu(x.tai_khoan)));
      tr.appendChild(oChu(chu(x.ten)));
      tr.appendChild(oChu(soHien(x.tong_no)));
      tr.appendChild(oChu(soHien(x.tong_co)));
      tr.appendChild(oChu(duNo > 0 ? soHien(duNo) : ""));
      tr.appendChild(oChu(duCo > 0 ? soHien(duCo) : ""));
      than.appendChild(tr);
    }
  });
}

function guiNhapKho(ev) {
  ev.preventDefault();
  anThongBao("kq-nhap-kho");
  var mh = document.getElementById("nk-mat-hang").value;
  var sl = document.getElementById("nk-so-luong").value;
  var dg = document.getElementById("nk-don-gia").value;
  var ngay = chu(document.getElementById("nk-ngay").value);
  var dien = chu(document.getElementById("nk-dien-gia").value);
  var soLuong = Number(sl), donGia = Number(dg);
  if (!mh) { hienThongBao("kq-nhap-kho", "Vui lòng chọn mặt hàng.", true); return; }
  if (!isFinite(soLuong) || soLuong <= 0) { hienThongBao("kq-nhap-kho", "Số lượng phải là số lớn hơn 0.", true); return; }
  if (dg === "" || !isFinite(donGia) || donGia < 0) { hienThongBao("kq-nhap-kho", "Đơn giá nhập phải là số không âm.", true); return; }
  if (dien.length > 200) { hienThongBao("kq-nhap-kho", "Diễn giải dài quá 200 ký tự.", true); return; }
  var nut = ev.target.querySelector('button[type="submit"]');
  nut.disabled = true;
  goiApi("/api/rpc/them_nhap_kho", {
    phuongThuc: "POST",
    than: {
      p_ngay: ngay || null,
      p_dien_gia: dien,
      p_dong: [{ mat_hang_id: Number(mh), so_luong: soLuong, don_gia: donGia }]
    }
  }).then(function (d) {
    var sp = d && d.so_phieu ? " " + chu(d.so_phieu) : "";
    hienThongBao("kq-nhap-kho", "Đã ghi phiếu nhập" + sp + ".", false);
    ev.target.reset();
    taiVatTu().catch(function () {});
    taiTonKho().catch(function () {});
    taiSoKho().catch(function () {});
  }).catch(function (e) {
    hienThongBao("kq-nhap-kho", e.message, true);
  }).then(function () { nut.disabled = false; });
}

function guiMatHang(ev) {
  ev.preventDefault();
  anThongBao("kq-mat-hang");
  var ma = chu(document.getElementById("mh-ma").value).toUpperCase();
  var ten = chu(document.getElementById("mh-ten").value);
  var dv = chu(document.getElementById("mh-don-vi").value) || "kg";
  var giaBan = Number(document.getElementById("mh-gia-ban").value || 0);
  if (!/^[A-Z0-9][A-Z0-9_-]{0,31}$/.test(ma)) {
    hienThongBao("kq-mat-hang", "Mã mặt hàng chỉ gồm chữ in hoa, số, gạch dưới, bắt đầu bằng chữ hoặc số (tối đa 32 ký tự).", true);
    return;
  }
  if (!ten) { hienThongBao("kq-mat-hang", "Vui lòng nhập tên mặt hàng.", true); return; }
  if (ten.length > 200) { hienThongBao("kq-mat-hang", "Tên mặt hàng dài quá 200 ký tự.", true); return; }
  if (!dv || dv.length > 16) { hienThongBao("kq-mat-hang", "Đơn vị tính phải có từ 1 đến 16 ký tự.", true); return; }
  if (!isFinite(giaBan) || giaBan < 0) { hienThongBao("kq-mat-hang", "Giá bán phải là số không âm.", true); return; }
  var nut = ev.target.querySelector('button[type="submit"]');
  nut.disabled = true;
  goiApi("/api/mat_hang", {
    phuongThuc: "POST",
    than: { ma: ma, ten: ten, don_vi: dv, gia_ban: giaBan }
  }).then(function () {
    hienThongBao("kq-mat-hang", "Đã thêm mặt hàng " + ten + ".", false);
    ev.target.reset();
    document.getElementById("mh-don-vi").value = "kg";
    taiVatTu().catch(function () {});
    taiTonKho().catch(function () {});
  }).catch(function (e) {
    hienThongBao("kq-mat-hang", e.message, true);
  }).then(function () { nut.disabled = false; });
}

function xuatTonKhoCsv() {
  if (!TON_KHO.length) { hienThongBao("kq-ton", "Chưa có dữ liệu tồn kho để xuất.", true); return; }
  var dong = [];
  for (var i = 0; i < TON_KHO.length; i++) {
    var x = TON_KHO[i];
    dong.push([chu(x.ma), chu(x.ten), chu(x.don_vi), soCsv(x.ton), soCsv(x.gia_von), soCsv(x.gia_ban), soCsv(x.ton_toi_thieu)]);
  }
  xuatCsv(tenTepCsv("ton-kho"), ["Mã", "Mặt hàng", "Đơn vị", "Tồn", "Giá vốn", "Giá bán", "Tồn tối thiểu"], dong);
}

function xuatSoKhoCsv() {
  if (!SO_KHO.length) { hienThongBao("kq-so-kho", "Chưa có phiếu kho để xuất.", true); return; }
  var dong = [];
  for (var i = 0; i < SO_KHO.length; i++) {
    var x = SO_KHO[i];
    dong.push([chu(x.so_phieu), chu(x.ngay), x.loai === "NHAP" ? "Nhập" : "Xuất", chu(x.ten_hang), chu(x.don_vi),
      soCsv(x.so_luong), soCsv(x.don_gia), soCsv(x.thanh_tien), chu(x.dien_gia)]);
  }
  xuatCsv(tenTepCsv("so-kho"), ["Số phiếu", "Ngày", "Loại", "Mặt hàng", "Đơn vị", "Số lượng", "Đơn giá", "Thành tiền", "Diễn giải"], dong);
}

function xuatNhatKyCsv() {
  if (!NHAT_KY.length) { hienThongBao("tq-nhat-ky", "Chưa có bút toán để xuất.", true); return; }
  var dong = [];
  for (var i = 0; i < NHAT_KY.length; i++) {
    var x = NHAT_KY[i];
    dong.push([chu(x.so_hieu), chu(x.ngay), chu(x.dien_gia), chu(x.chung_tu), chu(x.tai_khoan),
      chu(x.ten_tai_khoan), soCsv(x.no), soCsv(x.co)]);
  }
  xuatCsv(tenTepCsv("so-nhat-ky"), ["Số hiệu", "Ngày", "Diễn giải", "Chứng từ", "Tài khoản", "Tên tài khoản", "Nợ", "Có"], dong);
}

function xuatCanDoiCsv() {
  if (!CAN_DOI.length) { hienThongBao("tq-nhat-ky", "Chưa có bảng cân đối để xuất.", true); return; }
  var dong = [];
  for (var i = 0; i < CAN_DOI.length; i++) {
    var x = CAN_DOI[i], du = Number(x.du) || 0, duNo = 0, duCo = 0;
    if (x.loai === "tai_san" || x.loai === "chi_phi") {
      if (du >= 0) duNo = du; else duCo = -du;
    } else {
      if (du <= 0) duCo = -du; else duNo = du;
    }
    dong.push([chu(x.tai_khoan), chu(x.ten), soCsv(x.tong_no), soCsv(x.tong_co), soCsv(duNo), soCsv(duCo)]);
  }
  xuatCsv(tenTepCsv("bang-can-doi"), ["Tài khoản", "Tên tài khoản", "Tổng Nợ", "Tổng Có", "Dư Nợ", "Dư Có"], dong);
}

