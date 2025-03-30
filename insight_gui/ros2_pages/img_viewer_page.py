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

from ros2topic.api import get_topic_names_and_types
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, ImageViewRow, TextViewRow
from insight_gui.widgets.buttons import PlayPauseButton


class ImageViewerPage(ContentPage):
    __gtype_name__ = "ImageViewerPage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().connect("map", self.on_map)
        super().connect("unmap", self.on_unmap)
        super().set_title("Image Viewer")

        self.cv_bridge = CvBridge()
        self.sub = None

        self.img_group = self.pref_page.add_group(title="View Image", filterable=False)
        self.img_topic_row = self.img_group.add_row(
            Adw.ComboRow(
                title="Image Topic",
                enable_search=True,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.img_topic_row.connect("notify::selected-item", self.on_image_topic_changed)
        self.img_row: ImageViewRow = self.img_group.add_row(ImageViewRow(title="Image"))

        # Create a Gio.ListStore to fill the ComboBox with
        self.img_topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.img_topic_row.set_model(self.img_topic_list_store)

        self.continuous_img_stream = False
        self.single_img_done = False
        self.play_pause_btn = self.img_row.add_suffix(
            PlayPauseButton(
                default_active=self.continuous_img_stream,
                labels=("Continuous", "Single"),
                func=self.on_toggle_img_stream,
            ),
            prepend=True,
        )

        # rows to display infos about the image
        self.info_group = self.pref_page.add_group(title="Infos", filterable=False)
        self.width_row: PrefRow = self.info_group.add_row(PrefRow(title="Image Width"))
        self.height_row = self.info_group.add_row(PrefRow(title="Image Height"))
        self.encoding_row = self.info_group.add_row(PrefRow(title="Image Encoding"))

        self.width_lbl = self.width_row.add_suffix_lbl("")
        self.height_lbl = self.height_row.add_suffix_lbl("")
        self.encoding_lbl = self.encoding_row.add_suffix_lbl("")

    def on_map(self, *args):
        # TODO make the img stream start (again) when page is currently visible
        pass

    def on_unmap(self, *args):
        # TODO make the img stream stop when page is currently not visible
        pass

    def on_refresh_blocking(self) -> bool:
        self.img_topic_list = []

        available_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))

        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            if topic_types == "sensor_msgs/msg/Image":
                self.img_topic_list.append(topic_name)
        return len(self.img_topic_list) > 0

    def on_refresh_gui(self):
        for img_topic in self.img_topic_list:
            self.img_topic_list_store.append(Gtk.StringObject.new(img_topic))

        if self.img_topic_list_store.get_n_items() > 0:
            self.img_topic_row.set_model(self.img_topic_list_store)
            self.img_topic_row.set_selected(0)
        else:
            super().show_banner("No topic with images found")  # TODO add refresh btn

    def on_reset_gui(self):
        self.img_topic_list_store.remove_all()

    def on_image_topic_changed(self, *args):
        if self.img_topic_list_store.get_n_items() <= 0:
            return

        if self.sub:
            self.ros2_connector.destroy_subscription(self.sub)

        topic_name = self.img_topic_row.get_selected_item().get_string()
        if topic_name:
            # TODO maybe add another button to actually subscribe to the topic and not create it by changing the name?
            self.sub = self.ros2_connector.add_subsciption(Image, topic_name, self.on_ros_img_callback)
            self.single_img_done = False
            self.img_row.reset_image_to_default_icon()

    # TODO implement some rate limeting
    # TODO also pause, when the "tab" aka nav page is switched
    def on_ros_img_callback(self, msg: Image, *args):
        if self.continuous_img_stream or not self.single_img_done:
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

    def on_toggle_img_stream(self, playing: bool, *args):
        self.continuous_img_stream = playing
        self.single_img_done = False
