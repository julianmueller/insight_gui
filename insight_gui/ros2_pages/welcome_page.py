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

from operator import itemgetter
from typing import Dict

from rclpy.action import get_action_names_and_types

# from ros2action.api import get_action_
from rosidl_runtime_py import set_message_fields
from rosidl_runtime_py.utilities import get_service
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class WelcomePage(ContentPage):
    __gtype_name__ = "WelcomePage"

    def __init__(self, **kwargs):
        super().__init__(refreshable=False, searchable=False, detachable=False, **kwargs)
        super().set_title("Welcome to Insight GUI")

        status_page = Adw.StatusPage(
            title="Welcome to Insight GUI",
            description="Select the pages in the left navigation.",
            icon_name="insight-logo",
        )
        self.content_stack.add_child(status_page)
        self.content_stack.set_visible_child(status_page)
