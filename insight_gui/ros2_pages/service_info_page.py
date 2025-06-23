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

from ros2node.api import _is_hidden_name

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.ros2_pages.node_info_page import NodeInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.utils.constants import HIDDEN_OBJ_ICON


class ServiceInfoPage(ContentPage):
    __gtype_name__ = "ServiceInfoPage"

    def __init__(self, service_name: str, service_types: str | list[str], **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Service {service_name}")

        self.service_name = service_name
        self.service_types = service_types
        self.detach_kwargs = {"service_name": service_name, "service_types": service_types}

        self.call_btn = super().add_bottom_left_btn(
            label="Open Caller",
            icon_name="call-start-symbolic",
            func=self.on_goto_caller_page,
            tooltip_text="Go to the service caller",
        )

        # Service Type
        self.service_type_group = self.pref_page.add_group(title="Service Type")

        # Service Servers
        self.service_servers_group = self.pref_page.add_group(
            title="Service Servers", empty_group_text="Service has no servers"
        )

        # Service Clients
        self.service_clients_group = self.pref_page.add_group(
            title="Service Clients", empty_group_text="Service has no clients"
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a server/client of the service
        self.available_nodes = self.ros2_connector.get_available_nodes()
        return len(self.available_nodes) > 0

    def refresh_ui(self):
        def add_srv_type_row(srv_type: str):
            srv_type_row = PrefRow(title=srv_type)  # , subtitle=node_full_name)
            srv_type_row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=InterfaceInfoPage,
                subpage_kwargs={"interface_full_name": srv_type},
            )
            self.service_type_group.add_row(srv_type_row)

        if isinstance(self.service_types, str):
            add_srv_type_row(self.service_types)
        elif isinstance(self.service_types, list):
            for srv_type in self.service_types:
                add_srv_type_row(srv_type)

        for node_name, node_namespace, node_full_name in sorted(self.available_nodes, key=itemgetter(0)):
            # add those nodes, that serve this service
            self.service_server_list = self.ros2_connector.get_service_servers_by_node(
                node_name=node_name,
                node_namespace=node_namespace,
            )
            if any(self.service_name in service for service in self.service_server_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.service_servers_group.add_row(row)

            # add those nodes, that are clients to this service
            self.service_client_list = self.ros2_connector.get_service_clients_by_node(
                node_name=node_name, node_namespace=node_namespace
            )
            if any(self.service_name in service for service in self.service_client_list):
                row = PrefRow(title=node_name, subtitle=node_full_name)
                if _is_hidden_name(node_name):
                    row.add_prefix_icon(HIDDEN_OBJ_ICON, tooltip_text="Hidden node")

                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=NodeInfoPage,
                    subpage_kwargs={"node_full_name": node_full_name},
                )
                self.service_clients_group.add_row(row)

        # add the counts as descriptions
        self.service_servers_group.set_description_to_row_count()
        self.service_clients_group.set_description_to_row_count()

    def reset_ui(self):
        self.service_type_group.clear()
        self.service_servers_group.clear()
        self.service_clients_group.clear()

    def trigger(self):
        self.on_goto_caller_page()

    def on_goto_caller_page(self):
        self.nav_view.push(ServiceCallPage(preselect_service=self.service_name))
