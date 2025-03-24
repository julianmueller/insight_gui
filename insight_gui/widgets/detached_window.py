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
from gi.repository import Gtk, Adw


class DetachedWindow(Adw.ApplicationWindow):
    __gtype_name__ = "DetachedWindow"

    def __init__(self, application: Adw.Application, nav_page_class: Type, nav_page_kwargs: dict, **kwargs):
        super().__init__(**kwargs)

        super().set_destroy_with_parent(True)
        super().set_default_size(800, 600)

        self.nav_view: Adw.NavigationView = Adw.NavigationView()
        super().set_content(self.nav_view)

        self.app: Adw.Application = application  # backref to application
        self.nav_page: Adw.NavigationPage = nav_page_class(**nav_page_kwargs)
        self.nav_page.detach_btn.set_visible(False)
        self.nav_view.add(self.nav_page)

    # @property
    # def app(self):
    #     return self.app

    @property
    def ros2_connector(self):
        return self.app.ros2_connector
