# =============================================================================
# tf_page.py
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

import yaml
import time

import rclpy

# from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
from geometry_msgs.msg import TransformStamped
from rosidl_runtime_py import message_to_yaml

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow


class TransformsPage(ContentPage):
    __gtype_name__ = "TransformsPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Transforms")
        super().set_search_entry_placeholder_text("Search for Frames")
        super().set_refresh_fail_text("No frames found. Refresh to try again.")

        # TODO add a button row that shows a dialog with a tf-tree

        self.calc_group = self.pref_page.add_group(title="Calculate Transform", filterable=False)
        self.calc_group.add_suffix_btn(
            icon_name="vertical-arrows-symbolic", tooltip_text="Switch source/target", func=self.on_switch_frames
        )

        # TODO use prefix_icons left-large-symbolic and right-large-symbolic
        self.source_frame_row = self.calc_group.add_row(
            Adw.ComboRow(
                title="Source Frame",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.target_frame_row = self.calc_group.add_row(
            Adw.ComboRow(
                title="Target Frame",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )

        self.calc_button: Gtk.Button = self.calc_group.add_row(
            Gtk.Button(
                child=Adw.ButtonContent(
                    label="Calculate transform",
                    icon_name="calculate-symbolic",
                ),
                tooltip_text="Calculate transformation from source to target",
                sensitive=False,
                margin_top=12,
                halign=Gtk.Align.CENTER,
                css_classes=["suggested-action", "pill"],
            )
        )
        self.calc_button.connect("clicked", self.on_calc_transform)

        # result row that displays the result of the calculation
        # TODO maybe make this into individual rows for each tf component (position xyz, orientation xyzw, etc) that
        # are copyable, instead of a generic text field?
        self.result_text_row = self.calc_group.add_row(TextViewRow(title="Result", show_copy_btn=True, visible=False))

        # gio store that will hold all the frames
        self.frames_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.target_frame_row.set_model(self.frames_list_store)
        self.source_frame_row.set_model(self.frames_list_store)

        # a group to display all the frames
        self.frames_group = self.pref_page.add_group(title="Frames", empty_group_text="Refresh to show frames")
        self.frames_dict = {}

    def refresh_bg(self) -> bool:
        super().show_toast("Listening to tf data for 5.0 seconds...")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.ros2_connector.node)
        time.sleep(5.0)
        self.lookup_time = self.ros2_connector.node.get_clock().now()

        # Get the frames from the buffer as YAML
        result = self.tf_buffer.all_frames_as_yaml()
        self.frames_dict = yaml.safe_load(result)

        if isinstance(self.frames_dict, dict):
            # get all the infos from the collected frames
            for frame_name, frame_info in self.frames_dict.items():
                parent_frame = frame_info["parent"]
                print(frame_info)
                trans: TransformStamped = self.tf_buffer.lookup_transform(parent_frame, frame_name, rclpy.time.Time())
                self.frames_dict[frame_name]["transform"] = trans

            self.calc_button.set_sensitive(True)
            return True
        else:
            self.frames_group.set_empty_group_text("No frames found. Refresh to try again.")
            self.calc_button.set_sensitive(False)
            return False

    def refresh_ui(self):
        # create an expander row for each frame and add all the info as rows
        frame_rows = []
        for frame_name, frame_info in self.frames_dict.items():
            expander_row: Adw.ExpanderRow = Adw.ExpanderRow(title=frame_name)

            parent_frame_row = PrefRow(title="Parent frame")
            parent_frame_row.add_suffix_lbl(frame_info["parent"])
            expander_row.add_row(parent_frame_row)

            tf_row = TextViewRow(title="Transform", show_copy_btn=True)
            tf_row.set_text(message_to_yaml(frame_info["transform"]))
            expander_row.add_row(tf_row)

            broadcaster_row = PrefRow(title="Broadcaster")
            broadcaster_row.add_suffix_lbl(frame_info["broadcaster"])
            expander_row.add_row(broadcaster_row)

            rate_row = PrefRow(title="Rate")
            rate_row.add_suffix_lbl(str(frame_info["rate"]))
            expander_row.add_row(rate_row)

            most_recent_transform_row = PrefRow(title="Most recent transform")
            most_recent_transform_row.add_suffix_lbl(str(frame_info["most_recent_transform"]))
            expander_row.add_row(most_recent_transform_row)

            oldest_transform_row = PrefRow(title="Oldest transform")
            oldest_transform_row.add_suffix_lbl(str(frame_info["oldest_transform"]))
            expander_row.add_row(oldest_transform_row)

            buffer_length_row = PrefRow(title="Buffer length")
            buffer_length_row.add_suffix_lbl(str(frame_info["buffer_length"]))
            expander_row.add_row(buffer_length_row)

            frame_rows.append(expander_row)
            self.frames_list_store.append(Gtk.StringObject.new(frame_name))

        # add all rows to the group
        self.frames_group.add_rows_idle(frame_rows)
        self.frames_group.set_description(f"Lookup time: {(self.lookup_time.nanoseconds / 1e9):.2f}")

        # Set the Gio.ListModel on the ComboRow
        if self.frames_list_store.get_n_items() > 0:
            self.source_frame_row.set_selected(0)
            self.target_frame_row.set_selected(0)

    def reset_ui(self):
        self.frames_group.clear()
        self.result_text_row.set_visible(False)
        self.frames_list_store.remove_all()

    def on_switch_frames(self, *args):
        if len(self.frames_dict) == 0:
            super().show_toast("Not enough frames to switch")
            return

        current_source_index = self.source_frame_row.get_selected()
        current_target_index = self.target_frame_row.get_selected()

        self.source_frame_row.set_selected(current_target_index)
        self.target_frame_row.set_selected(current_source_index)

    def on_calc_transform(self, *args):
        source_frame = self.source_frame_row.get_selected_item().get_string()
        target_frame = self.target_frame_row.get_selected_item().get_string()

        if source_frame == target_frame:
            super().show_toast("'source frame' and 'target frame' cannot be the same")
            return

        try:
            # Lookup transform
            transform: TransformStamped = self.tf_buffer.lookup_transform(
                target_frame=source_frame,
                source_frame=target_frame,
                time=rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=5),
            )

            # TODO check if transform is valid, eg frames are connected in some way
            # and if not give an error like "not connected" etc

            text = message_to_yaml(transform.transform)

            self.result_text_row.set_subtitle(f"from <{source_frame}> to <{target_frame}>")
            self.result_text_row.set_text(text)
            self.result_text_row.set_visible(True)

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            super().show_toast(f"Could not calculate transform: {e}")
            self.result_text_row.set_text("")
            self.result_text_row.set_visible(False)
