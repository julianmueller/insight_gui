# =============================================================================
# node_info_page.py
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
from ros2node.api import parse_node_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.param_edit_page import ParamEditPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class NodeInfoPage(ContentPage):
    __gtype_name__ = "NodeInfoPage"

    def __init__(self, node_full_name: str, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Node {node_full_name}")

        self.node_full_name = node_full_name
        self.detach_kwargs = {
            "node_full_name": node_full_name,
        }

        parsed_name = parse_node_name(node_full_name)
        self.node_name = parsed_name.name
        self.node_namespace = parsed_name.namespace

        # Publishers
        self.publishers_group = self.pref_page.add_group(title="Publishers", empty_group_text="Node has no publishers")

        # Subscribers
        self.subscribers_group = self.pref_page.add_group(
            title="Subscribers", empty_group_text="Node has no subscribers"
        )

        # Service Servers
        self.service_servers_group = self.pref_page.add_group(
            title="Service Servers", description="", empty_group_text="Node has no service servers"
        )

        # Service Clients
        self.service_clients_group = self.pref_page.add_group(
            title="Service Clients", empty_group_text="Node has no service clients"
        )

        # Action Servers
        self.action_servers_group = self.pref_page.add_group(
            title="Action Servers", empty_group_text="Node has no action servers"
        )

        # Action Clients
        self.action_clients_group = self.pref_page.add_group(
            title="Action Clients", empty_group_text="Node has no action clients"
        )

        # Parameters
        self.parameters_group = self.pref_page.add_group(title="Parameters", empty_group_text="Node has no parameters")

    def refresh_bg(self) -> bool:
        # Publishers
        self.publisher_list = self.ros2_connector.get_publishers_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Subscribers
        self.subscriber_list = self.ros2_connector.get_subscribers_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Service Servers
        self.service_server_list = self.ros2_connector.get_service_servers_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Service Clients
        self.service_client_list = self.ros2_connector.get_service_clients_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Action Servers
        self.action_servers_list = self.ros2_connector.get_action_servers_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Action Clients
        self.action_clients_list = self.ros2_connector.get_action_clients_by_node(
            node_name=self.node_name, node_namespace=self.node_namespace
        )

        # Parameters
        self.parameter_list = self.ros2_connector.get_parameters_by_node(node_name=self.node_name)

        return (
            len(self.publisher_list)
            + len(self.subscriber_list)
            + len(self.service_server_list)
            + len(self.service_client_list)
            + len(self.action_servers_list)
            + len(self.action_clients_list)
            + len(self.parameter_list)
            > 0
        )

    def refresh_ui(self):
        # TODO this is ugly
        from insight_gui.ros2_pages.topic_info_page import TopicInfoPage
        from insight_gui.ros2_pages.service_info_page import ServiceInfoPage
        from insight_gui.ros2_pages.action_info_page import ActionInfoPage

        # Publishers
        for topic_name, topic_types in sorted(self.publisher_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                subpage_kwargs={"topic_name": topic_name, "topic_types": topic_types},
            )
            self.publishers_group.add_row(row)
        self.publishers_group.set_description_to_row_count()

        # Subscribers
        for topic_name, topic_types in sorted(self.subscriber_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                subpage_kwargs={"topic_name": topic_name, "topic_types": topic_types},
            )
            self.subscribers_group.add_row(row)
        self.subscribers_group.set_description_to_row_count()

        # Service Servers
        for service_name, service_types in sorted(self.service_server_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                subpage_kwargs={"service_name": service_name, "service_types": service_types},
            )
            self.service_servers_group.add_row(row)
        self.service_servers_group.set_description_to_row_count()

        # Service Clients
        for service_name, service_types in sorted(self.service_client_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                subpage_kwargs={"service_name": service_name, "service_types": service_types},
            )
            self.service_clients_group.add_row(row)
        self.service_clients_group.set_description_to_row_count()

        # Action Servers
        for action_name, action_types in sorted(self.action_servers_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={"action_name": action_name, "action_types": action_types},
            )
            self.action_servers_group.add_row(row)
        self.action_servers_group.set_description_to_row_count()

        # Action Clients
        for action_name, action_types in sorted(self.action_clients_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={"action_name": action_name, "action_types": action_types},
            )
            self.action_clients_group.add_row(row)
        self.action_clients_group.set_description_to_row_count()

        # Parameters
        for param_name in sorted(self.parameter_list):
            param_info = self.ros2_connector.get_parameter_info(node_name=self.node_name, parameter_name=param_name)
            param_type = param_info["type"]
            param_value = param_info["value"]
            param_read_only = param_info["read_only"]

            row = PrefRow(title=param_name, subtitle=f"{param_type}: {param_value}")
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ParamEditPage,
                subpage_kwargs={"node_name": self.node_name, "param_name": param_name},
            )
            if param_read_only:
                row.add_prefix_icon(icon_name="lock-symbolic", tooltip_text="Read-only parameter")

            self.parameters_group.add_row(row)
        self.parameters_group.set_description_to_row_count()

    def reset_ui(self):
        self.publishers_group.clear()
        self.subscribers_group.clear()
        self.service_servers_group.clear()
        self.service_clients_group.clear()
        self.action_servers_group.clear()
        self.action_clients_group.clear()
        self.parameters_group.clear()
