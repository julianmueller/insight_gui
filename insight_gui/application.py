#!/usr/bin/env python

# standard imports
from pathlib import Path

# GTK and GUI specific imports
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Adw, GLib

# custom imports
from insight_gui.widgets.window import MainWindow
from insight_gui.ros2_connector import ROS2Connector


class Ros2GuiApp(Adw.Application):
    """The main application singleton class."""

    def __init__(self, share_dir: Path = None, start_ros2_connector: bool = True):
        super().__init__(application_id="com.github.julianmueller.insight_gui")
        Gtk.init()
        Adw.init()

        self.share_dir = share_dir

        # Load the compiled GResource file
        # resource_path = Path(get_package_share_directory("insight_gui")) / "data" / "resources.gresource.xml"
        # resource = Gio.resource_load(str(resource_path))  # TODO compile the gresource
        # Gio.Resource._register(resource)

        self.window = None

        # add event handles
        self.connect("activate", self.on_activate)

        if start_ros2_connector:
            self.ros2_connector = ROS2Connector()

    def on_activate(self, app):
        if not self.window:
            self.window = MainWindow(application=app)

        self.window.connect("close-request", self.shutdown)
        self.window.present()

    def shutdown(self, widget=None):
        print("Shutting down GTK window.")
        self.ros2_connector.shutdown()
        Gtk.Application.quit(self)
        return GLib.SOURCE_REMOVE
