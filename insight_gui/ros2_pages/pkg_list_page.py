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


class PackageListPage(ContentPage):
    __gtype_name__ = "PackageListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Package List")
        super().set_empty_page_text("Refresh to show packages")
        super().set_search_entry_placeholder_text("Search for Packages")

        self.pkg_list_group = self.pref_page.add_group(empty_group_text="Refresh to show packages")

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

    def refresh_bg(self) -> bool:
        self.available_pkgs = get_packages_with_prefixes()

        if len(self.available_pkgs) == 0:
            self.pkg_list_group.set_empty_group_text("No packages found. Refresh to try again.")
            return False
        return True

    def refresh_ui(self):
        rows = []
        for pkg_name, pkg_path in sorted(self.available_pkgs.items()):
            row = PrefRow(title=pkg_name, subtitle=pkg_path)
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=PackageInfoPage,
                subpage_kwargs={"pkg_name": pkg_name},
            )
            rows.append(row)

        self.pkg_list_group.add_rows_idle(rows)

    def reset_ui(self):
        self.pkg_list_group.clear()
