# =============================================================================
# action_list_page.py
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

from insight_gui.ros2_pages.action_info_page import ActionInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.model_rows import ActionRow


# TODO do the GObject refactor for the entire page
class ActionListPage(ContentPage):
    __gtype_name__ = "ActionListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Actions")
        super().set_placeholder_text("No actions to show")
        super().set_search_entry_placeholder_text("Search for actions")
        super().set_refresh_fail_text("No actions found. Refresh to try again.")

        self.action_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.ros2_connector.refresh_actions_store()
        self.available_actions = self.ros2_connector.actions_store
        return self.available_actions is not None and self.available_actions.get_n_items() > 0

    def refresh_ui(self):
        rows_by_group: Dict[PrefGroup, list] = {}
        for action in self.available_actions:
            # put all actions in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-actions-by-namespace"):
                namespace = ""
            else:
                namespace = action.namespace if action.namespace else "/"

            # get the namespace group of the action
            if namespace in self.action_ns_groups.keys():
                group = self.action_ns_groups[namespace]
            else:
                description = "global namespace" if action.namespace == "/" else ""
                group = self.pref_page.add_group(title=namespace, description=description)
                self.action_ns_groups[namespace] = group

            row = ActionRow(action=action)
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                subpage_kwargs={"action": action},
                label="Show action info page",
            )
            rows_by_group.setdefault(group, []).append(row)

        for group, rows in rows_by_group.items():
            group.add_rows(rows, batch_size=10)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.action_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.action_ns_groups.clear()
