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
import networkx as nx
import matplotlib.pyplot as plt  # DEBUG
from operator import itemgetter

from ros2node.api import get_node_names
from ros2topic.api import get_topic_names_and_types

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

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

        # TODO add a "save btn" to save the graph as:
        # - an image
        # - a json
        # - a dot file
        # - a latex/tixz file
        # TODO make the graph viz adjustable, by exposing a selection for the different nx layouts and its params

        self.scolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.content_stack.add_child(self.scolled_window)

        self.overlay = Gtk.Overlay(
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
            hexpand=True,
            vexpand=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.scolled_window.set_child(self.overlay)

        self.drawing_area = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.drawing_area.set_draw_func(self.on_draw)
        self.overlay.set_child(self.drawing_area)

        self.fixed_canvas = Gtk.Fixed(hexpand=True, vexpand=True)
        self.overlay.add_overlay(self.fixed_canvas)

        self.nx_graph = nx.DiGraph()
        self.blocks = {}
        self.connections = []

    def refresh_bg(self):
        self.nx_graph.clear()

        # get all nodes and topics
        self.available_nodes = sorted(
            get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True), key=itemgetter(0)
        )
        self.available_topics = sorted(
            get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True), key=itemgetter(0)
        )

        # collect node and topic info
        for node_name, node_namespace, node_full_name in self.available_nodes:
            self.nx_graph.add_node(node_full_name, type="node")

            publishers = self.ros2_connector.node.get_publisher_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            for topic_name, topic_types in publishers:
                self.nx_graph.add_node(topic_name, type="topic")
                self.nx_graph.add_edge(node_full_name, topic_name, type="publisher")

            subscribers = self.ros2_connector.node.get_subscriber_names_and_types_by_node(
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
            self.connections.append((self.blocks[source], self.blocks[target]))
            # if data.get("type") == "publisher":
            #     self.connections.append((self.blocks[source], self.blocks[target]))
            # elif data.get("type") == "subscriber":
            #     self.connections.append((self.blocks[source], self.blocks[target]))

        # layout nodes
        try:
            from networkx.drawing.nx_agraph import graphviz_layout

            # Use Graphviz to layout the graph (left-to-right or top-down)
            pos = graphviz_layout(self.nx_graph, prog="dot")  # use prog='dot' for top-down or 'neato' for organic
        except ImportError:
            pos = nx.spring_layout(self.nx_graph, seed=42)

        # Normalize and scale coordinates to fit within canvas
        xs = [x for x, y in pos.values()]
        ys = [y for x, y in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        graph_width = max_x - min_x
        graph_height = max_y - min_y
        padding_x, padding_y = 300, 50
        self.set_canvas_size(graph_width + padding_x, graph_height + padding_y)

        for name, (x, y) in pos.items():
            canvas_x = x + padding_x / 2 - min_x
            canvas_y = y + padding_y / 2 - min_y

            if name in self.blocks.keys():
                block = self.blocks[name]
                block_size = block.get_preferred_size().minimum_size
                final_x = canvas_x - block_size.width / 2
                final_y = canvas_y - block_size.height / 2
                self.fixed_canvas.put(block, final_x, final_y)

        # draw all the connections as bezier curves
        self.drawing_area.queue_draw()

    def reset_ui(self):
        self.clear_graph_ui()

    def add_node_block(self, node_full_name: str):
        node_block = NodeBlock(node_full_name)
        node_block.connect("revealer-toggled", self._block_revealed)
        self.blocks[node_full_name] = node_block

    def add_topic_block(self, topic_name: str, topic_types: str | list[str] = None):
        if topic_types is None:
            for name, types in self.available_topics:
                if name == topic_name:
                    topic_types = types
                    break

        topic_block = TopicBlock(topic_name, topic_types)
        self.blocks[topic_name] = topic_block

    def add_interface_block(self, interface_name: str):
        interface_block = InterfaceBlock(interface_name)
        self.blocks[interface_name] = interface_block

    def on_draw(self, drawing_area, cr, width, height):
        for connection in self.connections:
            block1, block2 = connection
            x1, y1 = self._calc_block_attachment_position(block1, "east")
            x2, y2 = self._calc_block_attachment_position(block2, "west")
            self._draw_bezier(cr, x1, y1, 1, x2, y2, -1)

    def clear_graph_ui(self):
        for name in list(self.blocks.keys()):
            block = self.blocks.pop(name)
            self.fixed_canvas.remove(block)

        self.connections.clear()

    def set_canvas_size(self, width: int, height: int):
        self.drawing_area.set_content_width(int(width))
        self.drawing_area.set_content_height(int(height))
        self.fixed_canvas.set_size_request(int(width), int(height))

    def _block_revealed(self, block: BaseBlock, revealed: bool):
        if not revealed:
            return

        # reposition the block to the top
        x, y = self.fixed_canvas.get_child_position(block)
        self.fixed_canvas.remove(block)
        self.fixed_canvas.put(block, x, y)

    def _calc_block_attachment_position(self, block: BaseBlock, direction: str = "north"):
        pos_on_canvas = self.fixed_canvas.get_child_position(block)

        def _add_pos(p1: tuple, p2: tuple):
            return (p1[0] + p2[0], p1[1] + p2[1])

        if direction == "north":
            pos_on_canvas = _add_pos(pos_on_canvas, block.north_attachment_point)
        elif direction == "east":
            pos_on_canvas = _add_pos(pos_on_canvas, block.east_attachment_point)
        elif direction == "west":
            pos_on_canvas = _add_pos(pos_on_canvas, block.west_attachment_point)
        elif direction == "south":
            pos_on_canvas = _add_pos(pos_on_canvas, block.south_attachment_point)

        return pos_on_canvas

    def _draw_bezier(self, cr, x1: float, y1: float, dir1: int, x2: float, y2: float, dir2: int):
        # Compute control points
        control_point_offset = min(100, ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)

        def sign(_dir):  # check if plus or minus
            return 1 if _dir > 0 else -1

        # FIXME this could be a bit cleverer
        # control point next to the start point
        cx1, cy1 = (x1 + control_point_offset * sign(dir1), y1)
        cx2, cy2 = (x2 + control_point_offset * sign(dir2), y2)
        cx3, cy3 = None, None
        cx4, cy4 = None, None

        if dir1 < 0 and dir2 < 0 and abs(cx1 - cx2) < control_point_offset:
            cx3, cy3 = (cx1 if cx1 < cx2 else cx2, cy2 if cx1 < cx2 else cy1)

        elif dir1 > 0 and dir2 > 0 and abs(cx1 - cx2) < control_point_offset:
            cx3, cy3 = (cx2 if cx1 < cx2 else cx1, cy1 if cx1 < cx2 else cy2)

        # elif sign(dir1) != sign(dir2):
        #     cx3, cy3 = (cx2 if cx1 < cx2 else cx1, cy1 if cx1 < cx2 else cy2)
        #     cx4, cy4 = ()

        # control point next to the end point

        # Draw the bezier curve
        if Adw.StyleManager.get_default().get_dark():
            cr.set_source_rgb(1, 1, 1)  # Set color to white
        else:
            cr.set_source_rgb(0, 0, 0)  # Set color to white

        cr.set_line_width(2)
        cr.move_to(x1, y1)  # Move to the start point

        if cx4 is not None:
            cr.curve_to(cx1, cy1, cx2, cy2, cx3, cy3, cx4, cy4, x2, y2)  # Bezier curve
        elif cx3 is not None:
            cr.curve_to(cx1, cy1, cx2, cy2, cx3, cy3, x2, y2)
        else:
            cr.curve_to(cx1, cy1, cx2, cy2, x2, y2)

        # draw circles at the ends
        cr.stroke()
        cr.arc(x1, y1, 5, 0.0, 2 * math.pi)
        cr.arc(x2, y2, 5, 0.0, 2 * math.pi)
        cr.fill()

    # def _draw_arrow(self, cr, x1, y1, x2, y2, arrow_size=10):
    #     # Arrowhead points
    #     left = (
    #         x2 - arrow_size * math.cos(math.pi / 6),
    #         y2 - arrow_size * math.sin(math.pi / 6),
    #     )
    #     right = (
    #         x2 - arrow_size * math.cos(math.pi / 6),
    #         y2 - arrow_size * math.sin(math.pi / 6),
    #     )

    #     # Draw arrowhead
    #     cr.stroke()
    #     cr.move_to(x2, y2)
    #     cr.line_to(*left)
    #     cr.line_to(*right)
    #     cr.close_path()
    #     cr.fill()
