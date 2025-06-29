# =============================================================================
# node_list_page.py
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

from ros2node.api import _is_hidden_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class NodeListPage(ContentPage):
    __gtype_name__ = "NodeListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Nodes")
        super().set_empty_page_text("No nodes to show")
        super().set_search_entry_placeholder_text("Search for nodes")
        super().set_refresh_fail_text("No active nodes found. Refresh to try again.")

        self.node_ns_groups: Dict[PrefGroup] = {}

        # self.node_list_group = self.pref_page.add_group(empty_group_text="Refresh to show nodes")

    def refresh_bg(self) -> bool:
        self.available_nodes = self.ros2_connector.get_available_nodes()

        if len(self.available_nodes) == 0:
            # self.node_list_group.set_empty_group_text("No nodes found. Refresh to try again.")
            return False
        return True

    def refresh_ui(self):
        for node_name, node_namespace, node_full_name in self.available_nodes:
            # if the namespace is empty (root namespace) use an empty string
            if node_namespace == "/":
                node_namespace = ""

            # put all nodes in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-nodes-by-namespace"):
                node_namespace = ""

            # get the namespace group of the action
            if node_namespace in self.node_ns_groups.keys():
                group = self.node_ns_groups[node_namespace]
            else:
                group = self.pref_page.add_group(title=node_namespace)
                self.node_ns_groups[node_namespace] = group

            row = PrefRow(title=node_name, subtitle=node_full_name)
            if _is_hidden_name(node_name):
                row.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden node")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=NodeInfoPage,
                subpage_kwargs={"node_full_name": node_full_name},
            )
            group.add_row(row)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.node_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.node_ns_groups.clear()
        # self.node_list_group.clear()
