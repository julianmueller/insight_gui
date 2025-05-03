#!/usr/bin/env python

# =============================================================================
# application.py
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

# standard imports
from pathlib import Path

# GTK and GUI specific imports
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

# custom imports
from insight_gui.window import MainWindow
from insight_gui.ros2_connector import ROS2Connector


class Ros2GuiApp(Adw.Application):
    __gtype_name__ = "InsightApplication"

    def __init__(self, share_dir: Path = None):
        super().__init__(application_id="com.github.julianmueller.Insight")
        Gtk.init()
        Adw.init()

        self.share_dir = share_dir

        # Load the compiled GResource file
        resource = Gio.Resource.load(str(share_dir / "resources.gresource"))
        Gio.Resource._register(resource)

        # set the application icon
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_resource_path("/com/github/julianmueller/Insight/logo")

        self.window: Adw.ApplicationWindow = None
        self.detached_windows: list[Adw.ApplicationWindow] = []

    def do_startup(self):
        Adw.Application.do_startup(self)

        # ros2 connector handles all connections to the ros2 node
        self.ros2_connector = ROS2Connector(application=self)

        # Define "app.ros2_node_start" action
        ros2_node_start_action = Gio.SimpleAction.new("ros2-node-start", None)
        ros2_node_start_action.connect("activate", lambda *_: self.ros2_connector.start_node())
        self.add_action(ros2_node_start_action)

        # Define "app.ros2_node_stop" action
        ros2_node_stop_action = Gio.SimpleAction.new("ros2-node-stop", None)
        ros2_node_stop_action.connect("activate", lambda *_: self.ros2_connector.stop_node())
        self.add_action(ros2_node_stop_action)

        # Define "app.ros2_node_is_running" as a stateful action
        ros2_node_is_running_action = Gio.SimpleAction.new_stateful(
            "ros2-node-is-running", None, GLib.Variant.new_boolean(self.ros2_connector.is_running)
        )
        ros2_node_is_running_action.connect("notify::state", self.ros2_connector.on_node_state_changed)
        self.add_action(ros2_node_is_running_action)

        # start the ros2 node
        self.ros2_connector.start_node()

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self, title="Insight", icon_name="insight-logo")

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.window.on_preferences_dialog)
        self.add_action(action)

        action = Gio.SimpleAction.new("close-all-detached-windows", None)
        action.connect("activate", self.on_close_all_detached_windows)
        self.add_action(action)

        action = Gio.SimpleAction.new("shortcuts", None)
        action.connect("activate", self.window.on_shortcuts_dialog)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.window.on_about_dialog)
        self.add_action(action)

        self.window.connect("close-request", self.shutdown)
        self.window.present()

    def shutdown(self, *args):
        print("Shutting down GTK window.")
        self.ros2_connector.shutdown()
        Gtk.Application.quit(self)
        return GLib.SOURCE_REMOVE

    def on_close_all_detached_windows(self, *args):
        for win in reversed(self.detached_windows):
            win.close()
            self.detached_windows.remove(win)
