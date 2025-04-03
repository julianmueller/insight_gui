# content_page.py
#
# Copyright (C) 2025 Julian Müller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
from typing import Callable
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gio

from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.detached_window import DetachedWindow


class ContentPage(Adw.NavigationPage):
    __gtype_name__ = "ContentPage"

    def __init__(
        self,
        searchable: bool = True,
        refreshable: bool = True,
        detachable: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().connect("realize", self.on_realize)
        GLib.idle_add(self._deferred_init)
        # super().connect("map", self.on_map)
        # super().connect("unmap", self.on_unmap)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.toolbar_view: Adw.ToolbarView = builder.get_object("toolbar_view")
        self.header_bar: Adw.HeaderBar = builder.get_object("header_bar")
        self.search_btn: Gtk.ToggleButton = builder.get_object("search_btn")
        self.search_btn.set_action_name("win.toggle-search")
        self.search_btn.set_sensitive(True)  # this is somehow needed

        self.refresh_btn: Gtk.Button = builder.get_object("refresh_btn")
        # self.refresh_btn.connect("clicked", self.on_refresh)
        self.refresh_btn.set_action_name("win.refresh")
        self.refresh_icon: Gtk.Image = builder.get_object("refresh_icon")
        self.refresh_spinner: Gtk.Spinner = builder.get_object("refresh_spinner")

        self.detach_btn: Gtk.Button = builder.get_object("detach_btn")
        # self.detach_btn.connect("clicked", self.on_detach)
        self.detach_btn.set_action_name("win.detach")
        self.search_bar: Gtk.SearchBar = builder.get_object("search_bar")
        self.search_btn.bind_property(
            "active", self.search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL
        )
        self.search_entry: Gtk.SearchEntry = builder.get_object("search_entry")
        self.search_entry.connect("search-changed", self.on_search_changed)

        self.toast_overlay: Adw.ToastOverlay = builder.get_object("toast_overlay")
        self.banner: Adw.Banner = builder.get_object("banner")

        self.content_stack: Gtk.Stack = builder.get_object("content_stack")
        self.refresh_page: Adw.StatusPage = builder.get_object("refresh_page")
        self.empty_search_page: Adw.StatusPage = builder.get_object("empty_search_page")
        self.bottom_bar: Gtk.ActionBar = builder.get_object("bottom_bar")

        super().set_child(self.toolbar_view)

        self.searchable = searchable
        self.refreshable = refreshable
        self.detachable = detachable

        self.detach_kwargs = {}
        self.refreshing = False
        self.refresh_thread: threading.Thread = None

        self.pref_page = PrefPage()
        self.content_stack.add_child(self.pref_page)
        # if refreshable: # TODO necessary?
        #     self.content_stack.set_visible_child(self.refresh_page)
        # else:
        self.content_stack.set_visible_child(self.pref_page)

    def _deferred_init(self):
        # get these properties, after the widget has been realized in the window
        self.nav_view = super().get_ancestor(Adw.NavigationView)
        self.ros2_connector = super().get_root().ros2_connector

        self.search_btn.set_visible(self.searchable)
        self.refresh_btn.set_visible(self.refreshable)
        self.detach_btn.set_visible(self.detachable)

    def on_realize(self, *args):
        # refresh the gui
        if self.refreshable:
            GLib.idle_add(self.refresh)

    def refresh(self):
        if not self.refreshable or self.refreshing:
            return

        # refresh started
        self.refreshing = True
        self.search_bar.set_search_mode(False)
        self.refresh_spinner.start()
        self.refresh_icon.set_visible(False)
        self.refresh_spinner.set_visible(True)

        def background_task(*args):
            # TODO add, that if the ros2_connector is not running, a toast is shown
            try:
                refresh_result = self.refresh_bg()
            except Exception as e:
                self.show_toast(f"Refresh failed! Error: {e}")
                refresh_result = False

            GLib.idle_add(finish_thread, refresh_result)

        def finish_thread(refresh_result: bool):
            if refresh_result:
                self.hide_banner()
                self.reset_ui()
                self.refresh_ui()
            else:
                self.show_banner("Refresh yielded no results")

            # finish refresh
            self.refresh_spinner.set_visible(False)
            self.refresh_icon.set_visible(True)
            self.refresh_spinner.stop()
            self.refreshing = False
            return False  # Ensure idle_add runs once

        # start the refresh thread
        self.refresh_thread = threading.Thread(target=background_task, daemon=True)
        self.refresh_thread.start()

    def refresh_bg(self) -> bool:
        """Child class should override this with blocking, long-running computation."""
        # raise NotImplementedError("Child class must implement refresh_bg()!")
        return True

    def refresh_ui(self, *args):
        """Child class should override this to update the UI with the result of the blocking refresh."""
        # raise NotImplementedError("Child class must implement refresh_ui()!")
        pass

    def reset_ui(self):
        """Child class should override this to reset the UI before a refresh."""
        # raise NotImplementedError("Child class must implement reset_ui()!")
        pass

    def toggle_search(self):
        if self.searchable:
            self.search_bar.set_search_mode(not self.search_bar.get_search_mode())
            # self.search_bar.set_search_mode(True)

    def on_search_changed(self, *args):
        if not self.searchable:
            return
        self.pref_page.apply_filter(self.search_entry.get_text())

    def detach(self, *args):
        if self.detachable:
            detached_window = DetachedWindow(
                application=self.get_root().app,
                nav_page_class=self.__class__,
                nav_page_kwargs=self.detach_kwargs,
            )
            detached_window.show()

    def show_toast(self, toast_text: str):
        self.toast_overlay.add_toast(Adw.Toast(title=str(toast_text)))

    def show_toast_w_btn(self, toast_text: str, btn_label: str, func: Callable, **func_kwargs):
        toast = Adw.Toast(title=str(toast_text), button_label=str(btn_label))
        toast.connect("button-clicked", lambda toast, *_: func(**func_kwargs))
        self.toast_overlay.add_toast(toast)

    def show_banner(self, banner_text: str):
        self.banner.set_title(str(banner_text))
        self.banner.set_button_label("")
        self.banner.set_revealed(True)

    def show_banner_w_btn(self, banner_text: str, btn_label: str, func: Callable, **func_kwargs):
        self.banner.set_title(str(banner_text))
        self.banner.set_button_label(str(btn_label))
        self.banner.set_revealed(True)

        # TODO this causes problems! this gets executed multiple times, and
        # if hasattr(self, "banner_signal_handler") and self.banner_signal_handler is not None:
        #     self.disconnect(self.banner_signal_handler)

        # self.banner_signal_handler = self.banner.connect("button-clicked", func, func_kwargs)
        # print(self.banner_signal_handler)

    def hide_banner(self):
        self.banner.set_revealed(False)

    def add_header_btn(self, icon_name: str, tooltip_text: str, func: Callable, **func_kwargs) -> Gtk.Button:
        btn = Gtk.Button.new_from_icon_name(icon_name)
        btn.set_tooltip_text(tooltip_text)
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_header_widget(btn)
        return btn

    def add_header_widget(self, widget: Gtk.Widget) -> Gtk.Widget:
        self.header_bar.pack_start(widget)
        return widget

    def add_bottom_left_btn(
        self, *, label: str = "", icon_name: str = "", tooltip_text: str = "", func: Callable, **func_kwargs
    ) -> Gtk.Button:
        btn = Gtk.Button(tooltip_text=tooltip_text)
        btn.set_child(Adw.ButtonContent(label=label, icon_name=icon_name))
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_bottom_widget(btn, position="start")
        return btn

    def add_bottom_right_btn(
        self, *, label: str = "", icon_name: str = "", tooltip_text: str = "", func: Callable, **func_kwargs
    ) -> Gtk.Button:
        btn = Gtk.Button(tooltip_text=tooltip_text)
        btn.set_child(Adw.ButtonContent(label=label, icon_name=icon_name))
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_bottom_widget(btn, position="end")
        return btn

    def add_bottom_widget(self, widget: Gtk.Widget, position: str = "start") -> Gtk.Widget:
        self.bottom_bar.set_revealed(True)
        if position == "start":
            self.bottom_bar.pack_start(widget)
        elif position == "center":
            self.bottom_bar.set_center_widget(widget)
        elif position == "end":
            self.bottom_bar.pack_end(widget)
        else:
            raise ValueError(f"Invalid position: {position}, must be one of 'start', 'center', 'end'")
        return widget

    def set_search_entry_placeholder_text(self, text: str):
        self.search_entry.set_placeholder_text(str(text))

    def set_empty_page_text(self, text: str):
        self.pref_page.set_empty_page_text(str(text))
