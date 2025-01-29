import os
from pathlib import Path
import webbrowser

from ament_index_python.packages import get_package_share_directory
from ros2pkg.api.create import (
    create_package_environment,
    populate_ament_cmake,
    populate_ament_python,
    populate_cpp_node,
    populate_python_node,
)
from catkin_pkg.package import Package, Person, Dependency, License, Export

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio

from insight_gui.ros2_node import ROS2CommunicationNode
from insight_gui.widgets.helpers.pref_page import PrefPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.helpers.button_row import ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class NewPkgDialog(Adw.PreferencesDialog):
    __gtype_name__ = "NewPkgDialog"

    def __init__(self, ros2_node: ROS2CommunicationNode = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Create New ROS2 Package")

        # self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        # Page with ROS2 Settings
        self.page = PrefPage(title="ROS2 Node", icon_name="applications-other-symbolic")
        super().add(self.page)

        # Group of build type
        build_type_group = self.page.add_group(title="Build Type")
        build_type_group.add_btn(
            icon_name="info-symbolic",
            tooltip_text="ROS Documentation",
            func=lambda: webbrowser.open(
                "https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html"
            ),
        )

        self.python_switch_row = build_type_group.add_row(Adw.SwitchRow(title="ament_python", active=True))
        self.python_switch_handler = self.python_switch_row.connect("notify::active", self.on_build_type_changed)
        self.cmake_switch_row = build_type_group.add_row(Adw.SwitchRow(title="ament_cmake"))
        self.cmake_switch_handler = self.cmake_switch_row.connect("notify::active", self.on_build_type_changed)

        # group with package name
        pkg_group = self.page.add_group(title="Package Info")
        self.pkg_name_row = pkg_group.add_row(Adw.EntryRow(title="Package Name", text="my_package"))
        self.license_row = pkg_group.add_row(Adw.EntryRow(title="License", text="Apache-2.0"))  # TODO make dropdown
        self.node_name_row = pkg_group.add_row(Adw.EntryRow(title="Node Name"))
        self.maintainer_name_row = pkg_group.add_row(Adw.EntryRow(title="Maintainer Name"))
        self.maintainer_mail_row = pkg_group.add_row(Adw.EntryRow(title="Maintainer Mail"))
        self.description_row = pkg_group.add_row(Adw.EntryRow(title="Description"))

        self.pkg_path_row: PrefRow = pkg_group.add_row(PrefRow(title="Choose Package Path"))
        self.pkg_path = None
        self.pkg_path_row.add_suffix_btn(
            icon_name="folder-symbolic", tooltip_text="Choose Path", func=self.on_choose_pkg_path
        )

        # TODO add:
        # - dependencies
        # - description
        # - destination-directory
        # - maintainer-email
        # - maintainer-name
        # - library-name

        self.apply_btn = pkg_group.add_row(
            ButtonRow(
                title="Create",
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
                    self.pkg_path = folder.get_path()
                    self.pkg_path_row.set_subtitle(self.pkg_path)
            except Exception as e:
                # print("No folder selected or error:", e)
                self.pkg_path = None
                self.pkg_path_row.set_subtitle("")

        ros2_ws_src = str((Path(os.getenv("ROS_WS", os.getcwd())) / "src").resolve())
        if os.path.exists(ros2_ws_src):
            initial_folder = Gio.File.new_for_path(ros2_ws_src)
        else:
            initial_folder = None

        Gtk.FileDialog(title="Select a Folder", initial_folder=initial_folder, modal=True).select_folder(
            parent=self.get_root(), callback=callback, user_data=None
        )

    # with help from https://github.com/ros2/ros2cli/blob/rolling/ros2pkg/ros2pkg/verb/create.py
    def on_create_pkg(self, *args):
        build_type = "ament_python" if self.python_switch_row.get_active() else "ament_cmake"
        pkg_name = self.pkg_name_row.get_text()
        license_name = self.license_row.get_text()
        node_name = self.node_name_row.get_text()
        maintainer_name = self.maintainer_name_row.get_text()
        maintainer_mail = self.maintainer_mail_row.get_text()
        description = self.description_row.get_text()

        maintainer = Person(name=maintainer_name, email=maintainer_mail)
        package = Package(
            package_format=3,  # TODO necessary as option?
            name=pkg_name,
            version="0.0.0",
            description=description,
            maintainers=[maintainer],
            licenses=[license_name],
            # buildtool_depends=[Dependency(dep) for dep in buildtool_depends],
            # build_depends=[Dependency(dep) for dep in args.dependencies],
            # test_depends=[Dependency(dep) for dep in test_dependencies],
            exports=[Export("build_type", content=build_type)],
        )

        # package_path = os.path.join(self.pkg_path, pkg_name)
        package_directory, source_directory, include_directory = create_package_environment(
            package=package, destination_directory=self.pkg_path
        )

        if build_type == "ament_python":
            if not source_directory:
                return "unable to create source folder in " + args.destination_directory
            populate_ament_python(package, package_directory, source_directory, node_name)
            if node_name:
                populate_python_node(package, source_directory, node_name)
            # if library_name: # TODO
            #     populate_python_libary(package, source_directory, library_name)

        elif build_type == "ament_cmake":
            populate_ament_cmake(package, package_directory, node_name, None)

            if node_name:
                if not source_directory:
                    return "unable to create source folder in " + args.destination_directory
                populate_cpp_node(package, source_directory, node_name)
            # if library_name:
            #     if not source_directory or not include_directory:
            #         return "unable to create source or include folder in " + args.destination_directory
            #     populate_cpp_library(package, source_directory, include_directory, library_name)

        # TODO this does not really work yet
        if license_name:
            with open(os.path.join(package_directory, "LICENSE"), "w") as outfp:
                outfp.write(license_name)
        else:
            print(
                "\n[WARNING]: Unknown license '%s'.  This has been set in the package.xml, but "
                "no LICENSE file has been created.\nIt is recommended to use one of the ament "
                # "license identifiers:\n%s" % (args.license, "\n".join(available_licenses)) # TODO
            )

        self.close()
