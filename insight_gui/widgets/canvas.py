# =============================================================================
# canvas.py
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
from networkx.drawing.nx_agraph import to_agraph, graphviz_layout

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gdk, Gsk, Graphene, GObject, GLib

from insight_gui.widgets.canvas_blocks import (
    BaseBlock,
    NodeBlock,
    TopicBlock,
    ServiceBlock,
    ActionBlock,
    ParameterBlock,
    TransformBlock,
)
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.canvas_sidebar import CanvasSidebar


class Canvas(Adw.Bin):
    __gtype_name__ = "Canvas"

    zoom_factor = GObject.Property(type=float, default=1.0)
    zoom_speed = GObject.Property(type=float, default=0.1)
    zoom_min = GObject.Property(type=float, default=0.2)
    zoom_max = GObject.Property(type=float, default=5.0)

    def __init__(self):
        super().__init__()

        self.pan_offset = Graphene.Point(0.0, 0.0)
        self.custom_width = 1000.0
        self.custom_height = 1000.0

        # Create the main split view with sidebar on the right
        self.split_view = Adw.OverlaySplitView(
            sidebar_position=Gtk.PackType.END,  # Right side
            collapsed=False,  # Start collapsed
            show_sidebar=False,
            pin_sidebar=True,
            max_sidebar_width=500,
            min_sidebar_width=300,
        )
        super().set_child(self.split_view)

        # Create the main content area with overlay for toolbar
        self.overlay = Gtk.Overlay()
        self.split_view.set_content(self.overlay)

        # the toolbar with the zoom btns etc
        self.toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=2,
            margin_top=12,
            margin_bottom=16,
            margin_start=12,
            margin_end=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.END,
            css_classes=["toolbar", "card"],
        )
        self.overlay.add_overlay(self.toolbar)

        # scrolled window for all the canvas content
        self.scrolled_window = Gtk.ScrolledWindow(overflow=Gtk.Overflow.HIDDEN, hexpand=True, vexpand=True)
        self.overlay.set_child(self.scrolled_window)

        # Create sidebar content
        # TODO add an "ESC" action to close the sidebar
        self.sidebar = CanvasSidebar()
        self.sidebar.connect("close", self._on_sidebar_close)
        self.split_view.set_sidebar(self.sidebar)

        # Track the currently selected block for highlighting
        self._selected_block = None  # TODO

        # canvas where the blocks are places
        self.fixed = Gtk.Fixed(
            hexpand=True,
            vexpand=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        self.scrolled_window.set_child(self.fixed)

        # Zoom out button
        zoom_out_btn = Gtk.Button(icon_name="zoom-out-symbolic", tooltip_text="Zoom Out (Ctrl + Scroll)")
        zoom_out_btn.connect("clicked", lambda *_: self.zoom_by(1.0))  # Positive for zoom out
        self.toolbar.append(zoom_out_btn)

        # Zoom level label
        self.zoom_label = Gtk.Label()
        self.zoom_label.set_text("100%")
        self.zoom_label.set_margin_start(6)
        self.zoom_label.set_margin_end(6)
        self.toolbar.append(self.zoom_label)

        # Zoom in button
        zoom_in_btn = Gtk.Button(icon_name="zoom-in-symbolic", tooltip_text="Zoom In (Ctrl + Scroll)")
        zoom_in_btn.connect("clicked", lambda *_: self.zoom_by(-1.0))  # Negative for zoom in
        self.toolbar.append(zoom_in_btn)

        # Separator
        separator = Gtk.Separator(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=6,
            margin_end=6,
            css_classes=["spacer"],
        )
        self.toolbar.append(separator)

        # Zoom to fit button
        zoom_fit_btn = Gtk.Button(icon_name="zoom-fit-best-symbolic", tooltip_text="Zoom to Fit")
        zoom_fit_btn.connect("clicked", self._on_zoom_fit)
        self.toolbar.append(zoom_fit_btn)

        # Reset zoom button
        zoom_reset_btn = Gtk.Button(icon_name="zoom-original-symbolic", tooltip_text="Reset Zoom (100%)")
        zoom_reset_btn.connect("clicked", self._on_zoom_reset)
        self.toolbar.append(zoom_reset_btn)

        # Connect to zoom factor changes to update label
        super().connect("notify::zoom-factor", self._on_zoom_factor_changed)

        # Add scroll event listener for zooming
        scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll_controller.connect("scroll", self._on_scroll)
        self.scrolled_window.add_controller(scroll_controller)

        # add a drag controller for panning
        drag = Gtk.GestureDrag()
        drag.set_button(Gdk.BUTTON_MIDDLE)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        # drawing area which shows/draws the connections etc in the background
        self.drawing_area = Gtk.DrawingArea(
            hexpand=True,
            vexpand=True,
            content_width=self.custom_width,
            content_height=self.custom_height,
        )
        self.drawing_area.set_draw_func(self._on_draw)
        self.fixed.put(self.drawing_area, 0, 0)

        self._nx_graph = nx.DiGraph()
        self._blocks = set()
        self._connections = set()
        self._highlighted_blocks = set()  # Highlighted blocks
        self._highlighted_connections = set()  # Highlighted connections

    def _on_zoom_factor_changed(self, *args):
        """Handle zoom factor changes and update the canvas accordingly."""

        # Update fixed container size for scrolling
        zoomed_width = int(self.custom_width * self.zoom_factor)
        zoomed_height = int(self.custom_height * self.zoom_factor)

        # Update drawing area size
        self.drawing_area.set_content_width(zoomed_width)
        self.drawing_area.set_content_height(zoomed_height)

        # Update block positions based on zoom (keep natural size)
        for block in self._blocks:
            orig_x, orig_y = block.pos

            # Scale position only
            new_x = int(orig_x * self.zoom_factor)
            new_y = int(orig_y * self.zoom_factor)

            # Move block to new position (keep natural size)
            self.move_block(block, new_x, new_y, update_block_pos=False)

            # Reset to natural size (no scaling)
            block.set_size_request(-1, -1)

        # Redraw connections with new positions
        self.drawing_area.queue_draw()

        # Update zoom label when zoom factor changes
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_label.set_text(f"{zoom_percent}%")

    def set_zoom(self, zoom: float):
        """Set the zoom factor directly."""
        self.zoom_factor = max(self.zoom_min, min(zoom, self.zoom_max))

    def zoom_by(self, delta: float):
        """Zoom by a relative amount."""
        old_zoom = self.zoom_factor

        # Calculate zoom step based on current zoom level for smooth zooming
        step = delta * self.zoom_speed * old_zoom
        new_zoom = max(self.zoom_min, min(self.zoom_factor - step, self.zoom_max))

        if new_zoom != self.zoom_factor:
            # Get current scroll position to maintain zoom center
            hadj = self.scrolled_window.get_hadjustment()
            vadj = self.scrolled_window.get_vadjustment()

            # Calculate center point of current view
            center_x = hadj.get_value() + hadj.get_page_size() / 2
            center_y = vadj.get_value() + vadj.get_page_size() / 2

            # Update zoom factor
            self.zoom_factor = new_zoom
            zoom_ratio = self.zoom_factor / old_zoom

            # Adjust scroll position to keep the same center point
            new_center_x = center_x * zoom_ratio
            new_center_y = center_y * zoom_ratio

            # Set new scroll position (will be applied after zoom_changed)
            def adjust_scroll():
                hadj.set_value(new_center_x - hadj.get_page_size() / 2)
                vadj.set_value(new_center_y - vadj.get_page_size() / 2)
                return False

            # Delay scroll adjustment until after zoom is applied
            GLib.idle_add(adjust_scroll)

    def _on_zoom_fit(self, *args):
        """Zoom to fit all content in the viewport."""
        if not self._blocks:
            return

        # Calculate bounding box of all blocks
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for block in self._blocks:
            pos = self.fixed.get_child_position(block)
            size = block.get_preferred_size().minimum_size

            min_x = min(min_x, pos[0])
            min_y = min(min_y, pos[1])
            max_x = max(max_x, pos[0] + size.width)
            max_y = max(max_y, pos[1] + size.height)

        # Add padding
        padding = 30
        content_width = max_x - min_x + 2 * padding
        content_height = max_y - min_y + 2 * padding

        # Calculate zoom to fit
        viewport_width = self.scrolled_window.get_allocated_width()
        viewport_height = self.scrolled_window.get_allocated_height()

        if viewport_width > 0 and viewport_height > 0:
            zoom_x = viewport_width / content_width
            zoom_y = viewport_height / content_height
            target_zoom = min(zoom_x, zoom_y)

            # Apply zoom limits
            target_zoom = max(self.zoom_min, min(target_zoom, self.zoom_max))
            self.set_zoom(target_zoom)

    def _on_zoom_reset(self, *args):
        """Handle reset zoom (to 100%) button click."""
        self.set_zoom(1.0)

    # Scroll handler (zoom with Ctrl + scroll)
    def _on_scroll(self, controller: Gtk.EventControllerScroll, dx: float, dy: float):
        """Handle scroll events for zooming."""
        event = controller.get_current_event()

        # Check if Ctrl is pressed for zooming
        if event and (event.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK):
            self.zoom_by(dy)
            return True  # Event handled

        # Let normal scrolling happen
        return False

    # Middle mouse drag handlers
    def _on_drag_begin(self, gesture, start_x, start_y):
        self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("move", None))
        self.start_drag_x = self.scrolled_window.get_hadjustment().get_value()
        self.start_drag_y = self.scrolled_window.get_vadjustment().get_value()

    def _on_drag_update(self, gesture, offset_x, offset_y):
        self.scrolled_window.get_hadjustment().set_value(self.start_drag_x - offset_x)
        self.scrolled_window.get_vadjustment().set_value(self.start_drag_y - offset_y)

    def _on_drag_end(self, gesture, offset_x, offset_y):
        self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("default", None))

    def _on_draw(self, drawing_area, cr, width, height):
        if not self.get_realized():
            return

        for connection in self._connections:
            block1, block2 = connection
            self._draw_connection(cr, block1, block2, connection)

    def clear(self):
        for block in self._blocks:
            self.fixed.remove(block)
        self._blocks.clear()
        self._connections.clear()
        self._nx_graph.clear()

        # Reset zoom to 1.0 when clearing
        self.zoom_factor = 1.0
        self.drawing_area.queue_draw()

    def set_size(self, width: int, height: int):
        self.custom_width = width
        self.custom_height = height
        self.drawing_area.set_content_width(int(width))
        self.drawing_area.set_content_height(int(height))

    def add_block(self, block_class: BaseBlock, block_args: dict) -> str:
        # Create the block instance with the unique ID
        block = block_class(**block_args)
        block_type = block_class.__name__.lower()  # Use class name as type

        # check if the block already exists
        for b in self._blocks:
            if b.uuid == block.uuid:
                return block.uuid

        # Add to nx_graph
        self._nx_graph.add_node(block.uuid, label=block.title, type=block_type, args=block_args)

        # Set up block event handlers
        block.connect("revealer-toggled", self._block_revealed)
        block.connect("info-clicked", self._on_block_info_clicked)

        # Add hover event controllers for highlighting
        hover_controller = Gtk.EventControllerMotion()
        hover_controller.connect("enter", self._on_block_hover_enter, block)
        hover_controller.connect("leave", self._on_block_hover_leave, block)
        block.add_controller(hover_controller)

        # Add to canvas
        self._blocks.add(block)
        self.fixed.put(block, block.pos[0], block.pos[1])

        # # Apply current zoom if not at 1.0
        # if self.zoom_factor != 1.0:
        #     self._on_zoom_factor_changed()

        return block.uuid

    def get_block(self, uuid: str) -> BaseBlock:
        for block in self._blocks:
            if block.uuid == uuid:
                return block
        else:
            return None

    def get_block_by_label(self, label: str, type_filter: str = None) -> BaseBlock:
        for block in self._blocks:
            if block.title == label and (type_filter is None or block.__class__.__name__.lower() == type_filter):
                return block
        return None

    def has_block_with_label(self, label: str, type_filter: str = None) -> bool:
        return self.get_block_by_label(label, type_filter) is not None

    def move_block(self, block: BaseBlock, x: float, y: float, update_block_pos: bool = True):
        if block not in self._blocks:
            return
        self.fixed.move(block, x, y)

        # Update original position data if zoom tracking is active
        if update_block_pos and block in self._blocks:
            block.pos = (x, y)

    def remove_block(self, block: BaseBlock):
        if block not in self._blocks:
            return
        self.fixed.remove(block)

    def connect_blocks(self, source_uuid: str, target_uuid: str, label: str = ""):
        source_block = self.get_block(source_uuid)
        target_block = self.get_block(target_uuid)

        if (
            source_block is None
            or source_block not in self._blocks
            or target_block is None
            or target_block not in self._blocks
        ):
            return

        # Add edge to graph
        self._nx_graph.add_edge(source_uuid, target_uuid, label=label)

        # Add visual connection between blocks
        self._connections.add((source_block, target_block))

    def get_graph_nodes(self, node_type: str = None):
        """Get nodes from the graph, optionally filtered by type."""
        if node_type:
            return [
                (node_id, data) for node_id, data in self._nx_graph.nodes(data=True) if data.get("type") == node_type
            ]
        return list(self._nx_graph.nodes(data=True))

    def get_graph_edges(self):
        """Get edges from the graph, optionally filtered by type."""
        return list(self._nx_graph.edges(data=True))

    def set_node_layout_attributes(self, node_id: str, node_type: str):
        """Set node attributes based on type for better Graphviz layout."""
        if node_type == NodeBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
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
        elif node_type == TopicBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
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
        elif node_type == ServiceBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
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
        elif node_type == ActionBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
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
        elif node_type == ParameterBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
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
        elif node_type == TransformBlock.__name__.lower():
            self._nx_graph.nodes[node_id].update(
                {
                    "shape": "box",
                    "style": "rounded,filled",
                    "fillcolor": "#E0F7FA",
                    "color": "#00ACC1",
                    "fontname": "Arial",
                    "fontsize": "8",
                    "width": "2.5",
                    "height": "1.0",
                    "fixedsize": "true",
                }
            )

    def _block_revealed(self, block: BaseBlock, revealed: bool):
        if not revealed:
            return

        # reposition the block to the top of the fixed
        x, y = self.fixed.get_child_position(block)
        self.fixed.remove(block)
        self.fixed.put(block, x, y)

    def _on_block_hover_enter(self, controller, x: float, y: float, block: BaseBlock):
        """Handle mouse entering a block - highlight the block and its connections."""
        self._highlighted_blocks.clear()
        self._highlighted_connections.clear()

        # Find all connections involving this block
        for connection in self._connections:
            block1, block2 = connection
            if block1 == block or block2 == block:
                self._highlighted_connections.add(connection)
                self._highlighted_blocks.add(block1)
                self._highlighted_blocks.add(block2)

        # Apply highlighting styles
        self._apply_highlighting()
        self.drawing_area.queue_draw()

    def _on_block_hover_leave(self, *args):
        """Handle mouse leaving a block - remove highlighting."""
        self._highlighted_blocks.clear()
        self._highlighted_connections.clear()

        # Remove highlighting styles
        self._remove_highlighting()
        self.drawing_area.queue_draw()

    def _apply_highlighting(self):
        """Apply highlighting styles to blocks and connections."""
        for block in self._blocks:
            if block in self._highlighted_blocks:
                # Highlight connected blocks - make them stand out
                block.add_css_class("highlighted")
                block.remove_css_class("dimmed")
                # Add a visual highlight effect
                block.set_opacity(1.0)
            else:
                # Dim non-connected blocks
                block.add_css_class("dimmed")
                block.remove_css_class("highlighted")
                # Make them more transparent
                block.set_opacity(0.3)

    def _remove_highlighting(self):
        """Remove all highlighting styles."""
        for block in self._blocks:
            block.remove_css_class("highlighted")
            block.remove_css_class("dimmed")
            # Reset opacity to normal
            block.set_opacity(1.0)

    def _on_sidebar_toggle(self, *args):
        """Toggle the sidebar visibility."""
        self.split_view.set_show_sidebar(not self.split_view.get_show_sidebar())

    def _on_sidebar_close(self, *args):
        """Close the sidebar."""
        self.split_view.set_show_sidebar(False)

        if self._selected_block:
            self._selected_block.toggle_highlight(False)

    def _on_block_info_clicked(self, block: BaseBlock):
        """Handle when a block's info button is clicked."""
        # Remove previous selection highlighting
        if self._selected_block:
            self._selected_block.toggle_highlight(False)

        # Set new selection
        self._selected_block = block
        block.toggle_highlight(True)

        # Update sidebar content
        self.sidebar.update_content(block)

        # Show sidebar if hidden
        if not self.split_view.get_show_sidebar():
            self.split_view.set_show_sidebar(True)

    # def set_edge_layout_attributes(self):
    #     """Set edge attributes for better routing."""
    #     for source, target, data in self._nx_graph.edges(data=True):
    #         self._nx_graph.edges[source, target].update(
    #             {
    #                 "color": "#666666",
    #                 "penwidth": "1.5",
    #                 "arrowsize": "0.8",
    #                 "arrowhead": "normal",
    #             }
    #         )

    # def parse_edge_pos(self, pos_str):
    #     """Parse Graphviz edge position string to extract path points."""
    #     if not pos_str:
    #         return []

    #     # Remove all "e," prefixes (can appear at start or middle)
    #     cleaned_str = pos_str.replace("e,", "")

    #     # Split into coordinate pairs
    #     coord_pairs = cleaned_str.split()
    #     points = []

    #     for pair in coord_pairs:
    #         try:
    #             # Handle mixed separators - try comma first, then semicolon
    #             if "," in pair:
    #                 x, y = map(float, pair.split(","))
    #             elif ";" in pair:
    #                 x, y = map(float, pair.split(";"))
    #             else:
    #                 # Skip invalid pairs
    #                 continue
    #             points.append((x, y))
    #         except (ValueError, IndexError):
    #             # Skip malformed coordinate pairs
    #             continue

    #     return points

    def _transform_graph_point_to_canvas(self, point: tuple) -> tuple:
        # """Transform a point from graph coordinates to canvas coordinates."""
        # if not self._graph_node_positions:
        #     return point
        # TODO unify all the calculations in this method
        # to do so, use the layout to calculate the bounds and scale etc and save them into self
        pass

    def calculate_layout(self):
        # Check if we have any nodes to layout
        if not self._nx_graph.nodes():
            print("No nodes in graph, cannot calculate layout.")
            return

        try:
            self._nx_graph.graph.update(
                {
                    "rankdir": "LR",  # Left to right layout
                    "ranksep": "2.0",  # Spacing between ranks considering block widths
                    "nodesep": "0.3",  # Spacing between nodes considering block heights
                    "splines": "curved",
                    "overlap": "false",  # Prevent overlaps
                    "concentrate": "true",  # Merge multi-edges
                    "newrank": "true",  # Better ranking algorithm
                    "sep": "+20,20",  # Component separation
                }
            )

            # Use dot layout for hierarchical arrangement
            self._graph_node_positions = graphviz_layout(
                self._nx_graph,
                prog="dot",
                args="-Grankdir=LR -Granksep=2.0 -Gnodesep=0.5",
            )

        except (ImportError, Exception) as e:
            print(f"Graphviz layout failed: {e}, falling back to spring layout")
            self._graph_node_positions = nx.spring_layout(self._nx_graph, seed=42, k=3, iterations=50)

        # Get the bounds of the graph layout
        xs, ys = zip(*self._graph_node_positions.values())
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        graph_width, graph_height = max_x - min_x, max_y - min_y

        # Get the available viewport size
        viewport_width = self.scrolled_window.get_allocated_width()
        viewport_height = self.scrolled_window.get_allocated_height()

        # Use viewport size if available, otherwise use minimum defaults
        padding = 200
        if viewport_width > 0 and viewport_height > 0:
            canvas_width = max(viewport_width, graph_width + padding)
            canvas_height = max(viewport_height, graph_height + padding)
        else:
            # Fallback to larger defaults # TODO are these reasonable?
            canvas_width = max(1200, graph_width + 400)
            canvas_height = max(800, graph_height + 300)

        # Set the canvas size
        self.set_size(canvas_width, canvas_height)

        # Center the graph in the available space # TODO why 100?
        padding_x = max(100, (canvas_width - graph_width) / 2)
        padding_y = max(100, (canvas_height - graph_height) / 2)

        # Position blocks with better spacing
        for uuid, (x, y) in self._graph_node_positions.items():
            canvas_x = (x - min_x) + padding_x  # No extra scaling, use natural positions
            canvas_y = (y - min_y) + padding_y

            block = self.get_block(uuid)
            if block:
                # Wait for block to be realized to get accurate size
                block.realize()
                block_size = block.get_preferred_size().minimum_size
                final_x = max(0, canvas_x - block_size.width / 2)
                final_y = max(0, canvas_y - block_size.height / 2)
                self.move_block(block, final_x, final_y)

        self.drawing_area.queue_draw()

    def export_graph_as_pdf(self, filename: str):
        import matplotlib.pyplot as plt

        nx.draw(
            self._nx_graph,
            self._graph_node_positions,
            labels={n: d["label"] for n, d in self._nx_graph.nodes(data=True)},
            with_labels=True,
            arrows=True,
            node_size=2000,
            node_color="lightblue",
            font_size=10,
        )
        # plt.savefig("graph_output.pdf")  # or use "graph_output.png"
        plt.show(block=False)

    # def _calc_block_attachment_position(self, block: BaseBlock, direction: str = "north"):
    #     pos_on_canvas = self.fixed.get_child_position(block)

    #     def _add_pos(p1: tuple, p2: tuple):
    #         return (p1[0] + p2[0], p1[1] + p2[1])

    #     if direction == "north":
    #         pos_on_canvas = _add_pos(pos_on_canvas, block.top_attachment_point)
    #     elif direction == "east":
    #         pos_on_canvas = _add_pos(pos_on_canvas, block.right_attachment_point)
    #     elif direction == "west":
    #         pos_on_canvas = _add_pos(pos_on_canvas, block.left_attachment_point)
    #     elif direction == "south":
    #         pos_on_canvas = _add_pos(pos_on_canvas, block.bottom_attachment_point)

    #     return pos_on_canvas

    def _draw_connection(self, cr, block1: BaseBlock, block2: BaseBlock, connection=None):
        """Draw a connection between two blocks with smart routing to avoid overlaps."""

        # # helper function to parse Graphviz edge positions
        # def parse_edge_pos(pos_str: str):
        #     # Parse pos string into list of points
        #     # Example: "e,81,50 98,50 115,50"
        #     if not pos_str or not pos_str.startswith("e,"):
        #         return []

        #     coords_pair = pos_str[2:].split()  # remove 'e,' and split by spaces
        #     return [tuple(map(float, pair.split(","))) for pair in coords_pair]

        # A = to_agraph(self._nx_graph)
        # A.layout(prog="dot")  # or "neato", "fdp", etc.

        # splines = []

        # # Extract edge positions
        # for e in A.edges():
        #     pos_str = e.attr.get("pos")

        #     if pos_str:
        #         splines.append(parse_edge_pos(pos_str))

        # Determine if this connection is highlighted
        is_highlighted = connection in self._highlighted_connections if connection else False
        is_dimmed = self._highlighted_connections and not is_highlighted

        # Set line style based on highlighting state
        if is_highlighted:
            # Highlighted connections are brighter and thicker
            if Adw.StyleManager.get_default().get_dark():
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)  # Bright white for dark theme
            else:
                cr.set_source_rgba(0.0, 0.0, 0.0, 1.0)  # Bright black for light theme
            cr.set_line_width(3.5)
        elif is_dimmed:
            # Dimmed connections are more transparent
            if Adw.StyleManager.get_default().get_dark():
                cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)  # Very dim for dark theme
            else:
                cr.set_source_rgba(0.6, 0.6, 0.6, 0.7)  # Very dim for light theme
            cr.set_line_width(1.5)
        else:
            # Normal connections
            if Adw.StyleManager.get_default().get_dark():
                cr.set_source_rgba(0.8, 0.8, 0.8, 0.9)  # Light gray for dark theme
            else:
                cr.set_source_rgba(0.3, 0.3, 0.3, 0.9)  # Dark gray for light theme
            cr.set_line_width(2.5)

        cr.set_line_cap(1)  # Round line caps

        # Get the layout bounds for coordinate transformation
        # xs, ys = zip(*self._graph_node_positions.values())
        # min_x, max_x = min(xs), max(xs)
        # min_y, max_y = min(ys), max(ys)
        # graph_width, graph_height = max_x - min_x, max_y - min_y

        # # Calculate the same padding used in calculate_layout
        # viewport_width = self.scrolled_window.get_allocated_width()
        # viewport_height = self.scrolled_window.get_allocated_height()

        # if viewport_width > 0 and viewport_height > 0:
        #     canvas_width = max(viewport_width, graph_width + 200)
        #     canvas_height = max(viewport_height, graph_height + 200)
        # else:
        #     canvas_width = max(1200, graph_width + 400)
        #     canvas_height = max(800, graph_height + 300)

        # padding_x = max(100, (canvas_width - graph_width) / 2)
        # padding_y = max(100, (canvas_height - graph_height) / 2)

        # def quadratic_curve_to(x1, y1, x2, y2):
        #     cr.curve_to(x1, y1, x1, y1, x2, y2)

        # # draw all the splines
        # for spline in splines:
        #     canvas_points = []

        # transform spline points to canvas coordinates
        # for spline_point in spline:
        #     canvas_x = (spline_point[0] - min_x) + padding_x
        #     canvas_y = (spline_point[1] - min_y) + padding_y
        #     canvas_points.append((canvas_x, canvas_y))

        pos1 = self.fixed.get_child_position(block1)
        pos2 = self.fixed.get_child_position(block2)

        size1 = block1.get_preferred_size().minimum_size
        size2 = block2.get_preferred_size().minimum_size

        # Calculate block centers
        center1 = (pos1[0] + size1.width / 2, pos1[1] + size1.height / 2)
        center2 = (pos2[0] + size2.width / 2, pos2[1] + size2.height / 2)

        # Determine connection points based on relative positions
        if center1[0] < center2[0]:  # block1 is to the left of block2
            # Connect from right side of block1 to left side of block2
            start_point = (pos1[0] + size1.width, center1[1])
            end_point = (pos2[0], center2[1])
            start_dir = 1  # pointing right
            end_dir = -1  # pointing left
        else:  # block1 is to the right of block2
            # Connect from left side of block1 to right side of block2
            start_point = (pos1[0], center1[1])
            end_point = (pos2[0] + size2.width, center2[1])
            start_dir = -1  # pointing left
            end_dir = 1  # pointing right

        # Draw the connection with improved bezier curve
        x1, y1 = start_point
        x2, y2 = end_point

        # Calculate control points for better orthogonal routing that avoids blocks
        horizontal_distance = abs(x2 - x1)
        vertical_distance = abs(y2 - y1)

        # Adaptive control point distance based on block spacing
        base_offset = max(60, horizontal_distance * 0.4)

        # Adjust offset to avoid overlapping with blocks
        if vertical_distance > 100:  # If blocks are far apart vertically
            control_offset = min(base_offset, horizontal_distance * 0.6)
        else:  # If blocks are close vertically, use larger offset to route around
            control_offset = max(base_offset, 50)

        # Create control points for smooth orthogonal routing
        if start_dir > 0:  # going right
            cx1 = x1 + control_offset
        else:  # going left
            cx1 = x1 - control_offset

        if end_dir > 0:  # coming from left
            cx2 = x2 + control_offset
        else:  # coming from right
            cx2 = x2 - control_offset

        # Draw the path with improved routing
        cr.move_to(x1, y1)

        # Use cubic bezier for smooth orthogonal routing
        cr.curve_to(cx1, y1, cx2, y2, x2, y2)
        cr.stroke()

        # Draw connection point indicators
        cr.arc(x1, y1, 3, 0.0, 2 * math.pi)
        cr.fill()

        # Draw arrowhead at the end
        arrow_size = 12

        # Calculate arrowhead points based on direction
        # The arrowhead should point in the direction of data flow
        if end_dir > 0:  # connection going right (left to right)
            # Arrow points right (toward the target)
            angle = math.pi
        else:  # connection going left (right to left)
            # Arrow points left (toward the target)
            angle = 0

        # Calculate arrowhead vertices - pointing in the direction of flow
        p1_x = x2 - arrow_size * math.cos(angle - math.pi / 6)
        p1_y = y2 - arrow_size * math.sin(angle - math.pi / 6)

        p2_x = x2 - arrow_size * math.cos(angle + math.pi / 6)
        p2_y = y2 - arrow_size * math.sin(angle + math.pi / 6)

        # Draw filled arrowhead
        cr.move_to(x2, y2)
        cr.line_to(p1_x, p1_y)
        cr.line_to(p2_x, p2_y)
        cr.close_path()
        cr.fill()

    # def _draw_bezier(self, cr, x1: float, y1: float, dir1: int, x2: float, y2: float, dir2: int):
    #     """Legacy bezier drawing method - kept for compatibility."""
    #     # Compute control points
    #     control_point_offset = min(100, ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)

    #     def sign(_dir):  # check if plus or minus
    #         return 1 if _dir > 0 else -1

    #     # control point next to the start point
    #     cx1, cy1 = (x1 + control_point_offset * sign(dir1), y1)
    #     cx2, cy2 = (x2 + control_point_offset * sign(dir2), y2)
    #     cx3, cy3 = None, None
    #     cx4, cy4 = None, None

    #     if dir1 < 0 and dir2 < 0 and abs(cx1 - cx2) < control_point_offset:
    #         cx3, cy3 = (cx1 if cx1 < cx2 else cx2, cy2 if cx1 < cx2 else cy1)

    #     elif dir1 > 0 and dir2 > 0 and abs(cx1 - cx2) < control_point_offset:
    #         cx3, cy3 = (cx2 if cx1 < cx2 else cx1, cy1 if cx1 < cx2 else cy2)

    #     # Draw the bezier curve
    #     if Adw.StyleManager.get_default().get_dark():
    #         cr.set_source_rgb(1, 1, 1)  # Set color to white
    #     else:
    #         cr.set_source_rgb(0, 0, 0)  # Set color to black

    #     cr.set_line_width(2)
    #     cr.move_to(x1, y1)  # Move to the start point

    #     if cx4 is not None:
    #         cr.curve_to(cx1, cy1, cx2, cy2, cx3, cy3, cx4, cy4, x2, y2)  # Bezier curve
    #     elif cx3 is not None:
    #         cr.curve_to(cx1, cy1, cx2, cy2, cx3, cy3, x2, y2)
    #     else:
    #         cr.curve_to(cx1, cy1, cx2, cy2, x2, y2)

    #     # draw circles at the ends
    #     cr.stroke()
    #     cr.arc(x1, y1, 5, 0.0, 2 * math.pi)
    #     cr.arc(x2, y2, 5, 0.0, 2 * math.pi)
    #     cr.fill()
