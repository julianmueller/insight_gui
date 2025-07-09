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
from uuid import uuid4

from geometry_msgs.msg import TransformStamped

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject


from insight_gui.utils.adw_colors import AdwAccentColor
from insight_gui.widgets.buttons import RevealButton
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.ros2_pages.topic_info_page import TopicInfoPage
from insight_gui.ros2_pages.service_info_page import ServiceInfoPage
from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.ros2_pages.param_edit_page import ParamEditPage


class BaseBlock(Adw.Bin):
    __gtype_name__ = "BaseBlock"
    __gsignals__ = {"revealer-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,))}

    def __init__(self, label: str, uuid: str = None, accent_color: AdwAccentColor = None, **kwargs):
        super().__init__()
        super().connect("realize", self.on_realize)

        self.uuid: str = uuid if uuid is not None else uuid4().hex
        self.label: str = label
        self.pos = (0, 0)
        self.connected_blocks = []  # TODO fill these

        builder: Gtk.Builder = Gtk.Builder.new_from_file(str(Path(__file__).with_suffix(".ui")))

        self.main_box: Gtk.Box = builder.get_object("main_box")
        self.set_child(self.main_box)

        self.header_box: Gtk.Box = builder.get_object("header_box")
        self.header_lbl: Gtk.Label = builder.get_object("header_lbl")
        self.header_lbl.set_label(label)

        # TODO add options for more btns here, eg for topic pub/sub, service call etc
        self.subpage_btn: Gtk.Button = builder.get_object("subpage_btn")
        self.subpage_btn.connect("clicked", self.on_subpage_btn_clicked)

        self.revealer: Gtk.Revealer = builder.get_object("revealer")
        self.revealer.set_reveal_child(False)
        # self.revealer.set_visible(False)  # DEBUG
        # self.revealer.connect("notify::reveal-child", self._on_revealer_toggled)

        self.group: PrefGroup = builder.get_object("group")

        self.reveal_btn: RevealButton = RevealButton(self.revealer)
        self.header_box.prepend(self.reveal_btn)

        if accent_color is not None and isinstance(accent_color, AdwAccentColor):
            self.main_box.add_css_class(accent_color.as_css_name())

    def __hash__(self):
        return hash(self.uuid)  # used by networkx

    def on_realize(self, *args):
        self.nav_view = super().get_ancestor(Adw.NavigationView)
        self.ros2_connector = Gio.Application.get_default().ros2_connector

    @property
    def center_point(self) -> tuple[float, float]:
        return (self.width / 2.0, self.height / 2.0)

    @property
    def top_attachment_point(self) -> tuple[float, float]:
        return (self.width / 2.0, 0.0)

    @property
    def right_attachment_point(self) -> tuple[float, float]:
        return (self.width, self.height / 2.0)

    @property
    def bottom_attachment_point(self) -> tuple[float, float]:
        return (self.width / 2.0, self.height)

    @property
    def left_attachment_point(self) -> tuple[float, float]:
        return (0.0, self.height / 2.0)

    @property
    def width(self) -> float:
        return self.get_allocated_width()
        # return float(super().get_width())

    @property
    def height(self) -> float:
        return self.get_allocated_height()
        # return float(super().get_height())

    # def on_revealer_toggled(self, *args):
    #     self.emit("revealer-toggled", not self.revealer.get_child_revealed())

    def on_subpage_btn_clicked(self, *args):
        """Child class should override this."""
        pass


class NodeBlock(BaseBlock):
    __gtype_name__ = "NodeBlock"

    def __init__(self, node_full_name: str, **kwargs):
        super().__init__(
            label=node_full_name,
            uuid=f"node:{node_full_name}",
            accent_color=AdwAccentColor.ADW_ACCENT_COLOR_BLUE,
            **kwargs,
        )
        self.node_full_name = node_full_name

    def on_subpage_btn_clicked(self, *args):
        self.nav_view.push(NodeInfoPage(self.node_full_name))


class TopicBlock(BaseBlock):
    __gtype_name__ = "TopicBlock"

    def __init__(self, topic_name: str, topic_types: str | list[str], **kwargs):
        super().__init__(
            label=topic_name, uuid=f"topic:{topic_name}", accent_color=AdwAccentColor.ADW_ACCENT_COLOR_ORANGE, **kwargs
        )
        self.topic_name = topic_name
        self.topic_types = topic_types
        # TODO add subtitle etc

    def on_subpage_btn_clicked(self, *args):
        self.nav_view.push(TopicInfoPage(self.topic_name, self.topic_types))


class ServiceBlock(BaseBlock):
    __gtype_name__ = "ServiceBlock"

    def __init__(self, service_name: str, service_types: str | list[str], **kwargs):
        super().__init__(
            label=service_name,
            uuid=f"service:{service_name}",
            accent_color=AdwAccentColor.ADW_ACCENT_COLOR_GREEN,
            **kwargs,
        )
        self.service_name = service_name
        self.service_types = service_types
        # TODO add subtitle etc

    def on_subpage_btn_clicked(self, *args):
        self.nav_view.push(ServiceInfoPage(self.service_name, self.service_types))


class ActionBlock(BaseBlock):
    __gtype_name__ = "ActionBlock"

    def __init__(self, action_name: str, action_types: str | list[str], **kwargs):
        super().__init__(
            label=action_name, uuid=f"action:{action_name}", accent_color=AdwAccentColor.ADW_ACCENT_COLOR_RED, **kwargs
        )
        self.action_name = action_name
        self.action_types = action_types
        # TODO add subtitle etc

    def on_subpage_btn_clicked(self, *args):
        self.nav_view.push(ActionInfoPage(self.action_name, self.topic_types))


class ParameterBlock(BaseBlock):
    __gtype_name__ = "ParameterBlock"

    def __init__(self, node_name: str, parameter_name: str, **kwargs):
        super().__init__(
            label=parameter_name,
            uuid=f"param:{node_name}:{parameter_name}",
            accent_color=AdwAccentColor.ADW_ACCENT_COLOR_PURPLE,
            **kwargs,
        )
        self.node_name = node_name
        self.parameter_name = parameter_name

    def on_subpage_btn_clicked(self, *args):
        self.nav_view.push(ParamEditPage(self.node_name, self.parameter_name))


class TransformBlock(BaseBlock):
    __gtype_name__ = "TransformBlock"

    def __init__(
        self,
        frame_name: str,
        parent: str = "",
        transform: TransformStamped | None = None,
        broadcaster: str = "",
        rate: float = 0.0,
        most_recent_transform: str = "",
        oldest_transform: str = "",
        buffer_length: float = 0.0,
        **kwargs,
    ):
        super().__init__(
            label=frame_name, uuid=f"tf:{frame_name}", accent_color=AdwAccentColor.ADW_ACCENT_COLOR_BLUE, **kwargs
        )

        # TODO add no wrap and no ellipsize to labels, and 20 width-cards
        if parent:
            self.group.add_row(PrefRow(title="parent", subtitle=parent, css_classes=["property"]))

        # TODO add an update method, to refresh the transform data
        if transform:
            tf_row = self.group.add_row(Adw.ExpanderRow(title="transform", css_classes=["property"]))

            trans = transform.transform.translation
            tf_row.add_row(PrefRow(title="tx", subtitle=str(trans.x), css_classes=["property"]))
            tf_row.add_row(PrefRow(title="ty", subtitle=str(trans.y), css_classes=["property"]))
            tf_row.add_row(PrefRow(title="tz", subtitle=str(trans.z), css_classes=["property"]))

            rot = transform.transform.rotation
            tf_row.add_row(PrefRow(title="qx", subtitle=str(rot.x), css_classes=["property"]))
            tf_row.add_row(PrefRow(title="qy", subtitle=str(rot.y), css_classes=["property"]))
            tf_row.add_row(PrefRow(title="qz", subtitle=str(rot.z), css_classes=["property"]))
            tf_row.add_row(PrefRow(title="qw", subtitle=str(rot.w), css_classes=["property"]))

        if broadcaster:
            self.group.add_row(PrefRow(title="broadcaster", subtitle=broadcaster, css_classes=["property"]))

        if rate:
            self.group.add_row(PrefRow(title="rate", subtitle=rate, css_classes=["property"]))

        if most_recent_transform:
            self.group.add_row(
                PrefRow(title="most_recent_transform", subtitle=most_recent_transform, css_classes=["property"])
            )

        if buffer_length:
            self.group.add_row(PrefRow(title="buffer_length", subtitle=buffer_length, css_classes=["property"]))

    def on_subpage_btn_clicked(self, *args):
        # self.nav_view.push(ParamEditPage(self.node_name, self.parameter_name))
        print("not implemented yet")
