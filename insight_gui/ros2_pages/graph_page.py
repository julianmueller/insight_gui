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
from insight_gui.widgets.canvas_blocks import NodeBlock, TopicBlock, InterfaceBlock

# look into: https://github.com/ros-visualization/rqt_graph/tree/jazzy


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

        self.canvas = Canvas()
        self.content_stack.add_child(self.canvas)

        self.nx_graph = nx.DiGraph()

    def refresh_bg(self):
        self.nx_graph.clear()

        # get all nodes and topics
        self.available_nodes = self.ros2_connector.get_available_nodes()
        self.available_topics = self.ros2_connector.get_available_topics()

        # collect node and topic info
        for node_name, node_namespace, node_full_name in self.available_nodes:
            self.nx_graph.add_node(node_full_name, type="node")

            publishers = self.ros2_connector.get_publishers_by_node(node_name=node_name, node_namespace=node_namespace)
            for topic_name, topic_types in publishers:
                self.nx_graph.add_node(topic_name, type="topic")
                self.nx_graph.add_edge(node_full_name, topic_name, type="publisher")

            subscribers = self.ros2_connector.get_subscribers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for topic_name, topic_types in subscribers:
                self.nx_graph.add_node(topic_name, type="topic")
                self.nx_graph.add_edge(topic_name, node_full_name, type="subscriber")

            # services = self.ros2_connector.node.get_service_names_and_types_by_node(
            #     node_name=node_name, node_namespace=node_namespace
            # )
            # for service_name, service_types in services:
            #     self.nx_graph.add_node(service_name, type="service")
            #     self.nx_graph.add_edge(node_full_name, service_name, type="service")

        # # collect topic info
        # all_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))

        # for topic_name, topic_types in all_topics:
        #     self.nx_graph.add_node(topic_name, type="topic")

        #     # Publishers (Node → Topic)
        #     pub_infos = self.ros2_connector.node.get_publishers_info_by_topic(topic_name)
        #     for pub in pub_infos:
        #         pub_node = f"{pub.node_name}" if pub.node_namespace == "/" else f"{pub.node_namespace}/{pub.node_name}"
        #         graph["connections"].append((pub_node, topic_name))

        #     # Subscribers (Topic → Node)
        #     sub_infos = node.get_subscriptions_info_by_topic(topic_name)
        #     for sub in sub_infos:
        #         sub_node = f"{sub.node_name}" if sub.node_namespace == "/" else f"{sub.node_namespace}/{sub.node_name}"
        #         graph["connections"].append((topic_name, sub_node))

        # self.plot_graph()
        return len(self.available_nodes) + len(self.available_topics) > 0

    def refresh_ui(self):
        self.nx_graph.graph["graph"] = {
            "rankdir": "LR",
            "nodesep": "0.5",  # Horizontal spacing between nodes (default ~0.25)
            "ranksep": "2.5",  # Vertical spacing between layers (default ~0.5–1.0)
        }
        for node, data in self.nx_graph.nodes(data=True):
            if data.get("type") == "node":
                self.add_node_block(node)
            elif data.get("type") == "topic":
                self.add_topic_block(node)

        for source, target, data in self.nx_graph.edges(data=True):
            self.canvas.add_connection(self.canvas.get_block(source), self.canvas.get_block(target))
            # if data.get("type") == "publisher":
            #     self.connections.append((self.blocks[source], self.blocks[target]))
            # elif data.get("type") == "subscriber":
            #     self.connections.append((self.blocks[source], self.blocks[target]))

        # layout nodes
        self.canvas.layout_from_graph(self.nx_graph)

        self.show_banner("The Graph page is still experimental")  # DEBUG

    def reset_ui(self):
        self.canvas.clear()

    def add_node_block(self, node_full_name: str):
        node_block = NodeBlock(node_full_name)
        self.canvas.add_block(node_block, node_full_name)

    def add_topic_block(self, topic_name: str, topic_types: str | list[str] = None):
        if topic_types is None:
            for name, types in self.available_topics:
                if name == topic_name:
                    topic_types = types
                    break

        topic_block = TopicBlock(topic_name, topic_types)
        self.canvas.add_block(topic_block, topic_name)

    def add_interface_block(self, interface_name: str):
        interface_block = InterfaceBlock(interface_name)
        self.canvas.add_block(interface_block, interface_name)
