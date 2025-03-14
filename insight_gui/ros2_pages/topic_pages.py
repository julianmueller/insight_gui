# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from operator import itemgetter
from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2topic.api import get_topic_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import MessageTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class TopicListPage(ContentPage):
    __gtype_name__ = "TopicListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(empty_page_text="Refresh to show topics", **kwargs)
        super().set_title("Topic List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Search for topics")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.topic_ns_groups: Dict[PrefGroup] = {}

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return

        self.clear()

        available_topics = sorted(
            get_topic_names_and_types(node=self.ros2_connector.node, include_hidden_topics=True), key=itemgetter(0)
        )
        for i, (topic_name, topic_types) in enumerate(available_topics):
            # topic_types is a list, as multiple servers can advertise different types to the same topic
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(topic_types) == 1:
                topic_types = topic_types[0]
            else:
                topic_types = ", ".join(topic_types)

            # split topic name into namespace and name
            parts = topic_name.rstrip("/").split("/")
            namespace = "/".join(parts[:-1])  # Everything except the last part
            name = "/" + parts[-1]  # The last part, prefixed with '/'

            # TODO add a button to enable/disable sorting into groups
            # get the namespace group of the topic
            if namespace in self.topic_ns_groups.keys():
                group = self.topic_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.topic_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=name, subtitle=topic_types)
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_connector=self.ros2_connector,
            )
            group.add_row(row)

        if len(available_topics) == 0:
            self.pref_page.set_empty_page_text("No topics found. Refresh to try again.")

    def clear(self):
        for group in reversed(self.topic_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.topic_ns_groups.clear()


class TopicInfoPage(ContentPage):
    __gtype_name__ = "TopicInfoPage"

    def __init__(
        self,
        topic_name: str,
        topic_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Topic <{topic_name}>")

        self.topic_name = topic_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(
            type(self),
            dedock_kwargs={
                "topic_name": self.topic_name,
                "topic_types": topic_types,
                "ros2_connector": self.ros2_connector,
            },
        )

        # Message Type
        message_type_group = self.pref_page.add_group(title="Message Type")

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
        publishers_group = self.pref_page.add_group(title="Publishers", empty_group_text="Topic has no publishers")

        # Subscribers
        subscribers_group = self.pref_page.add_group(title="Subscribers", empty_group_text="Topic has no subscribers")

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # TODO maybe use self.ros2_connector.node.get_publishers_info_by_topic()
            # add those nodes, that publish that topic
            publishers_list = self.ros2_connector.node.get_publisher_names_and_types_by_node(
                node_name=node_name,
                node_namespace=node_namespace,
            )
            if any(self.topic_name in pub for pub in publishers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

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
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

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
