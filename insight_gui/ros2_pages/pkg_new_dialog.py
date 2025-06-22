# =============================================================================
# pkg_new_dialog.py
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

import ament_copyright
from ros2pkg.api.create import (
    create_package_environment,
    populate_ament_cmake,
    # populate_cmake,
    populate_cpp_node,
    populate_cpp_library,
    populate_ament_python,
    populate_python_node,
    populate_python_libary,
)
from catkin_pkg.package import Package, Person, Dependency, License, Export

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio

from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class PackageNewDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PackageNewDialog"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Create New ROS2 Package")
        super().set_size_request(width=300, height=500)
        super().set_presentation_mode(Adw.DialogPresentationMode.AUTO)

        self.page = PrefPage(title="New pkg", icon_name="document-new-symbolic")
        super().add(self.page)

        # Get all licenses
        self.available_licenses = {}
        for shortname, entry in ament_copyright.get_licenses().items():
            self.available_licenses[entry.spdx] = entry.license_files

        # Group of build type
        build_type_group = self.page.add_group(title="Build Type")
        build_type_group.add_suffix_btn(
            icon_name="info-symbolic",
            tooltip_text="ROS Documentation",
            func=lambda: Gio.AppInfo.launch_default_for_uri(
                "https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html",
                None,
            ),
        )

        self.python_switch_row = build_type_group.add_row(Adw.SwitchRow(title="ament_python", active=True))
        self.python_switch_handler = self.python_switch_row.connect("notify::active", self.on_build_type_changed)
        self.cmake_switch_row = build_type_group.add_row(Adw.SwitchRow(title="ament_cmake"))
        self.cmake_switch_handler = self.cmake_switch_row.connect("notify::active", self.on_build_type_changed)

        # group with package name
        pkg_group = self.page.add_group(title="Package Info")
        self.pkg_name_row = pkg_group.add_row(Adw.EntryRow(title="Package Name", text="my_package"))

        self.license_row = pkg_group.add_row(
            Adw.ComboRow(
                title="License",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.license_store = Gio.ListStore.new(Gtk.StringObject)
        for lic in self.available_licenses.keys():
            self.license_store.append(Gtk.StringObject.new(lic))
        self.license_store.append(Gtk.StringObject.new("Custom License"))
        self.license_row.set_model(self.license_store)

        self.node_name_row = pkg_group.add_row(Adw.EntryRow(title="Node Name"))
        self.library_name_row = pkg_group.add_row(Adw.EntryRow(title="Library Name"))
        self.maintainer_name_row = pkg_group.add_row(Adw.EntryRow(title="Maintainer Name"))
        self.maintainer_mail_row = pkg_group.add_row(Adw.EntryRow(title="Maintainer Mail"))
        self.description_row = pkg_group.add_row(Adw.EntryRow(title="Description"))
        self.dependencies_row = pkg_group.add_row(Adw.EntryRow(title="Dependencies (separated by ';')"))

        self.dest_dir_row: PrefRow = pkg_group.add_row(PrefRow(title="Destination Directory"))
        self.dest_dir = None
        self.dest_dir_row.add_suffix_btn(
            icon_name="folder-symbolic", tooltip_text="Choose Path", func=self.on_choose_pkg_path
        )

        self.apply_btn = pkg_group.add_row(
            ButtonRow(
                label="Create",
                tooltip_text="Create ROS2 Package",
                func=self.on_create_pkg,
            )
        )

    def on_build_type_changed(self, switch, prop_name):
        if switch == self.python_switch_row:
            other = self.cmake_switch_row
            other_handler = self.cmake_switch_handler
        elif switch == self.cmake_switch_row:
            other = self.python_switch_row
            other_handler = self.python_switch_handler

        GObject.signal_handler_block(other, other_handler)
        other.set_active(not switch.get_active())
        GObject.signal_handler_unblock(other, other_handler)

    def on_choose_pkg_path(self, *args):
        def callback(file_dialog: Gtk.FileDialog, result, user_data):
            try:
                folder = file_dialog.select_folder_finish(result)
                if folder:
                    self.dest_dir = folder.get_path()
                    self.dest_dir_row.set_subtitle(self.dest_dir)
            except Exception as e:
                # print("No folder selected or error:", e)
                self.dest_dir = None
                self.dest_dir_row.set_subtitle("")

        ros2_ws_src = str((Path(os.getenv("ROS_WS", os.getcwd())) / "src").resolve())
        if os.path.exists(ros2_ws_src):
            initial_folder = Gio.File.new_for_path(ros2_ws_src)
        else:
            initial_folder = None

        Gtk.FileDialog(title="Select a Folder", initial_folder=initial_folder, modal=True).select_folder(
            parent=self.get_root(), callback=callback, user_data=None
        )

    def show_toast(self, title: str, *, priority: Adw.ToastPriority = Adw.ToastPriority.NORMAL, timeout: int = 2):
        """Show a toast message"""
        self.add_toast(Adw.Toast(title=title, priority=priority, timeout=timeout))

    # adapted from https://github.com/ros2/ros2cli/blob/rolling/ros2pkg/ros2pkg/verb/create.py
    def on_create_pkg(self, *args):
        build_type = "ament_python" if self.python_switch_row.get_active() else "ament_cmake"
        pkg_name = self.pkg_name_row.get_text()
        license_name = self.license_row.get_selected_item().get_string()
        node_name = self.node_name_row.get_text()
        library_name = self.library_name_row.get_text()
        maintainer_name = self.maintainer_name_row.get_text()
        maintainer_mail = self.maintainer_mail_row.get_text()
        description = self.description_row.get_text()
        dependencies = [dep.strip() for dep in self.dependencies_row.get_text().split(";")]

        if self.dest_dir is None or self.dest_dir == "":
            self.show_toast("Destination directory must not be empty.")
            return

        if pkg_name == "":
            self.show_toast("Package name must not be empty.")
            return

        if library_name == node_name and not library_name == "":
            self.show_toast("If set, library name and node name must be different.")
            return

        if maintainer_name == "":
            maintainer_name = str(os.getlogin())

        if maintainer_mail == "":
            maintainer_mail = f"{os.getlogin()}@TODO.com"

        if description == "":
            description = "TODO: Package description"

        buildtool_depends = []
        if build_type == "ament_cmake":
            if library_name:
                buildtool_depends = ["ament_cmake_ros"]
            else:
                buildtool_depends = ["ament_cmake"]

        test_dependencies = []
        if build_type == "ament_cmake":
            test_dependencies = ["ament_lint_auto", "ament_lint_common"]
        elif build_type == "ament_python":
            test_dependencies = ["ament_copyright", "ament_flake8", "ament_pep257", "ament_xmllint", "python3-pytest"]

        if build_type == "ament_python" and pkg_name == "test":
            # If the package name is 'test', there will be a conflict between the directory the source code for the
            # package goes in and the directory the tests for the package go in.
            self.show_toast("'ament_python' packages can't be named 'test'")
            return

        maintainer = Person(name=maintainer_name, email=maintainer_mail)
        package = Package(
            package_format=3,  # TODO necessary as option?
            name=pkg_name,
            version="0.0.0",
            description=description,
            maintainers=[maintainer],
            licenses=[license_name],
            buildtool_depends=[Dependency(dep) for dep in buildtool_depends],
            build_depends=[Dependency(dep) for dep in dependencies],
            test_depends=[Dependency(dep) for dep in test_dependencies],
            exports=[Export("build_type", content=build_type)],
        )

        package_path = os.path.join(self.dest_dir, pkg_name)
        if os.path.exists(package_path):
            self.show_toast(f"directory '{package_path}' already exists")
            return

        package_directory, source_directory, include_directory = create_package_environment(
            package=package, destination_directory=self.dest_dir
        )

        if not package_directory:
            self.show_toast(f"unable to create folder '{self.dest_dir}'")
            return

        # populate the package directories
        # if build_type == 'cmake':
        #     populate_cmake(package, package_directory, node_name, library_name)

        if build_type == "ament_cmake":
            populate_ament_cmake(package, package_directory, node_name, library_name)

        if build_type == "ament_python":
            if not source_directory:
                self.show_toast(f"unable to create source folder in {self.dest_dir}")
                return

            populate_ament_python(package, package_directory, source_directory, node_name)

            if node_name:
                populate_python_node(package, source_directory, node_name)
            if library_name:
                populate_python_libary(package, source_directory, library_name)

        elif build_type == "ament_cmake" or build_type == "cmake":
            populate_ament_cmake(package, package_directory, node_name, None)

            if node_name:
                if not source_directory:
                    self.show_toast(f"unable to create source folder in '{self.dest_dir}'")
                    return
                populate_cpp_node(package, source_directory, node_name)
            if library_name:
                if not source_directory or not include_directory:
                    self.show_toast(f"unable to create source or include folder in '{self.dest_dir}'")
                    return
                populate_cpp_library(package, source_directory, include_directory, library_name)

        if license_name in self.available_licenses:
            with open(os.path.join(package_directory, "LICENSE"), "w") as outfp:
                for lic in self.available_licenses[license_name]:
                    outfp.write(lic)
        else:
            self.show_toast("Unknown license. So no LICENSE file was created.")

        self.close()
