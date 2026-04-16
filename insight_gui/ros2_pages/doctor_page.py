# =============================================================================
# doctor_page.py
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

from ros2doctor.api import generate_reports

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow
from insight_gui.widgets.buttons import CopyButton


class DoctorPage(ContentPage):
    __gtype_name__ = "DoctorPage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_title("Doctor")
        super().set_search_entry_placeholder_text("Ask the doctor")

        self.network_config_group = self.pref_page.add_group(
            title="NETWORK CONFIGURATION", placeholder_text="Refresh to show network configuration"
        )
        self.package_versions_group = self.pref_page.add_group(
            title="PACKAGE VERSIONS", placeholder_text="Refresh to show package versions"
        )
        self.platform_info_group = self.pref_page.add_group(
            title="PLATFORM INFORMATION", placeholder_text="Refresh to show platform information"
        )
        self.qos_compatibility_group = self.pref_page.add_group(
            title="QOS COMPATIBILITY LIST", placeholder_text="Refresh to show QoS compatibility list"
        )
        self.rmw_info_group = self.pref_page.add_group(
            title="RMW MIDDLEWARE", placeholder_text="Refresh to show RMW middleware"
        )
        self.ros2_info_group = self.pref_page.add_group(
            title="ROS2 INFORMATION", placeholder_text="Refresh to show ROS2 information"
        )
        self.topic_list_group = self.pref_page.add_group(title="TOPIC LIST", placeholder_text="Refresh to show topics")

    def refresh_bg(self) -> bool:
        self.reports = generate_reports()
        return len(self.reports) > 0

    def refresh_ui(self):
        for report in self.reports:
            if report.name == "NETWORK CONFIGURATION":
                # TODO these should be somehow grouped by network device
                self._add_item_rows_async(self.network_config_group, report.items, self._build_info_row)

                if not report.items:
                    self.network_config_group.set_placeholder_text(
                        "No network configuration found. Refresh to try again."
                    )

            elif report.name == "PACKAGE VERSIONS":
                self._add_item_rows_async(
                    self.package_versions_group,
                    sorted(report.items),
                    self._build_package_version_row,
                )

                if not report.items:
                    self.package_versions_group.set_placeholder_text("No package versions found.")

            elif report.name == "PLATFORM INFORMATION":
                self._add_item_rows_async(self.platform_info_group, sorted(report.items), self._build_info_row)

                if not report.items:
                    self.platform_info_group.set_placeholder_text(
                        "No platform information found. Refresh to try again."
                    )

            elif report.name == "QOS COMPATIBILITY LIST":
                if len(report.items) == 1:
                    self._add_item_rows_async(
                        self.qos_compatibility_group,
                        report.items,
                        self._build_info_row,
                        batch_size=1,
                    )

                else:
                    self._add_item_rows_async(
                        self.qos_compatibility_group,
                        self._iter_report_chunks(report.items, 4),
                        self._build_qos_compatibility_row,
                    )

                if not report.items:
                    self.qos_compatibility_group.set_placeholder_text(
                        "No QoS compatibility list found. Refresh to try again."
                    )

            elif report.name == "RMW MIDDLEWARE":
                self._add_item_rows_async(self.rmw_info_group, sorted(report.items), self._build_info_row)

                if not report.items:
                    self.rmw_info_group.set_placeholder_text("No RMW middleware found. Refresh to try again.")

            elif report.name == "ROS 2 INFORMATION":
                self._add_item_rows_async(self.ros2_info_group, report.items, self._build_ros2_info_row)

                if not report.items:
                    self.ros2_info_group.set_placeholder_text("No ROS 2 information found. Refresh to try again.")

            elif report.name == "TOPIC LIST":
                self._add_item_rows_async(
                    self.topic_list_group,
                    self._iter_report_chunks(report.items, 4),
                    self._build_topic_list_row,
                )

                if not report.items:
                    self.topic_list_group.set_placeholder_text("No topics found. Refresh to try again.")

    @staticmethod
    def _iter_report_chunks(items, chunk_size: int):
        return [
            tuple(items[i:i + chunk_size])
            for i in range(0, len(items), chunk_size)
            if len(items[i:i + chunk_size]) == chunk_size
        ]

    @staticmethod
    def _build_info_row(item) -> PrefRow:
        return PrefRow(title=item[0], subtitle=item[1])

    @staticmethod
    def _build_package_version_row(item) -> PrefRow:
        row = PrefRow(title=item[0], subtitle=item[1])

        re_match = re.match(r"^latest\=([^,]+), local\=([^,]+)$", item[1])
        if re_match is None:
            return row

        latest_version = re_match.group(1).strip()
        local_version = re_match.group(2).strip()
        if latest_version != local_version:
            row.add_prefix_icon("software-update-available-symbolic", tooltip_text="Update available")
        return row

    def _build_ros2_info_row(self, item) -> PrefRow:
        row = self._build_info_row(item)
        row.add_suffix(CopyButton(copy_text=row.get_subtitle(), toast_host=self.toast_overlay))
        return row

    @staticmethod
    def _build_qos_compatibility_row(items) -> PrefRow:
        topic_type, pub_node, sub_node, compatibility_status = items
        row = PrefRow(title=topic_type[1])
        row.set_use_markup(True)
        row.set_subtitle(subtitle=f"publisher_node: {pub_node[1]}\nsubscriber_node: {sub_node[1]}")
        if compatibility_status[1] == "OK":
            row.add_prefix_icon("check-symbolic")
        else:
            row.add_prefix_icon("dialog-error-symbolic")
        return row

    @staticmethod
    def _build_topic_list_row(items) -> PrefRow:
        topic_type, pub_node, sub_node, compatibility_status = items
        row = PrefRow(title=topic_type[1])
        row.set_use_markup(True)
        row.set_subtitle(subtitle=f"publisher_node: {pub_node[1]}\nsubscriber_node: {sub_node[1]}")
        if compatibility_status[1] == "OK":
            row.add_prefix_icon("checkbox-checked-symbolic")
        else:
            row.add_prefix_icon("dialog-error-symbolic")
        return row

    def reset_ui(self):
        self.network_config_group.clear()
        self.package_versions_group.clear()
        self.platform_info_group.clear()
        self.qos_compatibility_group.clear()
        self.rmw_info_group.clear()
        self.ros2_info_group.clear()
        self.topic_list_group.clear()


# TODO add NetworkHelloPage for 'ros2 doctor hello'
