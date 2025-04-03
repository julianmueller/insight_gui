# =============================================================================
# param_edit_dialog.py
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

from rcl_interfaces.msg import ParameterType
from ros2param.api import (
    call_get_parameters,
    call_set_parameters,
    call_describe_parameters,
    get_value,
    get_parameter_type_string,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class ParamEditDialog(Adw.PreferencesDialog):
    __gtype_name__ = "ParamEditDialog"

    def __init__(self, node_name: str, param_name: str, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Edit Parameter")
        super().set_size_request(300, 500)
        GLib.idle_add(self._deferred_init)

        self.node_name = node_name
        self.param_name = param_name
        self.ros2_connector = ros2_connector

        self.page = PrefPage(title="Edit param", icon_name="document-edit-symbolic")
        super().add(self.page)

        self.group = self.page.add_group(title=f"Parameter: {self.param_name}", description=f"Node: {self.node_name}")
        self.description_row = self.group.add_row(PrefRow(title="Description", visible=False, css_classes=["property"]))
        self.additional_constraints_row = self.group.add_row(
            PrefRow(title="Additional Constraints", visible=False, css_classes=["property"])
        )
        self.dynamic_typing_row = self.group.add_row(
            PrefRow(title="Dynamic Typing", visible=False, css_classes=["property"])
        )
        self.floating_point_range_row = self.group.add_row(
            PrefRow(title="Floating Point Range", visible=False, css_classes=["property"])
        )
        self.integer_range_row = self.group.add_row(
            PrefRow(title="Integer Range", visible=False, css_classes=["property"])
        )
        self.type_row = self.group.add_row(PrefRow(title="Type", css_classes=["property"]))
        self.read_only_row = self.group.add_row(PrefRow(title="Is Read Only", css_classes=["property"]))

        # rows, if the param is a bool
        self.current_bool_value_row = self.group.add_row(
            Adw.SwitchRow(title="Current Value", visible=False, sensitive=False)
        )
        self.new_bool_value_row = self.group.add_row(Adw.SwitchRow(title="New Value", visible=False))
        self.new_bool_value_row.connect_data("notify::active", self.on_bool_value_change)

        # rows if the param is a text etc
        self.current_text_value_row = self.group.add_row(
            PrefRow(title="Current Value", visible=False, css_classes=["property"], sensitive=False)
        )
        self.new_text_value_row = self.group.add_row(Adw.EntryRow(title="New Value", visible=False))
        self.new_text_value_row.connect_data("notify::text", self.on_text_value_change)

        # finally the apply button
        self.apply_btn = self.group.add_row(ButtonRow(label="Apply change", func=self.on_apply_change, sensitive=False))

    def _deferred_init(self):
        # get parameter infos
        param_descriptor = call_describe_parameters(
            node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
        ).descriptors[0]

        if param_descriptor.description:
            self.description_row.set_visible(True)
            self.description_row.set_subtitle(subtitle=str(param_descriptor.description))

        if param_descriptor.additional_constraints:
            self.additional_constraints_row.set_properties(  # TODO does this work?
                visible=True, subtitle=param_descriptor.additional_constraints
            )

        if param_descriptor.dynamic_typing:
            self.dynamic_typing_row.set_visible(True)
            self.dynamic_typing_row.set_subtitle(str(param_descriptor.dynamic_typing))

        if param_descriptor.floating_point_range:
            self.floating_point_range_row.set_visible(True)
            self.floating_point_range_row.set_subtitle(str(param_descriptor.floating_point_range))

        if param_descriptor.integer_range:
            self.integer_range_row.set_visible(True)
            self.integer_range_row.set_subtitle(str(param_descriptor.integer_range))

        self.type_row.set_subtitle(str(get_parameter_type_string(param_descriptor.type)))

        read_only = param_descriptor.read_only
        self.read_only_row.set_subtitle(str(read_only))
        self.read_only_row.set_css_classes(["property"])

        # get the current value of the parameter
        param_value = get_value(
            parameter_value=call_get_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
            ).values[0]
        )

        # depending on whether the param is a bool, show different rows
        if param_descriptor.type == ParameterType.PARAMETER_BOOL:
            self.current_bool_value = True if param_value == "true" else False

            self.current_bool_value_row.set_visible(True)
            self.current_bool_value_row.set_active(self.current_bool_value)
            self.new_bool_value_row.set_visible(True)
            self.new_bool_value_row.set_active(self.current_bool_value)

        else:
            self.current_text_value = str(param_value)

            self.current_text_value_row.set_visible(True)
            self.current_text_value_row.set_subtitle(str(self.current_text_value))
            self.new_text_value_row.set_visible(True)
            self.new_text_value_row.set_text(str(self.current_text_value))

        # disable the change button
        if read_only:
            self.new_bool_value_row.set_sensitive(False)

    def on_bool_value_change(self, *args):
        if self.new_bool_value_row.get_active() == self.current_bool_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)
        return

    def on_text_value_change(self, *args):
        if str(self.current_text_value_row.get_text()) == self.current_text_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)

    def on_apply_change(self, *args):
        # response = call_set_parameters(
        #     node=self.ros2_connector.node, node_name=self.node_name, parameters=[self.param_name]
        # )
        # TODO this is not working yet
        print("changing params not working yet")
        self.close()
