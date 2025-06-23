# =============================================================================
# img_viewer_page.py
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

import time

from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, Pango, GObject

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, ImageViewRow, TextViewRow
from insight_gui.widgets.buttons import PlayPauseButton

from insight_gui.utils.gtk_utils import find_str_in_list_store


class ImageViewerPage(ContentPage):
    __gtype_name__ = "ImageViewerPage"

    def __init__(self, preselect_topic: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Image Viewer")
        super().set_refresh_fail_text("No image topics found. Refresh to try again.")

        self.preselect_topic = preselect_topic
        self.detach_kwargs = {"preselect_topic": preselect_topic}

        self.is_streaming = False
        self.single_img_done = True
        self.cv_bridge = CvBridge()
        self.sub = None

        self.last_update_time = 0
        self.max_update_rate = 10  # in Hz

        # main btns in bottom bar
        self.play_pause_stream_btn = super().add_bottom_widget(
            PlayPauseButton(
                default_active=self.is_streaming,
                func=self.on_play_pause_stream,
                labels=("Stop Stream", "Start Stream"),
                visible=False,
                css_classes=["suggested-action"],
            ),
            position="start",
        )
        self.single_shot_btn = super().add_bottom_left_btn(
            label="Single Shot",
            icon_name="camera-photo-symbolic",
            func=self.on_single_shot_img,
            css_classes=["suggested-action"],
        )
        self.clear_btn = super().add_bottom_right_btn(
            label="Clear", icon_name="trash-symbolic", func=self.on_clear_img, css_classes=["destructive-action"]
        )

        self.img_group = self.pref_page.add_group(title="View Image", filterable=False)
        self.img_topic_row = self.img_group.add_row(
            Adw.ComboRow(
                title="Image Topic",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.img_topic_row.connect("notify::selected-item", self.on_img_topic_changed)
        self.img_stream_type_toggle_row = self.img_group.add_row(
            Adw.SwitchRow(title="Single Image / Continuous Stream")
        )
        self.img_stream_type_toggle_row.connect("notify::active", self.on_toggle_stream_type)
        self.img_row: ImageViewRow = self.img_group.add_row(ImageViewRow(title="Image"))

        # Create a Gio.ListStore to fill the ComboBox with
        self.img_topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.img_topic_row.set_model(self.img_topic_list_store)

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
        self.img_topic_row.set_factory(factory)

        # rows to display infos about the image
        self.info_group = self.pref_page.add_group(title="Infos", filterable=False)
        self.width_row: PrefRow = self.info_group.add_row(PrefRow(title="Image Width"))
        self.height_row = self.info_group.add_row(PrefRow(title="Image Height"))
        self.encoding_row = self.info_group.add_row(PrefRow(title="Image Encoding"))

        self.width_lbl = self.width_row.add_suffix_lbl("")
        self.height_lbl = self.height_row.add_suffix_lbl("")
        self.encoding_lbl = self.encoding_row.add_suffix_lbl("")

    def refresh_bg(self) -> bool:
        available_topics = self.ros2_connector.get_available_topics()
        self.available_img_topics = []

        for topic_name, topic_types in available_topics:
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            if topic_types == "sensor_msgs/msg/Image":
                self.available_img_topics.append(topic_name)

        return len(self.available_img_topics) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available topics
        for topic_name in self.available_img_topics:
            self.img_topic_list_store.append(Gtk.StringObject.new(topic_name))

        # set the selected service to the preselected one
        found_index = find_str_in_list_store(self.img_topic_list_store, self.preselect_topic)
        # found, found_index = self.img_topic_list_store.find(Gtk.StringObject.new(self.preselect_service))
        if found_index >= 0:
            self.img_topic_row.set_selected(found_index)
        else:
            self.img_topic_row.set_selected(0)

    def reset_ui(self):
        self.img_topic_list_store.remove_all()
        self.single_img_done = True
        self.img_row.reset_image_to_default_icon()
        self.remove_sub()

    def remove_sub(self):
        if self.sub:
            self.ros2_connector.destroy_subscription(self.sub)
            self.sub = None

    def trigger(self):
        if self.img_stream_type_toggle_row.get_active():
            self.play_pause_stream_btn.playing = True

    def on_unrealize(self, *args):
        super().on_unrealize(*args)
        self.remove_sub()

    def on_clear_img(self, *args):
        self.img_row.reset_image_to_default_icon()

    def on_toggle_stream_type(self, *args):
        # active = continuous stream, inactive = single shot
        if self.img_stream_type_toggle_row.get_active():
            self.single_shot_btn.set_visible(False)
            self.play_pause_stream_btn.set_visible(True)
        else:
            self.single_shot_btn.set_visible(True)
            self.play_pause_stream_btn.set_visible(False)

        self.play_pause_stream_btn.playing = False

    def on_single_shot_img(self, *args):
        self.single_img_done = False

    def on_play_pause_stream(self, *args):
        self.is_streaming = self.play_pause_stream_btn.playing

    def on_img_topic_changed(self, *args):
        if self.img_topic_list_store.get_n_items() <= 0:
            return

        self.remove_sub()

        topic_name = self.img_topic_row.get_selected_item().get_string()
        if topic_name:
            # TODO maybe add another button to actually subscribe to the topic and not create it by changing the name?
            self.sub = self.ros2_connector.add_subsciption(Image, topic_name, self.img_topic_callback)
            self.single_img_done = True
            self.img_row.reset_image_to_default_icon()

    def img_topic_callback(self, msg: Image, *args):
        if not self.is_mapped:
            return

        # apply rate limiting
        now = time.time()
        if now - self.last_update_time < 1.0 / self.max_update_rate:
            return

        if self.is_streaming or not self.single_img_done:
            # Convert sensor_msgs/Image to a BGR8 numpy array (default behavior).

            try:
                cv_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
                self.img_row.set_image_from_opencv(cv_image)

            except (RuntimeError, AttributeError, CvBridgeError) as e:
                self.show_toast(f"Error: {e}")

            # TODO fill the info rows
            self.width_lbl.set_label(str(msg.width))
            self.height_lbl.set_label(str(msg.height))
            self.encoding_lbl.set_label(str(msg.encoding))

            self.single_img_done = True
            self.last_update_time = now
