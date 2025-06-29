# =============================================================================
# topic_list_page.py
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

import re
from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class TopicListPage(ContentPage):
    __gtype_name__ = "TopicListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Topic List")
        super().set_empty_page_text("No topics to show")
        super().set_search_entry_placeholder_text("Search for topics")
        super().set_refresh_fail_text("No topics found. Refresh to try again.")

        self.topic_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.available_topics = self.ros2_connector.get_available_topics()
        return len(self.available_topics) > 0

    def refresh_ui(self):
        # TODO this is ugly
        from insight_gui.ros2_pages.topic_info_page import TopicInfoPage

        for topic_name, topic_types in self.available_topics:
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

            # put all topics in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-topics-by-namespace"):
                namespace = ""

            # get the namespace group of the topic
            if namespace in self.topic_ns_groups.keys():
                group = self.topic_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.topic_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=topic_name, subtitle=topic_types)
            row.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
            row.subtitle_lbl.set_tooltip_text(topic_name)

            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon("eye-not-looking-symbolic", tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                subpage_kwargs={"topic_name": topic_name, "topic_types": topic_types},
            )
            group.add_row(row)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.topic_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.topic_ns_groups.clear()
