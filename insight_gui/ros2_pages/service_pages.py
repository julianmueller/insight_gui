# =============================================================================
# service_pages.py
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

from operator import itemgetter
from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden
from ros2service.api import get_service_names_and_types
from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.msg_type_info_pages import ServiceTypeInfoPage
from insight_gui.ros2_pages.node_pages import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ServiceListPage(ContentPage):
    __gtype_name__ = "ServiceListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service List")
        super().set_empty_page_text("Refresh to show services")
        super().set_search_entry_placeholder_text("Search for services")

        self.service_ns_groups: Dict[PrefGroup] = {}

    def on_refresh_blocking(self) -> bool:
        self.available_services = sorted(
            get_service_names_and_types(node=self.ros2_connector.node, include_hidden_services=True), key=itemgetter(0)
        )
        if len(self.available_services) == 0:
            self.pref_page.set_empty_page_text("No services found. Refresh to try again.")
            return False
        return True

    def on_refresh_gui(self):
        for service_name, service_types in self.available_services:
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
                subpage_kwargs={
                    "service_name": service_name,
                    "service_types": service_types,
                },
            )
            group.add_row(row)

    def on_clear_gui(self):
        for group in reversed(self.service_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.service_ns_groups.clear()


class ServiceInfoPage(ContentPage):
    __gtype_name__ = "ServiceInfoPage"

    def __init__(self, service_name: str, service_types: str | list[str], **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)
        super().set_title(f"Service <{service_name}>")

        self.service_name = service_name
        self.service_types = service_types
        self.detach_kwargs = {"service_name": service_name, "service_types": service_types}

    def on_realize(self, *args):
        super().on_realize(*args)

        # Service Type
        service_type_group = self.pref_page.add_group(title="Service Type")

        def add_srv_type_row(srv_type: str):
            srv_type_row = PrefRow(title=srv_type)  # , subtitle=node_full_name)
            srv_type_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceTypeInfoPage,
                subpage_kwargs={"srv_type_full_name": srv_type},
            )
            service_type_group.add_row(srv_type_row)

        if isinstance(self.service_types, str):
            add_srv_type_row(self.service_types)
        elif isinstance(self.service_types, list):
            for srv_type in self.service_types:
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
                    subpage_kwargs={
                        "node_name": node_name,
                        "node_namespace": node_namespace,
                        "node_full_name": node_full_name,
                    },
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
                    subpage_kwargs={
                        "node_name": node_name,
                        "node_namespace": node_namespace,
                        "node_full_name": node_full_name,
                    },
                )
                service_clients_group.add_row(row)

        # add the counts as descriptions
        service_servers_group.set_description_to_row_count()
        service_clients_group.set_description_to_row_count()
