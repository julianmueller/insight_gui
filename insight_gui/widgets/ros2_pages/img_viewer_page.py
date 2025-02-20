from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2topic.api import get_topic_names_and_types
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.helpers.button_row import ButtonRow
from insight_gui.widgets.helpers.img_view_row import ImageViewRow


class ImageViewerPage(Adw.NavigationPage):
    __gtype_name__ = "ImageViewerPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Image Viewer")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector
        self.bridge = CvBridge()

        self.content_page = ContentPage(refresh_func=self.refresh, search_enabled=False)
        super().set_child(self.content_page)

        self.img_group = self.content_page.pref_page.add_group(title="View Image", filterable=False)
        self.img_topic_row = self.img_group.add_row(Adw.ComboRow(title="Image Topic", enable_search=True))
        self.img_topic_row.connect("notify::selected-item", self.on_image_topic_changed)
        self.img_row: ImageViewRow = self.img_group.add_row(ImageViewRow())

        # self.calc_button: ButtonRow = self.img_group.add_row(
        #     ButtonRow(
        #         title="Calculate transform",
        #         btn_icon_name="gnome-calculator-symbolic",
        #         tooltip_text="Calculate transformation from source to target",
        #         func=self.on_calc_transform,
        #         sensitive=False,
        #     )
        # )

        # rows to display infos about the image
        self.info_group = self.content_page.pref_page.add_group(title="Infos", filterable=False)
        self.width_row = self.info_group.add_row(PrefRow(title="Image Width"))
        self.height_row = self.info_group.add_row(PrefRow(title="Image Height"))
        self.encoding_row = self.info_group.add_row(PrefRow(title="Image Encoding"))

        self.width_lbl = self.width_row.add_suffix_label("")
        self.height_lbl = self.height_row.add_suffix_label("")
        self.encoding_lbl = self.encoding_row.add_suffix_label("")

    def refresh(self, *args) -> bool:
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        # TODO:
        # 1. look for all available topics
        # 2. filter those, that publish the message type Image
        # 3. fill the combo box with these topics
        # 4.
        self.topic_list = []

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

        # Create a Gio.ListStore
        self.list_store = Gio.ListStore.new(Gtk.StringObject)

        for img_topic in self.topic_list:
            self.list_store.append(Gtk.StringObject.new(img_topic))

        self.img_topic_row.set_model(self.list_store)
        self.img_topic_row.set_selected(0)

    def on_image_topic_changed(self, *args):
        topic_name = self.img_topic_row.get_selected_item().get_string()
        self.sub = self.ros2_connector.add_subsciption(Image, topic_name, self.on_ros_img_callback)

        # TODO add an option to pause the continuous update of the image stream/texture

    def on_ros_img_callback(self, msg: Image, *args):
        # Convert sensor_msgs/Image to a BGR8 numpy array (default behavior).
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        self.img_row.set_picture_from_opencv(cv_image)

        # TODO fill the info rows
        self.width_lbl.set_label(str(msg.width))
        self.height_lbl.set_label(str(msg.height))
        self.encoding_lbl.set_label(str(msg.encoding))
