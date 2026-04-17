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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import ActionRow, ParameterRow, ServiceRow, TopicRow
from insight_gui.models.node_item import NodeItem


class NodeInfoPage(ContentPage):
    __gtype_name__ = "NodeInfoPage"

    node = GObject.Property(type=NodeItem)

    def __init__(self, node: NodeItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        self.node = node

        super().set_title(f"Node {self.node.full_name}")
        self.detach_kwargs = {
            "node": self.node,
        }

        # Publishers
        self.publishers_group = self.pref_page.add_group(
            title="Publishers", placeholder_text="This node has no publishers."
        )

        # Subscribers
        self.subscribers_group = self.pref_page.add_group(
            title="Subscribers", placeholder_text="This node has no subscribers."
        )

        # Service Servers
        self.service_servers_group = self.pref_page.add_group(
            title="Service Servers", description="", placeholder_text="This node has no service servers."
        )

        # Service Clients
        self.service_clients_group = self.pref_page.add_group(
            title="Service Clients", placeholder_text="This node has no service clients."
        )

        # Action Servers
        self.action_servers_group = self.pref_page.add_group(
            title="Action Servers", placeholder_text="This node has no action servers."
        )

        # Action Clients
        self.action_clients_group = self.pref_page.add_group(
            title="Action Clients", placeholder_text="This node has no action clients."
        )

        # Parameters
        self.parameters_group = self.pref_page.add_group(
            title="Parameters", placeholder_text="This node has no parameters."
        )

    def refresh_bg(self) -> bool:
        # Publishers/Subscribers
        self.publisher_list = self.ros2_connector.collect_publishers_by_node(node=self.node)
        self.subscriber_list = self.ros2_connector.collect_subscribers_by_node(node=self.node)

        # Service Servers/Clients
        self.service_server_list = self.ros2_connector.collect_service_servers_by_node(node=self.node)
        self.service_client_list = self.ros2_connector.collect_service_clients_by_node(node=self.node)

        # Action Servers/Clients
        self.action_servers_list = self.ros2_connector.collect_action_servers_by_node(node=self.node)
        self.action_clients_list = self.ros2_connector.collect_action_clients_by_node(node=self.node)

        # Parameters
        self.parameters_list = self.ros2_connector.collect_parameters(node=self.node)

        return (
            len(self.publisher_list)
            + len(self.subscriber_list)
            + len(self.service_server_list)
            + len(self.service_client_list)
            + len(self.action_servers_list)
            + len(self.action_clients_list)
            + len(self.parameters_list)
        ) > 0

    def refresh_ui(self):
        self._add_item_rows_async(
            self.publishers_group,
            self.publisher_list,
            self._build_topic_row,
            batch_size=8,
            on_done=self.publishers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.subscribers_group,
            self.subscriber_list,
            self._build_topic_row,
            batch_size=8,
            on_done=self.subscribers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.service_servers_group,
            self.service_server_list,
            self._build_service_row,
            batch_size=8,
            on_done=self.service_servers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.service_clients_group,
            self.service_client_list,
            self._build_service_row,
            batch_size=8,
            on_done=self.service_clients_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.action_servers_group,
            self.action_servers_list,
            self._build_action_row,
            batch_size=8,
            on_done=self.action_servers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.action_clients_group,
            self.action_clients_list,
            self._build_action_row,
            batch_size=8,
            on_done=self.action_clients_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.parameters_group,
            self.parameters_list,
            self._build_parameter_row,
            batch_size=8,
            on_done=self.parameters_group.set_description_to_row_count,
        )

    def _build_topic_row(self, topic) -> TopicRow:
        return TopicRow(topic=topic, nav_view=self.nav_view)

    def _build_service_row(self, service) -> ServiceRow:
        return ServiceRow(service=service, nav_view=self.nav_view)

    def _build_action_row(self, action) -> ActionRow:
        return ActionRow(action=action, nav_view=self.nav_view)

    def _build_parameter_row(self, param) -> ParameterRow:
        return ParameterRow(parameter=param, nav_view=self.nav_view)

    def reset_ui(self):
        self.publishers_group.clear()
        self.subscribers_group.clear()
        self.service_servers_group.clear()
        self.service_clients_group.clear()
        self.action_servers_group.clear()
        self.action_clients_group.clear()
        self.parameters_group.clear()
