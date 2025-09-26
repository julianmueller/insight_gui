# =============================================================================
# pkg_info_page.py
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

from ament_index_python import get_package_share_directory, get_package_prefix, PackageNotFoundError
from ros2pkg.api import get_executable_paths
import xml.etree.ElementTree as ET

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, Gio

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.buttons import CopyButton


class PackageInfoPage(ContentPage):
    __gtype_name__ = "PackageInfoPage"

    def __init__(self, pkg_name: str, **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Package {pkg_name}")

        self.pkg_name = pkg_name
        self.detach_kwargs = {"pkg_name": pkg_name}

        package_share_dir = get_package_share_directory(self.pkg_name)
        package_xml = os.path.join(package_share_dir, "package.xml")
        self.xml_tree = ET.parse(package_xml).getroot()

        self.link_group = self.pref_page.add_group(title="Links")
        self.link_group.add_row(PrefRow(title="Open local package folder")).add_suffix_btn(
            icon_name="folder-symbolic",
            func=self.on_open_pkg_folder,
            func_kwargs={"pkg_name": self.pkg_name},
        )

        # add index link
        self.link_group.add_row(PrefRow(title="Open on index.ros.org")).add_suffix_btn(
            icon_name="web-browser-symbolic",
            func=lambda: Gio.AppInfo.launch_default_for_uri(f"https://index.ros.org/p/{self.pkg_name}/", None),
        )

        # add api link
        self.link_group.add_row(PrefRow(title="View API documentation on docs.ros.org")).add_suffix_btn(
            icon_name="folder-documents-symbolic",
            func=lambda: Gio.AppInfo.launch_default_for_uri(f"https://docs.ros.org/en/jazzy/p/{self.pkg_name}/", None),
        )

        # TODO there is currently no way (that i found) to get this
        # add source code link
        # self.link_group.add_row(PrefRow(title="View source code on repository")).add_suffix_btn(
        #     icon_name="git-symbolic",
        #     func=lambda: print("TODO"),
        # )

        # Executables
        self.executables_group = self.pref_page.add_group(
            title="Executables", empty_group_text="Package has no executables"
        )
        executable_paths = get_executable_paths(package_name=self.pkg_name)

        for path in sorted(executable_paths):
            executable_name = Path(path).name
            row: PrefRow = self.executables_group.add_row(PrefRow(title=executable_name))
            row.add_suffix(
                CopyButton(
                    copy_text=f"ros2 run {self.pkg_name} {executable_name}",
                    tooltip_text="Copy 'ros2 run' command",
                    toast_host=self.toast_overlay,
                )
            )
            row.add_suffix_btn(
                icon_name="terminal-alt-symbolic",
                tooltip_text="Open command in terminal",
                func=self.on_open_terminal_command,
                func_kwargs={"command": f"ros2 run {self.pkg_name} {executable_name}"},
            )

        # add the counts as descriptions
        self.executables_group.set_description_to_row_count()

        # XML inspection
        self.xml_group = self.pref_page.add_group(title="Content of package.xml")

    def on_realize(self, *args):
        super().on_realize()

        # version
        version = self.xml_tree.find("version").text
        self.xml_group.add_row(PrefRow(title="Version", subtitle=str(version), css_classes=["property"]))

        # description
        description = " ".join([line.strip() for line in str(self.xml_tree.find("description").text).split()])
        desc_row = self.xml_group.add_row(
            PrefRow(title="Description", subtitle=str(description), css_classes=["property"])
        )
        desc_row.subtitle_lbl.set_single_line_mode(False)
        desc_row.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.NONE)

        # maintainer
        maintainers = self.xml_tree.findall("maintainer")
        maintainers_exp = self.xml_group.add_row(Adw.ExpanderRow(title="Maintainers"))
        for m in maintainers:
            email = m.get("email")
            if email:
                row = PrefRow(title=m.text, subtitle=str(email), css_classes=["property"])
                row.add_suffix(CopyButton(copy_text=row.get_subtitle(), toast_host=self.toast_overlay))
            else:
                row = PrefRow(title=m.text)
            maintainers_exp.add_row(row)

        # license
        license_txt = self.xml_tree.find("license").text
        self.xml_group.add_row(PrefRow(title="License", subtitle=str(license_txt), css_classes=["property"]))

        # authors
        authors = self.xml_tree.findall("author")
        if len(authors) == 0:
            self.xml_group.add_row(PrefRow(title="<i>No authors</i>"))
        else:
            authors_exp = self.xml_group.add_row(Adw.ExpanderRow(title="Authors"))
            for a in authors:
                email = a.get("email")
                if email:
                    row = PrefRow(title=a.text, subtitle=str(email), css_classes=["property"])
                    row.add_suffix(CopyButton(copy_text=row.get_subtitle(), toast_host=self.toast_overlay))
                else:
                    row = PrefRow(title=a.text)
                authors_exp.add_row(row)

        def _add_depend_expander(depend: str):
            xml_dep_list = self.xml_tree.findall(depend)
            if len(xml_dep_list) == 0:
                row = self.xml_group.add_row(PrefRow(title=f"<i>No '{depend}' packages</i>"))
                row.set_use_markup(True)
                row.set_sensitive(False)
                return

            expander = self.xml_group.add_row(Adw.ExpanderRow(title=f"{depend} packages"))
            for xml_dep in xml_dep_list:
                dep_pkg_name = xml_dep.text
                row = PrefRow(title=dep_pkg_name)

                # check if package exists
                try:
                    pkg_prefix = get_package_prefix(dep_pkg_name)
                    row.set_subpage_link(
                        nav_view=self.nav_view,
                        subpage_class=PackageInfoPage,
                        subpage_kwargs={"pkg_name": dep_pkg_name},
                    )
                    row.set_subtitle(str(pkg_prefix))
                except PackageNotFoundError:
                    pass
                expander.add_row(row)

        # buildtool depends
        _add_depend_expander("buildtool_depend")

        # build depends
        _add_depend_expander("build_depend")

        # exec depends
        _add_depend_expander("exec_depend")

        # test depends
        _add_depend_expander("test_depend")

        # TODO also export ?

        # TODO add all the interfaces (msgs etc) that a package defines

    def on_open_pkg_folder(self, *, pkg_name: str):
        try:
            pkg_prefix = get_package_prefix(pkg_name)
        except PackageNotFoundError as e:
            self.show_toast(f"Package not found: {e}")
            return

        path = str((Path(pkg_prefix) / "share" / pkg_name).resolve())
        if os.path.isdir(path):
            folder_uri = Gio.File.new_for_path(path).get_uri()
            Gio.AppInfo.launch_default_for_uri(folder_uri, None)
        else:
            super().show_toast(f"Path '{path}' does not exist!")

    def on_open_terminal_command(self, *, command: str):
        """Open a terminal with a specific command."""
        try:
            launcher = Gio.SubprocessLauncher()
            launcher.set_flags(Gio.SubprocessFlags.NONE)

            # Set environment variables for the terminal
            env_list = [f"{key}={value}" for key, value in os.environ.items()]
            launcher.set_environ(env_list)

            launcher.spawnv(
                [
                    "gnome-terminal",
                    "--title",
                    f"Running: {command}",
                    "--",
                    "bash",
                    "-ic",
                    f"echo -e '\\033[1;32m{command}\\033[0m'; {command}",
                ]
            )
        except Exception as e:
            self.show_toast(f"Error opening terminal: {e}")
