# =============================================================================
# pkg_list_page.py
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

from ament_index_python.packages import get_packages_with_prefixes

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from insight_gui.ros2_pages.pkg_new_dialog import PackageNewDialog
from insight_gui.ros2_pages.pkg_info_page import PackageInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.models.package_item import PackageItem


class PackageListPage(ContentPage):
    __gtype_name__ = "PackageListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Package List")
        super().set_placeholder_text("Refresh to show packages")
        super().set_search_entry_placeholder_text("Search for Packages")

        self.pkg_list_group = self.pref_page.add_group(placeholder_text="Refresh to show packages")
        self.pkgs_store: Gio.ListStore = Gio.ListStore.new(PackageItem)

        self.new_pkg_btn = super().add_bottom_left_btn(
            label="New Package",
            icon_name="list-add-symbolic",
            tooltip_text="Create a new package",
            func=lambda *_: PackageNewDialog().present(),
        )

        self.open_ros_index_btn = super().add_bottom_right_btn(
            label="ROS Index",
            icon_name="web-browser-symbolic",
            tooltip_text="Open ROS Index",
            func=lambda: Gio.AppInfo.launch_default_for_uri("https://index.ros.org/packages/#jazzy", None),
        )

    def refresh_bg(self):
        self.available_pkgs = sorted(get_packages_with_prefixes().items())
        return bool(self.available_pkgs)

    def refresh_ui(self):
        if not self.available_pkgs:
            self.pkg_list_group.clear()
            self.pkg_list_group.set_placeholder_text("No packages found. Refresh to try again.")
            return

        self.pkg_list_group.clear()
        self._add_item_rows_async(
            self.pkg_list_group,
            self.available_pkgs,
            lambda pkg: self._build_pkg_row(*pkg),
            batch_size=5,
            priority=GLib.PRIORITY_LOW,
        )

    def _build_pkg_row(self, pkg_name: str, pkg_path: str) -> PrefRow:
        pkg = PackageItem(name=pkg_name, path=pkg_path)
        row = PrefRow(title=pkg.name, subtitle=pkg.path)
        row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=PackageInfoPage,
            subpage_kwargs={"pkg": pkg},
        )
        return row

    def reset_ui(self):
        pass
