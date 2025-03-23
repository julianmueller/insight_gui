# =============================================================================
# pkg_pages.py
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

import os
from pathlib import Path
import webbrowser

from ros2pkg.api import get_executable_paths
from ament_index_python.packages import get_packages_with_prefixes

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.new_pkg_dialog import NewPkgDialog
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.buttons import CopyButton


class PackageListPage(ContentPage):
    __gtype_name__ = "PackageListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Package List")
        super().set_empty_page_text("Refresh to show packages")
        super().set_search_entry_placeholder_text("Search for Packages")

    def on_realize(self, *args):
        super().on_realize(*args)

        self.pkg_list_group = self.pref_page.add_group(empty_group_text="Refresh to show packages")

        super().add_bottom_left_btn(
            icon_name="list-add-symbolic",
            tooltip_text="Create New Package",
            func=lambda: NewPkgDialog().present(self),
        )

        super().add_bottom_right_btn(
            icon_name="webpage-symbolic",
            tooltip_text="Open ROS Index",
            func=lambda: webbrowser.open("https://index.ros.org/packages/#jazzy"),
        )

    def on_refresh_blocking(self) -> bool:
        self.available_pkgs = get_packages_with_prefixes()

        if len(self.available_pkgs) == 0:
            self.pkg_list_group.set_empty_group_text("No packages found. Refresh to try again.")
            return False
        return True

    def on_refresh_gui(self):
        rows = []
        for pkg_name, pkg_path in self.available_pkgs.items():
            row = PrefRow(title=pkg_name, subtitle=pkg_path)
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=PackageInfoPage,
                subpage_kwargs={"pkg_name": pkg_name, "pkg_path": pkg_path},
            )
            rows.append(row)

        self.pkg_list_group.add_rows_idle(rows)

    def on_clear_gui(self):
        self.pkg_list_group.clear()


class PackageInfoPage(ContentPage):
    __gtype_name__ = "PackageInfoPage"

    def __init__(self, pkg_name: str, pkg_path: str, **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Package <{pkg_name}>")

        self.pkg_name = pkg_name
        self.pkg_path = pkg_path
        self.detach_kwargs = {"pkg_name": pkg_name, "pkg_path": pkg_path}

    def on_realize(self, *args):
        super().on_realize(*args)

        self.link_group = self.pref_page.add_group(title="Links")
        self.link_group.add_row(PrefRow(title="Open local package folder")).add_suffix_btn(
            icon_name="folder-symbolic",
            func=self.on_open_pkg_folder,
            func_kwargs={"pkg_path": self.pkg_path, "pkg_name": self.pkg_name},
        )

        # add index link
        self.link_group.add_row(PrefRow(title="Open on index.ros.org")).add_suffix_btn(
            icon_name="webpage-symbolic",
            func=lambda: webbrowser.open(f"https://index.ros.org/p/{self.pkg_name}/"),
        )

        # add api link
        self.link_group.add_row(PrefRow(title="View API documentation on docs.ros.org")).add_suffix_btn(
            icon_name="folder-documents-symbolic",
            func=lambda: webbrowser.open(f"https://docs.ros.org/en/jazzy/p/{self.pkg_name}/"),
        )

        # add source code link
        self.link_group.add_row(PrefRow(title="View source code on repository")).add_suffix_btn(
            icon_name="git-symbolic",
            func=lambda: print("TODO"),  # webbrowser.open(f""),
        )

        # TODO add the xml infos
        # from here: https://github.com/ros2/ros2cli/blob/jazzy/ros2pkg/ros2pkg/verb/xml.py
        # - package version number
        # - description
        # - authors & maintainers
        # - license
        # - urls
        # - dependencies?

        # TODO add all the interfaces (msgs etc) that a package defines

        # Executables
        executables_group = self.pref_page.add_group(title="Executables", empty_group_text="Package has no executables")
        executable_paths = get_executable_paths(package_name=self.pkg_name)

        for path in sorted(executable_paths):
            executable_name = Path(path).name
            row = executables_group.add_row(PrefRow(title=executable_name))
            row.add_suffix(
                CopyButton(
                    copy_text=f"ros2 run {self.pkg_name} {executable_name}",
                    tooltip_text="Copy 'ros2 run' command",
                    toast_host=self.toast_overlay,
                )
            )

        # add the counts as descriptions
        executables_group.set_description_to_row_count()

    def on_open_pkg_folder(self, *, pkg_path: str, pkg_name: str):
        path = (Path(pkg_path) / "share" / pkg_name).resolve()
        if os.path.isdir(path):
            os.system(rf"xdg-open {path}")
        else:
            super().show_toast(f"Path '{path}' does not exist!")
