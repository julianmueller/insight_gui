# =============================================================================
# teleop_page.py
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

from geometry_msgs.msg import Vector3, Twist
from sensor_msgs.msg import Joy

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import AdditionalContentRow


class TeleopDirection(GObject.GObject):
    __gtype_name__ = "TeleopDirection"
    # Forward: x = 1
    # Left: y = 1
    # (row, col):
    # (0,0) ↖    (0,1) ↑    (0,2) ↗
    # (1,0) ←    (1,1) •    (1,2) →
    # (2,0) ↙    (2,1) ↓    (2,2) ↘

    x = GObject.Property(type=float)
    y = GObject.Property(type=float)

    def __init__(self, x: float = 0.0, y: float = 0.0):
        super().__init__()
        self.x = x
        self.y = y


class TeleoperatorPage(ContentPage):
    __gtype_name__ = "TeleoperatorPage"

    def __init__(self, preselect_teleop_topic: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Teleoperator")
        super().set_refresh_fail_text("No teleop topics found. Refresh to try again.")

        self.preselect_teleop_topic = preselect_teleop_topic
        # ros2 run teleop_twist_keyboard teleop_twist_keyboard
        # ros2 run teleop_twist_joy teleop_twist_joy

        # TODO add
        # - scaling for linear and angular
        # - switch btw dpad and joystick controls
        self.pub = None

        self.topic_group = self.pref_page.add_group(title="Teleop Topic", filterable=False)
        self.topic_row: Adw.EntryRow = self.topic_group.add_row(Adw.EntryRow(title="Topic", show_apply_button=True))
        self.topic_row.connect("apply", self.on_topic_name_applied)
        self.topic_name = ""

        self.teleop_type_row = self.topic_group.add_row(
            Adw.ComboRow(
                title="Teleop Type",
                enable_search=False,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.teleop_type_row.connect("notify::selected-item", self.on_teleop_type_changed)

        # Create a Gio.ListStore to fill the ComboBox with
        self.TELEOP_TYPE_TWIST = "geometry_msgs/msg/Twist"
        self.TELEOP_TYPE_JOY = "sensor_msgs/msg/Joy"
        self.teleop_type_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.teleop_type_list_store.append(Gtk.StringObject.new(self.TELEOP_TYPE_TWIST))
        self.teleop_type_list_store.append(Gtk.StringObject.new(self.TELEOP_TYPE_JOY))
        self.teleop_type_row.set_model(self.teleop_type_list_store)
        self.teleop_type = self.TELEOP_TYPE_TWIST

        self.teleop_group = self.pref_page.add_group(title="Teleoperation", filterable=False)
        self.teleop_row = self.teleop_group.add_row(TeleopRow())
        self.teleop_row.connect("teleop-dir-changed", self.on_teleop_btns)

        # TODO
        self.linear_scaling = 1.0
        self.angular_scaling = 1.0

    def remove_pub(self):
        # TODO remove the pub
        pass

    def on_topic_name_applied(self, *args):
        self.topic_name = self.topic_row.get_text()
        print(f"publishing to: {self.topic_name}")

        if self.topic_name:
            # TODO check if topic with this name already exists

            if self.teleop_type == self.TELEOP_TYPE_TWIST:
                self.pub = self.ros2_connector.add_publisher(Twist, self.topic_name)
            elif self.teleop_type == self.TELEOP_TYPE_JOY:
                self.pub = self.ros2_connector.add_publisher(Joy, self.topic_name)

    def on_teleop_type_changed(self, *args):
        if self.pub:
            self.remove_pub()
        self.teleop_type = self.teleop_type_row.get_selected_item().get_string()

        if self.topic_name:
            # TODO check if topic with this name already exists

            if self.teleop_type == self.TELEOP_TYPE_TWIST:
                self.pub = self.ros2_connector.add_publisher(Twist, self.topic_name)
            elif self.teleop_type == self.TELEOP_TYPE_JOY:
                self.pub = self.ros2_connector.add_publisher(Joy, self.topic_name)
        # else:
        #     self.teleop_row.disable()

    def on_teleop_btns(self, btn: Gtk.Button, teleop_dir: TeleopDirection):
        if not self.topic_name:
            self.show_toast("No topic to publish to")
            return

        linear = Vector3(x=self.linear_scaling * teleop_dir.x)
        angular = Vector3(z=self.angular_scaling * teleop_dir.y)
        self.publish_twist(linear=linear, angular=angular)

    def publish_twist(self, linear: Vector3, angular: Vector3):
        if not self.pub:
            self.show_toast("no pub")

        twist = Twist()
        twist.linear = linear
        twist.angular = angular
        self.pub.publish(twist)


class TeleopRow(AdditionalContentRow):
    __gtype_name__ = "TeleopRow"
    __gsignals__ = {"teleop-dir-changed": (GObject.SignalFlags.RUN_FIRST, None, (TeleopDirection.__gtype__,))}

    def __init__(self, title="Teleoperator", **kwargs):
        super().__init__(title=title, **kwargs)
        super().grab_focus()

        self.grid: Gtk.Grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
            hexpand=True,
            vexpand=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.content_box.append(self.grid)

        # Buttons
        self.btns = []
        self.btn_nw = self._add_btn(icon_name="arrow2-top-left-symbolic", x_dir=1.0, y_dir=1.0)  # label="↖"
        self.btn_n = self._add_btn(icon_name="arrow2-up-symbolic", x_dir=1.0, y_dir=0.0)  # label="↑"
        self.btn_ne = self._add_btn(icon_name="arrow2-top-right-symbolic", x_dir=1.0, y_dir=-1.0)  # label="↗"
        self.btn_e = self._add_btn(icon_name="arrow2-right-symbolic", x_dir=0.0, y_dir=-1.0)  # label="→"
        self.btn_se = self._add_btn(icon_name="arrow2-bottom-right-symbolic", x_dir=-1.0, y_dir=-1.0)  # label="↘"
        self.btn_s = self._add_btn(icon_name="arrow2-down-symbolic", x_dir=-1.0, y_dir=0.0)  # label="↓"
        self.btn_sw = self._add_btn(icon_name="arrow2-bottom-left-symbolic", x_dir=-1.0, y_dir=1.0)  # label="↙"
        self.btn_w = self._add_btn(icon_name="arrow2-left-symbolic", x_dir=0.0, y_dir=1.0)  # label="←"

        self.btn_stop = self._add_btn(
            icon_name="cross-small-circle-outline-symbolic", x_dir=0.0, y_dir=0.0
        )  # label="•"

        # add key controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        key_controller.connect("key-released", self.on_key_released)
        self.add_controller(key_controller)
        self._allowed_keys = (Gdk.KEY_uparrow, Gdk.KEY_downarrow, Gdk.KEY_leftarrow, Gdk.KEY_rightarrow)
        self._held_keys = set()

        # make it focus when clicked on it
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", lambda c, n, x, y: self.grab_focus())
        self.add_controller(click_controller)

        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self.on_focus_out)
        self.add_controller(focus_controller)

        # self.disable()

    def _add_btn(self, icon_name: str, x_dir: float, y_dir: float) -> Gtk.Button:
        btn = Gtk.Button(icon_name=icon_name, width_request=80, height_request=80, can_focus=False)
        btn.connect("clicked", self._btn_callback, TeleopDirection(x_dir, y_dir))

        # Dynamically calculate position in grid
        row = int(1 - x_dir)
        col = int(1 - y_dir)

        self.grid.attach(btn, col, row, 1, 1)
        self.btns.append(btn)
        return btn

    def _btn_callback(self, btn, teleop_dir: TeleopDirection):
        self.emit("teleop-dir-changed", teleop_dir)

    def on_focus_out(self, *args):
        GLib.idle_add(self.grab_focus)  # Avoid recursion crash by delaying
        return False

    def on_key_pressed(self, controller, keyval, keycode, state):
        # if keyval not in self._allowed_keys:
        #     return False

        if keycode not in self._held_keys:
            self._held_keys.add(keycode)
        self._emit_from_keys()
        return True

    def on_key_released(self, controller, keyval, keycode, state):
        # if keyval not in self._allowed_keys:
        #     return False
        print(keycode)  # TODO rework

        if keycode in self._held_keys:
            self._held_keys.remove(keycode)
        self._emit_from_keys()
        return True

    def _emit_from_keys(self):
        x = 0.0
        y = 0.0
        print(self._held_keys)

        print(Gdk.KEY_uparrow)

        if Gdk.KEY_uparrow in self._held_keys:
            x += 1.0
        if Gdk.KEY_downarrow in self._held_keys:
            x -= 1.0
        if Gdk.KEY_leftarrow in self._held_keys:
            y += 1.0
        if Gdk.KEY_rightarrow in self._held_keys:
            y -= 1.0

        print(x, y)
        # /turtle1/cmd_vel

        self.emit("teleop-dir-changed", TeleopDirection(x=x, y=y))

    def enable(self):
        for btn in self.btns:
            btn.set_sensitive(True)

    def disable(self):
        for btn in self.btns:
            btn.set_sensitive(False)
