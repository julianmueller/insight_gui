# =============================================================================
# pref_page.py
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
from gi.repository import GObject, Gtk, Adw, Gio

from insight_gui.widgets.pref_group import PrefGroup


class PrefPage(Adw.PreferencesPage):
    """Custom wrapper class around Adw.PreferencesPage to manage preference groups and their rows."""

    __gtype_name__ = "PrefPage"

    __gsignals__ = {
        "group-filtered": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN)),
        "group-unfiltered": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    }

    groups = GObject.Property(type=Gio.ListStore)
    placeholder_group = GObject.Property(type=PrefGroup)

    def __init__(
        self,
        *,
        title: str = "Preferences",
        icon_name: str = "settings-symbolic",
        description: str = "",
        placeholder_text: str = "page is empty",
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_icon_name(icon_name)

        # NOTE a pref page can also have a description!
        if description:
            super().set_description(str(description))

        self.groups: Gio.ListStore = Gio.ListStore(item_type=PrefGroup.__gtype__)
        self.groups.connect("items-changed", self._on_groups_changed)

        self.placeholder_group = PrefGroup(sensitive=False, placeholder_text=placeholder_text)
        self.set_placeholder_text(placeholder_text)
        self.bind_property("is-empty", self.placeholder_group, "visible", GObject.BindingFlags.SYNC_CREATE)
        super().add(self.placeholder_group)

    @GObject.Property(type=int, default=0)
    def num_groups(self) -> int:
        return self.groups.get_n_items()

    @GObject.Property(type=bool, default=True)
    def is_empty(self) -> bool:
        return self.num_groups == 0

    @GObject.Property(type=str, default="page is empty")
    def placeholder_text(self) -> str:
        return self.placeholder_group.get_placeholder_text()

    @placeholder_text.setter
    def placeholder_text(self, value: str) -> None:
        self.placeholder_group.set_placeholder_text(str(value))

    def set_placeholder_text(self, text: str) -> None:
        self.placeholder_text = text

    def _on_groups_changed(self, *args) -> None:
        self.notify("num-groups")
        self.notify("is-empty")

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_group' instead")

    def add_group(
        self,
        *,
        title: str = "",
        description: str = "",
        filterable: bool = True,
        **kwargs,
    ) -> PrefGroup:
        # check if pref group already exists
        pref_group = self.get_group(title)
        if pref_group:
            return pref_group

        else:
            pref_group = PrefGroup(title=title, description=description, filterable=filterable, **kwargs)
            pref_group.connect("filtered", self._on_groups_filtered_changed)
            pref_group.connect("unfiltered", self.on_groups_unfiltered_changed)
            super().add(pref_group)
            self.groups.append(pref_group)
            return pref_group

    def get_group(self, title: str) -> PrefGroup:
        """Returns the PrefGroup with the given title, or None if not found."""
        for i in range(self.num_groups):
            group = self.groups.get_item(i)
            if group.get_title() == title:
                return group
        else:
            return None

    def sort_groups(self, reverse=False):
        """Sorts the groups by their title."""
        # materialize current groups, sort, then re-apply order in the store and on the page
        current = [self.groups.get_item(i) for i in range(self.groups.get_n_items())]
        current.sort(key=lambda g: g.get_title(), reverse=reverse)

        # remove all groups from the page
        for group in current:
            super().remove(group)

        # clear the store
        while self.groups.get_n_items() > 0:
            self.groups.remove(0)

        # re-add groups in sorted order
        for group in current:
            super().add(group)
            self.groups.append(group)

    def remove_group(self, pref_group: PrefGroup):
        super().remove(pref_group)
        # find index and remove from the store
        index = None
        for i in range(self.groups.get_n_items()):
            if self.groups.get_item(i) == pref_group:
                index = i
                break
        if index is not None:
            self.groups.remove(index)

    def clear(self):
        # remove groups from page and clear the ListStore
        # remove in reverse order to be safe
        while self.groups.get_n_items() > 0:
            idx = self.groups.get_n_items() - 1
            pref_group = self.groups.get_item(idx)
            self.remove_group(pref_group)

    def get_total_row_count(self) -> int:
        """Return total number of rows across all groups (excludes placeholders)."""
        total = 0
        for i in range(self.groups.get_n_items()):
            total += self.groups.get_item(i).num_rows
        return total

    def get_visible_row_count(self) -> int:
        """Return number of currently visible rows after filtering."""
        total = 0
        for i in range(self.groups.get_n_items()):
            group = self.groups.get_item(i)
            if group.get_visible():
                total += group.get_visible_row_count()
        return total

    def apply_filters(self, filter_str: str, filter_tags: set[str] = None):
        """Filters groups and rows based on the given filter string and tags."""
        filter_tags = filter_tags or set()

        if not filter_str.strip() and not filter_tags:
            self.reset_filtering()
            return

        for i in range(self.groups.get_n_items()):
            group = self.groups.get_item(i)
            if not group.filterable:
                continue
            group.apply_filters(filter_str, filter_tags)

    def reset_filtering(self):
        """Resets all groups and rows to their original visibility."""
        for i in range(self.groups.get_n_items()):
            group = self.groups.get_item(i)
            if not group.filterable:
                continue
            group.reset_filtering()

    def _on_groups_filtered_changed(self, group: PrefGroup, filtered: bool):
        self.emit("group-filtered", group, filtered)

    def on_groups_unfiltered_changed(self, group: PrefGroup):
        self.emit("group-unfiltered", group)
