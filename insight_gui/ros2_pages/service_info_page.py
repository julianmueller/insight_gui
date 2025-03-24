# =============================================================================
# service__info_page.py
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

from ros2node.api import _is_hidden_name, get_node_names

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.msg_type_info_pages import ServiceTypeInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


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
