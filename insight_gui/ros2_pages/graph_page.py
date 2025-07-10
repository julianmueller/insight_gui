# =============================================================================
# graph_page.py
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
from insight_gui.widgets.canvas import Canvas
from insight_gui.widgets.canvas_blocks import (
    NodeBlock,
    TopicBlock,
    ServiceBlock,
    ActionBlock,
    ParameterBlock,
)


class GraphPage(ContentPage):
    __gtype_name__ = "GraphPage"

    def __init__(self):
        super().__init__(searchable=False)
        super().set_title("Graph")
        super().set_refresh_fail_text("No nodes found. Refresh to try again.")

        self.content_stack.remove(self.pref_page)
        del self.pref_page

        # TODO add a "save btn" to save the graph as:
        # - an image
        # - a json
        # - a dot file
        # - a latex/tixz file
        # TODO make the graph viz adjustable, by exposing a selection for the different nx layouts and its params

        # Create canvas
        self.canvas = Canvas()
        self.content_stack.add_child(self.canvas)

    def refresh_bg(self):
        # Clear previous data
        self.canvas.clear()

        # get all nodes, topics, services, actions
        self.available_nodes = self.ros2_connector.get_available_nodes()
        self.available_publishers = {}
        self.available_subscribers = {}
        self.available_service_servers = {}
        self.available_service_clients = {}
        self.available_action_servers = {}
        self.available_action_clients = {}
        self.available_parameters = {}

        # collect node and topic info
        for node_name, node_namespace, node_full_name in self.available_nodes:
            # Add publishers to the node
            self.available_publishers[node_full_name] = self.ros2_connector.get_publishers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add subscribers to the node
            self.available_subscribers[node_full_name] = self.ros2_connector.get_subscribers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add service servers to the node
            self.available_service_servers[node_full_name] = self.ros2_connector.get_service_servers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add service clients to the node
            self.available_service_clients[node_full_name] = self.ros2_connector.get_service_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add actions servers to the node
            self.available_action_servers[node_full_name] = self.ros2_connector.get_action_servers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add actions clients to the node
            self.available_action_clients[node_full_name] = self.ros2_connector.get_action_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )

            # Add parameters to the node
            self.available_parameters[node_full_name] = self.ros2_connector.get_parameters_by_node(node_name=node_name)

        # TODO also add other topics etc here, that do not belong to any nodes

        return len(self.available_nodes) > 0

    def refresh_ui(self):
        # collect node and topic info
        for node_name, node_namespace, node_full_name in self.available_nodes:
            # Add node using unified interface
            node_id = self.canvas.add_block(
                block_class=NodeBlock,
                block_args={"node_name": node_name, "node_namespace": node_namespace, "node_full_name": node_full_name},
            )

            # Add publishers to the node
            for topic_name, topic_types in self.available_publishers[node_full_name]:
                topic_id = self.canvas.add_block(
                    block_class=TopicBlock,
                    block_args={"topic_name": topic_name, "topic_types": topic_types},
                )
                self.canvas.connect_blocks(node_id, topic_id)

            # Add subscribers to the node
            for topic_name, topic_types in self.available_subscribers[node_full_name]:
                topic_id = self.canvas.add_block(
                    block_class=TopicBlock,
                    block_args={"topic_name": topic_name, "topic_types": topic_types},
                )
                self.canvas.connect_blocks(topic_id, node_id)

            # Add service servers to the node
            for service_name, service_types in self.available_service_servers[node_full_name]:
                service_id = self.canvas.add_block(
                    block_class=ServiceBlock,
                    block_args={
                        "service_name": service_name,
                        "service_types": service_types,
                    },
                )
                self.canvas.connect_blocks(node_id, service_id)

            # Add service clients to the node
            for service_name, service_types in self.available_service_clients[node_full_name]:
                service_id = self.canvas.add_block(
                    block_class=ServiceBlock,
                    block_args={
                        "service_name": service_name,
                        "service_types": service_types,
                    },
                )
                self.canvas.connect_blocks(service_id, node_id)

            # Add actions servers to the node
            for action_name, action_types in self.available_action_servers[node_full_name]:
                action_id = self.canvas.add_block(
                    block_class=ActionBlock,
                    block_args={
                        "action_name": action_name,
                        "action_types": action_types,
                    },
                )
                self.canvas.connect_blocks(node_id, action_id)

            # Add actions clients to the node
            for action_name, action_types in self.available_action_clients[node_full_name]:
                action_id = self.canvas.add_block(
                    block_class=ActionBlock,
                    block_args={
                        "action_name": action_name,
                        "action_types": action_types,
                    },
                )
                self.canvas.connect_blocks(action_id, node_id)

            # Add parameters to the node
            for parameter_name in self.available_parameters[node_full_name]:
                # param_full_name = f"{node_full_name}/{parameter_name}"
                param_id = self.canvas.add_block(
                    block_class=ParameterBlock,
                    block_args={
                        "parameter_name": parameter_name,
                        "node_full_name": node_full_name,
                    },
                )
                self.canvas.connect_blocks(node_id, param_id)

        self.show_banner("The Graph page is still experimental")  # DEBUG
        self.canvas.calculate_layout()

    def reset_ui(self):
        # self.canvas.clear()
        pass
