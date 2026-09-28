#!/usr/bin/env python3
"""Cửa sổ GTK có 1 ô nhập. Nhấn Enter → ghi nội dung ô nhập ra file (argv[1]) rồi thoát.
Dùng để kiểm tra gõ tiếng Việt thật qua IBus (không cần người ngồi gõ)."""
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def main():
    out_path = sys.argv[1]
    win = Gtk.Window(title="OneBee IME test")
    entry = Gtk.Entry()

    def on_activate(widget):
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(widget.get_text())
        Gtk.main_quit()

    entry.connect("activate", on_activate)
    win.add(entry)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    entry.grab_focus()
    Gtk.main()


if __name__ == "__main__":
    main()
