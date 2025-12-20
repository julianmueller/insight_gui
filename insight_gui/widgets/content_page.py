# =============================================================================
# content_page.py
#
# This file is part of https://github.com/julianmueller/insight_gui
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
# =============================================================================

import concurrent.futures
import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gio

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.breadcrumbs import BreadcrumbsBar
from insight_gui.exceptions import RefreshCancelled


class ContentPage(Adw.NavigationPage):
    __gtype_name__ = "ContentPage"

    def __init__(
        self,
        searchable: bool = True,
        refreshable: bool = True,
        detachable: bool = True,
        auto_refresh_on_realize: bool = True,
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

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(self.app.share_dir / "content_page.ui"))

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
        self.main_content_page: Adw.Bin = builder.get_object("main_content_page")
        self.refresh_page: Adw.StatusPage = builder.get_object("refresh_page")
        self.empty_search_page: Adw.StatusPage = builder.get_object("empty_search_page")
        self.empty_search_clear_btn: Gtk.Button = builder.get_object("empty_search_clear_btn")
        self.empty_search_clear_btn.connect("clicked", self.on_clear_search_clicked)
        self.bottom_bar: Gtk.ActionBar = builder.get_object("bottom_bar")

        super().set_child(self.toolbar_view)

        self.searchable = searchable
        self.search_btn.set_visible(self.searchable)
        self.refreshable = refreshable
        self.refresh_btn.set_visible(self.refreshable)
        self.detachable = detachable
        self.detach_btn.set_visible(self.detachable)
        self.auto_refresh_on_realize = auto_refresh_on_realize

        # tags and search_text for filtering
        self.filter_tags: set[str] = set()
        self.search_text: str = ""
        self._latest_refresh_successful = True
        self._refresh_cancelled_by_user = False

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
        self.refresh_fail_text = "Refresh yielded no results"
        self._active_refresh_token: object | None = None
        self._refresh_cancel_event: threading.Event = threading.Event()
        self._refresh_future: concurrent.futures.Future | None = None

        self.pref_page = PrefPage()
        self.pref_page.connect("group-filtered", self._on_groups_filtered_changed)
        self.pref_page.connect("group-unfiltered", self._on_groups_unfiltered_changed)

        # this is here, because some contentpages do not have a pref_page (eg canvas-based pages)
        self.main_content_page.set_child(self.pref_page)
        self.content_stack.set_visible_child(self.main_content_page)

    def on_realize(self, *args):
        self.is_realized = True
        self.nav_view: Adw.NavigationView = super().get_ancestor(Adw.NavigationView)

        if self.app.settings.get_boolean("show-breadcrumbs-bar"):
            self.breadcrumbs_bar.set_nav_view(self.nav_view)
            self.breadcrumbs_bar.update()
            self.nav_view.connect("pushed", self.update_breadcrumbs)
            self.nav_view.connect("popped", self.update_breadcrumbs)

        # refresh the gui if allowed
        if self.auto_refresh_on_realize:
            self.refresh()

    def on_unrealize(self, *args):
        self.is_realized = False
        self.deprioritize_refresh()

    def on_map(self, *args):
        self.is_mapped = True

    def on_unmap(self, *args):
        self.is_mapped = False
        self.deprioritize_refresh()

    def cancel_refresh(self):
        """Request cancellation of the current refresh, if any, and reset UI state."""
        if self.refreshing:
            self._end_refresh_ui()
        if self._refresh_future:
            self._refresh_future.cancel()
        self._refresh_cancelled_by_user = True
        self._refresh_cancel_event.set()
        self._active_refresh_token = None

    def deprioritize_refresh(self):
        """Lower priority of the current refresh so newer pages can run first."""
        self._refresh_cancel_event.set()
        if self._refresh_future:
            self.app.reprioritize_worker_future(self._refresh_future, priority=self.app.WORKER_PRIORITY_LOW)

    def is_refresh_cancelled(self, *, cancel_event: threading.Event | None = None) -> bool:
        event = cancel_event or getattr(self, "_refresh_cancel_event", None)
        return bool(event and event.is_set())

    def wait_for_refresh_cancel(
        self, timeout: float | None = None, *, cancel_event: threading.Event | None = None
    ) -> bool:
        """Block up to ``timeout`` seconds, returning True if cancellation is requested."""
        event = cancel_event or getattr(self, "_refresh_cancel_event", None)
        if event is None:
            return False
        return event.wait(timeout)

    # TODO maybe change the whole refresh thing, so that there is only one refresh method, which always happens in the
    # bg and every update on the ui is performed with 'idle_add'. with this, the refresh is progressive and not all at
    # once, which might again freeze the ui, when many many ui changes all need to happen at once
    def refresh(self):
        if self.refreshing:
            return

        cancel_event = threading.Event()
        refresh_token = object()
        self._refresh_cancel_event = cancel_event
        self._active_refresh_token = refresh_token
        self._refresh_cancelled_by_user = False
        self._start_refresh_ui()
        self._latest_refresh_successful = True

        def _finish(
            payload: object, error: Exception | None = None, *, refresh_token=refresh_token, cancel_event=cancel_event
        ):
            if refresh_token is not self._active_refresh_token:
                return GLib.SOURCE_REMOVE
            if cancel_event.is_set() and (self._refresh_cancelled_by_user or not self.is_mapped):
                self._end_refresh_ui()
                return GLib.SOURCE_REMOVE
            # retry later if not yet realized
            if not self.is_realized:
                GLib.timeout_add(100, _finish, payload, error)
                return GLib.SOURCE_REMOVE

            try:
                if error:
                    self.show_toast(f"Refresh failed! Error: {error}")
                    self.ros2_connector.log(f"Refresh failed! Error: {error}", level="error")
                    self._latest_refresh_successful = False
                    payload = None

                # Treat explicit False as a failure signal; everything else counts as success
                if payload is False:
                    self.show_banner(self.refresh_fail_text)
                    self._latest_refresh_successful = False
                    return GLib.SOURCE_REMOVE

                self.hide_banner()
                try:
                    self.reset_ui()
                    self.refresh_ui()
                except Exception as ui_exc:
                    self.show_toast(f"Refresh UI failed! Error: {ui_exc}")
                    self.ros2_connector.log(f"Refresh UI failed! Error: {ui_exc}", level="error")
                    self.show_banner(self.refresh_fail_text)
                    self._latest_refresh_successful = False
                    raise ui_exc  # reraise it

            finally:
                # Update the stack to show the relevant status/content page
                GLib.idle_add(self.update_visible_content_stack_page)
                self._end_refresh_ui()

            return GLib.SOURCE_REMOVE

        def _handle_cancelled(*args, refresh_token=refresh_token, cancel_event=cancel_event):
            if refresh_token is not self._active_refresh_token:
                return GLib.SOURCE_REMOVE
            self._refresh_cancelled_by_user = True
            cancel_event.set()
            self._end_refresh_ui()
            return GLib.SOURCE_REMOVE

        def _on_done(fut):
            try:
                result = fut.result()
                error = None
            except RefreshCancelled:
                GLib.idle_add(_handle_cancelled)
                return
            except concurrent.futures.CancelledError:
                GLib.idle_add(_handle_cancelled)
                return
            except Exception as exc:
                result = None
                error = exc
            GLib.idle_add(_finish, result, error)

        try:
            self._refresh_future = self.app.run_in_worker(
                self.refresh_bg, done_callback=_on_done, priority=self.app.WORKER_PRIORITY_HIGH
            )
        except Exception as exc:
            GLib.idle_add(_finish, None, exc)

    def _start_refresh_ui(self):
        self.refreshing = True
        self.search_bar.set_search_mode(False)
        self.refresh_spinner.set_visible(True)
        self.refresh_btn.set_can_target(False)
        self.refresh_icon.set_visible(False)
        self.content_stack.set_sensitive(False)
        self.refresh_spinner.start()

    def _end_refresh_ui(self):
        self.refresh_spinner.stop()
        self.content_stack.set_sensitive(True)
        self.refresh_icon.set_visible(True)
        self.refresh_btn.set_can_target(True)
        self.refresh_spinner.set_visible(False)
        self.refreshing = False

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

    # TODO rename everywhere into "trigger_primary_action"
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
        self.apply_filters()

    def on_clear_search_clicked(self, *args):
        """Clear the search entry and reset filters when empty-search page button is pressed."""
        if not self.searchable:
            return
        self.search_entry.set_text("")
        self.search_text = ""
        self.search_bar.set_search_mode(False)
        self.apply_filters()

    def apply_filters(self):
        """Apply current search_text and filter_tags to the pref_page."""
        self.pref_page.apply_filters(filter_str=self.search_text, filter_tags=self.filter_tags)

    def _on_groups_filtered_changed(self, *args):
        self.update_visible_content_stack_page()

    def _on_groups_unfiltered_changed(self, *args):
        self.update_visible_content_stack_page()

    def update_visible_content_stack_page(self):
        """Central place to decide which child the stack should show based on content/search."""
        if not self._latest_refresh_successful:
            self.content_stack.set_visible_child(self.refresh_page)
            return

        # check if pref_page exists and if filtering is applied
        if self.searchable and getattr(self, "pref_page", None):
            search_active = bool(self.search_text.strip() or self.filter_tags)
            visible_rows_after_search = self.pref_page.get_visible_row_count()

            if search_active and visible_rows_after_search == 0:
                self.content_stack.set_visible_child(self.empty_search_page)
                return

        self.content_stack.set_visible_child(self.main_content_page)

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

    def set_placeholder_text(self, text: str):
        self.pref_page.set_placeholder_text(str(text))

    def set_refresh_fail_text(self, text: str):
        self.refresh_fail_text = str(text)
