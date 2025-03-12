from operator import itemgetter
from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2service.api import get_service_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.ros2_pages.msg_type_info_pages import ServiceTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ServiceListPage(ContentPage):
    __gtype_name__ = "ServiceListPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(empty_page_text="Refresh to show services", **kwargs)
        super().set_title("Service List")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Search for services")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.service_ns_groups: Dict[PrefGroup] = {}

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return

        self.clear()

        available_services = sorted(
            get_service_names_and_types(node=self.ros2_connector.node, include_hidden_services=True), key=itemgetter(0)
        )

        for service_name, service_types in available_services:
            # service_types is a list, as multiple servers can offer different types to the same service
            # see https://github.com/ros2/ros2cli/blob/acefd9c0d773e7a067a6c458455eebaa2fbc6751/ros2service/ros2service/api/__init__.py#L59
            if len(service_types) == 1:
                service_types = service_types[0]
            else:
                service_types = ", ".join(service_types)  # TODO this might cause problems in the info page

            # split service name into namespace and name
            parts = service_name.rstrip("/").split("/")
            namespace = "/".join(parts[:-1])  # Everything except the last part
            name = "/" + parts[-1]  # The last part, prefixed with '/'

            # TODO add a button to enable/disable sorting into groups
            # get the namespace group of the service
            if namespace in self.service_ns_groups.keys():
                group = self.service_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.service_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=name, subtitle=service_types)
            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                service_name=service_name,
                service_types=service_types,
                ros2_connector=self.ros2_connector,
            )
            group.add_row(row)

        if len(available_services) == 0:
            self.pref_page.set_empty_page_text("No services found. Refresh to try again.")

    def clear(self):
        for group in reversed(self.service_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.service_ns_groups.clear()


class ServiceInfoPage(ContentPage):
    __gtype_name__ = "ServiceInfoPage"

    def __init__(
        self,
        service_name: str,
        service_types: str | list[str],
        nav_view: Adw.NavigationView = None,
        ros2_connector: ROS2Connector = None,
        **kwargs,
    ):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Service <{service_name}>")

        self.service_name = service_name
        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(
            type(self),
            dedock_kwargs={
                "service_name": self.service_name,
                "service_types": service_types,
                "ros2_connector": self.ros2_connector,
            },
        )

        # Service Type
        service_type_group = self.pref_page.add_group(title="Service Type")

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
        service_servers_group = self.pref_page.add_group(
            title="Service Servers", empty_group_text="Service has no servers"
        )

        # Service Clients
        service_clients_group = self.pref_page.add_group(
            title="Service Clients", empty_group_text="Service has no clients"
        )

        for node_name, node_namespace, node_full_name in sorted(available_nodes, key=itemgetter(0)):
            # add those nodes, that serve this service
            service_server_list = self.ros2_connector.node.get_service_names_and_types_by_node(
                node_name=node_name,
                node_namespace=node_namespace,
            )
            if any(self.service_name in service for service in service_server_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

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
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

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
