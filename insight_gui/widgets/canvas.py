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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gdk, Gsk, Graphene, GObject

from insight_gui.widgets.canvas_blocks import BaseBlock


class Canvas(Gtk.ScrolledWindow):
    __gtype_name__ = "Canvas"

    # zoom_factor = GObject.Property(type=float, default=1.0)
    # zoom_speed = GObject.Property(type=float, default=0.1)
    # zoom_min = GObject.Property(type=float, default=0.1)
    # zoom_max = GObject.Property(type=float, default=20.0)

    def __init__(self):
        super().__init__()
        super().set_overflow(Gtk.Overflow.HIDDEN)
        super().set_hexpand(True)
        super().set_vexpand(True)

        self.pan_offset = Graphene.Point(0.0, 0.0)
        self.custom_width = 1000.0
        self.custom_height = 1000.0

        # # add a scroll event listener
        # scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        # scroll_controller.connect("scroll", self.on_scroll)
        # self.add_controller(scroll_controller)
        # self.connect("notify::zoom-factor", self.on_zoom_changed)

        # add a drag controller for panning
        drag = Gtk.GestureDrag()
        drag.set_button(Gdk.BUTTON_MIDDLE)
        drag.connect("drag-begin", self.on_drag_begin)
        drag.connect("drag-update", self.on_drag_update)
        drag.connect("drag-end", self.on_drag_end)
        self.add_controller(drag)

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
        super().set_child(self.fixed)

        self.drawing_area = Gtk.DrawingArea(
            hexpand=True, vexpand=True, content_width=self.custom_width, content_height=self.custom_height
        )
        self.drawing_area.set_draw_func(self.on_draw)
        self.fixed.put(self.drawing_area, 0, 0)

        self._blocks = {}
        self._connections = []

    # def on_zoom_changed(self, *args):
    #     # Update fixed container size request for scrolling
    #     width = int(self.custom_width * self.zoom_factor)
    #     height = int(self.custom_height * self.zoom_factor)
    #     self.fixed.set_size_request(width, height)

    #     # Resize and reposition each child
    #     for child, info in self.fixed._child_info.items():
    #         ox, oy = info["pos"]
    #         ow, oh = info["size"]
    #         nx = ox * self.zoom_factor + self.pan_offset.x
    #         ny = oy * self.zoom_factor + self.pan_offset.y
    #         nw = int(ow * self.zoom_factor)
    #         nh = int(oh * self.zoom_factor)
    #         self.fixed.move(child, int(nx), int(ny))
    #         child.set_size_request(nw, nh)

    #     # Redraw connections
    #     self.drawing_area.queue_draw()

    # def set_zoom(self, zoom):
    #     self.zoom_factor = zoom
    #     self.queue_draw()

    # def zoom_by(self, dy: float):
    #     old_zoom = self.zoom_factor
    #     step = dy * self.zoom_speed * old_zoom
    #     self.zoom_factor = max(self.zoom_min, min(self.zoom_factor - step, self.zoom_max))
    #     zoom_ratio = self.zoom_factor / old_zoom if old_zoom else 1

    #     hadj = self.get_hadjustment()
    #     vadj = self.get_vadjustment()

    #     hadj.set_value(hadj.get_value() + (hadj.get_page_size() / 2) * (zoom_ratio - 1))
    #     vadj.set_value(vadj.get_value() + (vadj.get_page_size() / 2) * (zoom_ratio - 1))

    #     self.queue_draw()

    # Scroll handler (zoom with Ctrl + scroll)
    # def on_scroll(self, controller: Gtk.EventControllerScroll, dx: float, dy: float):
    #     event = controller.get_current_event()
    #     print(f"[DEBUG] on_scroll called: dx={dx}, dy={dy}")
    #     if event and (event.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK):
    #         self.zoom_by(dy)
    #         return True
    #     return False

    # Middle mouse drag handlers
    def on_drag_begin(self, gesture, start_x, start_y):
        self.set_cursor(Gdk.Cursor.new_from_name("grabbing", None))
        self.start_drag_x = self.get_hadjustment().get_value()
        self.start_drag_y = self.get_vadjustment().get_value()

    def on_drag_update(self, gesture, offset_x, offset_y):
        self.get_hadjustment().set_value(self.start_drag_x - offset_x)
        self.get_vadjustment().set_value(self.start_drag_y - offset_y)

    def on_drag_end(self, gesture, offset_x, offset_y):
        self.set_cursor(None)

    def on_draw(self, drawing_area, cr, width, height):
        for connection in self._connections:
            block1, block2 = connection
            x1, y1 = self._calc_block_attachment_position(block1, "east")
            x2, y2 = self._calc_block_attachment_position(block2, "west")
            self._draw_bezier(cr, x1, y1, 1, x2, y2, -1)

    def clear(self):
        for name in list(self._blocks.keys()):
            self.fixed.remove(self._blocks.pop(name))
        self._connections.clear()
        # self.zoom_factor = 1.0
        # self.on_zoom_changed()
        self.drawing_area.queue_draw()

    def set_size(self, width: int, height: int):
        self.custom_width = width
        self.custom_height = height
        self.drawing_area.set_content_width(int(width))
        self.drawing_area.set_content_height(int(height))
        # self.on_zoom_changed()

    def add_block(self, block: BaseBlock, name: str):
        block.connect("revealer-toggled", self._block_revealed)
        self._blocks[name] = block
        self.fixed.put(block, 0, 0)

    def get_block(self, name: str):
        return self._blocks.get(name, None)

    def move_block(self, block: BaseBlock, x: float, y: float):
        if block not in self._blocks.values():
            return
        self.fixed.move(block, x, y)

    def remove_block(self, block: BaseBlock):
        if block not in self._blocks.values():
            return
        self.fixed.remove(block)

    def add_connection(self, block1: BaseBlock, block2: BaseBlock):
        if block1 not in self._blocks.values() or block2 not in self._blocks.values():
            return
        self._connections.append((block1, block2))

    def layout_from_graph(self, graph: nx.DiGraph):
        try:
            from networkx.drawing.nx_agraph import graphviz_layout

            # Use Graphviz to layout the graph (left-to-right or top-down)
            pos = graphviz_layout(graph, prog="dot")  # use prog='dot' for top-down or 'neato' for organic
        except ImportError:
            pos = nx.spring_layout(graph, seed=42)

        # Normalize and scale coordinates to fit within canvas

        xs, ys = zip(*pos.values())
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        graph_width, graph_height = max_x - min_x, max_y - min_y

        # xs = [x for x, y in pos.values()]
        # ys = [y for x, y in pos.values()]
        # min_x, max_x = min(xs), max(xs)
        # min_y, max_y = min(ys), max(ys)

        # graph_width = max_x - min_x
        # graph_height = max_y - min_y
        padding_x, padding_y = 300, 50
        self.set_size(graph_width + padding_x, graph_height + padding_y)

        for name, (x, y) in pos.items():
            canvas_x = x + padding_x / 2 - min_x
            canvas_y = y + padding_y / 2 - min_y

            block = self.get_block(name)
            if block:
                block_size = block.get_preferred_size().minimum_size
                final_x = canvas_x - block_size.width / 2
                final_y = canvas_y - block_size.height / 2
                self.move_block(block, final_x, final_y)

        self.drawing_area.queue_draw()

    def _block_revealed(self, block: BaseBlock, revealed: bool):
        if not revealed:
            return

        # reposition the block to the top of the fixed
        x, y = self.fixed.get_child_position(block)
        self.fixed.remove(block)
        self.fixed.put(block, x, y)

    def _calc_block_attachment_position(self, block: BaseBlock, direction: str = "north"):
        pos_on_canvas = self.fixed.get_child_position(block)

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
