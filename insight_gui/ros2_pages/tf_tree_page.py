# =============================================================================
# tf_tree_page.py
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
import math
import numpy as np
from contextlib import contextmanager

import rclpy

from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile
from tf_transformations import euler_from_quaternion, quaternion_from_euler
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
from rosidl_runtime_py import message_to_yaml
from geometry_msgs.msg import TransformStamped, Vector3, Quaternion
from tf2_msgs.msg import TFMessage

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.buttons import PlayPauseButton
from insight_gui.widgets.canvas import Canvas
from insight_gui.widgets.canvas_blocks import TransformBlock

ROTATION_MODE_QUATERNION = "Quaternion"
ROTATION_MODE_EULER = "Euler Angles"

ANGLE_FORMAT_DEG = "DEG"
ANGLE_FORMAT_RAD = "RAD"


class TFTreePage(ContentPage):
    __gtype_name__ = "TFTreePage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("TF-Tree")
        super().set_refresh_fail_text("No transforms found. Refresh to try again.")

        self.content_stack.remove(self.pref_page)
        del self.pref_page

        # Create canvas
        self.canvas = Canvas()
        self.content_stack.add_child(self.canvas)

        # store received frames
        self._frames_dict = {}
        self._connections = []

    def refresh_bg(self) -> bool:
        self.canvas.clear()
        self._connections = []

        # TODO move these tf calls to the connector and enable caching
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.ros2_connector.node)
        time.sleep(5.0)
        self.lookup_time = self.ros2_connector.node.get_clock().now()

        # Get the frames from the buffer as YAML
        result = self.tf_buffer.all_frames_as_yaml()
        self._frames_dict = yaml.safe_load(result)

        if isinstance(self._frames_dict, dict):
            return len(self._frames_dict) > 0
        else:
            return False

    def refresh_ui(self):
        """Refresh the UI by building the TF tree with proper parent-child relationships."""
        # Clear previous connections
        self._connections.clear()

        # Build the TF tree structure
        for frame_name, frame_info in self._frames_dict.items():
            parent_frame = frame_info.get("parent", "")

            # Try to get transform data
            try:
                transform = self.tf_buffer.lookup_transform(parent_frame, frame_name, rclpy.time.Time())
            except (LookupException, ConnectivityException, ExtrapolationException) as e:
                self.ros2_connector.log(f"Could not get transform from {parent_frame} to {frame_name}: {e}")
                continue
            except Exception as e:
                self.ros2_connector.log(f"Unexpected error getting transform from {parent_frame} to {frame_name}: {e}")
                continue

            # Add the child frame block
            block_id = self.canvas.add_block(
                TransformBlock,
                block_args={
                    "frame_name": frame_name,
                    "parent": parent_frame,
                    "transform": transform,
                    "broadcaster": frame_info.get("broadcaster", ""),
                    "rate": frame_info.get("rate", 0.0),
                    "most_recent_transform": frame_info.get("most_recent_transform", ""),
                    "oldest_transform": frame_info.get("oldest_transform", ""),
                    "buffer_length": frame_info.get("buffer_length", 0.0),
                },
            )

            # Store connection info for later processing
            if parent_frame:  # Only add connection if parent exists
                self._connections.append((parent_frame, frame_name))

        # Create all connections between parent and child frames
        for parent_frame, child_frame in self._connections:
            parent_block = self.canvas.get_block_by_label(parent_frame)
            child_block = self.canvas.get_block_by_label(child_frame)

            if parent_block is None:
                parent_id = self.canvas.add_block(TransformBlock, block_args={"frame_name": parent_frame})
            else:
                parent_id = parent_block.uuid

            self.canvas.connect_blocks(parent_id, child_block.uuid)

        # Layout the graph and show debug banner
        self.show_banner("The TF Tree page is still experimental")  # DEBUG
        self.canvas.calculate_layout()

    def reset_ui(self):
        # self.canvas.clear()
        pass

    def trigger(self):
        # TODO
        pass
