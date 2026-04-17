# =============================================================================
# custom_stack_sidebar.py
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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GObject, Adw, Gdk, Gio

from insight_gui.pages import Page
from insight_gui.widgets.pref_rows import PrefRow


class StackSidebar(Adw.PreferencesPage):
    __gtype_name__ = "StackSidebar"

    stack = GObject.Property(type=Gtk.Stack, default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.groups = []
        self._pages_by_id: dict[str, Page] = {}
        self._spinners_by_id: dict[str, Gtk.Spinner] = {}

    def set_stack(self, stack: Gtk.Stack):
        self.stack = stack

    def update_from_page_groups(self, page_groups: list):
        # Create sidebar groups and pages from the pages structure
        for page_group in page_groups:
            group = self.add_group(title=page_group.title)
            for page in page_group.pages:
                self.add_page_row(
                    group=group,
                    page=page,
                )

    def add_group(self, title: str = "", description: str = ""):
        group = Adw.PreferencesGroup(title=title, description=description)
        self.groups.append(group)
        super().add(group)
        return group

    def add_page_row(
        self,
        group: Adw.PreferencesGroup,
        page: Page,
    ):
        """Add a row to a specific group."""
        if group not in self.groups:
            raise ValueError(f"Group '{group.get_title()}' does not exist.")

        if not self.stack:
            return

        self._pages_by_id[page.page_id] = page

        def _on_pressed(controller: Gtk.GestureClick, n_press: int, x: float, y: float):
            state = controller.get_current_event_state()

            if state & Gdk.ModifierType.CONTROL_MASK:
                self.open_detached_page(page.page_id)
            else:
                nav_view = self.ensure_page(page.page_id)
                self.stack.set_visible_child(nav_view)

        row = PrefRow(activatable=True, title=page.title, subtitle=page.subtitle)
        row.add_prefix(Gtk.Image(icon_name=page.icon_name))
        loading_spinner = Gtk.Spinner(visible=False, tooltip_text="Page is refreshing")
        row.add_suffix(loading_spinner)
        self._spinners_by_id[page.page_id] = loading_spinner

        gesture = Gtk.GestureClick()
        gesture.connect("pressed", _on_pressed)
        row.add_controller(gesture)

        group.add(row)

    def ensure_page(self, page_id: str) -> Adw.NavigationView | None:
        if not self.stack:
            return None

        nav_view = self.stack.get_child_by_name(page_id)
        if nav_view:
            return nav_view

        page = self._pages_by_id.get(page_id)
        if page is None:
            return None

        try:
            nav_page = page.create_nav_page()
        except Exception as exc:
            nav_page = self._create_error_page(page, exc)
        self._connect_refresh_spinner(page_id, nav_page)

        nav_view = Adw.NavigationView()
        nav_view.add(nav_page)
        self.stack.add_titled(child=nav_view, name=page.page_id, title=page.title)
        return nav_view

    def open_detached_page(self, page_id: str):
        page = self._pages_by_id.get(page_id)
        if page is None:
            return

        from insight_gui.window import DetachedWindow

        app = Gio.Application.get_default()
        try:
            nav_page_class = page.nav_page_class
        except Exception as exc:
            detached_window = Adw.ApplicationWindow(application=app, title=page.title)
            detached_window.set_default_size(400, 500)
            detached_window.set_content(self._create_error_status_page(page, exc))
            app.detached_windows.append(detached_window)
            detached_window.show()
            return

        try:
            detached_window = DetachedWindow(app=app, nav_page_class=nav_page_class, nav_page_kwargs={})
        except Exception as exc:
            detached_window = Adw.ApplicationWindow(application=app, title=page.title)
            detached_window.set_default_size(400, 500)
            detached_window.set_content(self._create_error_status_page(page, exc))
        app.detached_windows.append(detached_window)
        detached_window.show()

    def _create_error_page(self, page: Page, error: Exception) -> Adw.NavigationPage:
        app = Gio.Application.get_default()
        connector = getattr(app, "ros2_connector", None)
        if connector:
            connector.log(f"Failed to load page '{page.page_id}': {error}", level="error")

        nav_page = Adw.NavigationPage(title=page.title)
        nav_page.set_child(self._create_error_status_page(page, error))
        return nav_page

    def _create_error_status_page(self, page: Page, error: Exception) -> Adw.StatusPage:
        return Adw.StatusPage(
            title=f"{page.title} Failed to Load",
            description=str(error),
            icon_name="dialog-error-symbolic",
        )

    def _connect_refresh_spinner(self, page_id: str, nav_page: Adw.NavigationPage):
        loading_spinner = self._spinners_by_id.get(page_id)
        if loading_spinner is None:
            return

        def _on_refresh_started(*args):
            loading_spinner.set_visible(True)
            loading_spinner.start()

        def _on_refresh_finished(*args):
            loading_spinner.stop()
            loading_spinner.set_visible(False)

        try:
            nav_page.connect("refresh-started", _on_refresh_started)
            nav_page.connect("refresh-finished", _on_refresh_finished)
        except TypeError:
            pass

    def clear_all(self):
        """Clear all groups and rows."""
        # Remove all groups from the page
        for group in self._groups.values():
            self.remove(group)

        self._groups.clear()
        self._rows.clear()
        self._group_order.clear()
