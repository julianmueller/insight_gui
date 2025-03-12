from operator import itemgetter

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node
from ros2node.api import _is_hidden_name, get_node_names
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
from insight_gui.ros2_pages.edit_param_dialog import EditParamDialog
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class NodeListPage(ContentPage):
    __gtype_name__ = "NodeListPage"

    def __init__(self, nav_view: Adw.NavigationView, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Node List")

        self.nav_view = nav_view  # if nav_view else self.get_parent()
        print(self.nav_view == self.get_parent())
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Search for nodes")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.node_list_group = self.pref_page.add_group(empty_group_text="Refresh to show nodes")

    def refresh(self, *args) -> bool:
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return

        self.clear()

        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=True)
        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            row = PrefRow(title=node_name, subtitle=node_full_name)
            if _is_hidden_name(node_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=NodeInfoPage,
                node_name=node_name,
                node_namespace=node_namespace,
                node_full_name=node_full_name,
                ros2_connector=self.ros2_connector,
            )

            self.node_list_group.add_row(row)

        if self.node_list_group.num_rows == 0:
            self.node_list_group.set_empty_group_text("No nodes found. Refresh to try again.")

    def clear(self):
        self.node_list_group.clear()


class NodeInfoPage(ContentPage):
    __gtype_name__ = "NodeInfoPage"

    def __init__(
        self,
        node_name: str,
        node_namespace: str,
        node_full_name: str,
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Node <{node_full_name}>")

        self.node_name = node_name
        self.node_namespace = node_namespace
        self.node_full_name = node_full_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(
            type(self),
            dedock_kwargs={
                "node_name": self.node_name,
                "node_namespace": self.node_namespace,
                "node_full_name": self.node_full_name,
                "ros2_connector": self.ros2_connector,
            },
        )

        # Imports here, to prevent circular imports # TODO find a nicer way?
        from insight_gui.ros2_pages.topic_pages import TopicInfoPage
        from insight_gui.ros2_pages.service_pages import ServiceInfoPage
        from insight_gui.ros2_pages.action_pages import ActionInfoPage

        # Publishers
        publishers_group = self.pref_page.add_group(title="Publishers", empty_group_text="Node has no publishers")

        # publisher_list = get_publisher_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        publisher_list = self.ros2_connector.node.get_publisher_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for topic_name, topic_types in sorted(publisher_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_connector=self.ros2_connector,
            )
            publishers_group.add_row(row)
        publishers_group.set_description_to_row_count()

        # Subscribers
        subscribers_group = self.pref_page.add_group(title="Subscribers", empty_group_text="Node has no subscribers")

        # subscriber_list = get_subscriber_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        subscriber_list = self.ros2_connector.node.get_subscriber_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for topic_name, topic_types in sorted(subscriber_list, key=itemgetter(0)):
            row = PrefRow(title=topic_name, subtitle=", ".join(topic_types))
            if topic_or_service_is_hidden(topic_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=TopicInfoPage,
                topic_name=topic_name,
                topic_types=topic_types,
                ros2_connector=self.ros2_connector,
            )
            subscribers_group.add_row(row)
        subscribers_group.set_description_to_row_count()

        # Service Servers
        service_servers_group = self.pref_page.add_group(
            title="Service Servers", description="", empty_group_text="Node has no service servers"
        )

        # service_servers_list = get_service_server_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        service_server_list = self.ros2_connector.node.get_service_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for service_name, service_types in sorted(service_server_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_connector=self.ros2_connector,
            )
            service_servers_group.add_row(row)
        service_servers_group.set_description_to_row_count()

        # Service Clients
        service_clients_group = self.pref_page.add_group(
            title="Service Clients", empty_group_text="Node has no service clients"
        )

        # service_clients_list = get_service_client_info(node=ros2_connector, remote_node_name=node_name, include_hidden=True)
        service_client_list = self.ros2_connector.node.get_client_names_and_types_by_node(
            node_name=node_name, node_namespace=node_namespace
        )
        for service_name, service_types in sorted(service_client_list, key=itemgetter(0)):
            row = PrefRow(title=service_name, subtitle=", ".join(service_types))
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_connector=self.ros2_connector,
            )
            service_clients_group.add_row(row)
        service_clients_group.set_description_to_row_count()

        # Action Servers
        action_servers_group = self.pref_page.add_group(
            title="Action Servers", empty_group_text="Node has no action servers"
        )

        action_servers_list = get_action_server_names_and_types_by_node(
            node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
        )
        for action_name, action_types in sorted(action_servers_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_connector=self.ros2_connector,
            )
            action_servers_group.add_row(row)
        action_servers_group.set_description_to_row_count()

        # Action Clients
        action_clients_group = self.pref_page.add_group(
            title="Action Clients", empty_group_text="Node has no action clients"
        )

        action_clients_list = get_action_client_names_and_types_by_node(
            node=self.ros2_connector.node, remote_node_name=node_name, remote_node_namespace=node_namespace
        )
        for action_name, action_types in sorted(action_clients_list, key=itemgetter(0)):
            row = PrefRow(title=action_name, subtitle=", ".join(action_types))
            # if topic_or_service_is_hidden(action_name): # TODO is_hidden possible for actions?
            #     row.add_prefix_icon(icon_name=HIDDEN_OBJ_ICON, tooltip_text="Hidden topic")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ActionInfoPage,
                action_name=action_name,
                action_types=action_types,
                ros2_connector=self.ros2_connector,
            )
            action_clients_group.add_row(row)
        action_clients_group.set_description_to_row_count()

        # Parameters
        parameters_group = self.pref_page.add_group(title="Parameters", empty_group_text="Node has no parameters")
        future = call_list_parameters(node=self.ros2_connector.node, node_name=node_name)
        if future is not None:
            parameter_list = future.result().result.names
            for param_name in sorted(parameter_list):
                param_type = get_parameter_type_string(
                    call_describe_parameters(
                        node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[param_name]
                    )
                    .descriptors[0]
                    .type
                )
                param_value = get_value(
                    parameter_value=call_get_parameters(
                        node=self.ros2_connector.node, node_name=self.node_name, parameter_names=[param_name]
                    ).values[0]
                )
                row = PrefRow(title=param_name, subtitle=f"{param_type}: {param_value}")
                row.add_suffix_btn(
                    icon_name="document-edit-symbolic",
                    tooltip_text="Edit",
                    func=self.on_edit_param,
                    func_kwargs={"node_name": node_name, "param_name": param_name},
                )
                parameters_group.add_row(row)
        parameters_group.set_description_to_row_count()

    def on_edit_param(self, *args, node_name: str, param_name: str):
        EditParamDialog(
            node_name=node_name,
            param_name=param_name,
            ros2_connector=self.ros2_connector,
        ).present(self)
