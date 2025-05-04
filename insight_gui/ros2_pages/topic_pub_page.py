# =============================================================================
# topic_pub_page.py
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

import json
import yaml
import time

from ros2topic.api import get_topic_names_and_types, get_msg_class
from rosidl_runtime_py import (
    message_to_yaml,
    message_to_csv,
    message_to_ordereddict,
    get_message_interfaces,
    set_message_fields,
)
from rosidl_runtime_py.utilities import get_message
from rclpy.exceptions import InvalidTopicNameException

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, TextViewRow, SuggestionEntryRow
from insight_gui.widgets.buttons import PlayPauseButton
from insight_gui.utils.gtk_utils import find_str_in_list_store


class TopicPublisherPage(ContentPage):
    __gtype_name__ = "TopicPublisherPage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Publish to Topic")
        super().set_refresh_fail_text("No topics found. Refresh to try again.")

        self.is_pubing = False
        self.single_pub_done = True
        self.ros2_pub = None
        self.topic_name = None
        self.msg_class = None
        self.msg_instance = None
        self.publishing_rate = 10.0

        # main btns in bottom bar
        self.play_pause_stream_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_pubing,
                func=self.on_play_pause_stream,
                labels=("Stop Publishing", "Start Publishing"),
                visible=False,
            ),
            position="start",
        )
        self.single_pub_btn = super().add_bottom_left_btn(
            label="Single Publish", icon_name="mail-send-symbolic", func=self.on_single_pub
        )
        super().add_bottom_right_btn(label="Clear", icon_name="trash-symbolic", func=self.on_clear_text)

        # select group
        self.select_group: PrefGroup = self.pref_page.add_group(title="Select Topic", filterable=False)
        self.topic_row = self.select_group.add_row(SuggestionEntryRow(title="Topic"))
        self.topic_row.connect("apply", self.on_topic_name_applied)
        self.topic_row.connect("suggestion-apply", self.on_topic_suggestion_applied)
        self.topic_list_store: Gio.ListStore = self.topic_row.list_store

        self.topic_type_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Message Type",
                enable_search=True,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.topic_type_row.connect("notify::selected-item", self.on_topic_type_changed)

        # Create a Gio.ListStore to fill the ComboBox with
        self.topic_type_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.topic_type_row.set_model(self.topic_type_list_store)

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
        self.topic_type_row.set_factory(factory)

        self.msg_format_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Message Format",
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.msg_format_row.connect("notify::selected-item", self.on_msg_format_changed)
        self.msg_format_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.msg_format_list_store.append(Gtk.StringObject.new("YAML"))
        # self.msg_format_list_store.append(Gtk.StringObject.new("CSV"))
        self.msg_format_list_store.append(Gtk.StringObject.new("JSON"))
        self.msg_format_row.set_model(self.msg_format_list_store)
        self.msg_format = "YAML"

        self.stream_type_toggle_row = self.select_group.add_row(Adw.SwitchRow(title="Single / Continuous Stream"))
        self.stream_type_toggle_row.connect("notify::active", self.on_toggle_stream_type)

        self.publishing_rate_row = self.select_group.add_row(
            Adw.EntryRow(
                title="Publishing Rate",
                text=self.publishing_rate,
                show_apply_button=True,
                visible=False,
                input_purpose=Gtk.InputPurpose.NUMBER,
            )
        )
        self.publishing_rate_row.connect("apply", self.on_publishing_rate_applied)

        # pub group for message on the topic to appear
        self.pub_group: PrefGroup = self.pref_page.add_group(title="Echo Messages", filterable=False)
        self.pub_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Text",
            func=self.on_copy_to_clipboard,
        )
        self.pub_group.add_suffix_btn(
            icon_name="edit-undo-symbolic", tooltip_text="Reset Message Text", func=self.update_pub_text
        )

        self.pub_text_view_row = self.pub_group.add_row(TextViewRow(editable=True, wrap_mode=Gtk.WrapMode.NONE))

        # TODO add rows that display infos about the topic, like qos and rate etc

    def refresh_bg(self) -> bool:
        self.available_msgs = get_message_interfaces()
        self.topic_list = []

        available_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))

        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            self.topic_list.append(topic_name)

        return len(self.available_msgs) + len(self.topic_list) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available topics
        for pkg_name, msgs_list in sorted(self.available_msgs.items()):
            for msg in sorted(msgs_list):
                msg_type_full_name = f"{pkg_name}/{msg}"
                self.topic_type_list_store.append(Gtk.StringObject.new(msg_type_full_name))

        for topic in self.topic_list:
            self.topic_list_store.append(Gtk.StringObject.new(topic))

    def reset_ui(self):
        self.topic_list_store.remove_all()
        self.topic_type_list_store.remove_all()
        self.single_pub_done = True
        self.pub_text_view_row.clear()
        self.remove_pub()

    def remove_pub(self):
        if self.ros2_pub:
            self.ros2_connector.destroy_publisher(self.ros2_pub)
            time.sleep(0.1)  # wait some time until the publisher is destroyed # TODO could be more elegant
            self.ros2_pub = None

    def trigger(self):
        if self.stream_type_toggle_row.get_active():
            self.play_pause_stream_btn.playing = True
        # self.is_pubing = not self.is_pubing
        # self.play_pause_btn.set_active(self.is_pubing)

    def on_unrealize(self, *args):
        super().on_unrealize(*args)
        self.remove_pub()

    def on_clear_text(self, *args):
        self.pub_text_view_row.clear()

    def on_toggle_stream_type(self, *args):
        # active = continuous stream, inactive = single shot
        if self.stream_type_toggle_row.get_active():
            self.single_pub_btn.set_visible(False)
            self.play_pause_stream_btn.set_visible(True)
            self.publishing_rate_row.set_visible(True)
        else:
            self.single_pub_btn.set_visible(True)
            self.play_pause_stream_btn.set_visible(False)
            self.publishing_rate_row.set_visible(False)

        self.play_pause_stream_btn.playing = False

    def on_single_pub(self, *args):
        if not self.topic_name:
            return

        if not self.text_to_msg():
            return

        self.single_pub_done = False
        self.ros2_pub.publish(self.msg_instance)

    def on_play_pause_stream(self, *args):
        self.is_pubing = self.play_pause_stream_btn.playing
        # TODO make continuous pub work

    def on_topic_name_applied(self, *args):
        self.topic_name = self.topic_row.get_text()
        try:
            self.create_pub()
        except InvalidTopicNameException as e:
            self.topic_row.set_text("")
            self.topic_name = None
            super().show_toast(e)

    def on_topic_suggestion_applied(self, *args):
        self.topic_name = self.topic_row.get_text()
        try:
            msg_class = get_msg_class(self.ros2_connector.node, self.topic_name)
            selected_topic_type = get_msg_full_name(msg_class)
            found_index = find_str_in_list_store(self.topic_type_list_store, selected_topic_type)
            if found_index:
                self.topic_type_row.set_selected(found_index)
            else:
                self.topic_type_row.set_selected(0)
            self.create_pub()
            # TODO check the
        except InvalidTopicNameException as e:
            self.topic_row.set_text("")
            self.topic_name = None
            super().show_toast(e)

    def on_topic_type_changed(self, *args):
        if self.topic_type_list_store.get_n_items() <= 0:
            return

        topic_type_str = self.topic_type_row.get_selected_item().get_string()

        if topic_type_str:
            self.msg_class = get_message(topic_type_str)
            self.msg_instance = self.msg_class()
            self.create_pub()
            self.update_pub_text()

    def on_msg_format_changed(self, *args):
        self.msg_format = self.msg_format_row.get_selected_item().get_string()
        self.update_pub_text()

    def on_publishing_rate_applied(self, *args):
        rate = self.publishing_rate_row.get_text()

        try:
            self.publishing_rate = float(rate)
        except ValueError as e:
            super().show_toast(f"Invalid publishing rate: {e}")
            rate = self.publishing_rate
            return

        self.publishing_rate = float(rate)
        # TODO check if rate
        self.publishing_rate

    def create_pub(self):
        if not self.msg_class or not self.topic_name:
            return

        self.remove_pub()
        self.ros2_pub = self.ros2_connector.add_publisher(msg_type=self.msg_class, topic_name=self.topic_name)

    def update_pub_text(self):
        if not self.msg_class:
            return

        self.msg_instance = self.msg_class()

        def _idle():
            self.pub_text_view_row.set_text(msg_text)

        if self.msg_format == "YAML":
            msg_text = message_to_yaml(self.msg_instance)
        elif self.msg_format == "CSV":
            msg_text = message_to_csv(self.msg_instance)
        elif self.msg_format == "JSON":
            msg_text = str(json.dumps(message_to_ordereddict(self.msg_instance), indent=4))  # .replace('"', "'")

        GLib.idle_add(_idle)

    def on_copy_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.pub_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Text copied!")

    def text_to_msg(self) -> bool:
        msg_text = self.pub_text_view_row.get_text()
        if self.msg_format == "YAML":
            try:
                data_dict = yaml.safe_load(msg_text)
            except Exception as e:
                super().show_toast(f"Invalid YAML: {e}")
                return False

        elif self.msg_format == "JSON":
            try:
                data_dict = json.loads(msg_text)
            except Exception as e:
                super().show_toast(f"Invalid JSON: {e}")
                return False

        try:
            set_message_fields(
                msg=self.msg_instance,
                values=data_dict,
            )
            return True
        except Exception as e:
            super().show_toast(f"Error parsing the message data: {e}")
            return False


def get_msg_full_name(msg_class):
    module_name = msg_class.__module__
    package_name = module_name.split(".")[0]
    message_type = module_name.split(".")[1]
    message_name = msg_class.__name__
    return f"{package_name}/{message_type}/{message_name}"
