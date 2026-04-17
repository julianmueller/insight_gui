# =============================================================================
# topic_info_page.py
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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.models.topic_item import TopicItem
from insight_gui.ros2_pages.topic_pub_page import TopicPublisherPage
from insight_gui.ros2_pages.topic_sub_page import TopicSubscriberPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import InterfaceTypeRow, NodeRow


class TopicInfoPage(ContentPage):
    __gtype_name__ = "TopicInfoPage"

    def __init__(self, topic: TopicItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Topic {topic.full_name}")

        self.topic = topic
        self.topic_full_name = topic.full_name
        self.topic_interface_full_name = topic.interface.full_name
        self.detach_kwargs = {"topic": topic}

        self.open_pub_btn = super().add_bottom_left_btn(
            label="Publish to topic",
            icon_name="rss-feed-symbolic",
            func=self._on_goto_publisher_page,
            tooltip_text="Go to the topic publisher",
        )

        self.open_sub_btn = super().add_bottom_right_btn(
            label="Subscribe to Topic",
            icon_name="subscriptions-symbolic",
            func=self._on_goto_subscriber_page,
            tooltip_text="Go to the topic subscriber",
        )

        # Topic Interface Type
        self.topic_interface_type_group = self.pref_page.add_group(title="Topic Interface Type", collapsable=True)

        # Publishers
        self.publishers_group = self.pref_page.add_group(
            title="Publishers", placeholder_text="This topic has no publishers.", collapsable=True
        )

        # Subscribers
        self.subscribers_group = self.pref_page.add_group(
            title="Subscribers", placeholder_text="This topic has no subscribers.", collapsable=True
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a pub/sub of this topic
        self.publisher_nodes = []
        self.subscriber_nodes = []

        for node in self.ros2_connector.collect_nodes():
            publishers = self.ros2_connector.collect_publishers_by_node(node=node)
            if any(publisher.full_name == self.topic_full_name for publisher in publishers):
                self.publisher_nodes.append(node)

            subscribers = self.ros2_connector.collect_subscribers_by_node(node=node)
            if any(subscriber.full_name == self.topic_full_name for subscriber in subscribers):
                self.subscriber_nodes.append(node)

        return bool(self.publisher_nodes or self.subscriber_nodes)

    def refresh_ui(self):
        # create a row for the message type
        interface_type_row = InterfaceTypeRow(interface=self.topic.interface, nav_view=self.nav_view)
        self._add_rows_async(self.topic_interface_type_group, (interface_type_row,), batch_size=1)
        self._add_item_rows_async(
            self.publishers_group,
            self.publisher_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.publishers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.subscribers_group,
            self.subscriber_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.subscribers_group.set_description_to_row_count,
        )

    def _build_node_row(self, node) -> NodeRow:
        return NodeRow(node=node, nav_view=self.nav_view)

    def reset_ui(self):
        self.topic_interface_type_group.clear()
        self.publishers_group.clear()
        self.subscribers_group.clear()

    # def trigger(self): # TODO
    #     self._on_goto_subscriber_page()

    def _on_goto_publisher_page(self, *args):
        self._push_subpage(TopicPublisherPage, {"preselect_topic": self.topic})

    def _on_goto_subscriber_page(self, *args):
        self._push_subpage(TopicSubscriberPage, {"preselect_topic": self.topic})
