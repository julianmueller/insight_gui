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


class PrefGroup(Adw.PreferencesGroup):
    """Custom wrapper class around Adw.PreferencesGroup to manage preference rows."""

    __gtype_name__ = "PrefGroup"

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
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_description(str(description))

        self.box: Gtk.Box = super().get_first_child()
        self.title_box: Gtk.Box = self.box.get_first_child()
        self.suffix_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        super().set_header_suffix(self.suffix_box)

        self.rows_box: Gtk.Box = self.title_box.get_next_sibling()
        self.listbox: Gtk.ListBox = self.rows_box.get_first_child()

        # keep track of all rows (use a Gio.ListStore instead of a python list)
        self.rows: Gio.ListStore = Gio.ListStore.new(Gtk.Widget)
        self.rows.connect("items-changed", self._on_rows_changed)
        self._default_visibility = self.get_visible()
        self._search_query: str = ""
        self._search_tags: set[str] = set()
        self._compiled_search: re.Pattern | None = None

        if not title and not description:
            self.title_box.set_visible(False)  # disable group header

        self.filterable = filterable
        self.placeholder_row = PrefRow(title=placeholder_text, sensitive=False)
        self.placeholder_row.add_prefix_icon("dialog-error-symbolic")
        self.set_placeholder_text(placeholder_text)
        # self.bind_property("is-empty", self.placeholder_row, "visible", GObject.BindingFlags.SYNC_CREATE)
        # super().add(self.placeholder_row)
        self.listbox.set_placeholder(self.placeholder_row)

        # Filtering model driven by Gtk instead of manual visibility toggles
        self.row_filter = Gtk.CustomFilter.new(self._filter_row)
        self.filtered_rows = Gtk.FilterListModel(model=self.rows, filter=self.row_filter)
        self.filtered_rows.connect("items-changed", self._on_filtered_items_changed)

        self.listbox.bind_model(self.filtered_rows, self._bind_row)

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

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def filter_text(self) -> str:
        return f"{self.get_title()} {self.get_description()}".lower()

    @GObject.Property(type=int, default=0)
    def visible_rows_count(self) -> int:
        return self.filtered_rows.get_n_items()

    def _on_rows_changed(self, *args):
        self.notify("num-rows")
        self.notify("is-empty")

    def _bind_row(self, row: Gtk.Widget) -> Gtk.Widget:
        return row

    def _compile_pattern(self, search: str) -> re.Pattern | None:
        search = search.strip()
        if not search:
            return None
        try:
            parts = [re.escape(part) for part in search.split()]
            return re.compile(".*?".join(parts), re.IGNORECASE)
        except re.error:
            return None

    def _filter_row(self, row: Gtk.Widget) -> bool:
        if not self.filterable:
            return True

        matches_query = True
        if self._compiled_search:
            row_text = getattr(row, "filter_text", "").lower()
            if row_text:
                matches_query = bool(self._compiled_search.search(row_text))
                if not matches_query:
                    matches_query = self._fuzzy_match(self._search_query, row_text)

        matches_tags = True
        if self._search_tags:
            matches_tags = any(getattr(row, "has_filter_tag", lambda *_: False)(tag) for tag in self._search_tags)

        return matches_query and matches_tags

    def _on_filtered_items_changed(self, *args):
        self._update_group_visibility()

    def _update_group_visibility(self):
        if not self.filterable:
            return

        if not self._compiled_search and not self._search_tags:
            self.set_visible(self._default_visibility)
            return

        group_matches = bool(self._compiled_search and self._compiled_search.search(self.filter_text))
        rows_visible = self.visible_rows_count > 0
        self.set_visible(group_matches or rows_visible)

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_row' instead")

    def add_row(self, row: Gtk.Widget) -> Gtk.Widget:
        GLib.idle_add(self.rows.append, row)
        return row

    def add_rows(self, rows: list[Gtk.Widget], batch_size: int = 2):
        if not rows:
            return

        index = 0

        def add_batch():
            nonlocal index
            end = min(index + batch_size, len(rows))
            for i in range(index, end):
                self.add_row(rows[i])
            index = end
            # return True to keep the idle source active if there are more items
            return index < len(rows)

        GLib.idle_add(add_batch)

    def remove_row(self, row: Gtk.Widget):
        for i in range(self.rows.get_n_items()):
            if self.rows.get_item(i) == row:
                self.rows.remove(i)
                break

    def clear(self):
        while self.rows.get_n_items() > 0:
            self.rows.remove(self.rows.get_n_items() - 1)
        self.placeholder_row.set_visible(True)

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

    def apply_filter(self, search_text: str = "", search_tags: set[str] | None = None):
        """Apply search + tag filters using Gtk.FilterListModel."""
        search_tags = search_tags or set()
        self._search_query = search_text.strip()
        self._search_tags = set(search_tags)
        self._compiled_search = self._compile_pattern(self._search_query)
        self.row_filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_group_visibility()

    def reset_filtering(self):
        """Reset group and row visibility to the defaults."""
        self.apply_filter("", set())

    def _fuzzy_match(self, query: str, text: str, threshold: float = 0.6) -> bool:
        """Simple fuzzy matcher using difflib ratio to allow near matches."""
        if not query or not text:
            return False
        ratio = SequenceMatcher(None, query.lower(), text.lower()).ratio()
        return ratio >= threshold
