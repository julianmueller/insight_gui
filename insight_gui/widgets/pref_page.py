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

    def remove_group(self, pref_group: PrefGroup):
        super().remove(pref_group)
        self.groups.remove(pref_group)

    def clear(self):
        for pref_group in reversed(self.groups):
            self.remove_group(pref_group)
        self.empty_group.set_visible(True)
        self.groups = []

    def apply_filter(self, text: str):
        """Filters groups and rows based on a search query."""

        def reset_filtering():
            """Resets all groups and rows to their original visibility."""
            for group in self.groups:
                if not group.filterable:
                    continue
                group.set_unfiltered()
                for row in group.rows:
                    if getattr(row, "filterable", False):
                        row.set_unfiltered()

        # If the search text is empty, restore original visibility
        if not text.strip():
            reset_filtering()
            return

        try:
            regex = re.compile(text, re.IGNORECASE)
        except re.error as e:
            print(f"Regex error: {e}")
            reset_filtering()
            return

        # Filtering process
        for group in self.groups:
            if not group.filterable:
                continue

            group_matches = bool(group.filter_text and regex.search(group.filter_text))
            any_row_matches = False

            for row in group.rows:
                if not getattr(row, "filterable", False):
                    continue

                row_matches = bool(row.filter_text and regex.search(row.filter_text))
                if row_matches:
                    row.set_filtered(True)  # Show matching row
                    any_row_matches = True
                else:
                    row.set_filtered(False)  # Hide non-matching row

            # Show group if it matches or any row inside it matches
            group.set_filtered(group_matches or any_row_matches)

    def set_empty_page_text(self, text: str):
        self.empty_group.set_empty_group_text(text)
