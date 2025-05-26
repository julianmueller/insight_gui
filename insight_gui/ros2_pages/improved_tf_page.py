# =============================================================================
# improved_tf_page.py
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
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
from geometry_msgs.msg import TransformStamped
from rosidl_runtime_py import message_to_yaml

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.widgets.improved_content_page import ImprovedContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow


class ImprovedTransformsPage(ImprovedContentPage):
    """
    Improved version of TransformsPage using the new async task manager.

    This demonstrates how to refactor existing pages to use the improved
    async patterns and reduce GLib.idle_add complexity.
    """

    __gtype_name__ = "ImprovedTransformsPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Transforms (Improved)")
        super().set_search_entry_placeholder_text("Search for Frames")
        super().set_refresh_fail_text("No frames found. Refresh to try again.")

        # TF-related attributes
        self.tf_buffer = None
        self.tf_listener = None
        self.frames_dict = {}
        self.lookup_time = None

        # Task IDs for async operations
        self._tf_listen_task_id = f"{self.__class__.__name__}_tf_listen"
        self._transform_calc_task_id = f"{self.__class__.__name__}_transform_calc"

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Calculate transform group
        self.calc_group = self.pref_page.add_group(title="Calculate Transform", filterable=False)
        self.calc_group.add_suffix_btn(
            icon_name="vertical-arrows-symbolic", tooltip_text="Switch source/target", func=self.on_switch_frames
        )

        # Source and target frame selection
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

        # Calculate button
        self.calc_button: ButtonRow = self.calc_group.add_row(
            ButtonRow(
                label="Calculate transform",
                start_icon_name="gnome-calculator-symbolic",
                tooltip_text="Calculate transformation from source to target",
                func=self.on_calc_transform,
                sensitive=False,
            )
        )

        # Result display
        self.result_text_row = self.calc_group.add_row(TextViewRow(title="Result", show_copy_btn=True, visible=False))

        # Frame list store for combo boxes
        self.frames_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.target_frame_row.set_model(self.frames_list_store)
        self.source_frame_row.set_model(self.frames_list_store)

        # Frames display group
        self.frames_group = self.pref_page.add_group(title="Frames", empty_group_text="Refresh to show frames")

    def refresh_bg(self) -> bool:
        """
        Background refresh operation - listens to TF data.

        This runs in a background thread and should not update the UI directly.
        """
        try:
            # Show progress to user
            self.schedule_ui_update("tf_progress", self.show_toast, "Listening to tf data for 5.0 seconds...")

            # Set up TF buffer and listener
            self.tf_buffer = Buffer()
            self.tf_listener = TransformListener(self.tf_buffer, self.ros2_connector.node)

            # Listen for TF data
            time.sleep(5.0)
            self.lookup_time = self.ros2_connector.node.get_clock().now()

            # Get frames as YAML
            result = self.tf_buffer.all_frames_as_yaml()
            frames_dict = yaml.safe_load(result)

            if not isinstance(frames_dict, dict):
                return False

            # Get transform information for each frame
            for frame_name, frame_info in frames_dict.items():
                try:
                    parent_frame = frame_info["parent"]
                    trans: TransformStamped = self.tf_buffer.lookup_transform(
                        parent_frame, frame_name, rclpy.time.Time()
                    )
                    frames_dict[frame_name]["transform"] = trans
                except Exception as e:
                    print(f"Failed to get transform for {frame_name}: {e}")
                    continue

            # Store results
            self.frames_dict = frames_dict
            return True

        except Exception as e:
            print(f"TF refresh error: {e}")
            return False

    def refresh_ui(self):
        """Update UI with refresh results."""
        if not self.frames_dict:
            return

        # Create frame rows
        frame_rows = []
        for frame_name, frame_info in self.frames_dict.items():
            expander_row = self._create_frame_expander_row(frame_name, frame_info)
            frame_rows.append(expander_row)
            self.frames_list_store.append(Gtk.StringObject.new(frame_name))

        # Add rows to the group using batched updates
        self.frames_group.add_rows_idle(frame_rows)
        self.frames_group.set_description(f"Lookup time: {(self.lookup_time.nanoseconds / 1e9):.2f}")

        # Set default selections
        if self.frames_list_store.get_n_items() > 0:
            self.source_frame_row.set_selected(0)
            self.target_frame_row.set_selected(0)
            self.calc_button.set_sensitive(True)

    def _create_frame_expander_row(self, frame_name: str, frame_info: dict) -> Adw.ExpanderRow:
        """Create an expander row for a frame."""
        expander_row = Adw.ExpanderRow(title=frame_name)

        # Parent frame
        parent_frame_row = PrefRow(title="Parent frame")
        parent_frame_row.add_suffix_lbl(frame_info["parent"])
        expander_row.add_row(parent_frame_row)

        # Transform
        if "transform" in frame_info:
            tf_row = TextViewRow(title="Transform", show_copy_btn=True)
            tf_row.set_text(message_to_yaml(frame_info["transform"]))
            expander_row.add_row(tf_row)

        # Broadcaster
        broadcaster_row = PrefRow(title="Broadcaster")
        broadcaster_row.add_suffix_lbl(frame_info["broadcaster"])
        expander_row.add_row(broadcaster_row)

        # Rate
        rate_row = PrefRow(title="Rate")
        rate_row.add_suffix_lbl(str(frame_info["rate"]))
        expander_row.add_row(rate_row)

        # Timestamps
        most_recent_row = PrefRow(title="Most recent transform")
        most_recent_row.add_suffix_lbl(str(frame_info["most_recent_transform"]))
        expander_row.add_row(most_recent_row)

        oldest_row = PrefRow(title="Oldest transform")
        oldest_row.add_suffix_lbl(str(frame_info["oldest_transform"]))
        expander_row.add_row(oldest_row)

        # Buffer length
        buffer_length_row = PrefRow(title="Buffer length")
        buffer_length_row.add_suffix_lbl(str(frame_info["buffer_length"]))
        expander_row.add_row(buffer_length_row)

        return expander_row

    def reset_ui(self):
        """Reset UI before refresh."""
        self.frames_group.clear()
        self.result_text_row.set_visible(False)
        self.frames_list_store.remove_all()
        self.calc_button.set_sensitive(False)

    def on_switch_frames(self, *args):
        """Switch source and target frames."""
        if len(self.frames_dict) == 0:
            self.show_toast("Not enough frames to switch")
            return

        current_source_index = self.source_frame_row.get_selected()
        current_target_index = self.target_frame_row.get_selected()

        self.source_frame_row.set_selected(current_target_index)
        self.target_frame_row.set_selected(current_source_index)

    def on_calc_transform(self, *args):
        """Calculate transform between selected frames."""
        if not self.tf_buffer:
            self.show_toast("No TF data available. Please refresh first.")
            return

        source_frame = self.source_frame_row.get_selected_item().get_string()
        target_frame = self.target_frame_row.get_selected_item().get_string()

        if source_frame == target_frame:
            self.show_toast("'source frame' and 'target frame' cannot be the same")
            return

        # Run transform calculation in background
        def calculate_transform():
            """Background task to calculate transform."""
            try:
                transform: TransformStamped = self.tf_buffer.lookup_transform(
                    target_frame=source_frame,
                    source_frame=target_frame,
                    time=rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=5),
                )
                return transform.transform
            except (LookupException, ConnectivityException, ExtrapolationException) as e:
                raise Exception(f"Could not calculate transform: {e}")

        def on_transform_success(transform):
            """Handle successful transform calculation."""
            text = message_to_yaml(transform)
            self.result_text_row.set_subtitle(f"from <{source_frame}> to <{target_frame}>")
            self.result_text_row.set_text(text)
            self.result_text_row.set_visible(True)

        def on_transform_error(error):
            """Handle transform calculation error."""
            self.show_toast(str(error))
            self.result_text_row.set_text("")
            self.result_text_row.set_visible(False)

        # Run the calculation asynchronously
        self.run_background_task(
            task_id=self._transform_calc_task_id,
            background_func=calculate_transform,
            success_callback=on_transform_success,
            error_callback=on_transform_error,
        )

    def on_unrealize(self, *args):
        """Clean up when page is unrealized."""
        super().on_unrealize(*args)
        # Cancel any running tasks
        self.cancel_task(self._tf_listen_task_id)
        self.cancel_task(self._transform_calc_task_id)
