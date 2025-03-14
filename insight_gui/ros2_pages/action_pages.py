# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from operator import itemgetter
from typing import Dict

from rclpy.action import get_action_names_and_types
from ros2node.api import _is_hidden_name, get_node_names
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import ActionTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ActionListPage(ContentPage):
    __gtype_name__ = "ActionListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(empty_page_text="Refresh to show actions", **kwargs)
        super().set_title("Action List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Search for actions")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.action_ns_groups: Dict[PrefGroup] = {}

    def refresh_blocking(self, *args) -> bool:
        self.available_actions = sorted(get_action_names_and_types(node=self.ros2_connector.node), key=itemgetter(0))
        return len(self.available_actions) > 0

    def refresh_gui(self, *args):
        if len(self.available_actions) == 0:
            self.pref_page.set_empty_page_text("No actions found. Refresh to try again.")
            return

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

            # TODO add a button to enable/disable sorting into groups
            # get the namespace group of the action
            if namespace in self.action_ns_groups.keys():
                group = self.action_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.action_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=name, subtitle=action_types)
            # , is_hidden=action_or_service_is_hidden(action_name)) # TODO is_hidden possible for actions?
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_connector=self.ros2_connector,
            )
            group.add_row(row)

    def clear_gui(self):
        for group in reversed(self.action_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.action_ns_groups.clear()


# TODO test this class, because i havent had an action in the list to look at its info
class ActionInfoPage(ContentPage):
    __gtype_name__ = "ActionInfoPage"

    def __init__(
        self,
        action_name: str,
        action_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Action <{action_name}>")

        self.action_name = action_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(
            type(self),
            dedock_kwargs={
                "action_name": self.action_name,
                "action_types": action_types,
                "ros2_connector": self.ros2_connector,
            },
        )

        # Action Type
        action_type_group = self.pref_page.add_group(title="Action Type")

        def add_act_type_row(msg_type_full_name: str):
            msg_row = PrefRow(title=msg_type_full_name)  # , subtitle=node_full_name)
            msg_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionTypeInfoPage,
                act_type_full_name=msg_type_full_name,
            )
            action_type_group.add_row(msg_row)

        if isinstance(action_types, str):
            add_act_type_row(action_types)
        elif isinstance(action_types, list):
            for msg_type in action_types:
                add_act_type_row(msg_type)

        # first, gather all nodes, to check which of them is a server/client of this action
        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        # Action Servers
        action_servers_group = self.pref_page.add_group(
            title="Action Servers", empty_group_text="action has no servers"
        )

        # Subscribers
        action_clients_group = self.pref_page.add_group(
            title="Action Clients", empty_group_text="action has no clients"
        )

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # add those nodes, that are servers to the action

            action_servers_list = get_action_server_names_and_types_by_node(
                node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            if any(self.action_name in server for server in action_servers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                action_servers_group.add_row(row)

            # add those nodes, that are clients to the action
            action_clients_list = get_action_client_names_and_types_by_node(
                node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
            )
            if any(self.action_name in client for client in action_clients_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                action_clients_group.add_row(row)

        # add the counts as descriptions
        action_servers_group.set_description_to_row_count()
        action_clients_group.set_description_to_row_count()
