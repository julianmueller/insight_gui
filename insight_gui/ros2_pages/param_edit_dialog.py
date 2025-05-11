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

from rcl_interfaces.msg import (
    Parameter,
    ParameterType,
    ParameterValue,
    ParameterDescriptor,
    FloatingPointRange,
    IntegerRange,
    SetParametersResult,
)
from rcl_interfaces.srv import SetParameters_Response
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
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, ScaleRow


class ParamEditDialog(Adw.PreferencesDialog):
    __gtype_name__ = "ParamEditDialog"

    def __init__(self, node_name: str, param_name: str, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title(f"Edit Parameter {param_name}")
        super().set_size_request(400, 600)
        GLib.idle_add(self._deferred_init)

        # TODO add a refresh button

        self.node_name = node_name
        self.param_name = param_name
        self.ros2_connector = ros2_connector

        # the message that holds the parameter
        self.param_msg = Parameter()
        self.param_msg.name = self.param_name
        self.param_msg.value: ParameterValue = ParameterValue()  # is this okay to leave it empty here?

        self.page = PrefPage(title="Edit Parameter", icon_name="document-edit-symbolic")
        super().add(self.page)

        self.group = self.page.add_group()

        self.name_row = self.group.add_row(
            PrefRow(title="Parameter Name", subtitle=self.param_name, css_classes=["property"])
        )
        self.node_name_row = self.group.add_row(
            PrefRow(title="Param of Node", subtitle=self.node_name, css_classes=["property"])
        )
        self.description_row = self.group.add_row(PrefRow(title="Description", css_classes=["property"]))
        self.type_row = self.group.add_row(PrefRow(title="Type", css_classes=["property"]))

        # rows, if the param is a bool
        self.current_bool_row = self.group.add_row(Adw.SwitchRow(title="Current Value", visible=False, sensitive=False))
        self.new_bool_row = self.group.add_row(Adw.SwitchRow(title="New Value", visible=False))
        self.new_bool_row.connect_data("notify::active", self.on_bool_value_change)

        # rows if the param is a constrained number
        self.current_number_range_row: ScaleRow = self.group.add_row(
            ScaleRow(title="Current Value", sensitive=False, visible=False)
        )
        self.new_number_range_row: ScaleRow = self.group.add_row(ScaleRow(title="New Value", visible=False))
        self.new_number_range_row.connect("value-changed", self.on_number_value_changed)

        # rows if the param is an un-constrained number
        self.current_number_text_row = self.group.add_row(
            PrefRow(title="Current Value", visible=False, css_classes=["property"], sensitive=False)
        )
        self.new_number_text_row = self.group.add_row(Adw.EntryRow(title="New Value", visible=False))
        self.new_number_text_row.connect_data("notify::text", self.on_number_text_value_change)

        # rows if the param is a text etc
        self.current_text_row = self.group.add_row(
            PrefRow(title="Current Value", visible=False, css_classes=["property"], sensitive=False)
        )
        self.new_text_row = self.group.add_row(Adw.EntryRow(title="New Value", visible=False))
        self.new_text_row.connect_data("notify::text", self.on_text_value_change)

        # TODO add all the rows, for when the param is a list/array of these types

        self.constraints_row = self.group.add_row(PrefRow(title="Constraints", visible=False, css_classes=["property"]))
        self.additional_constraints_row = self.group.add_row(
            PrefRow(title="Additional Constraints", visible=False, css_classes=["property"])
        )

        # finally the apply button
        self.apply_btn = self.group.add_row(ButtonRow(label="Apply change", func=self.on_apply, sensitive=False))

        # show note if param is read only
        self.read_only_row = self.group.add_row(PrefRow(title="Parameter is read-only!", visible=False))
        self.read_only_row.add_prefix_icon("warning-symbolic")

    def _deferred_init(self):
        # get parameter infos
        # TODO this call could be done async without waiting the 5 seconds timeout
        param_descriptor = call_describe_parameters(
            node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
        ).descriptors[0]

        # get the current value of the parameter
        self.current_param_value = get_value(
            parameter_value=call_get_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
            ).values[0]
        )

        # Parameter Description
        if param_descriptor.description:
            self.param_description = str(param_descriptor.description)
            self.description_row.set_subtitle(subtitle=self.param_description)

        # Parameter Type
        if param_descriptor.type:
            self.param_type = param_descriptor.type
            self.param_type_str = str(get_parameter_type_string(param_descriptor.type))

            # check if param type is dynamic
            if param_descriptor.dynamic_typing:
                # TODO dynamic typing is not supported by the gui
                self.param_type_str += " (dynamic, allowed to change type)"

            self.type_row.set_subtitle(self.param_type_str)

        # depending on whether the param is a bool, show different rows
        if self.param_type == ParameterType.PARAMETER_BOOL:
            self.current_bool_value = True if self.current_param_value == "true" else False
            self.param_msg.value.type = ParameterType.PARAMETER_BOOL
            self.param_msg.value.bool_value = self.current_bool_value

            self.current_bool_row.set_visible(True)
            self.current_bool_row.set_active(self.current_bool_value)
            self.new_bool_row.set_visible(True)
            self.new_bool_row.set_active(self.current_bool_value)

        # parameter is an integer
        elif self.param_type == ParameterType.PARAMETER_INTEGER:
            self.current_number_value = int(self.current_param_value)
            self.param_msg.value.type = ParameterType.PARAMETER_INTEGER
            self.param_msg.value.integer_value = self.current_number_value

            # param constraints are used to create a scale widget
            if param_descriptor.integer_range:
                int_range = param_descriptor.integer_range[0]  # TODO why is this a list?
                from_value = int(int_range.from_value)
                to_value = int(int_range.to_value)
                step = int(int_range.step)

                txt = f"From: {from_value}, To: {to_value}, Step: {step}"

                self.constraints_row.set_visible(True)
                self.constraints_row.set_subtitle(txt)

                # add a tooltip to the range
                self.constraints_row.subtitle_lbl.set_tooltip_text(
                    "Represents start, stop bounds (inclusive) and step of the parameter value"
                )

                self.current_number_range_row.set_digits(0)
                self.current_number_range_row.set_visible(True)
                self.current_number_range_row.set_range(
                    value=self.current_number_value, lower=from_value, upper=to_value, step=step
                )

                self.new_number_range_row.set_digits(0)
                self.new_number_range_row.set_visible(True)
                self.new_number_range_row.set_range(
                    value=self.current_number_value, lower=from_value, upper=to_value, step=step
                )

            # unconstrained parameters simply get a text input
            else:
                self.current_number_text_row.set_visible(True)
                self.current_number_text_row.set_subtitle(str(self.current_number_value))
                self.new_number_text_row.set_visible(True)
                self.new_number_text_row.set_text(str(self.current_number_value))

        # parameter is a float
        elif self.param_type == ParameterType.PARAMETER_DOUBLE:
            self.current_number_value = float(self.current_param_value)
            self.param_msg.value.type = ParameterType.PARAMETER_DOUBLE
            self.param_msg.value.double_value = self.current_number_value

            # param constraints are used to create a scale widget
            if param_descriptor.floating_point_range:
                float_range = param_descriptor.floating_point_range[0]  # TODO why is this a list?
                from_value = float(float_range.from_value)
                to_value = float(float_range.to_value)
                step = float(float_range.step)

                txt = f"From: {from_value}, To: {to_value}, Step: {step}"

                self.constraints_row.set_visible(True)
                self.constraints_row.set_subtitle(txt)

                # add a tooltip to the range
                self.constraints_row.subtitle_lbl.set_tooltip_text(
                    "Represents start, stop bounds (inclusive) and step of the parameter value"
                )

                self.current_number_range_row.set_digits(3)
                self.current_number_range_row.set_visible(True)
                self.current_number_range_row.set_range(
                    value=self.current_number_value, lower=from_value, upper=to_value, step=step
                )

                self.new_number_range_row.set_digits(3)
                self.new_number_range_row.set_visible(True)
                self.new_number_range_row.set_range(
                    value=self.current_number_value, lower=from_value, upper=to_value, step=step
                )

            # unconstrained parameters simply get a text input
            else:
                self.current_number_text_row.set_visible(True)
                self.current_number_text_row.set_subtitle(str(self.current_number_value))
                self.new_number_text_row.set_visible(True)
                self.new_number_text_row.set_text(str(self.current_number_value))

        # parameter is a text
        else:
            self.current_text_value = str(self.current_param_value)
            self.param_msg.value.type = ParameterType.PARAMETER_STRING
            self.param_msg.value.string_value = self.current_text_value

            self.current_text_row.set_visible(True)
            self.current_text_row.set_subtitle(str(self.current_text_value))
            self.new_text_row.set_visible(True)
            self.new_text_row.set_text(str(self.current_text_value))

        # Additional Contraints as plain text
        if param_descriptor.additional_constraints:
            self.additional_constraints_row.set_visible(True)
            self.additional_constraints_row.set_subtitle(str(param_descriptor.additional_constraints))

        # check if param is read only
        self.is_read_only = param_descriptor.read_only

        # disable the change button
        if self.is_read_only:
            self.new_bool_row.set_visible(False)
            self.new_number_range_row.set_visible(False)
            self.new_number_text_row.set_visible(False)
            self.new_text_row.set_visible(False)
            self.apply_btn.set_visible(False)

            self.read_only_row.set_visible(True)

    def on_bool_value_change(self, *args):
        new_bool_value = bool(self.new_bool_row.get_active())
        self.param_msg.value.bool_value = new_bool_value

        if new_bool_value == self.current_bool_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)

    def on_number_value_changed(self, *args):
        if self.param_type == ParameterType.PARAMETER_INTEGER:
            new_number_value = int(self.new_number_range_row.get_value())
            self.param_msg.value.integer_value = new_number_value
        elif self.param_type == ParameterType.PARAMETER_DOUBLE:
            new_number_value = float(self.new_number_range_row.get_value())
            self.param_msg.value.double_value = new_number_value

        if new_number_value == self.current_number_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)

    def on_number_text_value_change(self, *args):
        if self.param_type == ParameterType.PARAMETER_INTEGER:
            new_number_value = int(self.new_number_text_row.get_text())
            self.param_msg.value.integer_value = new_number_value
        elif self.param_type == ParameterType.PARAMETER_DOUBLE:
            new_number_value = float(self.new_number_text_row.get_text())
            self.param_msg.value.double_value = new_number_value

        if new_number_value == self.current_number_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)

    def on_text_value_change(self, *args):
        new_text_value = str(self.new_text_row.get_text())
        self.param_msg.value.string_value = new_text_value

        if new_text_value == self.current_text_value:
            self.apply_btn.set_sensitive(False)
        else:
            self.apply_btn.set_sensitive(True)

    def on_apply(self, *args):
        try:
            resp: SetParameters_Response = call_set_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameters=[self.param_msg]
            )
            if resp.results[0].successful:
                self.add_toast(Adw.Toast(title="Parameter changed successfully"))
                GLib.idle_add(self._deferred_init)  # TODO change this whole behaviour into reload etc
            else:
                reason = str(resp.results[0].reason)
                self.add_toast(Adw.Toast(title=f"Parameter changed failed: {reason}"))
        except Exception as e:
            self.add_toast(Adw.Toast(title=f"Error: {e}"))
        # self.close()
