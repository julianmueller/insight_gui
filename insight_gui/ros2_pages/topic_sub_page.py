# =============================================================================
# topic_sub_page.py
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
import time

from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango

from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, TextViewRow
from insight_gui.widgets.buttons import PlayPauseButton

from insight_gui.utils.gtk_utils import find_str_in_list_store


class TopicSubscriberPage(ContentPage):
    __gtype_name__ = "TopicSubscriberPage"

    def __init__(self, preselect_topic: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Subscribe to Topic")
        super().set_refresh_fail_text("No topics found. Refresh to try again.")

        self.preselect_topic = preselect_topic
        self.detach_kwargs = {"preselect_topic": preselect_topic}

        self.is_echoing = False
        self.single_echo_done = True
        self.msg_instance = None
        self.ros2_sub = None

        self.last_update_time = 0
        self.max_update_rate = 10  # in Hz

        # main btns in bottom bar
        self.toggle_stream_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_echoing,
                func=self.on_toggle_stream,
                labels=("Stop Subscription", "Start Subscription"),
                visible=False,
                css_classes=["suggested-action"],
            ),
            position="start",
        )
        self.single_sub_btn = super().add_bottom_left_btn(
            label="Single Subscription",
            icon_name="subscriptions-symbolic",
            func=self.on_single_sub,
            css_classes=["suggested-action"],
        )
        self.clear_btn = super().add_bottom_right_btn(
            label="Clear", icon_name="trash-symbolic", func=self.on_clear_text, css_classes=["destructive-action"]
        )

        # select group
        self.select_group: PrefGroup = self.pref_page.add_group(title="Select Topic", filterable=False)
        self.topic_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Topic",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.topic_row.connect("notify::selected-item", self.on_topic_changed)
        self.topic_type_row = self.select_group.add_row(PrefRow(title="Service Type", css_classes=["property"]))

        # Create a Gio.ListStore to fill the ComboBox with
        self.topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.topic_row.set_model(self.topic_list_store)

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

        # TODO maybe also group the topics by namespaces?
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)
        self.topic_row.set_factory(factory)

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
        self.msg_format_list_store.append(Gtk.StringObject.new("CSV"))
        self.msg_format_list_store.append(Gtk.StringObject.new("JSON"))
        self.msg_format_row.set_model(self.msg_format_list_store)
        self.msg_format = "YAML"

        self.stream_type_toggle_row = self.select_group.add_row(Adw.SwitchRow(title="Single / Continuous Stream"))
        self.stream_type_toggle_row.connect("notify::active", self.on_toggle_stream_type)

        # echo group for message on the topic to appear
        self.echo_group: PrefGroup = self.pref_page.add_group(title="Echo Messages", filterable=False)
        self.echo_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Text",
            func=self.on_copy_to_clipboard,
        )

        self.echo_text_view_row = self.echo_group.add_row(TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE))

        # TODO add rows that display infos about the topic, like qos and rate etc

    def refresh_bg(self) -> bool:
        self.available_topics = self.ros2_connector.get_available_topics()
        return len(self.available_topics) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available services
        for topic_name, topic_types in self.available_topics:
            self.topic_list_store.append(Gtk.StringObject.new(topic_name))

        # set the selected service to the preselected one
        found_index = find_str_in_list_store(self.topic_list_store, self.preselect_topic)
        # found, found_index = self.topic_list_store.find(Gtk.StringObject.new(self.preselect_topic))
        if found_index >= 0:
            self.topic_row.set_selected(found_index)
        else:
            self.topic_row.set_selected(0)

    def reset_ui(self):
        self.topic_list_store.remove_all()
        self.single_echo_done = True
        self.echo_text_view_row.clear()
        self.remove_sub()

    def remove_sub(self):
        if self.ros2_sub:
            self.ros2_connector.destroy_subscription(self.ros2_sub)
            self.ros2_sub = None

    def trigger(self):
        if self.stream_type_toggle_row.get_active():
            self.toggle_stream_btn.playing = True
        # self.is_echoing = not self.is_echoing
        # self.play_pause_btn.set_active(self.is_echoing)

    def on_unrealize(self, *args):
        super().on_unrealize(*args)
        self.remove_sub()

    def on_clear_text(self, *args):
        self.echo_text_view_row.clear()
        self.msg_instance = None

    def on_toggle_stream_type(self, *args):
        # active = continuous stream, inactive = single shot
        if self.stream_type_toggle_row.get_active():
            self.single_sub_btn.set_visible(False)
            self.toggle_stream_btn.set_visible(True)
        else:
            self.single_sub_btn.set_visible(True)
            self.toggle_stream_btn.set_visible(False)

        self.toggle_stream_btn.playing = False

    def on_single_sub(self, *args):
        self.single_echo_done = False

    def on_toggle_stream(self, *args):
        self.is_echoing = self.toggle_stream_btn.playing
        if self.is_echoing:
            self.topic_row.set_sensitive(False)
        else:
            self.topic_row.set_sensitive(True)

    def on_topic_changed(self, *args):
        if self.topic_list_store.get_n_items() <= 0:
            return

        self.remove_sub()

        topic_name = self.topic_row.get_selected_item().get_string()

        if topic_name:
            msg_class = self.ros2_connector.get_message_class(topic_name=topic_name)

            self.selected_topic_type = self.ros2_connector.get_message_type_name(msg_class)
            self.topic_type_row.set_subtitle(self.selected_topic_type)
            self.topic_type_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=InterfaceInfoPage,
                subpage_kwargs={"interface_full_name": self.selected_topic_type},
            )

            # TODO maybe add special treatment for some "known topics?"
            self.ros2_sub = self.ros2_connector.add_subsciption(
                msg_type=msg_class, topic_name=topic_name, callback=self.topic_callback
            )
            self.single_echo_done = True
            self.on_clear_text()

    def on_msg_format_changed(self, *args):
        self.msg_format = self.msg_format_row.get_selected_item().get_string()
        self.update_echo_text()

    def update_echo_text(self):
        if not self.msg_instance:
            return

        def _idle():
            self.echo_text_view_row.set_text(msg_text)

        if self.msg_format == "YAML":
            msg_text = message_to_yaml(self.msg_instance)
        elif self.msg_format == "CSV":
            msg_text = message_to_csv(self.msg_instance)
        elif self.msg_format == "JSON":
            msg_text = str(json.dumps(message_to_ordereddict(self.msg_instance), indent=4))  # .replace('"', "'")

        GLib.idle_add(_idle)

    def on_copy_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.echo_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Text copied!")

    def topic_callback(self, msg):
        if not self.is_mapped:
            return

        # apply rate limiting
        now = time.time()
        if now - self.last_update_time < 1.0 / self.max_update_rate:
            return

        if self.is_echoing or not self.single_echo_done:
            self.msg_instance = msg
            if self.msg_format == "YAML":
                msg_text = message_to_yaml(self.msg_instance)
            elif self.msg_format == "CSV":
                msg_text = message_to_csv(self.msg_instance)
            elif self.msg_format == "JSON":
                msg_text = str(json.dumps(message_to_ordereddict(self.msg_instance), indent=4))  # .replace('"', "'")

            if len(msg_text) > 1000:
                self.show_banner("Content of message very large, this may slow down the UI!")

            def _idle():
                self.echo_text_view_row.set_text(msg_text)
                self.last_update_time = now
                self.single_echo_done = True

            GLib.idle_add(_idle)
