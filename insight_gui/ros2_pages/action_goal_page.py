# =============================================================================
# action_list_page.py
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

from operator import itemgetter
from typing import Dict

from rclpy.action import get_action_names_and_types

# from ros2action.api import get_action_
from rosidl_runtime_py import set_message_fields
from rosidl_runtime_py.utilities import get_service
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ActionGoalPage(ContentPage):
    __gtype_name__ = "ActionGoalPage"

    def __init__(self, preselect_action: str = "", **kwargs):
        super().__init__(**kwargs)
        super().set_title("Send Action Goal")
        super().set_refresh_fail_text("No actions found. Refresh to try again.")

        self.preselect_action = preselect_action
        self.goal_class = None
        self.goal_instance = None
        self.feedback_class = None
        self.feedback_instance = None
        self.result_class = None
        self.result_instance = None

        self.send_goal_btn = super().add_bottom_left_btn(
            label="Send Goal",
            icon_name="document-send-symbolic",
            func=self.on_send_goal,
            tooltip_text="Send the action goal",
        )
        super().add_bottom_right_btn(label="Clear", icon_name="trash-symbolic", func=self.on_clear_text)

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
            TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE)
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
        self.available_actions = sorted(get_action_names_and_types(node=self.ros2_connector.node), key=itemgetter(0))
        return len(self.available_actions) > 0

    def refresh_ui(self):
        pass

    def reset_ui(self):
        pass

    def on_send_goal(self):
        pass

    def on_clear_text(self):
        self.goal_text_view_row.text_view.set_text("")
        self.feedback_text_view_row.text_view.set_text("")
        self.result_text_view_row.text_view.set_text("")

    def on_action_selected(self, *args):
        pass

    def on_msg_format_changed(self, *args):
        pass

    def on_copy_goal_to_clipboard(self, *args):
        pass

    def on_copy_feedback_to_clipboard(self, *args):
        pass

    def on_copy_result_to_clipboard(self, *args):
        pass

    def update_goal_text(self):
        pass
