# =============================================================================
# filtering_interface.py
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


class FilteringInterface:
    """Lightweight Python mixin for filtering support."""

    def __init__(self, filterable: bool = False):
        # filtering settings
        self._filterable = bool(filterable)
        self._filter_str = ""
        self._filter_tags: set[str] = set()
        self._is_currently_filtered = False

        # remember visibility so we can restore it after filtering
        self._visibility_before_filter = True

    @property
    def filterable(self) -> bool:
        return self._filterable

    @filterable.setter
    def filterable(self, value: bool):
        self._filterable = bool(value)

    def set_filterable(self, value: bool):
        self._filterable = bool(value)

    @property
    def filter_str(self) -> str:
        """The text used for filtering the row."""
        return self._filter_str.lower()

    @filter_str.setter
    def filter_str(self, value: str):
        self._filter_str = str(value).lower()

    def set_filter_str(self, text: str):
        self._filter_str = str(text).lower()

    @property
    def is_currently_filtered(self) -> bool:
        return self._is_currently_filtered

    @is_currently_filtered.setter
    def is_currently_filtered(self, value: bool):
        self._is_currently_filtered = bool(value)

    def has_filter_tag(self, tag: str) -> bool:
        return tag in self._filter_tags

    def add_filter_tag(self, tag):
        self._filter_tags.add(tag)

    def remove_filter_tag(self, tag):
        self._filter_tags.discard(tag)

    def _get_visible(self) -> bool:
        getter = getattr(self, "get_visible", None)
        if callable(getter):
            return getter()
        return True

    def _set_visible(self, value: bool):
        setter = getattr(self, "set_visible", None)
        if callable(setter):
            setter(value)

    # filters (hides) the row but remembers its original visibility
    def set_filtered(self, visible: bool):
        if not self.filterable:
            return

        if not self.is_currently_filtered:
            self._visibility_before_filter = self._get_visible()

        if self._visibility_before_filter:
            self._set_visible(visible)

        self.is_currently_filtered = True
        return

    # restores original visibility before the filtering
    def set_unfiltered(self):
        if self.is_currently_filtered:
            self._set_visible(self._visibility_before_filter)
            self.is_currently_filtered = False
