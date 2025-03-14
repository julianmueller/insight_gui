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
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class EditParamDialog(Adw.PreferencesDialog):
    __gtype_name__ = "EditParamDialog"

    def __init__(self, node_name: str, param_name: str, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)

        self.node_name = node_name
        self.param_name = param_name
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_title("Edit Parameter")

        self.page = PrefPage(title="Edit param", icon_name="document-edit-symbolic")
        super().add(self.page)
        group = self.page.add_group(title=f"Parameter: {self.param_name}", description=f"Node: {self.node_name}")

        # get parameter infos
        param_descriptor = call_describe_parameters(
            node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
        ).descriptors[0]

        if param_descriptor.description:
            self.description_row = group.add_row(
                PrefRow(title="Description", subtitle=param_descriptor.description, css_classes=["property"])
            )
        if param_descriptor.additional_constraints:
            self.description_row = group.add_row(
                PrefRow(
                    title="Additional Constraints",
                    subtitle=param_descriptor.additional_constraints,
                    css_classes=["property"],
                )
            )
        if param_descriptor.dynamic_typing:
            self.dynamic_typing_row = group.add_row(
                PrefRow(title="Dynamic Typing", subtitle=param_descriptor.dynamic_typing, css_classes=["property"])
            )
        if param_descriptor.floating_point_range:
            self.floating_point_range_row = group.add_row(
                PrefRow(
                    title="Floating Point Range",
                    subtitle=str(param_descriptor.floating_point_range),
                    css_classes=["property"],
                )
            )
        if param_descriptor.integer_range:
            self.integer_range_row = group.add_row(
                PrefRow(title="Integer Range", subtitle=str(param_descriptor.integer_range), css_classes=["property"])
            )

        self.type_row = group.add_row(
            PrefRow(title="Type", subtitle=get_parameter_type_string(param_descriptor.type), css_classes=["property"])
        )

        read_only = param_descriptor.read_only
        self.read_only_row = group.add_row(PrefRow(title="Is Read Only", subtitle=read_only, css_classes=["property"]))

        # get the current value
        param_value = get_value(
            parameter_value=call_get_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
            ).values[0]
        )

        if param_descriptor.type == ParameterType.PARAMETER_BOOL:
            bool_val = True if param_value == "true" else False
            self.current_value_row = group.add_row(
                Adw.SwitchRow(title="Current Value", active=bool_val, sensitive=False)
            )
            self.new_value_row = group.add_row(Adw.SwitchRow(title="New Value", active=bool_val))
            self.new_value_row.connect_data(
                "notify::active", lambda *_: self.on_change(widget=self.new_value_row, default_value=bool_val)
            )
        else:
            self.current_value_row = group.add_row(
                PrefRow(title="Current Value", subtitle=param_value, css_classes=["property"])
            )
            self.new_value_row = group.add_row(Adw.EntryRow(title="New Value", text=param_value))
            self.new_value_row.connect_data(
                "notify::text",
                lambda *_: self.on_change(widget=self.new_value_row, default_value=param_value),
            )

        # disable the change button
        if read_only:
            self.new_value_row.set_sensitive(False)

        self.apply_btn = group.add_row(
            ButtonRow(
                label="Apply change",
                func=self.on_apply_change,
                sensitive=False,
            )
        )

    def on_change(self, widget: Gtk.Widget, default_value):
        if isinstance(widget, Adw.SwitchRow):
            if widget.get_active() == default_value:
                self.apply_btn.set_sensitive(False)
            else:
                self.apply_btn.set_sensitive(True)
            return
        else:
            if str(widget.get_text()) == str(default_value):
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
