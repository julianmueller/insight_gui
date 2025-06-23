# =============================================================================
# action_goal_page.py
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
import json
import threading
import time

import rclpy
from rosidl_runtime_py import set_message_fields
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, TextViewRow
from insight_gui.utils.gtk_utils import find_str_in_list_store


class ActionGoalPage(ContentPage):
    __gtype_name__ = "ActionGoalPage"

    def __init__(self, preselect_action: str = "", **kwargs):
        super().__init__(**kwargs)
        super().set_title("Send Action Goal")
        super().set_refresh_fail_text("No actions found. Refresh to try again.")

        self.preselect_action = preselect_action
        self.detach_kwargs = {"preselect_action": preselect_action}

        self.goal_class = None
        self.goal_instance = None
        self.feedback_class = None
        self.feedback_instance = None
        self.result_class = None
        self.result_instance = None

        # Initialize action client and goal handle
        self.action_client = None
        self.goal_handle = None
        self.feedback_text = ""
        self.selected_action_name = None
        self.action_class = None

        self.send_goal_btn = super().add_bottom_left_btn(
            label="Send Goal",
            icon_name="emoji-flags-symbolic",
            func=self.on_send_goal,
            tooltip_text="Send the action goal",
            css_classes=["suggested-action"],
        )
        self.clear_btn = super().add_bottom_right_btn(
            label="Clear", icon_name="trash-symbolic", func=self.on_clear_text, css_classes=["destructive-action"]
        )

        # select group
        self.select_group = self.pref_page.add_group(title="Select Action")
        self.action_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Action",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.action_row.connect("notify::selected-item", self.on_action_selected)
        self.action_type_row = self.select_group.add_row(PrefRow(title="Action Type", css_classes=["property"]))

        # Create a Gio.ListStore to fill the ComboBox with
        self.action_list_store: Gio.ListStore = Gio.ListStore.new(Gtk.StringObject)
        self.action_row.set_model(self.action_list_store)

        def _on_factory_setup(factory, list_item):
            label = Gtk.Label(
                xalign=0,
                ellipsize=Pango.EllipsizeMode.MIDDLE,
                max_width_chars=50,
            )
            list_item.set_child(label)

        def _on_factory_bind(factory, list_item):
            item = list_item.get_item()
            label = list_item.get_child()
            if item and label:
                label.set_text(item.get_string())

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)
        self.action_row.set_factory(factory)

        self.msg_format_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Message Format",
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.msg_format_row.connect("notify::selected-item", self.on_msg_format_changed)
        self.msg_format_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.msg_format_list_store.append(Gtk.StringObject.new("YAML"))
        self.msg_format_list_store.append(Gtk.StringObject.new("JSON"))
        self.msg_format_row.set_model(self.msg_format_list_store)
        self.msg_format = "YAML"

        # goal group
        self.goal_group = self.pref_page.add_group(title="Goal")
        self.goal_group.add_suffix_btn(
            icon_name="edit-undo-symbolic", tooltip_text="Reset Goal Content", func=self.update_goal_text
        )
        self.goal_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Goal Text",
            func=self.on_copy_goal_to_clipboard,
        )
        self.goal_text_view_row = self.goal_group.add_row(TextViewRow(editable=True, wrap_mode=Gtk.WrapMode.NONE))

        # feedback group
        self.feedback_group = self.pref_page.add_group(title="Feedback")
        self.feedback_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Feedback Text",
            func=self.on_copy_feedback_to_clipboard,
        )
        self.feedback_text_view_row = self.feedback_group.add_row(
            TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE, max_height=500)
        )

        # result group
        self.result_group = self.pref_page.add_group(title="Result")
        self.result_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Result Text",
            func=self.on_copy_result_to_clipboard,
        )
        self.result_text_view_row = self.result_group.add_row(TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE))

    def refresh_bg(self) -> bool:
        self.available_actions = self.ros2_connector.get_available_actions()
        return len(self.available_actions) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available actions
        for action_name, _action_types in self.available_actions:
            self.action_list_store.append(Gtk.StringObject.new(action_name))

        # set the selected action to the preselected one
        found_index = find_str_in_list_store(self.action_list_store, self.preselect_action)
        if found_index >= 0:
            self.action_row.set_selected(found_index)
        else:
            self.action_row.set_selected(0)

    def reset_ui(self):
        # clear previous action list
        self.action_list_store.remove_all()
        self.goal_text_view_row.clear()
        self.feedback_text_view_row.clear()
        self.result_text_view_row.clear()
        self.send_goal_btn.set_sensitive(False)
        self.feedback_text = ""

    def on_send_goal(self):
        self.send_action_goal()

    def send_action_goal(self):
        goal_text = self.goal_text_view_row.get_text()

        if self.msg_format == "YAML":
            try:
                data_dict = yaml.safe_load(goal_text)
            except Exception as e:
                super().show_toast(f"Invalid YAML: {e}")
                return

        elif self.msg_format == "JSON":
            try:
                data_dict = json.loads(goal_text)
            except Exception as e:
                super().show_toast(f"Invalid JSON: {e}")
                return

        try:
            set_message_fields(
                msg=self.goal_instance,
                values=data_dict,
            )
        except Exception as e:
            super().show_toast(f"Error parsing the goal data: {e}")
            return

        def _thread_worker():
            self.send_goal_btn.set_sensitive(False)

            try:
                # Clear previous feedback and result
                self.feedback_text = ""

                self.feedback_text_view_row.clear()
                self.result_text_view_row.clear()

                # Send the goal with feedback callback
                self.action_client, goal_future = self.ros2_connector.send_action_goal(
                    action_type=self.action_class,
                    action_name=self.selected_action_name,
                    goal=self.goal_instance,
                    feedback_callback=self.feedback_callback,
                    timeout_sec=2,
                )

                # Wait for goal to be accepted
                start = time.monotonic()
                while not goal_future.done():
                    rclpy.spin_once(self.ros2_connector.node, timeout_sec=0.01)
                    if (time.monotonic() - start) > 5.0:  # 5 second timeout
                        raise TimeoutError("Timeout waiting for goal acceptance")

                self.goal_handle = goal_future.result()
                if not self.goal_handle.accepted:
                    self.show_toast("Goal was rejected by action server")
                    self.send_goal_btn.set_sensitive(True)
                    return

                # Get the result
                result_future = self.goal_handle.get_result_async()
                start = time.monotonic()
                while not result_future.done():
                    rclpy.spin_once(self.ros2_connector.node, timeout_sec=0.01)
                    # No timeout for result - let it run until completion

                result = result_future.result()
                self.result_instance = result.result

                if self.msg_format == "YAML":
                    result_text = message_to_yaml(self.result_instance)
                elif self.msg_format == "JSON":
                    result_text = str(json.dumps(message_to_ordereddict(self.result_instance), indent=4))

                self.result_text_view_row.set_text(result_text)
                self.send_goal_btn.set_sensitive(True)
                self.show_toast("Action completed!")

            except Exception as e:
                self.show_toast(f"Action Error: {e}")
                self.send_goal_btn.set_sensitive(True)

        threading.Thread(target=_thread_worker, daemon=True).start()

    def feedback_callback(self, feedback_msg):
        """Callback function for action feedback - accumulates feedback messages"""
        self.feedback_instance = feedback_msg.feedback

        if self.msg_format == "YAML":
            new_feedback = message_to_yaml(self.feedback_instance)
        elif self.msg_format == "JSON":
            new_feedback = str(json.dumps(message_to_ordereddict(self.feedback_instance), indent=4))

        # Accumulate feedback with timestamp
        import time

        timestamp = time.strftime("%H:%M:%S")
        if self.feedback_text:
            self.feedback_text += f"\n\n--- Feedback at {timestamp} ---\n{new_feedback}"
        else:
            self.feedback_text = f"--- Feedback at {timestamp} ---\n{new_feedback}"

        def _update_feedback():
            self.feedback_text_view_row.set_text(self.feedback_text)

        GLib.idle_add(_update_feedback)

    def on_clear_text(self):
        self.goal_text_view_row.clear()
        self.feedback_text_view_row.clear()
        self.result_text_view_row.clear()

    def on_action_selected(self, *args):
        if self.action_list_store.get_n_items() <= 0:
            return

        self.selected_action_name = self.action_row.get_selected_item().get_string()
        self.action_class = self.ros2_connector.get_action_class(action_name=self.selected_action_name)

        if not self.action_class:
            self.send_goal_btn.set_sensitive(False)
            super().show_toast(f"Could not load action class for {self.selected_action_name}")
            return

        selected_action_type = self.ros2_connector.get_action_type_name(self.action_class)
        self.action_type_row.set_subtitle(selected_action_type)

        # Get action types for ActionInfoPage
        available_actions = self.ros2_connector.get_available_actions()
        action_types = None
        for name, types in available_actions:
            if name == self.selected_action_name:
                action_types = types
                break

        self.action_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=InterfaceInfoPage,
            subpage_kwargs={"interface_full_name": action_types[0]},
        )

        self.goal_class = self.action_class.Goal
        self.goal_instance = self.goal_class()
        self.feedback_class = self.action_class.Feedback
        self.result_class = self.action_class.Result
        self.send_goal_btn.set_sensitive(True)
        self.update_goal_text()

    def on_msg_format_changed(self, *args):
        if not self.goal_instance:
            return

        self.msg_format = self.msg_format_row.get_selected_item().get_string()
        self.update_goal_text()
        self.update_feedback_text()
        self.update_result_text()

    def on_copy_goal_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.goal_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Goal text copied!")

    def on_copy_feedback_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.feedback_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Feedback text copied!")

    def on_copy_result_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.result_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Result text copied!")

    def update_goal_text(self):
        if not self.goal_instance:
            return

        def _idle():
            self.goal_text_view_row.set_text(goal_text)

        self.goal_instance = self.goal_class()  # reset instance
        if self.msg_format == "YAML":
            goal_text = message_to_yaml(self.goal_instance).rstrip()
        elif self.msg_format == "JSON":
            goal_text = str(json.dumps(message_to_ordereddict(self.goal_instance), indent=4))

        GLib.idle_add(_idle)

    def trigger(self):
        """Trigger method to send the action goal when called externally"""
        self.send_action_goal()

    def on_unrealize(self, *args):
        """Cleanup when the page is being destroyed"""
        super().on_unrealize(*args)
        if self.action_client:
            # Cancel any ongoing goal
            if self.goal_handle and not self.goal_handle.get_result_async().done():
                self.goal_handle.cancel_goal_async()

    def update_feedback_text(self):
        if not self.feedback_instance:
            return

        def _idle():
            self.feedback_text_view_row.set_text(feedback_text)

        if self.msg_format == "YAML":
            feedback_text = message_to_yaml(self.feedback_instance).rstrip()
        elif self.msg_format == "JSON":
            feedback_text = str(json.dumps(message_to_ordereddict(self.feedback_instance), indent=4))

        GLib.idle_add(_idle)

    def update_result_text(self):
        if not self.result_instance:
            return

        if self.msg_format == "YAML":
            result_text = message_to_yaml(self.result_instance).rstrip()
        elif self.msg_format == "JSON":
            result_text = str(json.dumps(message_to_ordereddict(self.result_instance), indent=4))

        def _idle():
            self.result_text_view_row.set_text(result_text)

        GLib.idle_add(_idle)
