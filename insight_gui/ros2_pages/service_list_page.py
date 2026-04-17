# =============================================================================
# service_list_page.py
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

from typing import Dict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.model_rows import ServiceRow


class ServiceListPage(ContentPage):
    __gtype_name__ = "ServiceListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service List")
        super().set_placeholder_text("No services to show")
        super().set_search_entry_placeholder_text("Search for services")
        super().set_refresh_fail_text("No services found. Refresh to try again.")

        self.service_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.available_services = self.ros2_connector.collect_services()
        return bool(self.available_services)

    def refresh_ui(self):
        services_by_group: Dict[PrefGroup, list] = {}
        for service in self.available_services:
            # put all services in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-services-by-namespace"):
                namespace = ""
                title = "Services"
            else:
                namespace = service.namespace if service.namespace else "/"
                title = namespace

            # get the namespace group of the service
            if namespace in self.service_ns_groups.keys():
                group = self.service_ns_groups[namespace]
            else:
                description = "global namespace" if namespace == "/" else ""
                group = self.pref_page.add_group(title=title, description=description, collapsable=True)
                self.service_ns_groups[namespace] = group

            services_by_group.setdefault(group, []).append(service)

        self.pref_page.sort_groups()

        for group, services in services_by_group.items():
            self._add_item_rows_async(
                group,
                services,
                self._build_service_row,
                batch_size=10,
            )

    def _build_service_row(self, service) -> ServiceRow:
        return ServiceRow(service=service, nav_view=self.nav_view)

    def reset_ui(self):
        for group in reversed(self.service_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.service_ns_groups.clear()
