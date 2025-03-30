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

import math
import random
from operator import itemgetter

from ros2node.api import _is_hidden_name, get_node_names
from ros2topic.api import get_topic_names_and_types

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.canvas_blocks import BaseBlock, NodeBlock, TopicBlock, InterfaceBlock

# look into: https://github.com/ros-visualization/rqt_graph/tree/jazzy


class GraphPage(ContentPage):
    __gtype_name__ = "GraphPage"

    def __init__(self):
        super().__init__(searchable=False)
        super().set_title("Graph")
        self.content_stack.remove(self.pref_page)
        del self.pref_page

        self.scolled_window = Gtk.ScrolledWindow()
        self.content_stack.add_child(self.scolled_window)

        self.canvas_width = 1000
        self.canvas_height = 1000

        self.graph_canvas = Gtk.Fixed(width_request=self.canvas_width, height_request=self.canvas_height)
        self.scolled_window.set_child(self.graph_canvas)

        self.node_blocks = []
        self.topic_blocks = []
        self.interface_blocks = []
        self.connections = []

    def on_refresh_blocking(self):
        self.available_nodes = sorted(
            get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True), key=itemgetter(0)
        )
        self.available_topics = sorted(
            get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True), key=itemgetter(0)
        )
        return len(self.available_nodes) + len(self.available_topics) > 0

    def on_refresh_gui(self):
        self.clear_graph()
        y_index = 1  # TODO dummy

        for node_name, node_namespace, node_full_name in self.available_nodes:
            self.add_node_block(node_full_name, 50, y_index * 50)
            y_index += 1

        for topic_name, topic_types in self.available_topics:
            self.add_topic_block(topic_name, topic_types, 50, y_index * 50)
            y_index += 1

        # self._layout_nodes()

    def on_reset_gui(self):
        self.clear_graph()

    def add_node_block(self, node_full_name: str, x: int = -1, y: int = -1):
        node_block = NodeBlock(node_full_name)
        self.node_blocks.append(node_block)
        self.add_block(node_block, x, y)

    def add_topic_block(self, topic_name: str, topic_types: str | list[str], x: int = -1, y: int = -1):
        topic_block = TopicBlock(topic_name, topic_types)
        self.topic_blocks.append(topic_block)
        self.add_block(topic_block, x, y)

    def add_interface_block(self, name: str, x: int = -1, y: int = -1):
        interface_block = InterfaceBlock(name)
        self.interface_blocks.append(interface_block)
        self.add_block(interface_block, x, y)

    def add_block(self, block: BaseBlock, x: int = -1, y: int = -1):
        if x == -1:
            x = random.uniform(0, self.canvas_width)
        if y == -1:
            y = random.uniform(0, self.canvas_height)

        self.graph_canvas.put(block, *self._calc_block_position(block, x, y))

    def _calc_block_position(self, block: BaseBlock, x: int, y: int, margin: int = 12):
        max_x = max(0, self.canvas_width - block.width - margin)
        max_y = max(0, self.canvas_height - block.height - margin)

        clamped_x = min(max(x, margin), max_x)
        clamped_y = min(max(y, margin), max_y)

        return clamped_x, clamped_y

    def _layout_nodes(self, iterations: int = 100):
        """Basic force-directed layout algorithm to position nodes without overlap."""
        for _ in range(iterations):
            forces = {node: [0, 0] for node in self.nodes}

            # Repulsion between all nodes
            for node_a, pos_a in self.positions.items():
                for node_b, pos_b in self.positions.items():
                    if node_a == node_b:
                        continue
                    dx = pos_a[0] - pos_b[0]
                    dy = pos_a[1] - pos_b[1]
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance < 1:
                        distance = 1
                    repulsive_force = 1000 / (distance * distance)

                    forces[node_a][0] += (dx / distance) * repulsive_force
                    forces[node_a][1] += (dy / distance) * repulsive_force

            # Apply forces
            for node, force in forces.items():
                self.positions[node][0] += force[0] * 0.01
                self.positions[node][1] += force[1] * 0.01

                # Keep nodes within the bounds
                self.positions[node][0] = min(max(self.positions[node][0], 0), 980)
                self.positions[node][1] = min(max(self.positions[node][1], 0), 980)

                # Update widget position
                self.move(self.nodes[node], *self.positions[node])

    def clear_graph(self):
        for node_block in reversed(self.node_blocks):
            self.graph_canvas.remove(node_block)
            self.node_blocks.remove(node_block)

        for topic_block in reversed(self.topic_blocks):
            self.graph_canvas.remove(topic_block)
            self.topic_blocks.remove(topic_block)

        for interface_block in reversed(self.interface_blocks):
            self.graph_canvas.remove(interface_block)
            self.interface_blocks.remove(interface_block)
