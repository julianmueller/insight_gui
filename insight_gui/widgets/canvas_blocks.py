# =============================================================================
# canvas_blocks.py
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

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject


from insight_gui.utils.adw_colors import AdwAccentColor
from insight_gui.widgets.buttons import RevealButton
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.ros2_pages.topic_info_page import TopicInfoPage


class BaseBlock(Adw.Bin):
    __gtype_name__ = "BaseBlock"
    __gsignals__ = {"revealer-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,))}

    def __init__(self, label: str, accent_color: AdwAccentColor = None, **kwargs):
        super().__init__()
        super().connect("realize", self.on_realize)

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.main_box: Gtk.Box = builder.get_object("main_box")
        self.set_child(self.main_box)

        self.header_box: Gtk.Box = builder.get_object("header_box")
        self.header_lbl: Gtk.Label = builder.get_object("header_lbl")
        self.header_lbl.set_label(label)
        self.subpage_btn: Gtk.Button = builder.get_object("subpage_btn")
        self.subpage_btn.connect("clicked", self.on_subpage_btn_clicked)

        self.revealer: Gtk.Revealer = builder.get_object("revealer")
        self.revealer.set_visible(False)
        # self.revealer.connect("notify::reveal-child", self._on_revealer_toggled)

        self.content_box: Gtk.Box = builder.get_object("content_box")
        self.left_box: Gtk.Box = builder.get_object("left_box")
        self.right_box: Gtk.Box = builder.get_object("right_box")

        self.reveal_btn: RevealButton = RevealButton(self.revealer)
        # self.header_box.prepend(self.reveal_btn)
        # self.label.set_cursor(Gdk.Cursor.new_from_name("grab"))

        if accent_color is not None and isinstance(accent_color, AdwAccentColor):
            self.main_box.add_css_class(accent_color.as_css_name())

    def on_realize(self, *args):
        self.nav_view = super().get_ancestor(Adw.NavigationView)
        self.ros2_connector = Gio.Application.get_default().ros2_connector

    @property
    def north_attachment_point(self):
        return (self.width / 2, 0)

    @property
    def east_attachment_point(self):
        return (self.width, self.height / 2)

    @property
    def south_attachment_point(self):
        return (self.width / 2, self.height)

    @property
    def west_attachment_point(self):
        return (0, self.height / 2)

    @property
    def width(self):
        return super().get_width()

    @property
    def height(self):
        return super().get_height()

    def _on_revealer_toggled(self, revealer, _param):
        self.emit("revealer-toggled", not revealer.get_child_revealed())

    def on_subpage_btn_clicked(self, button, *args):
        """Child class should override this with blocking, long-running computation."""
        pass


class NodeBlock(BaseBlock):
    __gtype_name__ = "NodeBlock"

    def __init__(self, node_full_name: str, **kwargs):
        super().__init__(label=node_full_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_BLUE, **kwargs)
        self.node_full_name = node_full_name

    def on_subpage_btn_clicked(self, button, *args):
        self.nav_view.push(NodeInfoPage(self.node_full_name))


class InterfaceBlock(BaseBlock):
    __gtype_name__ = "InterfaceBlock"

    def __init__(self, interface_name: str, **kwargs):
        super().__init__(label=interface_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_GREEN, **kwargs)
        self.interface_name = interface_name


class TopicBlock(BaseBlock):
    __gtype_name__ = "TopicBlock"

    def __init__(self, topic_name: str, topic_types: str | list[str], **kwargs):
        super().__init__(label=topic_name, accent_color=AdwAccentColor.ADW_ACCENT_COLOR_ORANGE, **kwargs)
        self.topic_name = topic_name
        self.topic_types = topic_types

    def on_subpage_btn_clicked(self, button, *args):
        self.nav_view.push(TopicInfoPage(self.topic_name, self.topic_types))


class ServiceBlock(BaseBlock):
    __gtype_name__ = "ServiceBlock"

    def __init__(self, service_name: str, **kwargs):
        super().__init__(label=service_name, **kwargs)
        self.service_name = service_name


class ActionBlock(BaseBlock):
    __gtype_name__ = "ActionBlock"

    def __init__(self, action_name: str, **kwargs):
        super().__init__(label=action_name, **kwargs)
        self.action_name = action_name


# class ParameterBlock(BaseBlock):
#     __gtype_name__ = "ParameterBlock"
#
#     def __init__(self, label: str, **kwargs):
#         super().__init__(label, **kwargs)
