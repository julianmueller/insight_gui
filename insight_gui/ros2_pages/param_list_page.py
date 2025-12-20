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

from typing import Dict

from rclpy.parameter import Parameter
from rclpy.exceptions import ParameterNotDeclaredException
from rcl_interfaces.msg import ParameterDescriptor

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from insight_gui.models.parameter_item import ParameterItem
from insight_gui.ros2_pages.param_edit_page import ParamEditPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class ParameterListPage(ContentPage):
    __gtype_name__ = "ParameterListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Parameters List")
        super().set_placeholder_text("Refresh to show parameters")
        super().set_search_entry_placeholder_text("Search for parameters")

        self.parameter_lists: Dict[PrefGroup] = {}

    def refresh_bg(self):
        available_nodes = self.ros2_connector.get_available_nodes()

        if available_nodes is None or available_nodes.get_n_items() == 0:
            return False

        self.parameters_by_node: Dict[str, Gio.ListStore] = {}

        for node in available_nodes:
            parameters = self.ros2_connector.get_parameters_by_node(node=node)

            if parameters and parameters.get_n_items() > 0:
                self.parameters_by_node[node.full_name] = parameters

        return self.parameters_by_node if self.parameters_by_node else False

    def refresh_ui(self):
        # for every node with params add a group
        for node_full_name, param_store in self.parameters_by_node.items():
            # create a group and add all parameters
            group = self.pref_page.add_group(title=node_full_name)

            for param in param_store:
                row = PrefRow(title=param.name, subtitle=f"{param.type}: {param.value}")
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ParamEditPage,
                    subpage_kwargs={"parameter": param},
                )

                # if the parameter is read-only, a prefix icon is added to the row
                if param.read_only:
                    row.add_prefix_icon(icon_name="lock-alt-symbolic", tooltip_text="Read-only parameter")

                group.add_row(row)

            group.set_description_to_row_count()

    def reset_ui(self):
        self.pref_page.clear()
