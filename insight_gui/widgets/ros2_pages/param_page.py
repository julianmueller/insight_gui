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
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow
from insight_gui.widgets.ros2_pages.edit_param_dialog import EditParamDialog


class ParameterListPage(Adw.NavigationPage):
    __gtype_name__ = "ParameterListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Parameters List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for Parameters")
        super().set_child(self.content_page)

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False
        # self.list_group.clear()

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
            group = self.content_page.pref_page.add_group(title=node_name)
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
                    node_name=node_name,
                    param_name=param_name,
                )
                group.add_row(row)
            group.set_description_to_row_count()

        return bool(self.content_page.pref_page.num_groups)

    def on_edit_param(self, *args, node_name: str, param_name: str):
        EditParamDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
