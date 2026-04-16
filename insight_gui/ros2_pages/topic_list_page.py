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

from typing import Dict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.model_rows import TopicRow


class TopicListPage(ContentPage):
    __gtype_name__ = "TopicListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Topic List")
        super().set_placeholder_text("No topics to show")
        super().set_search_entry_placeholder_text("Search for topics")
        super().set_refresh_fail_text("No topics found. Refresh to try again.")

        self.topic_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.available_topics = self.ros2_connector.collect_topics()
        return bool(self.available_topics)

    def refresh_ui(self):
        topics_by_group: Dict[PrefGroup, list] = {}
        # TODO this is ugly
        from insight_gui.ros2_pages.topic_info_page import TopicInfoPage

        self._topic_info_page_class = TopicInfoPage

        for topic in self.available_topics:
            # put all topics in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-topics-by-namespace"):
                namespace = ""
            else:
                namespace = topic.namespace if topic.namespace else "/"

            # get the namespace group of the topic
            if namespace in self.topic_ns_groups.keys():
                group = self.topic_ns_groups[namespace]
            else:
                description = "global namespace" if namespace == "/" else ""
                group = self.pref_page.add_group(title=namespace, description=description)
                self.topic_ns_groups[namespace] = group

            topics_by_group.setdefault(group, []).append(topic)

        self.pref_page.sort_groups()

        for group, topics in topics_by_group.items():
            self._add_item_rows_async(
                group,
                topics,
                self._build_topic_row,
                batch_size=10,
            )

    def _build_topic_row(self, topic) -> TopicRow:
        row = TopicRow(topic=topic)
        row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=self._topic_info_page_class,
            subpage_kwargs={"topic": topic},
            label="Show topic info page",
        )
        return row

    def reset_ui(self):
        for group in reversed(self.topic_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.topic_ns_groups.clear()
