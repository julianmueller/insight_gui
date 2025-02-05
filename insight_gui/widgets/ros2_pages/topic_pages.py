from operator import itemgetter

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2topic.api import get_topic_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.ros2_pages.msg_type_info_pages import MessageTypeInfoPage
from insight_gui.widgets.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow


class TopicListPage(Adw.NavigationPage):
    __gtype_name__ = "TopicListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Topic List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for topics")
        super().set_child(self.content_page)

        self.list_group = self.content_page.pref_page.add_group(empty_msg="No topics found")

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        self.list_group.clear()

        available_topics = sorted(get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True))
        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            row = PrefRow(title=topic_name, subtitle=topic_types, is_hidden=topic_or_service_is_hidden(topic_name))
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_connector=self.ros2_connector,
            )
            self.list_group.add_row(row)

        return bool(self.content_page.pref_page.num_groups)


class TopicInfoPage(Adw.NavigationPage):
    __gtype_name__ = "TopicInfoPage"

    def __init__(
        self,
        topic_name: str,
        topic_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(f"Topic '{topic_name}'")

        self.topic_name = topic_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(search_enabled=True, refresh_enabled=False)
        super().set_child(self.content_page)

        # Message Type
        message_type_group = self.content_page.pref_page.add_group(title="Message Type")

        def add_msg_type_row(msg_type_full_name: str):
            msg_row = PrefRow(title=msg_type_full_name)  # , subtitle=node_full_name)
            msg_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=MessageTypeInfoPage,
                msg_type_full_name=msg_type_full_name,
            )
            message_type_group.add_row(msg_row)

        if isinstance(topic_types, str):
            add_msg_type_row(topic_types)
        elif isinstance(topic_types, list):
            for msg_type in topic_types:
                add_msg_type_row(msg_type)

        # first, gather all nodes, to check which of them is a pub/sub of this topic
        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        # Publishers
        publishers_group = self.content_page.pref_page.add_group(
            title="Publishers", empty_msg="Topic has no publishers"
        )

        # Subscribers
        subscribers_group = self.content_page.pref_page.add_group(
            title="Subscribers", empty_msg="Topic has no subscribers"
        )

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # TODO maybe use self.ros2_connector.node.get_publishers_info_by_topic()
            # add those nodes, that publish that topic
            publishers_list = self.ros2_connector.node.get_publisher_names_and_types_by_node(
                node_name=node_name,
                node_namespace=node_namespace,
            )
            if any(self.topic_name in pub for pub in publishers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name, is_hidden=_is_hidden_name(node_name))
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                publishers_group.add_row(row)

            # add those nodes, that subscribe to that
            # TODO maybe use self.ros2_connector.node.get_subscribers_info_by_topic()
            subscribers_list = self.ros2_connector.node.get_subscriber_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.topic_name in sub for sub in subscribers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name, is_hidden=_is_hidden_name(node_name))
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                subscribers_group.add_row(row)

        # add the counts as descriptions
        publishers_group.set_description_to_row_count()
        subscribers_group.set_description_to_row_count()
