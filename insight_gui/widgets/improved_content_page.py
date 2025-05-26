# =============================================================================
# improved_content_page.py
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

from pathlib import Path
from typing import Callable, Any, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.breadcrumbs import BreadcrumbsBar
from insight_gui.utils.async_task_manager import task_manager, ui_batcher


class ImprovedContentPage(Adw.NavigationPage):
    """
    Improved content page with better async handling and UI updates.

    This class provides a cleaner interface for handling background tasks
    and UI updates, reducing the complexity of GLib.idle_add usage.
    """

    __gtype_name__ = "ImprovedContentPage"

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
        GLib.idle_add(self._deferred_init)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).parent / "content_page.ui"))

        self.toolbar_view: Adw.ToolbarView = builder.get_object("toolbar_view")
        self.header_bar: Adw.HeaderBar = builder.get_object("header_bar")

        self.search_btn: Gtk.ToggleButton = builder.get_object("search_btn")
        self.search_btn.set_action_name("win.toggle-search")
        self.search_btn.set_sensitive(True)

        self.refresh_btn: Gtk.Button = builder.get_object("refresh_btn")
        self.refresh_btn.set_action_name("win.refresh")
        self.refresh_icon: Gtk.Image = builder.get_object("refresh_icon")
        self.refresh_spinner: Gtk.Spinner = builder.get_object("refresh_spinner")

        self.detach_btn: Gtk.Button = builder.get_object("detach_btn")
        self.detach_btn.set_action_name("win.detach")

        self.search_bar: Gtk.SearchBar = builder.get_object("search_bar")
        self.search_btn.bind_property(
            "active", self.search_bar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL
        )
        self.search_entry: Gtk.SearchEntry = builder.get_object("search_entry")
        self.search_entry.connect("search-changed", self.on_search_changed)

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
        self.refreshable = refreshable
        self.detachable = detachable

        # tags and search_text for filtering
        self.filter_tags: set[str] = set()
        self.search_text: str = ""

        self.detach_kwargs = {}
        self.refresh_fail_text = "Refresh yielded no results"

        self.pref_page = PrefPage()
        self.content_stack.add_child(self.pref_page)
        self.content_stack.set_visible_child(self.pref_page)

        # Task management
        self._refresh_task_id = f"{self.__class__.__name__}_refresh"
        self._is_refreshing = False

    def _deferred_init(self):
        """Initialize properties after widget is realized."""
        self.window = super().get_root()
        self.nav_view: Adw.NavigationView = super().get_ancestor(Adw.NavigationView)
        self.ros2_connector: ROS2Connector = self.window.ros2_connector

        self.breadcrumbs_bar.set_nav_view(self.nav_view)
        self.breadcrumbs_bar.update()
        self.nav_view.connect("pushed", self.update_breadcrumbs)
        self.nav_view.connect("popped", self.update_breadcrumbs)

        self.search_btn.set_visible(self.searchable)
        self.refresh_btn.set_visible(self.refreshable)
        self.detach_btn.set_visible(self.detachable)

    def on_realize(self, *args):
        """Called when page is realized."""
        GLib.idle_add(self.refresh)

    def on_unrealize(self, *args):
        """Called when page is unrealized."""
        self.cancel_refresh()

    def on_map(self, *args):
        """Called when page is mapped."""
        self.page_is_mapped = True

    def on_unmap(self, *args):
        """Called when page is unmapped."""
        self.page_is_mapped = False
        self.cancel_refresh()

    # Async Task Methods
    def run_background_task(
        self,
        task_id: str,
        background_func: Callable,
        success_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> str:
        """
        Run a background task with proper UI callback handling.

        Args:
            task_id: Unique identifier for the task
            background_func: Function to run in background thread
            success_callback: Called on main thread when task succeeds
            error_callback: Called on main thread when task fails
            *args, **kwargs: Arguments passed to background_func

        Returns:
            task_id for tracking the task
        """
        return task_manager.run_task(
            task_id=task_id,
            background_func=background_func,
            success_callback=success_callback,
            error_callback=error_callback,
            *args,
            **kwargs,
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running background task."""
        return task_manager.cancel_task(task_id)

    def schedule_ui_update(self, update_id: str, update_func: Callable, *args, **kwargs):
        """
        Schedule a UI update with automatic batching for high-frequency updates.

        Args:
            update_id: Unique identifier for this type of update
            update_func: Function to call for the update
            *args, **kwargs: Arguments for update_func
        """
        ui_batcher.schedule_update(update_id, update_func, *args, **kwargs)

    # Refresh Methods
    def refresh(self):
        """Start the refresh process."""
        if self._is_refreshing:
            return

        self._is_refreshing = True
        self.search_bar.set_search_mode(False)
        self._start_refresh_ui()

        def on_refresh_success(result):
            self._finish_refresh_ui(success=True)
            if result:
                self.hide_banner()
                self.reset_ui()
                self.refresh_ui()
            else:
                self.show_banner(self.refresh_fail_text)

        def on_refresh_error(error):
            self._finish_refresh_ui(success=False)
            self.show_toast(f"Refresh failed! Error: {error}")

        self.run_background_task(
            task_id=self._refresh_task_id,
            background_func=self.refresh_bg,
            success_callback=on_refresh_success,
            error_callback=on_refresh_error,
        )

    def cancel_refresh(self):
        """Cancel the current refresh operation."""
        if self._is_refreshing:
            self.cancel_task(self._refresh_task_id)
            self._finish_refresh_ui(success=False)

    def _start_refresh_ui(self):
        """Update UI to show refresh is starting."""
        self.refresh_spinner.start()
        self.refresh_icon.set_visible(False)
        self.refresh_spinner.set_visible(True)

    def _finish_refresh_ui(self, success: bool):
        """Update UI to show refresh is finished."""
        self.refresh_spinner.set_visible(False)
        self.refresh_icon.set_visible(True)
        self.refresh_spinner.stop()
        self._is_refreshing = False

    # Abstract methods for subclasses
    def refresh_bg(self) -> bool:
        """
        Override this method with blocking, long-running computation.

        Returns:
            True if refresh was successful, False otherwise
        """
        return True

    def refresh_ui(self, *args):
        """Override this method to update the UI with refresh results."""
        pass

    def reset_ui(self):
        """Override this method to reset the UI before a refresh."""
        pass

    # UI Helper Methods
    def toggle_search(self):
        """Toggle search mode."""
        if self.searchable:
            self.search_bar.set_search_mode(not self.search_bar.get_search_mode())

    def trigger(self):
        """Override this method to trigger the primary action of the page."""
        pass

    def add_conditional_filter_tag(self, filter_tag: str, condition: bool):
        """Add or remove a filter_tag based on condition."""
        if condition:
            self.filter_tags.add(filter_tag)
        else:
            self.filter_tags.discard(filter_tag)

    def on_search_changed(self, *args):
        """Handle search text changes."""
        if not self.searchable:
            return
        self.search_text = self.search_entry.get_text()
        self.reapply_filters()

    def reapply_filters(self):
        """Reapply current filters to the page."""
        self.pref_page.apply_filters(search_str=self.search_text, search_tags=self.filter_tags)

    def detach(self, *args):
        """Detach this page to a new window."""
        from insight_gui.window import DetachedWindow

        if self.detachable:
            application: Adw.Application = self.get_ancestor(Adw.ApplicationWindow).app
            detached_window = DetachedWindow(
                application=application,
                nav_page_class=self.__class__,
                nav_page_kwargs=self.detach_kwargs,
            )
            application.detached_windows.append(detached_window)
            detached_window.show()

    # Toast and Banner Methods
    def show_toast(self, toast_text: str):
        """Show a toast notification."""
        self.toast_overlay.add_toast(Adw.Toast(title=str(toast_text)))

    def show_toast_w_btn(self, toast_text: str, btn_label: str, func: Callable, **func_kwargs):
        """Show a toast with an action button."""
        toast = Adw.Toast(title=str(toast_text), button_label=str(btn_label))
        toast.connect("button-clicked", lambda toast, *_: func(**func_kwargs))
        self.toast_overlay.add_toast(toast)

    def show_banner(self, banner_text: str):
        """Show a banner message."""
        self.banner.set_title(str(banner_text))
        self.banner.set_button_label("")
        self.banner.set_revealed(True)

    def show_banner_w_btn(self, banner_text: str, btn_label: str, func: Callable, **func_kwargs):
        """Show a banner with an action button."""
        self.banner.set_title(str(banner_text))
        self.banner.set_button_label(str(btn_label))
        self.banner.set_revealed(True)

    def hide_banner(self):
        """Hide the banner."""
        self.banner.set_revealed(False)

    def update_breadcrumbs(self, *args):
        """Update breadcrumbs navigation."""
        if self.nav_view.get_visible_page() == self:
            self.breadcrumbs_bar.update()

    # Widget Helper Methods
    def add_header_btn(
        self, icon_name: str, tooltip_text: str, func: Callable, func_kwargs: dict = {}, **kwargs
    ) -> Gtk.Button:
        """Add a button to the header bar."""
        btn = Gtk.Button(icon_name=icon_name, **kwargs)
        btn.set_tooltip_text(tooltip_text)
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_header_widget(btn)
        return btn

    def add_header_widget(self, widget: Gtk.Widget) -> Gtk.Widget:
        """Add a widget to the header bar."""
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
        """Add a button to the bottom left of the page."""
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
        """Add a button to the bottom right of the page."""
        btn = Gtk.Button(tooltip_text=tooltip_text, **kwargs)
        btn.set_child(Adw.ButtonContent(label=label, icon_name=icon_name))
        btn.connect_data("clicked", lambda *_: func(**func_kwargs))
        self.add_bottom_widget(btn, position="end")
        return btn

    def add_bottom_widget(self, widget: Gtk.Widget, position: str = "start") -> Gtk.Widget:
        """Add a widget to the bottom bar."""
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

    # Configuration Methods
    def set_search_entry_placeholder_text(self, text: str):
        """Set placeholder text for search entry."""
        self.search_entry.set_placeholder_text(str(text))

    def set_empty_page_text(self, text: str):
        """Set text for empty page state."""
        self.pref_page.set_empty_page_text(str(text))

    def set_refresh_fail_text(self, text: str):
        """Set text shown when refresh fails."""
        self.refresh_fail_text = str(text)
