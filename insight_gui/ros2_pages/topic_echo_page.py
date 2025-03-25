# =============================================================================
# topic_echo_page.py
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

from ros2topic.api import get_topic_names_and_types, get_msg_class
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from insight_gui.ros2_pages.msg_type_info_pages import MessageTypeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, TextViewRow
from insight_gui.widgets.buttons import PlayPauseButton


class TopicEchoPage(ContentPage):
    __gtype_name__ = "TopicEchoPage"

    def __init__(self, **kwargs):
        super().__init__(refreshable=True, searchable=False, **kwargs)
        super().set_title("Topic Echo")
        super().set_empty_page_text("Refresh to show topics")
        super().set_search_entry_placeholder_text("Search for topics")

        self.is_echoing = False
        self.sub = None

    def on_setup_gui(self):
        # Btn for opening the online link to msg definition
        self.play_pause_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_echoing,
                func=self.on_toggle_echoing,
                labels=("Stop echo", "Start echo"),
            ),
            position="start",
        )
        # super().add_bottom_right_btn(label="Clear", icon_name="trash-symbolic", func=self.on_clear_log)

        # filters to apply to the column view
        select_group: PrefGroup = self.pref_page.add_group(title="Select Topic", filterable=False)
        self.topic_row = select_group.add_row(
            Adw.ComboRow(
                title="Topic",
                enable_search=True,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.topic_row.connect("notify::selected-item", self.on_topic_selected)
        self.selected_topic_type_row = select_group.add_row(PrefRow(title="Service Type", css_classes=["property"]))

        # Create a Gio.ListStore to fill the ComboBox with
        self.topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.topic_row.set_model(self.topic_list_store)

        self.echo_format_row = select_group.add_row(
            Adw.ComboRow(
                title="Format",
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.echo_format_row.connect("notify::selected-item", self.on_echo_format_changed)
        self.echo_format_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.echo_format_list_store.append(Gtk.StringObject.new("YAML"))
        self.echo_format_list_store.append(Gtk.StringObject.new("CSV"))
        self.echo_format_list_store.append(Gtk.StringObject.new("JSON"))
        self.echo_format_row.set_model(self.echo_format_list_store)

        echo_group: PrefGroup = self.pref_page.add_group(title="Echo Messages", filterable=False)
        echo_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Text",
            func=self.on_copy_to_clipboard,
        )

        self.echo_text_view = echo_group.add_row(TextViewRow(editable=False))

        # TODO add rows that display infos about the topic, like qos and rate etc

    def on_refresh_blocking(self) -> bool:
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
        return len(self.topic_list) > 0

    def on_refresh_gui(self):
        for topic in self.topic_list:
            self.topic_list_store.append(Gtk.StringObject.new(topic))

        if self.topic_list_store.get_n_items() > 0:
            self.topic_row.set_model(self.topic_list_store)
            self.topic_row.set_selected(0)
        else:
            super().show_banner("No topic with found")

    def on_reset_gui(self):
        self.topic_list_store.remove_all()

    def on_unrealize(self, *args):
        # super().on_unrealize(*args)
        # TODO remove subscription
        # self.ros2_connector.remove_subscription(self.rosout_sub)
        pass

    def on_map(self, *args):
        # TODO make the logger start (again) logging when page is currently visible
        # super().on_map(*args)
        pass

    def on_unmap(self, *args):
        # TODO make the logger stop logging when page is currently not visible
        pass

    def on_topic_selected(self, *args):
        if self.topic_list_store.get_n_items() <= 0:
            return

        if self.sub:
            self.ros2_connector.destroy_subscription(self.sub)

        topic_name = self.topic_row.get_selected_item().get_string()
        if not topic_name:
            return

        msg_class = get_msg_class(self.ros2_connector.node, topic_name)

        self.selected_topic_type = get_msg_full_name(msg_class)
        self.selected_topic_type_row.set_subtitle(self.selected_topic_type)
        self.selected_topic_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=MessageTypeInfoPage,
            subpage_kwargs={"msg_type_full_name": self.selected_topic_type},
        )

        if topic_name:
            # TODO maybe add special treatment for some "known topics?"
            self.sub = self.ros2_connector.add_subsciption(msg_class, topic_name, self.topic_callback)

    def on_copy_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.echo_text_view.get_text()
        clip.set(str(text))
        self.show_toast("Text copied!")

    def on_toggle_echoing(self, btn: Gtk.Widget, playing: bool, *args):
        self.is_echoing = playing

        # create subscription to the rosout topic via the ros2 connector
        # self.rosout_sub = self.ros2_connector.add_subsciption(Log, "/rosout", self.log_callback)

    def on_echo_format_changed(self, *args):
        self.echo_format = self.echo_format_row.get_selected_item().get_string()

    def topic_callback(self, msg):
        if self.echo_format == "YAML":
            msg_str = message_to_yaml(msg)
        elif self.echo_format == "CSV":
            msg_str = message_to_csv(msg)
        elif self.echo_format == "JSON":
            msg_str = str(json.dumps(message_to_ordereddict(msg), indent=4)).replace('"', "'")

        def _idle():
            self.echo_text_view.set_text(msg_str)
            return False  # make idle_add stop after one iteration

        if self.is_echoing:
            GLib.idle_add(_idle)


def get_msg_full_name(msg_class):
    module_name = msg_class.__module__
    package_name = module_name.split(".")[0]
    message_type = module_name.split(".")[1]
    message_name = msg_class.__name__
    return f"{package_name}/{message_type}/{message_name}"
