# =============================================================================
# test_page.py
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

import webbrowser  # TODO replace with gnome tools

from ament_index_python.packages import get_packages_with_prefixes

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from insight_gui.ros2_pages.pkg_new_dialog import PackageNewDialog
from insight_gui.ros2_pages.pkg_info_page import PackageInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.zoomable_widget import ZoomableWidget
from insight_gui.widgets.zoomable import Zoomable


class TestPage(ContentPage):
    __gtype_name__ = "TestPage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title("Test")

        z = TestWidget()
        self.content_stack.add_named(z, "test")
        self.content_stack.set_visible_child_name("test")

    def refresh_bg(self) -> bool:
        return True

    def refresh_ui(self):
        pass

    def reset_ui(self):
        pass


class TestWidget(Zoomable, Gtk.Fixed):
    __gtype_name__ = "TestWidget"

    def __init__(self, **kwargs):
        Gtk.Fixed.__init__(self)
        Zoomable.__init__(self)
        print(self)

        self.set_overflow(Gtk.Overflow.HIDDEN)
        self.attach_zoom_controller()

        btn = Gtk.Button(label="Zoom Me")
        self.put(btn, 100, 100)
        self.add_zoom_child(btn)
