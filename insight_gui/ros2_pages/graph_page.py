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

from operator import itemgetter

from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.canvas_blocks import NodeBlock, TopicBlock, InterfaceBlock


class GraphPage(ContentPage):
    __gtype_name__ = "GraphPage"

    def __init__(self):
        super().__init__(searchable=False)
        super().set_title("Graph")
        self.content_stack.remove(self.pref_page)
        del self.pref_page

        self.scolled_window = Gtk.ScrolledWindow()
        self.content_stack.add_child(self.scolled_window)

        self.graph_canvas = Gtk.Fixed(width_request=1000, height_request=1000)
        self.scolled_window.set_child(self.graph_canvas)

        self.node_blocks = []
        self.topic_blocks = []
        self.interface_blocks = []
        self.connections = []

    # def on_refresh_blocking(self):
    #     return True

    def on_refresh_gui(self):
        self.clear_graph()
        self.add_node_block("node1", 50, 50)
        self.add_node_block("node2", 50, 150)

        self.add_topic_block("topic1", 250, 50)
        self.add_topic_block("topic2", 250, 150)

    def on_reset_gui(self):
        self.clear_graph()

    def add_node_block(self, name: str, x: int, y: int):
        node_block = NodeBlock(name)
        self.node_blocks.append(node_block)
        self.graph_canvas.put(node_block, x, y)

    def add_topic_block(self, name: str, x: int, y: int):
        topic_block = TopicBlock(name)
        self.topic_blocks.append(topic_block)
        self.graph_canvas.put(topic_block, x, y)

    def add_interface_block(self, name: str, x: int, y: int):
        interface_block = InterfaceBlock(name)
        self.interface_blocks.append(interface_block)
        self.graph_canvas.put(interface_block, x, y)

    def create_node_bin(self, name: str):
        bin_widget = Adw.Bin()
        label = Gtk.Label(label=name)
        bin_widget.set_child(label)
        bin_widget.set_size_request(100, 50)
        bin_widget.set_name(name)

        bin_widget.connect("button-press-event", self.on_node_clicked)
        return bin_widget

    def on_node_clicked(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            print(f"Node clicked: {widget.get_name()}")

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
