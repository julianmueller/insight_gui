from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gio

from insight_gui.widgets.helpers.pref_page import PrefPage


@Gtk.Template(filename=str(Path(__file__).with_suffix(".ui")))
class ContentPage(Adw.Bin):
    __gtype_name__ = "ContentPage"

    toolbar_view: Adw.ToolbarView = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    search_btn: Gtk.ToggleButton = Gtk.Template.Child()
    refresh_btn: Gtk.Button = Gtk.Template.Child()

    search_bar: Gtk.SearchBar = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    banner: Adw.Banner = Gtk.Template.Child()
    content_stack: Gtk.Stack = Gtk.Template.Child()

    refresh_page: Adw.StatusPage = Gtk.Template.Child()
    empty_search_page: Adw.StatusPage = Gtk.Template.Child()

    def __init__(
        self, refresh_func: Callable = lambda: None, search_enabled: bool = True, refresh_enabled: bool = True, **kwargs
    ):
        super().__init__(**kwargs)
        self.set_refresh_func(refresh_func)

        self.toggle_search_btn(search_enabled)
        self.toggle_refresh_btn(refresh_enabled)

        self.pref_page = PrefPage()
        self.content_stack.add_child(self.pref_page)
        if refresh_enabled:
            self.content_stack.set_visible_child(self.refresh_page)
        else:
            self.content_stack.set_visible_child(self.pref_page)

        # self.search_bar.set_key_capture_widget(self.get_root())
        self.search_btn.bind_property(
            "active", self.search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL
        )

    @Gtk.Template.Callback()
    def on_search_changed(self, *args):
        self.pref_page.apply_filter(self.search_entry.get_text())

    @Gtk.Template.Callback()
    def on_refresh(self, *args):
        self.search_bar.set_search_mode(False)
        GLib.idle_add(self.refresh_func)
        self.content_stack.set_visible_child(self.pref_page)

    def show_toast(self, toast_text: str):
        self.toast_overlay.add_toast(Adw.Toast(title=str(toast_text)))

    def show_toast_w_btn(self, toast_text: str, btn_label: str, func: Callable, **func_kwargs):
        toast = Adw.Toast(title=str(toast_text), button_label=str(btn_label))
        toast.connect("button-clicked", lambda toast, *_: func(**func_kwargs))
        self.toast_overlay.add_toast(toast)

    def show_banner(self, banner_text: str):
        self.banner.set_text(str(banner_text))
        self.banner.set_revealed(True)

    def show_banner_w_btn(self, banner_text: str, btn_label: str, func: Callable, **func_kwargs):
        self.banner.set_text(str(banner_text))
        self.banner.set_button_label(str(btn_label))
        self.banner.connect("button-clicked", lambda toast, *_: func(**func_kwargs))
        self.banner.set_revealed(True)

    def hide_banner(self):
        self.banner.set_revealed(False)

    def add_header_btn(self, icon_name: str, tooltip_text: str, func: Callable, **func_kwargs) -> Gtk.Button:
        btn = Gtk.Button.new_from_icon_name(icon_name)
        btn.set_tooltip_text(tooltip_text)
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.header_bar.pack_start(btn)
        return btn

    def add_header_widget(self, widget: Gtk.Widget) -> Gtk.Widget:
        self.header_bar.pack_start(widget)
        return widget

    def set_search_entry_placeholder_text(self, text: str):
        self.search_entry.set_placeholder_text(str(text))

    def set_refresh_func(self, func: Callable):
        self.refresh_func = lambda *_: func() and False

    def toggle_search_btn(self, enabled: bool):
        self.search_btn.set_visible(enabled)

    def toggle_refresh_btn(self, enabled: bool):
        self.refresh_btn.set_visible(enabled)
