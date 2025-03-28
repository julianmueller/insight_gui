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

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON

# class GraphPage(ContentPage):
#     def __init__(self, ros2_connector: ROS2Connector):
#         super().__init__("Graph")
#         self.graph_canvas = GraphCanvas(ros2_connector)
#         self.add(self.graph_canvas)


class GraphPage(Gtk.Fixed):
    __gtype_name__ = "GraphPage"

    def __init__(self, ros2_connector: ROS2Connector):
        super().__init__()
        self.ros2_connector = ros2_connector
        self.set_size_request(1000, 1000)  # Arbitrary size for now
        self.nodes = {}
        self.topics = {}
        self.connections = []

        self.refresh_graph()

    def refresh_graph(self):
        child1 = GraphChild("Node 1")
        self.put(child1, 50, 50)
        pass
        # self.clear_graph()
        # node_names = self.ros2_connector.get_node_names()

        # x, y = 50, 50
        # spacing = 150

        # for node_name in node_names:
        #     node_bin = self.create_node_bin(node_name)
        #     self.put(node_bin, x, y)
        #     self.nodes[node_name] = node_bin
        #     y += spacing

        # self.show_all()

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
        # for child in self.get_children():
        #     self.remove(child)
        # self.nodes.clear()
        # self.topics.clear()
        # self.connections.clear()
        pass


class GraphChild(Adw.Bin):
    __gtype_name__ = "GraphChild"

    def __init__(self, title: str):
        super().__init__()
        self.set_size_request(120, 70)
        frame = Gtk.Frame(css_classes=["card"])
        self.set_child(frame)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_top=4, margin_bottom=4, margin_start=4, margin_end=4
        )
        frame.set_child(box)

        label = Gtk.Label(label=title)
        label.set_xalign(0.5)
        box.append(label)

        button = Gtk.Button(label="Action")
        button.connect("clicked", self.on_button_clicked)
        box.append(button)

        # self.set_child(box)

    def on_button_clicked(self, button):
        print(f"Button clicked on: {self.get_name()}")
