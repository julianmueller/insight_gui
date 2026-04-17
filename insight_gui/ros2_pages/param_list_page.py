# =============================================================================
# param_list_page.py
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

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import ParameterRow


class ParameterListPage(ContentPage):
    __gtype_name__ = "ParameterListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Parameters List")
        super().set_placeholder_text("Refresh to show parameters")
        super().set_search_entry_placeholder_text("Search for parameters")

        self.parameters_by_node = []

    def refresh_bg(self):
        available_nodes = self.ros2_connector.collect_nodes()

        if not available_nodes:
            return False

        self.parameters_by_node = []

        for node in available_nodes:
            parameters = self.ros2_connector.collect_parameters(node=node)

            if parameters:
                self.parameters_by_node.append((node, parameters))

        return bool(self.parameters_by_node)

    def refresh_ui(self):
        # for every node with params add a group
        for node, parameters in self.parameters_by_node:
            # create a group and add all parameters
            group = self.pref_page.add_group(title=node.full_name)
            self._add_item_rows_async(
                group,
                parameters,
                self._build_parameter_row,
                batch_size=8,
                on_done=group.set_description_to_row_count,
            )

    def _build_parameter_row(self, param) -> ParameterRow:
        return ParameterRow(parameter=param, nav_view=self.nav_view)

    def reset_ui(self):
        self.pref_page.clear()
