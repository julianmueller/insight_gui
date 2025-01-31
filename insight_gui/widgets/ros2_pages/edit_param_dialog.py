from rcl_interfaces.msg import Parameter, ParameterType
from ros2param.api import (
    call_get_parameters,
    call_set_parameters,
    call_describe_parameters,
    get_parameter_type_string,
    get_value,
)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, Gio

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.helpers.pref_page import PrefPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.helpers.button_row import ButtonRow

# TODO add setting to show/hide hidden nodes/topics etc


class EditParamDialog(Adw.PreferencesDialog):
    __gtype_name__ = "EditParamDialog"

    def __init__(self, node_name: str, param_name: str, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)

        self.node_name = node_name
        self.param_name = param_name
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_title("Edit Parameter")

        # Page with ROS2 Settings
        self.page = PrefPage(title="Edit param", icon_name="document-edit-symbolic")
        super().add(self.page)

        param_descriptor = call_describe_parameters(
            node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
        ).descriptors[0]
        # 'additional_constraints',
        # 'description',
        # 'dynamic_typing',
        # 'floating_point_range',
        # 'get_fields_and_field_types',
        # 'integer_range',
        # 'name',
        # 'read_only',
        # 'type'

        param_value = get_value(
            parameter_value=call_get_parameters(
                node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[self.param_name]
            ).values[0]
        )

        # Group of build type
        group = self.page.add_group(title=f"Parameter: {self.param_name}", description=f"Node: {self.node_name}")
        # build_type_group.add_btn(
        #     icon_name="info-symbolic",
        #     tooltip_text="ROS Documentation",
        #     func=lambda: webbrowser.open(
        #         "https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html"
        #     ),
        # )

        # self.node_name_row = group.add_row(PrefRow(title="Node", subtitle=self.node_name))
        # self.param_name_row = group.add_row(PrefRow(title="Parameter", subtitle=self.param_name))
        if param_descriptor.description:
            self.description_row = group.add_row(
                PrefRow(title="Description", subtitle=param_descriptor.description, css_classes=["property"])
            )

        self.type_row = group.add_row(
            PrefRow(title="Type", subtitle=get_parameter_type_string(param_descriptor.type), css_classes=["property"])
        )
        self.read_only_row = group.add_row(
            PrefRow(title="Is Read Only", subtitle=param_descriptor.read_only, css_classes=["property"])
        )
        # TODO make that, if its read only, then the value cannot be changed

        if param_descriptor.type == ParameterType.PARAMETER_BOOL:
            bool_val = True if param_value == "true" else False
            self.bool_value_row = group.add_row(Adw.SwitchRow(title="Value", active=bool_val))
        else:
            self.current_value_row = group.add_row(
                PrefRow(title="Value", subtitle=param_value, css_classes=["property"])
            )
            self.new_value_row = group.add_row(Adw.EntryRow(title="New Value", text=param_value))

        self.apply_btn = group.add_row(
            ButtonRow(
                title="Apply change",
                # tooltip_text="Create ROS2 Package",
                func=self.on_apply_change,
            )
        )

    def on_apply_change(self, *args):
        print("Apply change")
        self.close()
