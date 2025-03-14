# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from ros2node.api import get_node_names, _is_hidden_name
from ros2param.api import (
    call_list_parameters,
    call_get_parameters,
    call_describe_parameters,
    get_value,
    get_parameter_type_string,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.ros2_pages.edit_param_dialog import EditParamDialog


class ParameterListPage(ContentPage):
    __gtype_name__ = "ParameterListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(empty_page_text="Refresh to show parameters", **kwargs)
        super().set_title("Parameters List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Refresh to show parameters")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

    def refresh_blocking(self) -> bool:
        self.available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        if len(self.available_nodes) == 0:
            self.pref_page.set_empty_group_text("No Parameters found. Refresh to try again.")
            return False
        return True

    def refresh_gui(self):
        # for every node with params add a group
        for node_name, node_namespace, node_full_name in sorted(self.available_nodes):
            future = call_list_parameters(node=self.ros2_connector.node, node_name=node_name)
            if future is None:
                continue

            parameter_list = future.result().result.names
            if len(parameter_list) == 0:
                continue

            # create a group and add all parameters
            group = self.pref_page.add_group(title=node_name)
            rows = []
            for param_name in sorted(parameter_list):
                param_type = get_parameter_type_string(
                    call_describe_parameters(
                        node=self.ros2_connector.node, node_name=node_name, parameter_names=[param_name]
                    )
                    .descriptors[0]
                    .type
                )
                param_value = get_value(
                    parameter_value=call_get_parameters(
                        node=self.ros2_connector.node, node_name=node_name, parameter_names=[param_name]
                    ).values[0]
                )
                row = PrefRow(title=param_name, subtitle=f"{param_type}: {param_value}")
                row.add_suffix_btn(
                    icon_name="document-edit-symbolic",
                    tooltip_text="Edit",
                    func=self.on_edit_param,
                    func_kwargs={"node_name": node_name, "param_name": param_name},
                )
                rows.append(row)

            group.add_rows_idle(rows)
            group.set_description_to_row_count()

    def clear_gui(self):
        self.pref_page.clear()

    def on_edit_param(self, *args, node_name: str, param_name: str):
        EditParamDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
