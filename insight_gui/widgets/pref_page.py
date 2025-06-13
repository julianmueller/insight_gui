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

import re

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.pref_group import PrefGroup


class PrefPage(Adw.PreferencesPage):
    __gtype_name__ = "PrefPage"

    def __init__(
        self,
        *,
        title: str = "Preferences",
        icon_name: str = "settings-symbolic",
        description: str = "",
        empty_page_text: str = "page is empty",
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(str(title))
        super().set_icon_name(icon_name)

        # NOTE a pref page can also have a description!
        if description:
            super().set_description(str(description))

        self.groups: list[PrefGroup] = []
        self.empty_group = PrefGroup(sensitive=False, empty_group_text=empty_page_text)
        super().add(self.empty_group)

    @property
    def num_groups(self) -> int:
        return len(self.groups)

    @property
    def is_empty(self) -> bool:
        return self.num_groups == 0

    def add(self, *args, **kwargs):
        raise NotImplementedError("use 'add_group' instead")

    def add_group(
        self,
        *,
        title: str = "",
        description: str = "",
        empty_group_text: str = "group is empty",
        filterable: bool = True,
        **kwargs,
    ) -> PrefGroup:
        self.empty_group.set_visible(False)

        # check if pref group already exists
        pref_group = self.get_group(title)
        if pref_group:
            return pref_group

        else:
            pref_group = PrefGroup(
                title=title, description=description, empty_group_text=empty_group_text, filterable=filterable, **kwargs
            )
            super().add(pref_group)
            self.groups.append(pref_group)
            return pref_group

    def get_group(self, title: str) -> PrefGroup:
        for group in self.groups:
            if group.get_title() == title:
                return group
        else:
            return None

    def sort_groups(self, reverse=False):
        """Sorts the groups by a given key."""
        self.groups.sort(key=lambda g: g.get_title(), reverse=reverse)
        for group in self.groups:
            super().remove(group)
        # Re-add the groups to the page to update their order
        for group in self.groups:
            super().add(group)

    def remove_group(self, pref_group: PrefGroup):
        super().remove(pref_group)
        self.groups.remove(pref_group)

    def clear(self):
        for pref_group in reversed(self.groups):
            self.remove_group(pref_group)
        self.empty_group.set_visible(True)
        self.groups = []

    def apply_filters(self, search_str: str, search_tags: set[str] = None):
        """Filters groups and rows based on a search query."""
        # TODO make this also handle tags of rows

        # If the search text is empty, restore original visibility
        if not search_str.strip() and not search_tags:
            self.reset_filtering()
            return

        # Compile the regex pattern beforehand to avoid repeated compilation
        try:
            str_parts = [re.escape(part) for part in search_str.strip().split()]
            fuzzy_pattern = ".*?".join(str_parts)  # Match any characters between the letters
            regex = re.compile(fuzzy_pattern, re.IGNORECASE)
        except re.error as e:
            print(f"Regex error: {e}")
            self.reset_filtering()
            return

        # Filtering process
        for group in self.groups:
            if not group.filterable:
                continue

            group_matches = bool(search_str and group.filter_text and regex.search(group.filter_text))
            any_row_matches = False

            for row in group.rows:
                if not getattr(row, "filterable", False):
                    continue

                # Check if the row matches the search text
                row_matches = bool(row.filter_text and regex.search(row.filter_text))

                # Check if the row matches any of the tags to keep
                if search_tags:
                    row_matches &= any(row.has_tag(tag) for tag in search_tags)

                if row_matches:
                    row.set_filtered(True)  # Show matching row
                    any_row_matches = True
                else:
                    row.set_filtered(False)  # Hide non-matching row

            # Show group if it matches or any row inside it matches
            group.set_filtered(group_matches or any_row_matches)

    def reset_filtering(self):
        """Resets all groups and rows to their original visibility."""
        for group in self.groups:
            if not group.filterable:
                continue
            group.set_unfiltered()
            for row in group.rows:
                if getattr(row, "filterable", False):
                    row.set_unfiltered()

    def set_empty_page_text(self, text: str):
        self.empty_group.set_empty_group_text(text)
