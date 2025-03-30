# =============================================================================
# param_page.py
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

from ros2node.api import get_node_names
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

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.ros2_pages.param_edit_dialog import ParamEditDialog


class ParameterListPage(ContentPage):
    __gtype_name__ = "ParameterListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Parameters List")
        super().set_empty_page_text("Refresh to show parameters")
        super().set_search_entry_placeholder_text("Search for parameters")

        self.parameter_lists: Dict[PrefGroup] = {}

    def on_refresh_blocking(self) -> bool:
        self.available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        if len(self.available_nodes) == 0:
            self.pref_page.set_empty_group_text("No Parameters found. Refresh to try again.")
            return False

        for node_name, node_namespace, node_full_name in sorted(self.available_nodes):
            # TODO add a button to enable/disable sorting into groups
            # get the namespace group of the action

            # TODO this somehow also blocks
            future = call_list_parameters(node=self.ros2_connector.node, node_name=node_name)
            if future is None:
                continue

            param_list = future.result().result.names
            if len(param_list) == 0:
                continue

            self.parameter_lists[node_name] = param_list
        return len(self.parameter_lists) > 0

    def on_refresh_gui(self):
        # for every node with params add a group
        for node_name, param_list in sorted(self.parameter_lists.items(), key=itemgetter(0)):
            # create a group and add all parameters
            group = self.pref_page.add_group(title=node_name)
            for param_name in sorted(param_list):
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
                group.add_row(row)

            group.set_description_to_row_count()

    def on_reset_gui(self):
        self.pref_page.clear()

    def on_edit_param(self, *args, node_name: str, param_name: str):
        ParamEditDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
