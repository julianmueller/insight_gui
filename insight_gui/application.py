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

import asyncio
import concurrent.futures
import threading
from collections.abc import Callable
from functools import partial
from pathlib import Path

# # HOTFIX for https://discourse.gnome.org/t/gtk4-efficiency-and-performance-in-x11-export-remote-drawing-mode/8786
# os.environ["GSK_RENDERER"] = "cairo"

from ament_index_python import get_package_share_directory

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

# custom imports
from insight_gui.window import MainWindow
from insight_gui.ros2_connector import ROS2Connector


APPLICATION_ID = "com.github.julianmueller.Insight"
APPLICATION_PATH = APPLICATION_ID.replace(".", "/")


class InsightApplication(Adw.Application):
    __gtype_name__ = "InsightApplication"

    def __init__(self):
        super().__init__(application_id=APPLICATION_ID)
        Gtk.init()
        Adw.init()

        # find the shared data directory
        self.share_dir = Path(get_package_share_directory("insight_gui")) / "data"

        # Load the compiled GResource file
        Gio.Resource.load(str(self.share_dir / "resources.gresource"))._register()

        # set the application icon
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        # icon_theme.add_resource_path(APPLICATION_PATH + "/icons")
        icon_theme.add_resource_path(APPLICATION_PATH + "/logo")

        self.main_window: Adw.ApplicationWindow = None
        self.detached_windows: list[Adw.ApplicationWindow] = []

        # Initialize settings
        try:
            # self.settings = Gio.Settings.new(APPLICATION_ID)
            schema_source = Gio.SettingsSchemaSource.new_from_directory(
                str(self.share_dir), Gio.SettingsSchemaSource.get_default(), False
            )
            schema = schema_source.lookup(APPLICATION_ID, False)
            self.settings = Gio.Settings.new_full(schema, None, None)

        except Exception as e:
            print(f"Application: Could not initialize GSettings normally: {e}")

        # Async machinery shared across widgets for background tasks
        self._loop_ready = threading.Event()
        self._worker_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="insight-worker"
        )
        self._asyncio_thread = threading.Thread(
            target=self._run_asyncio_loop,
            name="insight-asyncio",
            daemon=True,
        )
        self._asyncio_thread.start()

    def do_startup(self):
        Adw.Application.do_startup(self)

        # set color scheme
        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
        self.style_manager.connect("notify::dark", self.on_theme_changed)

        # set the default icon for the application
        Gtk.Window.set_default_icon_name("insight")

        # ros2 connector handles all connections to the ros2 node
        self.ros2_connector = ROS2Connector()

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
        if not self.main_window:
            self.main_window = MainWindow(app=self, title="Insight", icon_name="insight")

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.main_window.on_preferences_dialog)
        self.add_action(action)

        action = Gio.SimpleAction.new("close-all-detached-windows", None)
        action.connect("activate", self.on_close_all_detached_windows)
        self.add_action(action)

        action = Gio.SimpleAction.new("shortcuts", None)
        action.connect("activate", self.main_window.on_shortcuts_dialog)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.main_window.on_about_dialog)
        self.add_action(action)

        self.main_window.connect("close-request", self.shutdown)
        self.main_window.present()

    def shutdown(self, *args):
        self.ros2_connector.shutdown()
        if getattr(self, "asyncio_loop", None):
            self.asyncio_loop.call_soon_threadsafe(self.asyncio_loop.stop)
            if hasattr(self, "_asyncio_thread"):
                self._asyncio_thread.join(timeout=1)
        self._worker_executor.shutdown(wait=False, cancel_futures=True)
        Gtk.Application.quit(self)
        return GLib.SOURCE_REMOVE

    def on_close_all_detached_windows(self, *args):
        for win in reversed(self.detached_windows):
            win.close()
            self.detached_windows.remove(win)

    def on_theme_changed(self, *args):
        # TODO implement settings here, to choose light/dark/system
        dark = Adw.StyleManager.get_default().get_dark()
        provider = Gtk.CssProvider()

        if dark:
            provider.load_from_data(b"image { color: white; }")
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            provider.load_from_data(b"image { color: black; }")
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _run_asyncio_loop(self):
        # Dedicated asyncio loop for worker scheduling (no GLib event policy).
        self.asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.asyncio_loop)
        self._loop_ready.set()
        try:
            self.asyncio_loop.run_forever()
        finally:
            self.asyncio_loop.close()

    def run_in_worker(
        self,
        func: Callable,
        *args,
        done_callback: Callable[[concurrent.futures.Future], None] | None = None,
        **kwargs,
    ) -> concurrent.futures.Future:
        """Run a blocking callable on the single worker thread.

        The optional ``done_callback`` receives the resulting Future and is
        executed in the worker thread context, so use ``idle_add`` if you need
        to touch GTK from inside it.
        """

        async def _runner():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._worker_executor, partial(func, *args, **kwargs))

        if not self._loop_ready.wait(timeout=1):
            raise RuntimeError("Asyncio loop not ready")

        future = asyncio.run_coroutine_threadsafe(_runner(), self.asyncio_loop)
        if done_callback:
            future.add_done_callback(done_callback)
        return future

    def idle_add(self, func, *args, **kwargs) -> None:
        """Invoke `func` on the GTK/GLib main thread. Used for GUI updates."""

        def _wrapper():
            func(*args, **kwargs)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_wrapper)
