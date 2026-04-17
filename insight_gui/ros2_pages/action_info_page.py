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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.models.action_item import ActionItem
from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import InterfaceTypeRow, NodeRow


# TODO test this class, because i havent had an action in the list to look at its info
class ActionInfoPage(ContentPage):
    __gtype_name__ = "ActionInfoPage"

    def __init__(self, action: ActionItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Action {action.full_name}")

        self.action = action
        self.action_full_name = action.full_name
        self.action_interface_full_name = action.interface.full_name
        self.detach_kwargs = {"action": action}

        self.open_goal_page_btn = super().add_bottom_left_btn(
            label="Open Action Goal",
            icon_name="emoji-flags-symbolic",
            func=self._on_goto_action_goal_page,
            tooltip_text="Go to action goal page",
        )

        # Action Interface Type
        self.action_interface_type_group = self.pref_page.add_group(title="Action Interface Type", collapsable=True)

        # Action Servers
        self.action_servers_group = self.pref_page.add_group(
            title="Action Servers", placeholder_text="This action has no servers.", collapsable=True
        )

        # Action Clients
        self.action_clients_group = self.pref_page.add_group(
            title="Action Clients", placeholder_text="This action has no clients.", collapsable=True
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a server/client of this action
        self.server_nodes = []
        self.client_nodes = []

        for node in self.ros2_connector.collect_nodes():
            servers = self.ros2_connector.collect_action_servers_by_node(node=node)
            if any(server.full_name == self.action_full_name for server in servers):
                self.server_nodes.append(node)

            clients = self.ros2_connector.collect_action_clients_by_node(node=node)
            if any(client.full_name == self.action_full_name for client in clients):
                self.client_nodes.append(node)

        return bool(self.server_nodes or self.client_nodes)

    def refresh_ui(self):
        # create a row for the action type # TODO maybe rather add the request/response/feedback as rows?
        interface_type_row = InterfaceTypeRow(interface=self.action.interface, nav_view=self.nav_view)
        self._add_rows_async(self.action_interface_type_group, (interface_type_row,), batch_size=1)
        self._add_item_rows_async(
            self.action_servers_group,
            self.server_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.action_servers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.action_clients_group,
            self.client_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.action_clients_group.set_description_to_row_count,
        )

    def _build_node_row(self, node) -> NodeRow:
        return NodeRow(node=node, nav_view=self.nav_view)

    def reset_ui(self):
        self.action_interface_type_group.clear()
        self.action_servers_group.clear()
        self.action_clients_group.clear()

    # def trigger(self): # TODO
    #     self._on_goto_action_goal_page()

    def _on_goto_action_goal_page(self):
        self._push_subpage(ActionGoalPage, {"preselect_action": self.action})
