# =============================================================================
# action_info_page.py
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

from ros2node.api import _is_hidden_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


# TODO test this class, because i havent had an action in the list to look at its info
class ActionInfoPage(ContentPage):
    __gtype_name__ = "ActionInfoPage"

    def __init__(self, action_name: str, action_types: str | list[str], **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Action {action_name}")

        self.action_name = action_name
        self.action_types = action_types
        self.detach_kwargs = {
            "action_name": action_name,
            "action_types": action_types,
        }

        self.open_goal_page = super().add_bottom_left_btn(
            label="Open Action Goal",
            icon_name="emoji-flags-symbolic",
            func=self.on_goto_action_goal_page,
            tooltip_text="Go to action goal page",
        )

        # Action Type
        self.action_type_group = self.pref_page.add_group(title="Action Type")

        # Action Servers
        self.action_servers_group = self.pref_page.add_group(
            title="Action Servers", empty_group_text="action has no servers"
        )

        # Subscribers
        self.action_clients_group = self.pref_page.add_group(
            title="Action Clients", empty_group_text="action has no clients"
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a server/client of this action
        self.available_nodes = self.ros2_connector.get_available_nodes()
        return len(self.available_nodes) > 0

    def refresh_ui(self):
        def add_act_type_row(msg_type_full_name: str):
            msg_row = PrefRow(title=msg_type_full_name)  # , subtitle=node_full_name)
            msg_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=InterfaceInfoPage,
                subpage_kwargs={"interface_full_name": msg_type_full_name},
            )
            self.action_type_group.add_row(msg_row)

        if isinstance(self.action_types, str):
            add_act_type_row(self.action_types)
        elif isinstance(self.action_types, list):
            for msg_type in self.action_types:
                add_act_type_row(msg_type)

        for node_name, node_namespace, node_full_name in sorted(self.available_nodes, key=itemgetter(0)):
            # add those nodes, that are servers to the action
            action_servers_list = self.ros2_connector.get_action_servers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.action_name in server for server in action_servers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.action_servers_group.add_row(row)

            # add those nodes, that are clients to the action
            action_clients_list = self.ros2_connector.get_action_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.action_name in client for client in action_clients_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.action_clients_group.add_row(row)

        # add the counts as descriptions
        self.action_servers_group.set_description_to_row_count()
        self.action_clients_group.set_description_to_row_count()

    def reset_ui(self):
        self.action_type_group.clear()
        self.action_servers_group.clear()
        self.action_clients_group.clear()

    def on_goto_action_goal_page(self):
        self.nav_view.push(ActionGoalPage(preselect_action=self.action_name))
