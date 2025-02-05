from operator import itemgetter

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2service.api import get_service_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.ros2_pages.msg_type_info_pages import ServiceTypeInfoPage
from insight_gui.widgets.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.helpers.content_page import ContentPage
from insight_gui.widgets.helpers.pref_row import PrefRow


# TODO group by package names
class ServiceListPage(Adw.NavigationPage):
    __gtype_name__ = "ServiceListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(refresh_func=self.refresh)
        self.content_page.set_search_entry_placeholder_text("Search for services")
        super().set_child(self.content_page)

        self.list_group = self.content_page.pref_page.add_group(empty_msg="No services found")

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            self.content_page.show_toast_w_btn(
                "ROS2 node not running", "Start Node", func=self.ros2_connector.start_node
            )
            return False

        self.list_group.clear()

        available_services = sorted(
            get_service_names_and_types(node=self.ros2_connector.node, include_hidden_services=True)
        )
        for service_name, service_types in available_services:
            # service_types is a list, as multiple servers can offer different types to the same service
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(service_types) == 1:
                service_types = service_types[0]
            else:
                service_types = ", ".join(service_types)  # TODO this might cause problems in the info page

            row = PrefRow(
                title=service_name, subtitle=service_types, is_hidden=topic_or_service_is_hidden(service_name)
            )
            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_connector=self.ros2_connector,
            )
            self.list_group.add_row(row)

        return bool(self.content_page.pref_page.num_groups)


class ServiceInfoPage(Adw.NavigationPage):
    __gtype_name__ = "ServiceInfoPage"

    def __init__(
        self,
        service_name: str,
        service_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        super().set_title(f"Service '{service_name}'")

        self.service_name = service_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        self.content_page = ContentPage(search_enabled=True, refresh_enabled=False)
        super().set_child(self.content_page)

        # Service Type
        service_type_group = self.content_page.pref_page.add_group(title="Service Type")

        def add_srv_type_row(srv_type: str):
            srv_type_row = PrefRow(title=srv_type)  # , subtitle=node_full_name)
            srv_type_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceTypeInfoPage,
                srv_type_full_name=srv_type,
            )
            service_type_group.add_row(srv_type_row)

        if isinstance(service_types, str):
            add_srv_type_row(service_types)
        elif isinstance(service_types, list):
            for srv_type in service_types:
                add_srv_type_row(srv_type)

        # first, gather all nodes, to check which of them is a server/client of the service
        available_nodes = get_node_names(node=self.ros2_connector.node, include_hidden_nodes=False)

        # Service Servers
        service_servers_group = self.content_page.pref_page.add_group(
            title="Service Servers", empty_msg="Service has no servers"
        )

        # Service Clients
        service_clients_group = self.content_page.pref_page.add_group(
            title="Service Clients", empty_msg="Service has no clients"
        )

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # add those nodes, that serve this service
            service_server_list = self.ros2_connector.node.get_service_names_and_types_by_node(
                node_name=node_name,
                node_namespace=node_namespace,
            )
            if any(self.service_name in service for service in service_server_list):
                row = PrefRow(title=node_name, subtitle=node_full_name, is_hidden=_is_hidden_name(node_name))
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                service_servers_group.add_row(row)

            # add those nodes, that are clients to this service
            service_client_list = self.ros2_connector.node.get_client_names_and_types_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.service_name in service for service in service_client_list):
                row = PrefRow(title=node_name, subtitle=node_full_name, is_hidden=_is_hidden_name(node_name))
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    node_name=node_name,
                    node_namespace=node_namespace,
                    node_full_name=node_full_name,
                    ros2_connector=self.ros2_connector,
                )
                service_clients_group.add_row(row)

        # add the counts as descriptions
        service_servers_group.set_description_to_row_count()
        service_clients_group.set_description_to_row_count()
