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

from operator import itemgetter

from ros2node.api import _is_hidden_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.topic_pub_page import TopicPublisherPage
from insight_gui.ros2_pages.topic_sub_page import TopicSubscriberPage
from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class TopicInfoPage(ContentPage):
    __gtype_name__ = "TopicInfoPage"

    def __init__(self, topic_name: str, topic_types: str | list[str], **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Topic {topic_name}")

        self.topic_name = topic_name
        self.topic_types = topic_types
        self.detach_kwargs = {"topic_name": topic_name, "topic_types": topic_types}

        self.open_pub_btn = super().add_bottom_left_btn(
            label="Publish to topic",
            icon_name="megaphone-symbolic",
            func=self.on_goto_publisher_page,
            tooltip_text="Go to the topic publisher",
        )

        self.open_sub_btn = super().add_bottom_right_btn(
            label="Subscribe to Topic",
            icon_name="listen-symbolic",
            func=self.on_goto_subscriber_page,
            tooltip_text="Go to the topic subscriber",
        )

        # Message Type
        self.message_type_group = self.pref_page.add_group(title="Message Type")

        # Publishers
        self.publishers_group = self.pref_page.add_group(title="Publishers", empty_group_text="Topic has no publishers")

        # Subscribers
        self.subscribers_group = self.pref_page.add_group(
            title="Subscribers", empty_group_text="Topic has no subscribers"
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a pub/sub of this topic
        self.available_nodes = self.ros2_connector.get_available_nodes()
        return len(self.available_nodes) > 0

    def refresh_ui(self):
        def add_msg_type_row(msg_type_full_name: str):
            msg_row = PrefRow(title=msg_type_full_name)  # , subtitle=node_full_name)
            msg_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=InterfaceInfoPage,
                subpage_kwargs={"interface_full_name": msg_type_full_name},
            )
            self.message_type_group.add_row(msg_row)

        if isinstance(self.topic_types, str):
            add_msg_type_row(self.topic_types)
        elif isinstance(self.topic_types, list):
            for msg_type in self.topic_types:
                add_msg_type_row(msg_type)

        for node_name, node_namespace, node_full_name in sorted(self.available_nodes, key=itemgetter(0)):
            # TODO maybe use self.ros2_connector.node.get_publishers_info_by_topic()
            # add those nodes, that publish that topic
            publishers_list = self.ros2_connector.get_publishers_by_node(
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
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.publishers_group.add_row(row)

            # add those nodes, that subscribe to that
            # TODO maybe use self.ros2_connector.node.get_subscribers_info_by_topic()
            subscribers_list = self.ros2_connector.get_subscribers_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.topic_name in sub for sub in subscribers_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.subscribers_group.add_row(row)

        # add the counts as descriptions
        self.publishers_group.set_description_to_row_count()
        self.subscribers_group.set_description_to_row_count()

    def reset_ui(self):
        self.message_type_group.clear()
        self.publishers_group.clear()
        self.subscribers_group.clear()

    def trigger(self):
        self.on_goto_subscriber_page()

    def on_goto_publisher_page(self, *args):
        self.nav_view.push(TopicPublisherPage(preselect_topic=self.topic_name))

    def on_goto_subscriber_page(self, *args):
        self.nav_view.push(TopicSubscriberPage(preselect_topic=self.topic_name))
