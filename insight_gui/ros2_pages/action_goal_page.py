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
from operator import itemgetter

from rclpy.action import get_action_names_and_types
from ros2action.api import get_action_class
from rosidl_runtime_py import set_message_fields, message_to_yaml, message_to_ordereddict
from action_msgs.msg import GoalStatus

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Pango

from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.widgets.improved_content_page import ImprovedContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ActionGoalPage(ImprovedContentPage):
    __gtype_name__ = "ActionGoalPage"

    def __init__(self, preselect_action: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Send Action Goal")
        super().set_refresh_fail_text("No actions found. Refresh to try again.")

        self.preselect_action = preselect_action
        self.action_class = None
        self.goal_instance = None
        self.current_goal_id = None

        # Bottom buttons
        self.send_goal_btn = super().add_bottom_left_btn(
            label="Send Goal",
            icon_name="document-send-symbolic",
            func=self.on_send_goal,
            tooltip_text="Send the action goal",
            sensitive=False,
        )

        self.cancel_goal_btn = super().add_bottom_left_btn(
            label="Cancel Goal",
            icon_name="process-stop-symbolic",
            func=self.on_cancel_goal,
            tooltip_text="Cancel the current goal",
            sensitive=False,
            visible=False,
        )

        super().add_bottom_right_btn(label="Clear", icon_name="trash-symbolic", func=self.on_clear_text)

        # Select group
        self.select_group = self.pref_page.add_group(title="Select Action", filterable=False)
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

        # Goal group
        self.goal_group = self.pref_page.add_group(title="Goal", filterable=False)
        self.goal_group.add_suffix_btn(
            icon_name="edit-undo-symbolic", tooltip_text="Reset Goal Content", func=self.update_goal_text
        )
        self.goal_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Goal Text",
            func=self.on_copy_goal_to_clipboard,
        )
        self.goal_text_view_row = self.goal_group.add_row(TextViewRow(editable=True, wrap_mode=Gtk.WrapMode.NONE))

        # Status group
        self.status_group = self.pref_page.add_group(title="Status", filterable=False)
        self.status_row = self.status_group.add_row(PrefRow(title="Goal Status", subtitle="No goal sent"))

        # Feedback group
        self.feedback_group = self.pref_page.add_group(title="Feedback", filterable=False)
        self.feedback_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Feedback Text",
            func=self.on_copy_feedback_to_clipboard,
        )
        self.feedback_text_view_row = self.feedback_group.add_row(
            TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE)
        )

        # Result group
        self.result_group = self.pref_page.add_group(title="Result", filterable=False)
        self.result_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Result Text",
            func=self.on_copy_result_to_clipboard,
        )
        self.result_text_view_row = self.result_group.add_row(TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE))

    def refresh_bg(self) -> bool:
        self.available_actions = sorted(get_action_names_and_types(node=self.ros2_connector.node), key=itemgetter(0))
        return len(self.available_actions) > 0

    def refresh_ui(self):
        # Fill the ComboBox/ListStore with available actions
        for action_name, action_types in self.available_actions:
            self.action_list_store.append(Gtk.StringObject.new(action_name))

        # Set the selected action to the preselected one
        found, found_index = self.action_list_store.find(Gtk.StringObject.new(self.preselect_action))
        if found:
            self.action_row.set_selected(found_index)
        else:
            self.action_row.set_selected(0)

    def reset_ui(self):
        self.action_list_store.remove_all()
        self.goal_text_view_row.clear()
        self.feedback_text_view_row.clear()
        self.result_text_view_row.clear()
        self.send_goal_btn.set_sensitive(False)
        self.cancel_goal_btn.set_sensitive(False)
        self.cancel_goal_btn.set_visible(False)
        self.status_row.set_subtitle("No goal sent")

    def trigger(self):
        """Trigger the primary action - send goal."""
        self.send_goal()

    def on_action_selected(self, *args):
        if self.action_list_store.get_n_items() <= 0:
            return

        self.selected_action_name = self.action_row.get_selected_item().get_string()

        if self.selected_action_name:
            try:
                self.action_class = get_action_class(
                    node=self.ros2_connector.node,
                    action_name=self.selected_action_name,
                )

                self.selected_action_type = get_action_full_name(self.action_class)
                self.action_type_row.set_subtitle(self.selected_action_type)
                self.action_type_row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ActionInfoPage,
                    subpage_kwargs={"action_full_name": self.selected_action_type},
                )

                self.goal_instance = self.action_class.Goal()
                self.send_goal_btn.set_sensitive(True)
                self.update_goal_text()

            except Exception as e:
                self.show_toast(f"Error loading action: {e}")
                self.send_goal_btn.set_sensitive(False)

    def on_msg_format_changed(self, *args):
        if not self.goal_instance:
            return

        self.msg_format = self.msg_format_row.get_selected_item().get_string()
        self.update_goal_text()

    def update_goal_text(self):
        if not self.goal_instance:
            return

        self.goal_instance = self.action_class.Goal()  # Reset instance

        if self.msg_format == "YAML":
            goal_text = message_to_yaml(self.goal_instance).rstrip()
        elif self.msg_format == "JSON":
            goal_text = str(json.dumps(message_to_ordereddict(self.goal_instance), indent=4))

        # Use batched UI update
        self.schedule_ui_update("goal_text_update", self.goal_text_view_row.set_text, goal_text)

    def on_send_goal(self, *args):
        self.send_goal()

    def send_goal(self):
        if not self.action_class or not self.selected_action_name:
            self.show_toast("No action selected")
            return

        goal_text = self.goal_text_view_row.get_text()

        # Parse goal data
        if self.msg_format == "YAML":
            try:
                data_dict = yaml.safe_load(goal_text)
            except Exception as e:
                self.show_toast(f"Invalid YAML: {e}")
                return
        elif self.msg_format == "JSON":
            try:
                data_dict = json.loads(goal_text)
            except Exception as e:
                self.show_toast(f"Invalid JSON: {e}")
                return

        try:
            set_message_fields(
                msg=self.goal_instance,
                values=data_dict,
            )
        except Exception as e:
            self.show_toast(f"Error parsing the goal data: {e}")
            return

        # Disable send button and show cancel button
        self.send_goal_btn.set_sensitive(False)
        self.cancel_goal_btn.set_visible(True)
        self.cancel_goal_btn.set_sensitive(True)
        self.status_row.set_subtitle("Sending goal...")

        def send_goal_bg():
            """Background task to send the action goal."""
            return self.ros2_connector.send_action_goal(
                action_type=self.action_class,
                action_name=self.selected_action_name,
                goal=self.goal_instance,
                feedback_callback=self.on_feedback_received,
                result_callback=self.on_result_received,
                timeout_sec=10,
            )

        def on_goal_sent_success(goal_id):
            """Handle successful goal sending."""
            self.current_goal_id = goal_id
            self.status_row.set_subtitle("Goal sent - waiting for result...")
            self.show_toast("Goal sent successfully!")

        def on_goal_sent_error(error):
            """Handle goal sending error."""
            self.show_toast(f"Failed to send goal: {error}")
            self.send_goal_btn.set_sensitive(True)
            self.cancel_goal_btn.set_visible(False)
            self.cancel_goal_btn.set_sensitive(False)
            self.status_row.set_subtitle("Goal failed to send")

        # Use async task manager to send goal
        self.run_background_task(
            task_id="send_action_goal",
            background_func=send_goal_bg,
            success_callback=on_goal_sent_success,
            error_callback=on_goal_sent_error,
        )

    def on_cancel_goal(self, *args):
        if self.current_goal_id:

            def cancel_goal_bg():
                """Background task to cancel the goal."""
                return self.ros2_connector.cancel_action_goal(self.current_goal_id)

            def on_cancel_success(cancelled):
                """Handle successful goal cancellation."""
                if cancelled:
                    self.show_toast("Goal cancelled successfully!")
                    self.status_row.set_subtitle("Goal cancelled")
                else:
                    self.show_toast("Failed to cancel goal")

                self.send_goal_btn.set_sensitive(True)
                self.cancel_goal_btn.set_visible(False)
                self.cancel_goal_btn.set_sensitive(False)
                self.current_goal_id = None

            def on_cancel_error(error):
                """Handle goal cancellation error."""
                self.show_toast(f"Error cancelling goal: {error}")

            # Use async task manager to cancel goal
            self.run_background_task(
                task_id="cancel_action_goal",
                background_func=cancel_goal_bg,
                success_callback=on_cancel_success,
                error_callback=on_cancel_error,
            )

    def on_feedback_received(self, feedback):
        """Called when feedback is received from the action server."""
        if self.msg_format == "YAML":
            feedback_text = message_to_yaml(feedback)
        elif self.msg_format == "JSON":
            feedback_text = str(json.dumps(message_to_ordereddict(feedback), indent=4))

        # Use batched UI update for feedback
        self.schedule_ui_update("feedback_update", self.feedback_text_view_row.set_text, feedback_text)

    def on_result_received(self, result, status):
        """Called when the final result is received from the action server."""
        # Update status
        status_text = self.get_status_text(status)
        self.schedule_ui_update("status_update", self.status_row.set_subtitle, f"Goal completed: {status_text}")

        # Update result text
        if self.msg_format == "YAML":
            result_text = message_to_yaml(result)
        elif self.msg_format == "JSON":
            result_text = str(json.dumps(message_to_ordereddict(result), indent=4))

        self.schedule_ui_update("result_update", self.result_text_view_row.set_text, result_text)

        # Re-enable send button and hide cancel button
        self.schedule_ui_update("buttons_update", self._update_buttons_after_completion)

    def _update_buttons_after_completion(self):
        """Update buttons after goal completion."""
        self.send_goal_btn.set_sensitive(True)
        self.cancel_goal_btn.set_visible(False)
        self.cancel_goal_btn.set_sensitive(False)
        self.current_goal_id = None

    def get_status_text(self, status):
        """Convert goal status to human-readable text."""
        status_map = {
            GoalStatus.STATUS_UNKNOWN: "Unknown",
            GoalStatus.STATUS_ACCEPTED: "Accepted",
            GoalStatus.STATUS_EXECUTING: "Executing",
            GoalStatus.STATUS_CANCELING: "Canceling",
            GoalStatus.STATUS_SUCCEEDED: "Succeeded",
            GoalStatus.STATUS_CANCELED: "Canceled",
            GoalStatus.STATUS_ABORTED: "Aborted",
        }
        return status_map.get(status, f"Status {status}")

    def on_clear_text(self, *args):
        self.feedback_text_view_row.clear()
        self.result_text_view_row.clear()

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

    def on_unrealize(self, *args):
        """Clean up when page is unrealized."""
        super().on_unrealize(*args)
        # Cancel any running goal
        if self.current_goal_id:
            self.ros2_connector.cancel_action_goal(self.current_goal_id)


def get_action_full_name(action_class):
    """Get the full name of an action class."""
    module_name = action_class.__module__
    package_name = module_name.split(".")[0]
    action_type = module_name.split(".")[1]
    action_name = action_class.__name__
    return f"{package_name}/{action_type}/{action_name}"
