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

from rosidl_runtime_py import (
    message_to_yaml,
    message_to_csv,
    message_to_ordereddict,
    get_message_interfaces,
    set_message_fields,
)
from rosidl_runtime_py.utilities import get_message
from rclpy.validate_full_topic_name import validate_full_topic_name
from rclpy.exceptions import InvalidTopicNameException

from geometry_msgs.msg import Vector3, Twist
from sensor_msgs.msg import Joy

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, Gdk, GLib, Pango

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import AdditionalContentRow, SuggestionEntryRow
from insight_gui.widgets.buttons import ToggleButton
from insight_gui.utils.gtk_utils import find_str_in_list_store


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

    def __init__(self, preselect_topic: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Teleoperator")
        super().set_refresh_fail_text("No teleop topics found. Refresh to try again.")

        self.preselect_topic = preselect_topic
        self.detach_kwargs = {"preselect_topic": preselect_topic}
        # ros2 run teleop_twist_keyboard teleop_twist_keyboard
        # ros2 run teleop_twist_joy teleop_twist_joy

        # TODO add
        # - scaling for linear and angular
        # - switch btw dpad and joystick controls
        self.pub = None
        self.is_focus_locked = False
        self.lock_toggle_btn = None

        self.topic_group = self.pref_page.add_group(title="Teleop Topic", filterable=False)
        self.topic_row = self.topic_group.add_row(SuggestionEntryRow(title="Topic"))
        self.topic_row.connect("apply", self.on_topic_name_applied)
        self.topic_row.connect("suggestion-apply", self.on_topic_suggestion_applied)
        self.topic_name = ""
        self.teleop_topic_list_store: Gio.ListStore = self.topic_row.list_store

        self.teleop_type_row = self.topic_group.add_row(
            Adw.ComboRow(
                title="Teleop Type",
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.teleop_type_row.connect("notify::selected-item", self.on_teleop_type_changed)

        # Create a Gio.ListStore to fill the ComboBox with
        self.TELEOP_TYPE_TWIST = "geometry_msgs/msg/Twist"
        self.TELEOP_TYPE_JOY = "sensor_msgs/msg/Joy"
        self.teleop_type = self.TELEOP_TYPE_TWIST

        self.teleop_type_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.teleop_type_list_store.append(Gtk.StringObject.new(self.TELEOP_TYPE_TWIST))
        self.teleop_type_list_store.append(Gtk.StringObject.new(self.TELEOP_TYPE_JOY))
        self.teleop_type_row.set_model(self.teleop_type_list_store)

        def _on_factory_setup(factory, list_item):
            lbl = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=50)
            list_item.set_child(lbl)

        def _on_factory_bind(factory, list_item):
            lbl = list_item.get_child()
            itm = list_item.get_item()
            lbl.set_text(itm.get_string())

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)
        self.teleop_type_row.set_factory(factory)

        self.teleop_group = self.pref_page.add_group(title="Teleoperation", filterable=False)
        self.lock_toggle_btn = ToggleButton(
            func=self.on_lock_focus,
            default_active=False,
            icon_names=("padlock2-symbolic", "padlock2-open-symbolic"),
            tooltip_texts=("Unlock focus", "Lock focus for keyboard teleoperation"),
        )
        self.teleop_group.add_suffix_widget(self.lock_toggle_btn)

        self.teleop_row: TeleopRow = self.teleop_group.add_row(TeleopRow())
        self.teleop_row.connect("teleop-dir-changed", self.on_teleop_btns)
        self.teleop_row.teleop_page = self  # Set parent reference

        # TODO
        self.linear_scaling = 1.0
        self.angular_scaling = 1.0

    def refresh_bg(self) -> bool:
        available_topics = self.ros2_connector.get_available_topics()
        self.available_teleop_topics = []

        for topic_name, topic_types in available_topics:
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            if topic_types == self.TELEOP_TYPE_TWIST or topic_types == self.TELEOP_TYPE_JOY:
                self.available_teleop_topics.append(topic_name)

        return len(self.available_teleop_topics) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available topics
        for topic_name in self.available_teleop_topics:
            self.teleop_topic_list_store.append(Gtk.StringObject.new(topic_name))

        # set the selected service to the preselected one
        found_index = find_str_in_list_store(self.teleop_topic_list_store, self.preselect_topic)
        if found_index >= 0:
            self.topic_row.set_text(self.preselect_topic)
        else:
            self.topic_row.set_text("")

    def reset_ui(self):
        if self.is_focus_locked:
            self.unlock_focus()
        self.teleop_topic_list_store.remove_all()
        self.teleop_row.disable()
        self.remove_pub()

    def create_pub(self):
        if self.pub:
            self.remove_pub()

        self.topic_name = self.topic_row.get_text()  # equals item_text
        if not self.topic_name:
            self.show_toast("No topic name set")
            return

        try:
            validate_full_topic_name(self.topic_name)
        except InvalidTopicNameException as e:
            self.topic_row.set_text("")
            self.topic_name = None
            super().show_toast(e)
            return

        if self.teleop_type == self.TELEOP_TYPE_TWIST:
            self.pub = self.ros2_connector.add_publisher(Twist, self.topic_name)
        elif self.teleop_type == self.TELEOP_TYPE_JOY:
            self.pub = self.ros2_connector.add_publisher(Joy, self.topic_name)

    def remove_pub(self):
        if self.pub:
            self.ros2_connector.destroy_publisher(self.pub)
            self.pub = None

    def on_topic_name_applied(self, *args):
        self.create_pub()
        self.teleop_row.enable()

    def on_topic_suggestion_applied(self, _, item_text: str):
        try:
            msg_class = self.ros2_connector.get_message_class(topic_name=item_text)
            selected_topic_type = self.ros2_connector.get_message_type_name(msg_class)
            found_index = find_str_in_list_store(self.teleop_type_list_store, selected_topic_type)
            if found_index >= 0:
                self.teleop_type_row.set_selected(found_index)
                self.teleop_type_row.set_sensitive(False)
            else:
                self.teleop_type_row.set_selected(0)
                super().show_toast(f"There seems to be a problem with the topic type: {selected_topic_type}")

            self.create_pub()
            self.teleop_row.enable()

        except InvalidTopicNameException as e:
            self.topic_row.set_text("")
            self.topic_name = None
            super().show_toast(e)

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

        # TODO make joy also work
        linear = Vector3(x=self.linear_scaling * teleop_dir.x)
        angular = Vector3(z=self.angular_scaling * teleop_dir.y)
        self.publish_twist(linear=linear, angular=angular)

    def on_lock_focus(self, btn: ToggleButton, is_active: bool):
        self.is_focus_locked = is_active
        if is_active:
            self.teleop_row.lock_focus()
        else:
            self.teleop_row.unlock_focus()

    def unlock_focus(self):
        self.is_focus_locked = False
        self.lock_toggle_btn.set_active(False)

    def publish_twist(self, linear: Vector3, angular: Vector3):
        if not self.pub:
            self.show_toast("No publisher available")
            return

        twist = Twist()
        twist.linear = linear
        twist.angular = angular
        self.pub.publish(twist)


class TeleopRow(AdditionalContentRow):
    __gtype_name__ = "TeleopRow"
    __gsignals__ = {"teleop-dir-changed": (GObject.SignalFlags.RUN_FIRST, None, (TeleopDirection.__gtype__,))}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_focusable(True)
        super().set_can_focus(True)
        super().set_focus_on_click(True)

        self.is_focus_locked = False
        self.teleop_page = None  # Will be set by parent

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

        self._allowed_keys = (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Escape)
        self._held_keys = set()

        # self.disable()

    def _add_btn(self, icon_name: str, x_dir: float, y_dir: float) -> Gtk.Button:
        btn = Gtk.Button(icon_name=icon_name, width_request=100, height_request=100, can_focus=False)
        btn.connect("clicked", self._btn_callback, TeleopDirection(x_dir, y_dir))

        # Dynamically calculate position in grid
        row = int(1 - x_dir)
        col = int(1 - y_dir)

        self.grid.attach(btn, col, row, 1, 1)
        self.btns.append(btn)
        return btn

    def _btn_callback(self, btn, teleop_dir: TeleopDirection):
        self.emit("teleop-dir-changed", teleop_dir)

    def lock_focus(self):
        self.is_focus_locked = True
        # print("Locking focus on teleop row")
        self.grab_focus()

    def unlock_focus(self):
        self._held_keys.clear()
        # print("Unlocking focus on teleop row")

    def on_key_pressed(self, controller, keyval, keycode, state):
        # Handle ESC key to unlock focus
        if keyval == Gdk.KEY_Escape:
            if self.teleop_page:
                # print("Focus unlocked via ESC key")
                self.unlock_focus()
                self.teleop_page.unlock_focus()
            return True

        # Only process other keys if focus is locked
        if not self.is_focus_locked:
            return False

        if keyval in self._allowed_keys:
            self._held_keys.add(keyval)

        self._emit_from_keys()
        return True

    def on_key_released(self, controller, keyval, keycode, state):
        # Handle ESC key - already handled in key_pressed
        if keyval == Gdk.KEY_Escape:
            return True

        # Only process other keys if focus is locked
        if not self.is_focus_locked:
            return False

        if keyval in self._allowed_keys and keyval in self._held_keys:
            self._held_keys.remove(keyval)

        # self._emit_from_keys() # TODO this is an option for continuous teleoperation
        return True

    def _emit_from_keys(self):
        x = 0.0
        y = 0.0

        if Gdk.KEY_Up in self._held_keys:
            x += 1.0
        if Gdk.KEY_Down in self._held_keys:
            x -= 1.0
        if Gdk.KEY_Left in self._held_keys:
            y += 1.0
        if Gdk.KEY_Right in self._held_keys:
            y -= 1.0

        self.emit("teleop-dir-changed", TeleopDirection(x=x, y=y))

    def enable(self):
        for btn in self.btns:
            btn.set_sensitive(True)

    def disable(self):
        for btn in self.btns:
            btn.set_sensitive(False)
