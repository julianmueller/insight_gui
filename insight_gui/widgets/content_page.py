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

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.breadcrumbs import BreadcrumbsBar


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
        super().connect("unrealize", self.on_unrealize)
        super().connect("map", self.on_map)
        super().connect("unmap", self.on_unmap)

        self.app = Gio.Application.get_default()
        self.ros2_connector: ROS2Connector = self.app.ros2_connector

        self.is_mapped = False
        self.is_realized = False

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
        self.refresh_spinner: Gtk.Spinner = builder.get_object("refresh_spinner")  # replace with Adw.Spinner

        self.detach_btn: Gtk.Button = builder.get_object("detach_btn")
        # self.detach_btn.connect("clicked", self.on_detach)
        self.detach_btn.set_action_name("win.detach")

        self.search_bar: Gtk.SearchBar = builder.get_object("search_bar")
        self.search_btn.bind_property(
            "active", self.search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL
        )
        self.search_entry: Gtk.SearchEntry = builder.get_object("search_entry")
        self.search_entry.connect("search-changed", self.on_search_changed)

        if self.app.settings.get_boolean("show-breadcrumbs-bar"):
            self.breadcrumbs_bar = BreadcrumbsBar()
            self.toolbar_view.add_top_bar(self.breadcrumbs_bar)

        self.toast_overlay: Adw.ToastOverlay = builder.get_object("toast_overlay")
        self.banner: Adw.Banner = builder.get_object("banner")

        self.content_stack: Gtk.Stack = builder.get_object("content_stack")
        self.refresh_page: Adw.StatusPage = builder.get_object("refresh_page")
        self.empty_search_page: Adw.StatusPage = builder.get_object("empty_search_page")
        self.bottom_bar: Gtk.ActionBar = builder.get_object("bottom_bar")

        super().set_child(self.toolbar_view)

        self.searchable = searchable
        self.search_btn.set_visible(self.searchable)
        self.refreshable = refreshable
        self.refresh_btn.set_visible(self.refreshable)
        self.detachable = detachable
        self.detach_btn.set_visible(self.detachable)

        # tags and search_text for filtering
        self.filter_tags: set[str] = set()
        self.search_text: str = ""

        if self.detachable:
            self.detach_kwargs: dict = {}

            # TODO look into this
            # import inspect

            # frame = inspect.currentframe()
            # args, varargs, varkw, _locals = inspect.getargvalues(frame)

            # for arg in args:
            #     if arg == "self":
            #         continue

            #     self.detach_kwargs[arg] = _locals[arg]

        self.refreshing = False
        self.refresh_thread: threading.Thread = None
        self.refresh_fail_text = "Refresh yielded no results"

        self.pref_page = PrefPage()
        self.content_stack.add_child(self.pref_page)
        self.content_stack.set_visible_child(self.pref_page)

    def on_realize(self, *args):
        self.is_realized = True
        self.nav_view: Adw.NavigationView = super().get_ancestor(Adw.NavigationView)

        if self.app.settings.get_boolean("show-breadcrumbs-bar"):
            self.breadcrumbs_bar.set_nav_view(self.nav_view)
            self.breadcrumbs_bar.update()
            self.nav_view.connect("pushed", self.update_breadcrumbs)
            self.nav_view.connect("popped", self.update_breadcrumbs)

        # refresh the gui
        GLib.idle_add(self.refresh)

    def on_unrealize(self, *args):
        self.is_realized = False

    def on_map(self, *args):
        self.is_mapped = True

    def on_unmap(self, *args):
        self.is_mapped = False

    def refresh(self):
        if self.refreshing:
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
            if not self.is_realized:
                # Delay execution until realized
                GLib.timeout_add(100, finish_thread, refresh_result)
                return False  # Stop idle_add, let timeout_add retry

            if refresh_result:
                self.hide_banner()
                self.reset_ui()
                self.refresh_ui()
            else:
                self.show_banner(self.refresh_fail_text)

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

    def trigger(self):
        """Child class should override this to trigger some primary action of the page."""
        pass

    def add_conditional_filter_tag(self, filter_tag: str, condition: bool):
        """Add or remove a filter_tag from the filter_tags list based on the condition."""
        if condition:
            self.filter_tags.add(filter_tag)
        else:
            self.filter_tags.discard(filter_tag)

    def on_search_changed(self, *args):
        if not self.searchable:
            return
        self.search_text = self.search_entry.get_text()
        self.reapply_filters()

    def reapply_filters(self):
        self.pref_page.apply_filters(search_str=self.search_text, search_tags=self.filter_tags)

    def detach(self, *args):
        from insight_gui.window import DetachedWindow

        if self.detachable:
            detached_window = DetachedWindow(
                app=self.app,
                nav_page_class=self.__class__,
                nav_page_kwargs=self.detach_kwargs,
            )
            self.app.detached_windows.append(detached_window)
            detached_window.show()

    def show_toast(self, title: str, *, priority: Adw.ToastPriority = Adw.ToastPriority.NORMAL, timeout: int = 2):
        """Show a toast message"""
        self.toast_overlay.add_toast(Adw.Toast(title=title, priority=priority, timeout=timeout))

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

    def update_breadcrumbs(self, *args):
        if self.nav_view.get_visible_page() == self:
            self.breadcrumbs_bar.update()

    def add_header_btn(
        self, icon_name: str, tooltip_text: str, func: Callable, func_kwargs: dict = {}, **kwargs
    ) -> Gtk.Button:
        btn = Gtk.Button(icon_name=icon_name, **kwargs)
        btn.set_tooltip_text(tooltip_text)
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_header_widget(btn)
        return btn

    def add_header_widget(self, widget: Gtk.Widget) -> Gtk.Widget:
        self.header_bar.pack_start(widget)
        return widget

    def add_bottom_left_btn(
        self,
        *,
        label: str = "",
        icon_name: str = "",
        tooltip_text: str = "",
        func: Callable,
        func_kwargs: dict = {},
        **kwargs,
    ) -> Gtk.Button:
        btn = Gtk.Button(tooltip_text=tooltip_text, **kwargs)
        btn.set_child(Adw.ButtonContent(label=label, icon_name=icon_name))
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_bottom_widget(btn, position="start")
        return btn

    def add_bottom_right_btn(
        self,
        *,
        label: str = "",
        icon_name: str = "",
        tooltip_text: str = "",
        func: Callable,
        func_kwargs: dict = {},
        **kwargs,
    ) -> Gtk.Button:
        btn = Gtk.Button(tooltip_text=tooltip_text, **kwargs)
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

    def set_refresh_fail_text(self, text: str):
        self.refresh_fail_text = str(text)
