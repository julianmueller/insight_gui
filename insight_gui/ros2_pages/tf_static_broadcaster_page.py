# =============================================================================
# tf_broadcaster_page.py
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
from geometry_msgs.msg import TransformStamped, Vector3, Quaternion
from tf2_msgs.msg import TFMessage

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.buttons import PlayPauseButton

ROTATION_MODE_QUATERNION = "Quaternion"
ROTATION_MODE_EULER = "Euler Angles"

ANGLE_FORMAT_DEG = "DEG"
ANGLE_FORMAT_RAD = "RAD"


class StaticTransformBroadcasterPage(ContentPage):
    __gtype_name__ = "StaticTransformBroadcasterPage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Transform Broadcaster")
        super().set_refresh_fail_text("No frames found. Refresh to try again.")

        # TODO add a button row that shows a dialog with a tf-tree

        # Initialize broadcaster variables
        self.static_broadcaster = None
        self.is_broadcasting = False
        self.rotation_mode = ROTATION_MODE_QUATERNION
        self.angle_format = ANGLE_FORMAT_DEG

        self.play_pause_broadcast_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_broadcasting,
                func=self.on_toggle_broadcast,
                labels=("Stop Broadcast", "Start Broadcast"),
                css_classes=["suggested-action"],
            ),
            position="start",
        )

        # Frames Group
        self.frames_group = self.pref_page.add_group(title="Frames")

        # TODO turn these into SuggestionEntryRow
        self.parent_frame_row = self.frames_group.add_row(Adw.EntryRow(title="Parent Frame", text="world"))
        self.child_frame_row = self.frames_group.add_row(Adw.EntryRow(title="Child Frame", text="my_frame"))

        # Translation inputs
        self.translation_group = self.pref_page.add_group(title="Translation", description="in meters")

        self.reset_translation_btn = self.translation_group.add_suffix_btn(
            icon_name="edit-undo-symbolic",
            tooltip_text="Reset translation values",
            func=self.reset_translation_values,
        )

        self.tx_row = self.translation_group.add_row(
            Adw.SpinRow(
                title="Translation X",
                adjustment=Gtk.Adjustment(value=0.0, lower=-10000.0, upper=10000.0, step_increment=0.01),
                digits=7,
            )
        )

        self.ty_row = self.translation_group.add_row(
            Adw.SpinRow(
                title="Translation Y",
                adjustment=Gtk.Adjustment(value=0.0, lower=-10000.0, upper=10000.0, step_increment=0.01),
                digits=7,
            )
        )

        self.tz_row = self.translation_group.add_row(
            Adw.SpinRow(
                title="Translation Z",
                adjustment=Gtk.Adjustment(value=0.0, lower=-10000.0, upper=10000.0, step_increment=0.01),
                digits=7,
            )
        )

        # Quaternion inputs
        self.rotation_group = self.pref_page.add_group(title="Rotation")

        self.norm_quat_btn = self.rotation_group.add_suffix_btn(
            icon_name="normalize-symbolic",
            tooltip_text="Normalize quaternion",
            func=self.normalize_quaternion,
        )

        self.angle_format_btn = self.rotation_group.add_suffix_btn(
            icon_name="angle-symbolic",
            tooltip_text="Switch Degree / Radians",
            func=self.on_angle_format_changed,
            visible=False,
        )

        self.rotation_mode_btn = self.rotation_group.add_suffix_btn(
            icon_name="orbit-symbolic",
            tooltip_text="Switch Quaternion / Euler Angles",
            func=self.on_rotation_mode_changed,
        )

        self.reset_rotation_btn = self.rotation_group.add_suffix_btn(
            icon_name="edit-undo-symbolic",
            tooltip_text="Reset rotation values",
            func=self.reset_rotation_values,
        )

        # Dropdown to switch between Euler and Quaternion
        # self.rotation_mode_row = self.rotation_group.add_row(
        #     Adw.ComboRow(
        #         title="Rotation Mode",
        #         model=Gtk.StringList.new([ROTATION_MODE_QUATERNION, ROTATION_MODE_EULER]),
        #         selected=0,  # Default to Quaternion # TODO make this a setting
        #     )
        # )
        # self.rotation_mode_row.connect("notify::selected-item", self.on_rotation_mode_changed)

        self.qx_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Quaternion X",
                adjustment=Gtk.Adjustment(value=0.0, lower=-1.0, upper=1.0, step_increment=0.001),
                digits=7,
            )
        )
        self.qx_row.connect("notify::value", self.update_rotation_values)

        self.qy_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Quaternion Y",
                adjustment=Gtk.Adjustment(value=0.0, lower=-1.0, upper=1.0, step_increment=0.001),
                digits=7,
            )
        )
        self.qy_row.connect("notify::value", self.update_rotation_values)

        self.qz_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Quaternion Z",
                adjustment=Gtk.Adjustment(value=0.0, lower=-1.0, upper=1.0, step_increment=0.001),
                digits=7,
            )
        )
        self.qz_row.connect("notify::value", self.update_rotation_values)

        self.qw_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Quaternion W",
                adjustment=Gtk.Adjustment(value=1.0, lower=-1.0, upper=1.0, step_increment=0.001),
                digits=7,
            )
        )
        self.qw_row.connect("notify::value", self.update_rotation_values)

        # self.angle_format_row = self.rotation_group.add_row(
        #     Adw.ComboRow(
        #         title="Angle Format",
        #         model=Gtk.StringList.new([ANGLE_FORMAT_DEG, ANGLE_FORMAT_RAD]),  # TODO make this a setting
        #         selected=0,
        #         visible=False,
        #     )
        # )
        # self.angle_format_row.connect("notify::selected-item", self.on_angle_format_changed)

        self.roll_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Roll (X)",
                adjustment=Gtk.Adjustment(value=0.0, lower=-360.0, upper=360.0, step_increment=0.1),
                digits=7,
                wrap=True,
                visible=False,
            )
        )
        self.roll_row.connect("notify::value", self.update_rotation_values)
        self.roll_row_suffix_lbl = Gtk.Label(label=ANGLE_FORMAT_DEG)
        self.roll_row.add_suffix(self.roll_row_suffix_lbl)

        self.pitch_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Pitch (Y)",
                adjustment=Gtk.Adjustment(value=0.0, lower=-360.0, upper=360.0, step_increment=0.1),
                digits=7,
                wrap=True,
                visible=False,
            )
        )
        self.pitch_row.connect("notify::value", self.update_rotation_values)
        self.pitch_row_suffix_lbl = Gtk.Label(label=ANGLE_FORMAT_DEG)
        self.pitch_row.add_suffix(self.pitch_row_suffix_lbl)

        self.yaw_row = self.rotation_group.add_row(
            Adw.SpinRow(
                title="Yaw (Z)",
                adjustment=Gtk.Adjustment(value=0.0, lower=-360.0, upper=360.0, step_increment=0.1),
                digits=7,
                wrap=True,
                visible=False,
            )
        )
        self.yaw_row.connect("notify::value", self.update_rotation_values)
        self.yaw_row_suffix_lbl = Gtk.Label(label=ANGLE_FORMAT_DEG)
        self.yaw_row.add_suffix(self.yaw_row_suffix_lbl)

    def get_translation(self) -> tuple[float, float, float]:
        tx = self.tx_row.get_value()
        ty = self.ty_row.get_value()
        tz = self.tz_row.get_value()
        return (tx, ty, tz)

    def set_translation(self, tx: float, ty: float, tz: float):
        self.tx_row.set_value(tx)
        self.ty_row.set_value(ty)
        self.tz_row.set_value(tz)

    def get_quat_rotation(self) -> tuple[float, float, float, float]:
        qx = self.qx_row.get_value()
        qy = self.qy_row.get_value()
        qz = self.qz_row.get_value()
        qw = self.qw_row.get_value()
        return (qx, qy, qz, qw)

    def set_quat_rotation(self, qx: float, qy: float, qz: float, qw: float):
        with self.freeze_rotation_row_notifies():
            self.qx_row.set_value(qx)
            self.qy_row.set_value(qy)
            self.qz_row.set_value(qz)
            self.qw_row.set_value(qw)

    def get_euler_rotation(self) -> tuple[float, float, float]:
        r = self.roll_row.get_value()
        p = self.pitch_row.get_value()
        y = self.yaw_row.get_value()
        return (r, p, y)

    def set_euler_rotation(self, r: float, p: float, y: float):
        with self.freeze_rotation_row_notifies():
            self.roll_row.set_value(r)
            self.pitch_row.set_value(p)
            self.yaw_row.set_value(y)

    def refresh_bg(self) -> bool:
        # super().show_toast("Listening to tf data for 5.0 seconds...")

        # self.tf_buffer = Buffer()
        # self.tf_listener = TransformListener(self.tf_buffer, self.ros2_connector.node)
        # time.sleep(5.0)
        # self.lookup_time = self.ros2_connector.node.get_clock().now()

        # # Get the frames from the buffer as YAML
        # result = self.tf_buffer.all_frames_as_yaml()
        # self.frames_dict = yaml.safe_load(result)

        # TODO add suggestions for parent frame and make it, that child frame cannot be the same name as an existing frame

        # if isinstance(self.frames_dict, dict):
        #     # get all the infos from the collected frames
        #     for frame_name, frame_info in self.frames_dict.items():
        #         parent_frame = frame_info["parent"]
        #         trans: TransformStamped = self.tf_buffer.lookup_transform(parent_frame, frame_name, rclpy.time.Time())
        #         self.frames_dict[frame_name]["transform"] = trans

        #     # self.calc_button.set_sensitive(True)
        #     return True
        # else:
        #     # self.frames_group.set_empty_group_text("No frames found. Refresh to try again.")
        #     # self.calc_button.set_sensitive(False)
        #     return False
        return True

    def refresh_ui(self):
        pass
        # # Set the Gio.ListModel on the ComboRow
        # if self.frames_list_store.get_n_items() > 0:
        #     self.source_frame_row.set_selected(0)
        #     self.target_frame_row.set_selected(0)

    def reset_ui(self):
        self.reset_translation_values()
        self.reset_rotation_values()

    def trigger(self):
        # TODO
        pass

    def on_toggle_broadcast(self, *args):
        self.is_broadcasting = self.play_pause_broadcast_btn.playing
        self.toggle_row_sensitivity(sensitive=not self.is_broadcasting)

        if self.is_broadcasting:
            try:
                # Get values from the input fields
                parent_frame = self.parent_frame_row.get_text().strip()
                child_frame = self.child_frame_row.get_text().strip()

                if not parent_frame:
                    super().show_toast("Parent frame name cannot be empty")
                    return

                if not child_frame:
                    super().show_toast("Child frame name cannot be empty")
                    return

                if parent_frame == child_frame:
                    super().show_toast("Parent frame and child frame cannot be the same")
                    return

                # see https://github.com/ros2/geometry2/blob/rolling/tf2_ros_py/tf2_ros/static_transform_broadcaster.py
                self.static_broadcaster = self.ros2_connector.add_publisher(
                    msg_type=TFMessage,
                    topic_name="/tf_static",
                    qos_profile=QoSProfile(
                        depth=1,
                        durability=DurabilityPolicy.TRANSIENT_LOCAL,
                        history=HistoryPolicy.KEEP_LAST,
                    ),
                )

                # Send the transform
                tf = self.make_transform()
                self.static_broadcaster.publish(TFMessage(transforms=[tf]))

            except Exception as e:
                super().show_toast(f"Failed to start broadcasting: {e}")

        else:
            self.ros2_connector.destroy_publisher(self.static_broadcaster)

    def normalize_quaternion(self):
        qx, qy, qz, qw = self.get_quat_rotation()
        norm = (qx**2 + qy**2 + qz**2 + qw**2) ** 0.5

        if norm > 0:
            self.set_quat_rotation(qx / norm, qy / norm, qz / norm, qw / norm)
        else:
            super().show_toast("Cannot normalize zero quaternion")

    def make_transform(self) -> TransformStamped:
        # create transform message
        transform = TransformStamped()
        transform.header.stamp = self.ros2_connector.node.get_clock().now().to_msg()
        transform.header.frame_id = self.parent_frame_row.get_text().strip()
        transform.child_frame_id = self.child_frame_row.get_text().strip()

        # set translation
        tx, ty, tz = self.get_translation()
        transform.transform.translation = Vector3(x=tx, y=ty, z=tz)

        # set rotation
        self.normalize_quaternion()
        qx, qy, qz, qw = self.get_quat_rotation()
        transform.transform.rotation = Quaternion(x=qx, y=qy, z=qz, w=qw)

        return transform

    def on_rotation_mode_changed(self, *args):
        # self.rotation_mode = self.rotation_mode_row.get_selected_item().get_string()
        self.rotation_mode = (
            ROTATION_MODE_EULER if self.rotation_mode == ROTATION_MODE_QUATERNION else ROTATION_MODE_QUATERNION
        )
        rotation_mode_is_quat = self.rotation_mode == ROTATION_MODE_QUATERNION

        self.qx_row.set_visible(rotation_mode_is_quat)
        self.qy_row.set_visible(rotation_mode_is_quat)
        self.qz_row.set_visible(rotation_mode_is_quat)
        self.qw_row.set_visible(rotation_mode_is_quat)
        self.norm_quat_btn.set_visible(rotation_mode_is_quat)

        # self.angle_format_row.set_visible(not rotation_mode_is_quat)
        self.angle_format_btn.set_visible(not rotation_mode_is_quat)
        self.roll_row.set_visible(not rotation_mode_is_quat)
        self.pitch_row.set_visible(not rotation_mode_is_quat)
        self.yaw_row.set_visible(not rotation_mode_is_quat)

        if not rotation_mode_is_quat:
            if self.angle_format == ANGLE_FORMAT_DEG:
                self.rotation_group.set_description("RPY rotation in the order (Z-Y-X)")
            else:
                self.rotation_group.set_description("RPY rotation in the order (Z-Y-X)")
        else:
            self.rotation_group.set_description("")

    def on_angle_format_changed(self, *args):
        # self.angle_format = self.angle_format_row.get_selected_item().get_string()
        self.angle_format = ANGLE_FORMAT_DEG if self.angle_format == ANGLE_FORMAT_RAD else ANGLE_FORMAT_RAD
        angle_format_is_deg = self.angle_format == ANGLE_FORMAT_DEG

        if angle_format_is_deg:
            self.set_euler_rotation(*map(np.rad2deg, self.get_euler_rotation()))
            self.roll_row_suffix_lbl.set_label(ANGLE_FORMAT_DEG)
            self.pitch_row_suffix_lbl.set_label(ANGLE_FORMAT_DEG)
            self.yaw_row_suffix_lbl.set_label(ANGLE_FORMAT_DEG)

        else:
            self.set_euler_rotation(*map(np.deg2rad, self.get_euler_rotation()))
            self.roll_row_suffix_lbl.set_label(ANGLE_FORMAT_RAD)
            self.pitch_row_suffix_lbl.set_label(ANGLE_FORMAT_RAD)
            self.yaw_row_suffix_lbl.set_label(ANGLE_FORMAT_RAD)

    def reset_translation_values(self, *args):
        self.set_translation(0, 0, 0)

    def update_rotation_values(self, *args):
        rotation_mode_is_quat = self.rotation_mode == ROTATION_MODE_QUATERNION
        angle_format_is_deg = self.angle_format == ANGLE_FORMAT_DEG

        # rotations are currently displayed as quaternions
        if rotation_mode_is_quat:
            r, p, y = euler_from_quaternion(self.get_quat_rotation(), axes="sxyz")
            if angle_format_is_deg:
                r, p, y = map(np.rad2deg, (r, p, y))
            self.set_euler_rotation(r, p, y)

        # rotations are currently displayed as euler angles
        else:
            r, p, y = self.get_euler_rotation()
            if angle_format_is_deg:
                r, p, y = map(np.deg2rad, (r, p, y))

            # TODO make the rotation-axis-order also changeable
            qx, qy, qz, qw = quaternion_from_euler(r, p, y, axes="sxyz")
            self.set_quat_rotation(qx, qy, qz, qw)

    def reset_rotation_values(self, *args):
        self.set_quat_rotation(0, 0, 0, 1)
        self.set_euler_rotation(0, 0, 0)

    def toggle_row_sensitivity(self, sensitive: bool):
        self.parent_frame_row.set_sensitive(sensitive)
        self.child_frame_row.set_sensitive(sensitive)

        self.reset_translation_btn.set_sensitive(sensitive)
        self.tx_row.set_sensitive(sensitive)
        self.ty_row.set_sensitive(sensitive)
        self.tz_row.set_sensitive(sensitive)

        # self.rotation_mode_row.set_sensitive(sensitive)
        self.rotation_mode_btn.set_sensitive(sensitive)
        self.norm_quat_btn.set_sensitive(sensitive)
        self.reset_rotation_btn.set_sensitive(sensitive)
        self.qx_row.set_sensitive(sensitive)
        self.qy_row.set_sensitive(sensitive)
        self.qz_row.set_sensitive(sensitive)
        self.qw_row.set_sensitive(sensitive)

        # self.angle_format_row.set_sensitive(sensitive)
        self.angle_format_btn.set_sensitive(sensitive)
        self.roll_row.set_sensitive(sensitive)
        self.pitch_row.set_sensitive(sensitive)
        self.yaw_row.set_sensitive(sensitive)

    @contextmanager
    def freeze_rotation_row_notifies(self):
        try:
            self.qx_row.freeze_notify()
            self.qy_row.freeze_notify()
            self.qz_row.freeze_notify()
            self.qw_row.freeze_notify()

            self.roll_row.freeze_notify()
            self.pitch_row.freeze_notify()
            self.yaw_row.freeze_notify()

            yield

        finally:
            self.qx_row.thaw_notify()
            self.qy_row.thaw_notify()
            self.qz_row.thaw_notify()
            self.qw_row.thaw_notify()

            self.roll_row.thaw_notify()
            self.pitch_row.thaw_notify()
            self.yaw_row.thaw_notify()
