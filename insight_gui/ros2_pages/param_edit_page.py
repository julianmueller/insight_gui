# =============================================================================
# param_edit_page.py
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

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, ScaleRow, MultiButtonRow


class ParamEditPage(ContentPage):
    __gtype_name__ = "ParamEditPage"

    def __init__(self, node_name: str, param_name: str, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title(f"Parameter {param_name}")

        self.node_name = node_name
        self.param_name = param_name
        self.detach_kwargs = {
            "node_name": node_name,
            "param_name": param_name,
        }

        # the message that holds the parameter
        self.param_msg = Parameter()
        self.param_msg.name = self.param_name
        self.param_msg.value: ParameterValue = ParameterValue()  # is this okay to leave it empty here?

    def on_realize(self, *args):
        super().on_realize()

        self.group = self.pref_page.add_group()

        # apply button
        self.apply_btn = super().add_bottom_left_btn(
            label="Apply Changes",
            icon_name="emoji-flags-symbolic",
            func=self.on_apply,
            sensitive=False,
            tooltip_text="Apply changes to parameter",
            css_classes=["suggested-action"],
        )

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

    def refresh_bg(self):
        # get parameter infos
        # TODO this call could be done async without waiting the 5 seconds timeout
        self.param_descriptor = call_describe_parameters(
            node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
        ).descriptors[0]

        return self.param_descriptor is not None

    def refresh_ui(self):
        # get the current value of the parameter
        self.current_param_value = get_value(
            parameter_value=call_get_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
            ).values[0]
        )

        # Parameter Description
        if self.param_descriptor.description:
            self.param_description = str(self.param_descriptor.description)
            self.description_row.set_subtitle(subtitle=self.param_description)

        # Parameter Type
        if self.param_descriptor.type:
            self.param_type = self.param_descriptor.type
            self.param_type_str = str(get_parameter_type_string(self.param_descriptor.type))

            # check if param type is dynamic
            if self.param_descriptor.dynamic_typing:
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
            if self.param_descriptor.integer_range:
                int_range = self.param_descriptor.integer_range[0]  # TODO why is this a list?
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
            if self.param_descriptor.floating_point_range:
                float_range = self.param_descriptor.floating_point_range[0]  # TODO why is this a list?
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
        if self.param_descriptor.additional_constraints:
            self.additional_constraints_row.set_visible(True)
            self.additional_constraints_row.set_subtitle(str(self.param_descriptor.additional_constraints))

        # check if param is read only
        self.is_read_only = self.param_descriptor.read_only

        # disable the change button
        if self.is_read_only:
            self.show_banner("This parameter is read-only and cannot be changed.")

            self.new_bool_row.set_visible(False)
            self.new_number_range_row.set_visible(False)
            self.new_number_text_row.set_visible(False)
            self.new_text_row.set_visible(False)
            self.apply_btn.set_sensitive(False)

    def reset_ui(self):
        pass

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
                self.show_toast("Parameter changed successfully")
                self.refresh()
            else:
                reason = str(resp.results[0].reason)
                self.show_toast(f"Parameter changed failed: {reason}", priority=Adw.ToastPriority.HIGH)
        except Exception as e:
            self.show_toast(f"Error: {e}", priority=Adw.ToastPriority.HIGH)
