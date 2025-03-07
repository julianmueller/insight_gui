from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2topic.api import get_topic_names_and_types
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, ImageViewRow, TextViewRow
from insight_gui.widgets.buttons import PlayPauseButton


class ImageViewerPage(Adw.NavigationPage):
    __gtype_name__ = "ImageViewerPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Image Viewer")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector
        self.bridge = CvBridge()

        self.content_page = ContentPage(refresh_func=self.refresh, search_enabled=False)
        self.content_page.set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})
        super().set_child(self.content_page)

        self.img_group = self.content_page.pref_page.add_group(title="View Image", filterable=False)
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
        self.info_group = self.content_page.pref_page.add_group(title="Infos", filterable=False)
        self.width_row: PrefRow = self.info_group.add_row(PrefRow(title="Image Width"))
        self.height_row = self.info_group.add_row(PrefRow(title="Image Height"))
        self.encoding_row = self.info_group.add_row(PrefRow(title="Image Encoding"))

        self.width_lbl = self.width_row.add_suffix_lbl("")
        self.height_lbl = self.height_row.add_suffix_lbl("")
        self.encoding_lbl = self.encoding_row.add_suffix_lbl("")

    def refresh(self, *args) -> bool:
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        self.topic_list = []
        self.img_topic_list_store.remove_all()

        available_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))
        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            if topic_types == "sensor_msgs/msg/Image":
                self.topic_list.append(topic_name)

        for img_topic in self.topic_list:
            self.img_topic_list_store.append(Gtk.StringObject.new(img_topic))

        if self.img_topic_list_store.get_n_items() > 0:
            self.img_topic_row.set_model(self.img_topic_list_store)
            self.img_topic_row.set_selected(0)
        else:
            self.content_page.show_toast("No topic with images found")

    def on_image_topic_changed(self, *args):
        if self.img_topic_list_store.get_n_items() <= 0:
            return

        topic_name = self.img_topic_row.get_selected_item().get_string()
        if topic_name:
            self.sub = self.ros2_connector.add_subsciption(Image, topic_name, self.on_ros_img_callback)
            self.single_img_done = False
            self.img_row.reset_image_to_default_icon()

    # TODO implement some rate limeting
    # TODO also pause, when the "tab" aka nav page is switched
    def on_ros_img_callback(self, msg: Image, *args):
        if self.continuous_img_stream or not self.single_img_done:
            # Convert sensor_msgs/Image to a BGR8 numpy array (default behavior).
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            self.img_row.set_image_from_opencv(cv_image)

            # TODO fill the info rows
            self.width_lbl.set_label(str(msg.width))
            self.height_lbl.set_label(str(msg.height))
            self.encoding_lbl.set_label(str(msg.encoding))

            self.single_img_done = True

    def on_toggle_img_stream(self, playing: bool, *args):
        self.continuous_img_stream = playing
        self.single_img_done = False
        print(f"playing: {playing}")
