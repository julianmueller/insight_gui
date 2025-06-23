# =============================================================================
# pref_group.py
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

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from insight_gui.widgets.pref_rows import PrefRow


class PrefGroup(Adw.PreferencesGroup):
    __gtype_name__ = "PrefGroup"

    def __init__(
        self,
        *,
        title: str = "",
        description: str = "",
        empty_group_text: str = "empty list",
        filterable: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_description(str(description))

        self.box: Gtk.Box = super().get_first_child()
        self.title_box: Gtk.Box = self.box.get_first_child()
        self.suffix_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        super().set_header_suffix(self.suffix_box)

        self.rows_box: Gtk.Box = self.title_box.get_next_sibling()
        self.listbox: Gtk.ListBox = self.rows_box.get_first_child()

        # keep track of all rows
        self.rows: list[Adw.ActionRow] = []

        if not title and not description:
            self.title_box.set_visible(False)  # disable group header

        self.filterable = filterable
        self.empty_row = PrefRow(title=str(empty_group_text), sensitive=False)
        self.empty_row.add_prefix_icon("dialog-error-symbolic")
        super().add(self.empty_row)

        # Store initial visibility
        self._is_filtered = False
        self._visibility_before_filter = self.get_visible()

    @property
    def num_rows(self):
        return len(self.rows)

    @property
    def is_empty(self):
        return self.num_rows == 0

    @property
    def filter_text(self) -> str:
        return f"{self.get_title()} {self.get_description()}"

    # filters (hides) the row but remembers its original visibility
    def set_filtered(self, visible: bool) -> bool:
        if not self._is_filtered:
            self._visibility_before_filter = self.get_visible()

        if self._visibility_before_filter:
            self.set_visible(visible)

        self._is_filtered = True

    # restores original visibility before the filtering
    def set_unfiltered(self):
        if self._is_filtered:
            self.set_visible(self._visibility_before_filter)
            self._is_filtered = False

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_row' instead")

    def add_row(self, row: Gtk.Widget) -> Gtk.Widget:
        self.empty_row.set_visible(False)
        super().add(row)
        self.rows.append(row)
        return row

    def add_row_idle(self, row: Gtk.Widget):
        def _idle(row: Gtk.Widget):
            self.add_row(row)
            return False

        GLib.idle_add(_idle, row)
        return row

    def add_rows_idle(self, rows: list[Gtk.Widget], batch_size: int = 2):
        if len(rows) == 0:
            return

        index = 0

        def add_batch():
            nonlocal index
            end = min(index + batch_size, len(rows))

            for i in range(index, end):
                self.add_row(rows[i])

            index += batch_size
            return index < len(rows)  # Return True if more rows need to be added

        GLib.idle_add(add_batch)  # Start adding in batches

    def remove_row(self, row: Gtk.Widget):
        super().remove(row)
        self.rows = [_row for _row in self.rows if _row != row]

    def clear(self):
        rows_to_remove = reversed(self.rows)

        def _idle():
            for row in rows_to_remove:
                Adw.PreferencesGroup.remove(self, row)
            return False

        GLib.idle_add(_idle)
        self.rows = []
        self.empty_row.set_visible(True)

    def add_suffix_btn(
        self,
        *,
        icon_name: str,
        tooltip_text: str,
        func: Callable,
        func_kwargs: dict = {},
        **kwargs,
    ):
        btn = Gtk.Button(icon_name=icon_name, tooltip_text=tooltip_text, **kwargs)
        btn.connect("clicked", lambda *_: func(**func_kwargs))
        btn.add_css_class("flat")
        return self.add_suffix_widget(btn)

    def add_suffix_widget(self, widget: Gtk.Widget):
        self.suffix_box.append(widget)
        self.suffix_box.set_visible(True)
        return widget

    def set_description_to_row_count(self):
        super().set_description(f"Count: {self.num_rows}")

    def set_empty_group_text(self, text: str):
        self.empty_row.set_title(str(text))
