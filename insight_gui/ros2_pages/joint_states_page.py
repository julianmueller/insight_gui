from operator import itemgetter

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2topic.api import get_topic_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import MessageTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class JointStatesPage(Adw.NavigationPage):
    __gtype_name__ = "JointStatesPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Topic List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for topics")
        self.content_page.set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})
        super().set_child(self.content_page)

        self.search_group = self.content_page.pref_page.add_group(filterable=False)
        self.joint_topic_row = self.search_group.add_row(
            Adw.ComboRow(
                title="Joint Topic",
                enable_search=True,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.joint_topic_row.connect("notify::selected-item", self.on_joint_topic_changed)
        self.joint_topic_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.joint_topic_row.set_model(self.joint_topic_list_store)

        self.joints_group = self.content_page.pref_page.add_group(
            title="Joints", empty_group_text="Refresh to show joints"
        )

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        self.joint_topic_list_store.remove_all()
        self.joints_group.clear()

        # DUMMY
        for i in range(10):
            row: PrefRow = self.joints_group.add_row(PrefRow(title=f"Joint {i}"))
            scale = Gtk.Scale(
                orientation=Gtk.Orientation.HORIZONTAL,
                adjustment=Gtk.Adjustment(value=0, lower=0, upper=100, step_increment=1),
                draw_value=True,
                digits=2,
                hexpand=True,
                value_pos=Gtk.PositionType.RIGHT,
            )
            scale.connect("notify::value-changed", lambda *args: print(scale.get_value()))
            plus_button = Gtk.Button(icon_name="plus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            minus_button = Gtk.Button(icon_name="minus-symbolic", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            plus_button.connect("clicked", lambda *args: scale.set_value(scale.get_value() + 1))
            minus_button.connect("clicked", lambda *args: scale.set_value(scale.get_value() - 1))
            row.add_suffix(minus_button)
            row.add_suffix(scale)
            row.add_suffix(plus_button)

        # available_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))

        # for i, (topic_name, topic_types) in enumerate(available_topics):
        #     # topic_types is a list, as multiple servers can advertise different types to the same topic
        #     # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
        #     if len(topic_types) == 1:
        #         topic_types = topic_types[0]
        #     else:
        #         topic_types = ", ".join(topic_types)

        #     row = PrefRow(title=topic_name, subtitle=topic_types)

        #     row.set_subpage_link()
        #     self.topic_group.add_row(row)

        # if self.topic_group.num_rows == 0:
        #     self.topic_group.set_empty_group_text("No topics found. Refresh to try again.")

        # return bool(self.content_page.pref_page.num_groups)

    def on_joint_topic_changed(self, *args):
        if self.joint_topic_list_store.get_n_items() <= 0:
            return
        # self.joints_group.clear()
        pass
