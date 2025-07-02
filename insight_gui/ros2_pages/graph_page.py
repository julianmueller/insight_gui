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

import networkx as nx
from operator import itemgetter

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

        # self.clear_btn = super().add_bottom_right_btn(
        #     label="Clear", icon_name="trash-symbolic", func=self.on_clear_text, css_classes=["destructive-action"]
        # )

        # directed graph to store the ros2 graph
        self.nx_graph = nx.DiGraph()

    def refresh_bg(self):
        self.nx_graph.clear()

        # get all nodes, topics, services, actions
        self.available_nodes = self.ros2_connector.get_available_nodes()
        # self.available_topics = self.ros2_connector.get_available_topics()
        # self.available_services = self.ros2_connector.get_available_services()
        # self.available_actions = self.ros2_connector.get_available_actions()

        # collect node and topic info
        for node_name, node_namespace, node_full_name in self.available_nodes:
            self.nx_graph.add_node(
                node_full_name,  # TODO create unique identifier for all blocks, pass them to the block contructor and use them for the edges etc
                type="node",
                label=node_full_name,
                args={"node_full_name": node_full_name},
            )

            # Add topics
            publishers = self.ros2_connector.get_publishers_by_node(node_name=node_name, node_namespace=node_namespace)
            for topic_name, topic_types in publishers:
                self.nx_graph.add_node(
                    topic_name,
                    type="topic",
                    label=topic_name,
                    args={"topic_name": topic_name, "topic_types": topic_types},
                )
                self.nx_graph.add_edge(node_full_name, topic_name, type="publisher", label="")

            subscribers = self.ros2_connector.get_subscribers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for topic_name, topic_types in subscribers:
                self.nx_graph.add_node(
                    topic_name,
                    type="topic",
                    label=topic_name,
                    args={"topic_name": topic_name, "topic_types": topic_types},
                )
                self.nx_graph.add_edge(topic_name, node_full_name, type="subscriber", label="")

            # Add service servers
            service_servers = self.ros2_connector.get_service_servers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for service_name, service_types in service_servers:
                self.nx_graph.add_node(
                    service_name,
                    type="service",
                    label=service_name,
                    args={"service_name": service_name, "service_types": service_types},
                )
                self.nx_graph.add_edge(node_full_name, service_name, type="service_server", label="")

            # Add service clients
            service_clients = self.ros2_connector.get_service_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for service_name, service_types in service_clients:
                self.nx_graph.add_node(
                    service_name,
                    type="service",
                    label=service_name,
                    args={"service_name": service_name, "service_types": service_types},
                )
                self.nx_graph.add_edge(service_name, node_full_name, type="service_clients", label="")

            # Add actions servers
            action_servers = self.ros2_connector.get_action_servers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for action_name, action_types in action_servers:
                self.nx_graph.add_node(
                    action_name,
                    type="action",
                    label=action_name,
                    args={"action_name": action_name, "action_types": action_types},
                )
                self.nx_graph.add_edge(node_full_name, action_name, type="action_server", label="")

            # Add actions clients
            action_clients = self.ros2_connector.get_action_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for action_name, action_types in action_clients:
                self.nx_graph.add_node(
                    action_name,
                    type="action",
                    label=action_name,
                    args={"action_name": action_name, "action_types": action_types},
                )
                self.nx_graph.add_edge(action_name, node_full_name, type="action_clients", label="")

            # Add parameters
            parameters = self.ros2_connector.get_parameters_by_node(node_name=node_name)
            for parameter_name in parameters:
                param_full_name = f"{node_full_name}/{parameter_name}"
                self.nx_graph.add_node(
                    param_full_name,
                    type="parameter",
                    label=parameter_name,
                    args={"node_name": node_name, "parameter_name": parameter_name, "param_full_name": param_full_name},
                )
                self.nx_graph.add_edge(node_full_name, param_full_name, type="parameter", label="")

        return len(self.available_nodes) > 0

    def refresh_ui(self):
        # Configure graph attributes for better Graphviz layout
        self.nx_graph.graph.update(
            {
                "rankdir": "LR",  # Left to right layout like rqt_graph
                "ranksep": "1.5",  # Increased spacing between ranks (columns)
                "nodesep": "0.8",  # Increased spacing between nodes in same rank
                "splines": "ortho",  # Orthogonal edge routing to avoid overlaps
                "overlap": "false",  # Prevent node overlaps
                "concentrate": "true",  # Merge multi-edges
                "compound": "true",  # Allow edges between clusters
                "newrank": "true",  # Use new ranking algorithm
                "pack": "true",  # Pack connected components tightly
                "packmode": "graph",  # Pack mode for better layout
                "sep": "+20,20",  # Minimum separation between components
            }
        )

        # Set node attributes based on type for better Graphviz layout
        for nx_node, data in self.nx_graph.nodes(data=True):
            if data.get("type") == "node":
                # Nodes are rectangular and should be arranged in columns
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#E3F2FD",
                        "color": "#1976D2",
                        "fontname": "Arial",
                        "fontsize": "10",
                        "width": "2.0",
                        "height": "1.0",
                        "fixedsize": "true",
                    }
                )
                self.add_node_block(**data.get("args"))
            elif data.get("type") == "topic":
                # Topics are elliptical and should be in middle columns
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "ellipse",
                        "style": "filled",
                        "fillcolor": "#FFF3E0",
                        "color": "#F57C00",
                        "fontname": "Arial",
                        "fontsize": "9",
                        "width": "1.8",
                        "height": "0.8",
                        "fixedsize": "true",
                    }
                )
                self.add_topic_block(**data.get("args"))
            elif data.get("type") == "service_server":
                # Services are rectangular with green color
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#E8F5E8",
                        "color": "#4CAF50",
                        "fontname": "Arial",
                        "fontsize": "8",
                        "width": "3.0",
                        "height": "1.2",
                        "fixedsize": "true",
                    }
                )
                self.add_service_block(**data.get("args"))
            elif data.get("type") == "service_client":
                # Services are rectangular with green color
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#E8F5E8",
                        "color": "#4CAF50",
                        "fontname": "Arial",
                        "fontsize": "8",
                        "width": "3.0",
                        "height": "1.2",
                        "fixedsize": "true",
                    }
                )
                self.add_service_block(**data.get("args"))
            elif data.get("type") == "action_server":
                # Actions are rectangular with red color
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#FFEBEE",
                        "color": "#F44336",
                        "fontname": "Arial",
                        "fontsize": "8",
                        "width": "3.0",
                        "height": "1.2",
                        "fixedsize": "true",
                    }
                )
                self.add_action_block(**data.get("args"))
            elif data.get("type") == "action_client":
                # Actions are rectangular with red color
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#FFEBEE",
                        "color": "#F44336",
                        "fontname": "Arial",
                        "fontsize": "8",
                        "width": "3.0",
                        "height": "1.2",
                        "fixedsize": "true",
                    }
                )
                self.add_action_block(**data.get("args"))
            elif data.get("type") == "parameter":
                # Parameters are small rectangles with purple color
                self.nx_graph.nodes[nx_node].update(
                    {
                        "shape": "box",
                        "style": "rounded,filled",
                        "fillcolor": "#F3E5F5",
                        "color": "#9C27B0",
                        "fontname": "Arial",
                        "fontsize": "8",
                        "width": "1.0",
                        "height": "0.5",
                        "fixedsize": "true",
                    }
                )
                self.add_parameter_block(**data.get("args"))

        # Set edge attributes for better routing
        for source, target, data in self.nx_graph.edges(data=True):
            self.nx_graph.edges[source, target].update(
                {"color": "#666666", "penwidth": "1.5", "arrowsize": "0.8", "arrowhead": "normal"}
            )
            self.canvas.add_connection(self.canvas.get_block(source), self.canvas.get_block(target))

        # Use improved layout algorithm
        self.canvas.layout_from_graph(self.nx_graph)

        self.show_banner("The Graph page is still experimental")  # DEBUG

    def reset_ui(self):
        self.canvas.clear()

    def add_node_block(self, node_full_name: str):
        node_block = NodeBlock(node_full_name)
        self.canvas.add_block(node_block)

    def add_topic_block(self, topic_name: str, topic_types: str | list[str] = None):
        topic_block = TopicBlock(topic_name, topic_types)
        self.canvas.add_block(topic_block)

    def add_service_block(self, service_name: str, service_types: str | list[str]):
        service_block = ServiceBlock(service_name, service_types)
        self.canvas.add_block(service_block)

    def add_action_block(self, action_name: str, action_types: str | list[str]):
        action_block = ActionBlock(action_name, action_types)
        self.canvas.add_block(action_block)

    def add_parameter_block(self, node_name: str, parameter_name: str, param_full_name: str):
        # Extract just the parameter name from the full path for display
        param_display_name = parameter_name.split("/")[-1]  # TODO
        parameter_block = ParameterBlock(node_name, param_full_name)
        self.canvas.add_block(parameter_block)

    # def add_interface_block(self, interface_name: str):
    #     interface_block = InterfaceBlock(interface_name)
    #     self.canvas.add_block(interface_block, interface_name)
