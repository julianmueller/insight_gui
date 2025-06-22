# =============================================================================
# launch_list_page.py
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

from pathlib import Path
from typing import Dict

from ament_index_python.packages import get_packages_with_prefixes
from ros2launch.api import is_launch_file

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from insight_gui.ros2_pages.launch_info_page import LaunchInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class LaunchListPage(ContentPage):
    __gtype_name__ = "LaunchListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Launch Files")
        super().set_empty_page_text("Refresh to show packages with launch files")
        super().set_search_entry_placeholder_text("Search for Packages with Launch Files")

        self.pkg_launch_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        """Find all packages that contain launch files."""
        self.pkgs_with_launch_files = {}

        # TODO move this into the connector
        try:
            # Get all packages and their launch files
            all_packages = get_packages_with_prefixes()

            for pkg_name, pkg_path in all_packages.items():
                launch_dir = Path(pkg_path) / "share" / pkg_name / "launch"
                if not launch_dir.exists() or not launch_dir.is_dir():
                    continue

                # Look for launch files in the pkg launch dir
                launch_files = []
                for file in launch_dir.glob("*"):
                    file_path = str(file.resolve())
                    if file.is_file() and is_launch_file(file_path):
                        launch_files.append(file_path)

                if launch_files:
                    self.pkgs_with_launch_files[pkg_name] = {
                        "path": str(launch_dir),
                        "launch_files": [f for f in launch_files],
                    }

            return len(self.pkgs_with_launch_files) > 0

        except Exception as e:
            print(f"Error finding launch packages: {e}")
            return False

    def refresh_ui(self):
        # TODO add a setting to group launch files
        for pkg_name, pkg_info in sorted(self.pkgs_with_launch_files.items()):
            # get the namespace group of the topic
            if pkg_name in self.pkg_launch_groups.keys():
                group = self.pkg_launch_groups[pkg_name]
            else:
                group = self.pref_page.add_group(title=pkg_name, description=pkg_info["path"])
                self.pkg_launch_groups[pkg_name] = group

            rows = []
            for launch_file_path in pkg_info["launch_files"]:
                launch_file_name = Path(launch_file_path).name

                row = PrefRow(title=launch_file_name, subtitle=launch_file_path)
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=LaunchInfoPage,
                    subpage_kwargs={"pkg_name": pkg_name, "launch_file_path": launch_file_path},
                )
                rows.append(row)

            group.add_rows_idle(rows)

            # set the subtitle of the group to the package path and number of launch files
            num_launch_files = len(pkg_info["launch_files"])
            group.set_description(
                f"{num_launch_files} launch file{'s' if num_launch_files > 1 else ''} in {pkg_info['path']}"
            )

        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.pkg_launch_groups.values()):
            self.pref_page.remove_group(group)
        self.pkg_launch_groups.clear()
