# =============================================================================
# action_list_page.py
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

from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ActionListPage(ContentPage):
    __gtype_name__ = "ActionListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Actions")
        super().set_empty_page_text("No actions to show")
        super().set_search_entry_placeholder_text("Search for actions")
        super().set_refresh_fail_text("No actions found. Refresh to try again.")

        self.action_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.available_actions = self.ros2_connector.get_available_actions()
        return len(self.available_actions) > 0

    def refresh_ui(self):
        for action_name, action_types in self.available_actions:
            # action_types is a list, as multiple servers can advertise different types to the same action
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(action_types) == 1:
                action_types = action_types[0]
            else:
                action_types = ", ".join(action_types)

            # split action name into namespace and name
            parts = action_name.rstrip("/").split("/")
            namespace = "/".join(parts[:-1])  # Everything except the last part
            name = "/" + parts[-1]  # The last part, prefixed with '/'

            # put all actions in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-actions-by-namespace"):
                namespace = ""

            # get the namespace group of the action
            if namespace in self.action_ns_groups.keys():
                group = self.action_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.action_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=action_name, subtitle=action_types)
            row.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
            row.subtitle_lbl.set_tooltip_text(action_name)

            if topic_or_service_is_hidden(action_name):
                row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={"action_name": action_name, "action_types": action_types},
            )
            group.add_row(row)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.action_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.action_ns_groups.clear()
