# =============================================================================
# welcome_page.py
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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage


class WelcomePage(ContentPage):
    __gtype_name__ = "WelcomePage"

    def __init__(self, **kwargs):
        super().__init__(refreshable=False, searchable=False, detachable=False, **kwargs)
        super().set_title("Welcome to Insight GUI")

        status_page = Adw.StatusPage(
            title="Welcome to Insight GUI",
            description="Select the pages in the left navigation.",
            icon_name="insight",
        )
        self.content_stack.add_child(status_page)
        self.content_stack.set_visible_child(status_page)
