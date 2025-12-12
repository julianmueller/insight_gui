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
from operator import itemgetter

from rclpy.parameter import Parameter
from rclpy.exceptions import ParameterNotDeclaredException
from rcl_interfaces.msg import ParameterDescriptor

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

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

        if len(available_nodes) == 0:
            return False

        parameters_by_node: Dict[str, list[tuple[str, Dict[str, object]]]] = {}

        for node_name, _node_namespace, _node_full_name in sorted(available_nodes):
            param_names = self.ros2_connector.get_parameters_by_node(node_name=node_name)
            if not param_names:
                continue

            param_entries: list[tuple[str, Dict[str, object]]] = []
            for param_name in sorted(param_names):
                param_info = self.ros2_connector.get_parameter_info(node_name=node_name, parameter_name=param_name)
                param_entries.append((param_name, param_info))

            if param_entries:
                parameters_by_node[node_name] = param_entries

        return parameters_by_node if parameters_by_node else False

    def refresh_ui(self, parameters_by_node: Dict[str, list[tuple[str, Dict[str, object]]]]):
        # for every node with params add a group
        for node_name, param_entries in sorted(parameters_by_node.items(), key=itemgetter(0)):
            # create a group and add all parameters
            group = self.pref_page.add_group(title=node_name)
            for param_name, param_info in param_entries:
                param_type = param_info.get("type", "")
                param_value = param_info.get("value")
                param_read_only = bool(param_info.get("read_only", False))

                row = PrefRow(title=param_name, subtitle=f"{param_type}: {param_value}")
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=ParamEditPage,
                    subpage_kwargs={"node_name": node_name, "param_name": param_name},
                )

                # if the parameter is read-only, a prefix icon is added to the row
                if param_read_only:
                    row.add_prefix_icon(icon_name="lock-alt-symbolic", tooltip_text="Read-only parameter")

                group.add_row(row)

            group.set_description_to_row_count()

    def reset_ui(self):
        self.pref_page.clear()
