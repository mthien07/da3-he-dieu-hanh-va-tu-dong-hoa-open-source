#!/usr/bin/env python3
"""Kiểm tra THẬT cấu hình LibreOffice (qua UNO) sau khi cài OneBee OS Desktop:
định dạng lưu mặc định của Writer/Calc/Impress là Microsoft Office, đã tắt cảnh báo định dạng
và giao diện mặc định là Ribbon (Tabbed Notebookbar).
Cần gói python3-uno. Thoát mã 1 nếu sai."""
import os
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue

EXPECTED = {
    "com.sun.star.text.TextDocument": "MS Word 2007 XML",
    "com.sun.star.sheet.SpreadsheetDocument": "Calc MS Excel 2007 XML",
    "com.sun.star.presentation.PresentationDocument": "Impress MS PowerPoint 2007 XML",
}
PORT = 2002


def connect():
    """Chờ LibreOffice headless mở cổng UNO rồi trả về component context."""
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            return resolver.resolve(f"uno:socket,host=localhost,port={PORT};urp;StarOffice.ComponentContext")
        except Exception:  # LibreOffice chưa sẵn sàng
            time.sleep(1)
    sys.exit("FAIL  Không kết nối được LibreOffice headless")


def read(provider, path, prop):
    arg = PropertyValue(Name="nodepath", Value=path)
    node = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
    return node.getPropertyValue(prop)


def che_do_dang_bat(provider, app):
    """(giá trị Active, chế độ đó có hiện Ribbon không) — so như LibreOffice: Active phải trùng CommandArg của một chế độ
    trong Modes của chính bản đang cài, và chế độ đó có HasNotebookbar. Active không khớp chế độ nào → LibreOffice mở thanh công cụ cũ."""
    duong = f"/org.openoffice.Office.UI.ToolbarMode/Applications/org.openoffice.Office.UI.ToolbarMode:Application['{app}']"
    active = read(provider, duong, "Active")
    arg = PropertyValue(Name="nodepath", Value=duong + "/Modes")
    modes = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
    for ten in modes.getElementNames():
        m = modes.getByName(ten)
        if m.getPropertyValue("CommandArg") == active:
            return active, bool(m.getPropertyValue("HasNotebookbar"))
    return active, False


def main():
    profile = tempfile.mkdtemp(prefix="onebee-lo-")  # hồ sơ người dùng sạch, như người dùng mới
    proc = subprocess.Popen(
        ["soffice", "--headless", "--invisible", "--norestore",
         f"-env:UserInstallation=file://{profile}",
         f"--accept=socket,host=localhost,port={PORT};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "HOME": profile})
    fails = 0
    try:
        ctx = connect()
        provider = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", ctx)
        for factory, want in EXPECTED.items():
            got = read(provider, f"/org.openoffice.Setup/Office/Factories/org.openoffice.Setup:Factory['{factory}']",
                       "ooSetupFactoryDefaultFilter")
            ok = got == want
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  LibreOffice {factory.split('.')[-1]} lưu mặc định: {got}")
        for app in ("Writer", "Calc", "Impress"):
            got, co_ribbon = che_do_dang_bat(provider, app)
            ok = co_ribbon and got == "notebookbar.ui"
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  LibreOffice {app} mở mặc định giao diện Ribbon (Tabbed): {got}")
        warn = read(provider, "/org.openoffice.Office.Common/Save/Document", "WarnAlienFormat")
        fails += bool(warn)
        print(f"{'FAIL' if warn else 'PASS'}  LibreOffice tắt cảnh báo khi lưu định dạng Microsoft")
        try:
            ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx).terminate()
        except Exception:  # LibreOffice đóng kết nối khi thoát — bình thường
            pass
    finally:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
