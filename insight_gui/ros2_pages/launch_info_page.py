# =============================================================================
# launch_info_page.py
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
from typing import Dict, Any

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import TextSubstitution, LaunchConfiguration
from launch.launch_description_sources.any_launch_file_utilities import (
    get_launch_description_from_any_launch_file,
)
from launch_ros.actions.node import Node
from ros2launch.api import launch_a_launch_file


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


class LaunchInfoPage(ContentPage):
    __gtype_name__ = "LaunchInfoPage"

    def __init__(self, pkg_name: str, launch_file_path: str, **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        self.launch_file_name = Path(launch_file_path).name
        super().set_title(f"Launch File {self.launch_file_name}")

        self.pkg_name = pkg_name
        self.launch_file_path = launch_file_path
        self.detach_kwargs = {
            "pkg_name": pkg_name,
            "launch_file_path": launch_file_path,
        }

        # Store argument values
        self.launch_args: Dict[str, Any] = {}
        self.arg_widgets: Dict[str, Gtk.Widget] = {}

    def on_realize(self, *args):
        super().on_realize()

        # Info group
        info_group = self.pref_page.add_group(title="Launch File Info")

        self.pkg_row = info_group.add_row(PrefRow(title="Package", subtitle=self.pkg_name, css_classes=["property"]))
        self.launch_path_row = info_group.add_row(
            PrefRow(
                title="Launch Path",
                subtitle=self.launch_file_path,
                css_classes=["property"],
            )
        )
        self.launch_path_row.add_suffix_btn(
            icon_name="folder-symbolic",
            func=lambda: Gio.AppInfo.launch_default_for_uri(
                Gio.File.new_for_path(self.launch_file_path).get_uri(), None
            ),
            tooltip_text="Open launch file folder",
        )

        # Group for all node entities
        self.nodes_group = self.pref_page.add_group(
            title="Executed Nodes",
            empty_group_text="Launch file has no nodes",
        )

        # TODO add groups, aka included launch files here as subpage
        # TODO add all nodes that are started with the launch, and show its remaps

        # Group for launch arguments
        self.arg_group = self.pref_page.add_group(
            title="Launch Arguments", empty_group_text="Launch file has no arguments"
        )

        # Add launch button in bottom left corner
        self.launch_btn = super().add_bottom_left_btn(
            label="Launch",
            icon_name="media-playback-start-symbolic",
            tooltip_text="Execute launch file with current arguments",
            func=self.on_launch_clicked,
            css_classes=["suggested-action"],
        )

    def refresh_bg(self) -> bool:
        try:
            self.launch_desc: LaunchDescription = get_launch_description_from_any_launch_file(
                launch_file_path=self.launch_file_path
            )

            return True
        except Exception as e:
            print(f"Error parsing launch arguments: {e}")
            return False

    def refresh_ui(self):
        if self.launch_desc.deprecated:
            self.show_banner(f"Launch Description deprecated: {self.launch_desc.deprecated_reason}")

        for entity in self.launch_desc.entities:
            if isinstance(entity, DeclareLaunchArgument):
                default_value = ""
                for val in entity.default_value:
                    if isinstance(val, TextSubstitution):
                        default_value += val.text
                    elif isinstance(val, LaunchConfiguration):
                        default_value += val.variable_name[0].text

                row = self.arg_group.add_row(
                    Adw.EntryRow(
                        title=entity.name,
                        text=default_value,
                        tooltip_text=entity.description,
                        show_apply_button=True,
                    )
                )

                self.launch_args[entity.name] = row.get_text

            elif isinstance(entity, Node):
                # TODO turn this into a expander, that shows all the args to that node
                self.nodes_group.add_row(
                    PrefRow(
                        title=f"pkg {entity.node_package}",
                        subtitle=f"exec {entity.node_executable}",
                        css_classes=["property"],
                    )
                )

        self.show_banner("The Launch Info page is still experimental")  # DEBUG

    def reset_ui(self):
        pass

    # def add_argument_row(self, arg_name: str, arg_info: Dict[str, Any]):
    #     """Add a row for a launch argument based on its type."""
    #     arg_type = arg_info.get("type", "string")
    #     description = arg_info.get("description", "")
    #     default_value = arg_info.get("default")

    #     # Create subtitle with description and default
    #     subtitle_parts = []
    #     if description:
    #         subtitle_parts.append(description)
    #     if default_value is not None:
    #         subtitle_parts.append(f"Default: {default_value}")
    #     subtitle = " • ".join(subtitle_parts) if subtitle_parts else f"Type: {arg_type}"

    #     if arg_type == "bool":
    #         # Use SwitchRow for boolean arguments
    #         row = Adw.SwitchRow(title=arg_name, subtitle=subtitle)
    #         if default_value and default_value.lower() == "true":
    #             row.set_active(True)
    #         row.connect("notify::active", self.on_bool_arg_changed, arg_name)
    #         self.arg_widgets[arg_name] = row

    #     elif arg_type in ["int", "float"]:
    #         # Use EntryRow for numeric arguments
    #         row = Adw.EntryRow(
    #             title=arg_name, text=str(default_value) if default_value else ""
    #         )
    #         row.set_subtitle(subtitle)
    #         if arg_type == "int":
    #             row.set_input_purpose(Gtk.InputPurpose.DIGITS)
    #         else:
    #             row.set_input_purpose(Gtk.InputPurpose.NUMBER)
    #         row.connect("notify::text", self.on_text_arg_changed, arg_name)
    #         self.arg_widgets[arg_name] = row

    #     else:
    #         # Use EntryRow for string arguments
    #         row = Adw.EntryRow(
    #             title=arg_name, text=str(default_value) if default_value else ""
    #         )
    #         row.set_subtitle(subtitle)
    #         row.connect("notify::text", self.on_text_arg_changed, arg_name)
    #         self.arg_widgets[arg_name] = row

    #     self.args_group.add_row(row)

    #     # Initialize the argument value
    #     if arg_type == "bool":
    #         self.launch_args[arg_name] = row.get_active()
    #     else:
    #         self.launch_args[arg_name] = row.get_text()

    # def on_bool_arg_changed(self, switch_row: Adw.SwitchRow, pspec, arg_name: str):
    #     """Handle boolean argument changes."""
    #     self.launch_args[arg_name] = switch_row.get_active()

    # def on_text_arg_changed(self, entry_row: Adw.EntryRow, pspec, arg_name: str):
    #     """Handle text argument changes."""
    #     self.launch_args[arg_name] = entry_row.get_text()

    def on_launch_clicked(self):
        # TODO work this out further:
        # - only pass args that were changed
        # - start the launch in a new terminal

        args = []
        for arg, arg_val in self.launch_args.items():
            args.append(f"{arg}:={arg_val()}")

        launch_a_launch_file(launch_file_path=self.launch_file_path, launch_file_arguments=args)

    #     """Execute the launch file with current arguments."""
    #     try:
    #         # Build launch command
    #         cmd = ["ros2", "launch", self.pkg_name, self.launch_file]

    #         # Add arguments
    #         for arg_name, arg_value in self.launch_args.items():
    #             if arg_value is not None and str(arg_value).strip():
    #                 if isinstance(arg_value, bool):
    #                     cmd.append(f"{arg_name}:={'true' if arg_value else 'false'}")
    #                 else:
    #                     cmd.append(f"{arg_name}:={arg_value}")

    #         # Show launch command in toast
    #         cmd_str = " ".join(cmd)
    #         self.show_toast(f"Launching: {cmd_str}")

    #         # Execute in background thread
    #         def run_launch():
    #             try:
    #                 # Use subprocess to run the launch command
    #                 process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    #                 # Don't wait for completion as launch files typically run indefinitely
    #                 GLib.idle_add(
    #                     lambda: self.show_toast(f"Launch started successfully (PID: {process.pid})", timeout=5)
    #                 )

    #             except Exception as ex:
    #                 GLib.idle_add(lambda ex=ex: self.show_toast(f"Launch failed: {ex}", timeout=5))

    #         # Start launch in background thread
    #         launch_thread = threading.Thread(target=run_launch, daemon=True)
    #         launch_thread.start()

    #     except Exception as e:
    #         self.show_toast(f"Error preparing launch: {e}")
