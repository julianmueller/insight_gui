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

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return False

        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)

        # for every node with params add a group
        for node_name, node_namespace, node_full_name in sorted(available_nodes):
            future = call_list_parameters(node=self.ros2_connector.node, node_name=node_name)
            if future is None:
                continue

            parameter_list = future.result().result.names
            if len(parameter_list) == 0:
                continue

            # create a group and add all parameters
            group = self.pref_page.add_group(title=node_name)
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
                group.add_row(row)
            group.set_description_to_row_count()

        if len(available_nodes) == 0:
            self.pref_page.set_empty_group_text("No Parameters found. Refresh to try again.")

    def on_edit_param(self, *args, node_name: str, param_name: str):
        EditParamDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
