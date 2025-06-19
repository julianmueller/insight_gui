# =============================================================================
# joint_states_page.py
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

from sensor_msgs.msg import JointState

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.widgets.content_page import ContentPage


class JointStatesPage(ContentPage):
    __gtype_name__ = "JointStatesPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Joint States")
        super().set_search_entry_placeholder_text("Search for topics")
        super().set_refresh_fail_text("No joints found. Refresh to try again.")

        self.search_group = self.pref_page.add_group(filterable=False)
        self.js_topic_row = self.search_group.add_row(
            Adw.ComboRow(
                title="Joint Topic",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.js_topic_row.connect("notify::selected-item", self.on_joint_states_changed)
        self.js_topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.js_topic_row.set_model(self.js_topic_list_store)

        self.joints_group = self.pref_page.add_group(title="Joints", empty_group_text="Refresh to show joints")

    def refresh_bg(self) -> bool:
        self.joint_states_topic_list = []

        available_topics = self.ros2_connector.get_available_topics()

        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            if topic_types == "sensor_msgs/msg/JointState":
                self.joint_states_topic_list.append(topic_name)
        return len(self.joint_states_topic_list) > 0

    def refresh_ui(self):
        for js_topic in self.joint_states_topic_list:
            self.js_topic_list_store.append(Gtk.StringObject.new(js_topic))

        if self.js_topic_list_store.get_n_items() > 0:
            self.js_topic_row.set_model(self.js_topic_list_store)
            self.js_topic_row.set_selected(0)
        else:
            super().show_toast("No topic with joint_states found")

    def reset_ui(self):
        self.js_topic_list_store.remove_all()
        self.joints_group.clear()

    def on_joint_states_changed(self, *args):
        if self.js_topic_list_store.get_n_items() <= 0:
            return

        topic_name = self.js_topic_row.get_selected_item().get_string()
        if topic_name:
            self.sub = self.ros2_connector.add_subsciption(JointState, topic_name, self.on_ros_js_callback)

    # TODO implement some rate limeting
    # TODO also pause, when the "tab" aka nav page is switched
    def on_ros_js_callback(self, msg: JointState, *args):
        pass

        # TODO implement
        # self.joints_group.clear()
        # rows = []
        # for name, pos in zip(msg.name, msg.position):
        #     row: PrefRow = self.joints_group.add_row(PrefRow(title=name))
        #     adj = Gtk.Adjustment(value=pos, lower=-6.133, upper=6.133, step_increment=0.05)
        #     scale = Gtk.Scale(
        #         orientation=Gtk.Orientation.HORIZONTAL,
        #         adjustment=adj,
        #         # TODO lower and upper boundaries should be based on the joint limits
        #         draw_value=True,
        #         digits=3,
        #         hexpand=True,
        #         value_pos=Gtk.PositionType.RIGHT,
        #     )
        #     scale.connect("notify::value-changed", lambda *args: print(scale.get_value()))
        #     plus_button = Gtk.Button(icon_name="plus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        #     minus_button = Gtk.Button(icon_name="minus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)

        #     val = scale.get_value()
        #     step_inc = adj.get_step_increment()

        #     plus_button.connect("clicked", lambda *args: scale.set_value(val + step_inc))
        #     minus_button.connect("clicked", lambda *args: scale.set_value(val - step_inc))

        #     row.add_suffix(minus_button)
        #     row.add_suffix(scale)
        #     row.add_suffix(plus_button)

        #     rows.append(row)

        # self.joints_group.add_rows_idle(rows)
