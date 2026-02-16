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
from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


# TODO test this class, because i havent had an action in the list to look at its info
class ActionInfoPage(ContentPage):
    __gtype_name__ = "ActionInfoPage"

    def __init__(self, action: ActionItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Action {action.full_name}")

        self.action = action
        self.detach_kwargs = {"action": action}

        self.open_goal_page_btn = super().add_bottom_left_btn(
            label="Open Action Goal",
            icon_name="emoji-flags-symbolic",
            func=self._on_goto_action_goal_page,
            tooltip_text="Go to action goal page",
        )

        # Action Interface Type
        self.action_interface_type_group = self.pref_page.add_group(title="Action Interface Type")

        # Action Servers
        self.action_servers_group = self.pref_page.add_group(
            title="Action Servers", placeholder_text="This action has no servers."
        )

        # Action Clients
        self.action_clients_group = self.pref_page.add_group(
            title="Action Clients", placeholder_text="This action has no clients."
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a server/client of this action
        self.ros2_connector.refresh_nodes_store()
        self.available_nodes = self.ros2_connector.nodes_store
        return self.available_nodes is not None and self.available_nodes.get_n_items() > 0

    def refresh_ui(self):
        # create a row for the action type # TODO maybe rather add the request/response/feedback as rows?
        interface_type_row = PrefRow(title=self.action.interface.full_name)
        interface_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=InterfaceInfoPage,
            subpage_kwargs={"interface": self.action.interface},
        )
        self.action_interface_type_group.add_row(interface_type_row)

        # populate the servers and clients
        for node in self.available_nodes:
            # add those nodes, that are servers to the action # TODO this could probably be optimized
            action_servers_list = self.ros2_connector.get_action_servers_by_node(node=node)
            found, index = action_servers_list.find(self.action)
            if found:
                row = PrefRow(title=node.name, subtitle=node.full_name)
                if node.hidden:
                    row.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node": node},
                )
                self.action_servers_group.add_row(row)

            # add those nodes, that are clients to the action # TODO this could probably be optimized
            action_clients_list = self.ros2_connector.get_action_clients_by_node(node=node)
            found, index = action_clients_list.find(self.action)
            if found:
                row = PrefRow(title=node.name, subtitle=node.full_name)
                if node.hidden:
                    row.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node": node},
                )
                self.action_clients_group.add_row(row)

        # add the counts as descriptions
        self.action_servers_group.set_description_to_row_count()
        self.action_clients_group.set_description_to_row_count()

    def reset_ui(self):
        self.action_interface_type_group.clear()
        self.action_servers_group.clear()
        self.action_clients_group.clear()

    # def trigger(self): # TODO
    #     self._on_goto_action_goal_page()

    def _on_goto_action_goal_page(self):
        self.nav_view.push(ActionGoalPage(preselect_action=self.action))
