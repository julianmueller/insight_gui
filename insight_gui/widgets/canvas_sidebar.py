# =============================================================================
# canvas_sidebar.py
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


from insight_gui.widgets.canvas_blocks import (
    BaseBlock,
    NodeBlock,
    TopicBlock,
    ServiceBlock,
    ActionBlock,
    ParameterBlock,
    TransformBlock,
)
from insight_gui.widgets.buttons import CopyButton
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class CanvasSidebar(Gtk.Box):
    __gtype_name__ = "CanvasSidebar"
    __gsignals__ = {
        "close": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        # super().connect("realize", self.on_realize)

        # Header with title and close button
        self.header_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        super().append(self.header_box)

        # title
        self.title_lbl = Gtk.Label(
            label="",
            css_classes=["heading"],
            hexpand=True,
            halign=Gtk.Align.FILL,
        )
        self.header_box.append(self.title_lbl)

        # close button
        close_btn = Gtk.Button(
            icon_name="window-close-symbolic",
            tooltip_text="Close Sidebar",
            css_classes=["flat"],
        )
        close_btn.connect("clicked", self._on_close)
        self.header_box.append(close_btn)

        # Create PrefPage for content
        self.pref_page = PrefPage()
        super().append(self.pref_page)

    def update_content(self, block: BaseBlock):
        # Clear existing content from PrefPage
        self.pref_page.clear()

        self.title_lbl.set_label(block.title)

        # Block type-specific content
        block_type = type(block).__name__

        # Basic block info
        # info_group = self.pref_page.add_group(title="Basic Information")

        # Block type
        # type_row = info_group.add_row(PrefRow(title="Type", subtitle=block_type))
        # title_row = info_group.add_row(PrefRow(title="Title", subtitle=block.title))
        # if block.subtitle:
        #     subtitle_row = info_group.add_row(PrefRow(title="Subtitle", subtitle=block.subtitle))

        # uuid_row = info_group.add_row(PrefRow(title="UUID", subtitle=block.uuid))

        # Type-specific information
        if isinstance(block, NodeBlock):
            node_group = self.pref_page.add_group(title="Node Details")
            node_group.add_row(PrefRow(title="Node Name", subtitle=block.node_name, css_classes=["property"]))
            node_group.add_row(PrefRow(title="Namespace", subtitle=block.node_namespace, css_classes=["property"]))

        elif isinstance(block, TopicBlock):
            topic_group = self.pref_page.add_group(title="Topic Details")
            topic_group.add_row(PrefRow(title="Topic Name", subtitle=block.topic_name, css_classes=["property"]))
            types_text = block.topic_types if isinstance(block.topic_types, str) else ", ".join(block.topic_types)
            topic_group.add_row(PrefRow(title="Message Types", subtitle=types_text, css_classes=["property"]))

        elif isinstance(block, ServiceBlock):
            service_group = self.pref_page.add_group(title="Service Details")
            service_group.add_row(PrefRow(title="Service Name", subtitle=block.service_name, css_classes=["property"]))
            types_text = block.service_types if isinstance(block.service_types, str) else ", ".join(block.service_types)
            service_group.add_row(PrefRow(title="Service Types", subtitle=types_text, css_classes=["property"]))

        elif isinstance(block, ActionBlock):
            action_group = self.pref_page.add_group(title="Action Details")
            action_group.add_row(PrefRow(title="Action Name", subtitle=block.action_name, css_classes=["property"]))
            types_text = block.action_types if isinstance(block.action_types, str) else ", ".join(block.action_types)
            action_group.add_row(PrefRow(title="Action Types", subtitle=types_text, css_classes=["property"]))

        elif isinstance(block, ParameterBlock):
            param_group = self.pref_page.add_group(title="Parameter Details")
            param_group.add_row(
                PrefRow(title="Parameter Name", subtitle=block.parameter_name, css_classes=["property"])
            )
            param_group.add_row(PrefRow(title="Node", subtitle=block.node_full_name, css_classes=["property"]))

        elif isinstance(block, TransformBlock):

            def _make_tf_row(title, subtitle):
                """Helper function to add a row with title and subtitle."""
                row = PrefRow(title=title, subtitle=subtitle, css_classes=["property"])
                row.add_suffix(
                    CopyButton(
                        copy_callback=row.get_subtitle,
                        tooltip_text="Copy text",
                    )
                )
                return row

            # TODO add an update method, to refresh the transform data
            if block.transform:
                trans_group = self.pref_page.add_group(title="Translation")
                trans = block.transform.transform.translation
                trans_group.add_row(_make_tf_row(title="tx", subtitle=str(trans.x)))
                trans_group.add_row(_make_tf_row(title="ty", subtitle=str(trans.y)))
                trans_group.add_row(_make_tf_row(title="tz", subtitle=str(trans.z)))

                rot_group = self.pref_page.add_group(title="Rotation")
                rot = block.transform.transform.rotation
                rot_group.add_row(_make_tf_row(title="qx", subtitle=str(rot.x)))
                rot_group.add_row(_make_tf_row(title="qy", subtitle=str(rot.y)))
                rot_group.add_row(_make_tf_row(title="qz", subtitle=str(rot.z)))
                rot_group.add_row(_make_tf_row(title="qw", subtitle=str(rot.w)))
            else:
                group = self.pref_page.add_group(title="Transform Data")
                group.add_row(PrefRow(title="No transform data available"))

            tf_info_group = self.pref_page.add_group(title="/tf Details")
            # tf_info_group.add_row(PrefRow(title="Frame Name", subtitle=block.title))

            # TODO add no wrap and no ellipsize to labels, and 20 width-cards
            tf_info_group.add_row(
                PrefRow(title="parent", subtitle=block.parent if block.parent else "None", css_classes=["property"])
            )

            if block.broadcaster:
                tf_info_group.add_row(
                    PrefRow(title="broadcaster", subtitle=block.broadcaster, css_classes=["property"])
                )

            if block.rate:
                tf_info_group.add_row(PrefRow(title="rate", subtitle=block.rate, css_classes=["property"]))

            if block.most_recent_transform:
                tf_info_group.add_row(
                    PrefRow(
                        title="most_recent_transform", subtitle=block.most_recent_transform, css_classes=["property"]
                    )
                )

            if block.buffer_length:
                tf_info_group.add_row(
                    PrefRow(title="buffer_length", subtitle=block.buffer_length, css_classes=["property"])
                )

            # Add any additional transform-specific info here
            # This could include parent frame, transform data, etc.

    def _on_close(self, *args):
        """Signal handler for close button."""
        self.emit("close")
