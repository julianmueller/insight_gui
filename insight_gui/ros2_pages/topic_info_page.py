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
from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow


class TopicInfoPage(ContentPage):
    __gtype_name__ = "TopicInfoPage"

    def __init__(self, topic: TopicItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Topic {topic.full_name}")

        self.topic = topic
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
        self.topic_interface_type_group = self.pref_page.add_group(title="Topic Interface Type")

        # Publishers
        self.publishers_group = self.pref_page.add_group(
            title="Publishers", placeholder_text="This topic has no publishers."
        )

        # Subscribers
        self.subscribers_group = self.pref_page.add_group(
            title="Subscribers", placeholder_text="This topic has no subscribers."
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a pub/sub of this topic
        self.ros2_connector.refresh_nodes_store()
        self.available_nodes = self.ros2_connector.nodes_store
        return self.available_nodes is not None and self.available_nodes.get_n_items() > 0

    def refresh_ui(self):
        # create a row for the message type
        interface_type_row = PrefRow(title=self.topic.interface.full_name)
        interface_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=InterfaceInfoPage,
            subpage_kwargs={"interface": self.topic.interface},
        )
        self.topic_interface_type_group.add_row(interface_type_row)

        # populate the publishers and subscribers
        for node in self.available_nodes:
            # add those nodes, that are publishers to the topic # TODO this could probably be optimized
            publishers_list = self.ros2_connector.get_publishers_by_node(node=node)
            found, index = publishers_list.find(self.topic)
            if found:
                row = PrefRow(title=node.name, subtitle=node.full_name)
                if node.hidden:
                    row.add_prefix_icon("eye-not-looking-symbolic", tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node": node},
                )
                self.publishers_group.add_row(row)

            # add those nodes, that are subscribers to the topic # TODO this could probably be optimized
            subscribers_list = self.ros2_connector.get_subscribers_by_node(node=node)
            found, index = subscribers_list.find(self.topic)
            if found:
                row = PrefRow(title=node.name, subtitle=node.full_name)
                if node.hidden:
                    row.add_prefix_icon("eye-not-looking-symbolic", tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node": node},
                )
                self.subscribers_group.add_row(row)

        # add the counts as descriptions
        self.publishers_group.set_description_to_row_count()
        self.subscribers_group.set_description_to_row_count()

    def reset_ui(self):
        self.topic_interface_type_group.clear()
        self.publishers_group.clear()
        self.subscribers_group.clear()

    # def trigger(self): # TODO
    #     self._on_goto_subscriber_page()

    def _on_goto_publisher_page(self, *args):
        self.nav_view.push(TopicPublisherPage(preselect_topic=self.topic))

    def _on_goto_subscriber_page(self, *args):
        self.nav_view.push(TopicSubscriberPage(preselect_topic=self.topic))
