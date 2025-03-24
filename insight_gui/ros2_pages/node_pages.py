# =============================================================================
# node_pages.py
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

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node
from ros2node.api import _is_hidden_name, get_node_names
from ros2param.api import (
    call_list_parameters,
    call_get_parameters,
    call_describe_parameters,
    get_value,
    get_parameter_type_string,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.edit_param_dialog import EditParamDialog
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class NodeListPage(ContentPage):
    __gtype_name__ = "NodeListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Nodes")
        super().set_search_entry_placeholder_text("Search for nodes")

    def on_realize(self, *args):
        super().on_realize(*args)

        self.node_list_group = self.pref_page.add_group(empty_group_text="Refresh to show nodes")

    def on_refresh_blocking(self) -> bool:
        self.available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        if len(self.available_nodes) == 0:
            self.node_list_group.set_empty_group_text("No nodes found. Refresh to try again.")
            return False
        return True

    def on_refresh_gui(self):
        rows = []
        for node_name, node_namespace, node_full_name in sorted(self.available_nodes, key=itemgetter(0)):
            row = PrefRow(title=node_name, subtitle=node_full_name)
            if _is_hidden_name(node_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=NodeInfoPage,
                subpage_kwargs={
                    "node_name": node_name,
                    "node_namespace": node_namespace,
                    "node_full_name": node_full_name,
                },
            )
            rows.append(row)

        self.node_list_group.add_rows_idle(rows)

    def on_clear_gui(self):
        self.node_list_group.clear()


class NodeInfoPage(ContentPage):
    __gtype_name__ = "NodeInfoPage"

    def __init__(self, node_name: str, node_namespace: str, node_full_name: str, **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Node <{node_full_name}>")

        self.node_name = node_name
        self.node_namespace = node_namespace
        self.node_full_name = node_full_name
        self.detach_kwargs = {
            "node_name": node_name,
            "node_namespace": node_namespace,
            "node_full_name": node_full_name,
        }

    def on_realize(self, *args):
        super().on_realize(*args)

        # Imports here, to prevent circular imports # TODO find a nicer way?
        from insight_gui.ros2_pages.topic_pages import TopicInfoPage
        from insight_gui.ros2_pages.service_pages import ServiceInfoPage
        from insight_gui.ros2_pages.action_pages import ActionInfoPage

        # Publishers
        publishers_group = self.pref_page.add_group(title="Publishers", empty_group_text="Node has no publishers")

        # publisher_list = get_publisher_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        publisher_list = self.ros2_connector.node.get_publisher_names_and_types_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )
        for topic_name, topic_types in sorted(publisher_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                subpage_kwargs={
                    "topic_name": topic_name,
                    "topic_types": topic_types,
                },
            )
            publishers_group.add_row(row)
        publishers_group.set_description_to_row_count()

        # Subscribers
        subscribers_group = self.pref_page.add_group(title="Subscribers", empty_group_text="Node has no subscribers")

        # subscriber_list = get_subscriber_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        subscriber_list = self.ros2_connector.node.get_subscriber_names_and_types_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )
        for topic_name, topic_types in sorted(subscriber_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                subpage_kwargs={
                    "topic_name": topic_name,
                    "topic_types": topic_types,
                },
            )
            subscribers_group.add_row(row)
        subscribers_group.set_description_to_row_count()

        # Service Servers
        service_servers_group = self.pref_page.add_group(
            title="Service Servers", description="", empty_group_text="Node has no service servers"
        )

        # service_servers_list = get_service_server_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        service_server_list = self.ros2_connector.node.get_service_names_and_types_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )
        for service_name, service_types in sorted(service_server_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                subpage_kwargs={
                    "service_name": service_name,
                    "service_types": service_types,
                },
            )
            service_servers_group.add_row(row)
        service_servers_group.set_description_to_row_count()

        # Service Clients
        service_clients_group = self.pref_page.add_group(
            title="Service Clients", empty_group_text="Node has no service clients"
        )

        # service_clients_list = get_service_client_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        service_client_list = self.ros2_connector.node.get_client_names_and_types_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )
        for service_name, service_types in sorted(service_client_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                subpage_kwargs={
                    "service_name": service_name,
                    "service_types": service_types,
                },
            )
            service_clients_group.add_row(row)
        service_clients_group.set_description_to_row_count()

        # Action Servers
        action_servers_group = self.pref_page.add_group(
            title="Action Servers", empty_group_text="Node has no action servers"
        )

        action_servers_list = get_action_server_names_and_types_by_node(
            node=self.ros2_connector.node, remote_node_name=self.node_name, remote_node_namespace=self.node_namespace
        )
        for action_name, action_types in sorted(action_servers_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={
                    "action_name": action_name,
                    "action_types": action_types,
                },
            )
            action_servers_group.add_row(row)
        action_servers_group.set_description_to_row_count()

        # Action Clients
        action_clients_group = self.pref_page.add_group(
            title="Action Clients", empty_group_text="Node has no action clients"
        )

        action_clients_list = get_action_client_names_and_types_by_node(
            node=self.ros2_connector.node, remote_node_name=self.node_name, remote_node_namespace=self.node_namespace
        )
        for action_name, action_types in sorted(action_clients_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={
                    "action_name": action_name,
                    "action_types": action_types,
                },
            )
            action_clients_group.add_row(row)
        action_clients_group.set_description_to_row_count()

        # Parameters
        parameters_group = self.pref_page.add_group(title="Parameters", empty_group_text="Node has no parameters")
        future = call_list_parameters(node=self.ros2_connector.node, node_name=self.node_name)
        if future is not None:
            parameter_list = future.result().result.names
            for param_name in sorted(parameter_list):
                param_type = get_parameter_type_string(
                    call_describe_parameters(
                        node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[param_name]
                    )
                    .descriptors[0]
                    .type
                )
                param_value = get_value(
                    parameter_value=call_get_parameters(
                        node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[param_name]
                    ).values[0]
                )
                row = PrefRow(title=param_name, subtitle=f"{param_type}: {param_value}")
                row.add_suffix_btn(
                    icon_name="document-edit-symbolic",
                    tooltip_text="Edit",
                    func=self.on_edit_param,
                    func_kwargs={"node_name": self.node_name, "param_name": param_name},
                )
                parameters_group.add_row(row)
        parameters_group.set_description_to_row_count()

    def on_edit_param(self, *args, node_name: str, param_name: str):
        EditParamDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
