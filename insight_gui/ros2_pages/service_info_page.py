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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.models.service_item import ServiceItem
from insight_gui.ros2_pages.service_call_page import ServiceCallPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.model_rows import InterfaceTypeRow, NodeRow


class ServiceInfoPage(ContentPage):
    __gtype_name__ = "ServiceInfoPage"

    def __init__(self, service: ServiceItem, **kwargs):
        super().__init__(searchable=True, refreshable=True, **kwargs)
        super().set_title(f"Service {service.full_name}")

        self.service = service
        self.service_full_name = service.full_name
        self.service_interface_full_name = service.interface.full_name
        self.detach_kwargs = {"service": service}

        self.open_call_page_btn = super().add_bottom_left_btn(
            label="Open Caller",
            icon_name="call-start-symbolic",
            func=self._on_goto_caller_page,
            tooltip_text="Go to the service caller page",
        )

        # Service Interface Type
        self.service_interface_type_group = self.pref_page.add_group(title="Service Interface Type")

        # Service Servers
        self.service_servers_group = self.pref_page.add_group(
            title="Service Servers", placeholder_text="This service has no servers."
        )

        # Service Clients
        self.service_clients_group = self.pref_page.add_group(
            title="Service Clients", placeholder_text="This service has no clients."
        )

    def refresh_bg(self) -> bool:
        # first, gather all nodes, to check which of them is a server/client of the service
        self.server_nodes = []
        self.client_nodes = []

        for node in self.ros2_connector.collect_nodes():
            servers = self.ros2_connector.collect_service_servers_by_node(node=node)
            if any(server.full_name == self.service_full_name for server in servers):
                self.server_nodes.append(node)

            clients = self.ros2_connector.collect_service_clients_by_node(node=node)
            if any(client.full_name == self.service_full_name for client in clients):
                self.client_nodes.append(node)

        return bool(self.server_nodes or self.client_nodes)

    def refresh_ui(self):
        # create a row for the service type # TODO maybe rather add the request/response as rows?
        interface_type_row = InterfaceTypeRow(interface=self.service.interface, nav_view=self.nav_view)
        self._add_rows_async(self.service_interface_type_group, (interface_type_row,), batch_size=1)
        self._add_item_rows_async(
            self.service_servers_group,
            self.server_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.service_servers_group.set_description_to_row_count,
        )
        self._add_item_rows_async(
            self.service_clients_group,
            self.client_nodes,
            self._build_node_row,
            batch_size=8,
            on_done=self.service_clients_group.set_description_to_row_count,
        )

    def _build_node_row(self, node) -> NodeRow:
        return NodeRow(node=node, nav_view=self.nav_view)

    def reset_ui(self):
        self.service_interface_type_group.clear()
        self.service_servers_group.clear()
        self.service_clients_group.clear()

    def trigger(self):
        self._on_goto_caller_page()

    def _on_goto_caller_page(self):
        self._push_subpage(ServiceCallPage, {"preselect_service": self.service})
