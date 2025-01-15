from operator import itemgetter
import yaml
import time

import rclpy

# from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
from geometry_msgs.msg import TransformStamped

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.ros2_node import ROS2CommunicationNode
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.helpers.button_row import ButtonRow
from insight_gui.widgets.helpers.text_view_row import TextViewRow


class TransformsPage(Adw.NavigationPage):
    __gtype_name__ = "TransformsPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_node: ROS2CommunicationNode = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Transforms")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_node = ros2_node if ros2_node else self.get_root().ros2_node

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for Frames")
        super().set_child(self.content_page)

        self.calc_group = self.content_page.pref_page.add_group(title="Calculate Transform")

        # TODO use prefix_icons left-large-symbolic and right-large-symbolic
        self.source_frame_row = self.calc_group.add_row(Adw.ComboRow(title="Source Frame"))
        self.source_frame_row.connect("notify::selected-item", self.on_source_frame_changed)
        self.target_frame_row = self.calc_group.add_row(Adw.ComboRow(title="Target Frame"))
        self.target_frame_row.connect("notify::selected-item", self.on_target_frame_changed)

        self.calc_button: ButtonRow = self.calc_group.add_row(
            ButtonRow(
                title="Calculate transform",
                # start_icon_name="gnome-calculator-symbolic",
                tooltip_text="Calculate transformation from source to target",
                func=self.on_calc_transform,
            )
        )

        self.result_row = self.calc_group.add_row(TextViewRow(title="Result", show_copy_btn=True, min_height=200))
        self.result_row.set_visible(False)  # TODO this does somehow not work

        # self.list_group = self.content_page.pref_page.add_group(empty_msg="No transforms found")

        self.frames_group = self.content_page.pref_page.add_group(title="Frames", empty_msg="No frames found")
        self.frames_list = []

    def refresh(self, *args) -> bool:
        if not self.ros2_node.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_node.start_node)
            return False

        self.frames_group.clear()

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.ros2_node.node)
        time.sleep(1.0)

        frames_dict = yaml.safe_load(self.tf_buffer.all_frames_as_yaml())
        self.frames_list = sorted(list(frames_dict.keys()))

        # Create a Gio.ListStore
        self.list_store = Gio.ListStore.new(Gtk.StringObject)

        for frame_name in self.frames_list:
            # Create a PrefRow for each frame
            self.frames_group.add_row(PrefRow(title=frame_name))

            # Fill the ListStore with items
            self.list_store.append(Gtk.StringObject.new(frame_name))

        # Set the Gio.ListModel on the ComboRow
        self.source_frame_row.set_model(self.list_store)
        self.target_frame_row.set_model(self.list_store)

    def on_source_frame_changed(self, *args):
        self.source_frame = self.source_frame_row.get_selected_item().get_string()

    def on_target_frame_changed(self, *args):
        self.target_frame = self.target_frame_row.get_selected_item().get_string()

    def on_calc_transform(self, *args):
        source_frame = self.source_frame_row.get_selected_item().get_string()
        target_frame = self.target_frame_row.get_selected_item().get_string()

        if source_frame == target_frame:
            self.content_page.show_toast("Source and target frame cannot be the same")
            return

        try:
            # Lookup transform
            transform: TransformStamped = self.tf_buffer.lookup_transform(
                target_frame=source_frame, source_frame=target_frame, time=rclpy.time.Time()
            )

            text = (
                f"Transform from {self.source_frame} to {self.target_frame}:\n"
                + "Translation:\n"
                + f"  x: {transform.transform.translation.x:.8f},\n"
                + f"  y: {transform.transform.translation.y:.8f},\n"
                + f"  z: {transform.transform.translation.z:.8f}\n"
                + "Rotation:\n"
                + f"  x: {transform.transform.rotation.x:.8f},\n"
                + f"  y: {transform.transform.rotation.y:.8f},\n"
                + f"  z: {transform.transform.rotation.z:.8f},\n"
                + f"  w: {transform.transform.rotation.w:.8f}"
            )

            self.result_row.set_text(text)
            self.result_row.set_visible(True)

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().error(f"Could not calculate transform: {e}")
            self.result_row.set_visible(False)
