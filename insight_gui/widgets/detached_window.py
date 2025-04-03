# =============================================================================
# detached_window.py
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
from typing import Type

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk

from insight_gui.ros2_connector import ROS2Connector


class DetachedWindow(Adw.ApplicationWindow):
    __gtype_name__ = "DetachedWindow"

    def __init__(self, application: Adw.Application, nav_page_class: Type, nav_page_kwargs: dict, **kwargs):
        super().__init__(**kwargs)

        super().set_destroy_with_parent(True)
        super().set_size_request(480, 600)
        super().set_default_size(480, 600)

        self.nav_view: Adw.NavigationView = Adw.NavigationView()
        super().set_content(self.nav_view)

        self.app: Adw.Application = application  # backref to application
        # nav_page_kwargs.update({"detachable": False})  # make detached pages not detachable
        self.nav_page: Adw.NavigationPage = nav_page_class(**nav_page_kwargs)
        self.nav_view.add(self.nav_page)

        action = Gio.SimpleAction.new("refresh", None)
        action.connect("activate", self.on_refresh)
        self.add_action(action)

        action = Gio.SimpleAction.new("toggle_search", None)
        action.connect("activate", self.on_toggle_search)
        self.add_action(action)

        action = Gio.SimpleAction.new("detach", None)
        action.connect("activate", self.on_detach)
        self.add_action(action)

        action = Gio.SimpleAction.new("close", None)
        action.connect("activate", self.on_close)
        self.add_action(action)

        # Shortcuts # TODO make them also work in the detached windows
        self.shortcut_controller = Gtk.ShortcutController()
        self.shortcut_controller.set_scope(Gtk.ShortcutScope.LOCAL)  # Important!
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.AlternativeTrigger.new(
                    Gtk.KeyvalTrigger.new(Gdk.KEY_r, Gdk.ModifierType.CONTROL_MASK),
                    Gtk.KeyvalTrigger.new(Gdk.KEY_F5, Gdk.ModifierType.NO_MODIFIER_MASK),
                ),
                action=Gtk.NamedAction.new("win.refresh"),  # Use window-scoped action
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_f, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.toggle_search"),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_d, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.detach"),
            )
        )
        self.shortcut_controller.add_shortcut(
            shortcut=Gtk.Shortcut.new(
                trigger=Gtk.KeyvalTrigger.new(Gdk.KEY_w, Gdk.ModifierType.CONTROL_MASK),
                action=Gtk.NamedAction.new("win.close"),
            )
        )

        # Add controller to window
        self.add_controller(self.shortcut_controller)

    # @property
    # def app(self):
    #     return self.app

    @property
    def ros2_connector(self) -> ROS2Connector:
        return self.app.ros2_connector

    def on_refresh(self, *args):
        if self.nav_page.refreshable:
            self.nav_page.refresh()

    def on_detach(self, *args):
        if self.nav_page.detachable:
            self.nav_page.detach()

    def on_toggle_search(self, *args):
        if self.nav_page.searchable:
            self.nav_page.toggle_search()

    def on_close(self, *args):
        self.close()
