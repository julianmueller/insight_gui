# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re

from ros2doctor.api import generate_reports

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.buttons import CopyButton


class DoctorPage(ContentPage):
    __gtype_name__ = "DoctorPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Doctor")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_search_entry_placeholder_text("Ask the doctor")
        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        self.network_config_group = self.pref_page.add_group(
            title="NETWORK CONFIGURATION", empty_group_text="Refresh to show network configuration"
        )
        self.package_versions_group = self.pref_page.add_group(
            title="PACKAGE VERSIONS", empty_group_text="Refresh to show package versions"
        )
        self.platform_info_group = self.pref_page.add_group(
            title="PLATFORM INFORMATION", empty_group_text="Refresh to show platform information"
        )
        self.qos_compatibility_group = self.pref_page.add_group(
            title="QOS COMPATIBILITY LIST", empty_group_text="Refresh to show QoS compatibility list"
        )
        self.rmw_info_group = self.pref_page.add_group(
            title="RMW MIDDLEWARE", empty_group_text="Refresh to show RMW middleware"
        )
        self.ros2_info_group = self.pref_page.add_group(
            title="ROS2 INFORMATION", empty_group_text="Refresh to show ROS2 information"
        )
        self.topic_list_group = self.pref_page.add_group(title="TOPIC LIST", empty_group_text="Refresh to show topics")

    def refresh_blocking(self, *args) -> bool:
        self.reports = generate_reports()
        return len(self.reports) > 0

    def refresh_gui(self, *args):
        for report in self.reports:
            if report.name == "NETWORK CONFIGURATION":
                # TODO these should be somehow grouped by network device
                for item in report.items:
                    self.network_config_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

                if self.network_config_group.num_rows == 0:
                    self.network_config_group.set_empty_group_text(
                        "No network configuration found. Refresh to try again."
                    )

            elif report.name == "PACKAGE VERSIONS":
                rows = []
                for item in sorted(report.items):
                    row: PrefRow = PrefRow(title=item[0], subtitle=item[1])

                    re_match = re.match(r"^latest\=([^,]+), local\=([^,]+)$", item[1])
                    latest_version = re_match.group(1).strip()
                    local_version = re_match.group(2).strip()
                    if latest_version != local_version:
                        row.add_prefix_icon("software-update-available-symbolic", tooltip_text="Update available")
                    rows.append(row)
                self.package_versions_group.add_rows_idle(rows)

                if self.package_versions_group.num_rows == 0:
                    self.package_versions_group.set_empty_group_text("No package versions found.")

            elif report.name == "PLATFORM INFORMATION":
                rows = []
                for item in sorted(report.items):
                    rows.append(PrefRow(title=item[0], subtitle=item[1]))
                self.platform_info_group.add_rows_idle(rows)

                if self.platform_info_group.num_rows == 0:
                    self.platform_info_group.set_empty_group_text(
                        "No platform information found. Refresh to try again."
                    )

            elif report.name == "QOS COMPATIBILITY LIST":
                if len(report.items) == 1:
                    self.qos_compatibility_group.add_row(PrefRow(title=report.items[0][0], subtitle=report.items[0][1]))

                else:
                    rows = []
                    for i in range(0, len(report.items), 4):
                        # print(i)
                        topic_type = report.items[i]
                        pub_node = report.items[i + 1]
                        sub_node = report.items[i + 2]
                        compatibility_status = report.items[i + 3]

                        row = PrefRow(title=topic_type[1])
                        row.set_use_markup(True)
                        row.set_subtitle(subtitle=f"publisher_node: {pub_node[1]}\nsubscriber_node: {sub_node[1]}")
                        if compatibility_status[1] == "OK":
                            row.add_prefix_icon("check-symbolic")
                        else:
                            row.add_prefix_icon("dialog-error-symbolic")
                        rows.append(row)
                    self.qos_compatibility_group.add_rows_idle(rows)

                # for item in report.items:
                #     self.qos_compatibility_group.add_row(PrefRow(title=item[0], subtitle=item[1]))

                if self.qos_compatibility_group.num_rows == 0:
                    self.qos_compatibility_group.set_empty_group_text(
                        "No QoS compatibility list found. Refresh to try again."
                    )

            elif report.name == "RMW MIDDLEWARE":
                rows = []
                for item in sorted(report.items):
                    rows.append(PrefRow(title=item[0], subtitle=item[1]))
                self.rmw_info_group.add_rows_idle(rows)

                if self.rmw_info_group.num_rows == 0:
                    self.rmw_info_group.set_empty_group_text("No RMW middleware found. Refresh to try again.")

            elif report.name == "ROS 2 INFORMATION":
                rows = []
                for item in report.items:
                    row = PrefRow(title=item[0], subtitle=item[1])
                    row.add_suffix(CopyButton(copy_text=row.get_subtitle(), toast_host=self.toast_overlay))
                    rows.append(row)
                self.ros2_info_group.add_rows_idle(rows)

                if self.ros2_info_group.num_rows == 0:
                    self.ros2_info_group.set_empty_group_text("No ROS 2 information found. Refresh to try again.")

            elif report.name == "TOPIC LIST":
                rows = []
                for i in range(0, len(report.items), 4):
                    topic_type = report.items[i]
                    pub_node = report.items[i + 1]
                    sub_node = report.items[i + 2]
                    compatibility_status = report.items[i + 3]

                    row = PrefRow(title=topic_type[1])
                    row.set_use_markup(True)
                    row.set_subtitle(subtitle=f"publisher_node: {pub_node[1]}\nsubscriber_node: {sub_node[1]}")
                    if compatibility_status[1] == "OK":
                        row.add_prefix_icon("checkbox-checked-symbolic")
                    else:
                        row.add_prefix_icon("dialog-error-symbolic")
                    rows.append(row)
                self.topic_list_group.add_rows_idle(rows)

                if self.topic_list_group.num_rows == 0:
                    self.topic_list_group.set_empty_group_text("No topics found. Refresh to try again.")

    def clear_gui(self):
        self.network_config_group.clear()
        self.package_versions_group.clear()
        self.platform_info_group.clear()
        self.qos_compatibility_group.clear()
        self.rmw_info_group.clear()
        self.ros2_info_group.clear()
        self.topic_list_group.clear()


# TODO add NetworkHelloPage for 'ros2 doctor hello'
