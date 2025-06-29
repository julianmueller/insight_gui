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

import re
from typing import Dict

from rclpy.topic_or_service_is_hidden import topic_or_service_is_hidden

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from insight_gui.ros2_pages.service_info_page import ServiceInfoPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class ServiceListPage(ContentPage):
    __gtype_name__ = "ServiceListPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Service List")
        super().set_empty_page_text("No services to show")
        super().set_search_entry_placeholder_text("Search for services")
        super().set_refresh_fail_text("No services found. Refresh to try again.")

        self.service_ns_groups: Dict[PrefGroup] = {}

    def refresh_bg(self) -> bool:
        self.available_services = self.ros2_connector.get_available_services()
        return len(self.available_services) > 0

    def refresh_ui(self):
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

            # put all services in one group if grouping is disabled
            if not self.app.settings.get_boolean("group-services-by-namespace"):
                namespace = ""

            # get the namespace group of the service
            if namespace in self.service_ns_groups.keys():
                group = self.service_ns_groups[namespace]
            else:
                group = self.pref_page.add_group(title=namespace)
                self.service_ns_groups[namespace] = group

            # TODO this somehow messes with the sorting :( again ...

            row = PrefRow(title=service_name, subtitle=service_types)
            row.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
            row.subtitle_lbl.set_tooltip_text(service_name)

            if topic_or_service_is_hidden(service_name):
                row.add_prefix_icon("eye-not-looking-symbolic", tooltip_text="Hidden service")

            row.set_subpage_link(
                nav_view=self.nav_view,
                subpage_class=ServiceInfoPage,
                subpage_kwargs={"service_name": service_name, "service_types": service_types},
            )
            group.add_row(row)

        # sort the groups alphabetically by title
        self.pref_page.sort_groups()

    def reset_ui(self):
        for group in reversed(self.service_ns_groups.values()):
            self.pref_page.remove_group(group)
        self.service_ns_groups.clear()
