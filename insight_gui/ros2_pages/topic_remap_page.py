# =============================================================================
# topic_remap_page.py
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

from __future__ import annotations

from typing import Optional

from rclpy.exceptions import InvalidTopicNameException
from rclpy.validate_full_topic_name import validate_full_topic_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Pango

from insight_gui.models.topic_item import TopicItem
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.gtk_utils import find_str_in_list_store


# TODO do the GObject refactor for the entire page
class TopicRemapPage(ContentPage):
    __gtype_name__ = "TopicRemapPage"

    def __init__(self, preselect_topic: TopicItem = None, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Remap Topic")
        super().set_refresh_fail_text("No topics found. Refresh to try again.")

        self.preselect_topic = preselect_topic
        self.detach_kwargs = {"preselect_topic": preselect_topic}

        self.selected_topic: str = ""
        self.selected_topic_type: str = ""
        self.target_topic_full: str = ""

        self.remap_sub = None
        self.remap_pub = None
        self.is_remapping: bool = False

        # Source topic group
        self.source_group: PrefGroup = self.pref_page.add_group(title="Source Topic", filterable=False)
        self.topic_row: Adw.ComboRow = self.source_group.add_row(
            Adw.ComboRow(
                title="Topic",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )

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

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)
        self.topic_row.set_factory(factory)

        self.topic_type_row: PrefRow = self.source_group.add_row(
            PrefRow(title="Message Type", css_classes=["property"])
        )

        self.topic_row.connect("notify::selected-item", self.on_topic_changed)

        # Target topic group
        self.target_group: PrefGroup = self.pref_page.add_group(title="Target Topic", filterable=False)
        self.target_name_row: Adw.EntryRow = self.target_group.add_row(
            Adw.EntryRow(title="Remap Name", show_apply_button=False)
        )
        target_entry = self.target_name_row.get_child()
        if isinstance(target_entry, Gtk.Entry):
            target_entry.set_placeholder_text("New topic name (namespace optional)")

        self.toggle_button: Gtk.Button = self.target_group.add_row(
            Gtk.Button(
                child=Adw.ButtonContent(label="Start remap", icon_name="media-playback-start-symbolic"),
                tooltip_text="Start republishing messages to the target topic",
                margin_top=12,
                halign=Gtk.Align.CENTER,
                css_classes=["suggested-action", "pill"],
            )
        )
        self.toggle_button.connect("clicked", self.on_toggle_clicked)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def refresh_bg(self) -> bool:
        self.available_topics = self.ros2_connector.get_available_topics()
        return self.available_topics is not None and self.available_topics.get_n_items() > 0

    def refresh_ui(self):
        self.topic_list_store.remove_all()

        for topic in self.available_topics:
            self.topic_list_store.append(Gtk.StringObject.new(topic.full_name))

        found_index = find_str_in_list_store(self.topic_list_store, self.preselect_topic)
        if found_index >= 0:
            self.topic_row.set_selected(found_index)
        elif self.topic_list_store.get_n_items() > 0:
            self.topic_row.set_selected(0)

    def reset_ui(self):
        self.topic_list_store.remove_all()
        self.topic_type_row.set_subtitle("")
        self.target_name_row.set_text("")
        self.stop_remap()

    def on_unrealize(self, *args):
        super().on_unrealize(*args)
        self.stop_remap()

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------
    def on_topic_changed(self, *args):
        item = self.topic_row.get_selected_item()
        if not item:
            self.selected_topic = ""
            self.topic_type_row.set_subtitle("")
            return

        topic_name = item.get_string()
        self.selected_topic = topic_name

        topic_type = self._get_topic_type(topic_name)
        self.selected_topic_type = topic_type or ""
        self.topic_type_row.set_subtitle(self.selected_topic_type)

        if topic_name:
            base_name = topic_name.rsplit("/", 1)[-1]
            if base_name and not self.target_name_row.get_text():
                self.target_name_row.set_text(base_name)

    def on_toggle_clicked(self, *args):
        if self.is_remapping:
            self.stop_remap()
            return

        self.start_remap()

    # ------------------------------------------------------------------
    # Remapping helpers
    # ------------------------------------------------------------------
    def start_remap(self) -> bool:
        if not self.selected_topic:
            self.show_toast("No source topic selected")
            return False

        target_topic = self._build_target_topic()
        if not target_topic:
            self.show_toast("Set a valid target topic name")
            return False

        try:
            validate_full_topic_name(target_topic)
        except InvalidTopicNameException as exc:
            self.show_toast(str(exc))
            return False

        msg_class = self.ros2_connector.get_message_class(self.selected_topic)
        if not msg_class or not msg_class.python_class:
            self.show_toast("Could not determine message type")
            return False
        msg_class_python = msg_class.python_class

        try:
            self.remap_pub = self.ros2_connector.add_publisher(msg_class_python, target_topic)
            self.remap_sub = self.ros2_connector.add_subsciption(
                msg_class_python, self.selected_topic, self._on_remap_message
            )
        except Exception as exc:
            self.show_toast(f"Failed to start remap: {exc}")
            self.stop_remap()
            return False

        self.target_topic_full = target_topic
        self.topic_row.set_sensitive(False)
        self.target_name_row.set_sensitive(False)
        self.is_remapping = True
        self.update_toggle_button()
        return True

    def stop_remap(self):
        if self.remap_sub:
            try:
                self.ros2_connector.destroy_subscription(self.remap_sub)
            except Exception:
                pass
            finally:
                self.remap_sub = None

        if self.remap_pub:
            try:
                self.ros2_connector.destroy_publisher(self.remap_pub)
            except Exception:
                pass
            finally:
                self.remap_pub = None

        self.topic_row.set_sensitive(True)
        self.target_name_row.set_sensitive(True)
        if self.is_remapping:
            self.show_toast("Stopped remapping")
        self.is_remapping = False
        self.target_topic_full = ""
        self.update_toggle_button()

    def _on_remap_message(self, msg):
        if self.remap_pub:
            self.remap_pub.publish(msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_topic_type(self, topic_name: str) -> Optional[str]:
        for topic in self.available_topics:
            if topic.full_name == topic_name and topic.type_names:
                if len(topic.type_names) == 1:
                    return topic.type_names[0]
                return ", ".join(topic.type_names)
        return None

    def _build_target_topic(self) -> str:
        entry_text = (self.target_name_row.get_text() or "").strip()

        if not entry_text:
            return ""

        if entry_text.startswith("/"):
            full_topic = entry_text
        else:
            full_topic = entry_text

        while "//" in full_topic:
            full_topic = full_topic.replace("//", "/")

        if full_topic and not full_topic.startswith("/"):
            full_topic = f"/{full_topic}"

        return full_topic.rstrip("/")

    def update_toggle_button(self):
        content = self.toggle_button.get_child()
        if isinstance(content, Adw.ButtonContent):
            if self.is_remapping:
                content.set_label("Stop remap")
                content.set_icon_name("media-playback-stop-symbolic")
            else:
                content.set_label("Start remap")
                content.set_icon_name("media-playback-start-symbolic")

        if self.is_remapping:
            self.toggle_button.remove_css_class("suggested-action")
            self.toggle_button.add_css_class("destructive-action")
            self.toggle_button.set_tooltip_text("Stop remapping the selected topic")
        else:
            self.toggle_button.remove_css_class("destructive-action")
            if "suggested-action" not in self.toggle_button.get_css_classes():
                self.toggle_button.add_css_class("suggested-action")
            self.toggle_button.set_tooltip_text("Start republishing messages to the target topic")
