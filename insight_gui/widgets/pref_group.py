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
import asyncio
import re
from difflib import SequenceMatcher

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw, GLib, Gio

from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.filtering_interface import FilteringInterface


class PrefGroup(Adw.PreferencesGroup, FilteringInterface):
    """Custom wrapper class around Adw.PreferencesGroup to manage preference rows."""

    __gtype_name__ = "PrefGroup"
    __gsignals__ = {
        # filtered signal emits a boolean indicating whether the row "survived" the filtering (filtered-in/filtered-out)
        "filtered": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        # unfiltered signal emits when the filtering is cleared
        "unfiltered": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "row-filtered": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN)),
        "row-unfiltered": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    }

    rows = GObject.Property(type=Gio.ListStore)
    placeholder_row = GObject.Property(type=PrefRow)

    def __init__(
        self,
        *,
        title: str = "",
        description: str = "",
        placeholder_text: str = "group is empty",
        filterable: bool = True,
        **kwargs,
    ):
        Adw.PreferencesGroup.__init__(self, **kwargs)
        FilteringInterface.__init__(self, filterable=filterable)

        super().set_title(str(title))
        super().set_description(str(description))
        self.set_filterable(filterable)
        self.set_filter_str(f"{self.get_title()} {self.get_description()}".lower())

        self.box: Gtk.Box = super().get_first_child()
        self.title_box: Gtk.Box = self.box.get_first_child()
        self.suffix_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        super().set_header_suffix(self.suffix_box)

        self.rows_box: Gtk.Box = self.title_box.get_next_sibling()
        self.listbox: Gtk.ListBox = self.rows_box.get_first_child()

        # keep track of all rows (use a Gio.ListStore instead of a python list)
        self.rows: Gio.ListStore = Gio.ListStore.new(Gtk.Widget)
        self.rows.connect("items-changed", self._on_rows_changed)

        if not title and not description:
            self.title_box.set_visible(False)  # disable group header

        self.placeholder_row = PrefRow(title=placeholder_text, sensitive=False)
        self.placeholder_row.add_prefix_icon("dialog-error-symbolic")
        self.set_placeholder_text(placeholder_text)
        self.bind_property("is-empty", self.placeholder_row, "visible", GObject.BindingFlags.SYNC_CREATE)
        super().add(self.placeholder_row)
        # self.listbox.set_placeholder(self.placeholder_row)

        # Filtering model driven by Gtk instead of manual visibility toggles
        # self.row_filter = Gtk.CustomFilter.new(self._custom_row_filter_func)
        # self.filtered_rows = Gtk.FilterListModel(model=self.rows, filter=self.row_filter)
        # self.filtered_rows.connect("items-changed", self._on_filtered_items_changed)

        # self.listbox.bind_model(self.filtered_rows, lambda row: row)

    @GObject.Property(type=int, default=0)
    def num_rows(self):
        # return the number of items in the ListStore
        return self.rows.get_n_items()

    @GObject.Property(type=bool, default=True)
    def is_empty(self):
        return self.num_rows == 0

    @GObject.Property(type=str, default="group is empty")
    def placeholder_text(self) -> str:
        return self.placeholder_row.get_title()

    @placeholder_text.setter
    def placeholder_text(self, value) -> str:
        return self.placeholder_row.set_title(value)

    def set_placeholder_text(self, text: str) -> None:
        self.placeholder_text = text

    def _on_rows_changed(self, *args):
        self.notify("num-rows")
        self.notify("is-empty")

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_row' instead")

    def _append_row(self, row: Gtk.Widget):
        """Internal method to append a row immediately. Might be blocking!"""
        super(PrefGroup, self).add(row)
        self.rows.append(row)

        if isinstance(row, FilteringInterface) and row.filterable:
            row.connect("filtered", self._on_row_filtered)
            row.connect("unfiltered", self._on_row_unfiltered)

    def add_row(self, row: Gtk.Widget) -> Gtk.Widget:
        """Add a single row to the group 'asynchronously' to avoid blocking the UI."""

        def _append_row():
            self._append_row(row)
            return GLib.SOURCE_REMOVE  # run only once

        GLib.idle_add(_append_row)
        return row

    def add_rows(self, rows: list[Gtk.Widget], batch_size: int = 2):
        """Add multiple rows to the group 'asynchronously' in batches to avoid blocking the UI."""
        if not rows:
            return

        index = 0

        def add_batch():
            nonlocal index
            end = min(index + batch_size, len(rows))
            for i in range(index, end):
                self._append_row(rows[i])
            index = end
            # return True to keep the idle source active if there are more items
            return index < len(rows)

        GLib.idle_add(add_batch)

    def remove_row(self, row: Gtk.Widget):
        for i in range(self.rows.get_n_items()):
            if self.rows.get_item(i) == row:
                super().remove(row)
                self.rows.remove(i)
                break

    def clear(self):
        while self.rows.get_n_items() > 0:
            idx = self.rows.get_n_items() - 1
            row = self.rows.get_item(idx)
            super().remove(row)
            self.rows.remove(idx)
        self.set_unfiltered()

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

    def get_visible_row_count(self) -> int:
        """Return the number of currently visible rows (excludes placeholders)."""
        count = 0
        for row in self.rows:
            count += int(row.get_visible())
        return count

    def apply_filters(self, filter_str: str = "", filter_tags: set[str] | None = None):
        """Apply search + tag filters using Gtk.FilterListModel."""
        if not self.filterable:
            return

        filter_str = filter_str.strip()
        filter_tags = filter_tags or set()

        # No filters -> restore original visibility
        if not filter_str and not filter_tags:
            self.reset_filtering()
            return

        regex = None
        if filter_str:
            try:
                parts = [re.escape(part) for part in filter_str.split()]
                fuzzy_pattern = ".*?".join(parts)  # Match any characters between the letters
                regex = re.compile(fuzzy_pattern, re.IGNORECASE)
            except re.error:
                return

        group_matches = bool(regex and self.filter_str and regex.search(self.filter_str))
        any_row_matches = group_matches

        for row in self.rows:
            if not isinstance(row, FilteringInterface):
                # Non-filterable rows stay as-is and count as visible content
                any_row_matches = True
                continue

            if not row.filterable:
                # row.set_unfiltered()
                any_row_matches = True
                continue

            row_matches = True
            if regex:
                row_matches = bool(row.filter_str and regex.search(row.filter_str))

            if filter_tags:
                row_matches = row_matches and any(row.has_filter_tag(tag) for tag in filter_tags)

            row.set_filtered(row_matches)
            any_row_matches = any_row_matches or row_matches

        self.set_filtered(any_row_matches)
        return

    def reset_filtering(self):
        """Reset group and row visibility to the defaults."""
        for row in self.rows:
            if isinstance(row, FilteringInterface):
                row.set_unfiltered()
        self.set_unfiltered()

    def set_filtered(self, visible: bool):
        super().set_filtered(visible)
        self.emit("filtered", visible)

    def set_unfiltered(self):
        super().set_unfiltered()
        self.emit("unfiltered")

    def _on_row_filtered(self, row: Gtk.Widget, visible: bool):
        """Handle a row being filtered."""
        self.emit("row-filtered", row, visible)

    def _on_row_unfiltered(self, row: Gtk.Widget):
        """Handle a row being unfiltered."""
        self.emit("row-unfiltered", row)
