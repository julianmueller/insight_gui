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

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GObject, Adw, Gdk

from insight_gui.widgets.pref_rows import PrefRow


class StackSidebar(Adw.PreferencesPage):
    __gtype_name__ = "StackSidebar"

    stack = GObject.Property(type=Gtk.Stack, default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.groups = []

    def set_stack(self, stack: Gtk.Stack):
        self.stack = stack

    def update_from_page_groups(self, page_groups: list):
        # Create sidebar groups and pages from the pages structure
        for page_group in page_groups:
            group = self.add_group(title=page_group.title)
            for page in page_group.pages:
                self.add_page_row(
                    group=group,
                    title=page.title,
                    page_name=page.page_id,
                    nav_page=page.nav_page_class(),
                    prefix_icon=page.icon_name,
                    subtitle=page.subtitle,
                )

    def add_group(self, title: str = "", description: str = ""):
        group = Adw.PreferencesGroup(title=title, description=description)
        self.groups.append(group)
        super().add(group)
        return group

    def add_page_row(
        self,
        group: Adw.PreferencesGroup,
        title: str,
        page_name: str,
        nav_page: Adw.NavigationPage,
        prefix_icon: Optional[str] = None,
        subtitle: Optional[str] = None,
    ):
        """Add a row to a specific group."""
        if group not in self.groups:
            raise ValueError(f"Group '{group.get_title()}' does not exist.")

        if not self.stack:
            return

        def _on_pressed(controller: Gtk.GestureClick, n_press: int, x: float, y: float):
            state = controller.get_current_event_state()

            # add CTRL+click functionality to open in detached window
            if state & Gdk.ModifierType.CONTROL_MASK:
                nav_page.detach()

            # regular click
            else:
                nav_view = self.stack.get_child_by_name(page_name)
                self.stack.set_visible_child(nav_view)

        nav_view = Adw.NavigationView()
        nav_view.add(nav_page)
        self.stack.add_titled(child=nav_view, name=page_name, title=title)

        row = PrefRow(activatable=True, title=title, subtitle=subtitle)
        row.add_prefix(Gtk.Image(icon_name=prefix_icon)) if prefix_icon else None

        gesture = Gtk.GestureClick()
        gesture.connect("pressed", _on_pressed)
        row.add_controller(gesture)

        group.add(row)

    def clear_all(self):
        """Clear all groups and rows."""
        # Remove all groups from the page
        for group in self._groups.values():
            self.remove(group)

        self._groups.clear()
        self._rows.clear()
        self._group_order.clear()
